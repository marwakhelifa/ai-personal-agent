"""
Point d'entrée de l'application. Gère un appel de bout en bout :
accueil, analyse avec Groq, préférences, réservation Google Calendar, enregistrement SQLite.
"""

import secrets

from fastapi import FastAPI, Form, Header, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from twilio.twiml.voice_response import VoiceResponse, Gather

from app.config import ADMIN_KEY
from app.llm_agent import understand
from app.calendar_service import create_appointment
from app.timeutils import parse_slot, now_local
from app import db

app = FastAPI(title="AI Personal Agent")

db.init_db()


def _xml(response: VoiceResponse) -> Response:
    return Response(content=str(response), media_type="application/xml")


def _ask(response: VoiceResponse, text: str) -> None:
    """Dit `text` à l'appelant puis attend sa réponse vocale."""
    gather = Gather(
        input="speech",
        action="/process_speech",
        method="POST",
        language="ar-SA",
        speech_timeout="auto",
    )
    gather.say(text, language="ar-SA")
    response.append(gather)


@app.get("/")
def root():
    return {"status": "running", "message": "AI Personal Agent is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/bookings")
def get_bookings(
    key: str = Query(default=""),
    x_admin_key: str = Header(default=""),
):
    """
    Liste des réservations (mini tableau de bord).
    Protégée par ADMIN_KEY : /bookings?key=... ou en-tête X-Admin-Key.
    """
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Route désactivée : définissez ADMIN_KEY.")
    provided = key or x_admin_key
    if not secrets.compare_digest(provided, ADMIN_KEY):
        raise HTTPException(status_code=401, detail="Clé invalide.")
    return JSONResponse(content=db.list_bookings())


@app.post("/voice")
def voice_incoming(From: str = Form(default="")):
    """Appelé par Twilio au début de chaque nouvel appel."""
    prefs = db.get_user_preferences(From)

    greeting = "أهلاً بيك، أنا المساعد الذكي متاعك. واش تحب نديرلك؟"
    if prefs:
        greeting = "أهلاً بيك مرة أخرى! واش تحب نديرلك اليوم؟"

    response = VoiceResponse()
    _ask(response, greeting)
    response.say("ما سمعتش حاجة، نعاود نتصل من بعد.", language="ar-SA")
    return _xml(response)


@app.post("/process_speech")
def process_speech(
    CallSid: str = Form(...),
    SpeechResult: str = Form(default=""),
    From: str = Form(default=""),
):
    """Appelé à chaque fois que l'utilisateur a fini de parler (après Gather)."""
    response = VoiceResponse()

    # Rien n'a été reconnu : on redemande sans appeler le modèle.
    if not SpeechResult.strip():
        _ask(response, "ما سمعتكش مليح، عاود قولّي واش تحب.")
        return _xml(response)

    session = db.get_call_state(CallSid)
    prefs = db.get_user_preferences(From)

    result = understand(SpeechResult, session, prefs)
    intent = result["intent"]

    # Mise à jour des informations de réservation de cet appel
    for key in ["service", "date", "time"]:
        if result.get(key):
            session[key] = result[key]
    db.save_call_state(CallSid, From, session)

    if intent == "set_preference" and result.get("preference_key"):
        # L'appelant veut qu'on retienne une préférence générale (ex. : rendez-vous après 16h)
        db.update_user_preferences(From, {result["preference_key"]: result["preference_value"]})
        _ask(response, result["reply_text"])

    elif intent == "cancel":
        response.say(result["reply_text"], language="ar-SA")
        response.hangup()
        db.clear_call_state(CallSid)

    elif intent == "confirm" and all(k in session for k in ["service", "date", "time"]):
        slot = parse_slot(session["date"], session["time"])

        if slot is None or slot < now_local():
            # Date ou heure invalide, ou déjà passée : on les efface et on redemande.
            session.pop("date", None)
            session.pop("time", None)
            db.save_call_state(CallSid, From, session)
            _ask(response, "التاريخ ولا الوقت ما فهمتهمش مليح، ولا فاتو. عاود قولّي نهار والساعة.")
        else:
            booking = create_appointment(
                session["service"], session["date"], session["time"], From
            )
            if booking["success"]:
                db.save_booking(
                    From, session["service"], session["date"], session["time"],
                    booking.get("event_id", ""),
                )
                response.say(result["reply_text"], language="ar-SA")
            else:
                # On ne prétend jamais avoir réservé si Google Calendar a échoué.
                response.say("سامحني، صرات مشكلة وما قدرتش نسجل الموعد. عاود اتصل من بعد.",
                             language="ar-SA")
            response.hangup()
            db.clear_call_state(CallSid)

    else:
        # Il manque encore des informations, ou on attend la confirmation : on continue
        _ask(response, result["reply_text"])

    return _xml(response)
