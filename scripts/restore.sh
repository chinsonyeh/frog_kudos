#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ -z "${1:-}" ]; then
    echo "❌ 錯誤: 請指定要還原的備份檔案路徑！"
    echo "使用範例: ./scripts/restore.sh /path/to/frog_kudos_backup_20260927_120000.dump [-y]"
    exit 1
fi

BACKUP_FILE="$1"
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ 找不到備份檔案: $BACKUP_FILE"
    exit 1
fi

ENV_FILE="$ROOT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

DB_NAME="${DB_NAME:-frog_kudos}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

FORCE_RESTORE=0
for arg in "$@"; do
    if [ "$arg" = "-y" ] || [ "$arg" = "--yes" ]; then
        FORCE_RESTORE=1
    fi
done

if [ "$FORCE_RESTORE" -ne 1 ]; then
    echo "⚠️  【危險警告】即將把備份檔案還原至資料庫 [${DB_NAME}]！"
    echo "⚠️  現有所有資料將會被該備份覆蓋！"
    echo "備份檔案: $BACKUP_FILE"
    read -p "確定要繼續執行還原嗎？(請輸入 YES 確認): " CONFIRM
    if [ "$CONFIRM" != "YES" ]; then
        echo "🛑 已取消還原作業。"
        exit 0
    fi
else
    echo "⚡ 檢測到 --yes / -y 參數，略過互動式確認直接執行還原..."
fi

# 1. 還原前自動建立安全快照，避免誤操作
SNAPSHOT_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
mkdir -p "$SNAPSHOT_DIR"
PRE_RESTORE_BACKUP="${SNAPSHOT_DIR}/pre_restore_snapshot_$(date +"%Y%m%d_%H%M%S").dump"
echo "🛡️ 正在建立還原前安全快照: ${PRE_RESTORE_BACKUP} ..."

# 安全注入資料庫密碼至子程序環境變數 (避免 ps aux 明文洩漏，NFR-4)
export PGPASSWORD="${DB_PASSWORD:-}"
if [ -n "${DB_PASSWORD:-}" ]; then
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc "$DB_NAME" > "$PRE_RESTORE_BACKUP" || true
elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    sudo -n -u postgres pg_dump -Fc "$DB_NAME" > "$PRE_RESTORE_BACKUP" || true
else
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc "$DB_NAME" > "$PRE_RESTORE_BACKUP" || true
fi
chmod 600 "$PRE_RESTORE_BACKUP" 2>/dev/null || true

# 2. 執行還原 (使用 --clean --if-exists 清除舊表後乾淨恢復)
echo "🔄 開始執行資料庫還原..."
if [ -n "${DB_PASSWORD:-}" ]; then
    pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --clean --if-exists "$BACKUP_FILE"
elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    cat "$BACKUP_FILE" | sudo -n -u postgres pg_restore -d "$DB_NAME" --clean --if-exists
else
    pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --clean --if-exists "$BACKUP_FILE"
fi
unset PGPASSWORD

echo "✅ 資料庫還原成功！已恢復至備份時間點。"
