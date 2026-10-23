"""
overview_module.py
==================
Central data structure builder for CodeAtlas.

Responsibilities:
- Accepts the output of parser_module.parse_project()
- Calls Google Gemini to generate plain-language summaries for every node
  (FILE, BLOCK, LOGICAL_BLOCK, FUNCTION)
- Builds and returns a FunctionTree dict that is the single source of truth
  for the rest of the CodeAtlas backend
- Degrades gracefully when the Gemini API is unavailable

Environment variables (loaded from .env):
    GEMINI_API_KEY  – required for LLM summaries
    GEMINI_MODEL    – optional, defaults to "gemini-1.5-flash"
"""

from __future__ import annotations

import logging
import os
import time
import textwrap
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

_GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
_FUNCTION_BATCH_SIZE: int = 5           # smaller batches → fewer 503s
_INTER_BATCH_DELAY_SECONDS: float = 0.3 # reduced delay with flash-lite
_MAX_RETRIES: int = 3                   # retries on 503 / transient errors
_RETRY_BASE_DELAY: float = 2.0          # exponential backoff base (seconds)

# ---------------------------------------------------------------------------
# Gemini client initialisation (uses key_manager for rotation)
# ---------------------------------------------------------------------------

def _init_gemini() -> tuple[object | None, str | None]:
    """
    Check that at least one Gemini key is available via key_manager.

    Returns:
        (sentinel, None)     – on success (sentinel is just True)
        (None, error_msg)    – if no API keys available
    """
    try:
        client = key_manager.get_client()
        logger.info("Gemini key_manager ready with model '%s'.", _GEMINI_MODEL)
        return client, None
    except Exception as exc:  # noqa: BLE001
        msg = f"Failed to initialise Gemini via key_manager: {exc}"
        logger.error(msg)
        return None, msg


# ---------------------------------------------------------------------------
# Summary generation helpers
# ---------------------------------------------------------------------------

def generate_summary(
    text: str,
    context: str,
    model: Any = None,   # kept for API compat; ignored — key_manager handles client
) -> str | None:
    """
    Ask Gemini to produce a concise 2-4 sentence plain-language summary.

    Args:
        text:    The source code / snippet to summarise.
        context: Extra context string (e.g. file path, function name, node type)
                 that helps the model produce a better summary.
        model:   Ignored — key_manager selects the active client automatically.

    Returns:
        A summary string, or None if the model is unavailable or fails.
    """
    prompt = textwrap.dedent(f"""
        You are a senior software engineer reviewing a codebase.
        Provide a concise plain-language summary of the following code in
        2 to 4 sentences. Focus on *what* it does and *why* it exists.
        Do NOT include code in your response.

        Context: {context}

        Code:
        ```
        {text[:4000]}
        ```

        Summary:
    """).strip()

    try:
        response = key_manager.generate_content(_GEMINI_MODEL, prompt)
        summary = response.text.strip()
        return summary if summary else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("generate_summary failed for context '%s': %s", context, exc)
        return None


def _generate_summary_with_retry(text: str, context: str, model: Any = None) -> str | None:
    """Wrapper with exponential-backoff retry on transient 503 / UNAVAILABLE errors."""
    for attempt in range(_MAX_RETRIES):
        result = generate_summary(text, context)
        if result is not None:
            return result
        if attempt < _MAX_RETRIES - 1:
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            logger.info("Retrying summary for '%s' in %.1fs (attempt %d/%d)…",
                        context, delay, attempt + 1, _MAX_RETRIES)
            time.sleep(delay)
    return None


