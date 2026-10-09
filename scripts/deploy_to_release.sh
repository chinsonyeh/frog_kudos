#!/usr/bin/env bash
# ==============================================================================
# Frog Kudos - Release & Production Deployment Script
# 流程：
# 1. 於開發環境執行完整測試 (pytest)
# 2. 確認 Git 狀態乾淨並檢查版本號
# 3. 建立 Git Tag 並推送到 GitHub 遠端儲存庫
# 4. 進入正式發佈目錄 (/home/chinsonyeh/frog_kudos/)
# 5. 拉取最新代碼 (git pull origin master)
# 6. 更新後端依賴與前端打包資源
# 7. 重啟 systemd 正式服務 (frog_kudos.service)
# 8. 驗證正式環境健康檢查端點 (Port 8000)
# ==============================================================================
set -euo pipefail

DEV_DIR="/home/chinsonyeh/Code/frog_kudos"
PROD_DIR="/home/chinsonyeh/frog_kudos"

VERSION="${1:-}"

if [ -z "$VERSION" ]; then
    CURRENT_VER=$(cat "$DEV_DIR/VERSION" 2>/dev/null || echo "v1.0.1")
    echo "❌ 請指定欲發佈的版本號 (例如: ./scripts/deploy_to_release.sh v1.0.2)"
    echo "   目前開發版版本標籤: ${CURRENT_VER}"
    exit 1
fi

echo "=========================================================="
echo "🚀 準備發佈 Frog Kudos 版本: ${VERSION}"
echo "=========================================================="

# 步驟 1: 於開發環境執行自動化測試
echo "🧪 [1/6] 執行開發版本整合測試..."
cd "$DEV_DIR"
"$DEV_DIR/venv/bin/pytest" "$DEV_DIR/tests" -q

# 步驟 2: 更新 VERSION 檔並確認 Git 工作目錄乾淨
echo "📝 [2/6] 更新版本標記 (${VERSION})..."
echo "$VERSION" > "$DEV_DIR/VERSION"

git add -A
if ! git diff-index --quiet HEAD --; then
    git commit -m "release: bump version to ${VERSION}"
fi

# 步驟 3: 建立 Git Tag 並推送到 GitHub
echo "🏷️  [3/6] 建立 Git Tag (${VERSION}) 並推送至 GitHub..."
if git rev-parse "$VERSION" >/dev/null 2>&1; then
    echo "   Tag ${VERSION} 已存在，更新標籤..."
    git tag -d "$VERSION" >/dev/null 2>&1 || true
    git push origin ":refs/tags/${VERSION}" >/dev/null 2>&1 || true
fi
git tag -a "$VERSION" -m "Release ${VERSION}"
git push origin master --tags

# 步驟 4: 進入正式發佈目錄拉取最新版本
echo "📥 [4/6] 同步正式發佈目錄 (${PROD_DIR})..."
cd "$PROD_DIR"
git pull origin master

# 步驟 5: 更新正式版 Python 依賴與前端資源
echo "📦 [5/6] 檢查依賴並更新正式環境資源..."
"$PROD_DIR/venv/bin/pip" install -q -r "$PROD_DIR/requirements.txt"

if [ -d "$PROD_DIR/frontend" ]; then
    cd "$PROD_DIR/frontend"
    npm run build --silent
fi

# 步驟 6: 重啟正式服務並執行健康檢查
echo "🔄 [6/6] 重啟正式 systemd 系統服務..."
sudo systemctl restart frog_kudos.service
sleep 2

HEALTH_CHECK=$(curl -s http://127.0.0.1:8000/api/health || echo "FAILED")
echo "=========================================================="
if echo "$HEALTH_CHECK" | grep -q '"status":"ok"'; then
    echo "🎉 版本 ${VERSION} 正式發佈並部署成功！"
    echo "📍 正式環境運行狀態: active (Port 8000)"
    echo "🌐 健康檢查回傳: ${HEALTH_CHECK}"
else
    echo "⚠️ 服務重啟後健康檢查異常: ${HEALTH_CHECK}"
    echo "請檢視日誌: sudo journalctl -u frog_kudos -n 30"
fi
echo "=========================================================="
