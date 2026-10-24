"""
overview_module.py
==================
Central data structure builder for CodeAtlas.

Responsibilities:
- Accepts the output of parser_module.parse_project()
- Generates plain-language summaries for all 4 hierarchical levels:
    * FILE (File-wise overview)
    * BLOCK (Classes and module-level blocks)
    * LOGICAL_BLOCK (Loops, conditionals, exception handling)
    * FUNCTION (Individual functions and methods)
- High-efficiency architecture:
    * Batches summarization per file (1 API call per file instead of dozens),
      drastically reducing API calls by ~90% and maximizing speed & accuracy.
    * Logical blocks are analyzed with high-precision AST semantics instantly.
    * Full resilience with automatic API key rotation and model cascading via key_manager.
    * Graceful degradation when the LLM API is unavailable.
"""

from __future__ import annotations

import json
import logging
import os
import re
import textwrap
import time
from typing import Any, Callable

from dotenv import load_dotenv
import key_manager

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv()

_GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
_INTER_FILE_DELAY_SECONDS: float = float(os.getenv("AI_DELAY_BETWEEN_CALLS", "0.15"))
_BATCH_PER_FILE: bool = os.getenv("AI_BATCH_SUMMARIZE_PER_FILE", "true").lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Helpers for JSON extraction
# ---------------------------------------------------------------------------

def _clean_and_parse_json(raw_text: str) -> dict:
    """Extract and parse the JSON payload from the LLM output."""
    cleaned = raw_text.strip()
    # Strip markdown code blocks if wrapped
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback regex search for { ... }
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {}


# ---------------------------------------------------------------------------
# High-precision AST logical block descriptor (0 API calls, instant & accurate)
# ---------------------------------------------------------------------------

def _describe_logical_block(lb_type: str, lineno: int, snippet: str) -> str:
    """Generate a concise, accurate semantic description of an AST logical block."""
    t = (lb_type or "block").upper()
    first_line = snippet.strip().split("\n")[0].strip() if snippet else ""

    if t == "IF":
        cond = first_line.replace("if ", "").rstrip(":")
        return f"Conditional check: evaluates `{cond}` (line {lineno})"
    elif t == "ELIF":
        cond = first_line.replace("elif ", "").rstrip(":")
        return f"Alternative branch: evaluates `{cond}` (line {lineno})"
    elif t == "ELSE":
        return f"Fallback branch executing when preceding conditions are false (line {lineno})"
    elif t in ("FOR", "WHILE"):
        loop = first_line.rstrip(":")
        return f"Loop iteration: executes `{loop}` (line {lineno})"
    elif t == "TRY":
        return f"Exception-handling block: protects statements starting at line {lineno}"
    elif t == "EXCEPT":
        exc = first_line.replace("except ", "").rstrip(":") or "Exception"
        return f"Exception handler: catches and handles `{exc}` (line {lineno})"
    elif t == "FINALLY":
        return f"Cleanup block: guaranteed to execute after try/except (line {lineno})"
    elif t == "WITH":
        ctx = first_line.replace("with ", "").rstrip(":")
        return f"Context manager: manages lifecycle of `{ctx}` (line {lineno})"

    return f"Logical control block ({t}) at line {lineno}"


# ---------------------------------------------------------------------------
# File-level batch summarization (1 call per file)
# ---------------------------------------------------------------------------

def _summarize_file_batch(
    filepath: str,
    source: str,
    class_names: list[str],
    function_names: list[str],
) -> dict:
    """
    Summarize a file and all its classes and functions in a single API call.

    Returns dict with keys: 'file_summary', 'blocks', 'functions'.
    """
    classes_str = ", ".join(f"`{c}`" for c in class_names) if class_names else "none"
    functions_str = ", ".join(f"`{fn}`" for fn in function_names) if function_names else "none"

    prompt = textwrap.dedent(f"""
        You are an expert Python software architect analyzing the file `{filepath}`.
        Return ONLY a valid JSON object (no markdown formatting, no code fences, no extra text) with this EXACT structure:
        {{
          "file_summary": "A 2 to 3 sentence concise summary of what this file does, its core responsibility, and how it fits into the project.",
          "blocks": {{
            <for each class in {classes_str}: "<class_name>": "A 1 to 2 sentence summary of this class's role and state">
          }},
          "functions": {{
            <for each function in {functions_str}: "<function_name>": "A 1 to 2 sentence summary of what this function does, its parameters, and what it returns">
          }}
        }}

        File: {filepath}
        Source code:
        ```python
        {source[:10000]}
        ```
    """).strip()

    try:
        resp = key_manager.generate_content(_GEMINI_MODEL, prompt)
        return _clean_and_parse_json(resp.text)
    except Exception as exc:
        logger.warning("Batch summarization failed for '%s': %s", filepath, exc)
        return {}


# ---------------------------------------------------------------------------
# Single-item summary fallback
# ---------------------------------------------------------------------------

