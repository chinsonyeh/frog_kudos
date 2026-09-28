#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PACKAGE_ARG="${1:-}"  # 可為本地檔案路徑或留空自動從 GitHub 取得
TMP_DIR="/tmp/frog_kudos_upgrade_$(date +%s)"
mkdir -p "$TMP_DIR"

ENV_FILE="$ROOT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

DB_NAME="${DB_NAME:-frog_kudos}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
GITHUB_REPO="${GITHUB_REPO:-chinsonyeh/frog_kudos}"

echo "🔄 開始進行 Frog Kudos 系統平滑升級..."

# 1. 強制升級前備份資料庫
echo "📦 步驟 1/6: 執行升級前強制資料庫備份..."
"$ROOT_DIR/scripts/backup.sh"

# 2. 獲取升級套件 (自動自 GitHub 下載或使用本地套件)
if [ -n "$PACKAGE_ARG" ] && [ -f "$PACKAGE_ARG" ]; then
    echo "📥 步驟 2/6: 使用指定的本地發行包: $PACKAGE_ARG"
    TARGET_TAR="$PACKAGE_ARG"
else
    echo "🌐 步驟 2/6: 查詢 GitHub Releases 最新版本..."
    LATEST_JSON=$(curl -s "https://api.github.com/repos/${GITHUB_REPO}/releases/latest")
    LATEST_TAG=$(echo "$LATEST_JSON" | grep -oP '"tag_name": "\K[^"]+')
    DOWNLOAD_URL=$(echo "$LATEST_JSON" | grep -oP '"browser_download_url": "\Khttps://[^"]+\.tar\.gz')
    
    if [ -z "$LATEST_TAG" ] || [ -z "$DOWNLOAD_URL" ]; then
        echo "❌ 無法從 GitHub 取得最新 Release 資訊，請檢查網路或手動下載套件升級！"
        exit 1
    fi
    
    LOCAL_VERSION=$(cat "$ROOT_DIR/VERSION" 2>/dev/null || echo "v0.0.0")
    echo "目前版本: $LOCAL_VERSION ➔ 最新版本: $LATEST_TAG"
    
    TARGET_TAR="${TMP_DIR}/frog_kudos-${LATEST_TAG}.tar.gz"
    echo "⬇️ 下載發行套件: $DOWNLOAD_URL ..."
    curl -L "$DOWNLOAD_URL" -o "$TARGET_TAR"
fi

# 3. 解壓縮新版本並覆蓋程式檔案 (保留 .env, backups, venv 與安全替換 upgrade.sh)
echo "📂 步驟 3/6: 解壓縮並套用新版本檔案..."
# 先排除 scripts/upgrade.sh 解壓，避免 Linux Bash 執行時原地覆蓋引發 byte offset 錯位崩潰
tar -xzvf "$TARGET_TAR" -C "$ROOT_DIR" --exclude='scripts/upgrade.sh'
# 透過原子替換 (Atomic Move) 安全更新 upgrade.sh
tar -xzvf "$TARGET_TAR" -C "$TMP_DIR" scripts/upgrade.sh
cp "$TMP_DIR/scripts/upgrade.sh" "$ROOT_DIR/scripts/upgrade.sh.new"
mv -f "$ROOT_DIR/scripts/upgrade.sh.new" "$ROOT_DIR/scripts/upgrade.sh"
chmod +x "$ROOT_DIR/scripts/upgrade.sh"

# 4. 更新 Python 虛擬環境套件
echo "🐍 步驟 4/6: 更新後端 Python 套件依賴..."
if [ -d "$ROOT_DIR/venv" ]; then
    source "$ROOT_DIR/venv/bin/activate"
    pip install -r "$ROOT_DIR/requirements.txt"
fi

# 5. 資料庫結構遷移 (Migration - 執行冪等性 DDL)
echo "🐘 步驟 5/6: 檢查並執行資料庫結構遷移..."
export PGPASSWORD="${DB_PASSWORD:-}"
if [ -n "${DB_PASSWORD:-}" ]; then
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$ROOT_DIR/schema.sql" || true
elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    cat "$ROOT_DIR/schema.sql" | sudo -n -u postgres psql -d "$DB_NAME" || true
else
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$ROOT_DIR/schema.sql" || true
fi
unset PGPASSWORD

# 6. 清理暫存檔並完成
rm -rf "$TMP_DIR"
NEW_VER=$(cat "$ROOT_DIR/VERSION" 2>/dev/null || echo "unknown")
echo "🎉 系統已成功升級至版本: $NEW_VER！"
echo "👉 若以背景服務運行，請執行重啟命令完成切換。"
