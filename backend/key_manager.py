"""
key_manager.py — Multi-API-Key rotation and resilience engine for CodeAtlas.

Features:
- Reads GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3, GEMINI_API_KEY_4
  (and legacy GEMINI_API_KEY) from .env.
- Automatically tracks rate limits, quota exhaustion (429), and spikes in demand (503).
- Rotates to the next available API key automatically.
- Fallback model cascading: if the primary model encounters 503 or 404,
  it falls back smoothly to active models (e.g., gemini-2.5-flash, gemini-3.5-flash-lite).
- Thread-safe cooldown management and key status reporting for UI monitoring.
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

# ── Fallback model sequence ──────────────────────────────────────────────────
_FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
]

# ── Load keys ────────────────────────────────────────────────────────────────
def _load_keys() -> list[str]:
    keys: list[str] = []
    # Check GEMINI_API_KEY_1 through GEMINI_API_KEY_10
    for i in range(1, 11):
        k = os.getenv(f"GEMINI_API_KEY_{i}", "").strip()
        if k and k not in keys:
            keys.append(k)

    # Also check single legacy key
    legacy = os.getenv("GEMINI_API_KEY", "").strip()
    if legacy and legacy not in keys:
        keys.append(legacy)

    if not keys:
        logger.warning("KeyManager: No Gemini API keys found in environment.")
    else:
        logger.info("KeyManager: Loaded %d Gemini API key(s).", len(keys))
    return keys


_KEYS: list[str] = _load_keys()

# ── Cooldown tracking ────────────────────────────────────────────────────────
_COOLDOWN_SECS = 45          # seconds to cooldown an exhausted or rate-limited key
_lock = threading.Lock()
_cooldowns: dict[int, float] = {}   # key index → timestamp until available
_clients: dict[int, genai.Client] = {}


def _get_client_for(idx: int) -> genai.Client:
    with _lock:
        if idx not in _clients:
            _clients[idx] = genai.Client(api_key=_KEYS[idx])
        return _clients[idx]


def _is_available(idx: int) -> bool:
    with _lock:
        until = _cooldowns.get(idx, 0)
    return time.time() >= until


def _mark_exhausted(idx: int, reason: str = "rate limit") -> None:
    with _lock:
        _cooldowns[idx] = time.time() + _COOLDOWN_SECS
    logger.warning(
        "KeyManager: Key #%d cooldown for %ds (reason: %s).",
        idx + 1, _COOLDOWN_SECS, reason
    )


def _pick_key() -> int | None:
    """Return index of first available key, or None if all are on cooldown."""
    for i in range(len(_KEYS)):
        if _is_available(i):
            return i
    return None


def _is_rotatable_error(exc: Exception) -> bool:
    """Detect errors that warrant rotating to another API key."""
    msg = str(exc).lower()
    return any(kw in msg for kw in (
        "429", "resource_exhausted", "quota", "rate limit",
        "too many requests", "ratelimitexceeded",
        "503", "unavailable", "high demand", "spikes in demand", "overloaded"
    ))


def _is_model_unavailable_error(exc: Exception) -> bool:
    """Detect errors that warrant falling back to an alternate model."""
    msg = str(exc).lower()
    return any(kw in msg for kw in (
        "404", "not_found", "is no longer available",
        "503", "unavailable", "high demand", "spikes in demand"
    ))


# ── Public API ───────────────────────────────────────────────────────────────

def get_client() -> genai.Client:
    """Return a Gemini Client using the active key."""
    if not _KEYS:
        raise RuntimeError("No Gemini API keys configured in .env.")
    idx = _pick_key()
    if idx is None:
        with _lock:
            idx = min(_cooldowns, key=lambda i: _cooldowns[i], default=0)
    return _get_client_for(idx)


def generate_content(model: str, contents: Any, **kwargs) -> Any:
    """
    Call client.models.generate_content() with key rotation and model fallback.
    Tries each configured API key, and if model is unavailable, tries fallback models.
    """
    if not _KEYS:
        raise RuntimeError("No Gemini API keys configured in .env.")

    # Build model candidate list (requested model first, then fallbacks)
    model_candidates = [model]
    for fb in _FALLBACK_MODELS:
        if fb not in model_candidates:
            model_candidates.append(fb)

    last_exc: Exception | None = None

    for candidate_model in model_candidates:
        tried_keys: set[int] = set()

        for _ in range(len(_KEYS)):
            idx = _pick_key()
            if idx is None or idx in tried_keys:
                break
            tried_keys.add(idx)
            client = _get_client_for(idx)

            try:
                resp = client.models.generate_content(
                    model=candidate_model,
                    contents=contents,
                    **kwargs,
                )
                return resp
            except Exception as exc:
                last_exc = exc
                if _is_rotatable_error(exc):
                    _mark_exhausted(idx, reason=str(exc)[:60])
                    logger.info(
                        "KeyManager: Rotating away from Key #%d on model '%s'.",
                        idx + 1, candidate_model
                    )
                    time.sleep(0.5)
                elif _is_model_unavailable_error(exc):
                    # Model not available on this endpoint, try next candidate model
                    logger.warning(
                        "KeyManager: Model '%s' unavailable (%s), trying fallback model...",
                        candidate_model, str(exc)[:60]
                    )
                    break
                else:
                    # Non-retryable error
                    raise

    raise last_exc or RuntimeError("All Gemini API keys and fallback models exhausted.")


def embed_content(model: str, contents: Any, **kwargs) -> Any:
    """
    Call client.models.embed_content() with automatic key rotation.
    """
    if not _KEYS:
        raise RuntimeError("No Gemini API keys configured in .env.")

    last_exc: Exception | None = None
    tried_keys: set[int] = set()

    for _ in range(len(_KEYS)):
        idx = _pick_key()
        if idx is None or idx in tried_keys:
            break
        tried_keys.add(idx)
        client = _get_client_for(idx)

        try:
            return client.models.embed_content(
                model=model,
                contents=contents,
                **kwargs,
            )
        except Exception as exc:
            last_exc = exc
            if _is_rotatable_error(exc):
                _mark_exhausted(idx, reason=str(exc)[:60])
                time.sleep(0.5)
            else:
                raise

    raise last_exc or RuntimeError("All Gemini API keys exhausted for embeddings.")


def key_status() -> list[dict]:
    """Return list of {index, available, cooldown_remaining} for all configured keys."""
    now = time.time()
    result = []
    for i in range(len(_KEYS)):
        until = _cooldowns.get(i, 0)
        result.append({
            "index": i + 1,
            "available": now >= until,
            "cooldown_remaining": max(0, round(until - now)),
        })
    return result