def generate_summary(text: str, context: str, model: Any = None) -> str | None:
    """Fallback single-item summarizer."""
    prompt = textwrap.dedent(f"""
        Provide a concise plain-language summary of the following Python code in
        2 to 3 sentences. Focus on what it does and why it exists.
        Do NOT include code or markdown fences in your response.

        Context: {context}

        Code:
        ```
        {text[:4000]}
        ```
    """).strip()

    try:
        response = key_manager.generate_content(_GEMINI_MODEL, prompt)
        summary = response.text.strip()
        return summary if summary else None
    except Exception as exc:
        logger.warning("generate_summary failed for '%s': %s", context, exc)
        return None


# ---------------------------------------------------------------------------
# FunctionTree builder
# ---------------------------------------------------------------------------

def build_function_tree(
    parsed: dict,
    session_id: str,
    progress_cb: Callable[[str, int, int], None] | None = None,
) -> dict:
    """
    Build the canonical FunctionTree from parser_module output.

    Uses file-level batch summarization to minimize API calls while maximizing
    context awareness and speed.
    """
    try:
        key_manager.get_client()
        llm_available = True
        llm_error = None
    except Exception as exc:
        llm_available = False
        llm_error = str(exc)

    tree: dict[str, Any] = {
        "session_id": session_id,
        "files": {},
        "all_functions": {},
        "functions": {},  # backwards-compat alias
        "call_graph": dict(parsed.get("call_graph", {})),
        "entry_points": list(parsed.get("entry_points", [])),
        "syntax_errors": parsed.get("syntax_errors", {}),
        "llm_available": llm_available,
        "llm_error": llm_error,
    }

    parsed_files: dict = parsed.get("files", {})

    def _to_dict_by_id(items: list | dict, id_key: str) -> dict:
        if isinstance(items, dict):
            return items
        return {item[id_key]: item for item in items if id_key in item}

    total_files = len(parsed_files)

    for file_idx, (filepath, file_data) in enumerate(parsed_files.items(), 1):
        logger.info("[%d/%d] Processing file: %s", file_idx, total_files, filepath)

        file_source: str = file_data.get("source", "")
        file_imports: list = file_data.get("imports", [])
        is_entry: bool = file_data.get("entry_point", False)

        blocks_dict = _to_dict_by_id(file_data.get("blocks", {}), "block_id")
        functions_dict = _to_dict_by_id(file_data.get("functions", {}), "func_id")
        logical_blocks_dict = _to_dict_by_id(file_data.get("logical_blocks", {}), "block_id")

        class_names = [b.get("name", bid) for bid, b in blocks_dict.items()]
        func_names = [f.get("name", fid) for fid, f in functions_dict.items()]

        # ── Step 1: Batch LLM call for the entire file (1 call) ─────────────
        batch_results: dict = {}
        if llm_available and _BATCH_PER_FILE:
            batch_results = _summarize_file_batch(
                filepath=filepath,
                source=file_source,
                class_names=class_names,
                function_names=func_names,
            )
            time.sleep(_INTER_FILE_DELAY_SECONDS)

        # ── Step 2: FILE node ───────────────────────────────────────────────
        file_summary = batch_results.get("file_summary")
        if not file_summary and llm_available and not _BATCH_PER_FILE:
            file_summary = generate_summary(file_source, f"File: {filepath}")

        # Fallback file summary if LLM failed
        if not file_summary:
            doc = file_data.get("docstring")
            if doc:
                file_summary = doc.strip().split("\n")[0]
            else:
                file_summary = f"Python source file containing {len(functions_dict)} functions and {len(blocks_dict)} classes/blocks."

        file_node: dict[str, Any] = {
            "level": "FILE",
            "summary": file_summary,
            "source": file_source,
            "entry_point": is_entry,
            "imports": file_imports,
            "blocks": {},
            "functions": {},
            "logical_blocks": {},
        }

        # ── Step 3: BLOCK nodes ─────────────────────────────────────────────
        llm_blocks = batch_results.get("blocks", {})
        for block_id, block_data in blocks_dict.items():
            bname = block_data.get("name", block_id)
            bsummary = llm_blocks.get(bname) or llm_blocks.get(block_id)
            if not bsummary and block_data.get("docstring"):
                bsummary = block_data["docstring"].strip().split("\n")[0]
            if not bsummary:
                bsummary = f"Class `{bname}` encapsulating related attributes and methods."

            file_node["blocks"][block_id] = {
                "level": "BLOCK",
                "summary": bsummary,
                "source_snippet": block_data.get("source_snippet", ""),
                "name": bname,
                "lineno": block_data.get("lineno", 0),
                "end_lineno": block_data.get("end_lineno", 0),
            }

        # ── Step 4: LOGICAL_BLOCK nodes (high-precision AST descriptions) ───
        for lb_id, lb_data in logical_blocks_dict.items():
            snippet = lb_data.get("source_snippet", "")
            lb_type = lb_data.get("type", "unknown")
            lineno = lb_data.get("lineno", 0)

            # High-precision semantic description without burning API calls
            lb_summary = _describe_logical_block(lb_type, lineno, snippet)

            file_node["logical_blocks"][lb_id] = {
                "level": "LOGICAL_BLOCK",
                "summary": lb_summary,
                "source_snippet": snippet,
                "type": lb_type,
                "lineno": lineno,
                "end_lineno": lb_data.get("end_lineno", 0),
            }

        # ── Step 5: FUNCTION nodes ──────────────────────────────────────────
        llm_funcs = batch_results.get("functions", {})
        for fid, fdata in functions_dict.items():
            fname = fdata.get("name", fid)
            fsummary = llm_funcs.get(fname) or llm_funcs.get(fid)

            # Fallback to function docstring if present
            if not fsummary and fdata.get("docstring"):
                fsummary = fdata["docstring"].strip().split("\n")[0]
            if not fsummary:
                cls_ctx = f" (in class {fdata['class_ctx']})" if fdata.get("class_ctx") else ""
                fsummary = f"Function `{fname}`{cls_ctx} defined at line {fdata.get('lineno', 0)}."

            callers = fdata.get("callers", [])
            callees = fdata.get("callees", [])

            func_node: dict[str, Any] = {
                "level": "FUNCTION",
                "summary": fsummary,
                "source_snippet": fdata.get("source_snippet", ""),
                "name": fname,
                "lineno": fdata.get("lineno", 0),
                "end_lineno": fdata.get("end_lineno", 0),
                "class_ctx": fdata.get("class_ctx", ""),
                "callers": callers,
                "callees": callees,
                "docstring": fdata.get("docstring", ""),
                "file": filepath,
            }

            file_node["functions"][fid] = func_node
            tree["all_functions"][fid] = func_node
            tree["functions"][fid] = func_node  # backwards compatibility

            if callees:
                tree["call_graph"][fid] = callees

        # Register file node
        tree["files"][filepath] = file_node
        if is_entry:
            tree["entry_points"].append(filepath)

    logger.info(
        "FunctionTree built: %d files, %d functions, %d call-graph entries. (llm_available=%s)",
        len(tree["files"]),
        len(tree["all_functions"]),
        len(tree["call_graph"]),
        llm_available,
    )
    return tree


