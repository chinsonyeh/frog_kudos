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

## 📚 相關設計文件

- [系統架構設計文件 (ARCHITECTURE.md)](./ARCHITECTURE.md) - 詳細 Mermaid 資料庫實體關聯 (ERD)、API 規格、Vue 3 介面線框圖與 DDL 腳本。
- [系統規劃書 (docs/PLAN.md)](./docs/PLAN.md) - 需求分析、Vue 3 vs React 技術評估與執行階段計畫。
