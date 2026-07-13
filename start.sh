#!/bin/bash
# Start Higgins — backend + frontend in one command

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  echo ""
  echo "Shutting down Higgins..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
  echo "Done."
  exit 0
}
trap cleanup INT TERM

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

echo ""
echo "✨ Higgins is running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop."

wait
