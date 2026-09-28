# Frog Kudos 家庭積分獎勵系統 - 系統詳細設計文件 (DESIGN.md)

本文件依據 [REQUIREMENT.md](./REQUIREMENT.md) 需求規格書，定義 **Frog Kudos 家庭積分獎勵系統** 的技術架構、PostgreSQL 資料庫實體關聯 (Mermaid ERD)、後端推導引擎演算法、RESTful API 規格以及 Vue 3 前端介面詳細設計。

---

## 1. 系統架構總覽 (System Architecture)

系統採用前後端整合部署設計，**「平日日常使用只需單一 Port」**，運行於本機 Linux 環境，使用現有的 PostgreSQL `frog_kudos` 資料庫。

#### 1.1 平日日常運行架構（單一 Port 模式，預設 Port 8000，安裝時可自訂指定）
Vue 3 前端編譯建置為靜態資源（`dist/`），由 FastAPI 後端伺服器在單一連接埠上同時託管「前端單頁應用 (SPA)」與「後端 REST API」。

```
  家庭成員裝置 (手機 / iPad / 電腦瀏覽器)
                   │
                   ▼ (單一連接埠: 例如 http://主機IP:<自訂Port>)
+---------------------------------------------------------------------------------+
|                       FastAPI 整合伺服器 (Port: <自訂Port>)                       |
|                                                                                 |
|   ├── GET /api/*        ➔ RESTful APIs (業務邏輯、推導引擎、資料庫交易)            |
|   └── GET /*            ➔ StaticFiles 靜態託管 (Vue 3 SPA 單頁應用 index.html)    |
|                                                                                 |
|   ├── routers/          (成員、規則、點數發放、批次調整、商城兌換)               |
|   ├── services/         (智慧規則比對推導引擎 Rule Matching Engine)              |
|   ├── schemas/          (Pydantic v2 資料驗證與型別轉換)                         |
|   └── models/           (SQLAlchemy 2.0 Async ORM 實體)                         |
+---------------------------------------------------------------------------------+
                                      │ asyncpg 連線池 (ACID Transactions)
                                      ▼
+---------------------------------------------------------------------------------+
|                       資料庫層 (PostgreSQL: frog_kudos)                         |
|   ├── members           (家庭成員與餘額快取)                                     |
|   ├── categories        (規則與獎項分類)                                         |
|   ├── reward_rules      (成員專屬與通用獎勵規則)                                 |
|   ├── kudos_records     (核心快照流水帳 - 永久封存歷史點數與規則)                |
|   ├── reward_items      (兌換商城品項)                                           |
|   └── redemptions       (兌換核銷紀錄)                                           |
+---------------------------------------------------------------------------------+
```

- **單一 Port 優勢**：
  1. **自訂與防衝突**：安裝時可自由指定連接埠（如 `8080`、`5000`），避免與家庭現有服務（如 NAS、Home Assistant、既有網頁）發生 Port 衝突。
  2. **零額外組態**：不需安裝設定 Nginx 反向代理，家庭主機資源消耗極低。
  3. **連線便利**：家人手機或平板只要儲存一個書籤（如 `http://192.168.1.100:8080`）。
  4. **無跨域問題 (Zero CORS issues)**：API 與網頁同源同 Port，避免跨來源請求被瀏覽器安全政策阻擋。
  5. **Vue Router SPA 路由 Fallback 防 404 機制**：後端 `app/main.py` 實作 Catch-All 路由處理器。當使用者在瀏覽器直接輸入或按 F5 重新整理前端路由（如 `/ledger`、`/rewards`）時，若請求非 `/api/*` 且非磁碟上的實體靜態資源，後端強制回傳 `frontend/dist/index.html`，徹底杜絕 SPA 重新整理拋出 404 Not Found 的衝突問題。

### 1.2 本機開發模式 (Dev Mode，雙 Port 模式)
- **前端開發伺服器**：Vite 監聽 Port `5173`，支援 HMR（模組熱更替，存檔即刷新）。
- **後端開發伺服器**：FastAPI (Uvicorn) 監聽 Port `8000`，支援自動熱重載 (Reload)。
- **Vite Proxy**：Vite 設定代理將 `/api` 請求無縫轉發至 Port `8000`。

---

## 2. 資料庫架構與 Mermaid 詳細關聯 (Database Schema)

資料庫核心設計原則：**「Append-Only 記帳與數值快照（Snapshotting）」**。
歷史發放的點數紀錄（`kudos_records`）與兌換紀錄（`redemptions`）獨立保存當下的數值與規則快照，即使 `reward_rules` 被修改或刪除，過往紀錄完全不變。

### 2.1 Mermaid 實體關聯圖 (ER Diagram)

```mermaid
erDiagram
    MEMBERS ||--o{ REWARD_RULES : "擁有 (member_id)"
    CATEGORIES ||--o{ REWARD_RULES : "分類 (category_id)"
    MEMBERS ||--o{ KUDOS_RECORDS : "獲得積分 (member_id)"
    REWARD_RULES ||--o{ KUDOS_RECORDS : "參考規則 (rule_id)"
    MEMBERS ||--o{ REDEMPTIONS : "發起兌換 (member_id)"
    REWARD_ITEMS ||--o{ REDEMPTIONS : "兌換獎品 (item_id)"
    MEMBERS ||--o{ MEMBER_BADGES : "獲得勳章 (member_id)"

    MEMBERS {
        uuid id PK "PRIMARY KEY, DEFAULT gen_random_uuid()"
        varchar name UK "NOT NULL, UNIQUE, 成員姓名(如 Ian)"
        varchar role "NOT NULL DEFAULT 'child', 角色(parent/child)"
        varchar avatar "DEFAULT '🐸', 頭像圖示"
        integer current_points "NOT NULL DEFAULT 0, CHECK(current_points >= 0)"
        integer total_earned_points "NOT NULL DEFAULT 0, 歷史累積總點數"
        varchar pin_code "NULLABLE, 家長管理PIN碼"
        boolean is_active "NOT NULL DEFAULT TRUE, 是否啟用"
        timestamptz created_at "NOT NULL DEFAULT NOW()"
        timestamptz updated_at "NOT NULL DEFAULT NOW()"
    }

    CATEGORIES {
        serial id PK "PRIMARY KEY, 自增ID"
        varchar name "NOT NULL, UNIQUE, 分類名(學業成績/生活常規)"
        varchar icon "DEFAULT '📚', 分類圖示"
        integer sort_order "NOT NULL DEFAULT 0, 排序權重"
    }

    REWARD_RULES {
        uuid id PK "PRIMARY KEY, DEFAULT gen_random_uuid()"
        uuid member_id FK "FOREIGN KEY -> members(id) ON DELETE CASCADE, NULL表示全家通用"
        integer category_id FK "FOREIGN KEY -> categories(id) ON DELETE SET NULL, NULLABLE"
        varchar target_name "NOT NULL, 目標項目(如 社會科, 數學科)"
        varchar match_type "NOT NULL DEFAULT 'NUM_GTE', 比對方式(EXACT, NUM_GTE, NUM_EQ)"
        varchar condition_value "NOT NULL, 門檻值(如 100, 90, 完成)"
        integer reward_points "NOT NULL, 獎勵點數(如 50)"
        text description "NULLABLE, 規則說明文字"
        boolean is_active "NOT NULL DEFAULT TRUE, 是否生效"
        timestamptz created_at "NOT NULL DEFAULT NOW()"
        timestamptz updated_at "NOT NULL DEFAULT NOW()"
    }

    KUDOS_RECORDS {
        uuid id PK "PRIMARY KEY, DEFAULT gen_random_uuid()"
        uuid member_id FK "FOREIGN KEY -> members(id) ON DELETE RESTRICT, NOT NULL"
        uuid rule_id FK "FOREIGN KEY -> reward_rules(id) ON DELETE SET NULL, NULLABLE"
        varchar target_name_snapshot "NOT NULL, [快照] 目標項目名(如 社會科)"
        varchar condition_snapshot "NOT NULL, [快照] 達成數值/條件(如 100)"
        integer points_awarded "NOT NULL, [快照] 實發點數(如 50, 可由家長批次統一調整)"
        jsonb rule_detail_snapshot "NULLABLE, [快照] 當下規則JSON完整備份"
        text note "NULLABLE, 家長備註(如 第一次段考滿分)"
        text adjustment_note "NULLABLE, [批次調整] 統一修改原因備註"
        varchar recorded_by "NOT NULL DEFAULT 'Parent', 登記人"
        timestamptz created_at "NOT NULL DEFAULT NOW(), 獲得時間"
        timestamptz updated_at "NOT NULL DEFAULT NOW(), 最後異動時間"
    }

    REWARD_ITEMS {
        uuid id PK "PRIMARY KEY, DEFAULT gen_random_uuid()"
        varchar title "NOT NULL, 獎品名稱(如 玩Switch 1小時)"
        text description "NULLABLE, 兌換限制與備註"
        integer cost_points "NOT NULL, 兌換所需點數, CHECK(cost_points > 0)"
        varchar icon "DEFAULT '🎁', 獎品圖示"
        boolean is_active "NOT NULL DEFAULT TRUE, 是否上架"
        timestamptz created_at "NOT NULL DEFAULT NOW()"
    }

    REDEMPTIONS {
        uuid id PK "PRIMARY KEY, DEFAULT gen_random_uuid()"
        uuid member_id FK "FOREIGN KEY -> members(id) ON DELETE RESTRICT, NOT NULL"
        uuid item_id FK "FOREIGN KEY -> reward_items(id) ON DELETE SET NULL, NULLABLE"
        varchar item_title_snapshot "NOT NULL, [快照] 兌換時品項名稱"
        integer points_spent "NOT NULL, [快照] 扣除點數"
        varchar status "NOT NULL DEFAULT 'PENDING', 狀態(PENDING/COMPLETED/REJECTED)"
        text review_note "NULLABLE, 審核備註"
        timestamptz created_at "NOT NULL DEFAULT NOW(), 申請時間"
        timestamptz reviewed_at "NULLABLE, 核准時間"
    }

    MEMBER_BADGES {
        uuid id PK "PRIMARY KEY, DEFAULT gen_random_uuid()"
        uuid member_id FK "FOREIGN KEY -> members(id) ON DELETE CASCADE, NOT NULL"
        varchar badge_key "NOT NULL, 勳章識別碼(如 FIRST_100_PTS)"
        timestamptz unlocked_at "NOT NULL DEFAULT NOW(), 解鎖時間"
    }
```

