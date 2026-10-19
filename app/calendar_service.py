"""
Création des rendez-vous dans Google Calendar.

Les identifiants viennent soit de la variable d'environnement GOOGLE_TOKEN_JSON
(cas de Render), soit du fichier token.json à la racine du projet
(généré par scripts/setup_google_calendar.py).
"""

import os
import json
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.config import (
    GOOGLE_TOKEN_FILE, GOOGLE_TOKEN_JSON, GOOGLE_CALENDAR_SCOPES, TIMEZONE,
)
from app.timeutils import parse_slot


def _get_calendar_service():
    if GOOGLE_TOKEN_JSON:
        creds = Credentials.from_authorized_user_info(
            json.loads(GOOGLE_TOKEN_JSON), GOOGLE_CALENDAR_SCOPES
        )
    elif os.path.exists(GOOGLE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, GOOGLE_CALENDAR_SCOPES)
    else:
        raise RuntimeError(
            "Identifiants Google introuvables : lancez d'abord "
            "python scripts/setup_google_calendar.py (ou définissez GOOGLE_TOKEN_JSON)."
        )
    return build("calendar", "v3", credentials=creds)


def create_appointment(service_name: str, date_text: str, time_text: str, phone_number: str) -> dict:
    """
    Crée un événement de 30 minutes à la date et à l'heure demandées
    (date au format YYYY-MM-DD, heure au format HH:MM, fuseau Africa/Algiers).
    """
    slot = parse_slot(date_text, time_text)
    if slot is None:
        print(f"[CALENDAR ERROR] date ou heure invalide : {date_text!r} {time_text!r}")
        return {"success": False, "event_id": "", "link": ""}

    try:
        calendar_service = _get_calendar_service()
        end = slot + datetime.timedelta(minutes=30)

        event = {
            "summary": f"Rendez-vous : {service_name}",
            "description": f"Réservé via AI Personal Agent pour le numéro {phone_number}",
            "start": {"dateTime": slot.isoformat(), "timeZone": TIMEZONE},
            "end": {"dateTime": end.isoformat(), "timeZone": TIMEZONE},
        }

        created = calendar_service.events().insert(calendarId="primary", body=event).execute()
        return {"success": True, "event_id": created.get("id"), "link": created.get("htmlLink")}

    except Exception as e:
        print(f"[CALENDAR ERROR] {e}")
        return {"success": False, "event_id": "", "link": ""}