def _summarise_batch(
    items: list[tuple[str, str, str]],
    model: Any = None,
    progress_cb: Callable[[int], None] | None = None,
) -> dict[str, str | None]:
    """
    Summarise a small batch of (item_id, snippet, context) tuples with retry.
    Calls progress_cb(1) after each item if provided.
    """
    results: dict[str, str | None] = {}
    for idx, (item_id, snippet, context) in enumerate(items):
        summary = _generate_summary_with_retry(snippet, context)
        results[item_id] = summary
        if progress_cb:
            progress_cb(1)
        if idx < len(items) - 1:
            time.sleep(_INTER_BATCH_DELAY_SECONDS)
    return results


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

    Args:
        parsed:     The dict returned by ``parser_module.parse_project()``.
        session_id: Unique session identifier (e.g. UUID from the upload endpoint).

    Returns:
        A FunctionTree dict with the schema documented at the top of this module.
    """
    model, llm_error = _init_gemini()
    llm_available: bool = model is not None

    # ------------------------------------------------------------------
    # Skeleton tree
    # ------------------------------------------------------------------
    tree: dict[str, Any] = {
        "session_id": session_id,
        "files": {},
        "all_functions": {},
        "call_graph": {},
        "entry_points": [],
        "syntax_errors": parsed.get("syntax_errors", {}),
        "llm_available": llm_available,
        "llm_error": llm_error,
    }

    parsed_files: dict = parsed.get("files", {})

    # ------------------------------------------------------------------
    # Normalise parser output: blocks/functions/logical_blocks may be
    # returned as lists (with block_id / func_id keys) OR already as
    # dicts keyed by id.  Normalise to dict form here so the rest of
    # the function can always call .items().
    # ------------------------------------------------------------------
    def _to_dict_by_id(items: list | dict, id_key: str) -> dict:
        if isinstance(items, dict):
            return items
        return {item[id_key]: item for item in items if id_key in item}

    # ------------------------------------------------------------------
    # Process each file sequentially (rate-limit friendliness)
    # ------------------------------------------------------------------
    for filepath, file_data in parsed_files.items():
        logger.info("Processing file: %s", filepath)

        file_source: str = file_data.get("source", "")
        file_imports: list = file_data.get("imports", [])
        is_entry: bool = file_data.get("entry_point", False)

        # ---- FILE-level summary --------------------------------------
        file_summary: str | None = None
        if llm_available:
            file_summary = generate_summary(
                text=file_source,
                context=f"File: {filepath}",
            )
            time.sleep(_INTER_BATCH_DELAY_SECONDS)

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

        # ---- BLOCKs --------------------------------------------------
        for block_id, block_data in _to_dict_by_id(file_data.get("blocks", {}), "block_id").items():
            snippet: str = block_data.get("source_snippet", "")
            name: str = block_data.get("name", block_id)
            block_summary: str | None = None
            if llm_available and snippet:
                block_summary = generate_summary(
                    text=snippet,
                    context=f"Block '{name}' in {filepath}",
                )
                time.sleep(_INTER_BATCH_DELAY_SECONDS)

            file_node["blocks"][block_id] = {
                "level": "BLOCK",
                "summary": block_summary,
                "source_snippet": snippet,
                "name": name,
                "lineno": block_data.get("lineno", 0),
                "end_lineno": block_data.get("end_lineno", 0),
            }

        # ---- LOGICAL_BLOCKs ------------------------------------------
        for lb_id, lb_data in _to_dict_by_id(file_data.get("logical_blocks", {}), "block_id").items():
            snippet = lb_data.get("source_snippet", "")
            lb_type: str = lb_data.get("type", "unknown")
            lb_summary: str | None = None
            if llm_available and snippet:
                lb_summary = generate_summary(
                    text=snippet,
                    context=f"Logical block ({lb_type}) in {filepath}",
                )
                time.sleep(_INTER_BATCH_DELAY_SECONDS)

            file_node["logical_blocks"][lb_id] = {
                "level": "LOGICAL_BLOCK",
                "summary": lb_summary,
                "source_snippet": snippet,
                "type": lb_type,
                "lineno": lb_data.get("lineno", 0),
                "end_lineno": lb_data.get("end_lineno", 0),
            }

        # ---- FUNCTIONs (batched in groups of _FUNCTION_BATCH_SIZE) ---
        raw_functions: dict = _to_dict_by_id(file_data.get("functions", {}), "func_id")
        func_ids = list(raw_functions.keys())

        for batch_start in range(0, len(func_ids), _FUNCTION_BATCH_SIZE):
            batch_ids = func_ids[batch_start : batch_start + _FUNCTION_BATCH_SIZE]
            batch_items: list[tuple[str, str, str]] = []

            for fid in batch_ids:
                fdata = raw_functions[fid]
                fsnippet = fdata.get("source_snippet", "")
                fname = fdata.get("name", fid)
                fclass = fdata.get("class_ctx", "")
                ctx_parts = [f"Function '{fname}'", f"in {filepath}"]
                if fclass:
                    ctx_parts.insert(1, f"(class {fclass})")
                batch_items.append((fid, fsnippet, " ".join(ctx_parts)))

            summaries: dict[str, str | None] = {}
            if llm_available:
                summaries = _summarise_batch(batch_items)

            for fid in batch_ids:
                fdata = raw_functions[fid]
                callers: list = fdata.get("callers", [])
                callees: list = fdata.get("callees", [])

                func_node: dict[str, Any] = {
                    "level": "FUNCTION",
                    "summary": summaries.get(fid),
                    "source_snippet": fdata.get("source_snippet", ""),
                    "name": fdata.get("name", fid),
                    "lineno": fdata.get("lineno", 0),
                    "end_lineno": fdata.get("end_lineno", 0),
                    "class_ctx": fdata.get("class_ctx", ""),
                    "callers": callers,
                    "callees": callees,
                    "docstring": fdata.get("docstring", ""),
                }

                file_node["functions"][fid] = func_node
                tree["all_functions"][fid] = func_node

                # Build call graph entry
                if callees:
                    tree["call_graph"][fid] = callees

        # Register file node
        tree["files"][filepath] = file_node

        if is_entry:
            tree["entry_points"].append(filepath)

    logger.info(
        "FunctionTree built: %d files, %d functions, llm_available=%s",
        len(tree["files"]),
        len(tree["all_functions"]),
        llm_available,
    )
    return tree


# ---------------------------------------------------------------------------
# Retry failed summaries
# ---------------------------------------------------------------------------

def retry_summarization(function_tree: dict) -> dict:
    """
    Re-attempt AI summarisation for every node whose summary is None.

    Useful when the initial build_function_tree() call ran with
    ``llm_available=False`` or encountered transient API errors.

    Args:
        function_tree: A FunctionTree dict (possibly from a previous call).

    Returns:
        The same dict mutated in place with newly populated summaries.
        ``llm_available`` and ``llm_error`` are updated to reflect the
        outcome of the retry attempt.
    """
    model, llm_error = _init_gemini()
    if model is None:
        function_tree["llm_available"] = False
        function_tree["llm_error"] = llm_error
        logger.warning("retry_summarization: Gemini still unavailable – %s", llm_error)
        return function_tree

    function_tree["llm_available"] = True
    function_tree["llm_error"] = None

    for filepath, file_node in function_tree.get("files", {}).items():

        # FILE
        if file_node.get("summary") is None:
            file_node["summary"] = generate_summary(
                text=file_node.get("source", ""),
                context=f"File: {filepath}",
                model=model,
            )
            time.sleep(_INTER_BATCH_DELAY_SECONDS)

        # BLOCKs
        for block_id, block_node in file_node.get("blocks", {}).items():
            if block_node.get("summary") is None:
                block_node["summary"] = generate_summary(
                    text=block_node.get("source_snippet", ""),
                    context=f"Block '{block_node.get('name', block_id)}' in {filepath}",
                    model=model,
                )
                time.sleep(_INTER_BATCH_DELAY_SECONDS)

        # LOGICAL_BLOCKs
        for lb_id, lb_node in file_node.get("logical_blocks", {}).items():
            if lb_node.get("summary") is None:
                lb_node["summary"] = generate_summary(
                    text=lb_node.get("source_snippet", ""),
                    context=f"Logical block ({lb_node.get('type', 'unknown')}) in {filepath}",
                    model=model,
                )
                time.sleep(_INTER_BATCH_DELAY_SECONDS)

        # FUNCTIONs (batched)
        funcs_needing_summary = [
            fid
            for fid, fnode in file_node.get("functions", {}).items()
            if fnode.get("summary") is None
        ]

        for batch_start in range(0, len(funcs_needing_summary), _FUNCTION_BATCH_SIZE):
            batch_ids = funcs_needing_summary[batch_start : batch_start + _FUNCTION_BATCH_SIZE]
            batch_items: list[tuple[str, str, str]] = []

            for fid in batch_ids:
                fnode = file_node["functions"][fid]
                fname = fnode.get("name", fid)
                fclass = fnode.get("class_ctx", "")
                ctx_parts = [f"Function '{fname}'", f"in {filepath}"]
                if fclass:
                    ctx_parts.insert(1, f"(class {fclass})")
                batch_items.append((fid, fnode.get("source_snippet", ""), " ".join(ctx_parts)))

            summaries = _summarise_batch(batch_items, model)

            for fid, summary in summaries.items():
                file_node["functions"][fid]["summary"] = summary
                # Keep all_functions in sync
                if fid in function_tree.get("all_functions", {}):
                    function_tree["all_functions"][fid]["summary"] = summary

    logger.info("retry_summarization complete.")
    return function_tree


# ---------------------------------------------------------------------------
# Node lookup
# ---------------------------------------------------------------------------

def get_node_by_id(function_tree: dict, node_id: str) -> dict | None:
    """
    Look up any node in the FunctionTree by its ID.

    Search order:
      1. ``all_functions``  – direct O(1) lookup for FUNCTION nodes
      2. ``files``          – the filepath itself is used as the FILE node ID
      3. Per-file blocks and logical_blocks

    Args:
        function_tree: A FunctionTree dict built by :func:`build_function_tree`.
        node_id:       The node identifier to search for.

    Returns:
        The node dict if found, otherwise ``None``.
    """
    if not isinstance(function_tree, dict):
        return None

    # 1. FUNCTION nodes (fastest path)
    all_functions: dict = function_tree.get("all_functions", {})
    if node_id in all_functions:
        return all_functions[node_id]

    # 2. FILE nodes – the filepath is the node ID
    files: dict = function_tree.get("files", {})
    if node_id in files:
        return files[node_id]

    # 3. BLOCK and LOGICAL_BLOCK nodes (scan per-file dicts)
    for file_node in files.values():
        if node_id in file_node.get("blocks", {}):
            return file_node["blocks"][node_id]
        if node_id in file_node.get("logical_blocks", {}):
            return file_node["logical_blocks"][node_id]

    return None
