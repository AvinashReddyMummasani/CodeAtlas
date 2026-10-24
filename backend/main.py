"""
main.py — FastAPI application entry point for CodeAtlas.

Wires together all modules and exposes the REST API consumed by the frontend.

Environment variables (loaded from .env in the project root):
    GEMINI_API_KEY
    GEMINI_MODEL
    GEMINI_EMBEDDING_MODEL
    CHROMA_DIR
    CORS_ORIGINS   — comma-separated origins, or "*" for all  (default: "*")
    SESSION_DIR    — directory for uploaded session data        (default: sessions)
    MAX_UPLOAD_MB  — maximum compressed upload size             (default: 50)
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from the project root (parent of this file's directory)
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_ENV_FILE = _HERE.parent / ".env"
load_dotenv(dotenv_path=_ENV_FILE)

# ---------------------------------------------------------------------------
# FastAPI and Starlette imports
# ---------------------------------------------------------------------------
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

# ---------------------------------------------------------------------------
# CodeAtlas module imports
# ---------------------------------------------------------------------------
import sys

sys.path.insert(0, str(_HERE))  # ensure backend/ is on the path

import upload_module
import parser_module
import overview_module
import key_manager
import auth_module
from features import rag_module

# Feature modules — imported lazily so missing files don't crash startup
try:
    from features import report_module
    _HAS_REPORT = True
except ImportError:
    _HAS_REPORT = False

try:
    from features import optimizer_module
    _HAS_OPTIMIZER = True
except ImportError:
    _HAS_OPTIMIZER = False

try:
    from features import risk_module
    _HAS_RISK = True
except ImportError:
    _HAS_RISK = False

try:
    from features import flow_module
    _HAS_FLOW = True
except ImportError:
    _HAS_FLOW = False

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("codeatlas.main")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_CORS_ORIGINS_RAW: str = os.getenv("CORS_ORIGINS", "*")
_CORS_ORIGINS: list[str] = (
    ["*"]
    if _CORS_ORIGINS_RAW.strip() == "*"
    else [o.strip() for o in _CORS_ORIGINS_RAW.split(",") if o.strip()]
)
_MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "50"))
_SESSION_DIR: str = os.getenv("SESSION_DIR", str(_HERE.parent / "sessions"))
_FRONTEND_DIR: Path = _HERE.parent / "frontend"

# ---------------------------------------------------------------------------
# In-memory session store
# { session_id: { "function_tree": dict, "session_dir": str, "status": dict } }
# ---------------------------------------------------------------------------
sessions: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Session status helpers
# ---------------------------------------------------------------------------
def _save_session_state(session_id: str) -> None:
    """Persist session status and tree to disk so sessions survive server reloads."""
    session = sessions.get(session_id)
    if not session:
        return
    sdir = session.get("session_dir")
    if not sdir or not Path(sdir).exists():
        return
    try:
        meta_file = Path(sdir) / "session_meta.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "session_id": session_id,
                "status": session.get("status", {}),
                "has_tree": session.get("function_tree") is not None,
            }, f)
        tree = session.get("function_tree")
        if tree is not None:
            tree_file = Path(sdir) / "function_tree.json"
            with open(tree_file, "w", encoding="utf-8") as f:
                json.dump(tree, f)
    except Exception as exc:
        logger.warning("Could not persist session '%s' to disk: %s", session_id, exc)

def _set_status(session_id: str, stage: str, done: int = 0, total: int = 0) -> None:
    if session_id in sessions:
        sessions[session_id]["status"] = {
            "stage": stage, "done": done, "total": total,
            "finished": False, "error": None,
        }
        _save_session_state(session_id)

def _finish_status(session_id: str, error: str | None = None) -> None:
    if session_id in sessions:
        s = sessions[session_id].get("status", {})
        s["finished"] = True
        s["error"] = error
        sessions[session_id]["status"] = s
        _save_session_state(session_id)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CodeAtlas API",
    description="AI-powered Python codebase explorer and analyser.",
    version="1.0.0",
)

# ------------------------------------------------------------------
# CORS
# ------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# No-cache middleware for SPA HTML and JS assets
# ------------------------------------------------------------------
@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/js") or path.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# ------------------------------------------------------------------
# Static file serving — serve the frontend SPA
# ------------------------------------------------------------------
_FRONTEND_INDEX = _FRONTEND_DIR / "index.html"


@app.get("/", include_in_schema=False)
async def serve_frontend() -> FileResponse:
    if not _FRONTEND_INDEX.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return FileResponse(
        str(_FRONTEND_INDEX),
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


# Optionally mount the rest of the frontend assets if the directory exists
if _FRONTEND_DIR.exists():
    try:
        app.mount(
            "/static",
            StaticFiles(directory=str(_FRONTEND_DIR), html=True),
            name="static",
        )
    except Exception as _mount_err:
        logger.warning("Could not mount frontend static files: %s", _mount_err)

_JS_DIR = _FRONTEND_DIR / "js"
if _JS_DIR.exists():
    try:
        app.mount(
            "/js",
            StaticFiles(directory=str(_JS_DIR)),
            name="js",
        )
    except Exception as _mount_err:
        logger.warning("Could not mount /js directory: %s", _mount_err)

# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


class SignupRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class CreateThreadRequest(BaseModel):
    title: Optional[str] = "New Chat"


class UpdateThreadRequest(BaseModel):
    title: str


class OptimizeRequest(BaseModel):
    func_id: Optional[str] = None
    filepath: Optional[str] = None
    bulk: bool = False


class RiskRequest(BaseModel):
    func_id: Optional[str] = None
    filepath: Optional[str] = None
    bulk: bool = False


class FlowRequest(BaseModel):
    func_id: str


class ChatRequest(BaseModel):
    question: str
    chat_history: list[dict] = Field(default_factory=list)
    thread_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Helper: require a valid session
# ---------------------------------------------------------------------------


def _get_current_user(request: Request) -> Optional[dict]:
    """Extract user profile from Authorization Bearer token header if present."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    return auth_module.get_user_by_token(auth_header)


