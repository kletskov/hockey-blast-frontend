#!/bin/bash
# pull_and_deploy.sh — pull latest code and restart the frontend service
# Usage: ./pull_and_deploy.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🏒 Hockey Blast Frontend Deploy"
echo "================================"

# ── 1. Pull latest from GitHub ─────────────────────────────────────────────
echo ""
echo "📥 Pulling latest code..."
git fetch origin main
BEFORE=$(git rev-parse HEAD)
git pull origin main
AFTER=$(git rev-parse HEAD)

if [ "$BEFORE" = "$AFTER" ]; then
  echo "   Already up to date."
else
  CHANGED_FILES=$(git diff --name-only "$BEFORE" "$AFTER")
  echo "   Updated: $BEFORE → $AFTER"
  echo "$CHANGED_FILES" | sed 's/^/   • /'
fi

# ── 2. Restart the service ─────────────────────────────────────────────────
echo ""
echo "🔄 Restarting frontend service..."
sudo launchctl kickstart -k system/com.pavelkletskov.flask_hockey

sleep 4

# ── 3. Health check ────────────────────────────────────────────────────────
echo ""
echo "🩺 Health check..."
HEALTH=$(curl -s --max-time 5 http://127.0.0.1:8000/ -A "Mozilla/5.0" -o /dev/null -w "%{http_code}" 2>/dev/null)
if [ "$HEALTH" = "200" ] || [ "$HEALTH" = "302" ]; then
  echo "   ✅ Service is healthy (HTTP $HEALTH)"
else
  echo "   ❌ Health check failed (HTTP $HEALTH)"
  echo "   Check logs: tail -30 /tmp/log_flask_hockey_err.log"
  exit 1
fi

echo ""
echo "🎉 Deploy complete!"
