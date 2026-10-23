"""
key_manager.py — Multi-API-Key rotation for CodeAtlas.

Reads GEMINI_API_KEY_1 … GEMINI_API_KEY_N (plus the legacy GEMINI_API_KEY)
from the environment.  When a key hits a rate-limit or quota error the
manager marks it as temporarily unavailable and falls back to the next one.

Usage
-----
    from key_manager import get_client, rotate_on_error

    client = get_client()          # returns a google.genai.Client
    try:
        resp = client.models.generate_content(...)
    except Exception as e:
        client = rotate_on_error(e)   # swap to next key; re-raises if no keys left
        resp = client.models.generate_content(...)

Or use the higher-level helper:
    from key_manager import generate_content

    text = generate_content(model, prompt)   # handles rotation internally
"""

from __future__ import annotations

import logging
import os
import time
import threading
from typing import Any

from dotenv import load_dotenv
from google import genai

load_dotenv()

logger = logging.getLogger(__name__)

# ── collect keys ────────────────────────────────────────────────────────────
def _load_keys() -> list[str]:
    keys: list[str] = []
    # numbered keys take precedence: GEMINI_API_KEY_1 … GEMINI_API_KEY_10
    for i in range(1, 11):
        k = os.getenv(f"GEMINI_API_KEY_{i}", "").strip()
        if k:
            keys.append(k)
    # fall back to the legacy single key
    legacy = os.getenv("GEMINI_API_KEY", "").strip()
    if legacy and legacy not in keys:
        keys.append(legacy)
    if not keys:
        logger.error("No Gemini API keys found in environment!")
    else:
        logger.info("KeyManager: %d API key(s) loaded.", len(keys))
    return keys


_KEYS: list[str] = _load_keys()

# ── per-key cooldown tracking ────────────────────────────────────────────────
_COOLDOWN_SECS = 60          # seconds to wait before retrying an exhausted key
_lock = threading.Lock()
_cooldowns: dict[int, float] = {}   # key index → epoch time when it can be retried

# ── client cache ─────────────────────────────────────────────────────────────
_clients: dict[int, genai.Client] = {}


def _get_client_for(idx: int) -> genai.Client:
    if idx not in _clients:
        _clients[idx] = genai.Client(api_key=_KEYS[idx])
    return _clients[idx]


def _is_available(idx: int) -> bool:
    with _lock:
        until = _cooldowns.get(idx, 0)
    return time.time() >= until


def _mark_exhausted(idx: int) -> None:
    with _lock:
        _cooldowns[idx] = time.time() + _COOLDOWN_SECS
    logger.warning(
        "KeyManager: key #%d marked exhausted — will retry after %ds.",
        idx + 1, _COOLDOWN_SECS,
    )


def _pick_key() -> int | None:
    """Return the index of the first available key, or None."""
    for i in range(len(_KEYS)):
        if _is_available(i):
            return i
    return None


# ── public API ───────────────────────────────────────────────────────────────

def get_client() -> genai.Client:
    """Return a Gemini Client using the current active key."""
    if not _KEYS:
        raise RuntimeError("No Gemini API keys configured.")
    idx = _pick_key()
    if idx is None:
        # all keys on cooldown — use the one whose cooldown expires soonest
        with _lock:
            idx = min(_cooldowns, key=lambda i: _cooldowns[i], default=0)
        logger.warning("All keys on cooldown — using key #%d anyway.", idx + 1)
    return _get_client_for(idx)


def _is_quota_error(exc: Exception) -> bool:
    """Heuristic: detect rate-limit / quota errors from Gemini."""
    msg = str(exc).lower()
    return any(kw in msg for kw in (
        "429", "resource_exhausted", "quota", "rate limit",
        "too many requests", "ratelimitexceeded",
    ))


def generate_content(model: str, contents: Any, **kwargs) -> Any:
    """
    Call client.models.generate_content() with automatic key rotation.

    Tries every available key before giving up.  Returns the API response.
    Raises the last exception if all keys fail.
    """
    if not _KEYS:
        raise RuntimeError("No Gemini API keys configured.")

    last_exc: Exception | None = None
    tried: set[int] = set()

    for _ in range(len(_KEYS)):
        idx = _pick_key()
        if idx is None or idx in tried:
            # all available keys tried; wait briefly and try cooldown keys
            break
        tried.add(idx)
        client = _get_client_for(idx)
        try:
            return client.models.generate_content(
                model=model, contents=contents, **kwargs
            )
        except Exception as exc:
            last_exc = exc
            if _is_quota_error(exc):
                _mark_exhausted(idx)
                logger.info("KeyManager: quota hit on key #%d — rotating.", idx + 1)
            else:
                # non-quota error: don't rotate, just re-raise
                raise

    raise last_exc or RuntimeError("All Gemini API keys exhausted.")


def embed_content(model: str, contents: Any, **kwargs) -> Any:
    """
    Call client.models.embed_content() with automatic key rotation.
    """
    if not _KEYS:
        raise RuntimeError("No Gemini API keys configured.")

    last_exc: Exception | None = None
    tried: set[int] = set()

    for _ in range(len(_KEYS)):
        idx = _pick_key()
        if idx is None or idx in tried:
            break
        tried.add(idx)
        client = _get_client_for(idx)
        try:
            return client.models.embed_content(
                model=model, contents=contents, **kwargs
            )
        except Exception as exc:
            last_exc = exc
            if _is_quota_error(exc):
                _mark_exhausted(idx)
                logger.info("KeyManager: quota hit on key #%d — rotating (embed).", idx + 1)
            else:
                raise

    raise last_exc or RuntimeError("All Gemini API keys exhausted (embed).")


def key_status() -> list[dict]:
    """Return a list of {index, available, cooldown_remaining} for monitoring."""
    now = time.time()
    result = []
    for i, _ in enumerate(_KEYS):
        until = _cooldowns.get(i, 0)
        result.append({
            "index": i + 1,
            "available": now >= until,
            "cooldown_remaining": max(0, round(until - now)),
        })
    return result