def _get_session(session_id: str) -> dict:
    """Return the session dict or raise HTTP 404. Also recovers from disk if server reloaded."""
    if session_id in sessions:
        return sessions[session_id]

    # Check if session exists on disk
    candidate_paths = [
        Path(_SESSION_DIR) / session_id,
        _HERE.parent / "sessions" / session_id,
        _HERE / "sessions" / session_id,
    ]
    for sess_path in candidate_paths:
        if sess_path.exists():
            tree = None
            tree_file = sess_path / "function_tree.json"
            if tree_file.exists():
                try:
                    with open(tree_file, "r", encoding="utf-8") as f:
                        tree = json.load(f)
                except Exception:
                    pass

            meta_file = sess_path / "session_meta.json"
            status = {"stage": "Ready", "finished": True, "error": None}
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        status = meta.get("status", status)
                except Exception:
                    pass

            recovered = {
                "function_tree": tree,
                "session_dir": str(sess_path),
                "status": status,
            }
            sessions[session_id] = recovered
            logger.info("Recovered session '%s' from disk storage.", session_id)
            return recovered

    raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")


def _get_tree(session_id: str) -> dict:
    """Return the function_tree for *session_id* or raise HTTP 404/202."""
    session = _get_session(session_id)
    tree = session.get("function_tree")
    if tree is None:
        raise HTTPException(status_code=202, detail="Summarization still in progress. Poll /status.")
    return tree


# ---------------------------------------------------------------------------
# Background task: RAG indexing
# ---------------------------------------------------------------------------


def _background_index(function_tree: dict, session_id: str) -> None:
    """Build the RAG vector index in the background after upload."""
    try:
        rag_module.get_or_build_index(function_tree, session_id)
        logger.info("Background RAG indexing complete for session '%s'.", session_id)
    except Exception as exc:
        logger.error("Background RAG indexing failed for '%s': %s", session_id, exc)


def _background_summarize(parse_result: dict, session_id: str) -> None:
    """Run Gemini summarization + RAG indexing fully in the background."""
    try:
        _set_status(session_id, "Generating AI summaries…", 0, 1)
        function_tree = overview_module.build_function_tree(parse_result, session_id)
        sessions[session_id]["function_tree"] = function_tree
        _set_status(session_id, "Indexing for chat…", 0, 1)
        rag_module.get_or_build_index(function_tree, session_id)
        _finish_status(session_id)
        logger.info("Background summarization+indexing done for '%s'.", session_id)
        try:
            fn_cnt = len(function_tree.get("all_functions", {}))
            with auth_module._get_connection() as conn:
                conn.execute("UPDATE user_projects SET functions_count = ? WHERE session_id = ?", (fn_cnt, session_id))
        except Exception:
            pass
    except Exception as exc:
        logger.error("Background summarization failed for '%s': %s", session_id, exc)
        _finish_status(session_id, error=str(exc))


