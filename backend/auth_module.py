"""
backend/auth_module.py
======================
Lightweight, zero-dependency SQLite authentication, user session persistence,
and multi-thread chat history storage for CodeAtlas.

Features:
- Secure password hashing via bcrypt
- Cryptographically secure bearer tokens via secrets.token_urlsafe
- User registration (signup), login, logout, and token authentication
- User uploaded projects association (switch between projects)
- Multi-thread chat history management (ChatGPT-style chat threads & messages)
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import bcrypt

logger = logging.getLogger("codeatlas.auth")

# Database path
_DB_PATH = Path(os.environ.get("CODEATLAS_DB_PATH", Path(__file__).resolve().parent.parent / "codeatlas.db"))


def _get_connection() -> sqlite3.Connection:
    """Return a connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db() -> None:
    """Create authentication and chat tables if they do not exist."""
    with _get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL COLLATE NOCASE,
            email TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS auth_tokens (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_projects (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            project_name TEXT NOT NULL,
            files_count INTEGER DEFAULT 0,
            functions_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, session_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS chat_threads (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            user_id TEXT,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            text TEXT NOT NULL,
            citations_json TEXT DEFAULT '[]',
            created_at TEXT NOT NULL,
            FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_tokens_token ON auth_tokens(token);
        CREATE INDEX IF NOT EXISTS idx_projects_user ON user_projects(user_id);
        CREATE INDEX IF NOT EXISTS idx_threads_session ON chat_threads(session_id);
        CREATE INDEX IF NOT EXISTS idx_messages_thread ON chat_messages(thread_id);
        """)
        logger.info("Initialized CodeAtlas SQLite auth and chat database at %s", _DB_PATH)


# Initialize DB on module import
init_db()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Authentication & User Management
# ---------------------------------------------------------------------------

def signup(username: str, email: str, password: str) -> dict[str, Any]:
    """Register a new user, return user data and auth token."""
    username = username.strip()
    email = email.strip().lower()

    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters long.")
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        raise ValueError("Username can only contain letters, numbers, underscores, and hyphens.")
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        raise ValueError("Invalid email address format.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    pw_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    pw_hash = bcrypt.hashpw(pw_bytes, salt).decode("utf-8")

    user_id = str(uuid.uuid4())
    now = _now_iso()
    token = secrets.token_urlsafe(32)

    with _get_connection() as conn:
        # Check existing
        existing = conn.execute(
            "SELECT username, email FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()
        if existing:
            if existing["username"].lower() == username.lower():
                raise ValueError("Username is already taken.")
            raise ValueError("Email is already registered.")

        conn.execute(
            "INSERT INTO users (id, username, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, email, pw_hash, now)
        )
        conn.execute(
            "INSERT INTO auth_tokens (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_id, now)
        )

    return {
        "token": token,
        "user": {
            "id": user_id,
            "username": username,
            "email": email,
            "created_at": now,
        }
    }


def login(username_or_email: str, password: str) -> dict[str, Any]:
    """Authenticate user with username or email, return user data and auth token."""
    identifier = username_or_email.strip()
    with _get_connection() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (identifier, identifier.lower())
        ).fetchone()

        if not user:
            raise ValueError("Invalid username/email or password.")

        pw_bytes = password.encode("utf-8")
        hash_bytes = user["password_hash"].encode("utf-8")

        if not bcrypt.checkpw(pw_bytes, hash_bytes):
            raise ValueError("Invalid username/email or password.")

        token = secrets.token_urlsafe(32)
        now = _now_iso()
        conn.execute(
            "INSERT INTO auth_tokens (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user["id"], now)
        )

        return {
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "created_at": user["created_at"],
            }
        }


def get_user_by_token(token: Optional[str]) -> Optional[dict[str, Any]]:
    """Look up user by bearer token."""
    if not token or not token.strip():
        return None
    token = token.strip()
    if token.startswith("Bearer "):
        token = token[7:].strip()

    with _get_connection() as conn:
        row = conn.execute("""
            SELECT u.id, u.username, u.email, u.created_at
            FROM users u
            JOIN auth_tokens t ON u.id = t.user_id
            WHERE t.token = ?
        """, (token,)).fetchone()

        if row:
            return dict(row)
        return None


def logout(token: Optional[str]) -> bool:
    """Invalidate an auth token."""
    if not token:
        return False
    if token.startswith("Bearer "):
        token = token[7:].strip()

    with _get_connection() as conn:
        cur = conn.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# User Projects Association
# ---------------------------------------------------------------------------

def link_user_project(user_id: str, session_id: str, project_name: str, files_count: int = 0, functions_count: int = 0) -> None:
    """Associate an uploaded session with a user."""
    proj_id = str(uuid.uuid4())
    now = _now_iso()
    with _get_connection() as conn:
        conn.execute("""
            INSERT INTO user_projects (id, user_id, session_id, project_name, files_count, functions_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, session_id) DO UPDATE SET
                project_name = excluded.project_name,
                files_count = excluded.files_count,
                functions_count = excluded.functions_count
        """, (proj_id, user_id, session_id, project_name, files_count, functions_count, now))


def get_user_projects(user_id: str) -> list[dict[str, Any]]:
    """List all projects associated with a user, newest first."""
    with _get_connection() as conn:
        rows = conn.execute("""
            SELECT session_id, project_name, files_count, functions_count, created_at
            FROM user_projects
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Chat History Management (Threads & Messages)
# ---------------------------------------------------------------------------

def list_threads(session_id: str, user_id: Optional[str] = None) -> list[dict[str, Any]]:
    """List all chat threads for a session (and optionally filtered by user)."""
    with _get_connection() as conn:
        if user_id:
            rows = conn.execute("""
                SELECT t.id, t.session_id, t.user_id, t.title, t.created_at, t.updated_at,
                       (SELECT COUNT(*) FROM chat_messages m WHERE m.thread_id = t.id) as message_count
                FROM chat_threads t
                WHERE t.session_id = ? AND (t.user_id = ? OR t.user_id IS NULL)
                ORDER BY t.updated_at DESC
            """, (session_id, user_id)).fetchall()
        else:
            rows = conn.execute("""
                SELECT t.id, t.session_id, t.user_id, t.title, t.created_at, t.updated_at,
                       (SELECT COUNT(*) FROM chat_messages m WHERE m.thread_id = t.id) as message_count
                FROM chat_threads t
                WHERE t.session_id = ?
                ORDER BY t.updated_at DESC
            """, (session_id,)).fetchall()

        return [dict(r) for r in rows]


def create_thread(session_id: str, title: str, user_id: Optional[str] = None) -> dict[str, Any]:
    """Create a new chat thread."""
    thread_id = str(uuid.uuid4())
    now = _now_iso()
    clean_title = (title or "New Chat").strip()[:80]

    with _get_connection() as conn:
        conn.execute("""
            INSERT INTO chat_threads (id, session_id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (thread_id, session_id, user_id, clean_title, now, now))

    return {
        "id": thread_id,
        "session_id": session_id,
        "user_id": user_id,
        "title": clean_title,
        "created_at": now,
        "updated_at": now,
        "message_count": 0,
    }


def get_thread(thread_id: str) -> Optional[dict[str, Any]]:
    """Get thread info."""
    with _get_connection() as conn:
        row = conn.execute("SELECT * FROM chat_threads WHERE id = ?", (thread_id,)).fetchone()
        return dict(row) if row else None


def get_thread_messages(thread_id: str) -> list[dict[str, Any]]:
    """Get all messages for a thread in chronological order."""
    with _get_connection() as conn:
        rows = conn.execute("""
            SELECT id, thread_id, sender, text, citations_json, created_at
            FROM chat_messages
            WHERE thread_id = ?
            ORDER BY created_at ASC
        """, (thread_id,)).fetchall()

        res = []
        for r in rows:
            d = dict(r)
            try:
                d["citations"] = json.loads(d.pop("citations_json", "[]") or "[]")
            except Exception:
                d["citations"] = []
            res.append(d)
        return res


def add_message(thread_id: str, sender: str, text: str, citations: Optional[list] = None) -> dict[str, Any]:
    """Append a user or AI message to a thread and update thread updated_at timestamp."""
    msg_id = str(uuid.uuid4())
    now = _now_iso()
    citations_json = json.dumps(citations or [])

    with _get_connection() as conn:
        conn.execute("""
            INSERT INTO chat_messages (id, thread_id, sender, text, citations_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (msg_id, thread_id, sender, text, citations_json, now))

        conn.execute("""
            UPDATE chat_threads SET updated_at = ? WHERE id = ?
        """, (now, thread_id))

    return {
        "id": msg_id,
        "thread_id": thread_id,
        "sender": sender,
        "text": text,
        "citations": citations or [],
        "created_at": now,
    }


def delete_thread(thread_id: str) -> bool:
    """Delete a chat thread and all its messages."""
    with _get_connection() as conn:
        cur = conn.execute("DELETE FROM chat_threads WHERE id = ?", (thread_id,))
        return cur.rowcount > 0


def update_thread_title(thread_id: str, title: str) -> bool:
    """Rename a chat thread."""
    clean_title = title.strip()[:80]
    now = _now_iso()
    with _get_connection() as conn:
        cur = conn.execute("UPDATE chat_threads SET title = ?, updated_at = ? WHERE id = ?", (clean_title, now, thread_id))
        return cur.rowcount > 0
