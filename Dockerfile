# CodeAtlas Production Dockerfile for Hugging Face Spaces & Cloud Containers
FROM python:3.12-slim

# Avoid writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# Install build tools needed for native dependencies (e.g., bcrypt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs containers with UID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Install Python dependencies first for efficient layer caching
COPY --chown=user requirements.txt $HOME/app/
RUN pip install --no-cache-dir --user --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# Copy application source code
COPY --chown=user backend/ $HOME/app/backend/
COPY --chown=user frontend/ $HOME/app/frontend/
COPY --chown=user README.md $HOME/app/

# Create persistent storage directories
RUN mkdir -p $HOME/app/sessions $HOME/app/chroma_store

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

EXPOSE 7860

# Run FastAPI via Uvicorn
CMD ["sh", "-c", "python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
