"""
backend/auth_module.py
======================
Database-agnostic authentication, user session persistence, and multi-thread
chat history storage for CodeAtlas.

Supports:
- Free Cloud PostgreSQL (Supabase, Neon.tech, Render Postgres) via DATABASE_URL
- Local SQLite (codeatlas.db) if no cloud database URL is provided
- Secure password hashing via bcrypt (rounds=12)
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
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger("codeatlas.auth")

# Determine database engine
_DATABASE_URL = os.environ.get("DATABASE_URL")

def _create_db_engine() -> Engine:
    """Initialize SQLAlchemy engine for either Cloud Postgres or SQLite."""
    url = _DATABASE_URL
    if not url or not url.strip():
        # Fall back to SQLite
        db_file = Path(os.environ.get("CODEATLAS_DB_PATH", Path(__file__).resolve().parent.parent / "codeatlas.db"))
        sqlite_url = f"sqlite:///{db_file}"
        logger.info("Using local SQLite database: %s", db_file)
        return create_engine(sqlite_url, connect_args={"check_same_thread": False})

    url = url.strip()
    # Normalize postgres URL to use pure-python pg8000 driver if available
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+pg8000://", 1)
    elif url.startswith("postgresql://") and "+pg8000" not in url and "+psycopg2" not in url:
        try:
            import pg8000
            url = url.replace("postgresql://", "postgresql+pg8000://", 1)
        except ImportError:
            pass

    # Strip sslmode if pg8000 handles ssl differently
    logger.info("Connecting to Cloud Database: %s", url.split("@")[-1] if "@" in url else "configured URL")
    return create_engine(url, pool_pre_ping=True)


engine: Engine = _create_db_engine()


def init_db() -> None:
    """Create authentication and chat tables if they do not exist."""
    schema_statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR(64) PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(160) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at VARCHAR(40) NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS auth_tokens (
            token VARCHAR(128) PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL,
            created_at VARCHAR(40) NOT NULL,
            expires_at VARCHAR(40),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS user_projects (
            id VARCHAR(64) PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL,
            session_id VARCHAR(64) NOT NULL,
            project_name VARCHAR(255) NOT NULL,
            files_count INTEGER DEFAULT 0,
            functions_count INTEGER DEFAULT 0,
            created_at VARCHAR(40) NOT NULL,
            UNIQUE(user_id, session_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_threads (
            id VARCHAR(64) PRIMARY KEY,
            session_id VARCHAR(64) NOT NULL,
            user_id VARCHAR(64),
            title VARCHAR(255) NOT NULL,
            created_at VARCHAR(40) NOT NULL,
            updated_at VARCHAR(40) NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id VARCHAR(64) PRIMARY KEY,
            thread_id VARCHAR(64) NOT NULL,
            sender VARCHAR(20) NOT NULL,
            text TEXT NOT NULL,
            citations_json TEXT DEFAULT '[]',
            created_at VARCHAR(40) NOT NULL,
            FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
        )
        """
    ]

    with engine.begin() as conn:
        for stmt in schema_statements:
            conn.execute(text(stmt))

    logger.info("Initialized CodeAtlas tables (users, auth_tokens, user_projects, chat_threads, chat_messages).")


# Initialize DB on module load
try:
    init_db()
except Exception as e:
    logger.warning("Database init warning: %s", e)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Authentication & User Management
# ---------------------------------------------------------------------------

def signup(username: str, email: str, password: str) -> dict[str, Any]:
    """Register a new user, return user profile and auth token."""
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

    with engine.begin() as conn:
        # Check existing username or email
        existing = conn.execute(
            text("SELECT username, email FROM users WHERE LOWER(username) = LOWER(:u) OR LOWER(email) = LOWER(:e)"),
            {"u": username, "e": email}
        ).mappings().first()

        if existing:
            if existing["username"].lower() == username.lower():
                raise ValueError("Username is already taken.")
            raise ValueError("Email is already registered.")

        conn.execute(
            text("INSERT INTO users (id, username, email, password_hash, created_at) VALUES (:id, :u, :e, :p, :c)"),
            {"id": user_id, "u": username, "e": email, "p": pw_hash, "c": now}
        )
        conn.execute(
            text("INSERT INTO auth_tokens (token, user_id, created_at) VALUES (:t, :u, :c)"),
            {"t": token, "u": user_id, "c": now}
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
    """Authenticate user with username or email, return user profile and token."""
    identifier = username_or_email.strip()
    with engine.begin() as conn:
        user = conn.execute(
            text("SELECT * FROM users WHERE LOWER(username) = LOWER(:ident) OR LOWER(email) = LOWER(:ident)"),
            {"ident": identifier}
        ).mappings().first()

        if not user:
            raise ValueError("Invalid username/email or password.")

        pw_bytes = password.encode("utf-8")
        hash_bytes = user["password_hash"].encode("utf-8")

        if not bcrypt.checkpw(pw_bytes, hash_bytes):
            raise ValueError("Invalid username/email or password.")

        token = secrets.token_urlsafe(32)
        now = _now_iso()
        conn.execute(
            text("INSERT INTO auth_tokens (token, user_id, created_at) VALUES (:t, :u, :c)"),
            {"t": token, "u": user["id"], "c": now}
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

    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT u.id, u.username, u.email, u.created_at
                FROM users u
                JOIN auth_tokens t ON u.id = t.user_id
                WHERE t.token = :t
            """),
            {"t": token}
        ).mappings().first()

        if row:
            return dict(row)
        return None


def logout(token: Optional[str]) -> bool:
    """Invalidate an auth token."""
    if not token:
        return False
    if token.startswith("Bearer "):
        token = token[7:].strip()

    with engine.begin() as conn:
        res = conn.execute(text("DELETE FROM auth_tokens WHERE token = :t"), {"t": token})
        return res.rowcount > 0


# ---------------------------------------------------------------------------
# User Projects Association
# ---------------------------------------------------------------------------

def link_user_project(user_id: str, session_id: str, project_name: str, files_count: int = 0, functions_count: int = 0) -> None:
    """Associate an uploaded session with a user account."""
    proj_id = str(uuid.uuid4())
    now = _now_iso()
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO user_projects (id, user_id, session_id, project_name, files_count, functions_count, created_at)
                VALUES (:id, :u, :s, :p, :files, :funcs, :c)
                ON CONFLICT(user_id, session_id) DO UPDATE SET
                    project_name = :p,
                    files_count = :files,
                    functions_count = :funcs
            """),
            {
                "id": proj_id,
                "u": user_id,
                "s": session_id,
                "p": project_name,
                "files": files_count,
                "funcs": functions_count,
                "c": now,
            }
        )


