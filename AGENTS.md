# Frog Kudos 專案工作規範

本檔案定義 Frog Kudos 專案的環境架構、部署鐵則與開發準則，供所有 Agent 對話自動載入遵循。

## 1. 環境與主機對照（Single Source of Truth）

| 角色 | 位置 / 連線 | 路徑 | 資料庫 (`DB_NAME`) | systemd 服務 | 本機 Port | Caddy HTTPS Port & 網址 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **本機開發區** | Windows 本機 | `d:\Users\Chinson\Documents\Code\frog_kudos` | — | — | — | — |
| **程式碼倉庫** | GitHub | `git@github.com:chinsonyeh/frog_kudos.git`（`master`） | — | — | — | — |
| **開發 / 測試環境** | `ssh chinsonyeh@192.168.50.3`（`frog-asset`） | `/home/chinsonyeh/Code/frog_kudos` | `frog_kudos_dev` | `frog_kudos_dev.service` | `8001` | **`8443`** → `https://kudos.chinson.idv.tw:8443` |
| **正式環境** | `ssh chinsonyeh@192.168.50.3`（`frog-asset`） | `/home/chinsonyeh/frog_kudos` | `frog_kudos` | `frog_kudos.service` | `8000` | **`443`** → `https://kudos.chinson.idv.tw` |

> 完整操作步驟與防呆清單請參閱 `doc/deployment-workflow.md`。

## 2. 部署與維運鐵則

- **一律走 GitHub 同步**：所有程式碼修改必須先於本機完成、測試並推送至 GitHub，再 SSH 至 `192.168.50.3` 執行 `git pull`；嚴禁跨機直接傳檔覆寫，也不要只在遠端改碼。
- **先測試、後正式**：未經使用者明確確認前，部署驗證一律只更新**開發 / 測試環境**（`/home/chinsonyeh/Code/frog_kudos`、`frog_kudos_dev.service`、Port `8001` / HTTPS `8443`），切勿未經同意更動正式環境（`/home/chinsonyeh/frog_kudos`、`frog_kudos.service`、資料庫 `frog_kudos`）。
- **保護未追蹤資料**：遠端更新優先使用 `git pull`，嚴禁誤刪 `.env`、`uploads/`、`backups/`、`venv/`。
- **發版腳本注意**：執行 `scripts/deploy_to_release.sh <version>` 前須先確認遠端開發目錄 `git status -sb` 乾淨；若 `frontend/package.json` 有變動，正式目錄須補跑 `npm install`；發版後本機須執行 `git pull origin master` 同步 `VERSION` commit。

## 3. 核心開發與安全準則

- **繁體中文溝通**：回覆與專案文件一律使用繁體中文。
- **積分快照不可溯及既往**：修改規則、分類或獎項時，絕不可破壞既有 `kudos_records` 的歷史快照。
- **三層權限後端把關**：家長 / 小孩 / 訪客權限皆須由 FastAPI 後端驗證，不可僅依賴前端隱藏按鈕。
- **行動端 Safe Area 規範**：維持 `frontend/index.html` 的 `viewport-fit=cover`，修改頂部導覽列或 Modal 時須遵守 `env(safe-area-inset-*)` 與 `doc/iphone-safe-area-plan.md` 之設計。
- **嚴禁洩漏敏感資訊**：切勿在回應、日誌或提交內容中輸出 `.env` 密碼、PIN、LINE Token 或 Caddy Cloudflare API Token。