# ---------------------------------------------------------------------------
# Retry failed summaries
# ---------------------------------------------------------------------------

def retry_summarization(function_tree: dict) -> dict:
    """
    Re-attempt AI summarisation for any nodes that have default/missing summaries.
    Uses efficient batch-per-file summarization.
    """
    try:
        key_manager.get_client()
        function_tree["llm_available"] = True
        function_tree["llm_error"] = None
    except Exception as exc:
        function_tree["llm_available"] = False
        function_tree["llm_error"] = str(exc)
        return function_tree

    for filepath, file_node in function_tree.get("files", {}).items():
        source = file_node.get("source", "")
        blocks = file_node.get("blocks", {})
        functions = file_node.get("functions", {})

        class_names = [b.get("name", bid) for bid, b in blocks.items()]
        func_names = [f.get("name", fid) for fid, f in functions.items()]

        batch_results = _summarize_file_batch(filepath, source, class_names, func_names)
        time.sleep(_INTER_FILE_DELAY_SECONDS)

        if batch_results.get("file_summary"):
            file_node["summary"] = batch_results["file_summary"]

        llm_blocks = batch_results.get("blocks", {})
        for bid, bnode in blocks.items():
            bname = bnode.get("name", bid)
            if bname in llm_blocks:
                bnode["summary"] = llm_blocks[bname]

        llm_funcs = batch_results.get("functions", {})
        for fid, fnode in functions.items():
            fname = fnode.get("name", fid)
            if fname in llm_funcs:
                fnode["summary"] = llm_funcs[fname]
                if fid in function_tree.get("all_functions", {}):
                    function_tree["all_functions"][fid]["summary"] = llm_funcs[fname]

    logger.info("retry_summarization complete.")
    return function_tree


# ---------------------------------------------------------------------------
# Node lookup
# ---------------------------------------------------------------------------

def get_node_by_id(function_tree: dict, node_id: str) -> dict | None:
    """Look up any node in the FunctionTree by its ID."""
    if not isinstance(function_tree, dict):
        return None

    all_functions: dict = function_tree.get("all_functions", {})
    if node_id in all_functions:
        return all_functions[node_id]

    files: dict = function_tree.get("files", {})
    if node_id in files:
        return files[node_id]

    for file_node in files.values():
        if node_id in file_node.get("blocks", {}):
            return file_node["blocks"][node_id]
        if node_id in file_node.get("logical_blocks", {}):
            return file_node["logical_blocks"][node_id]

    return None
