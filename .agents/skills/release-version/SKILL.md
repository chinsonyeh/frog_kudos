---
name: release-version
description: >-
  Frog Kudos 專案標準進版與正式環境發佈流程（Release Workflow）。當使用者要求「進版」、「發版」、「部署到正式環境」、「更新版本號 / ReleaseNote.md / Git Tag」或執行 `scripts/deploy_to_release.sh` 時必須載入並嚴格遵循本技能。
---

# Frog Kudos 標準進版與發佈流程（Release Workflow）

本技能定義 **Frog Kudos** 從準備進版、補齊 `ReleaseNote.md`、測試驗證、發版前備份、正式部署、失敗回滾到四方同步的完整標準作業程序（SOP）。

> **發佈機制定位說明**：本專案正式升級以 **GitHub `master` + Annotated Git Tag + `scripts/deploy_to_release.sh`** 為主。Web 後台「系統版本與升級」分頁（`/api/system/version`）查詢的是 GitHub Releases（含 `.tar.gz` asset）；僅推送 Git Tag 時不會觸發 Web UI 遠端更新提示，若未來需讓 Web UI 顯示新版可另外於 GitHub 建立對應 Release 並附上發行套件。

## 0. 環境對照與不可違反鐵則

| 環境 | 主機與路徑 | 服務名稱 | 本機健康檢查 | 對外 HTTPS 網址 |
| :--- | :--- | :--- | :--- | :--- |
| **本機開發區** | `d:\Users\Chinson\Documents\Code\frog_kudos`（Windows PowerShell） | — | — | — |
| **GitHub 倉庫** | `git@github.com:chinsonyeh/frog_kudos.git`（`master`） | — | — | — |
| **開發 / 測試環境** | `192.168.50.3:/home/chinsonyeh/Code/frog_kudos`（Linux Bash） | `frog_kudos_dev.service` | `http://127.0.0.1:8001/api/health` | `https://kudos.chinson.idv.tw:8443` |
| **正式環境** | `192.168.50.3:/home/chinsonyeh/frog_kudos`（Linux Bash） | `frog_kudos.service` | `http://127.0.0.1:8000/api/health` | `https://kudos.chinson.idv.tw` |

- **必須先獲同意**：未經使用者明確確認「部署正式環境／進版」，僅可部署開發測試環境（`frog_kudos_dev`）。
- **一律走 GitHub**：所有程式碼與文件異動須於本機提交並推送至 GitHub，再於 `192.168.50.3` 執行 `git pull`；嚴禁直接跨機覆寫。
- **保護未追蹤資料**：遠端嚴禁誤刪 `.env`、`uploads/`、`backups/`、`venv/`。
- **嚴禁洩漏機密**：提交內容、`ReleaseNote.md` 與回應中皆不可出現密碼、PIN、LINE Token 或 Cloudflare API Token。

---

## 階段 1：版本確認與發佈文件更新（本機 Windows PowerShell・發版前必做）

1. **確認目前版本與本次變更範圍**（注意：PowerShell 必須以雙引號包住 `"$(...)..HEAD"` 避免參數拆解錯誤）：
   ```powershell
   cat VERSION
   $prevTag = git describe --tags --abbrev=0
   git log "$prevTag..HEAD" --oneline
   ```
   - 依語意化版本規則決定新版本號 `vX.Y.Z`（格式須符合 `^v[0-9]+\.[0-9]+\.[0-9]+$`）。
2. **更新 `ReleaseNote.md`（強制必做；`deploy_to_release.sh` 會自動檢查）**：
   - 於根目錄 `ReleaseNote.md` 最上方新增 `## 🚀 [vX.Y.Z] - YYYY-MM-DD` 區塊，風格與既有版本保持一致。
   - 依本次 `git log` 內容清楚分類撰寫（新增核心功能 / 介面與體驗優化 / 問題修正 / 資料庫或維運文件變更）。
