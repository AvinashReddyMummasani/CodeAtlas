"""
rag_module.py — Explorer RAG Chatbot module for CodeAtlas.

Public API
----------
build_vector_index(function_tree, session_id)  -> chromadb.Collection
query_rag(question, session_id, chat_history, function_tree, top_k) -> dict
get_or_build_index(function_tree, session_id)  -> chromadb.Collection
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import chromadb
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ---------------------------------------------------------------------------
# Configuration  (loaded from .env at the project root)
# ---------------------------------------------------------------------------
load_dotenv()

# ensure backend/ is on path so key_manager can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import key_manager

_GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
_EMBEDDING_MODEL: str = os.getenv(
    "GEMINI_EMBEDDING_MODEL", "models/text-embedding-004"
)
_CHROMA_DIR: str = os.getenv("CHROMA_DIR", "chroma_store")

_llm = True  # key_manager handles actual API calls

# ---------------------------------------------------------------------------
# ChromaDB client cache  {session_id -> chromadb.ClientAPI}
# ---------------------------------------------------------------------------
_chroma_clients: dict[str, chromadb.ClientAPI] = {}


def _get_chroma_client(session_id: str) -> chromadb.ClientAPI:
    """Return (and cache) a persistent ChromaDB client for *session_id*."""
    if session_id not in _chroma_clients:
        persist_path = str(Path(_CHROMA_DIR) / session_id)
        Path(persist_path).mkdir(parents=True, exist_ok=True)
        _chroma_clients[session_id] = chromadb.PersistentClient(path=persist_path)
        logger.info("ChromaDB client created at '%s'.", persist_path)
    return _chroma_clients[session_id]


def _collection_name(session_id: str) -> str:
    # ChromaDB collection names must be 3-63 chars, alphanumeric + hyphens,
    # start/end with alphanumeric.  Sanitise the session_id just in case.
    safe = re.sub(r"[^a-zA-Z0-9-]", "-", session_id)[:40]
    return f"codeatlas-{safe}"


# ---------------------------------------------------------------------------
# Document builder helpers
# ---------------------------------------------------------------------------

def _iter_indexable_nodes(function_tree: dict):
    """
    Yield (node_id, name, file, level, lineno, summary, source_snippet)
    for every FUNCTION and BLOCK node in the function_tree.
    """
    files: dict = function_tree.get("files", {})
    for filepath, file_node in files.items():
        # FUNCTION nodes
        for func_id, fnode in file_node.get("functions", {}).items():
            yield (
                func_id,
                fnode.get("name", func_id),
                filepath,
                fnode.get("level", "function"),
                fnode.get("lineno", 0),
                fnode.get("summary", ""),
                fnode.get("source_snippet", ""),
            )
        # BLOCK nodes (classes, module-level blocks)
        for block_id, bnode in file_node.get("blocks", {}).items():
            yield (
                block_id,
                bnode.get("name", block_id),
                filepath,
                bnode.get("level", "block"),
                bnode.get("lineno", 0),
                bnode.get("summary", ""),
                bnode.get("source_snippet", ""),
            )
        # LOGICAL_BLOCK nodes
        for lb_id, lbnode in file_node.get("logical_blocks", {}).items():
            yield (
                lb_id,
                lbnode.get("name", lb_id),
                filepath,
                lbnode.get("level", "logical_block"),
                lbnode.get("lineno", 0),
                lbnode.get("summary", ""),
                lbnode.get("source_snippet", ""),
            )


def _make_document(name: str, filepath: str, summary: str, source_snippet: str) -> str:
    """Compose the text document that will be embedded and stored."""
    return (
        f"Function: {name}\n"
        f"File: {filepath}\n"
        f"Summary: {summary or 'N/A'}\n\n"
        f"Code:\n{source_snippet or ''}"
    )


def _embed_text(text: str, task_type: str = "retrieval_document") -> list[float] | None:
    """
    Generate an embedding vector via google.genai Client.
    Returns None if the API key is missing or the call fails.
    """
    try:
        response = key_manager.embed_content(
            model=_EMBEDDING_MODEL,
            contents=text,
            config={"task_type": task_type},
        )
        # New SDK returns EmbedContentResponse with .embeddings list
        return response.embeddings[0].values
    except Exception as exc:  # noqa: BLE001
        logger.warning("Embedding failed (%s): %s", task_type, exc)
        return None


# ---------------------------------------------------------------------------
# Public: build_vector_index
# ---------------------------------------------------------------------------

_UPSERT_BATCH_SIZE = 50  # ChromaDB performs best with moderate batch sizes


def build_vector_index(
    function_tree: dict,
    session_id: str,
) -> chromadb.Collection:
    """
    Build (or rebuild) the ChromaDB vector index for *session_id*.

    Iterates every FUNCTION and BLOCK node in *function_tree*, generates an
    embedding for each, and upserts them into a named collection.

    Parameters
    ----------
    function_tree : dict
        The FunctionTree produced by overview_module.build_function_tree().
    session_id : str
        Unique session identifier — used to namespace the ChromaDB collection.

    Returns
    -------
    chromadb.Collection
        The populated collection.
    """
    client = _get_chroma_client(session_id)
    col_name = _collection_name(session_id)

    # Delete the old collection if it exists so we always get a clean slate.
    try:
        client.delete_collection(col_name)
        logger.info("Existing ChromaDB collection '%s' deleted for rebuild.", col_name)
    except Exception:  # collection may not exist yet — that's fine
        pass

    collection = client.create_collection(
        name=col_name,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info("ChromaDB collection '%s' created.", col_name)

    # Accumulate batches
    batch_ids: list[str] = []
    batch_docs: list[str] = []
    batch_embeddings: list[list[float]] = []
    batch_metas: list[dict] = []

    fallback_mode = not bool(_GEMINI_API_KEY)  # embed as text only when no key

    total_indexed = 0

    for node_id, name, filepath, level, lineno, summary, snippet in _iter_indexable_nodes(
        function_tree
    ):
        doc_text = _make_document(name, filepath, summary, snippet)

        if not fallback_mode:
            embedding = _embed_text(doc_text, task_type="retrieval_document")
            if embedding is None:
                # Skip nodes we cannot embed rather than polluting the index.
                logger.warning("Skipping node '%s' — embedding returned None.", node_id)
                continue
            batch_embeddings.append(embedding)

        batch_ids.append(node_id)
        batch_docs.append(doc_text)
        batch_metas.append(
            {
                "func_id": node_id,
                "name": name,
                "file": filepath,
                "level": str(level),
                "lineno": int(lineno) if lineno else 0,
            }
        )

        # Flush a batch when it reaches the batch size limit
        if len(batch_ids) >= _UPSERT_BATCH_SIZE:
            _upsert_batch(collection, batch_ids, batch_docs, batch_embeddings, batch_metas, fallback_mode)
            total_indexed += len(batch_ids)
            batch_ids, batch_docs, batch_embeddings, batch_metas = [], [], [], []

    # Flush remaining items
    if batch_ids:
        _upsert_batch(collection, batch_ids, batch_docs, batch_embeddings, batch_metas, fallback_mode)
        total_indexed += len(batch_ids)

    logger.info(
        "Vector index built for session '%s': %d nodes indexed.", session_id, total_indexed
    )
    return collection


def _upsert_batch(
    collection: chromadb.Collection,
    ids: list[str],
    docs: list[str],
    embeddings: list[list[float]],
    metas: list[dict],
    fallback_mode: bool,
) -> None:
    """Upsert a batch into ChromaDB, with or without pre-computed embeddings."""
    if fallback_mode or not embeddings:
        # Let ChromaDB use its default embedding function (sentence-transformers)
        collection.upsert(ids=ids, documents=docs, metadatas=metas)
    else:
        collection.upsert(
            ids=ids,
            documents=docs,
            embeddings=embeddings,
            metadatas=metas,
        )


# ---------------------------------------------------------------------------
# Public: get_or_build_index
# ---------------------------------------------------------------------------

def get_or_build_index(
    function_tree: dict,
    session_id: str,
) -> chromadb.Collection:
    """
    Return the existing ChromaDB collection for *session_id* if it already
    contains data; otherwise call :func:`build_vector_index` first.

    Parameters
    ----------
    function_tree : dict
    session_id    : str

    Returns
    -------
    chromadb.Collection
    """
    client = _get_chroma_client(session_id)
    col_name = _collection_name(session_id)

    try:
        collection = client.get_collection(col_name)
        if collection.count() > 0:
            logger.info(
                "Reusing existing ChromaDB collection '%s' (%d docs).",
                col_name,
                collection.count(),
            )
            return collection
        logger.info("Collection '%s' exists but is empty — rebuilding.", col_name)
    except Exception:
        logger.info("Collection '%s' not found — building from scratch.", col_name)

    return build_vector_index(function_tree, session_id)


# ---------------------------------------------------------------------------
# Public: query_rag
# ---------------------------------------------------------------------------

def query_rag(
    question: str,
    session_id: str,
    chat_history: list[dict],
    function_tree: dict,
    top_k: int = 5,
) -> dict:
    """
    Answer *question* using Retrieval-Augmented Generation over the indexed
    codebase for *session_id*.

    Parameters
    ----------
    question     : str  — user's natural-language question
    session_id   : str
    chat_history : list[dict]  — list of {"role": "user"|"model", "content": str}
    function_tree: dict — used to build the index if it doesn't exist yet
    top_k        : int  — number of context chunks to retrieve

    Returns
    -------
    dict with keys:
        answer          : str
        cited_functions : list[{"func_id", "name", "file"}]
        context_used    : list[{"func_id", "name", "relevance_score"}]
        error           : None | str
    """
    result: dict[str, Any] = {
        "answer": "",
        "cited_functions": [],
        "context_used": [],
        "error": None,
    }

    # ------------------------------------------------------------------
    # 1. Ensure the vector index exists
    # ------------------------------------------------------------------
    try:
        collection = get_or_build_index(function_tree, session_id)
    except Exception as exc:
        logger.error("query_rag: failed to get/build index: %s", exc)
        result["error"] = f"Failed to initialise vector index: {exc}"
        result["answer"] = "I'm sorry — I couldn't initialise the search index. Please try again."
        return result

    # ------------------------------------------------------------------
    # 2. Embed the question
    # ------------------------------------------------------------------
    query_embedding = _embed_text(question, task_type="retrieval_query")

    # ------------------------------------------------------------------
    # 3. Retrieve top-k context chunks from ChromaDB
    # ------------------------------------------------------------------
    try:
        if query_embedding is not None:
            chroma_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, collection.count() or 1),
                include=["documents", "metadatas", "distances"],
            )
        else:
            # Fallback: text-based query (ChromaDB built-in embedding)
            chroma_results = collection.query(
                query_texts=[question],
                n_results=min(top_k, collection.count() or 1),
                include=["documents", "metadatas", "distances"],
            )
    except Exception as exc:
        logger.error("query_rag: ChromaDB query failed: %s", exc)
        result["error"] = f"Vector search failed: {exc}"
        result["answer"] = "I'm sorry — the search step encountered an error."
        return result

    retrieved_docs: list[str] = chroma_results.get("documents", [[]])[0]
    retrieved_metas: list[dict] = chroma_results.get("metadatas", [[]])[0]
    retrieved_distances: list[float] = chroma_results.get("distances", [[]])[0]

    # Build context_used list (convert cosine distance -> similarity score)
    context_used: list[dict] = []
    for meta, dist in zip(retrieved_metas, retrieved_distances):
        relevance = round(1.0 - float(dist), 4)  # cosine similarity ∈ [0, 1]
        context_used.append(
            {
                "func_id": meta.get("func_id", ""),
                "name": meta.get("name", ""),
                "relevance_score": relevance,
            }
        )
    result["context_used"] = context_used

    # ------------------------------------------------------------------
    # 4. Build the prompt
    # ------------------------------------------------------------------
    history_snippet = _format_chat_history(chat_history, max_turns=6)
    context_block = _format_context(retrieved_docs, retrieved_metas)

    prompt = _build_prompt(
        history=history_snippet,
        context=context_block,
        question=question,
    )

    # ------------------------------------------------------------------
    # 5. Call Gemini
    # ------------------------------------------------------------------
    if not _llm:
        result["error"] = "LLM unavailable: GEMINI_API_KEY not configured."
        result["answer"] = (
            "I can't generate an answer because the LLM is not configured. "
            "Please set GEMINI_API_KEY in your .env file."
        )
        return result

    try:
        response = key_manager.generate_content(_GEMINI_MODEL, prompt)
        answer_text: str = response.text.strip()
    except Exception as exc:
        logger.error("query_rag: Gemini generate_content failed: %s", exc)
        result["error"] = f"LLM generation failed: {exc}"
        result["answer"] = "I'm sorry — I encountered an error while generating the answer."
        return result

    result["answer"] = answer_text

    # ------------------------------------------------------------------
    # 6. Extract function references cited in the answer
    # ------------------------------------------------------------------
    result["cited_functions"] = _extract_cited_functions(
        answer_text, retrieved_metas
    )

    return result


# ---------------------------------------------------------------------------
# Prompt-building helpers
# ---------------------------------------------------------------------------

def _format_chat_history(chat_history: list[dict], max_turns: int = 6) -> str:
    """Render the last *max_turns* messages as a formatted string."""
    if not chat_history:
        return ""
    recent = chat_history[-max_turns:]
    lines: list[str] = []
    for msg in recent:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "").strip()
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _format_context(docs: list[str], metas: list[dict]) -> str:
    """Combine retrieved documents into a numbered context block."""
    if not docs:
        return "No relevant code context found."
    parts: list[str] = []
    for i, (doc, meta) in enumerate(zip(docs, metas), 1):
        name = meta.get("name", "unknown")
        filepath = meta.get("file", "unknown")
        parts.append(
            f"--- Context {i}: {name} ({filepath}) ---\n{doc}\n"
        )
    return "\n".join(parts)


def _build_prompt(history: str, context: str, question: str) -> str:
    """Assemble the full RAG prompt."""
    history_section = (
        f"**Conversation History:**\n{history}\n\n" if history else ""
    )
    return f"""You are CodeAtlas, an expert AI assistant that helps developers understand Python codebases.
