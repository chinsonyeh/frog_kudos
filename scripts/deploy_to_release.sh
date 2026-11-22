#!/usr/bin/env bash
# ==============================================================================
# Frog Kudos - Release & Production Deployment Script
# 用法：
#   ./scripts/deploy_to_release.sh <vX.Y.Z> [--force-tag] [--dry-run]
#
# 標準流程：
# 0. 前置防呆檢查（版號格式、非互動 sudo、雙目錄乾淨與 master 分支、遠端同步、
#    DEV 資料庫防誤連正式庫、ReleaseNote.md 檢查、既有 Tag 防覆寫）
# 1. 於開發環境執行完整整合測試 (pytest)
# 2. 更新 VERSION 與 frontend/package.json 版號並明確提交（禁用 git add -A）
# 3. 建立 Annotated Git Tag 並推送至 GitHub
# 4. 強制備份正式環境資料庫 (scripts/backup.sh)
# 5. 同步正式目錄 (git pull --ff-only)，若 schema.sql 有變動則安全套用冪等遷移
# 6. 更新後端依賴、偵測前端依賴變更自動補跑 npm install 並建置前端資源
# 7. 重啟正式服務 (frog_kudos.service) 並重試驗證健康檢查與版號（失敗回傳 exit 1）
# ==============================================================================
set -euo pipefail

DEV_DIR="/home/chinsonyeh/Code/frog_kudos"
PROD_DIR="/home/chinsonyeh/frog_kudos"

VERSION=""
FORCE_TAG=0
DRY_RUN=0

for arg in "$@"; do
    case "$arg" in
        --force-tag)
            FORCE_TAG=1
            ;;
        --dry-run)
            DRY_RUN=1
            ;;
        -h|--help)
            echo "用法: $0 <vX.Y.Z> [--force-tag] [--dry-run]"
            exit 0
            ;;
        *)
            if [ -z "$VERSION" ]; then
                VERSION="$arg"
            else
                echo "❌ 未知或重複的參數: $arg"
                echo "用法: $0 <vX.Y.Z> [--force-tag] [--dry-run]"
                exit 1
            fi
            ;;
    esac
done

if [ -z "$VERSION" ]; then
    CURRENT_VER=$(cat "$DEV_DIR/VERSION" 2>/dev/null || echo "v1.0.0")
    echo "❌ 請指定欲發佈的版本號 (例如: ./scripts/deploy_to_release.sh v1.0.6)"
    echo "   目前開發版版本標籤: ${CURRENT_VER}"
    exit 1
fi

if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "❌ 版本號格式錯誤: '${VERSION}'（必須符合 vX.Y.Z 語意化格式，例如 v1.0.6）"
    exit 1
fi

SEMVER_NUM="${VERSION#v}"

echo "=========================================================="
echo "🚀 準備發佈 Frog Kudos 版本: ${VERSION}"
if [ "$DRY_RUN" -eq 1 ]; then
    echo "🧪 模式: DRY-RUN（僅執行前置防呆檢查，不修改檔案或重啟服務）"
fi
echo "=========================================================="

# ------------------------------------------------------------------------------
# 步驟 0: 前置防呆檢查 (Pre-flight Guardrails)
# ------------------------------------------------------------------------------
echo "🛡️  [0/7] 執行發版前置防呆檢查..."

# 0.1 檢查非互動 sudo 權限，避免 systemctl restart 卡住超時
if ! sudo -n true 2>/dev/null; then
    echo "❌ 無法以非互動模式執行 sudo（sudo -n 失敗），請確認 sudoers 設定後重試。"
    exit 1
fi

# 0.2 檢查開發與正式目錄皆存在、位於 master 分支且工作區完全乾淨
for dir_path in "$DEV_DIR" "$PROD_DIR"; do
    if [ ! -d "$dir_path/.git" ]; then
        echo "❌ 找不到有效的 Git 目錄: ${dir_path}"
        exit 1
    fi
    cur_branch=$(git -C "$dir_path" rev-parse --abbrev-ref HEAD)
    if [ "$cur_branch" != "master" ]; then
        echo "❌ 目錄 ${dir_path} 目前位於分支 '${cur_branch}'，發版必須在 'master' 分支！"
        exit 1
    fi
    if [ -n "$(git -C "$dir_path" status --porcelain)" ]; then
        echo "❌ 目錄 ${dir_path} 工作區不乾淨，請先清理或提交後再發版："
        git -C "$dir_path" status -sb
        exit 1
    fi
