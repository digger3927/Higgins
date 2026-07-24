#!/bin/bash
# Start Higgins — backend + frontend in one command

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  echo ""
  echo "Shutting down Higgins..."
  kill $BACKEND_PID $FRONTEND_PID $SEARXNG_PID $LOCALTUNNEL_PID 2>/dev/null
  wait $BACKEND_PID $FRONTEND_PID $SEARXNG_PID $LOCALTUNNEL_PID 2>/dev/null
  echo "Done."
  exit 0
}
trap cleanup INT TERM

# Start SearXNG
echo "Starting SearXNG..."
cd "$SCRIPT_DIR/searxng"
./start_searxng.sh > /dev/null 2>&1 &
SEARXNG_PID=$!

# Start backend
echo "Starting backend..."
cd "$SCRIPT_DIR/backend"
./venv/bin/python main.py &
BACKEND_PID=$!

# Wait a moment for backend to be ready
sleep 2

# Start frontend
echo "Starting frontend..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# Start localtunnel
echo "Starting localtunnel..."
npx localtunnel --port 8000 > /tmp/localtunnel.log 2>&1 &
LOCALTUNNEL_PID=$!

# Wait for localtunnel and update webhook
sleep 3
LT_URL=$(grep -o 'https://[^[:space:]]*\.loca\.lt' /tmp/localtunnel.log | head -n 1)

echo ""
echo "✨ Higgins is running!"
echo "   Frontend:     http://localhost:5173"
echo "   Backend:      http://localhost:8000"
echo "   SearXNG:      http://localhost:8888"

if [ -n "$LT_URL" ]; then
    echo "   Localtunnel:  $LT_URL"
    TOKEN=$(python3 -c "import json; print(json.load(open('$SCRIPT_DIR/config.json')).get('telegram_bot_token', ''))" 2>/dev/null)
    if [ -n "$TOKEN" ]; then
        curl -s "https://api.telegram.org/bot$TOKEN/setWebhook?url=$LT_URL/api/webhooks/telegram" > /dev/null
        echo "   (Telegram Webhook automatically updated!)"
    fi
else
    echo "   Localtunnel:  Failed to start or fetch URL"
fi

echo ""
echo "Press Ctrl+C to stop."

wait