### 2.2 外鍵約束與級聯行為說明

1. **`reward_rules.member_id` ➔ `members.id` (`ON DELETE CASCADE`)**：
   - 當成員帳號被徹底刪除時，其專屬的規則自動隨之清理。
   - `member_id` 允許為 `NULL`，代表該規則為**全家共用規則**。
2. **`kudos_records.rule_id` ➔ `reward_rules.id` (`ON DELETE SET NULL`)**：
   - 規則未來即便被刪除，歷史發放紀錄依舊完整保留，`rule_id` 僅被設為 `NULL`，不損壞歷史記帳。
3. **`kudos_records.member_id` ➔ `members.id` (`ON DELETE RESTRICT`)**：
   - 若成員已有歷史點數紀錄，禁止直接硬刪除成員，確保審計鏈完整。
4. **`kudos_records` 快照欄位組與批次調整審計**：
   - `target_name_snapshot`、`condition_snapshot`、`points_awarded`、`rule_detail_snapshot` 均為發放當下儲存值，系統預設不隨規則變動而回溯重算。
   - 當家長主動使用「批次篩選調整工具」時，系統在同一資料庫交易內更新 `points_awarded`、記錄 `adjustment_note`（調整原因）與 `updated_at`，並同步調整該成員之點數餘額，確保審計軌跡清楚透明。
5. **`member_badges.member_id` ➔ `members.id` (`ON DELETE CASCADE`)**：
   - 綁定成員與成就勳章解鎖紀錄，設有 `UNIQUE(member_id, badge_key)` 限制，確保勳章不可重複領取。成員刪除時連帶清理。
6. **點數雙軌帳本語義約束 (`current_points` vs `total_earned_points`)**：
   - **`current_points` (即時可用點數錢包)**：代表成員當前可用於商城兌換之即時餘額。成就發放 (+)、兌換花費 (-)、違規扣點 (-)、批次調整 (±) 皆會影響此欄位，受 `CHECK (current_points >= 0)` 防呆約束。
   - **`total_earned_points` (歷史累計榮譽成就值)**：代表孩子一生付出的努力總成果，解鎖勳章專用。
     - **臨時違規扣點 (FR-14 Penalty)**：僅扣除可用點數 `current_points`，**絕不扣減 `total_earned_points`**，既保護歷史榮譽感，也防止新成員 0 點被扣點時觸發 `CHECK (total_earned_points >= 0)` 違規拋錯。
     - **歷史成就批次調整 (FR-7 Batch Adjustment)**：因屬於回溯修正過往成績，當 $\Delta$ 變動時，同時更新 `current_points += Δ` 與 `total_earned_points += Δ`，且交易前置防呆必須同時滿足 `current_points + Δ >= 0` 與 `total_earned_points + Δ >= 0`。
7. **家長安全鎖 PIN 碼分級驗證架構**：
   - **系統種子 PIN (`.env` 的 `PARENT_DEFAULT_PIN`)**：僅用於系統初次安裝建立種子家長帳號（Dad/Mom）時的初始預設值（預設 `0000`）與緊急維護重設。
   - **日常業務 API 驗證**：前端發起批次調整、兌換審核或系統設定傳入 `parent_pin` 時，後端統一查詢資料庫中 `role = 'parent'` 且 `is_active = TRUE` 的所有家長成員，使用 `bcrypt.verify` 逐一比對 `pin_code`，符合任一家長之 PIN 碼即視為驗證通過。

---

## 3. 後端架構與 API 介面規格 (FastAPI Backend)

### 3.1 規則自動推導引擎算法 (Rule Engine Matching Flow)

當前端觸發試算：`POST /api/kudos/preview`
- **輸入**：`member_id`, `target_name` (如 "社會科"), `condition_value` (如 "100")
- **演算法流程**：
  ```mermaid
  flowchart TD
      Start([收到預覽請求: Member + Target + Value]) --> Step1[查詢 Active 規則清單]
      Step1 --> Step2{是否有符合 target_name 的專屬規則?<br>member_id == input.member_id}
      Step2 -- 是 --> MatchCustom[鎖定成員專屬候選規則]
      Step2 -- 否 --> Step3{是否有全家通用規則?<br>member_id IS NULL}
      Step3 -- 是 --> MatchGlobal[鎖定全家通用候選規則]
      Step3 -- 否 --> NoMatch[無匹配規則: 預設建議點數 0]
      
      MatchCustom --> Filter[條件門檻過濾]
      MatchGlobal --> Filter
      
      Filter --> CondType{比對 match_type}
      CondType -- NUM_GTE --> CheckNum{數值 value >= condition_value?}
      CondType -- EXACT --> CheckStr{字串相符?}
      
      CheckNum -- 符合 --> RankPoints[可能有多條符合, 取 reward_points 最高者]
      CheckStr -- 符合 --> RankPoints
      CheckNum -- 不符合 --> NoMatch
      CheckStr -- 不符合 --> NoMatch

      RankPoints --> OutputResult([回傳: matched=true, rule_id, 建議點數, 規則名稱])
  ```

- **轉型安全防呆機制 (Type Casting Safety)**：
  - 當規則之 `match_type` 為 `NUM_GTE` 或 `NUM_EQ` 時，引擎以 `try ... except (ValueError, TypeError)` 包裹輸入字串轉型（`float(condition_value)`）。
  - 若使用者輸入非純數字文字（如：「甲上」、「優」、「全部完成」），引擎安全判定為條件不符合（`is_matched = False`），並繼續比對其他候選規則或優雅降級回傳建議點數 0，絕不拋出 500 內部伺服器錯誤。

### 3.2 關鍵 API 端點規格

