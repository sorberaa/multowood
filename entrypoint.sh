#!/bin/bash
set -e

# Load environment variables safely
if [ -f /app/config/.env ]; then
  set -a
  source /app/config/.env
  set +a
elif [ -f config/.env ]; then
  set -a
  source config/.env
  set +a
fi

cleanup() {
  echo "[*] Получен сигнал завершения. Остановка сервисов..."
  kill -TERM "$WEBAPP_PID" 2>/dev/null || true
  kill -TERM "$BOT_PID" 2>/dev/null || true
  wait "$WEBAPP_PID" 2>/dev/null || true
  wait "$BOT_PID" 2>/dev/null || true
  exit 0
}

trap cleanup SIGINT SIGTERM

echo "[*] Запуск Web App (FastAPI/Uvicorn) на порту 8000..."
python /app/src/webapp.py &
WEBAPP_PID=$!

sleep 2

echo "[*] Запуск Telegram Bot (aiogram 3)..."
python /app/src/bot.py &
BOT_PID=$!

# Wait for either process to exit
wait -n "$WEBAPP_PID" "$BOT_PID"
cleanup
