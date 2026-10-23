"""
utils.py — Shared utility functions for TaskFlow.
Provides ID generation, timestamps, table formatting, and string helpers.
"""

import hashlib
import time
import uuid
from typing import Any


def generate_id() -> str:
    """Generate a unique task ID using UUID4."""
    return str(uuid.uuid4())


def get_timestamp() -> str:
    """Return the current Unix timestamp as a string."""
    return str(int(time.time()))


def format_table(headers: list[str], rows: list[tuple]) -> str:
    """
    Render a simple ASCII table.

    Args:
        headers: Column header labels.
        rows:    List of tuples, one per row.

    Returns:
        A multi-line string with the formatted table.
    """
    if not rows:
        return "(no data)"

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    def fmt_row(cells):
        return "| " + " | ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(cells)) + " |"

    sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    lines = [sep, fmt_row(headers), sep]
    for row in rows:
        lines.append(fmt_row(row))
    lines.append(sep)
    return "\n".join(lines)


def slugify(text: str) -> str:
    """Convert a string to a URL-safe slug."""
    import re
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = text.strip("-")
    return text


def truncate(text: str, max_len: int = 50, suffix: str = "…") -> str:
    """Truncate a string to max_len characters."""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix


def hash_string(s: str) -> str:
    """Return the MD5 hex digest of a string (for deduplication, not security)."""
    return hashlib.md5(s.encode()).hexdigest()


def chunk_list(lst: list, size: int) -> list[list]:
    """Split a list into chunks of a given size."""
    if size <= 0:
        raise ValueError("Chunk size must be positive.")
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide safely, returning *default* when denominator is zero."""
    if denominator == 0:
        return default
    return numerator / denominator