| 方法 | 路徑 | 請求 Payload / 查詢參數 | 回應資料 | 說明 |
|---|---|---|---|---|
| `GET` | `/api/members` | - | `MemberOut[]` | 取得家庭成員清單（含即時點數錢包與歷史累計） |
| `POST` | `/api/members` | `{ name, role, avatar, pin_code, parent_pin }` | `MemberOut` | 新增家庭成員（若 role=parent 需設定 4 碼 PIN，需家長鎖） |
| `GET` | `/api/members/{id}/badges` | - | `MemberBadgeOut[]` | **查詢成員里程碑成就勳章清單與達成進度 (FR-18)** |
| `GET` | `/api/categories` | - | `CategoryOut[]` | **取得規則與獎勵分類清單 (學業、常規、家事等)** |
| `POST` | `/api/categories` | `{ name, icon, sort_order, parent_pin }` | `CategoryOut` | **新增自訂規則分類（需家長安全鎖）** |
| `GET` | `/api/rules` | `?member_id=...` | `RuleOut[]` | 取得規則清單（可過濾專屬或通用） |
| `POST` | `/api/rules` | `{ member_id, category_id, target_name, match_type, condition_value, reward_points, description, parent_pin }` | `RuleOut` | **新增獎勵規則（需家長安全鎖，防小孩越權）** |
| `PUT` | `/api/rules/{id}` | `{ member_id, category_id, target_name, match_type, condition_value, reward_points, description, is_active, parent_pin }` | `RuleOut` | **修改規則（明示不溯及歷史點數，需家長安全鎖）** |
| `DELETE` | `/api/rules/{id}` | `{ parent_pin }` | `{ success: true }` | **停用或刪除規則（需家長安全鎖）** |
| `POST` | `/api/kudos/preview` | `{ member_id, target_name, condition_value }` | `{ matched, suggested_points, rule_id, rule_name }` | **智慧即時試算預覽（支援輸入文字防呆降級）** |
| `POST` | `/api/kudos/record` | `{ member_id, rule_id, target_name, condition_value, points_awarded, note, recorded_by, parent_pin }` | `KudosRecordOut` | **正式發放點數或臨時獎懲（自訂模式 condition_value 可選填，需家長鎖，回傳 newly_unlocked_badges）** |
| `GET` | `/api/kudos/history` | `?member_id=...&limit=50` | `LedgerItemOut[]` | **查詢家庭綜合存摺流水帳（後端自動 UNION kudos_records 與已核銷 redemptions 依時間排序）** |
| `GET` | `/api/items` | `?all=false` | `RewardItemOut[]` | 查詢兌換商城品項（預設僅列出上架中品項） |
| `POST` | `/api/items` | `{ title, description, cost_points, icon, parent_pin }` | `RewardItemOut` | **新增商城獎品（需家長安全鎖）** |
| `PUT` | `/api/items/{id}` | `{ title, description, cost_points, icon, is_active, parent_pin }` | `RewardItemOut` | **編輯商城獎品內容、調整點數或重新上架（需家長安全鎖）** |
| `DELETE` | `/api/items/{id}` | `{ parent_pin }` | `{ success: true }` | **軟刪除下架獎品 (is_active = FALSE，需家長安全鎖)** |
| `POST` | `/api/redemptions` | `{ member_id, item_id, note }` | `RedemptionOut` | **小孩發起兌換申請（扣除可用點數 Transaction，狀態為 PENDING，背景任務非同步推播 LINE 通知）** |
| `GET` | `/api/redemptions` | `?member_id=...&status=...` | `RedemptionOut[]` | 查詢兌換與核銷歷史（支援依狀態篩選） |
| `POST` | `/api/redemptions/{id}/review` | `{ action: "COMPLETE"\|"REJECT", review_note, parent_pin }` | `RedemptionOut` | **家長審核核銷或退回（核銷將狀態設為 COMPLETED，退回將狀態設為 REJECTED 並自動全額退還點數；action 相容 APPROVE 別名）** |
| `GET` | `/api/kudos/export` | `?member_id=...&start_date=...&end_date=...` | `FileStream (CSV)` | **匯出完整學期成就獲得與兌換支出之綜合存摺 CSV 檔案** |
| `POST` | `/api/kudos/batch-preview` | `{ member_id, target_name, start_date, end_date, mode, value }` | `BatchPreviewOut` | **歷史積分批次調整預覽試算** |
| `POST` | `/api/kudos/batch-adjust` | `{ member_id, target_name, start_date, end_date, mode, value, reason, parent_pin }` | `BatchAdjustOut` | **執行歷史積分批次統一調整 (雙軌餘額防負檢查，ACID Transaction)** |
| `POST` | `/api/system/backup` | `{ target_path, parent_pin }` | `{ success, backup_file, file_size, created_at }` | **觸發資料庫備份至指定目標路徑** |
| `GET` | `/api/system/backups` | `?target_path=...` | `BackupFileInfo[]` | **查詢指定目錄歷史備份清單** |
| `GET` | `/api/system/config` | - | `{ backup_dir, port, db_name, github_repo, auto_backup, retention_count, line_configured, line_user_id }` | **Web 取得備份、排程、LINE 通知與系統配置 (密碼欄位強制排除脫敏)** |
| `PUT` | `/api/system/config` | `{ backup_dir, auto_backup, retention_count, line_channel_access_token, line_user_id, parent_pin }` | `{ success }` | **Web 儲存自訂備份路徑、排程與 LINE 通知憑證** |
| `POST` | `/api/system/line/test` | `{ parent_pin }` | `{ success, message }` | **測試發送 LINE Messaging API 推播訊息 (FR-19)** |
| `GET` | `/api/system/version` | - | `{ current_version, latest_version, has_update, release_notes, download_url }` | **連線 GitHub Releases API 檢查最新發行版** |
| `POST` | `/api/system/upgrade` | `{ parent_pin, package_url }` | `{ status, message }` | **Web 一鍵從 GitHub 下載發行包並自動升級** |
| `POST` | `/api/system/upload-package` | `multipart: file, parent_pin` | `{ status, message }` | **手動上傳離線安裝/升級套件 (.tar.gz) 進行升級** |
| `GET` | `/api/system/upgrade-status` | - | `{ status, progress, current_step, logs }` | **Web 輪詢即時升級進度與日誌** |

> 💡 **家長安全鎖 (`parent_pin`) 傳遞彈性**：所有標註需家長鎖之 API，除了可於 JSON Payload 中傳遞 `parent_pin` 外，亦支援於 HTTP Request Header 帶入 `X-Parent-PIN: <PIN>`，方便前端在解鎖狀態下由 Axios / Fetch 攔截器統一附加。

### 3.3 歷史積分批次統一調整演算法與交易安全 (Batch Adjustment Logic & Safety)

當家長需要依「人員、目標項目、時間區間」統一修改過往積分時，後端執行嚴格的交易安全保障：

```mermaid
flowchart TD
    Start([家長發起批次修改請求]) --> Step1[驗證家長安全鎖 PIN 碼]
    Step1 -- 驗證失敗 --> ErrPin[拋出 403: PIN 碼錯誤]
    Step1 -- 驗證成功 --> Step2[DB 交易開啟: 鎖定該成員資料列 SELECT ... FOR UPDATE]
    Step2 --> Step3[查詢符合條件之歷史紀錄清單<br>member_id + target_name + date_range]
    Step3 --> Step4{符合筆數 > 0 ?}
    Step4 -- 否 --> ErrZero[拋出 404: 無符合之歷史紀錄]
    Step4 -- 是 --> Step5[計算各筆新點數與總變動量 Δ]
    Step5 --> Step6{雙軌餘額檢查:<br>current_points + Δ >= 0<br>且 total_earned_points + Δ >= 0 ?}
    Step6 -- 否 --> ErrNeg[拋出 400: 調降後餘額不足以支付歷史已兌換獎品或導致累計為負]
    Step6 -- 是 --> Step7[批次更新 kudos_records:<br>設定 points_awarded, adjustment_note, updated_at]
    Step7 --> Step8[更新 members 表:<br>current_points += Δ<br>total_earned_points += Δ]
    Step8 --> Commit([提交 DB 交易並回傳成功結果])
```

- **批次調整模式 (`mode`)**：
  - `FIXED`（統一設為固定值）：所有符合紀錄的 `points_awarded` 直接更新為 `value`。各筆變動量 $\Delta_i = \text{value} - \text{old\_points}_i$。
  - `OFFSET`（統一增減點數）：所有符合紀錄的 `points_awarded` 更新為 $\text{old\_points}_i + \text{value}$。各筆變動量 $\Delta_i = \text{value}$。
- **不可小於零防呆 (雙軌檢查)**：因批次調整屬於回溯修正歷史成績，變動量 $\Delta$ 同步反映於可用餘額 `current_points` 與歷史累計 `total_earned_points`。若調整為負變動量（向下扣減），系統在同一交易中嚴格保障會員的 `current_points + \Delta \ge 0` 且 `total_earned_points + \Delta \ge 0`，避免破壞已完成之兌換扣點或導致歷史累計值變為負數。

---

## 4. 前端 Web UI 詳細規格 (Vue 3 + TailwindCSS)

前端採用現代 Vue 3 (Composition API + `<script setup>`)，搭配 TailwindCSS 建立活潑親切的家庭 UI。全站具備完整 RWD，手機與平板操作體驗極佳。

### 4.1 頁面架構與導航設計
- **頂部 Header**：
  - 左側：🐸 **Frog Kudos** 系統 Logo 與品牌名稱。
  - 右側：
    - **模式切換**：`[ 👦 小孩模式 (唯讀) ]` ⇄ `[ 🔐 家長模式 (已解鎖) ]`。
    - **家長安全鎖**：點擊後輸入 4 位數 PIN 碼解鎖管理功能；15 分鐘無操作自動安全鎖定退回小孩模式。
- **主要導航 (Navigation Tabs)**：
  - **小孩模式下**：僅開放 `🏆 榮譽榜與存摺 (Ledger)` 與 `🎁 兌換商城 (Rewards Shop)`（僅能申請兌換）。
  - **家長解鎖後**：完整開放全部 4 大功能：
    1. 📝 **快速登記 (Record)**
    2. 🏆 **榮譽榜與存摺 (Ledger)**
    3. 🎁 **兌換商城與審核 (Rewards & Reviews)**
    4. ⚙️ **規則管理 (Rule Settings)**

