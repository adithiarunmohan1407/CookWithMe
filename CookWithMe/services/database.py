"""
database.py
------------
Handles all SQLite persistence for CookWithMe:
  - Chat sessions (so the sidebar can list "previous chats")
  - Chat messages (full conversation history per session)
  - User preferences (favorite cuisine, veg/non-veg, spice level, allergies)

Kept deliberately simple (raw sqlite3, no ORM) so it's easy to read,
audit, and swap out later if the project grows.
"""

import sqlite3
import os
import uuid
from datetime import datetime
from contextlib import contextmanager

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/cookwithme.db")


def _ensure_data_dir():
    """Make sure the folder that will hold the .db file actually exists."""
    directory = os.path.dirname(DATABASE_PATH)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


@contextmanager
def get_connection():
    """
    Context manager for a SQLite connection.
    Ensures connections are always closed, even if an error occurs.
    """
    _ensure_data_dir()
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """
    Create all required tables if they don't already exist.
    Safe to call every time the app starts.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # One row per chat "conversation" shown in the sidebar
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT 'New Chat',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Every message (user or bot) belonging to a session
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )
        """)

        # Long-term memory of user cooking preferences.
        # Single-row-per-key design keeps it flexible without a schema change
        # every time a new preference type is added.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


# ---------------------------------------------------------------------
# Chat session helpers
# ---------------------------------------------------------------------

def create_session(title="New Chat"):
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (session_id, title, now, now),
        )
    return session_id


def list_sessions():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM chat_sessions ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def rename_session(session_id, new_title):
    with get_connection() as conn:
        conn.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?",
            (new_title, datetime.utcnow().isoformat(), session_id),
        )


def delete_session(session_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))


def touch_session(session_id):
    """Bump updated_at so the sidebar shows most-recently-active chats first."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), session_id),
        )


# ---------------------------------------------------------------------
# Chat message helpers
# ---------------------------------------------------------------------

def add_message(session_id, role, content):
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now),
        )
    touch_session(session_id)


def get_messages(session_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM chat_messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        return [dict(row) for row in rows]


# ---------------------------------------------------------------------
# User preference helpers (favorite cuisine, veg/non-veg, spice level, allergies)
# ---------------------------------------------------------------------

def set_preference(key, value):
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_preferences (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, value, now),
        )


def get_preference(key, default=None):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM user_preferences WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default


def get_all_preferences():
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM user_preferences").fetchall()
        return {row["key"]: row["value"] for row in rows}