3. **檢查資料庫遷移（`schema.sql`）與關聯設計文件**：
   ```powershell
   git diff "$prevTag..HEAD" -- schema.sql frontend/package.json frontend/package-lock.json
   ```
   - 若 `schema.sql` 有變更：務必確認所有 DDL 皆為**完全冪等**（`IF NOT EXISTS`、`ON CONFLICT ... DO NOTHING`，**絕不可使用會覆寫使用者自訂設定的 `DO UPDATE`**），並已先在開發庫 `frog_kudos_dev` 實測通過；`deploy_to_release.sh` 將於備份正式庫後自動以 `psql -v ON_ERROR_STOP=1` 套用變更。
   - 若涉及資料表、API 規格或重要架構變更，同步更新 `DESIGN.md` 與 `REQUIREMENT.md`。
   - `frontend/package.json` 的 `"version"` 欄位將由 `deploy_to_release.sh` 步驟 2 自動與 `VERSION` 同步，並於正式環境偵測依賴變更自動執行 `npm install`。
4. **品質把關（建議）**：
   - 若本次包含程式碼或腳本異動且尚未審查，先呼叫專案 `reviewer` Agent 確認無 Blocker／Major 遺留。

---

## 階段 2：本機提交、推送 GitHub 與開發環境最後確認

1. **本機提交並推送至 GitHub**（本機 PowerShell）：
   ```powershell
   git status -sb
   git add ReleaseNote.md <其他異動檔案>
   git commit -m "docs: 更新 vX.Y.Z 版本發佈日誌"
   git push origin master
   ```
2. **確認開發環境已同步最新提交並通過實機驗證**（遠端 Linux SSH）：
   ```bash
   ssh -o BatchMode=yes chinsonyeh@192.168.50.3 'cd /home/chinsonyeh/Code/frog_kudos && git pull --ff-only origin master && git status -sb'
   ```
   - 若程式碼尚未在開發環境建置驗證，先於 `/home/chinsonyeh/Code/frog_kudos/frontend` 執行 `npm run build`（有新依賴先跑 `npm install`）並 `sudo -n systemctl restart frog_kudos_dev.service`，確認 `https://kudos.chinson.idv.tw:8443` 驗證無誤後，再進入階段 3。

---

## 階段 3：執行正式環境發版（遠端 Linux SSH）

1. **（建議）先跑 `--dry-run` 確認前置防呆全數通過**：
   ```bash
   ssh -o BatchMode=yes chinsonyeh@192.168.50.3 'cd /home/chinsonyeh/Code/frog_kudos && ./scripts/deploy_to_release.sh vX.Y.Z --dry-run'
   ```
   腳本前置檢查會自動把關：
   - 版號符合 `^v[0-9]+\.[0-9]+\.[0-9]+$`
   - 非互動 `sudo -n true` 可用
   - 開發與正式目錄皆位於 `master` 分支且工作區完全乾淨
   - 開發目錄未落後 `origin/master`
   - 開發目錄 `.env` 的 `DB_NAME` 不得為正式庫 `frog_kudos`（防 `pytest` 誤刪正式資料）
   - `ReleaseNote.md` 已包含 `[vX.Y.Z]`
   - Git Tag `vX.Y.Z` 尚未存在（禁止誤覆寫既有 Tag，僅明確傳入 `--force-tag` 時允許）
2. **執行一鍵正式發版腳本**：
   ```bash
   ssh -o BatchMode=yes chinsonyeh@192.168.50.3 'cd /home/chinsonyeh/Code/frog_kudos && ./scripts/deploy_to_release.sh vX.Y.Z'
   ```
   腳本會自動依序完成 7 個步驟（任一步驟失敗皆立即中止並回傳非零 Exit Code）：
   1. 於開發環境執行完整 `pytest` 整合測試。
   2. 更新 `VERSION` 與 `frontend/package.json` 版號，明確僅 `git add VERSION frontend/package.json` 提交（禁用 `git add -A`）。
   3. 建立 Annotated Git Tag `vX.Y.Z` 並推送 `master` 與 Tag 至 GitHub。
   4. **強制備份正式資料庫**（呼叫 `/home/chinsonyeh/frog_kudos/scripts/backup.sh`）並記錄備份檔路徑與發版前 `PREV_PROD_COMMIT`。
   5. 於正式目錄執行 `git pull --ff-only origin master`；若偵測到 `schema.sql` 異動，自動以 `psql -v ON_ERROR_STOP=1` 安全套用冪等遷移。
   6. 更新正式版 Python 依賴；若偵測到 `frontend/package.json` 依賴欄位或 `package-lock.json` 異動則自動補跑 `npm install`，再執行 `npm run build`。
   7. `sudo -n systemctl restart frog_kudos.service`，以 10 次重試迴圈驗證 `/api/health` 同時回傳 `"status":"ok"` 與 `"version":"vX.Y.Z"`（失敗回傳 `exit 1` 並列印回滾指引）。
