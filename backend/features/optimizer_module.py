"""
optimizer_module.py
===================
Function optimality checker for CodeAtlas.

Uses Gemini to rate each function's quality, identify anti-patterns,
and produce refactoring suggestions with complexity analysis.
"""

from __future__ import annotations

import json
import os
import re
import sys
import textwrap
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# ensure backend/ is on path so key_manager can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import key_manager

_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client():
    return key_manager.get_client()


def _parse_json_from_response(text: str) -> dict:
    """Extract the first JSON object found in *text*."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    cleaned = re.sub(r"```(?:json)?", "", text).strip().rstrip("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {}


def _rating_label(rating: int) -> str:
    labels = {1: "Poor", 2: "Below Average", 3: "Average", 4: "Good", 5: "Excellent"}
    return labels.get(rating, "Unknown")


def _generate_summary(source: str, name: str) -> str:
    """Ask Gemini for a one-sentence summary of a function."""
    prompt = (
        f"Summarise the following Python function named `{name}` in ONE concise sentence "
        f"(≤20 words). Return ONLY the sentence.\n\n```python\n{source[:3000]}\n```"
    )
    try:
        model    = _get_client()
        if not model:
            return "{}"
        response = key_manager.generate_content(_MODEL, prompt)
        return response.text.strip()
    except Exception:
        return ""


def _lookup_function(func_id: str, function_tree: dict) -> dict | None:
    """Return the function metadata dict for *func_id*, or None if not found."""
    return (function_tree.get("all_functions") or function_tree.get("functions", {})).get(func_id)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_function_optimality(func_id: str, function_tree: dict) -> dict:
    """
    Analyse a single function for optimality.

    Parameters
    ----------
    func_id       : unique identifier of the function in function_tree
    function_tree : parsed project representation

    Returns
    -------
    dict with keys: func_id, name, source, summary, optimality, error
    """
    func = _lookup_function(func_id, function_tree)

    if func is None:
        return {
            "func_id":   func_id,
            "name":      func_id,
            "source":    "",
            "summary":   "",
            "optimality": None,
            "error":     f"Function '{func_id}' not found in function_tree.",
        }

    name    = func.get("name", func_id)
    source  = func.get("source_snippet") or func.get("source", "")
    summary = func.get("summary", "")

    # If no summary exists, generate one via Gemini
    if not summary and source:
        summary = _generate_summary(source, name)

    if not source:
        return {
            "func_id":   func_id,
            "name":      name,
            "source":    source,
            "summary":   summary,
            "optimality": None,
            "error":     "No source code available for this function.",
        }

    prompt = textwrap.dedent(f"""
        You are an expert Python performance and code-quality engineer.

        Analyse the following Python function and return ONLY a JSON object
        (no markdown fences, no extra text) with EXACTLY this structure:

        {{
          "rating": 3,
          "rating_label": "Average",
          "issues": [
            {{
              "type": "complexity|anti_pattern|performance|readability",
              "description": "...",
              "line_hint": "line 12 or a short snippet"
            }}
          ],
          "refactoring_suggestions": [
            {{
              "description": "...",
              "code_example": "..."
            }}
          ],
          "time_complexity":  "O(n)",
          "space_complexity": "O(1)"
        }}

        Rules:
        - rating: integer 1-5 (1 = highly inefficient, 5 = optimal)
        - rating_label must match: 1→"Poor", 2→"Below Average", 3→"Average",
          4→"Good", 5→"Excellent"
        - issues may be empty if none found
        - refactoring_suggestions may be empty if code is optimal

        === FUNCTION NAME ===
        {name}

        === ONE-SENTENCE SUMMARY ===
        {summary or '(not available)'}

        === SOURCE CODE ===
        ```python
        {source[:4000]}
        ```
    """).strip()

    try:
        model    = _get_client()
        if not model:
            raise RuntimeError("GEMINI_API_KEY not configured")
        response = key_manager.generate_content(_MODEL, prompt)
        parsed   = _parse_json_from_response(response.text)

        if not parsed:
            raise ValueError("Gemini returned an unparseable response.")

        # Coerce and validate fields
        rating = int(parsed.get("rating", 3))
        rating = max(1, min(5, rating))  # clamp 1–5

        optimality = {
            "rating":                  rating,
            "rating_label":            parsed.get("rating_label", _rating_label(rating)),
            "issues":                  parsed.get("issues", []),
            "refactoring_suggestions": parsed.get("refactoring_suggestions", []),
            "time_complexity":         parsed.get("time_complexity", "Unknown"),
            "space_complexity":        parsed.get("space_complexity", "Unknown"),
        }

        return {
            "func_id":   func_id,
            "name":      name,
            "source":    source,
            "summary":   summary,
            "optimality": optimality,
            "error":     None,
        }

    except Exception as exc:
        return {
            "func_id":   func_id,
            "name":      name,
            "source":    source,
            "summary":   summary,
            "optimality": None,
            "error":     str(exc),
        }


def bulk_check_file(filepath: str, function_tree: dict) -> list[dict]:
    """
    Run check_function_optimality for every function that belongs to *filepath*.

    Results are sorted ascending by rating (worst-first).

    Parameters
    ----------
    filepath      : path string to match against function_tree entries
    function_tree : parsed project representation

    Returns
    -------
    list of result dicts (same shape as check_function_optimality)
    """
    # Normalise separators for comparison
    norm_target = filepath.replace("\\", "/").lower()

    matching_ids = [
        fid
        for fid, fdata in (function_tree.get("all_functions") or function_tree.get("functions", {})).items()
        if fdata.get("file", "").replace("\\", "/").lower() == norm_target
    ]

    results: list[dict] = []
    for func_id in matching_ids:
        result = check_function_optimality(func_id, function_tree)
        results.append(result)

    def _sort_key(r: dict) -> int:
        opt = r.get("optimality") or {}
        return opt.get("rating", 999)  # errored entries sort last

    results.sort(key=_sort_key)
    return results
