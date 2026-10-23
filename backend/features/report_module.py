"""
report_module.py
================
Two-stage project report generator for CodeAtlas.

Stage 1 – Web search: scrapes CVE / known-issue data for every imported library.
Stage 2 – Gemini: synthesises a structured security / quality report from the
           function_tree overview + Stage-1 results.
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

_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-lite')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client():
    return key_manager.get_client()


def _extract_imports(function_tree: dict) -> list[str]:
    """Return a deduplicated list of top-level library names from function_tree."""
    libs: set[str] = set()

    # function_tree["imports"] may be a list of strings like "import os" / "from os import path"
    for raw in function_tree.get("imports", []):
        raw = raw.strip()
        if raw.startswith("from "):
            # from X.Y import Z  →  X
            parts = raw.split()
            if len(parts) >= 2:
                libs.add(parts[1].split(".")[0])
        elif raw.startswith("import "):
            # import X, Y  or  import X.Y
            tokens = raw[len("import "):].split(",")
            for tok in tokens:
                libs.add(tok.strip().split(".")[0].split(" as ")[0])

    # Also collect from individual function metadata
    for func in function_tree.get("functions", {}).values():
        for raw in func.get("imports", []):
            raw = raw.strip()
            if raw.startswith("from "):
                parts = raw.split()
                if len(parts) >= 2:
                    libs.add(parts[1].split(".")[0])
            elif raw.startswith("import "):
                tokens = raw[len("import "):].split(",")
                for tok in tokens:
                    libs.add(tok.strip().split(".")[0].split(" as ")[0])

    # Remove stdlib-looking single-char or obviously empty tokens
    libs.discard("")
    return sorted(libs)


def _web_search_library(lib_name: str) -> tuple[list[dict], list[str]]:
    """
    Search DuckDuckGo for CVEs / known issues for *lib_name*.
    Returns (results_list, urls_list).
    """
    try:
        from duckduckgo_search import DDGS  # lazy import so missing pkg = graceful fail

        query = f"{lib_name} python CVE vulnerability security issue"
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        urls = [r.get("href", r.get("url", "")) for r in results if r]
        return results, urls
    except Exception:
        return [], []


def _build_file_structure(function_tree: dict) -> str:
    """Return a compact textual summary of the project file structure."""
    files: dict[str, list[str]] = {}
    for func_id, func in function_tree.get("functions", {}).items():
        fp = func.get("file", "unknown")
        files.setdefault(fp, []).append(func.get("name", func_id))

    lines = []
    for fp, names in sorted(files.items()):
        lines.append(f"  {fp}: {', '.join(names[:10])}" + (" …" if len(names) > 10 else ""))
    return "\n".join(lines) if lines else "  (no file information available)"


def _parse_json_from_response(text: str) -> dict:
    """Extract the first JSON object found in *text*."""
    # Try raw parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown fences
    cleaned = re.sub(r"```(?:json)?", "", text).strip().rstrip("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find first { … } block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_report(function_tree: dict) -> dict:
    """
    Two-stage report generator.

    Parameters
    ----------
    function_tree : dict
        The parsed project representation from the analyser.

    Returns
    -------
    dict with keys: report, web_search_used, sources, error
    """
    web_search_used = True
    all_sources: list[str] = []
    search_summaries: list[str] = []

    # ------------------------------------------------------------------
    # Stage 1 – Web search for each imported library
    # ------------------------------------------------------------------
    libs = _extract_imports(function_tree)

    if not libs:
        web_search_used = False
    else:
        for lib in libs:
            results, urls = _web_search_library(lib)
            if not results:
                web_search_used = False  # at least one search failed / empty
                search_summaries.append(f"Library: {lib}\n  No search results found.\n")
            else:
                all_sources.extend(u for u in urls if u)
                snippet_text = ""
                for r in results:
                    title = r.get("title", "")
                    body  = r.get("body", r.get("snippet", ""))
                    snippet_text += f"  - {title}: {body[:200]}\n"
                search_summaries.append(f"Library: {lib}\n{snippet_text}")

    web_search_block = "\n".join(search_summaries) if search_summaries else "No web search data available."

    # ------------------------------------------------------------------
    # Stage 2 – Gemini structured report
    # ------------------------------------------------------------------
    file_structure  = _build_file_structure(function_tree)
    syntax_errors   = function_tree.get("syntax_errors", [])
    func_count      = len(function_tree.get("functions", {}))

    # Build a concise function overview (name + summary, capped to avoid token overflow)
    func_overview_lines = []
    for func_id, func in list(function_tree.get("functions", {}).items())[:60]:
        name    = func.get("name", func_id)
        summary = func.get("summary", "")[:120]
        fp      = func.get("file", "")
        func_overview_lines.append(f"  [{fp}] {name}: {summary}")
    func_overview = "\n".join(func_overview_lines) or "  (no functions parsed)"

    prompt = textwrap.dedent(f"""
        You are a senior software security and code-quality auditor.
        Analyse the following Python project and produce a **structured JSON report**.

        === PROJECT OVERVIEW ===
        Total functions: {func_count}
        Syntax errors detected: {len(syntax_errors)}
        Imported libraries: {', '.join(libs) if libs else 'none detected'}

        === FILE STRUCTURE ===
        {file_structure}

        === FUNCTION OVERVIEW (name → summary) ===
        {func_overview}

        === WEB SEARCH RESULTS (CVEs / known issues per library) ===
        {web_search_block}

        === TASK ===
        Return ONLY a JSON object with EXACTLY this shape (no extra keys, no markdown fences):
        {{
          "vulnerabilities": [
            {{
              "severity": "HIGH|MEDIUM|LOW",
              "title": "...",
              "description": "...",
              "affected_code": "...",
              "remediation": "..."
            }}
          ],
          "code_smells": [
            {{
              "severity": "HIGH|MEDIUM|LOW",
              "title": "...",
              "description": "...",
              "affected_code": "...",
              "suggestion": "..."
            }}
          ],
          "improvements": [
            {{
              "priority": "HIGH|MEDIUM|LOW",
              "title": "...",
              "description": "...",
              "suggestion": "..."
            }}
          ],
          "summary": "Executive summary string (2-4 sentences).",
          "overall_score": 75
        }}

        Be specific, cite actual function/file names where possible. overall_score is 0-100.
    """).strip()

    try:
        model    = _get_client()
        if not model:
            raise RuntimeError("GEMINI_API_KEY not configured")
        response = key_manager.generate_content(_MODEL, prompt)
        raw_text = response.text
        parsed   = _parse_json_from_response(raw_text)

        if not parsed:
            raise ValueError("Gemini returned an unparseable response.")

        # Ensure all expected keys exist with safe defaults
        report = {
            "vulnerabilities": parsed.get("vulnerabilities", []),
            "code_smells":     parsed.get("code_smells", []),
            "improvements":    parsed.get("improvements", []),
            "summary":         parsed.get("summary", "Report generated."),
            "overall_score":   int(parsed.get("overall_score", 50)),
        }

        return {
            "report":          report,
            "web_search_used": web_search_used,
            "sources":         list(dict.fromkeys(all_sources)),  # deduplicate, preserve order
            "error":           None,
        }

    except Exception as exc:
        return {
            "report":          None,
            "web_search_used": web_search_used,
            "sources":         list(dict.fromkeys(all_sources)),
            "error":           str(exc),
        }


def export_report_markdown(report: dict, function_tree: dict) -> str:
    """
    Convert a report dict (as returned inside generate_report()["report"])
    into a nicely formatted Markdown string suitable for download.

    Parameters
    ----------
    report        : the inner report dict (not the full generate_report response)
    function_tree : the original project representation (used for metadata)

    Returns
    -------
    str – full Markdown document
    """
    if not report:
        return "# CodeAtlas Report\n\n_No report data available._\n"

    now   = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    score = report.get("overall_score", "N/A")

    lines: list[str] = [
        "# CodeAtlas – Project Analysis Report",
        "",
        f"> Generated: {now}  |  Overall Score: **{score}/100**",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        report.get("summary", "_No summary available._"),
        "",
        "---",
        "",
    ]

    # ── Vulnerabilities ─────────────────────────────────────────────────────
    vulns = report.get("vulnerabilities", [])
    lines += [f"## 🔒 Vulnerabilities ({len(vulns)} found)", ""]
    if vulns:
        for i, v in enumerate(vulns, 1):
            sev = v.get("severity", "UNKNOWN")
            badge = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(sev, "⚪")
            lines += [
                f"### {i}. {badge} [{sev}] {v.get('title', 'Untitled')}",
                "",
                f"**Description:** {v.get('description', '')}",
                "",
                f"**Affected Code:** `{v.get('affected_code', 'N/A')}`",
                "",
                f"**Remediation:** {v.get('remediation', '')}",
                "",
            ]
    else:
        lines += ["_No vulnerabilities detected._", ""]

    lines += ["---", ""]

    # ── Code Smells ─────────────────────────────────────────────────────────
    smells = report.get("code_smells", [])
    lines += [f"## 🌿 Code Smells ({len(smells)} found)", ""]
    if smells:
        for i, s in enumerate(smells, 1):
            sev   = s.get("severity", "UNKNOWN")
            badge = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(sev, "⚪")
            lines += [
                f"### {i}. {badge} [{sev}] {s.get('title', 'Untitled')}",
                "",
                f"**Description:** {s.get('description', '')}",
                "",
                f"**Affected Code:** `{s.get('affected_code', 'N/A')}`",
                "",
                f"**Suggestion:** {s.get('suggestion', '')}",
                "",
            ]
    else:
        lines += ["_No code smells detected._", ""]

    lines += ["---", ""]

    # ── Improvements ────────────────────────────────────────────────────────
    improvements = report.get("improvements", [])
    lines += [f"## 💡 Improvement Opportunities ({len(improvements)} found)", ""]
    if improvements:
        for i, imp in enumerate(improvements, 1):
            pri   = imp.get("priority", "UNKNOWN")
            badge = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(pri, "⚪")
            lines += [
                f"### {i}. {badge} [{pri}] {imp.get('title', 'Untitled')}",
                "",
                f"**Description:** {imp.get('description', '')}",
                "",
                f"**Suggestion:** {imp.get('suggestion', '')}",
                "",
            ]
    else:
        lines += ["_No improvements suggested._", ""]

    lines += ["---", ""]

    # ── Metadata footer ─────────────────────────────────────────────────────
    func_count = len(function_tree.get("functions", {}))
    libs       = _extract_imports(function_tree)
    lines += [
        "## 📊 Project Metadata",
        "",
        f"| Key | Value |",
        f"|-----|-------|",
        f"| Total Functions Analysed | {func_count} |",
        f"| Libraries Detected | {', '.join(libs) if libs else 'none'} |",
        f"| Syntax Errors | {len(function_tree.get('syntax_errors', []))} |",
        f"| Overall Score | {score}/100 |",
        "",
        "_Report produced by CodeAtlas._",
    ]

    return "\n".join(lines)
