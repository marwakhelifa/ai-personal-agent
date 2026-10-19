# AI Personal Agent

Un assistant téléphonique qui prend les rendez-vous à votre place. On appelle un numéro Twilio, on parle en arabe ou en darija, et le rendez-vous est ajouté directement dans Google Calendar.

J'ai construit ce projet pour voir jusqu'où on peut aller avec des outils gratuits : Groq pour comprendre ce que dit l'appelant, Twilio pour la téléphonie, Google Calendar pour l'agenda, et Render pour l'hébergement.

## Ce que fait l'application

Quand quelqu'un appelle, l'assistant l'accueille à voix haute et écoute sa demande (par exemple « je veux un rendez-vous chez le dentiste demain après 16 h »). Il pose ensuite les questions qui manquent : le service, la date, l'heure. Une fois que l'appelant confirme, le rendez-vous est créé dans Google Calendar et enregistré dans une base SQLite.

L'assistant garde aussi en mémoire certaines préférences. Si l'appelant dit qu'il préfère les rendez-vous en fin d'après-midi, il s'en souviendra à l'appel suivant, et l'accueil sera différent pour un client déjà connu.

## Technologies

- Python 3.10+ et FastAPI
- Twilio Voice (appels et reconnaissance vocale)
- Groq (compréhension de la demande)
- Google Calendar API
- SQLite
- Render pour le déploiement

## Structure du projet

```
app/
  main.py               routes FastAPI et déroulement de l'appel
  llm_agent.py          appel à Groq, extraction du service, de la date et de l'heure
  calendar_service.py   création des événements Google Calendar
  db.py                 base SQLite (état des appels, préférences, réservations)
  timeutils.py          date du jour et conversion date/heure (fuseau Africa/Algiers)
  config.py             lecture des variables d'environnement
scripts/
  setup_google_calendar.py   autorisation Google, à lancer une seule fois
data/                   emplacement de la base de données
render.yaml             configuration du déploiement sur Render
```

## Installation en local

Il faut Python 3.10 ou plus récent et Git.

```bash
git clone https://github.com/marwakhelifa/ai-personal-agent.git
cd ai-personal-agent

python -m venv venv
source venv/bin/activate      # sous Windows : venv\Scripts\activate
pip install -r requirements.txt
```

### Les comptes à créer

Trois services sont nécessaires, tous gratuits pour un usage de test.

**Groq.** Créez un compte sur [console.groq.com](https://console.groq.com), puis générez une clé dans la rubrique API Keys. Elle commence par `gsk_`.

**Twilio.** Créez un compte d'essai sur [twilio.com](https://www.twilio.com/try-twilio). Notez l'Account SID et l'Auth Token affichés sur le tableau de bord, puis achetez un numéro compatible Voice avec le crédit offert. En mode essai, Twilio n'accepte d'appels que depuis des numéros vérifiés : ajoutez le vôtre.

**Google Calendar.** Dans la [console Google Cloud](https://console.cloud.google.com) :

1. Créez un projet et activez la Google Calendar API.
2. Configurez l'écran de consentement OAuth en mode External, et ajoutez votre adresse Gmail dans les utilisateurs de test.
3. Créez un identifiant OAuth de type application de bureau, téléchargez le JSON et renommez-le `credentials.json`.
4. Placez ce fichier à la racine du projet.

### Autoriser l'accès à l'agenda

```bash
python scripts/setup_google_calendar.py
```

Le navigateur s'ouvre, vous vous connectez avec le compte ajouté plus haut et vous acceptez. Un fichier `token.json` est alors créé. Ne le publiez jamais, il est déjà exclu par le `.gitignore`.

### Variables d'environnement

```bash
cp .env.example .env
```

Ouvrez `.env` et remplissez :

```
GROQ_API_KEY=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
ADMIN_KEY=
```

`ADMIN_KEY` est un mot de passe de votre choix qui protège la route `/bookings` (elle contient des numéros de téléphone). Sans cette clé, la route est désactivée.

## Lancer et tester

```bash
uvicorn app.main:app --reload --port 8000
```

Si tout va bien, `http://localhost:8000` renvoie un petit JSON avec le statut « running ».

Twilio doit pouvoir joindre votre machine. Le plus simple est d'utiliser [ngrok](https://ngrok.com/download) :

```bash
ngrok config add-authtoken VOTRE_TOKEN   # une seule fois
ngrok http 8000
```

Copiez l'adresse en `https://xxxx.ngrok-free.app`, puis dans la console Twilio, ouvrez votre numéro et remplissez le champ « A call comes in » avec :

```
https://xxxx.ngrok-free.app/voice
```

Appelez ensuite votre numéro Twilio et demandez un rendez-vous. Vous pouvez voir les réservations enregistrées sur `http://localhost:8000/bookings?key=VOTRE_ADMIN_KEY`.

## Routes disponibles

| Route | Rôle |
|---|---|
| `GET /` | vérifie que l'application tourne |
| `GET /health` | état de santé (utile pour l'hébergeur) |
| `GET /bookings?key=...` | liste des réservations en JSON (protégée par `ADMIN_KEY`) |
| `POST /voice` | point d'entrée appelé par Twilio au début d'un appel |
| `POST /process_speech` | appelé à chaque réponse de l'appelant |

## Déploiement sur Render

1. Créez un compte sur [render.com](https://render.com) et connectez votre dépôt GitHub.
2. Choisissez New, puis Web Service, puis ce dépôt. Render lit `render.yaml` tout seul.
3. Renseignez les mêmes variables que dans votre `.env`. Pour `GOOGLE_TOKEN_JSON`, collez le contenu complet de votre fichier `token.json` (il n'est pas dans le dépôt, donc Render ne peut pas le lire autrement).
4. Une fois le build terminé, remplacez l'adresse ngrok dans Twilio par celle de Render, par exemple `https://ai-personal-agent.onrender.com/voice`.

Avec l'offre gratuite, le service se met en veille après un moment d'inactivité. Le premier appel qui suit peut donc mettre quelques secondes à démarrer. De plus, le disque de l'offre gratuite est temporaire : la base SQLite peut être réinitialisée à chaque redéploiement. C'est acceptable pour une démo, pas pour un vrai usage.

## Limites actuelles

- Le modèle convertit les expressions comme « gadwa » ou « après-demain » en date précise à partir de la date du jour (fuseau Africa/Algiers). Une date invalide ou passée est refusée et redemandée, mais le modèle peut encore se tromper sur des formulations inhabituelles.
- Les conflits de calendrier (deux rendez-vous à la même heure) ne sont pas détectés.
- La reconnaissance vocale de la darija (langue `ar-SA` de Twilio) reste imparfaite.
- Le compte d'essai Twilio limite les appels aux numéros vérifiés.
- Un seul agenda est géré, celui du compte Google autorisé.

## Pistes d'amélioration

- Passer un appel au nom de l'utilisateur, pas seulement en recevoir.
- Mieux gérer les annulations et les modifications de rendez-vous (l'annulation ne fait pour l'instant que raccrocher).
- Vérifier la signature des requêtes Twilio et ajouter des tests automatisés.
- Ajouter une petite interface web au lieu de la route `/bookings`.

## Sécurité

Les fichiers `.env`, `credentials.json` et `token.json` contiennent des secrets et ne doivent jamais être envoyés sur GitHub. Si une clé a été publiée par erreur, révoquez-la tout de suite et générez-en une nouvelle.

## Auteure

Saliha Marwa Khelifa · [LinkedIn](https://www.linkedin.com/in/marwa-khelifa-6359983a7) · marwakhelifa17@gmail.com