# ===========================================================================
# Endpoints
# ===========================================================================

# ---------------------------------------------------------------------------
# POST /api/upload
# ---------------------------------------------------------------------------


@app.post("/api/upload", summary="Upload a ZIP of Python source files")
async def upload(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="ZIP archive of the project"),
    session_id: Optional[str] = Form(None, description="Existing session ID (optional)"),
) -> JSONResponse:
    """
    Accept a ZIP upload, extract + parse synchronously (fast),
    then kick off Gemini summarization in the background and return immediately.
    """
    if session_id is None or session_id.strip() == "":
        session_id = str(uuid.uuid4())

    # 1. Save & extract the upload
    upload_result = await upload_module.save_upload(
        file=file,
        session_id=session_id,
        max_mb=_MAX_UPLOAD_MB,
    )
    if upload_result.get("error"):
        raise HTTPException(status_code=400, detail=upload_result["error"])

    session_dir: str = upload_result["session_dir"]
    py_files: list[str] = upload_result["py_files"]
    other_files: list[str] = upload_result["other_files"]

    # 2. Parse the project (fast — pure AST, no network)
    try:
        parse_result = parser_module.parse_project(
            session_dir=session_dir,
            py_files=py_files,
        )
    except Exception as exc:
        logger.error("parse_project failed for session '%s': %s", session_id, exc)
        raise HTTPException(status_code=500, detail=f"Parsing failed: {exc}") from exc

    # 3. Store a skeleton session immediately (no summaries yet)
    sessions[session_id] = {
        "function_tree": None,   # filled by background task
        "session_dir": session_dir,
        "status": {
            "stage": "Parsing complete — starting AI summarization…",
            "done": 0, "total": len(py_files),
            "finished": False, "error": None,
        },
    }

    # 4. Summarize + index in background — frontend polls /status
    background_tasks.add_task(_background_summarize, parse_result, session_id)

    # Associate with authenticated user if logged in
    user = _get_current_user(request)
    if user:
        proj_name = file.filename or "Python Project"
        if proj_name.lower().endswith(".zip"):
            proj_name = proj_name[:-4]
        try:
            auth_module.link_user_project(
                user_id=user["id"],
                session_id=session_id,
                project_name=proj_name,
                files_count=len(py_files),
                functions_count=0,
            )
            logger.info("Associated session '%s' with user '%s'.", session_id, user["username"])
        except Exception as exc:
            logger.warning("Failed linking project to user: %s", exc)

    syntax_errors = parse_result.get("syntax_errors", {})
    entry_points  = parse_result.get("entry_points", [])

    return JSONResponse(
        status_code=200,
        content={
            "session_id": session_id,
            "py_files_count": len(py_files),
            "other_files_count": len(other_files),
            "syntax_errors": syntax_errors,
            "entry_points": entry_points,
            "summarizing": True,   # tells frontend to poll /status
        },
    )


# ---------------------------------------------------------------------------
# GET /api/session/{session_id}/tree
# ---------------------------------------------------------------------------


@app.get(
    "/api/session/{session_id}/tree",
    summary="Get full function tree for a session",
)
async def get_tree(session_id: str) -> JSONResponse:
    """Return the complete FunctionTree dict for *session_id*."""
    session = _get_session(session_id)
    tree = session.get("function_tree")
    if tree is None:
        # Still summarizing — return 202 Accepted
        return JSONResponse(status_code=202, content={"summarizing": True})
    return JSONResponse(content=tree)


# ---------------------------------------------------------------------------
# GET /api/session/{session_id}/status
# ---------------------------------------------------------------------------

