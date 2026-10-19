"""Chargement de la configuration depuis le fichier .env (ou les variables d'environnement)."""

import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "")
DATABASE_PATH = os.environ.get("DATABASE_PATH", "./data/agent.db")

# Clé qui protège la route /bookings (les numéros de téléphone y sont visibles).
# Si elle est vide, la route est désactivée.
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")

GOOGLE_CREDENTIALS_FILE = "credentials.json"
GOOGLE_TOKEN_FILE = "token.json"
# Sur Render, token.json n'est pas dans le dépôt (il est dans le .gitignore) :
# on colle son contenu complet dans cette variable d'environnement.
GOOGLE_TOKEN_JSON = os.environ.get("GOOGLE_TOKEN_JSON", "")
GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]

# L'Algérie est à UTC+1 toute l'année (pas de changement d'heure).
TIMEZONE = "Africa/Algiers"
UTC_OFFSET_HOURS = 1