done

# 0.3 同步遠端資訊並確認開發目錄未落後 origin/master
git -C "$DEV_DIR" fetch origin --quiet
BEHIND_COUNT=$(git -C "$DEV_DIR" rev-list --count HEAD..origin/master)
if [ "$BEHIND_COUNT" -gt 0 ]; then
    echo "❌ 開發目錄落後 origin/master 共 ${BEHIND_COUNT} 筆提交，請先執行 git pull origin master！"
    exit 1
fi

# 0.4 防誤連正式庫檢查（確保 DEV pytest 絕不連向正式庫 frog_kudos）
if [ ! -f "$DEV_DIR/.env" ]; then
    echo "❌ 找不到開發環境設定檔: ${DEV_DIR}/.env"
    exit 1
fi
DEV_DB_NAME=$(
    set -a
    # shellcheck disable=SC1090
    source "$DEV_DIR/.env"
    set +a
    echo "${DB_NAME:-}"
)
if [ -z "$DEV_DB_NAME" ] || [ "$DEV_DB_NAME" = "frog_kudos" ]; then
    echo "❌ 安全攔截：開發目錄 .env 的 DB_NAME='${DEV_DB_NAME}' 不得為空或正式庫 'frog_kudos'！"
    echo "   pytest 會執行資料清理，請確認 ${DEV_DIR}/.env 指向測試庫（例如 frog_kudos_dev）。"
    exit 1
fi

# 0.5 檢查 ReleaseNote.md 是否已包含本次版本條目
if [ ! -f "$DEV_DIR/ReleaseNote.md" ] || ! grep -Fq "[${VERSION}]" "$DEV_DIR/ReleaseNote.md"; then
    echo "❌ ${DEV_DIR}/ReleaseNote.md 尚未包含 [${VERSION}] 的版本發佈日誌！"
    echo "   請先於本機補齊 ReleaseNote.md、提交推送 GitHub 並於開發目錄 git pull 後再發版。"
    exit 1
fi

# 0.6 檢查 Tag 是否已存在（預設禁止覆寫，僅明確傳入 --force-tag 時允許）
TAG_EXISTS_LOCAL=0
TAG_EXISTS_REMOTE=0
if git -C "$DEV_DIR" rev-parse -q --verify "refs/tags/${VERSION}" >/dev/null 2>&1; then
    TAG_EXISTS_LOCAL=1
fi
if git -C "$DEV_DIR" ls-remote --tags origin "refs/tags/${VERSION}" | grep -Fq "refs/tags/${VERSION}"; then
    TAG_EXISTS_REMOTE=1
fi
if { [ "$TAG_EXISTS_LOCAL" -eq 1 ] || [ "$TAG_EXISTS_REMOTE" -eq 1 ]; } && [ "$FORCE_TAG" -ne 1 ]; then
    echo "❌ Git Tag '${VERSION}' 已存在（local=${TAG_EXISTS_LOCAL}, remote=${TAG_EXISTS_REMOTE}）！"
    echo "   為保護歷史發佈紀錄，預設禁止覆寫既有 Tag；如確需覆寫請明確加上 --force-tag。"
    exit 1
fi

# 記錄正式目錄發版前 Commit（供差異偵測與失敗回滾用）
PREV_PROD_COMMIT=$(git -C "$PROD_DIR" rev-parse HEAD)
echo "✅ 前置檢查全數通過！（DEV DB: ${DEV_DB_NAME}｜PROD 當前 Commit: ${PREV_PROD_COMMIT:0:7}）"

if [ "$DRY_RUN" -eq 1 ]; then
    echo "🎉 DRY-RUN 檢查完成，未執行任何變更。"
    exit 0
fi

# ------------------------------------------------------------------------------
# 步驟 1: 於開發環境執行自動化整合測試
# ------------------------------------------------------------------------------
echo "🧪 [1/7] 執行開發版本整合測試 (pytest)..."
cd "$DEV_DIR"
"$DEV_DIR/venv/bin/pytest" "$DEV_DIR/tests" -q

