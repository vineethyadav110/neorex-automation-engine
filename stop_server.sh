#!/usr/bin/env bash
echo "🛑 Stopping any running Neo.Rex server on port 8000..."
PID=$(lsof -ti :8000 2>/dev/null || true)
if [ -n "$PID" ]; then
    kill -9 $PID
    echo "✅ Stopped process $PID"
else
    echo "ℹ️ No active process on port 8000."
fi