def get_user_projects(user_id: str) -> list[dict[str, Any]]:
    """List all projects associated with a user, newest first."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT session_id, project_name, files_count, functions_count, created_at
                FROM user_projects
                WHERE user_id = :u
                ORDER BY created_at DESC
            """),
            {"u": user_id}
        ).mappings().all()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Chat History Management (Threads & Messages)
# ---------------------------------------------------------------------------

def list_threads(session_id: str, user_id: Optional[str] = None) -> list[dict[str, Any]]:
    """List all chat threads for a session (optionally filtered by user)."""
    with engine.connect() as conn:
        if user_id:
            rows = conn.execute(
                text("""
                    SELECT t.id, t.session_id, t.user_id, t.title, t.created_at, t.updated_at,
                           (SELECT COUNT(*) FROM chat_messages m WHERE m.thread_id = t.id) as message_count
                    FROM chat_threads t
                    WHERE t.session_id = :s AND (t.user_id = :u OR t.user_id IS NULL)
                    ORDER BY t.updated_at DESC
                """),
                {"s": session_id, "u": user_id}
            ).mappings().all()
        else:
            rows = conn.execute(
                text("""
                    SELECT t.id, t.session_id, t.user_id, t.title, t.created_at, t.updated_at,
                           (SELECT COUNT(*) FROM chat_messages m WHERE m.thread_id = t.id) as message_count
                    FROM chat_threads t
                    WHERE t.session_id = :s
                    ORDER BY t.updated_at DESC
                """),
                {"s": session_id}
            ).mappings().all()

        return [dict(r) for r in rows]


def create_thread(session_id: str, title: str, user_id: Optional[str] = None) -> dict[str, Any]:
    """Create a new chat thread."""
    thread_id = str(uuid.uuid4())
    now = _now_iso()
    clean_title = (title or "New Chat").strip()[:80]

    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO chat_threads (id, session_id, user_id, title, created_at, updated_at)
                VALUES (:id, :s, :u, :t, :c, :up)
            """),
            {"id": thread_id, "s": session_id, "u": user_id, "t": clean_title, "c": now, "up": now}
        )

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
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM chat_threads WHERE id = :id"),
            {"id": thread_id}
        ).mappings().first()
        return dict(row) if row else None


def get_thread_messages(thread_id: str) -> list[dict[str, Any]]:
    """Get all messages for a thread in chronological order."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, thread_id, sender, text, citations_json, created_at
                FROM chat_messages
                WHERE thread_id = :t
                ORDER BY created_at ASC
            """),
            {"t": thread_id}
        ).mappings().all()

        res = []
        for r in rows:
            d = dict(r)
            try:
                d["citations"] = json.loads(d.pop("citations_json", "[]") or "[]")
            except Exception:
                d["citations"] = []
            res.append(d)
        return res


def add_message(thread_id: str, sender: str, text_content: str, citations: Optional[list] = None) -> dict[str, Any]:
    """Append a user or AI message to a thread and update thread updated_at timestamp."""
    msg_id = str(uuid.uuid4())
    now = _now_iso()
    citations_json = json.dumps(citations or [])

    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO chat_messages (id, thread_id, sender, text, citations_json, created_at)
                VALUES (:id, :t, :s, :txt, :cjson, :c)
            """),
            {"id": msg_id, "t": thread_id, "s": sender, "txt": text_content, "cjson": citations_json, "c": now}
        )

        conn.execute(
            text("UPDATE chat_threads SET updated_at = :up WHERE id = :id"),
            {"up": now, "id": thread_id}
        )

    return {
        "id": msg_id,
        "thread_id": thread_id,
        "sender": sender,
        "text": text_content,
        "citations": citations or [],
        "created_at": now,
    }


def delete_thread(thread_id: str) -> bool:
    """Delete a chat thread and all its messages."""
    with engine.begin() as conn:
        res = conn.execute(text("DELETE FROM chat_threads WHERE id = :id"), {"id": thread_id})
        return res.rowcount > 0


def update_thread_title(thread_id: str, title: str) -> bool:
    """Rename a chat thread."""
    clean_title = title.strip()[:80]
    now = _now_iso()
    with engine.begin() as conn:
        res = conn.execute(
            text("UPDATE chat_threads SET title = :t, updated_at = :up WHERE id = :id"),
            {"t": clean_title, "up": now, "id": thread_id}
        )
        return res.rowcount > 0
