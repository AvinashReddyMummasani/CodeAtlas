#!/bin/bash
# CodeAtlas – Backend startup script (Linux/macOS)
set -e

cd "$(dirname "$0")/backend"

echo "🔍 Checking Python..."
python3 --version

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🚀 Starting CodeAtlas backend on http://localhost:8000"
python3 main.py