---

### 4.2 畫面 1：快速成就登記 (Quick Kudos Entry Form)

最頻繁使用的操作介面，以高對比卡片呈現，支援**「規則匹配推導」**與**「自訂臨時獎懲 (Bonus/Penalty)」**雙模式。

```
+-------------------------------------------------------------------------+
|  🐸 Frog Kudos                [ 🔐 家長模式已解鎖 (剩餘12分) 🔒手動鎖定 ]|
+-------------------------------------------------------------------------+
|  第一步：選擇對象                                                       |
|  +--------------------+  +--------------------+  +-------------------+  |
|  |  [ 🐸 Ian ]        |  |  [ 👧 Amy ]        |  |  [ + 新增成員 ]   |  |
|  |  餘額: 180 點 (選定)|  |  餘額: 95 點       |  |                   |  |
|  +--------------------+  +--------------------+  +-------------------+  |
|                                                                         |
|  登記模式切換:  [ (•) 依規則自動帶出 ]    [ ( ) 自由臨時獎懲 (Bonus/扣點) ]|
|                                                                         |
|  ┌── 【模式 A：依規則自動帶出】 ─────────────────────────────────────┐  |
|  │ 1. 目標項目:  [ 社會科                         ▼ ]                 │  |
|  │ 2. 達成成績:  [ 100                            ] 分                │  |
|  │                                                                   │  |
|  │ ▼ 系統即時比對反饋 (Live Preview Badge)                           │  |
|  │ 🌟 命中規則：【Ian 專屬規則】社會科段考滿分獎勵                   │  |
|  │ 🎁 建議獎勵：[ +50 ] 點 (可直接點擊數字微調)                      │  |
|  └───────────────────────────────────────────────────────────────────┘  |
|  ┌── 【模式 B：自由臨時獎懲 (切換時顯示)】 ──────────────────────────┐  |
|  │ 1. 自訂事項:  [ 主動幫忙照顧弟妹 / 未寫完作業偷看電視          ]   │  |
|  │ 2. 點數增減:  [ +20 / -10                      ] 點 (支援負數扣點) │  |
|  └───────────────────────────────────────────────────────────────────┘  |
|                                                                         |
|  備註說明: [ 表現非常優良，值得肯定！                            ]      |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |             🎉 確認發放點數 / 登記獎懲 (Submit)                   |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
```

#### 互動與視覺反饋細節：
1. **成員卡片動態選取**：點選 Ian 時，卡片放大浮起並帶綠色光暈（Frog Green）。
2. **防呆自動聯想**：在目標項目鍵入「社」，即時出現 `社會科` 快捷標籤可點擊。
3. **即時推導（Debounce 300ms）**：當「社會科」與「100」填寫完成，自動呼叫 `/api/kudos/preview`，即時渲染帶有彈跳淡入動畫的綠色徽章，顯示「+50 點」。
4. **成就慶祝效果**：按下【確認發放】成功時，畫面噴灑 **Canvas Confetti（全螢幕彩帶灑花）**，並播放清脆的金幣音效（可靜音），彈出 Toast 提示「已為 Ian 增加 50 點！目前累積 230 點」。

---

### 4.3 畫面 2：家庭榮譽榜與點數存摺 (Family Dashboard & Ledger)

清晰呈現孩子累積的成果與每一筆歷史快照。

```
+-------------------------------------------------------------------------+
|  🏆 家庭榮譽存摺              [ 區間: 本學期 ▼ ]  [ 📥 匯出存摺 (CSV) ] |
+-------------------------------------------------------------------------+
|  [ 🐸 Ian 的存摺 ]      目前可用: 🪙 230 點     歷史累計總獲: 🌟 480 點  |
|  進度條: [████████████████░░░░] 距下一個大獎 (樂高模型 300 點) 還差 70點 |
+-------------------------------------------------------------------------+
|  🏅 Ian 的榮譽成就勳章牆 (Milestone Badges - FR-18)                     |
|  +----------------+  +----------------+  +----------------+  +--------+ |
|  | 🌟 初出茅廬蛙  |  | 🏆 百分學霸蛙  |  | 🧹 家事小達人  |  | 👑 ... | |
|  | [✨ 已解鎖]    |  | [✨ 已解鎖]    |  | [🔒 120/200點] |  | [🔒]   | |
|  | 累計獲得 100 點|  | 科目滿分達 5 次|  | 生活常規滿200點|  |        | |
|  +----------------+  +----------------+  +----------------+  +--------+ |
+-------------------------------------------------------------------------+
|  點數歷史流水帳 (Immutable Ledger)                                      |
|                                                                         |
|  • 2026-09-27 22:45 | 社會科 (100分)                     [ +50 點 ] 🟢  |
|    備註: 第一次段考滿分 | 登記人: Dad                                   |
|    快照細節: 命中當時規則「Ian 專屬 - 社會科滿分 (條件: >=100, 點數: 50)」 |
|                                                                         |
|  • 2026-09-25 18:20 | 整理房間 (完成)                    [ +10 點 ] 🟢  |
|    備註: 玩具收拾整齊 | 登記人: Mom                                     |
|                                                                         |
|  • 2026-09-24 15:00 | 兌換: 週末玩 Switch 1小時          [ -50 點 ] 🔴  |
|    狀態: 已核銷完成 | 審核人: Dad                                       |
+-------------------------------------------------------------------------+
```

---

### 4.4 畫面 3：獎勵兌換商城與審核中心 (Rewards Shop & Redemptions Review)

支援孩子發起心願兌換，並由家長在線上進行核准兌現或退回退點。

```
+-------------------------------------------------------------------------+
|  🎁 獎勵兌換商城                 [ Ian 目前點數錢包: 🪙 230 點 ]        |
|  分頁切換: [ 🎁 可兌換品項清單 ]   [ 📋 待審核兌換申請 (1) - 家長專區 ] |
+-------------------------------------------------------------------------+
|  【 分頁 1: 可兌換品項清單 】                                           |
|  +------------------------+   +------------------------+                |
|  | 🎮 玩 Switch 1 小時    |   | 🍦 週末吃冰淇淋一球    |                |
|  | 所需點數: 50 點         |   | 所需點數: 30 點         |                |
|  | 說明: 限週末完成作業後  |   | 說明: 任何口味皆可     |                |
|  | [   🟢 申請兌換 (凍結) ]|   | [   🟢 申請兌換 (凍結) ]|                |
|  +------------------------+   +------------------------+                |
|                                                                         |
|  【 分頁 2: 待審核兌換申請 (家長解鎖後顯示) 】                          |
|  ┌───────────────────────────────────────────────────────────────────┐  |
|  │ 🕒 2026-09-27 20:00 申請待審核：                                  │  |
|  │ 成員: 🐸 Ian  | 項目: 🎮 玩 Switch 1 小時 | 消耗點數: 50 點        │  |
|  │ 目前狀態: ⏳ PENDING (點數已暫扣)                                  │  |
|  │                                                                   │  |
|  │ 操作:                                                             │  |
|  │ [ 🟢 核准兌現 (COMPLETED) ]   [ 🔴 退回申請並退點 (REJECTED) ]    │  |
|  │ (退回時系統自動在資料庫交易中全額退還 50 點給 Ian，並附註退回原因)│  |
|  └───────────────────────────────────────────────────────────────────┘  |
+-------------------------------------------------------------------------+
```

#### 兌換流程與交易防呆：
1. **點數檢核與凍結**：若成員可用點數不足，按鈕呈現反灰鎖定狀態，顯示「還差 70 點」，防止超兌；申請時點數先扣除，狀態為 `PENDING`。
2. **核銷或退回退點**：
   - 家長確認兌現：狀態變更為 `COMPLETED`。
   - 家長退回申請：輸入原因後狀態變更為 `REJECTED`，後端 DB Transaction **自動退回點數**（`current_points += points_spent`）。

---

### 4.5 畫面 4：規則管理中心 (Rule Settings)

家長管理各成員規則的後台，明確告知「規則不溯及既往」原則。

```
+-------------------------------------------------------------------------+
|  ⚙️ 獎勵規則設定中心                                                    |
|  ℹ️ 重要提醒：在此修改或刪除規則，只會影響「未來」的新成就，過往已發放的  |
|     點數紀錄已永久快照存檔，絕不會被修改。                              |
+-------------------------------------------------------------------------+
|  規則對象切換: [ 🐸 Ian 專屬 (3) ]  [ 👧 Amy 專屬 (2) ]  [ 🌐 全家通用 (5) ]  |
+-------------------------------------------------------------------------+
|  目前規則列表 (Ian 專屬):                                               |
|                                                                         |
|  • 社會科 | 門檻: >= 100 分  | 獎勵: +50 點  | 狀態: [啟用中]  [編輯] [停用]|
|  • 社會科 | 門檻: >= 90 分   | 獎勵: +20 點  | 狀態: [啟用中]  [編輯] [停用]|
|  • 數學科 | 門檻: >= 100 分  | 獎勵: +50 點  | 狀態: [啟用中]  [編輯] [停用]|
|                                                                         |
|  [ + 為 Ian 新增專屬規則 ]                                              |
+-------------------------------------------------------------------------+
```

