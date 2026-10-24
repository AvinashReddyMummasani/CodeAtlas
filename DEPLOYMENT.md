# CodeAtlas Deployment Guide

CodeAtlas is packaged to deploy seamlessly across any cloud platform, container service, or self-hosted server.

---

## Option 1: Render.com (Recommended Free Cloud Deployment)
1. Go to [render.com](https://render.com) and click **New → Web Service**.
2. Connect your GitHub repository: `https://github.com/AvinashReddyMummasani/CodeAtlas`.
3. Render automatically detects `render.yaml` or you can configure manually:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. In the **Environment Variables** section, add your Gemini API keys:
   - `GEMINI_API_KEY_1`: `your_gemini_api_key`
   - `GEMINI_API_KEY_2`: `your_backup_gemini_key` (optional)
   - `GEMINI_MODEL`: `gemini-3.5-flash-lite`
   - `GEMINI_EMBEDDING_MODEL`: `models/gemini-embedding-001`
5. Click **Create Web Service**. Your live URL will be ready in ~2 minutes!

---

## Option 2: Docker / Docker Compose
To run locally or on a VPS (AWS, GCP, DigitalOcean, Linode):

```bash
# Clone the repository
git clone https://github.com/AvinashReddyMummasani/CodeAtlas.git
cd CodeAtlas

# Configure your keys
cp .env.example .env
# Edit .env with your GEMINI_API_KEY_1

# Build and start the container
docker compose up -d --build
```
The application will be live at `http://localhost:8000`.

---

## Option 3: Railway.app
1. Go to [railway.app](https://railway.app) and click **New Project → Deploy from GitHub repo**.
2. Select `AvinashReddyMummasani/CodeAtlas`.
3. Under **Variables**, add `GEMINI_API_KEY_1` (and optionally `2`, `3`, `4`).
4. Railway will automatically build via `Procfile` and deploy your app with an HTTPS URL.

---

## Option 4: Hugging Face Spaces (Docker Space)
1. Create a new Space on [huggingface.co/spaces](https://huggingface.co/spaces) with **SDK: Docker**.
2. Push this repository to your Space.
3. In **Settings → Variables and Secrets**, add `GEMINI_API_KEY_1`.
4. Hugging Face will build the Docker container and host it publicly for free.

---

## Option 5: Local Production Server
Run the production server directly with Python:

```bash
# On Linux/macOS
./start_backend.sh

# On Windows
.\start_backend.ps1
```
