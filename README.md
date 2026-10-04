# 🐸 Frog Kudos 家庭積分獎勵系統

專為家庭設計的積分與正向獎勵激勵系統。

## 🌟 核心特色

1. **多成員帳號隔離與客製**：支援多位家庭成員（例如家長 Admin、小孩 Ian），每位成員可享有各自專屬的目標與獎勵標準，亦可繼承全家通用規則。
2. **智慧帶出（Auto-calc Preview）**：輸入「成員 + 目標項目 + 達成條件/數值」時，後端智慧比對規則並即時帶出建議積分。
3. **積分快照保存（Point & Rule Snapshotting）**：**不可溯及既往原則**。規則可能隨學期或年齡調整，但歷史已發放的紀錄永久保存快照（Snapshot），絕不受後續規則修改影響。
4. **獎勵商城與兌換機制（Kudos Shop）**：累積點數可兌換自訂獎勵（如遊戲時間、課外活動、心願禮物），支援餘額檢查與扣點交易完整性。

## 🛠 技術架構

- **資料庫**：PostgreSQL (`frog_kudos`)
- **後端**：Python 3.12 + FastAPI + SQLAlchemy 2.0 (Async) + asyncpg + Pydantic v2
- **前端**：Vue 3 (Composition API) + Vite + TailwindCSS + Pinia + Canvas Confetti

## 🚀 快速開始：從 0 開始安裝指南

### 1. 系統環境需求
- **作業系統**：Linux / macOS (支援 Ubuntu 22.04+, Debian 12+)
- **Python**：Python 3.12+
- **Node.js**：Node.js 18+ (包含 npm)
- **PostgreSQL**：PostgreSQL 14+ (含 `psql` 與 `pg_dump` 命令列工具)

### 2. 下載專案並執行自動化安裝
```bash
# 複製專案庫
git clone https://github.com/chinsonyeh/frog_kudos.git
cd frog_kudos

# 執行自動化安裝腳本 (自動檢查環境、建立設定檔、初始化資料庫與編譯前端)
./scripts/install.sh
```

> **進階安裝參數**（支援自動化或自訂設定）：
> ```bash
> ./scripts/install.sh --port 8000 --db-user postgres --db-password your_password --db-name frog_kudos
> ```

### 3. 啟動系統
```bash
# 啟動系統單一連接埠服務
./run.sh

# 亦可臨時指定自訂 Port 啟動
./run.sh 8080
```

* **本機瀏覽器開啟**：`http://localhost:8000`
* **家庭區網其他裝置開啟**：`http://<主機區域IP>:8000`

---

## 🔑 預設登入身分與安全 PIN 碼

系統冷啟動時自動建立初始成員種子資料（相容於 `schema.sql`）：
* **家長管理帳號**：`Dad`（預設 PIN: `0000`）
* **小孩專屬帳號**：`Ian`（預設 PIN: `0000`）
* **未解鎖/訪客模式**：無需輸入密碼，可安全瀏覽家庭榮譽存摺。

---

## 🛠️ 常用管理與維運腳本

| 任務 | 執行命令 | 說明 |
| :--- | :--- | :--- |
| **啟動系統** | `./run.sh` | 啟動單一連接埠整合服務（FastAPI + Vue 3 SPA） |
| **手動備份** | `./scripts/backup.sh [路徑]` | 建立資料庫二進位 dump 備份，自動輪替保留最新 10 份 |
| **資料庫還原** | `./scripts/restore.sh <dump_file> [-y]` | 安全還原資料庫（還原前自動建立防護快照） |
| **一鍵系統升級** | `./scripts/upgrade.sh [套件檔]` | 自動自 GitHub 下載或使用本地套件執行無縫升級與 Migration |
| **執行自動化測試** | `./venv/bin/pytest tests/test_api.py -v` | 執行 12 項核心端到端與單元測試套件 |

---

## 📚 相關設計文件

- [需求規格書 (REQUIREMENT.md)](./REQUIREMENT.md) - 系統背景、角色定位、功能需求與非功能需求。
- [系統詳細設計文件 (DESIGN.md)](./DESIGN.md) - 詳細 Mermaid 資料庫實體關聯 (ERD)、API 規格、Vue 3 介面線框圖與 PostgreSQL DDL 腳本。