---

### 4.6 畫面 5：歷史積分批次篩選與調整工具 (Batch Points Adjuster Modal)

專為家長提供的管理審計工具，整合於「榮譽榜與存摺」右上角之【🛠 批次調整歷史積分】。

```
+-------------------------------------------------------------------------+
|  🛠 批次調整歷史積分 (家長管理工具)                                     |
|  說明：此功能將依篩選條件「統一批次修改」歷史已發放的點數紀錄並同步更新餘額。|
+-------------------------------------------------------------------------+
|  1. 篩選對象 (Member):    [ 🐸 Ian                                ▼ ]   |
|  2. 目標項目 (Target):    [ 社會科                                ▼ ]   |
|  3. 時間區間 (Date Range):[ 2026-09-01 ] 至 [ 2026-09-27 ]              |
|                                                                         |
|  4. 調整模式 (Mode):                                                    |
|     (•) 統一設為固定新點數: 每筆設為 [ 60 ] 點                          |
|     ( ) 統一增減點數:       每筆 [ +10 ] 點                             |
|                                                                         |
|  5. 調整原因 (Reason):    [ 九月份社會科加碼獎勵補發                      ]  |
|                                                                         |
|  [ 🔍 試算影響範圍 (Preview) ]                                          |
|  ┌───────────────────────────────────────────────────────────────────┐  |
|  │ 📊 試算結果：                                                     │  |
|  │ • 符合歷史紀錄：共 3 筆                                           │  |
|  │ • 原發放總點數：150 點 (50 + 50 + 50)                             │  |
|  │ • 調整後總點數：180 點 (60 + 60 + 60)                             │  |
|  │ • 預計變動差額 (Δ)：+30 點 (Ian 餘額將由 230 點變為 260 點)        │  |
|  │ ───────────────────────────────────────────────────────────────── │  |
|  │ 明細預覽:                                                         │  |
|  │  1. 2026-09-10 | 社會科 (100分) : 50 點 ➔ 60 點                   │  |
|  │  2. 2026-09-18 | 社會科 (100分) : 50 點 ➔ 60 點                   │  |
|  │  3. 2026-09-27 | 社會科 (100分) : 50 點 ➔ 60 點                   │  |
|  └───────────────────────────────────────────────────────────────────┘  |
|                                                                         |
|  請輸入家長 PIN 碼: [ **** ]                                            |
|                                                                         |
|  [ 取消 ]                          [ ⚠️ 確認執行批次調整 (+30 點) ]     |
+-------------------------------------------------------------------------+
```

---

### 4.7 畫面 6：系統設定、資料庫備份與升級中心 (System Settings, Backup & Upgrade Modal)

家長可在右上角齒輪選單點選【⚙️ 系統設定與維運】，提供 Web 前端視覺化分頁介面，支援**資料庫自訂路徑備份**與**系統一鍵升級**。

```
+-------------------------------------------------------------------------+
|  ⚙️ 系統管理中心 (家長專區)                                             |
|  [ 💾 資料庫備份與管理 ]  [ 🔄 系統版本與升級 ]  [ 📱 LINE 推播通知 (FR-19) ]|
+-------------------------------------------------------------------------+
|  【 分頁 1: 資料庫備份與管理 】                                         |
|                                                                         |
|  1. 自訂備份目的地路徑:                                                 |
|     [ /home/chinsonyeh/Code/frog_kudos/backups                    ]     |
|     (支援本機目錄、隨身碟或家庭 NAS 儲存路徑)                           |
|     [ 💾 儲存路徑設定 ]                                                 |
|                                                                         |
|  2. 立即備份:                                                           |
|     輸入家長 PIN: [ **** ]    [ 📦 立即建立資料庫完整備份 ]             |
|                                                                         |
|  ┌───────────────────────────────────────────────────────────────────┐  |
|  │ ✅ 備份成功！檔案: frog_kudos_backup_20260927_232500.dump (42 KB) │  |
|  └───────────────────────────────────────────────────────────────────┘  |
|  3. 定期自動備份排程與輪替:                                             |
|     自動備份開關: [ (•) 開啟  ( ) 關閉 ]                                 |
|     排程頻率: 每週日深夜 02:00 自動執行                                  |
|     保留備份份數: [ 10 ] 份 (超過時自動清理舊備份)                       |
|     [ 💾 儲存排程設定 ]                                                 |
|                                                                         |
|  📁 歷史備份清單:                                                       |
|  ┌───────────────────────────────────────────────────────────────────┐  |
|  │ • 2026-09-27 23:25 | frog_kudos_backup_20260927_232500.dump (42 KB)│  |
|  │ • 2026-09-26 18:00 | frog_kudos_backup_20260926_180000.dump (38 KB)│  |
|  └───────────────────────────────────────────────────────────────────┘  |
|  💡 還原提醒：為保障資料安全，請於伺服器終端機執行：                    |
|     $ ./scripts/restore.sh <備份檔案絕對路徑>                            |
+-------------------------------------------------------------------------+
|  【 分頁 2: 系統版本與一鍵升級 (GitHub Releases) 】                     |
|                                                                         |
|  目前安裝版本: v1.0.0                                                   |
|  GitHub 儲存庫: https://github.com/chinsonyeh/frog_kudos                |
|  [ 🔍 檢查 GitHub 最新 Release (Check Updates) ]                        |
|                                                                         |
|  ┌───────────────────────────────────────────────────────────────────┐  |
|  │ 🚀 發現新版本！最新正式發行版: v1.1.0 (發佈於 2026-09-27)          │  |
|  │ 📦 官方發行包: frog_kudos-v1.1.0.tar.gz (內建前端免編譯)           │  |
|  │ 📝 更新日誌 (Changelog):                                           │  |
|  │  • 新增歷史積分批次統一調整功能 (FR-7)                             │  |
|  │  • 新增資料庫自訂路徑備份與 Web 端 UI 管理 (FR-8)                  │  |
|  │  • 支援 GitHub Releases 一鍵自動升級與離線包手動安裝               │  |
|  └───────────────────────────────────────────────────────────────────┘  |
|                                                                         |
|  模式 A：從 GitHub 自動下載並升級                                       |
|  輸入家長 PIN: [ **** ]                                                 |
|  [ 🚀 立即從 GitHub 下載並執行自動平滑升級 ]                            |
|                                                                         |
|  模式 B：手動/離線套件升級                                               |
|  [ 選擇本機 frog_kudos-*.tar.gz 升級包 ]  [ 📤 上傳並執行升級 ]         |
|  (若家庭伺服器無對外網路，可先手動從 GitHub 下載發行包後在此上傳)       |
|                                                                         |
|  ▼ 即時升級進度顯示 (即時輪詢 /api/system/upgrade-status):              |
|  進度: [████████████████████░░░░░░░░] 75%                              |
|  目前步驟: 正在解壓縮新版發行包並執行資料庫 Migration...                |
+-------------------------------------------------------------------------+
|  【 分頁 3: 📱 LINE 外部即時推播通知設定 (FR-19) 】                     |
|                                                                         |
|  說明：設定 LINE Messaging API 憑證，當孩子於商城申請兌換時即時推播至家長手機。|
|                                                                         |
|  1. LINE Channel Access Token:                                          |
|     [ eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...                         ] |
|  2. 家長 LINE User ID / Group ID:                                       |
|     [ U1234567890abcdef1234567890abcdef                              ] |
|                                                                         |
|  輸入家長 PIN: [ **** ]                                                 |
|  [ 💾 儲存通知設定 ]        [ 📨 發送測試訊息 (Verify Connection) ]      |
|  ┌───────────────────────────────────────────────────────────────────┐  |
|  │ ✅ 測試推播已發送成功！請檢查家長手機 LINE 聊天室。                │  |
|  └───────────────────────────────────────────────────────────────────┘  |
|                                                                         |
|  [ 關閉 ]                                                               |
+-------------------------------------------------------------------------+
```

---

### 4.8 PWA (Progressive Web App) 行動裝置原生化規格

為讓家庭成員在手機或 iPad 上如同使用原生 App，前端深度整合 PWA 技術：
1. **Web App Manifest (`frontend/public/manifest.webmanifest`)**：
   - `name`: "Frog Kudos 家庭積分獎勵系統"
   - `short_name`: "Frog Kudos"
   - `start_url`: "/"
   - `display`: "standalone"（隱藏瀏覽器網址列與工具列，提供沉浸式獨立 App 體驗）
   - `theme_color`: "#10B981"（清新青蛙綠）
   - `background_color`: "#F9FAFB"
   - `icons`: 提供 192x192 與 512x512 高解析度 🐸 圖示。
