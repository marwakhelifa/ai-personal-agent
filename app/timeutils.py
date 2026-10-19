"""Outils de date et d'heure (fuseau de l'Algérie, UTC+1)."""

import datetime
from app.config import UTC_OFFSET_HOURS

LOCAL_TZ = datetime.timezone(datetime.timedelta(hours=UTC_OFFSET_HOURS))

# Jours de la semaine en arabe (lundi = 0), pour informer le modèle de la date du jour.
JOURS_AR = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]


def now_local() -> datetime.datetime:
    """Date et heure actuelles en Algérie."""
    return datetime.datetime.now(LOCAL_TZ)


def parse_slot(date_text, time_text):
    """
    Convertit une date « YYYY-MM-DD » et une heure « HH:MM » en datetime local.
    Renvoie None si le format est invalide.
    """
    try:
        date_part = datetime.datetime.strptime(str(date_text).strip(), "%Y-%m-%d")
    except (ValueError, TypeError):
        return None

    time_part = None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            time_part = datetime.datetime.strptime(str(time_text).strip(), fmt)
            break
        except (ValueError, TypeError):
            continue
    if time_part is None:
        return None

    return datetime.datetime(
        date_part.year, date_part.month, date_part.day,
        time_part.hour, time_part.minute, tzinfo=LOCAL_TZ,
    )
