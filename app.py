"""
app.py — CodeAtlas All-in-One Entrypoint
========================================
- Local One-Line Launch: python app.py
  (Starts FastAPI backend and automatically opens the browser at http://localhost:8000)
- Cloud / Hugging Face Spaces / Render Deployments:
  (Respects PORT, SPACE_ID, RENDER environment variables)
"""

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Ensure root and backend are on Python path
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
if str(_HERE / "backend") not in sys.path:
    sys.path.insert(0, str(_HERE / "backend"))

# Load .env if present
_env_path = _HERE / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=_env_path)
    except ImportError:
        pass

import uvicorn
from backend.main import app as fastapi_app

# Default port: 7860 on HuggingFace, PORT env var if present, or 8000 locally
_DEFAULT_PORT = 7860 if os.environ.get("SPACE_ID") else 8000
PORT = int(os.environ.get("PORT", _DEFAULT_PORT))

# Optional Hugging Face Gradio SDK compatibility
try:
    import gradio as gr
    demo = gr.mount_gradio_app(fastapi_app, gr.Blocks(title="CodeAtlas"), path="/gradio")
except ImportError:
    demo = None


def _auto_open_browser(url: str):
    """Wait for server to bind, then open the default web browser."""
    time.sleep(1.8)
    try:
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == "__main__":
    url = f"http://localhost:{PORT}"
    is_headless = bool(os.environ.get("SPACE_ID") or os.environ.get("RENDER") or os.environ.get("HEADLESS"))

    print("")
    print("  ================================================")
    print("       CodeAtlas — AI Code Intelligence Platform   ")
    print(f"       Server URL: {url}                         ")
    print("  ================================================")
    print("")

    if not is_headless:
        print(f"  Opening browser at {url} ...")
        threading.Thread(target=_auto_open_browser, args=(url,), daemon=True).start()

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_level="info",
    )