@app.get("/api/session/{session_id}/status", summary="Poll summarization progress")
async def get_status(session_id: str) -> JSONResponse:
    """Return current background summarization status."""
    session = _get_session(session_id)
    status = session.get("status", {"stage": "unknown", "finished": False, "error": None})
    tree = session.get("function_tree")
    return JSONResponse(content={
        **status,
        "tree_ready": tree is not None,
        "llm_available": tree.get("llm_available", False) if tree else False,
    })


# ---------------------------------------------------------------------------
# GET /api/session/{session_id}/file/{file_path}
# ---------------------------------------------------------------------------


@app.get(
    "/api/session/{session_id}/file/{file_path:path}",
    summary="Get file-level node",
)
async def get_file_node(session_id: str, file_path: str) -> JSONResponse:
    """
    Return the file-level node (with all its blocks, functions, logical_blocks)
    for the given relative *file_path* within the session.
    """
    tree = _get_tree(session_id)
    files: dict = tree.get("files", {})

    # The file_path in the tree uses the OS-normalised relative path
    # Try direct lookup first, then a suffix match
    node = files.get(file_path)
    if node is None:
        # Try matching by suffix / normalisation
        for stored_path, stored_node in files.items():
            if stored_path.replace("\\", "/").endswith(file_path.replace("\\", "/")):
                node = stored_node
                break

    if node is None:
        raise HTTPException(
            status_code=404,
            detail=f"File '{file_path}' not found in session '{session_id}'.",
        )
    return JSONResponse(content=node)


# ---------------------------------------------------------------------------
# POST /api/session/{session_id}/retry_summarization
# ---------------------------------------------------------------------------


@app.post(
    "/api/session/{session_id}/retry_summarization",
    summary="Retry LLM summarisation and re-index RAG",
)
async def retry_summarization(
    session_id: str,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    """
    Re-run Gemini summarisation for any nodes that still lack a summary,
    then trigger a fresh RAG re-index in the background.
    """
    session = _get_session(session_id)
    tree = _get_tree(session_id)

    try:
        updated_tree = overview_module.retry_summarization(tree)
    except Exception as exc:
        logger.error("retry_summarization failed for '%s': %s", session_id, exc)
        raise HTTPException(status_code=500, detail=f"Retry summarisation failed: {exc}") from exc

    session["function_tree"] = updated_tree

    # Re-index RAG with fresh summaries
    background_tasks.add_task(
        lambda: rag_module.build_vector_index(updated_tree, session_id)
    )

    # Return a lightweight summary of the tree
    all_funcs = updated_tree.get("all_functions", {})
    summarised = sum(1 for f in all_funcs.values() if f.get("summary"))
    return JSONResponse(
        content={
            "session_id": session_id,
            "llm_available": updated_tree.get("llm_available", False),
            "total_functions": len(all_funcs),
            "summarised_functions": summarised,
        }
    )


# ---------------------------------------------------------------------------
# GET /api/session/{session_id}/search
# ---------------------------------------------------------------------------


@app.get(
    "/api/session/{session_id}/search",
    summary="Search functions/blocks by name",
)
async def search(session_id: str, q: str = "") -> JSONResponse:
    """
    Case-insensitive substring search over all function and block names.

    Query parameter: ``q`` — the search string (must be non-empty).
    """
    tree = _get_tree(session_id)
    if not q:
        return JSONResponse(content=[])

    q_lower = q.lower()
    matches: list[dict] = []
    all_functions: dict = tree.get("all_functions", {})

    for func_id, fnode in all_functions.items():
        name: str = fnode.get("name", "")
        if q_lower in name.lower():
            summary_full: str = fnode.get("summary", "") or ""
            summary_short = summary_full[:120] + "…" if len(summary_full) > 120 else summary_full
            matches.append(
                {
                    "func_id": func_id,
                    "name": name,
                    "file": fnode.get("file", fnode.get("filepath", "")),
                    "lineno": fnode.get("lineno", 0),
                    "summary_short": summary_short,
                }
            )

    # Sort alphabetically by name for deterministic output
    matches.sort(key=lambda m: m["name"].lower())
    return JSONResponse(content=matches)


# ---------------------------------------------------------------------------
# POST /api/session/{session_id}/report
# ---------------------------------------------------------------------------


@app.post(
    "/api/session/{session_id}/report",
    summary="Generate a project health report",
)
async def generate_report(session_id: str) -> JSONResponse:
    """Generate and return the full CodeAtlas project report."""
    if not _HAS_REPORT:
        raise HTTPException(status_code=501, detail="report_module is not installed.")
    tree = _get_tree(session_id)
    try:
        report = report_module.generate_report(tree)  # type: ignore[union-attr]
    except Exception as exc:
        logger.error("generate_report failed for '%s': %s", session_id, exc)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}") from exc
    return JSONResponse(content=report)


