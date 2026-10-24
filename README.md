---
title: CodeAtlas
emoji: 🗺️
colorFrom: blue
colorTo: indigo
sdk: gradio
app_file: app.py
pinned: false
---

# CodeAtlas 🗺️

> **AI-Powered Python Code Analysis & Documentation Platform**

CodeAtlas is a full-stack web application that ingests a Python project as a ZIP file and provides:

- 🔍 **Layered Code Overview** — drill-down from File → Block → Logical Block → Function with AI summaries
- 📊 **Project Report** — two-stage vulnerability scan (web search + LLM) with severity-graded findings
- ⚡ **Function Optimality Check** — complexity analysis and refactoring suggestions (rated 1–5)
- 💥 **Blast Radius / Risk Score** — call-graph-based impact analysis (score 0–10)
- 🌊 **Execution Flow Tracer** — visualizes entry-point → target function call paths
- 💬 **RAG Chatbot** — natural-language Q&A grounded in your codebase via ChromaDB + Gemini

---

## Quick Start

### Prerequisites
- Python 3.10+
- A Google Gemini API key ([get one here](https://aistudio.google.com/apikey))

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY
```

### 2. Install & run backend

**Windows (PowerShell):**
```powershell
.\start_backend.ps1
```

**Linux / macOS:**
```bash
chmod +x start_backend.sh
./start_backend.sh
```

Or manually:
```bash
cd backend
pip install -r requirements.txt
python main.py
```

The backend starts at **http://localhost:8000**

### 3. Open the frontend

Open `frontend/index.html` in your browser (double-click or drag into Chrome/Firefox).

> **Note:** The frontend fetches from `http://localhost:8000`. Keep the backend running while using the app.

---

## Project Structure

```
LAB PROJECT/
├── .env                    # Your API keys (not committed)
├── .env.example            # Template for .env
├── start_backend.ps1       # Windows startup script
├── start_backend.sh        # Linux/macOS startup script
│
├── backend/
│   ├── main.py             # FastAPI app + all API endpoints
│   ├── upload_module.py    # Safe ZIP upload & extraction
│   ├── parser_module.py    # AST parsing & call graph builder
│   ├── overview_module.py  # Function Tree + AI summarization
│   ├── requirements.txt    # Python dependencies
│   └── features/
│       ├── report_module.py    # Two-stage project report
│       ├── optimizer_module.py # Function optimality checker
│       ├── risk_module.py      # Blast radius / risk scorer
│       ├── flow_module.py      # Execution flow tracer
│       └── rag_module.py       # ChromaDB RAG chatbot
│
└── frontend/
    └── index.html          # Self-contained React app (CDN)
```

---

## Architecture

```
ZIP Upload
    │
    ▼
upload_module  ──→  Safe extraction, .py filter
    │
    ▼
parser_module  ──→  AST parse → Function Tree + Call Graph (networkx)
    │
    ▼
overview_module ──→  Gemini summaries → "Function Tree with Description"
    │                                      (central data structure)
    │
    ├──→ Feature 1: Layered Overview Explorer
    ├──→ Feature 2: Project Report (DuckDuckGo + Gemini)
    ├──→ Feature 3: Function Optimality Check (Gemini)
    ├──→ Feature 4: Blast Radius / Risk Score (networkx + Gemini)
    ├──→ Feature 5: Execution Flow Tracer (networkx paths)
    └──→ Feature 6: RAG Chatbot (ChromaDB + Gemini embeddings)
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload ZIP, returns session_id |
| GET | `/api/session/{id}/tree` | Full function tree |
| GET | `/api/session/{id}/search?q=name` | Search functions by name |
| POST | `/api/session/{id}/retry_summarization` | Retry failed LLM summaries |
| POST | `/api/session/{id}/report` | Generate project report |
| GET | `/api/session/{id}/report/export` | Download report as Markdown |
| POST | `/api/session/{id}/optimize` | Check function optimality |
| POST | `/api/session/{id}/risk` | Compute blast radius & risk score |
| POST | `/api/session/{id}/flow` | Trace execution paths to function |
| POST | `/api/session/{id}/chat` | RAG chatbot query |
| DELETE | `/api/session/{id}` | Clean up session |

---

## AI Advisory Notice

> ⚠️ All AI-generated content (summaries, risk scores, reports, chat responses) is advisory in nature and should be reviewed by a human developer. CodeAtlas performs **strictly static analysis** — it never executes uploaded code.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | REST API framework |
| `uvicorn` | ASGI server |
| `google-generativeai` | Gemini LLM + embeddings |
| `chromadb` | In-process vector database |
| `networkx` | Call graph analysis |
| `duckduckgo-search` | Web search for report generation |
| `python-dotenv` | Environment variable loading |
| `pydantic` | Data validation |

Frontend: React 18 (CDN), TailwindCSS (CDN), Prism.js (CDN), Lucide Icons (CDN)
