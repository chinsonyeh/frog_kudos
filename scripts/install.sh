#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "🚀 開始執行 Frog Kudos 家庭積分獎勵系統自動化安裝..."

# 1. 檢查主機環境相依工具
echo "🔍 步驟 1/5: 檢查主機環境..."
command -v python3 >/dev/null 2>&1 || { echo "❌ 缺少 python3，請先安裝 Python 3.12+"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ 缺少 node，請先安裝 Node.js 18+"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ 缺少 npm"; exit 1; }
command -v psql >/dev/null 2>&1 || { echo "❌ 缺少 psql，請先安裝 postgresql-client"; exit 1; }
command -v pg_dump >/dev/null 2>&1 || { echo "❌ 缺少 pg_dump"; exit 1; }

# 2. 決定並驗證運行連接埠與資料庫連線參數
DEFAULT_PORT="8000"
INPUT_PORT="${PORT:-}"
INPUT_DB_HOST="${DB_HOST:-localhost}"
INPUT_DB_PORT="${DB_PORT:-5432}"
INPUT_DB_USER="${DB_USER:-postgres}"
INPUT_DB_NAME="${DB_NAME:-frog_kudos}"
INPUT_DB_PASSWORD="${DB_PASSWORD:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)
            INPUT_PORT="$2"
            shift 2
            ;;
        --db-host)
            INPUT_DB_HOST="$2"
            shift 2
            ;;
        --db-port)
            INPUT_DB_PORT="$2"
            shift 2
            ;;
        --db-user)
            INPUT_DB_USER="$2"
            shift 2
            ;;
        --db-password)
            INPUT_DB_PASSWORD="$2"
            shift 2
            ;;
        --db-name)
            INPUT_DB_NAME="$2"
            shift 2
            ;;
        -h|--help)
            echo "🐸 Frog Kudos 家庭積分獎勵系統 - 自動化安裝腳本"
            echo "用法: ./scripts/install.sh [選項]"
            echo ""
            echo "選項:"
            echo "  --port <port>             指定系統監聽連接埠 (預設: 8000)"
            echo "  --db-host <host>          PostgreSQL 主機 (預設: localhost)"
            echo "  --db-port <port>          PostgreSQL 埠號 (預設: 5432)"
            echo "  --db-user <user>          PostgreSQL 使用者 (預設: postgres)"
            echo "  --db-password <pwd>       PostgreSQL 密碼 (未提供時使用環境變數或預設值)"
            echo "  --db-name <name>          PostgreSQL 資料庫名稱 (預設: frog_kudos)"
            echo "  -h, --help                顯示此說明訊息"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

if [ -z "$INPUT_PORT" ] && [ -t 0 ]; then
    echo "🔌 連接埠配置 (Port Configuration)："
    read -p "   請輸入 Frog Kudos 系統運行的連接埠 [預設: ${DEFAULT_PORT}]: " USER_CHOICE
    CHOSEN_PORT="${USER_CHOICE:-$DEFAULT_PORT}"
else
    CHOSEN_PORT="${INPUT_PORT:-$DEFAULT_PORT}"
fi

# 驗證 Port 合法性 (1-65535)
if ! [[ "$CHOSEN_PORT" =~ ^[0-9]+$ ]] || [ "$CHOSEN_PORT" -lt 1 ] || [ "$CHOSEN_PORT" -gt 65535 ]; then
    echo "❌ 錯誤: 連接埠 ${CHOSEN_PORT} 不合法，必須為 1 到 65535 之間的整數！"
    exit 1
fi

# 檢查 Port 是否已被佔用
if command -v ss >/dev/null 2>&1 && ss -tuln | grep -q ":${CHOSEN_PORT} "; then
    echo "⚠️  警告: 連接埠 ${CHOSEN_PORT} 目前已被其他程式佔用，請留意後續啟動是否會發生衝突！"
fi

# 3. 建立或更新 .env 設定檔
if [ ! -f "$ROOT_DIR/.env" ]; then
    echo "📝 步驟 2/5: 建立環境設定檔 (.env，設定 PORT=${CHOSEN_PORT})..."

    DB_PASS="${INPUT_DB_PASSWORD:-${DB_PASSWORD:-postgres}}"

    if [ -n "$DB_PASS" ]; then
        DB_URL="postgresql+asyncpg://${INPUT_DB_USER}:${DB_PASS}@${INPUT_DB_HOST}:${INPUT_DB_PORT}/${INPUT_DB_NAME}"
    else
        DB_URL="postgresql+asyncpg://${INPUT_DB_USER}@${INPUT_DB_HOST}:${INPUT_DB_PORT}/${INPUT_DB_NAME}"
    fi

    cat << EOF > "$ROOT_DIR/.env"