2. **iOS Safari 最佳化支援**：
   - 注入 `<meta name="apple-mobile-web-app-capable" content="yes">`
   - 注入 `<link rel="apple-touch-icon" href="/icons/icon-192.png">`
   - 家長與孩子只需於 Safari 點擊「分享 ➔ 加入主畫面」，即可常駐於手機桌面隨點即用。

---

## 5. PostgreSQL DDL 建表腳本 (預備執行腳本)

本腳本規劃於審查通過後，在 `frog_kudos` 資料庫中執行：

```sql
-- 1. 啟用 UUID 擴充功能
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. 成員表
CREATE TABLE IF NOT EXISTS members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    role VARCHAR(20) NOT NULL DEFAULT 'child',
    avatar VARCHAR(100) DEFAULT '🐸',
    current_points INTEGER NOT NULL DEFAULT 0 CHECK (current_points >= 0),
    total_earned_points INTEGER NOT NULL DEFAULT 0 CHECK (total_earned_points >= 0),
    pin_code VARCHAR(60),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. 分類表
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    icon VARCHAR(50) DEFAULT '📚',
    sort_order INTEGER NOT NULL DEFAULT 0
);

-- 4. 獎勵規則表 (支援特定成員或全家通用)
CREATE TABLE IF NOT EXISTS reward_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID REFERENCES members(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    target_name VARCHAR(100) NOT NULL,
    match_type VARCHAR(20) NOT NULL DEFAULT 'NUM_GTE', -- 'NUM_GTE', 'NUM_EQ', 'EXACT'
    condition_value VARCHAR(50) NOT NULL,
    reward_points INTEGER NOT NULL CHECK (reward_points >= 0),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. 點數獲得快照紀錄表 (核心快照，不可溯及修改，支援家長批次統一調整)
CREATE TABLE IF NOT EXISTS kudos_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
    rule_id UUID REFERENCES reward_rules(id) ON DELETE SET NULL,
    target_name_snapshot VARCHAR(100) NOT NULL,
    condition_snapshot VARCHAR(100) NOT NULL DEFAULT '自訂',
    points_awarded INTEGER NOT NULL,
    rule_detail_snapshot JSONB,
    note TEXT,
    adjustment_note TEXT,
    recorded_by VARCHAR(50) NOT NULL DEFAULT 'Parent',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. 兌換商城品項表
CREATE TABLE IF NOT EXISTS reward_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(100) NOT NULL,
    description TEXT,
    cost_points INTEGER NOT NULL CHECK (cost_points > 0),
    icon VARCHAR(50) DEFAULT '🎁',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. 兌換紀錄表
CREATE TABLE IF NOT EXISTS redemptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
    item_id UUID REFERENCES reward_items(id) ON DELETE SET NULL,
    item_title_snapshot VARCHAR(100) NOT NULL,
    points_spent INTEGER NOT NULL CHECK (points_spent > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'COMPLETED', 'REJECTED'
    review_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ
);

-- 8. 成員成就勳章解鎖紀錄表 (FR-18)
CREATE TABLE IF NOT EXISTS member_badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    badge_key VARCHAR(50) NOT NULL,
    unlocked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (member_id, badge_key)
);

-- 9. 效能索引
CREATE INDEX IF NOT EXISTS idx_rules_member_active ON reward_rules(member_id, is_active);
CREATE INDEX IF NOT EXISTS idx_kudos_records_member_created ON kudos_records(member_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_kudos_batch_filter ON kudos_records(member_id, target_name_snapshot, created_at);
CREATE INDEX IF NOT EXISTS idx_redemptions_member_created ON redemptions(member_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_member_badges_member ON member_badges(member_id);

-- 10. 系統預設種子分類資料 (Categories Initial Seed Data)
INSERT INTO categories (name, icon, sort_order) VALUES
    ('學業成績', '📚', 1),
    ('生活常規', '🌱', 2),
    ('家事協助', '🧹', 3),
    ('運動健康', '🏃', 4)
ON CONFLICT (name) DO NOTHING;
```

---

## 6. 資料庫備份、還原與維運自動化腳本 (Backup, Restore, Install & Upgrade)

本系統提供獨立的維運腳本目錄 `scripts/`，同時在 Web 前端家長後台（畫面 4.7）提供視覺化 UI 設定介面。當家長在 Web 介面發起「立即備份」或「一鍵升級」時，FastAPI 後端以非同步背景程序（Background Process）觸發對應腳本，並透過 `/api/system/upgrade-status` 即時串流進度回傳前端，達成 **Web 前端圖形介面** 與 **伺服器終端機 CLI** 雙軌無縫支援。

### 6.1 資料庫指定路徑備份機制 (`scripts/backup.sh`)
- **功能**：使用 PostgreSQL 原生 `pg_dump` 建立高壓縮 Custom 格式（`.dump`）備份檔。
- **自訂目標路徑**：支援命令列傳入目標目錄（若未傳入則讀取 `.env` 中的 `BACKUP_DIR`，預設為專案目錄下之 `backups/`）。
- **腳本內容設計**：
```bash
#!/usr/bin/env bash
set -euo pipefail

# 載入環境變數
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

DB_NAME="${DB_NAME:-frog_kudos}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# 取得指定目標路徑 (第 1 個引數)，若無指定則預設讀取 BACKUP_DIR 或 $ROOT_DIR/backups
TARGET_DIR="${1:-${BACKUP_DIR:-$ROOT_DIR/backups}}"
mkdir -p "$TARGET_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${TARGET_DIR}/frog_kudos_backup_${TIMESTAMP}.dump"

echo "📦 開始備份資料庫 [${DB_NAME}] 至目標路徑: ${BACKUP_FILE} ..."
# 安全注入資料庫密碼至子程序環境變數 (避免 ps aux 明文洩漏，NFR-4)
export PGPASSWORD="${DB_PASSWORD:-}"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc "$DB_NAME" > "$BACKUP_FILE"
unset PGPASSWORD

# 鎖定備份檔案權限為 600
chmod 600 "$BACKUP_FILE"

FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "✅ 備份成功！檔案大小: ${FILE_SIZE}"
echo "📍 完整備份路徑: ${BACKUP_FILE}"

# 執行備份保留輪替 (Retention Cleanup，預設保留最新 10 份)
RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-10}"
BACKUP_LIST=$(ls -1t "$TARGET_DIR"/frog_kudos_backup_*.dump 2>/dev/null || true)
TOTAL_BACKUPS=$(echo "$BACKUP_LIST" | grep -c . || true)
if [ "$TOTAL_BACKUPS" -gt "$RETENTION_COUNT" ]; then
    echo "🧹 執行備份輪替清理 (超過保留上限 ${RETENTION_COUNT} 份)..."
    echo "$BACKUP_LIST" | tail -n +$((RETENTION_COUNT + 1)) | while IFS= read -r old_file; do
        if [ -f "$old_file" ]; then
            echo "   🗑️ 刪除過期舊備份: $(basename "$old_file")"
            rm -f "$old_file"
        fi
    done
fi
```

### 6.2 資料庫安全還原腳本 (`scripts/restore.sh`)
- **功能**：使用 `pg_restore` 還原資料庫，具備**前置安全快照**與**二次輸入確認**機制。
- **腳本內容設計**：
```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ -z "${1:-}" ]; then
    echo "❌ 錯誤: 請指定要還原的備份檔案路徑！"
    echo "使用範例: ./scripts/restore.sh /path/to/frog_kudos_backup_20260927_120000.dump"
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

echo "⚠️  【危險警告】即將把備份檔案還原至資料庫 [${DB_NAME}]！"
echo "⚠️  現有所有資料將會被該備份覆蓋！"
echo "備份檔案: $BACKUP_FILE"
read -p "確定要繼續執行還原嗎？(請輸入 YES 確認): " CONFIRM
if [ "$CONFIRM" != "YES" ]; then
    echo "🛑 已取消還原作業。"
    exit 0
fi

# 1. 還原前自動建立安全快照，避免誤操作
SNAPSHOT_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
mkdir -p "$SNAPSHOT_DIR"
PRE_RESTORE_BACKUP="${SNAPSHOT_DIR}/pre_restore_snapshot_$(date +"%Y%m%d_%H%M%S").dump"
echo "🛡️ 正在建立還原前安全快照: ${PRE_RESTORE_BACKUP} ..."

# 安全注入資料庫密碼至子程序環境變數 (避免 ps aux 明文洩漏，NFR-4)
export PGPASSWORD="${DB_PASSWORD:-}"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc "$DB_NAME" > "$PRE_RESTORE_BACKUP" || true
chmod 600 "$PRE_RESTORE_BACKUP" 2>/dev/null || true

# 2. 執行還原 (使用 --clean --if-exists 清除舊表後乾淨恢復)
echo "🔄 開始執行資料庫還原..."
pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --clean --if-exists "$BACKUP_FILE"
unset PGPASSWORD

echo "✅ 資料庫還原成功！已恢復至備份時間點。"
```