# ------------------------------------------------------------------------------
# 步驟 2: 更新 VERSION 與 frontend/package.json 並明確提交（禁用 git add -A）
# ------------------------------------------------------------------------------
echo "📝 [2/7] 更新版本標記 (${VERSION}) 與 frontend/package.json (${SEMVER_NUM})..."
printf '%s\n' "$VERSION" > "$DEV_DIR/VERSION"

if [ -f "$DEV_DIR/frontend/package.json" ]; then
    python3 - "$DEV_DIR/frontend/package.json" "$SEMVER_NUM" <<'PY'
import json, sys
path, ver = sys.argv[1], sys.argv[2]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
if data.get("version") != ver:
    data["version"] = ver
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
PY
    git add VERSION frontend/package.json
else
    git add VERSION
fi

if ! git diff --cached --quiet; then
    git commit -m "release: bump version to ${VERSION}"
fi

# ------------------------------------------------------------------------------
# 步驟 3: 建立 Annotated Git Tag 並推送至 GitHub
# ------------------------------------------------------------------------------
echo "🏷️  [3/7] 建立 Git Tag (${VERSION}) 並推送至 GitHub..."
if [ "$FORCE_TAG" -eq 1 ]; then
    if [ "$TAG_EXISTS_LOCAL" -eq 1 ]; then
        echo "   ⚠️  --force-tag 已啟用，移除本地舊標籤 ${VERSION}..."
        git tag -d "$VERSION" >/dev/null
    fi
    if [ "$TAG_EXISTS_REMOTE" -eq 1 ]; then
        echo "   ⚠️  --force-tag 已啟用，移除遠端舊標籤 ${VERSION}..."
        git push origin ":refs/tags/${VERSION}" >/dev/null
    fi
fi
git tag -a "$VERSION" -m "Release ${VERSION}"
git push origin master
git push origin "refs/tags/${VERSION}"

# ------------------------------------------------------------------------------
# 步驟 4: 發版前強制備份正式環境資料庫
# ------------------------------------------------------------------------------
echo "💾 [4/7] 執行正式環境資料庫發版前強制備份..."
BACKUP_OUTPUT=$("$PROD_DIR/scripts/backup.sh")
echo "$BACKUP_OUTPUT"
LATEST_BACKUP=$(echo "$BACKUP_OUTPUT" | grep '完整備份路徑:' | sed 's/.*完整備份路徑:[[:space:]]*//' | tail -n 1 || true)

# ------------------------------------------------------------------------------
# 步驟 5: 同步正式目錄並檢查 DB Schema 變更
# ------------------------------------------------------------------------------
echo "📥 [5/7] 同步正式發佈目錄 (${PROD_DIR})..."
cd "$PROD_DIR"
git pull --ff-only origin master

if git diff --name-only "$PREV_PROD_COMMIT"..HEAD -- schema.sql | grep -q '^schema\.sql$'; then
    echo "🐘 偵測到 schema.sql 有變更，套用冪等資料庫遷移 (ON_ERROR_STOP=1)..."
    (
        set -euo pipefail
        if [ -f "$PROD_DIR/.env" ]; then
            set -a
            # shellcheck disable=SC1090
            source "$PROD_DIR/.env"
            set +a
        fi
        DB_NAME="${DB_NAME:-frog_kudos}"
        DB_USER="${DB_USER:-postgres}"
        DB_HOST="${DB_HOST:-localhost}"
        DB_PORT="${DB_PORT:-5432}"
        export PGPASSWORD="${DB_PASSWORD:-}"
        if [ -n "${DB_PASSWORD:-}" ]; then
            psql -v ON_ERROR_STOP=1 -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$PROD_DIR/schema.sql"
        elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
            sudo -n -u postgres psql -v ON_ERROR_STOP=1 -d "$DB_NAME" < "$PROD_DIR/schema.sql"
        else
            psql -v ON_ERROR_STOP=1 -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$PROD_DIR/schema.sql"
        fi
        unset PGPASSWORD
    )
else
    echo "🐘 schema.sql 無異動，略過資料庫結構遷移。"
fi

