#!/usr/bin/env bash
set -euo pipefail

# 載入環境變數
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

DB_NAME="${DB_NAME:-frog_kudos}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# 取得指定目標路徑 (第 1 個引數)，若無指定則預設讀取 BACKUP_DIR 或 $ROOT_DIR/backups
TARGET_DIR="${1:-${BACKUP_DIR:-$ROOT_DIR/backups}}"
mkdir -p "$TARGET_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${TARGET_DIR}/frog_kudos_backup_${TIMESTAMP}.dump"

echo "📦 開始備份資料庫 [${DB_NAME}] 至目標路徑: ${BACKUP_FILE} ..."
# 安全注入資料庫密碼至子程序環境變數 (避免 ps aux 明文洩漏，NFR-4)
export PGPASSWORD="${DB_PASSWORD:-}"
if [ -n "${DB_PASSWORD:-}" ]; then
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc "$DB_NAME" > "$BACKUP_FILE"
elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    sudo -n -u postgres pg_dump -Fc "$DB_NAME" > "$BACKUP_FILE"
else
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc "$DB_NAME" > "$BACKUP_FILE"
fi
unset PGPASSWORD

# 鎖定備份檔案權限為 600
chmod 600 "$BACKUP_FILE"

FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "✅ 備份成功！檔案大小: ${FILE_SIZE}"
echo "📍 完整備份路徑: ${BACKUP_FILE}"

# 執行備份保留輪替 (Retention Cleanup，預設保留最新 10 份)
RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-${RETENTION_COUNT:-10}}"
BACKUP_LIST=$(ls -1t "$TARGET_DIR"/frog_kudos_backup_*.dump 2>/dev/null || true)
TOTAL_BACKUPS=$(echo "$BACKUP_LIST" | grep -c . || true)
if [ "$TOTAL_BACKUPS" -gt "$RETENTION_COUNT" ]; then
    echo "🧹 執行備份輪替清理 (超過保留上限 ${RETENTION_COUNT} 份)..."
    echo "$BACKUP_LIST" | tail -n +$((RETENTION_COUNT + 1)) | while IFS= read -r old_file; do
        if [ -f "$old_file" ]; then
            echo "   🗑️ 刪除過期舊備份: $(basename "$old_file")"
            rm -f "$old_file"
        fi
    done
fi
