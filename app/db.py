"""
Accès à la base SQLite. Trois tables :
- bookings : les rendez-vous confirmés
- user_memory : les préférences de chaque appelant (clé : numéro de téléphone)
- call_state : l'état d'un appel en cours, conservé entre deux requêtes HTTP
"""

import sqlite3
import json
import os
from contextlib import contextmanager
from app.config import DATABASE_PATH

os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT NOT NULL,
                service TEXT,
                date TEXT,
                time TEXT,
                calendar_event_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_memory (
                phone_number TEXT PRIMARY KEY,
                preferences_json TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS call_state (
                call_sid TEXT PRIMARY KEY,
                phone_number TEXT,
                state_json TEXT DEFAULT '{}',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


# --- réservations ---
def save_booking(phone_number: str, service: str, date: str, time: str, calendar_event_id: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO bookings (phone_number, service, date, time, calendar_event_id) VALUES (?, ?, ?, ?, ?)",
            (phone_number, service, date, time, calendar_event_id),
        )


def list_bookings() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM bookings ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


# --- préférences des utilisateurs ---
def get_user_preferences(phone_number: str) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT preferences_json FROM user_memory WHERE phone_number = ?", (phone_number,)
        ).fetchone()
        return json.loads(row["preferences_json"]) if row else {}


def update_user_preferences(phone_number: str, new_prefs: dict):
    current = get_user_preferences(phone_number)
    current.update(new_prefs)
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO user_memory (phone_number, preferences_json) VALUES (?, ?)
               ON CONFLICT(phone_number) DO UPDATE SET preferences_json = excluded.preferences_json""",
            (phone_number, json.dumps(current, ensure_ascii=False)),
        )


# --- état des appels en cours ---
def get_call_state(call_sid: str) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT state_json FROM call_state WHERE call_sid = ?", (call_sid,)).fetchone()
        return json.loads(row["state_json"]) if row else {}


def save_call_state(call_sid: str, phone_number: str, state: dict):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO call_state (call_sid, phone_number, state_json) VALUES (?, ?, ?)
               ON CONFLICT(call_sid) DO UPDATE SET state_json = excluded.state_json,
                   updated_at = CURRENT_TIMESTAMP""",
            (call_sid, phone_number, json.dumps(state, ensure_ascii=False)),
        )


def clear_call_state(call_sid: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM call_state WHERE call_sid = ?", (call_sid,))