### 6.3 系統一鍵安裝腳本 (`scripts/install.sh`)
- **功能**：自動檢查主機 Python/Node/PostgreSQL 環境、初始化資料庫、建置 Python 虛擬環境、打包前端並生成單一 Port 啟動器。
- **腳本內容設計**：
```bash
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

# 2. 決定並驗證運行連接埠 (Port)
DEFAULT_PORT="8000"
INPUT_PORT="${PORT:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)
            INPUT_PORT="$2"
            shift 2
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
    cat << EOF > "$ROOT_DIR/.env"
DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/frog_kudos
DB_NAME=frog_kudos
DB_USER=postgres
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432
PORT=${CHOSEN_PORT}
BACKUP_DIR=/home/chinsonyeh/Code/frog_kudos/backups
PARENT_DEFAULT_PIN=0000
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

# 4. 初始化 PostgreSQL frog_kudos 資料庫結構
echo "🐘 步驟 3/5: 初始化資料庫結構..."
export PGPASSWORD="${DB_PASSWORD:-}"
# 自動防呆檢查資料庫是否存在，若無則自動建立
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" 2>/dev/null | grep -q 1 || \
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || true
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$ROOT_DIR/schema.sql"
unset PGPASSWORD

# 5. 建置後端 Python 虛擬環境
echo "🐍 步驟 4/5: 建置 Python 虛擬環境並安裝依賴..."
cd "$ROOT_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 6. 前端相依安裝與打包編譯 (支援單一 Port 託管)
echo "🎨 步驟 5/5: 安裝前端套件並編譯生產環境資源 (npm run build)..."
cd "$ROOT_DIR/frontend"
npm install
npm run build

echo "🎉 Frog Kudos 安裝完成！"
echo "👉 執行 ./run.sh 即可啟動系統 (瀏覽器開啟: http://localhost:${CHOSEN_PORT})"
```

### 6.4 GitHub Release 打包計畫與 CI/CD 自動化 (`.github/workflows/release.yml`)

為實現「主機端免裝 Node.js/npm、開箱即用、版本明確」，每次發佈新版本時透過 GitHub Actions 自動打包生產環境發行包：

1. **打包套件內容 (`frog_kudos-vX.Y.Z.tar.gz`)**：
   ```
   frog_kudos-vX.Y.Z/
   ├── app/                   # FastAPI 後端核心代碼
   ├── frontend/
   │   └── dist/              # 預先在 GitHub Actions 編譯完成的 Vue 3 靜態網頁資源
   ├── scripts/               # 運維工具 (backup.sh, restore.sh, install.sh, upgrade.sh)
   ├── schema.sql             # 資料庫 DDL 建表與初始資料腳本
   ├── requirements.txt       # Python 生產環境套件依賴
   ├── run.sh                 # 單一 Port 一鍵啟動入口腳本
   └── VERSION                # 當前發行版本字串 (例如 v1.1.0)
   ```
   - **重大優勢**：生產環境家庭伺服器**完全不需要安裝 Node.js 與 npm**，也不需在低功耗主機上承受耗時的前端編譯，只需 Python 3.12+ 與 PostgreSQL 即可極速部署與升級。

2. **GitHub Actions 流程定義 (`.github/workflows/release.yml`)**：
   ```yaml
   name: Release Build and Packaging

   on:
     push:
       tags:
         - 'v*'

   jobs:
     build-and-release:
       runs-on: ubuntu-latest
       permissions:
         contents: write
       steps:
         - name: Checkout Code
           uses: actions/checkout@v4

         - name: Setup Node.js
           uses: actions/setup-node@v4
           with:
             node-version: 18

         - name: Build Vue 3 Frontend
           run: |
             cd frontend
             npm ci
             npm run build

         - name: Prepare Release Package
           run: |
             VERSION=${GITHUB_REF_NAME}
             echo "$VERSION" > VERSION
             mkdir -p release_package
             tar --exclude='.git' \
                 --exclude='frontend/node_modules' \
                 --exclude='frontend/src' \
                 --exclude='venv' \
                 --exclude='.env' \
                 -czvf "frog_kudos-${VERSION}.tar.gz" \
                 app frontend/dist scripts schema.sql requirements.txt run.sh VERSION
             sha256sum "frog_kudos-${VERSION}.tar.gz" > "frog_kudos-${VERSION}.tar.gz.sha256"

         - name: Create GitHub Release
           uses: softprops/action-gh-release@v2
           with:
             files: |
               frog_kudos-${{ github.ref_name }}.tar.gz
               frog_kudos-${{ github.ref_name }}.tar.gz.sha256
             generate_release_notes: true
   ```

---

### 6.5 系統雙軌平滑升級腳本 (`scripts/upgrade.sh`)
- **功能**：支援**模式 A（自動連線 GitHub Releases 下載最新版）**與**模式 B（手動/離線傳入本地發行包）**。
- **腳本內容設計**：
```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PACKAGE_ARG="${1:-}"  # 可為本地檔案路徑或留空自動從 GitHub 取得
GITHUB_REPO="chinsonyeh/frog_kudos"
TMP_DIR="/tmp/frog_kudos_upgrade_$(date +%s)"
mkdir -p "$TMP_DIR"

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
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$ROOT_DIR/schema.sql" || true
unset PGPASSWORD

# 6. 清理暫存檔並完成
rm -rf "$TMP_DIR"
NEW_VER=$(cat "$ROOT_DIR/VERSION" 2>/dev/null || echo "unknown")
echo "🎉 系統已成功升級至版本: $NEW_VER！"
echo "👉 若以背景服務運行，請執行重啟命令完成切換。"
```

---

## 7. 需求對應檢核與總結 (Requirements Traceability & Summary)

### 7.1 需求規格對應檢核矩陣 (Traceability Matrix)

本詳細設計文件已逐項落實 [REQUIREMENT.md](./REQUIREMENT.md) 中定義之所有功能與非功能需求：

