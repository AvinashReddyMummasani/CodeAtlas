# CodeAtlas 100% Free Cloud Deployment Guide

CodeAtlas is completely configured to deploy on **free-tier cloud platforms without requiring any credit card**.

---

## 🌟 Best Option: Render.com (100% Free Full-Stack Web Service)

Render gives you free hosting for Python full-stack applications with an HTTPS URL (e.g., `https://codeatlas.onrender.com`).

### Step 1: Deploy on Render
1. Go to **[dashboard.render.com](https://dashboard.render.com)** and sign in with GitHub (free, no credit card required).
2. Click **New +** → **Web Service**.
3. Select your repository: **`https://github.com/AvinashReddyMummasani/CodeAtlas`**.
4. Configure the settings:
   * **Name**: `codeatlas` (or your choice)
   * **Region**: Oregon (US West) or Frankfurt (EU)
   * **Branch**: `main`
   * **Runtime**: `Python 3`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   * **Instance Type**: **Free** (0.5 CPU, 512 MB RAM)

### Step 2: Add Environment Variables
Scroll down to **Environment Variables** and add:
* `GEMINI_API_KEY_1`: `your_gemini_api_key_here`
* `GEMINI_MODEL`: `gemini-3.5-flash-lite`
* `GEMINI_EMBEDDING_MODEL`: `models/gemini-embedding-001`
* `AI_BATCH_SUMMARIZE_PER_FILE`: `true`
* `DATABASE_URL`: *(Your free Neon database connection string — see below)*

### Step 3: Deploy
Click **Create Web Service**. Within ~2 minutes, your live site will be up at `https://codeatlas-xxxx.onrender.com`!

---

## 🗄️ 100% Free Cloud Database Setup (Neon.tech PostgreSQL)

To keep your users, login credentials, saved projects, and chat history permanently saved in the cloud for free:

1. Go to **[Neon.tech](https://neon.tech)** and click **Sign Up with GitHub** (takes 10 seconds, zero credit card).
2. Create a project named `codeatlas`.
3. In your dashboard, copy the **Connection string**:
   ```
   postgresql://user:password@ep-cool-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. Paste this string as `DATABASE_URL` in your Render Environment Variables (or `.env`).
5. CodeAtlas will automatically connect and create the tables (`users`, `auth_tokens`, `user_projects`, `chat_threads`, `chat_messages`) on startup!

*(Note: If you leave `DATABASE_URL` empty, CodeAtlas will automatically use the built-in SQLite database).*

---

## 🚀 Alternative Free Option: Koyeb

1. Go to **[koyeb.com](https://app.koyeb.com)** and sign up with GitHub.
2. Click **Create App** → **GitHub**.
3. Select `AvinashReddyMummasani/CodeAtlas`.
4. Koyeb detects the `Procfile` / `Dockerfile`. Set port to `8000`.
5. Add `GEMINI_API_KEY_1` and `DATABASE_URL` in environment variables.
6. Click **Deploy**.

---

## 💻 Local / Self-Hosted Docker Option

```bash
git clone https://github.com/AvinashReddyMummasani/CodeAtlas.git
cd CodeAtlas
docker compose up -d --build
```
Live at `http://localhost:8000`.
