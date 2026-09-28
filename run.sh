#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ 找不到 .env 設定檔！請先執行 ./scripts/install.sh 進行安裝設定。"
    exit 1
fi

# 載入環境變數 (讀取 PORT, DB 等設定)
export $(grep -v '^#' "$ENV_FILE" | xargs)
PORT="${PORT:-8000}"

# 檢查虛擬環境
if [ ! -d "$ROOT_DIR/venv" ]; then
    echo "❌ 找不到 Python 虛擬環境 venv，請先執行 ./scripts/install.sh"
    exit 1
fi

source "$ROOT_DIR/venv/bin/activate"

# 檢查前端編譯資源是否存在
if [ ! -d "$ROOT_DIR/frontend/dist" ]; then
    echo "⚠️  未偵測到 frontend/dist 靜態編譯檔案，嘗試啟動..."
fi

echo "=========================================================="
echo "🐸 啟動 Frog Kudos 家庭積分獎勵系統 (Single Port Mode)"
echo "📍 服務監聽埠號: ${PORT}"
echo "🌐 本機瀏覽請開啟: http://localhost:${PORT}"
echo "📱 區域網路內其他裝置請開啟: http://<主機區域IP>:${PORT}"
echo "=========================================================="

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --proxy-headers
