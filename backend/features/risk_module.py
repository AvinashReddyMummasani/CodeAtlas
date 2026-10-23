"""
risk_module.py
==============
Function risk score & blast-radius analyser for CodeAtlas.

Uses NetworkX to traverse the call graph and Gemini to produce a
human-readable "blast radius narrative" for each function.
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


def _build_graph(function_tree: dict) -> nx.DiGraph:
    """
    Build a directed graph from function_tree["call_graph"].

    call_graph is expected to be either:
      - a dict mapping caller_id → list[callee_id]   (adjacency list)
      - a list of [caller_id, callee_id] edges
    """
    G = nx.DiGraph()

    call_graph = function_tree.get("call_graph", {})

    if isinstance(call_graph, dict):
        for caller, callees in call_graph.items():
            G.add_node(caller)
            for callee in (callees or []):
                G.add_edge(caller, callee)
    elif isinstance(call_graph, list):
        for edge in call_graph:
            if isinstance(edge, (list, tuple)) and len(edge) >= 2:
                G.add_edge(edge[0], edge[1])

    # Ensure every function in the tree is a node
    for func_id in function_tree.get("functions", {}):
        G.add_node(func_id)

    return G


def _compute_risk_score_values(dependent_count: int, file_spread: int) -> tuple[float, str]:
    """Return (risk_score, risk_tier)."""
    score = min(10.0, dependent_count * 1.5 + file_spread * 0.5)
    if score < 3:
        tier = "LOW"
    elif score <= 6:
        tier = "MEDIUM"
    else:
        tier = "HIGH"
    return round(score, 2), tier


def _blast_radius_narrative(
    func_name: str,
    risk_tier: str,
    risk_score: float,
    dependent_count: int,
    file_spread: int,
    affected_functions: list[dict],
    summary: str,
) -> str:
    """Ask Gemini for a brief blast-radius narrative paragraph."""
    affected_names = ", ".join(
        f["name"] for f in affected_functions[:15]
    ) or "none"

    prompt = textwrap.dedent(f"""
        You are a software architect describing the blast radius of a code change.
        Write a concise paragraph (3-5 sentences) explaining what happens if the
        function `{func_name}` is modified or broken.

        Facts:
        - One-sentence summary: {summary or '(not available)'}
        - Risk tier: {risk_tier}  |  Risk score: {risk_score}/10
        - Transitively dependent functions ({dependent_count} total): {affected_names}
        - Unique files affected: {file_spread}

        Use plain English. Be specific about downstream impact. No bullet points.
        Return ONLY the paragraph.
    """).strip()

    try:
        model    = _get_client()
        if not model:
            return "Blast radius narrative unavailable (LLM not configured)."
        response = key_manager.generate_content(_MODEL, prompt)
        return response.text.strip()
    except Exception as exc:
        return f"Blast radius narrative unavailable: {exc}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_risk_score(func_id: str, function_tree: dict) -> dict:
    """
    Compute risk score and blast radius for a single function.

    Parameters
    ----------
    func_id       : unique function identifier
    function_tree : parsed project representation

    Returns
    -------
    dict with keys: func_id, name, risk_score, risk_tier, dependent_count,
                    file_spread, affected_functions, affected_files,
                    blast_radius_narrative, partial_graph, error
    """
    functions = function_tree.get("functions", {})
    func      = functions.get(func_id)

    if func is None:
        return {
            "func_id":               func_id,
            "name":                  func_id,
            "risk_score":            0.0,
            "risk_tier":             "LOW",
            "dependent_count":       0,
            "file_spread":           0,
            "affected_functions":    [],
            "affected_files":        [],
            "blast_radius_narrative": "",
            "partial_graph":         bool(function_tree.get("syntax_errors")),
            "error":                 f"Function '{func_id}' not found in function_tree.",
        }

    name    = func.get("name", func_id)
    summary = func.get("summary", "")
    partial = bool(function_tree.get("syntax_errors"))

    # Build the call graph (caller → callee edges)
    G = _build_graph(function_tree)

    # We want functions that depend on func_id, i.e. callers (and their callers).
    # In the graph caller→callee, the *ancestors* of func_id are its callers.
    # Use the reversed graph descendants to find all transitive callers.
    try:
        # ancestors = all nodes from which func_id is reachable
        ancestors: set[str] = nx.ancestors(G, func_id)
    except nx.exception.NetworkXError:
        ancestors = set()

    # Build affected_functions list
    affected_functions: list[dict] = []
    affected_files: set[str] = set()

    for dep_id in ancestors:
        dep = functions.get(dep_id, {})
        dep_file = dep.get("file", "unknown")
        affected_files.add(dep_file)
        affected_functions.append(
            {
                "func_id": dep_id,
                "name":    dep.get("name", dep_id),
                "file":    dep_file,
                "summary": dep.get("summary", ""),
            }
        )

    dependent_count = len(affected_functions)
    file_spread     = len(affected_files)

    risk_score, risk_tier = _compute_risk_score_values(dependent_count, file_spread)

    narrative = _blast_radius_narrative(
        func_name=name,
        risk_tier=risk_tier,
        risk_score=risk_score,
        dependent_count=dependent_count,
        file_spread=file_spread,
        affected_functions=affected_functions,
        summary=summary,
    )

    return {
        "func_id":               func_id,
        "name":                  name,
        "risk_score":            risk_score,
        "risk_tier":             risk_tier,
        "dependent_count":       dependent_count,
        "file_spread":           file_spread,
        "affected_functions":    affected_functions,
        "affected_files":        sorted(affected_files),
        "blast_radius_narrative": narrative,
        "partial_graph":         partial,
        "error":                 None,
    }


def rank_file_by_risk(filepath: str, function_tree: dict) -> list[dict]:
    """
    Compute risk scores for all functions in *filepath* and return them
    sorted by risk_score descending (highest risk first).

    Parameters
    ----------
    filepath      : path to match against function entries
    function_tree : parsed project representation

    Returns
    -------
    list of result dicts (same shape as compute_risk_score)
    """
    norm_target = filepath.replace("\\", "/").lower()

    matching_ids = [
        fid
        for fid, fdata in function_tree.get("functions", {}).items()
        if fdata.get("file", "").replace("\\", "/").lower() == norm_target
    ]

    results: list[dict] = [compute_risk_score(fid, function_tree) for fid in matching_ids]
    results.sort(key=lambda r: r.get("risk_score", 0.0), reverse=True)
    return results