You have been given relevant code snippets from the project as context.

{history_section}**Relevant Code Context:**
{context}

**User Question:**
{question}

**Instructions:**
- Answer the question based primarily on the provided code context.
- If you reference specific functions or classes, mention their names clearly.
- If the context does not contain enough information, say so honestly.
- Be concise, precise, and technically accurate.
- Format code references using backticks, e.g. `function_name`.

**Answer:**"""


# ---------------------------------------------------------------------------
# Function-reference extractor
# ---------------------------------------------------------------------------

def _extract_cited_functions(
    answer: str, retrieved_metas: list[dict]
) -> list[dict]:
    """
    Identify which of the retrieved functions are explicitly mentioned in
    the generated answer.

    Strategy: look for backtick-quoted identifiers in the answer and cross-
    reference them against the metadata names.
    """
    # Extract identifiers surrounded by backticks
    cited_names: set[str] = set(re.findall(r"`([^`]+)`", answer))

    cited: list[dict] = []
    seen_ids: set[str] = set()

    for meta in retrieved_metas:
        func_id = meta.get("func_id", "")
        name = meta.get("name", "")
        filepath = meta.get("file", "")

        if func_id in seen_ids:
            continue

        # Match by function name or any part of the func_id
        if any(
            cited_name in (name, func_id) or name in cited_name
            for cited_name in cited_names
        ):
            cited.append({"func_id": func_id, "name": name, "file": filepath})
            seen_ids.add(func_id)

    return cited


# ---------------------------------------------------------------------------
# Cleanup helper (used by DELETE /api/session/{session_id})
# ---------------------------------------------------------------------------

def delete_session_index(session_id: str) -> None:
    """
    Drop the ChromaDB collection and remove the cached client for *session_id*.
    Called when a session is deleted via the API.
    """
    try:
        client = _get_chroma_client(session_id)
        col_name = _collection_name(session_id)
        client.delete_collection(col_name)
        logger.info("Deleted ChromaDB collection '%s'.", col_name)
    except Exception as exc:
        logger.warning("Could not delete ChromaDB collection for '%s': %s", session_id, exc)
    finally:
        _chroma_clients.pop(session_id, None)