3. **（選用）重啟開發服務同步執行中應用狀態與 `/docs` 版本號**：
   ```bash
   ssh -o BatchMode=yes chinsonyeh@192.168.50.3 'sudo -n systemctl restart frog_kudos_dev.service'
   ```

---

## 階段 4：發版後驗收與本機回步（強制必做）

1. **本機工作區回步同步（本機 PowerShell，防止分支分叉）**：
   ```powershell
   git pull origin master --tags
   git status -sb
   cat VERSION
   ```
2. **發版完成驗證清單**：
   - [ ] `ReleaseNote.md` 已包含 `vX.Y.Z` 完整條目。
   - [ ] `VERSION` 與 `frontend/package.json` 版本號一致（`vX.Y.Z` / `X.Y.Z`）。
   - [ ] `pytest` 全部通過且已產出發版前正式資料庫備份檔（`.dump`）。
   - [ ] 正式環境健康檢查 `http://127.0.0.1:8000/api/health` 回傳 `{"status":"ok","app":"Frog Kudos","version":"vX.Y.Z"}`。
   - [ ] **四方版本完全一致**：本機工作區、GitHub (`origin/master` + Tag `vX.Y.Z`)、遠端開發目錄 (`~/Code/frog_kudos`)、遠端正式目錄 (`~/frog_kudos`) 皆位於同一 Commit 且工作區乾淨。
   - [ ] 正式網址 `https://kudos.chinson.idv.tw` 可正常開啟運作。

---

## 附錄 A：發版失敗回滾 SOP（Rollback）

若步驟 5～7 發生異常（例如遷移失敗、前端建置異常或服務啟動健康檢查失敗），請依腳本印出的 `PREV_PROD_COMMIT` 與備份檔路徑立即執行回滾：

```bash
ssh -o BatchMode=yes chinsonyeh@192.168.50.3 '
  set -e
  cd /home/chinsonyeh/frog_kudos
  git reset --hard <PREV_PROD_COMMIT>
  cd /home/chinsonyeh/frog_kudos/frontend
  npm run build --silent
  sudo -n systemctl restart frog_kudos.service
  sleep 2
  curl -fsS http://127.0.0.1:8000/api/health
'
```
- 若本次發版涉及資料庫異動或需復原資料，再執行還原腳本（會自動先留還原前快照）：
  ```bash
  ssh -t chinsonyeh@192.168.50.3 '/home/chinsonyeh/frog_kudos/scripts/restore.sh <LATEST_BACKUP_PATH>'
  ```
- 回滾確認正式環境恢復正常後，再於開發環境排查根因，切勿在未釐清問題前使用 `--force-tag` 硬蓋版本。

## 附錄 B：若發版後才補寫 `ReleaseNote.md` 的補救方式

- 於本機補寫 `ReleaseNote.md` → `git commit -m "docs: 補齊 vX.Y.Z 版本發佈日誌"` → `git push origin master`。
- 於遠端開發目錄（`~/Code/frog_kudos`）與正式目錄（`~/frog_kudos`）各執行一次 `git pull --ff-only origin master`（純文件變更無須重編前端或重啟服務）。
- 除非使用者明確要求，否則**不隨意強制覆寫已推送之既有 Git Tag**。
