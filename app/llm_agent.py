"""
Analyse de ce que dit l'appelant (darija, arabe ou français) avec Groq.
Le modèle renvoie l'intention et les informations du rendez-vous en JSON,
en tenant compte des préférences déjà enregistrées pour ce numéro
et de la date du jour (pour convertir « demain » en vraie date).
"""

import json
from groq import Groq
from app.config import GROQ_API_KEY
from app.timeutils import now_local, JOURS_AR

client = Groq(api_key=GROQ_API_KEY)

MODEL_NAME = "llama-3.3-70b-versatile"  # modèle Llama 3.3 hébergé sur Groq

# Le prompt est en arabe volontairement : l'agent parle à des utilisateurs arabophones.
SYSTEM_PROMPT = """
أنت مساعد صوتي جزائري ذكي اسمه "المساعد". تفهم الدارجة الجزائرية والعربية الفصحى
والفرنسية، وأحيانًا مزيج بينها في نفس الجملة. مهمتك في هذه النسخة هي فهم طلبات
حجز المواعيد (طبيب أسنان، حلاق، مطعم...) واستخراج معطياتها.

أرجع فقط JSON بهذا الشكل بالضبط، بدون أي نص إضافي قبله أو بعده:

{
  "intent": "book_appointment" | "unclear" | "confirm" | "cancel" | "set_preference",
  "service": "نوع الخدمة المطلوبة أو null",
  "date": "التاريخ بصيغة YYYY-MM-DD فقط، أو null",
  "time": "الوقت بصيغة 24 ساعة HH:MM فقط (مثال 16:00)، أو null",
  "preference_key": "اسم التفضيل إذا قال المستخدم شيئًا يريد تذكّره دائمًا، وإلا null",
  "preference_value": "قيمة التفضيل أو null",
  "reply_text": "رد صوتي قصير ومهذب بالدارجة الجزائرية يوجّه المستخدم للخطوة التالية"
}

قواعد مهمة:
- حوّل التعابير مثل "غدوة" و"بعد غدوة" و"الجمعة الجاية" إلى تاريخ فعلي YYYY-MM-DD انطلاقًا من تاريخ اليوم المذكور أسفل.
- المواعيد عادة نهارية: "الساعة 4" تعني 16:00، و"الساعة 10" تعني 10:00.
- إذا قال المستخدم وقتًا تقريبيًا فقط مثل "بعد الرابعة"، اطلب منه ساعة محددة ولا تخمّن.
- إذا ذكر المستخدم تفضيلًا عامًا مثل "أنا نفضل المواعيد بعد الرابعة" اجعل intent = "set_preference".
- استخدم التفضيلات المحفوظة (إن وُجدت) لتوجيه أسئلتك، لكن لا تخترع ساعة محددة لم يقلها المستخدم.
- إذا كانت المعلومات ناقصة، اسأل فقط عن المعلومة الناقصة.
- إذا كان الطلب مكتملًا (خدمة + تاريخ + وقت)، لخّص الطلب بالتاريخ والساعة واطلب التأكيد.
- عندما يؤكد المستخدم، اجعل intent = "confirm" وأبقِ service وdate وtime كما هي.
"""

KEYS = ["intent", "service", "date", "time", "preference_key", "preference_value", "reply_text"]
VALID_INTENTS = {"book_appointment", "unclear", "confirm", "cancel", "set_preference"}
FALLBACK_REPLY = "سامحني ما فهمتش مليح، عاود قولّي واش تحب."


def _clean(value):
    """Le modèle écrit parfois « null » comme texte : on le ramène à None."""
    if isinstance(value, str) and value.strip().lower() in ("", "null", "none"):
        return None
    return value


def _fallback() -> dict:
    result = {key: None for key in KEYS}
    result["intent"] = "unclear"
    result["reply_text"] = FALLBACK_REPLY
    return result


def understand(user_text: str, conversation_state: dict, user_preferences: dict) -> dict:
    today = now_local()
    context_note = (
        f"\nتاريخ اليوم: {today:%Y-%m-%d} ({JOURS_AR[today.weekday()]})، التوقيت: الجزائر."
        f"\nمعطيات محفوظة في هذه المكالمة حتى الآن: {json.dumps(conversation_state, ensure_ascii=False)}"
        f"\nتفضيلات هذا المستخدم المحفوظة من مكالمات سابقة: {json.dumps(user_preferences, ensure_ascii=False)}"
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + context_note},
                {"role": "user", "content": user_text},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        parsed = json.loads(response.choices[0].message.content)
        if not isinstance(parsed, dict):
            raise ValueError("la réponse n'est pas un objet JSON")
    except Exception as e:
        # Erreur réseau, quota Groq, JSON invalide... : l'appel ne doit jamais planter.
        print(f"[LLM ERROR] {e}")
        return _fallback()

    result = {key: _clean(parsed.get(key)) for key in KEYS}
    if result["intent"] not in VALID_INTENTS:
        result["intent"] = "unclear"
    if not result["reply_text"]:
        result["reply_text"] = FALLBACK_REPLY
    return result
