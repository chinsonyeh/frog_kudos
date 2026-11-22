# Frog Kudos 開發與部署標準流程（本機 -> GitHub -> 192.168.50.3）

> **原則**：所有程式碼修改皆於**本機開發環境**完成並推送至 **GitHub**（單一真實來源 Single Source of Truth），再透過 **SSH 連線至 `192.168.50.3`** 從 GitHub 拉取程式碼並更新服務；不直接跨機覆寫檔案或僅在遠端改檔。

---

## 1. 環境與主機資訊

| 角色 | 位置 / 連線方式 | 路徑 | 資料庫 (`DB_NAME`) | 對應服務 / 本機監聽 / Caddy HTTPS 對外網址 |
| :--- | :--- | :--- | :--- | :--- |
| **本機開發區** | Windows 本機 | `d:\Users\Chinson\Documents\Code\frog_kudos` | — | — |
| **程式碼倉庫** | GitHub | `git@github.com:chinsonyeh/frog_kudos.git`（分支 `master`） | — | — |
| **開發測試環境** | `ssh chinsonyeh@192.168.50.3`（主機名 `frog-asset`） | `/home/chinsonyeh/Code/frog_kudos` | `frog_kudos_dev` | `frog_kudos_dev.service`（本機 `127.0.0.1:8001`；Caddy HTTPS Port **`8443`** → `https://kudos.chinson.idv.tw:8443`） |
| **正式運行環境** | `ssh chinsonyeh@192.168.50.3`（主機名 `frog-asset`） | `/home/chinsonyeh/frog_kudos` | `frog_kudos` | `frog_kudos.service`（本機 `127.0.0.1:8000`；Caddy HTTPS Port **`443`** → `https://kudos.chinson.idv.tw`，`http://192.168.50.3` 會 301 重導向至此） |

---

## 2. 標準開發與部署步驟

### 步驟 1：本機開發、驗證並推送至 GitHub
於本機工作區完成開發、前端建置測試與 Git 提交後，先推送至 GitHub：

```bash
git status
git add <異動檔案>
git commit -m "<commit message>"
git push origin master
```

### 步驟 2：SSH 連線至 `192.168.50.3` 同步 GitHub 程式碼

```bash
ssh chinsonyeh@192.168.50.3
```

依目標目錄狀態選擇同步方式：

#### 情境 A：全新目錄（尚未建立時）— 使用 `git clone`
```bash
git clone git@github.com:chinsonyeh/frog_kudos.git /home/chinsonyeh/Code/frog_kudos
```
> 若首次建置或重新 clone，請確認補回或初始化 `.env`、`venv/`、`uploads/` 等未被 Git 追蹤的資料，或執行 `./scripts/install.sh`。

#### 情境 B：既有部署目錄（日常更新推薦）— 使用 `git pull`
> **重要提醒**：`192.168.50.3` 既有目錄內包含被 `.gitignore` 排除的環境與使用者資料（`.env`、`venv/`、`uploads/`、`backups/`、`frontend/node_modules/`）。日常更新建議使用 `git pull` 以保留這些資料；若確實需要刪除後重新 `git clone`，務必先備份上述檔案與目錄。

```bash
# 1. 先同步開發環境驗證
cd /home/chinsonyeh/Code/frog_kudos
git pull origin master
```

### 步驟 3：更新依賴、建置前端並重啟開發服務（驗證階段）
```bash
cd /home/chinsonyeh/Code/frog_kudos

# 若有後端依賴更新
./venv/bin/pip install -q -r requirements.txt

# 建置前端 SPA 靜態資源
cd frontend
npm install   # 若 package.json 有變更時執行
npm run build

# 重啟開發版服務並執行健康檢查
sudo systemctl restart frog_kudos_dev.service
systemctl is-active frog_kudos_dev.service
curl -s http://127.0.0.1:8001/api/health
```
> 驗證時請連線至開發測試網址 `https://kudos.chinson.idv.tw:8443`，避免誤測正式環境。

### 步驟 4：同步正式環境並發佈（驗證通過後）
開發環境（含 iPhone 實機於 `https://kudos.chinson.idv.tw:8443`）驗證無誤後，再更新正式環境 `/home/chinsonyeh/frog_kudos`（對外網址 `https://kudos.chinson.idv.tw`）：

- **方式一（單純更新正式環境）**：
  ```bash
  cd /home/chinsonyeh/frog_kudos
  git pull origin master
  ./venv/bin/pip install -q -r requirements.txt
  cd frontend
  npm install   # 若 package.json 有新增或更新依賴時必跑
  npm run build
  sudo systemctl restart frog_kudos.service
  curl -s http://127.0.0.1:8000/api/health
  ```
- **方式二（正式發版並打 Git Tag）**：
  於 `192.168.50.3` 的開發目錄執行既有一鍵發佈腳本（自動跑 `pytest`、寫入 `VERSION`、commit 並推 Tag 至 GitHub、同步 `~/frog_kudos`、建置前端並重啟正式服務）：
  ```bash
  cd /home/chinsonyeh/Code/frog_kudos
  git status -sb                      # 執行前務必確認工作區乾淨（腳本會 git add -A 並 commit + push）
  ./scripts/deploy_to_release.sh v1.0.x
  ```
  - **若 `frontend/package.json` 有新增依賴**：因 `deploy_to_release.sh` 預設僅執行 `npm run build` 而不會自動執行 `npm install`，請於正式目錄補跑：
    ```bash
    cd /home/chinsonyeh/frog_kudos/frontend
    npm install && npm run build
    sudo systemctl restart frog_kudos.service
    curl -s http://127.0.0.1:8000/api/health
    ```
  - **發佈後同步本機**：腳本會自動產生更新 `VERSION` 的 commit 並推送至 GitHub，發佈完成後請務必回到**本機開發區**執行：
    ```bash
    git pull origin master
    ```

---

## 3. 注意事項與防呆清單

1. **禁止未經 GitHub 直接傳檔覆寫 50.3**：確保本機、GitHub、`~/Code/frog_kudos`、`~/frog_kudos` 四處版本可追溯且一致。
2. **執行 `deploy_to_release.sh` 前必先檢查 `git status -sb`**：因腳本內含 `git add -A`、`git commit` 與 `git push`，務必先確認遠端開發目錄沒有未預期之暫存或修改檔案，避免誤提交。
3. **發佈後本機必執行 `git pull origin master`**：同步 `deploy_to_release.sh` 建立的 `VERSION` commit，防止本機與遠端分支歷史分叉。
4. **前端依賴異動時正式目錄須補跑 `npm install`**：`deploy_to_release.sh` 預設僅執行 `npm run build`，若本次更新有異動 `frontend/package.json`，須手動於 `/home/chinsonyeh/frog_kudos/frontend` 執行 `npm install` 後再建置。
5. **重做 `git clone` 前必備份清單**：`.env`、`uploads/`、`backups/`（以及可重建但耗時的 `venv/`、`frontend/node_modules/`）。
6. **資料庫隔離確認**：開發測試環境使用獨立資料庫 `frog_kudos_dev`，正式環境使用 `frog_kudos`；測試驗證一律於 `https://kudos.chinson.idv.tw:8443` 進行，避免誤寫正式資料。
7. **變更檢查**：部署完成後可於遠端以 `git rev-parse --short HEAD` 與 `git status -sb` 確認版本號與 GitHub 一致且工作目錄乾淨，並透過對應健康檢查端點確認服務運作正常（開發：`127.0.0.1:8001/api/health`、正式：`127.0.0.1:8000/api/health`）。
