#!/bin/bash
# Auto-restart wrapper for hockey-blast-frontend
# Revives the Flask app immediately if it gets killed

cd "$(dirname "$0")"
set -a && source .env && set +a
source .venv/bin/activate

echo "Starting hockey-blast-frontend with auto-restart..."
while true; do
    echo "[$(date)] Starting app..."
    python app.py
    EXIT_CODE=$?
    echo "[$(date)] App exited with code $EXIT_CODE — restarting in 2s..."
    sleep 2
done
