#!/bin/bash
set -e

VENV="/home/egiabot/venvs/seriea-predictor"
PROJECT="/home/egiabot/PROJECT/seriea-predictor"
PORT=8001

source "$VENV/bin/activate"

echo "🚀 Avvio API su http://localhost:$PORT (docs: /docs)"
cd "$PROJECT"
PYTHONPATH="$PROJECT" uvicorn src.api:app --host 0.0.0.0 --port "$PORT"