# ---------------------------------------------------------------------------
# GET /api/session/{session_id}/report/export
# ---------------------------------------------------------------------------


@app.get(
    "/api/session/{session_id}/report/export",
    summary="Export the report as a Markdown file",
)
async def export_report(session_id: str) -> Response:
    """Stream the generated report as a downloadable Markdown attachment."""
    if not _HAS_REPORT:
        raise HTTPException(status_code=501, detail="report_module is not installed.")
    tree = _get_tree(session_id)
    try:
        report_result = report_module.generate_report(tree)  # type: ignore[union-attr]
        md_content: str = report_module.export_report_markdown(report_result, tree)  # type: ignore[union-attr]
        if not md_content:
            import json
            md_content = f"# CodeAtlas Report\n\n```json\n{json.dumps(report_result, indent=2)}\n```\n"
    except Exception as exc:
        logger.error("export_report failed for '%s': %s", session_id, exc)
        raise HTTPException(status_code=500, detail=f"Report export failed: {exc}") from exc

    return Response(
        content=md_content.encode("utf-8"),
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="codeatlas_report_{session_id[:8]}.md"'
        },
    )


# ---------------------------------------------------------------------------
# POST /api/session/{session_id}/optimize
# ---------------------------------------------------------------------------


@app.post(
    "/api/session/{session_id}/optimize",
    summary="Check function(s) for optimisation opportunities",
)
async def optimize(session_id: str, body: OptimizeRequest) -> JSONResponse:
    """
    Single-function: ``{"func_id": "..."}``
    Bulk (whole file): ``{"filepath": "...", "bulk": true}``
    """
    if not _HAS_OPTIMIZER:
        raise HTTPException(status_code=501, detail="optimizer_module is not installed.")
    tree = _get_tree(session_id)

    try:
        if body.bulk and body.filepath:
            result = optimizer_module.bulk_check_file(  # type: ignore[union-attr]
                function_tree=tree,
                filepath=body.filepath,
            )
        elif body.func_id:
            result = optimizer_module.check_function_optimality(  # type: ignore[union-attr]
                function_tree=tree,
                func_id=body.func_id,
            )
        else:
            raise HTTPException(
                status_code=422,
                detail="Provide either 'func_id' or 'filepath' + 'bulk: true'.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("optimize failed for '%s': %s", session_id, exc)
        raise HTTPException(status_code=500, detail=f"Optimisation check failed: {exc}") from exc

    return JSONResponse(content=result)


# ---------------------------------------------------------------------------
# POST /api/session/{session_id}/risk
# ---------------------------------------------------------------------------


@app.post(
    "/api/session/{session_id}/risk",
    summary="Compute risk score for function(s)",
)
async def risk(session_id: str, body: RiskRequest) -> JSONResponse:
    """
    Single-function: ``{"func_id": "..."}``
    Bulk (whole file): ``{"filepath": "...", "bulk": true}``
    """
    if not _HAS_RISK:
        raise HTTPException(status_code=501, detail="risk_module is not installed.")
    tree = _get_tree(session_id)

    try:
        if body.bulk and body.filepath:
            result = risk_module.rank_file_by_risk(  # type: ignore[union-attr]
                function_tree=tree,
                filepath=body.filepath,
            )
        elif body.func_id:
            result = risk_module.compute_risk_score(  # type: ignore[union-attr]
                function_tree=tree,
                func_id=body.func_id,
            )
        else:
            raise HTTPException(
                status_code=422,
                detail="Provide either 'func_id' or 'filepath' + 'bulk: true'.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("risk failed for '%s': %s", session_id, exc)
        raise HTTPException(status_code=500, detail=f"Risk computation failed: {exc}") from exc

    return JSONResponse(content=result)


# ---------------------------------------------------------------------------
# POST /api/session/{session_id}/flow
# ---------------------------------------------------------------------------


@app.post(
    "/api/session/{session_id}/flow",
    summary="Find execution paths for a function",
)
async def flow(session_id: str, body: FlowRequest) -> JSONResponse:
    """Return the execution-path analysis for the given ``func_id``."""
    if not _HAS_FLOW:
        raise HTTPException(status_code=501, detail="flow_module is not installed.")
    tree = _get_tree(session_id)

    try:
        result = flow_module.find_execution_paths(  # type: ignore[union-attr]
            function_tree=tree,
            target_func_id=body.func_id,
        )
    except Exception as exc:
        logger.error("flow failed for '%s': %s", session_id, exc)
        raise HTTPException(status_code=500, detail=f"Flow analysis failed: {exc}") from exc

    return JSONResponse(content=result)


# ---------------------------------------------------------------------------
# POST /api/session/{session_id}/chat
# ---------------------------------------------------------------------------


# ===========================================================================
# Authentication & User Management Endpoints
# ===========================================================================

@app.post("/api/auth/signup", summary="Register a new user account")
async def auth_signup(body: SignupRequest) -> JSONResponse:
    try:
        data = auth_module.signup(body.username, body.email, body.password)
        return JSONResponse(content=data, status_code=201)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Signup error: %s", exc)
        raise HTTPException(status_code=500, detail="Registration failed.")


@app.post("/api/auth/login", summary="Log in to user account")
async def auth_login(body: LoginRequest) -> JSONResponse:
    try:
        data = auth_module.login(body.username_or_email, body.password)
        return JSONResponse(content=data, status_code=200)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception as exc:
        logger.error("Login error: %s", exc)
        raise HTTPException(status_code=500, detail="Authentication failed.")


@app.get("/api/auth/me", summary="Get current user and saved projects")
async def auth_me(request: Request) -> JSONResponse:
    user = _get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    projects = auth_module.get_user_projects(user["id"])
    return JSONResponse(content={"user": user, "projects": projects})


@app.post("/api/auth/logout", summary="Log out user")
async def auth_logout(request: Request) -> JSONResponse:
    auth_header = request.headers.get("Authorization")
    if auth_header:
        auth_module.logout(auth_header)
    return JSONResponse(content={"success": True})


@app.get("/api/auth/projects", summary="List all projects for authenticated user")
async def auth_user_projects(request: Request) -> JSONResponse:
    user = _get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    projects = auth_module.get_user_projects(user["id"])
    return JSONResponse(content=projects)


@app.post("/api/session/{session_id}/activate", summary="Activate and load existing session")
async def activate_session(session_id: str) -> JSONResponse:
    session = _get_session(session_id)
    tree = session.get("function_tree")
    files_count = len(tree.get("files", {})) if tree else 0
    funcs_count = len(tree.get("all_functions", {})) if tree else 0
    return JSONResponse(content={
        "session_id": session_id,
        "py_files_count": files_count,
        "functions_count": funcs_count,
        "summarizing": False if tree else True,
        "status": session.get("status", {}),
    })


# ===========================================================================
# Chat Threads & Message History Endpoints
# ===========================================================================

@app.get("/api/session/{session_id}/threads", summary="List chat threads for a session")
async def list_chat_threads(session_id: str, request: Request) -> JSONResponse:
    user = _get_current_user(request)
    threads = auth_module.list_threads(session_id, user["id"] if user else None)
    return JSONResponse(content=threads)


@app.post("/api/session/{session_id}/threads", summary="Create a new chat thread")
async def create_chat_thread(session_id: str, body: CreateThreadRequest, request: Request) -> JSONResponse:
    user = _get_current_user(request)
    thread = auth_module.create_thread(session_id, body.title or "New Chat", user["id"] if user else None)
    return JSONResponse(content=thread, status_code=201)


@app.get("/api/session/{session_id}/threads/{thread_id}/messages", summary="Get messages in a thread")
async def get_thread_messages(session_id: str, thread_id: str) -> JSONResponse:
    thread = auth_module.get_thread(thread_id)
    if not thread or thread["session_id"] != session_id:
        raise HTTPException(status_code=404, detail="Chat thread not found.")
    messages = auth_module.get_thread_messages(thread_id)
    return JSONResponse(content={"thread": thread, "messages": messages})


@app.delete("/api/session/{session_id}/threads/{thread_id}", summary="Delete a chat thread")
async def delete_chat_thread(session_id: str, thread_id: str) -> JSONResponse:
    ok = auth_module.delete_thread(thread_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Chat thread not found.")
    return JSONResponse(content={"success": True})


@app.put("/api/session/{session_id}/threads/{thread_id}", summary="Rename a chat thread")
async def update_chat_thread(session_id: str, thread_id: str, body: UpdateThreadRequest) -> JSONResponse:
    ok = auth_module.update_thread_title(thread_id, body.title)
    if not ok:
        raise HTTPException(status_code=404, detail="Chat thread not found.")
    return JSONResponse(content={"success": True})


# ---------------------------------------------------------------------------
# POST /api/session/{session_id}/chat
# ---------------------------------------------------------------------------

@app.post(
    "/api/session/{session_id}/chat",
    summary="Ask the RAG chatbot a question with persistent chat history",
)
async def chat(session_id: str, body: ChatRequest, request: Request) -> JSONResponse:
    """
    Use Retrieval-Augmented Generation to answer a natural-language question
    about the uploaded codebase with persistent chat history.
    """
    tree = _get_tree(session_id)
    user = _get_current_user(request)
    thread_id = body.thread_id

    # If no thread_id provided, create a new thread with question title
    if not thread_id:
        title = body.question.strip()[:45]
        if len(body.question.strip()) > 45:
            title += "…"
        thread = auth_module.create_thread(
            session_id=session_id,
            title=title,
            user_id=user["id"] if user else None,
        )
        thread_id = thread["id"]

    # Record user message in history
    auth_module.add_message(thread_id=thread_id, sender="user", text=body.question)

    # Reconstruct history from thread if body.chat_history was empty
    history = list(body.chat_history)
    if not history:
        past_msgs = auth_module.get_thread_messages(thread_id)
        for m in past_msgs[:-1]:  # exclude the one we just added
            role = "user" if m["sender"] == "user" else "assistant"
            history.append({"role": role, "content": m["text"]})

    try:
        result = rag_module.query_rag(
            question=body.question,
            session_id=session_id,
            chat_history=history,
            function_tree=tree,
        )
    except Exception as exc:
        logger.error("chat failed for '%s': %s", session_id, exc)
        raise HTTPException(status_code=500, detail=f"RAG query failed: {exc}") from exc

    # Record AI message in history
    auth_module.add_message(
        thread_id=thread_id,
        sender="ai",
        text=result.get("answer", ""),
        citations=result.get("citations", []),
    )
    result["thread_id"] = thread_id
    return JSONResponse(content=result)


# ---------------------------------------------------------------------------
# DELETE /api/session/{session_id}
# ---------------------------------------------------------------------------


@app.delete(
    "/api/session/{session_id}",
    summary="Delete a session and free all resources",
)
async def delete_session(session_id: str) -> JSONResponse:
    """
    Remove the session from the in-memory store, delete uploaded files from
    disk, and drop the associated ChromaDB collection.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    session = sessions.pop(session_id)

    # 1. Delete uploaded files from disk
    session_dir: str | None = session.get("session_dir")
    if session_dir:
        try:
            shutil.rmtree(session_dir, ignore_errors=True)
            logger.info("Deleted session directory '%s'.", session_dir)
        except Exception as exc:
            logger.warning("Could not delete session dir '%s': %s", session_dir, exc)

    # 2. Drop the ChromaDB collection
    try:
        rag_module.delete_session_index(session_id)
    except Exception as exc:
        logger.warning("Could not delete RAG index for '%s': %s", session_id, exc)

    return JSONResponse(
        content={"session_id": session_id, "deleted": True},
        status_code=200,
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/api/health", include_in_schema=False)
async def health() -> JSONResponse:
    return JSONResponse(content={"status": "ok", "service": "CodeAtlas"})


@app.get("/api/keys/status", summary="Check API key rotation status")
async def keys_status() -> JSONResponse:
    """Return availability status for all configured Gemini API keys."""
    return JSONResponse(content={"keys": key_manager.key_status()})


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(_HERE)],
        reload_excludes=["sessions*", "chroma_store*", "*.zip", "*.json"],
        log_level="info",
    )
