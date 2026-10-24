"""
app.py — CodeAtlas Entrypoint for Hugging Face Spaces (Free Gradio SDK) & Local/Cloud Execution.

On Hugging Face Spaces (Gradio SDK):
Hugging Face runs this file with python app.py on a free 2 vCPU / 16GB RAM instance.
It serves the full CodeAtlas FastAPI backend and interactive React SPA on port 7860.
"""

import os
import sys
from pathlib import Path

# Ensure root and backend are on python path
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
if str(_HERE / "backend") not in sys.path:
    sys.path.insert(0, str(_HERE / "backend"))

import uvicorn
from backend.main import app as fastapi_app

# Port for Hugging Face Spaces is 7860 by default, or from PORT env variable
PORT = int(os.environ.get("PORT", 7860))

# Hugging Face Gradio SDK compatibility
try:
    import gradio as gr
    # Mount FastAPI onto Gradio Blocks if required by Hugging Face runner
    demo = gr.mount_gradio_app(fastapi_app, gr.Blocks(title="CodeAtlas"), path="/gradio")
except ImportError:
    demo = None

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_level="info",
    )