| 需求代號 | 需求項目名稱 | 設計對應之資料表 / 檔案 | 設計對應之後端 API / 演算法 | 設計對應之前端 Web UI 畫面 | 檢核結果 |
|---|---|---|---|---|---|
| **FR-1** | 多成員帳號管理 | `members` 表 | `GET /api/members`<br>`POST /api/members` | 頁面頂部大頭像成員切換卡片 | ✅ 100% 符合 |
| **FR-2** | 個別化客製獎勵規則 | `reward_rules`, `categories` | `GET/POST/PUT/DELETE /api/rules` | 畫面 4：規則管理中心（成員專屬/通用分頁） | ✅ 100% 符合 |
| **FR-3** | 快速成就登記與智慧自動帶出 | `reward_rules`, `kudos_records` | `POST /api/kudos/preview`<br>(3.1 規則推導演算法) | 畫面 1：快速登記卡（即時試算徽章與灑花動畫） | ✅ 100% 符合 |
| **FR-4** | 積分快照與歷史不可篡改機制 | `kudos_records` (快照欄位組) | `POST /api/kudos/record` | 畫面 2：歷史存摺清單（展示當時規則快照細節） | ✅ 100% 符合 |
| **FR-5** | 獎勵商城與兌換機制 | `reward_items`, `redemptions` | `POST /api/redemptions`<br>(原子扣點與防負數檢查) | 畫面 3：獎勵兌換商城（錢包餘額、防超兌鎖定） | ✅ 100% 符合 |
| **FR-6** | 家庭榮譽榜與點數存摺 | `kudos_records`, `members` | `GET /api/kudos/history` | 畫面 2：榮譽榜存摺（可用餘額、累計總額、願望進度條） | ✅ 100% 符合 |
| **FR-7** | 歷史積分批次篩選與統一修改 | `kudos_records` (`adjustment_note`)<br>`idx_kudos_batch_filter` | `POST /api/kudos/batch-preview`<br>`POST /api/kudos/batch-adjust` (3.3 演算法) | 畫面 5：歷史積分批次調整彈窗（多條件篩選與預覽） | ✅ 100% 符合 |
| **FR-8** | 資料庫自訂路徑備份與還原 | `scripts/backup.sh`<br>`scripts/restore.sh` | `POST /api/system/backup`<br>`GET /api/system/backups` | 畫面 6：分頁 1 備份管理（自訂路徑、立即備份、清單） | ✅ 100% 符合 |
| **FR-9** | 系統平滑升級與 GitHub Releases 整合 | `scripts/upgrade.sh` | `GET /api/system/version`<br>`POST /api/system/upgrade` | 畫面 6：分頁 2 系統升級（檢查更新、Changelog、進度條） | ✅ 100% 符合 |
| **FR-10**| GitHub Release 自動化打包發佈 | `.github/workflows/release.yml` | GitHub Actions CI/CD 自動構建 | 發行包內建編譯後 `dist/`，主機免裝 Node/npm | ✅ 100% 符合 |
| **FR-11**| 安裝時使用者自訂連接埠 | `scripts/install.sh`, `.env`, `run.sh` | 支援 `--port` 與互動式輸入、佔用防呆 | 後端單一 Port 整合託管自訂 Port | ✅ 100% 符合 |
| **FR-12**| PWA 行動裝置主畫面應用支援 | `frontend/public/manifest.webmanifest` | Web App Manifest、iOS Safari meta | 全螢幕原生 App 體驗、桌面圖示 | ✅ 100% 符合 |
| **FR-13**| 客廳共用裝置家長鎖與小孩模式 | 前端狀態機 Pinia / SessionStorage | 家長 PIN 碼認證、15 分鐘閒置自動鎖定 | 頂部模式切換開關、自動隱藏管理選單 | ✅ 100% 符合 |
| **FR-14**| 自訂臨時特別獎勵與違規扣點 | `kudos_records` (支援負數點數) | `POST /api/kudos/record` (自訂模式) | 畫面 1：自由臨時獎懲切換卡片 | ✅ 100% 符合 |
| **FR-15**| 兌換商城審核與退回退點閉環 | `redemptions` (`PENDING` 狀態) | `POST /api/redemptions/{id}/review` | 畫面 3：分頁 2 家長審核卡片 (核銷/自動退點) | ✅ 100% 符合 |
| **FR-16**| 定期自動備份排程與保留輪替 | `scripts/backup.sh`, `.env` | 後端定時任務 + 備份上限輪替清理 | 畫面 6：分頁 1 自動排程與保留上限設定 | ✅ 100% 符合 |
| **FR-17**| 學期成就紀錄與存摺 CSV 匯出 | `kudos_records` | `GET /api/kudos/export` | 畫面 2：【📥 匯出存摺 (CSV)】按鈕 | ✅ 100% 符合 |
| **FR-18**| 里程碑成就勳章系統 | `member_badges` 表 | `GET /api/members/{id}/badges`<br>成就評定邏輯 | 畫面 2：榮譽榜成就勳章牆、解鎖彈窗與灑花 | ✅ 100% 符合 |
| **FR-19**| LINE 兌換申請即時推播通知 | 後端 `BackgroundTasks` + LINE Messaging API | `POST /api/redemptions`<br>`POST /api/system/line/test` | 畫面 6：分頁 3 LINE 推播設定與連線測試 | ✅ 100% 符合 |
| **NFR-1**| 易用性與行動裝置友善 | Vue 3 + TailwindCSS | - | RWD 手機/平板優先、大觸控區塊、灑花慶祝反饋 | ✅ 100% 符合 |
| **NFR-2**| 資料交易一致性 (ACID) | PostgreSQL DB Transaction | 點數發放/扣抵/批次調整均於單一 Transaction 完成 | - | ✅ 100% 符合 |
| **NFR-3**| 資料庫與環境相容性 | PostgreSQL `frog_kudos` | SQLAlchemy 2.0 Async + asyncpg | - | ✅ 100% 符合 |
| **NFR-4**| 機敏憑證與資料庫密碼安全防護 | `.env` (`chmod 600`), `scripts/` | `PGPASSWORD` 安全銷毀、API 脫敏、日誌連線字串遮蔽 | 前端設定 API 零密碼洩漏、備份檔 600 權限鎖定 | ✅ 100% 符合 |

---

### 7.2 總結與後續實作準備

本架構設計文件完整落實：
1. **主機 PostgreSQL `frog_kudos` 資料庫設計**：清楚標明 PK、FK 關聯約束、快照儲存與防負數 Check 限制。
2. **前後端技術定案**：採用 **Python FastAPI** + **Vue 3 (Composition API + TailwindCSS)**。
3. **單一 Port 整合運行（安裝時可自訂指定）**：平日家庭日常使用由 FastAPI 在單一連接埠（安裝時可自由指定，預設 Port 8000）同時提供 Vue 3 SPA 網頁與 RESTful APIs，徹底避免 Port 衝突且家庭裝置連線最簡便。
4. **Web UI 詳細規格**：包含快速登記、即時試算動畫反饋、兌換商城、不可篡改存摺、歷史批次調整工具、系統設定與維運中心。
5. **完整維運與 Release 發行自動化**：包含指定路徑資料庫備份 (`backup.sh`)、安全還原 (`restore.sh`)、一鍵安裝 (`install.sh`)、GitHub Actions 自動化發行包打包 (`.github/workflows/release.yml`)、以及從 GitHub Releases 一鍵自動升級與離線套件手動升級 (`upgrade.sh`)。
6. **五重安全防護體系**：涵蓋 `.env` 檔案權限鎖定、進程安全隔離、API 與日誌脫敏。

計畫已就緒，待您確認審查通過後，我們將立即從 **Phase 1（建立資料庫結構與初始種子資料）** 正式開始實作。

---

## 8. 資料庫密碼與機敏憑證安全防護架構 (Database Password & Credential Security)

為確保家庭主機運行時機敏憑證的安全性，系統嚴格實施「五重防護層級」：

### 8.1 實體儲存隔離與嚴格檔案權限 (`.env` & `chmod 600`)
- **隔離存放**：資料庫連線帳號與密碼（`DB_PASSWORD`）、LINE Channel Access Token 與家長預設 PIN 碼等機敏設定**僅持久化於專案根目錄 `.env` 檔案**中，禁止在任何 Python 程式碼或腳本中硬編碼（Hardcode）。
- **權限鎖定**：安裝腳本（`scripts/install.sh`）在建立或更新 `.env` 時，強制執行：
  ```bash
  chmod 600 "$ROOT_DIR/.env"
  ```
  確保僅有執行該程式的 Linux 系統帳號具備讀寫權限，阻絕同機其他一般使用者、訪客或背景程序的未授權讀取。
- **版本庫與發行包排除**：
  - `.gitignore` 嚴格將 `.env`、`*.dump`、`venv/` 納入忽略清單。
  - GitHub Actions 發行打包腳本（`.github/workflows/release.yml`）打包時明確 `--exclude='.env'`，防止機敏密碼洩漏至 GitHub 或公開發行包。

### 8.2 進程防窺與安全認證（防止 `ps aux` 洩漏）
- 在 Linux 多行程環境下，若使用命令列引數傳遞密碼（如 `--password <pass>`），同主機任何使用者皆可透過 `ps aux` 查閱到明文。
- **子程序生命週期隔離**：在資料庫備份（`scripts/backup.sh`）與還原（`scripts/restore.sh`）執行 `pg_dump` / `pg_restore` 前，僅透過環境變數傳入子程序：
  ```bash
  export PGPASSWORD="${DB_PASSWORD:-}"
  pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc "$DB_NAME" > "$BACKUP_FILE"
  unset PGPASSWORD # 執行完畢立即銷毀
  ```
  執行結束立即 `unset`，密碼不留存於終端機歷史紀錄或進程列表。

### 8.3 Web API 憑證零洩漏脫敏 (API Sanitization)
- 前端透過 `GET /api/system/config` 查詢系統設定時，後端 Pydantic Response Schema 嚴格過濾：
  - 僅回傳 `db_name`、`db_host`、`db_port` 與 `line_configured: bool`。
  - **資料庫密碼（`DB_PASSWORD`）與 LINE Token 絕不向前端回傳**。
  - 避免家庭成員或小孩透過瀏覽器開發者工具（F12 / Network Tab）窺探資料庫憑證。

### 8.4 系統日誌與連線字串脫敏 (Logging Sanitization)
- 後端 FastAPI 服務啟動、記錄連線或打印錯誤堆疊追蹤（Traceback）時，若涉及資料庫連線字串，必須使用 SQLAlchemy 內建安全脫敏方法：
  ```python
  safe_db_url = engine.url.render_as_string(hide_password=True)
  logger.info(f"Database connected to: {safe_db_url}")
  # 輸出範例: postgresql+asyncpg://postgres:***@localhost:5432/frog_kudos
  ```
- 升級進度日誌（`GET /api/system/upgrade-status`）中絕不輸出任何包含帳密的連線字串。

### 8.5 備份檔案權限安全 (Backup Files Permissions)
- `scripts/backup.sh` 與還原前快照所產生的 `.dump` 檔案，生成當下自動執行 `chmod 600 "$BACKUP_FILE"`，確保備份檔案僅有系統擁有者可讀寫。
- PostgreSQL Custom dump 檔案僅儲存關聯資料與結構，不包含 PostgreSQL 伺服器登入帳號密碼。
