---
name: release-version
description: >-
  Frog Kudos 專案標準進版與正式環境發佈流程（Release Workflow）。當使用者要求「進版」、「發版」、「部署到正式環境」、「更新版本號 / ReleaseNote.md / Git Tag」或執行 `scripts/deploy_to_release.sh` 時必須載入並嚴格遵循本技能。
---

# Frog Kudos 標準進版與發佈流程（Release Workflow）

本技能定義 **Frog Kudos** 從準備進版、補齊發佈日誌、測試驗證、正式部署到發版後四方同步的完整標準作業程序（SOP），確保每次進版都不遺漏 `ReleaseNote.md`、測試驗證與本機 Git 回步。

## 0. 環境對照與不可違反鐵則

| 環境 | 主機與路徑 | 服務名稱 | 本機健康檢查 | 對外 HTTPS 網址 |
| :--- | :--- | :--- | :--- | :--- |
| **本機開發區** | `d:\Users\Chinson\Documents\Code\frog_kudos` | — | — | — |
| **GitHub 倉庫** | `git@github.com:chinsonyeh/frog_kudos.git`（`master`） | — | — | — |
| **開發 / 測試環境** | `192.168.50.3:/home/chinsonyeh/Code/frog_kudos` | `frog_kudos_dev.service` | `http://127.0.0.1:8001/api/health` | `https://kudos.chinson.idv.tw:8443` |
| **正式環境** | `192.168.50.3:/home/chinsonyeh/frog_kudos` | `frog_kudos.service` | `http://127.0.0.1:8000/api/health` | `https://kudos.chinson.idv.tw` |

- **必須先獲同意**：未經使用者明確確認「部署正式環境／進版」，僅可部署開發測試環境（`frog_kudos_dev`）。
- **一律走 GitHub**：所有程式碼與文件異動須於本機提交並推送至 GitHub，再於 `192.168.50.3` 執行 `git pull`；嚴禁直接跨機覆寫。
- **保護未追蹤資料**：遠端嚴禁誤刪 `.env`、`uploads/`、`backups/`、`venv/`。
- **嚴禁洩漏機密**：提交內容、`ReleaseNote.md` 與回應中皆不可出現密碼、PIN、LINE Token 或 Cloudflare API Token。

---

## 階段 1：版本確認與發佈文件更新（本機・發版前必做）

1. **確認目前版本與本次變更範圍**：
   ```bash
   cat VERSION
   git describe --tags --abbrev=0
   git log $(git describe --tags --abbrev=0)..HEAD --oneline
   ```
   - 依語意化版本規則決定新版本號 `vX.Y.Z`（Bugfix / 小調整升 Patch；新功能升 Minor）。
2. **更新 `ReleaseNote.md`（強制必做，不可省略）**：
   - 於根目錄 `ReleaseNote.md` 最上方新增 `## 🚀 [vX.Y.Z] - YYYY-MM-DD` 區塊，風格與既有版本保持一致。
   - 依本次 `git log` 內容清楚分類撰寫：
     - `### ✨ 新增核心功能 (New Features)`（若有）
     - `### 🎨 介面與體驗優化 (UI/UX Improvements)`（若有）
     - `### 🐛 問題修正 (Bug Fixes)`（若有）
     - `### 🔧 資料庫／維運與文件變更 (Infrastructure & Docs)`（若有）
3. **檢查關聯設計文件與套件相依**：
   - 若本次異動涉及資料表 Schema、API 規格或重要架構變更，同步更新 `DESIGN.md` 與 `REQUIREMENT.md`。
   - 檢查本次變更是否修改過 `frontend/package.json`（決定階段 3 是否須於正式目錄補跑 `npm install`）：
     ```bash
     git diff $(git describe --tags --abbrev=0)..HEAD -- frontend/package.json
     ```
4. **品質把關（建議）**：
   - 若本次包含程式碼異動且尚未審查，先呼叫專案 `reviewer` Agent 確認無 Blocker／Major 遺留。

---

## 階段 2：本機提交、推送 GitHub 與開發環境最後確認

1. **本機提交並推送至 GitHub**：
   ```bash
   git status -sb
   git add ReleaseNote.md <其他異動檔案>
   git commit -m "docs: 更新 vX.Y.Z 版本發佈日誌"
   git push origin master
   ```