DATABASE_URL=${DB_URL}
DB_NAME=${INPUT_DB_NAME}
DB_USER=${INPUT_DB_USER}
DB_PASSWORD=${DB_PASS}
DB_HOST=${INPUT_DB_HOST}
DB_PORT=${INPUT_DB_PORT}
PORT=${CHOSEN_PORT}
BACKUP_DIR=${ROOT_DIR}/backups
AUTO_BACKUP=true
BACKUP_RETENTION_COUNT=10
PARENT_DEFAULT_PIN=0000
GITHUB_REPO=chinsonyeh/frog_kudos
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
EOF
else
    echo "📝 步驟 2/5: 更新現有 .env 設定檔 (PORT=${CHOSEN_PORT})..."
    if grep -q "^PORT=" "$ROOT_DIR/.env"; then
        sed -i "s/^PORT=.*/PORT=${CHOSEN_PORT}/" "$ROOT_DIR/.env"
    else
        echo "PORT=${CHOSEN_PORT}" >> "$ROOT_DIR/.env"
    fi
fi

# 鎖定 .env 檔案權限為 600 (僅擁有者可讀寫，防止同機窺探 NFR-4)
chmod 600 "$ROOT_DIR/.env"

# 載入 .env 變數以供後續步驟使用
export $(grep -v '^#' "$ROOT_DIR/.env" | xargs)
DB_NAME="${DB_NAME:-frog_kudos}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_PASSWORD="${DB_PASSWORD:-}"

# 確保本地版本標識檔存在
[ ! -f "$ROOT_DIR/VERSION" ] && echo "v1.0.0" > "$ROOT_DIR/VERSION"

# 4. 初始化 PostgreSQL frog_kudos 資料庫結構
echo "🐘 步驟 3/5: 初始化資料庫結構..."
export PGPASSWORD="${DB_PASSWORD}"

# 自動防呆檢查資料庫是否存在，若無則自動建立
if [ -n "${DB_PASSWORD}" ]; then
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" 2>/dev/null | grep -q 1 || \
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || true
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$ROOT_DIR/schema.sql"
elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    sudo -n -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" 2>/dev/null | grep -q 1 || \
        sudo -n -u postgres psql -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || true
    cat "$ROOT_DIR/schema.sql" | sudo -n -u postgres psql -d "$DB_NAME"
else
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" 2>/dev/null | grep -q 1 || \
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || true
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$ROOT_DIR/schema.sql"
fi
unset PGPASSWORD

# 5. 建置後端 Python 虛擬環境
echo "🐍 步驟 4/5: 建置 Python 虛擬環境並安裝依賴..."
cd "$ROOT_DIR"
if [ ! -d "venv" ]; then
    if python3 -m venv venv 2>/dev/null; then
        echo "   使用 python3 -m venv 建立虛擬環境成功"
    elif command -v virtualenv >/dev/null 2>&1; then
        echo "   偵測到非原生符號連結檔案系統 (如 exFAT)，使用 virtualenv --always-copy 建立..."
        virtualenv --always-copy venv
    else
        echo "   使用 python3 -m venv --copies 建立..."
        python3 -m venv --copies venv
    fi
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 6. 前端相依安裝與打包編譯 (支援單一 Port 託管)
echo "🎨 步驟 5/5: 檢查前端資源..."
if [ -f "$ROOT_DIR/frontend/package.json" ]; then
    echo "   安裝前端套件並編譯生產環境資源 (npm run build)..."
    cd "$ROOT_DIR/frontend"
    npm install --no-bin-links || npm install
    npm run build
else
    echo "   ℹ️ 前端源碼目錄尚未建置，略過靜態編譯 (將於 Phase 3 前端開發時打包)"
fi

echo "🎉 Frog Kudos 安裝與初始化完成！"
echo "👉 執行 ./run.sh 即可啟動系統 (瀏覽器開啟: http://localhost:${CHOSEN_PORT})"
