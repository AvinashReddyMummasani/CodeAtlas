"""
flow_module.py
==============
Root-to-function execution flow tracer for CodeAtlas.

Uses NetworkX to enumerate all simple paths from each project entry point
to a target function, giving a complete picture of how execution can reach
any function in the codebase.
"""

from __future__ import annotations

from typing import Any

import networkx as nx


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MAX_PATHS       = 20   # cap on number of paths returned
_MAX_PATH_LENGTH = 50   # cap on path depth (edges) to avoid combinatorial explosion


def _build_graph(function_tree: dict) -> nx.DiGraph:
    """
    Build a directed graph from function_tree["call_graph"].

    Edges represent caller → callee relationships.
    call_graph may be:
      - dict:  { caller_id: [callee_id, ...], ... }
      - list:  [[caller_id, callee_id], ...]
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

    # Ensure all known functions are nodes (even isolated ones)
    for func_id in function_tree.get("functions", {}):
        G.add_node(func_id)

    return G


def _build_step(func_id: str, function_tree: dict) -> dict:
    """Build a single path-step dict for *func_id*."""
    func = function_tree.get("functions", {}).get(func_id, {})
    full_summary = func.get("summary", "")
    # Truncate summary to ≤120 chars for readability
    summary_short = (full_summary[:117] + "…") if len(full_summary) > 120 else full_summary

    return {
        "func_id":      func_id,
        "name":         func.get("name", func_id),
        "file":         func.get("file", "unknown"),
        "summary_short": summary_short,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_execution_paths(target_func_id: str, function_tree: dict) -> dict:
    """
    Trace all execution paths from project entry points to *target_func_id*.

    Parameters
    ----------
    target_func_id : the function whose call chains we want to discover
    function_tree  : parsed project representation containing:
                     - "call_graph"   : caller→callee adjacency
                     - "entry_points" : list of func_ids that are roots
                     - "functions"    : metadata per func_id

    Returns
    -------
    dict with keys:
        target_func_id  : str
        target_name     : str
        paths           : list of { path_id: int, steps: [step_dict] }
        total_paths     : int
        dead_code_hint  : bool  (True when no path found from any entry point)
        error           : None or str
    """
    functions = function_tree.get("functions", {})
    target    = functions.get(target_func_id, {})
    target_name = target.get("name", target_func_id)

    entry_points: list[str] = function_tree.get("entry_points", [])

    if not entry_points:
        return {
            "target_func_id": target_func_id,
            "target_name":    target_name,
            "paths":          [],
            "total_paths":    0,
            "dead_code_hint": True,
            "error":          "No entry points defined in function_tree.",
        }

    try:
        G = _build_graph(function_tree)
    except Exception as exc:
        return {
            "target_func_id": target_func_id,
            "target_name":    target_name,
            "paths":          [],
            "total_paths":    0,
            "dead_code_hint": True,
            "error":          f"Failed to build call graph: {exc}",
        }

    if target_func_id not in G:
        return {
            "target_func_id": target_func_id,
            "target_name":    target_name,
            "paths":          [],
            "total_paths":    0,
            "dead_code_hint": True,
            "error":          f"Target function '{target_func_id}' not present in call graph.",
        }

    collected_paths: list[list[str]] = []

    for entry in entry_points:
        if entry not in G:
            continue  # skip entry points absent from graph

        if entry == target_func_id:
            # The entry point IS the target — trivial single-step path
            collected_paths.append([entry])
            if len(collected_paths) >= _MAX_PATHS:
                break
            continue

        try:
            path_gen = nx.all_simple_paths(
                G,
                source=entry,
                target=target_func_id,
                cutoff=_MAX_PATH_LENGTH,
            )
            for path in path_gen:
                collected_paths.append(path)
                if len(collected_paths) >= _MAX_PATHS:
                    break
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass
        except Exception:
            # Swallow unexpected errors from a single entry point
            pass

        if len(collected_paths) >= _MAX_PATHS:
            break

    dead_code_hint = len(collected_paths) == 0

    # Build structured path objects
    paths_output: list[dict] = []
    for path_id, raw_path in enumerate(collected_paths, start=1):
        steps = [_build_step(node, function_tree) for node in raw_path]
        paths_output.append({"path_id": path_id, "steps": steps})

    return {
        "target_func_id": target_func_id,
        "target_name":    target_name,
        "paths":          paths_output,
        "total_paths":    len(paths_output),
        "dead_code_hint": dead_code_hint,
        "error":          None,
    }