2. **確認開發環境已同步最新提交並通過實機驗證**：
   ```bash
   ssh chinsonyeh@192.168.50.3 'cd /home/chinsonyeh/Code/frog_kudos && git pull origin master && git status -sb'
   ```
   - 若程式碼尚未在開發環境建置驗證，先執行 `cd frontend && npm run build` 與 `sudo systemctl restart frog_kudos_dev.service`，並請使用者於 `https://kudos.chinson.idv.tw:8443` 確認無誤後，再進入階段 3。

---

## 階段 3：執行正式環境發版（`192.168.50.3`）

1. **發版前工作區潔淨檢查（強制）**：
   - 確認 `/home/chinsonyeh/Code/frog_kudos` 與 `/home/chinsonyeh/frog_kudos` 的 `git status -sb` **皆完全乾淨**（因 `scripts/deploy_to_release.sh` 會執行 `git add -A` 並自動 commit 與 push，未預期暫存檔會被誤提交）。
   ```bash
   ssh chinsonyeh@192.168.50.3 'for d in /home/chinsonyeh/Code/frog_kudos /home/chinsonyeh/frog_kudos; do echo "=== $d ==="; cd "$d"; git status -sb; done'
   ```
2. **前端新依賴補裝（僅在 `frontend/package.json` 有變更時）**：
   - 因 `deploy_to_release.sh` 預設僅跑 `npm run build`，若本次有新增或更新前端套件，須先於正式目錄拉取並安裝依賴，或於發版腳本完成後補跑：
     ```bash
     ssh chinsonyeh@192.168.50.3 'cd /home/chinsonyeh/frog_kudos/frontend && npm install && npm run build && sudo systemctl restart frog_kudos.service'
     ```
3. **執行一鍵正式發版腳本**：
   ```bash
   ssh chinsonyeh@192.168.50.3 'cd /home/chinsonyeh/Code/frog_kudos && ./scripts/deploy_to_release.sh vX.Y.Z'
   ```
   該腳本會自動依序完成：
   1. 於開發環境執行完整 `pytest` 整合測試（任一失敗即中止發版）。
   2. 寫入新版本號至 `VERSION` 並建立 `release: bump version to vX.Y.Z` commit。
   3. 建立 Annotated Git Tag `vX.Y.Z` 並推送 `master` 與 `--tags` 至 GitHub。
   4. 於正式目錄 `/home/chinsonyeh/frog_kudos` 執行 `git pull origin master`。
   5. 更新正式版 Python 依賴（`pip install -r requirements.txt`）並建置正式版前端（`npm run build`）。
   6. 重啟 `frog_kudos.service` 並呼叫 `http://127.0.0.1:8000/api/health` 驗證狀態。
4. **（選用）重啟開發服務對齊版本顯示**：
   - 若希望開發環境 `/api/health` 亦顯示新版本號 `vX.Y.Z`，執行：
     ```bash
     ssh chinsonyeh@192.168.50.3 'sudo systemctl restart frog_kudos_dev.service'
     ```

---

## 階段 4：發版後驗收與本機回步（強制必做）

1. **本機工作區回步同步（防止分支分叉）**：
   ```bash
   git pull origin master --tags
   git status -sb
   cat VERSION
   ```
2. **發版完成驗證清單**：
   - [ ] `ReleaseNote.md` 已包含 `vX.Y.Z` 完整條目。
   - [ ] `pytest` 全部通過，無失敗案例。
   - [ ] 正式環境健康檢查 `http://127.0.0.1:8000/api/health` 回傳 `{"status":"ok","app":"Frog Kudos","version":"vX.Y.Z"}`。
   - [ ] **四方版本完全一致**：本機工作區、GitHub (`origin/master` + Tag `vX.Y.Z`)、遠端開發目錄 (`~/Code/frog_kudos`)、遠端正式目錄 (`~/frog_kudos`) 皆位於同一 Commit 且工作區乾淨。
   - [ ] 正式網址 `https://kudos.chinson.idv.tw` 可正常開啟運作。

---

## 附錄：若發版後才發現漏更新 `ReleaseNote.md` 的補救方式

- 於本機補寫 `ReleaseNote.md` → `git commit -m "docs: 補齊 vX.Y.Z 版本發佈日誌"` → `git push origin master`。
- 於遠端開發目錄（`~/Code/frog_kudos`）與正式目錄（`~/frog_kudos`）各執行一次 `git pull origin master`（純文件變更無須重編前端或重啟服務）。
- 除非使用者明確要求，否則**不隨意強制覆寫已推送之既有 Git Tag**。
