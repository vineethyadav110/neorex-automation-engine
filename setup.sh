#!/usr/bin/env bash
set -e

# Detect if executing from root or inside neorex
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/neorex" ]; then
    PROJECT_DIR="$SCRIPT_DIR/neorex"
else
    PROJECT_DIR="$SCRIPT_DIR"
fi
cd "$PROJECT_DIR"

echo "============================================================"
echo "   Neo.Rex & Workday Co-Pilot: Total System Setup           "
echo "   Engineered by Vineeth Yadav                  "
echo "   GitHub: https://github.com/vineethyadav110               "
echo "============================================================"
echo "📍 Working Directory: $PROJECT_DIR"

# 1. Locate Python 3
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python 3 not found in PATH."
    exit 1
fi

PY_VER=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python detected: $PYTHON_CMD ($PY_VER)"

# 2. Virtual Environment Setup
VENV_DIR="$PROJECT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating Python virtual environment at ./venv..."
    $PYTHON_CMD -m venv "$VENV_DIR" 2>/dev/null || true
fi

if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
    echo "✅ Virtual environment active: $VENV_DIR"
    PIP_CMD="pip"
    PYTHON_RUN="python"
else
    echo "ℹ️ Running with local environment: $PYTHON_CMD"
    PIP_CMD="$PYTHON_CMD -m pip"
    PYTHON_RUN="$PYTHON_CMD"
fi

# 3. Install required packages
echo "📥 Installing dependencies..."
$PIP_CMD install fastapi uvicorn pydantic python-docx --quiet 2>/dev/null || $PIP_CMD install fastapi uvicorn pydantic python-docx --user --quiet 2>/dev/null || true

# 4. Prepare data directories
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/data/generated_docs"

# 5. Health Check
echo "🧪 Verifying system components..."
PYTHONPATH="$(dirname "$PROJECT_DIR"):"$PROJECT_DIR"" $PYTHON_RUN -c "
import sys
try:
    from neorex.core.mapper import ScreeningEngine
    from neorex.core.evaluator import JobRoleEvaluator
    from neorex.core.storage import ApplicationTrackerDB
    print('   -> Verified ScreeningEngine & JobRoleEvaluator.')
except ImportError:
    from core.mapper import ScreeningEngine
    from core.evaluator import JobRoleEvaluator
    from core.storage import ApplicationTrackerDB
    print('   -> Verified ScreeningEngine & JobRoleEvaluator (local).')
"

chmod +x "$PROJECT_DIR/start_server.sh" 2>/dev/null || true
chmod +x "$PROJECT_DIR/stop_server.sh" 2>/dev/null || true

echo ""
echo "============================================================"
echo "🎉 Total Setup Completed Successfully!"
echo "============================================================"
echo ""
echo "▶️  To start the backend server, run:"
echo "    ./start_server.sh"
echo ""
echo "▶️  To install the Chrome Extension cleanly:"
echo "    1. Open Google Chrome and go to: chrome://extensions"
echo "    2. Enable 'Developer mode' (toggle in the top-right corner)."
echo "    3. If you previously had Neo.Rex installed, click 'Remove'."
echo "    4. Click 'Load unpacked' (top-left button)."
echo "    5. Select the 'extension' folder:"
echo "       $PROJECT_DIR/extension"
echo "    6. Pin Neo.Rex to your Chrome toolbar."
echo ""