# ------------------------------------------------------------------------------
# 步驟 6: 更新後端 Python 依賴與前端套件／建置資源
# ------------------------------------------------------------------------------
echo "📦 [6/7] 檢查依賴並更新正式環境資源..."
"$PROD_DIR/venv/bin/pip" install -q -r "$PROD_DIR/requirements.txt"

if [ -d "$PROD_DIR/frontend" ]; then
    cd "$PROD_DIR/frontend"
    NEED_NPM_INSTALL=0
    if [ ! -d "$PROD_DIR/frontend/node_modules" ]; then
        NEED_NPM_INSTALL=1
    elif git -C "$PROD_DIR" diff --name-only "$PREV_PROD_COMMIT"..HEAD -- frontend/package-lock.json | grep -q 'package-lock\.json'; then
        NEED_NPM_INSTALL=1
    elif python3 - "$PROD_DIR" "$PREV_PROD_COMMIT" <<'PY'
import json, subprocess, sys
prod_dir, prev_commit = sys.argv[1], sys.argv[2]
try:
    old_raw = subprocess.check_output(["git", "-C", prod_dir, "show", f"{prev_commit}:frontend/package.json"], text=True)
    new_raw = subprocess.check_output(["git", "-C", prod_dir, "show", "HEAD:frontend/package.json"], text=True)
    old_pkg, new_pkg = json.loads(old_raw), json.loads(new_raw)
    changed = (old_pkg.get("dependencies") != new_pkg.get("dependencies")) or (old_pkg.get("devDependencies") != new_pkg.get("devDependencies"))
    sys.exit(0 if changed else 1)
except Exception:
    sys.exit(0)
PY
    then
        NEED_NPM_INSTALL=1
    fi

    if [ "$NEED_NPM_INSTALL" -eq 1 ]; then
        echo "   📥 偵測到前端套件相依變更，執行 npm install..."
        npm install --no-audit --no-fund --silent
    fi
    npm run build --silent
fi

# ------------------------------------------------------------------------------
# 步驟 7: 重啟正式服務並嚴格重試驗證健康檢查與版本號
# ------------------------------------------------------------------------------
echo "🔄 [7/7] 重啟正式 systemd 系統服務並驗證健康檢查..."
sudo -n systemctl restart frog_kudos.service

HEALTH_OK=0
HEALTH_CHECK=""
for attempt in $(seq 1 20); do
    sleep 1
    HEALTH_CHECK=$(curl -fsS --max-time 3 http://127.0.0.1:8000/api/health 2>/dev/null || true)
    if echo "$HEALTH_CHECK" | grep -Fq '"status":"ok"' && echo "$HEALTH_CHECK" | grep -Fq "\"version\":\"${VERSION}\""; then
        HEALTH_OK=1
        break
    fi
    echo "   ⏳ 等待服務就緒 (${attempt}/20)..."
done

echo "=========================================================="
if [ "$HEALTH_OK" -eq 1 ]; then
    echo "🎉 版本 ${VERSION} 正式發佈並部署成功！"
    echo "📍 正式環境運行狀態: active (Port 8000)"
    echo "🌐 健康檢查回傳: ${HEALTH_CHECK}"
    echo "💾 發版前備份檔: ${LATEST_BACKUP:-已存於 ${PROD_DIR}/backups}"
    echo "👉 請記得回本機開發區執行: git pull origin master --tags"
    echo "=========================================================="
else
    echo "❌ 服務重啟後健康檢查失敗或版本不符！"
    echo "   預期版本: ${VERSION}"
    echo "   實際回傳: ${HEALTH_CHECK:-<無回應>}"
    echo "   檢視日誌: sudo journalctl -u frog_kudos -n 50 --no-pager"
    echo "   回滾指引:"
    echo "     cd ${PROD_DIR} && git reset --hard ${PREV_PROD_COMMIT}"
    echo "     cd ${PROD_DIR}/frontend && npm run build && sudo -n systemctl restart frog_kudos.service"
    if [ -n "${LATEST_BACKUP:-}" ]; then
        echo "     (如需還原資料庫) ${PROD_DIR}/scripts/restore.sh ${LATEST_BACKUP}"
    fi
    echo "=========================================================="
    exit 1
fi
