"""
À lancer une seule fois pour autoriser l'accès à Google Calendar.
Le navigateur s'ouvre pour la connexion, puis token.json est créé.

Utilisation : python scripts/setup_google_calendar.py
Il faut d'abord placer credentials.json à la racine (voir README).
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_auth_oauthlib.flow import InstalledAppFlow
from app.config import GOOGLE_CREDENTIALS_FILE, GOOGLE_TOKEN_FILE, GOOGLE_CALENDAR_SCOPES


def main():
    if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
        print(f"❌ Fichier {GOOGLE_CREDENTIALS_FILE} introuvable à la racine du projet.")
        print("Téléchargez-le depuis Google Cloud Console (voir README.md) et placez-le ici.")
        return

    flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS_FILE, GOOGLE_CALENDAR_SCOPES)
    creds = flow.run_local_server(port=0)

    with open(GOOGLE_TOKEN_FILE, "w") as token_file:
        token_file.write(creds.to_json())

    print(f"✅ {GOOGLE_TOKEN_FILE} créé avec succès. Vous pouvez lancer l'application.")
    print("Pour Render : copiez le contenu de ce fichier dans la variable GOOGLE_TOKEN_JSON.")


if __name__ == "__main__":
    main()
