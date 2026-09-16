#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/neorex" ]; then
    PROJECT_DIR="$SCRIPT_DIR/neorex"
else
    PROJECT_DIR="$SCRIPT_DIR"
fi
cd "$PROJECT_DIR"

export PYTHONPATH="$(dirname "$PROJECT_DIR"):$PROJECT_DIR"

if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
elif [ -f "$(dirname "$PROJECT_DIR")/venv/bin/activate" ]; then
    source "$(dirname "$PROJECT_DIR")/venv/bin/activate"
fi

echo "============================================================"
echo "   Neo.Rex ATS Co-Pilot v2.0                                "
echo "   Engineered by Vineeth Yadav                  "
echo "   GitHub: https://github.com/vineethyadav110               "
echo "============================================================"
echo "🚀 Starting Neo.Rex Backend Server on http://127.0.0.1:8000..."
uvicorn neorex.api.server:app --host 0.0.0.0 --port 8000 --reload
