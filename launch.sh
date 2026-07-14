#!/bin/bash
# AFFAIRS launcher — starts backend + frontend (if not already running) and opens the app.
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

BACKEND="/Users/echo/Regulation/platform/backend"
FRONTEND="/Users/echo/Regulation/platform/frontend"
PORT=5188

# 1) backend on :8000
if ! lsof -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  cd "$BACKEND" || exit 1
  nohup .venv/bin/python -m uvicorn regintel.api.main:app --host 127.0.0.1 --port 8000 \
    >/tmp/affairs-backend.log 2>&1 &
fi

# 2) frontend on :PORT
if ! lsof -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
  cd "$FRONTEND" || exit 1
  nohup npm run dev -- --port $PORT --strictPort >/tmp/affairs-frontend.log 2>&1 &
fi

# 3) wait until the page responds, then open it
for i in $(seq 1 40); do
  if curl -s -o /dev/null "http://localhost:$PORT/"; then break; fi
  sleep 0.5
done
open "http://localhost:$PORT/"
