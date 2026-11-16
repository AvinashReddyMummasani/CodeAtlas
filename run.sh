#!/bin/bash
# CodeAtlas one-liner launcher: ./run.sh

PORT=${1:-8000}
URL="http://localhost:$PORT"

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║      🗺️  CodeAtlas — AI Code Explorer     ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "  ✗ Python3 not found"
    exit 1
fi
echo "  ✓ $(python3 --version)"

# Install deps
if [ -f requirements.txt ]; then
    python3 -m pip install -r requirements.txt -q --disable-pip-version-check 2>/dev/null
    echo "  ✓ Dependencies ready"
fi

# Load .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "  ✓ Environment loaded"
fi

echo ""
echo "  🚀 Starting CodeAtlas on $URL"
echo "  Press Ctrl+C to stop"
echo ""

# Open browser in background
(sleep 2.5 && (xdg-open "$URL" 2>/dev/null || open "$URL" 2>/dev/null || true)) &

# Start server
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port "$PORT" --reload --reload-dir backend
