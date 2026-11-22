# iPhone 動態島與 WebLoader 安全區域（Safe Area）UI 適配實作計畫

> **建立日期**：2026-11-22  
> **目標系統**：Frog Kudos 家庭積分獎勵系統（Vue 3 + Vite + Tailwind CSS 3）  
> **基準版本**：`v1.0.4`（Commit `87134bc`）  
> **測試/部署主機**：`192.168.50.3`（開發：`~/Code/frog_kudos` / 正式：`~/frog_kudos`）

---

## 1. 背景與問題描述

當使用者在具備 **動態島（Dynamic Island）** 或 **瀏海（Notch）** 的 iPhone 上，透過 **WebLoader 類型的全螢幕網頁載入程式**（底層多為 iOS `WKWebView`）或 PWA 獨立模式開啟 Frog Kudos 時，頁面上方內容容易被動態島與系統狀態列遮擋，導致頂部導覽列與彈窗右上角關閉按鈕難以辨識與點擊。

### 1.1 現況架構根因分析

1. **已宣告 `viewport-fit=cover`，但全站尚未套用 `env(safe-area-inset-*)`**
   - `frontend/index.html`（第 5 行）已設定 `viewport-fit=cover`，會使 iOS WebKit 將畫面延伸至實體螢幕邊緣（覆蓋頂部約 `59px` 動態島 / `47px` 瀏海與底部約 `34px` Home Indicator）。
   - 然而 `frontend/src/` 所有樣式與元件均未使用 `env(safe-area-inset-top/bottom/left/right)`。
2. **頂部導覽列直接貼齊 `y = 0`**
   - `frontend/src/components/Navbar.vue`（第 66–68 行）使用 `<header class="sticky top-0 z-40 ...">` 與 `h-16`（`64px`），Logo、標題、身分模式膠囊與 `🎨`/`⚙️` 按鈕會直接落入動態島遮蔽區。
3. **全螢幕彈窗（Modal）未考量上下安全區（共 12 個檔案、14 處遮罩）**
   - 所有彈窗外層皆為 `fixed inset-0 ... p-4`，內層高度上限為 `max-h-[90vh]` 或 `max-h-[92vh]`。
   - 在 iPhone 15 / 16（視窗高約 `852px`）上，`92vh` 上下僅各剩約 `34px`，小於動態島高度（`~59px`），長內容彈窗的標題列與 `✕` 關閉鈕可能被動態島遮住。
4. **行動端導覽列結構偏高**
   - `frontend/src/components/Navbar.vue`（第 194–219 行）的行動端導覽列雖註解為「底部快速導航」，但實際仍位於頂部 `<header>` 內。加上頂部安全區後，頂部 sticky 區塊總高將達約 `59 + 64 + 52 ≈ 175px`（超過螢幕高度 20%）。
5. **低耦合優勢**
   - 盤點 `frontend/src/views/` 下所有頁面（`GuideView`、`LedgerView`、`QuickEntryView`、`RewardsView`、`RulesView`），**均無次級 `sticky top-16` 定位元件**，調整 `<header>` 高度與安全區不會引發頁面內部錯位。

### 1.2 WebLoader 類程式的兩種底層行為

| 情境 | iOS `WKWebView` 行為 | `env(safe-area-inset-top)` 實測值 | 對應處理策略 |
| :--- | :--- | :--- | :--- |
| **情境 A（標準 WKWebView / PWA）** | 畫面延伸至實體邊緣，且正確向 WebKit 傳遞 Safe Area | 動態島約 `59px`、瀏海約 `47px`、一般瀏覽器 `0px` | **第一層**：標準 CSS `env(safe-area-inset-*)` 自動避讓 |
| **情境 B（非標準 WebLoader）** | 原生層設為無視 Safe Area（如 `contentInsetAdjustmentBehavior = .never`），畫面延伸至動態島下，但未傳遞安全區給網頁 | 永遠回傳 `0px` | **第二層**：URL 參數 + 本機裝置設定 + 謹慎滿版偵測備援 |

> **關鍵原則**：**不可**為了避開動態島而單純移除 `viewport-fit=cover`。在多數強制全螢幕的 WebLoader 中，移除 `viewport-fit=cover` 不會縮回視窗，反而會使 WebKit 強制將 `env(safe-area-inset-top)` 歸零，失去自動適配能力。

---

## 2. 分層架構設計

採用 **三層式漸進改造**：第一、二層為核心必做項目，第三層為選配的行動端體驗升級。

### 第一層（必做）：標準 Safe Area CSS 系統

#### 2.1 統一 CSS 變數與工具類別（`frontend/src/style.css`）
在 `:root` 建立統一的安全區變數層，所有元件只引用 `--app-safe-*`：

```css
:root {
  --safe-top: env(safe-area-inset-top, 0px);
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  --safe-left: env(safe-area-inset-left, 0px);
  --safe-right: env(safe-area-inset-right, 0px);

  /* 第二層 WebLoader 備援覆寫值（預設 0px，由 URL 參數或本機設定注入） */
  --top-inset-override: 0px;

  /* 實際生效的頂部安全距離：取系統值與備援值之較大者 */
  --app-safe-top: max(var(--safe-top), var(--top-inset-override));
  --app-safe-bottom: var(--safe-bottom);
  --app-safe-left: var(--safe-left);
  --app-safe-right: var(--safe-right);
}
```

同時於 `@layer utilities` 定義共用類別，避免重複散落 inline style：
- `.pt-safe-top`：`padding-top: var(--app-safe-top);`
- `.pb-safe-bottom`：`padding-bottom: var(--app-safe-bottom);`
- `.px-safe`：`padding-left: var(--app-safe-left); padding-right: var(--app-safe-right);`
- `.modal-safe-backdrop`：
  ```css
  .modal-safe-backdrop {
    padding-top: calc(1rem + var(--app-safe-top));
    padding-bottom: calc(1rem + var(--app-safe-bottom));
    padding-left: calc(1rem + var(--app-safe-left));
    padding-right: calc(1rem + var(--app-safe-right));
  }
  ```

#### 2.2 頂部導覽列改造（`frontend/src/components/Navbar.vue`）
- **將頂部安全間距加在 `<header>` 本身，而非 `<body>`**：
  - `<header>` 維持 `sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-gray-100 shadow-sm`，新增 `pt-safe-top px-safe`。
  - **設計理由**：
    1. 畫面在頂端時，毛玻璃背景無縫延伸至動態島後方，呈現原生 iOS App 視覺質感。
    2. 往下捲動時，`<header>` 持續固定在 `top: 0`，安全區 padding 不會消失，捲動內容會平滑從毛玻璃下方經過，不會再與動態島重疊。
    3. 橫向旋轉時，`px-safe` 同步保護左右側不被動態島或圓角裁切。

#### 2.3 全站 14 處彈窗統一安全邊界
將以下 12 個檔案中的 14 處全螢幕遮罩（`fixed inset-0`）套用 `.modal-safe-backdrop`（取代原本單純的 `p-4` / `p-3 sm:p-4`），並將內容卡片的 `max-h-[90vh]` / `max-h-[92vh]` 改為 `max-h-full`（讓外層 backdrop 的安全區 padding 真正生效）：

| # | 檔案路徑 | 行號位置 | 備註 |
| :-: | :--- | :--- | :--- |
| 1 | `frontend/src/components/MemberModal.vue` | L604–605、L1130 | 主彈窗（`max-h-[90vh]` -> `max-h-full`）與次級刪除確認彈窗（`z-60`） |
| 2 | `frontend/src/components/SystemSettingsModal.vue` | L217–218 | 系統設定彈窗（`max-h-[90vh]` -> `max-h-full`） |
| 3 | `frontend/src/components/ThemeModal.vue` | L60–63 | 佈景主題彈窗（`max-h-[92vh]` -> `max-h-full`） |
| 4 | `frontend/src/components/ImageViewModal.vue` | L40–43 | 圖片預覽彈窗（`max-h-[92vh]` -> `max-h-full`） |
| 5 | `frontend/src/components/BadgeManageModal.vue` | L232–233 | 成就管理彈窗（`max-h-[90vh]` -> `max-h-full`） |
| 6 | `frontend/src/components/BatchAdjustModal.vue` | L143–144 | 批次調整彈窗（`max-h-[90vh]` -> `max-h-full`） |
| 7 | `frontend/src/components/AvatarCropperModal.vue` | L273 | 頭像裁切彈窗 |
| 8 | `frontend/src/components/BadgeUnlockModal.vue` | L20 | 成就解鎖慶祝彈窗 |
| 9 | `frontend/src/components/ParentPinModal.vue` | L144 | 家長 PIN 碼解鎖彈窗 |
| 10 | `frontend/src/components/MemberPinModal.vue` | L95 | 成員 PIN 碼驗證彈窗 |
| 11 | `frontend/src/views/RewardsView.vue` | L721、L743 | 拒絕審核彈窗與新增/編輯獎品彈窗（2 處） |
| 12 | `frontend/src/views/RulesView.vue` | L237 | 新增/編輯規則彈窗 |

#### 2.4 根容器與頁尾修正（`frontend/src/App.vue`）
- 根節點由 `min-h-screen` 升級為 `min-h-screen min-h-[100dvh]`（保留 `min-h-screen` 供舊瀏覽器降級），避免 iOS 動態工具列造成虛假捲軸。
- `<footer>` 底部加上 `padding-bottom: calc(1rem + var(--app-safe-bottom))`，避免版權文字貼近底部橫條。

---

### 第二層（必做）：WebLoader 情境 B 備援機制

為確保即使 WebLoader 原生層回傳 `env(safe-area-inset-top) = 0px` 仍能妥善避讓，設計三段優先順序明確的備援機制（**僅影響設定該項的單一裝置，不影響桌機、Android 與一般 Safari**）：

#### 2.5 優先順序規則
1. **URL 查詢參數（最高優先，專為 WebLoader 啟動網址設計）**
   - 支援格式：`?top_inset=59`（合法範圍 `0`～`120`，單位 `px`）或 `?top_inset=auto`。
   - 行為：啟動時若偵測到合法 `top_inset` 參數，立即寫入 `document.documentElement.style.setProperty('--top-inset-override', '<N>px')`，並同步存入 `localStorage`（鍵值 `frog_kudos_top_inset`），讓後續頁內路由切換或重新整理仍維持生效。
   - 使用方式：在 iPhone WebLoader 設定開啟網址為 `http://192.168.50.3:8000/?top_inset=59` 即可零操作生效。
2. **本機裝置顯示設定（持久化於 `localStorage`）**
   - 擴充 `frontend/src/stores/theme.js`（既有本機裝置設定 store，不需家長權限）管理 `topInsetMode`：
     - `auto`（預設）：系統自動偵測（`0px` 覆寫，完全依賴 `env(safe-area-inset-top)`；若有開啟滿版啟發式備援則自動套用）
     - `notch`：`48px`（iPhone 瀏海機型備援）
     - `island`：`60px`（iPhone 動態島機型備援）
     - `custom`：自訂數值（滑桿或數字輸入 `0`～`100px`，即時預覽效果）
   - 在 `frontend/src/components/ThemeModal.vue` 新增第三個分頁或設定區塊（例如 `📱 裝置顯示`），並即時顯示目前瀏覽器回報的 `env(safe-area-inset-top)` 實測數值，方便除錯與微調。
3. **Anti-FOUC / Anti-CLS 預載腳本（`frontend/index.html`）**
   - 沿用 `index.html`（第 9–16 行）既有的 inline preloader 概念，在 Vue 掛載前即讀取 URL `?top_inset=` 與 `localStorage['frog_kudos_top_inset']` 並寫入 `--top-inset-override`，避免畫面首屏閃動跳位。
4. **謹慎的滿版啟發式自動偵測（選配，可整合於 `auto` 模式）**
   - **僅在同時滿足以下 4 個條件時才自動補 `59px`（動態島）或 `47px`（瀏海）**：
     1. 為 iPhone iOS 裝置（UA / `maxTouchPoints` 判斷）。
     2. 透過隱藏 DOM 探針實測 `env(safe-area-inset-top)` 為 `0px`。
     3. 處於直向且 `window.innerHeight >= window.screen.height - 20`（確認 WebView **確實滿版鋪到實體螢幕頂端**，排除一般 Safari 與已被宿主 App 預先內縮的安全 WebView，避免雙重留白）。
     4. 螢幕邏輯解析度符合瀏海／動態島機型清單（例如動態島機型：`393×852`、`430×932`、`402×874`、`440×956`；瀏海機型：`375×812`、`414×896`、`390×844`、`428×926`）。

---

### 第三層（選配）：行動端導覽與狀態列視覺優化

此層不影響防遮擋功能，但可顯著改善加上安全區後的 iPhone 螢幕利用率與單手體驗：

1. **將行動端分頁列移至真正底部（Bottom Tab Bar）**
   - 將 `frontend/src/components/Navbar.vue`（第 194–219 行）的 `md:hidden` 分頁列移出 `<header>`，改為 `fixed bottom-0 inset-x-0 z-40 pb-safe-bottom`。
   - 頂部 `<header>` 高度由 `~175px` 縮減為 `~123px`（含 59px 動態島安全區）。
   - `frontend/src/App.vue` 的 `<main>` 與 `<footer>` 在行動版補上 `pb-20 md:pb-4`（搭配 `var(--app-safe-bottom)`），避免頁面最底端內容被底部 Tab Bar 遮住。
2. **檢視 `meta[name="theme-color"]` 與頂部 header 銜接**
   - 目前 `frontend/src/stores/theme.js`（第 243–246 行）會將 `theme-color` 設為鮮明主題色，而 `<header>` 為白色毛玻璃；可依實機觀察決定保留主題色，或在 header 最頂端加入細微主題漸層／改為淺色 `#F9FAFB` 使頂部融為一體。

---

## 3. 逐檔修改清單

| 階段 | 檔案 | 修改摘要 |
| :--- | :--- | :--- |
| **第一＋二層** | `frontend/index.html` | 保留 `viewport-fit=cover`；擴充 inline preloader 讀取 `?top_inset=` 與 `localStorage` 並於首屏前注入 `--top-inset-override`。 |
| **第一＋二層** | `frontend/src/style.css` | 定義 `--safe-*` / `--top-inset-override` / `--app-safe-*` CSS 變數與 `.pt-safe-top`、`.pb-safe-bottom`、`.px-safe`、`.modal-safe-backdrop` 工具類別。 |
| **第一層** | `frontend/src/components/Navbar.vue` | `<header>` 加上 `pt-safe-top px-safe`（維持 `sticky top-0`）。 |
| **第一層** | `frontend/src/App.vue` | 根容器改為 `min-h-screen min-h-[100dvh]`；`<footer>` 加上底部安全區間距。 |
| **第一層** | 12 個含 Modal 的元件與頁面 | 將 14 處 `fixed inset-0` 遮罩套用 `.modal-safe-backdrop`，內層高度上限由 `max-h-[90vh]` / `max-h-[92vh]` 改為 `max-h-full`。 |
| **第二層** | `frontend/src/stores/theme.js` | 新增本機裝置 `topInset` 狀態、URL 參數解析、`localStorage` 持久化、即時 CSS 變數同步與實測 `env(safe-area-inset-top)` 診斷函式。 |
| **第二層** | `frontend/src/components/ThemeModal.vue` | 新增「裝置顯示與安全區」設定分頁（支援 `自動` / `瀏海 48px` / `動態島 60px` / 自訂滑桿 + 實測安全區數值顯示）。 |
| **第三層（選配）** | `frontend/src/components/Navbar.vue`、`frontend/src/App.vue` | 將行動端分頁列獨立為 `fixed bottom-0` 底部導覽列並補齊底部內容預留空間。 |

---

## 4. 驗證與部署流程

### 4.1 本機建置與基礎驗證
1. 於 `frontend/` 執行 `npm run build`，確認 Tailwind 編譯與 Vite 打包零錯誤。
2. 以桌機瀏覽器與 DevTools 行動模擬（iPhone 14 Pro / 15 Pro / SE，直向與橫向）：
   - 驗證一般瀏覽器（`--safe-top: 0px`、`--top-inset-override: 0px`）版面與修改前完全一致，無多餘空白。
   - 於網址列加上 `?top_inset=59` 驗證 `<header>` 向下避讓、頁面捲動時毛玻璃覆蓋頂端、開啟長彈窗（如 `MemberModal`、`SystemSettingsModal`、`ThemeModal`、`ImageViewModal`）標題與 `✕` 不會超出安全區。

### 4.2 測試環境實機驗證（`192.168.50.3` 開發環境）
> 完整部署規範請見 [deployment-workflow.md](./deployment-workflow.md)（原則：**本機開發 -> 推送 GitHub -> SSH 至 `192.168.50.3` 從 GitHub 拉取**）。

1. 於本機完成修改、測試建置並提交後，先推送至 GitHub（`git push origin master`）。
2. SSH 連線至 `chinsonyeh@192.168.50.3`，於開發目錄 `/home/chinsonyeh/Code/frog_kudos` 從 GitHub 同步最新程式碼（既有目錄執行 `git pull origin master` 以保留 `.env`/`venv/`/`uploads/`；若為全新目錄則執行 `git clone git@github.com:chinsonyeh/frog_kudos.git`），接著於 `frontend/` 執行 `npm run build` 並重啟 `frog_kudos_dev.service`。
3. 以 iPhone 實機依序測試以下 4 種情境：
   - [ ] **WebLoader 預設開啟（無參數）**：檢查 `ThemeModal` 顯示之系統實測 `env(safe-area-inset-top)` 數值，確認是否直接由第一層自動避讓。
   - [ ] **WebLoader 情境 B 測試**：若實測為 `0px`，改用 `?top_inset=59` 或於 `ThemeModal` 切換為「動態島（60px）」，確認重整與換頁後維持生效。
   - [ ] **iOS Safari 一般瀏覽與「加入主畫面」PWA 模式**：確認不會產生雙重留白，且捲動與點擊流暢。
   - [ ] **橫向旋轉與各類彈窗**：開啟所有主要 Modal（成員管理、系統設定、佈景主題、圖片放大、PIN 碼鎖、批次調整）確認無裁切或難以關閉。

### 4.3 正式環境發佈
- 開發環境實機驗證無誤後，依 [deployment-workflow.md](./deployment-workflow.md) 流程同步正式目錄 `/home/chinsonyeh/frog_kudos`（或執行 `scripts/deploy_to_release.sh v1.0.5` 自動執行 `pytest`、更新 `VERSION`、推送 GitHub Tag、拉取至正式目錄、重新打包前端並重啟 `frog_kudos.service`）。

---

## 5. 風險與注意事項

1. **避免雙重留白**：CSS 使用 `max(var(--safe-top), var(--top-inset-override))` 而非 `calc(... + ...)`，確保即使系統已有回報 `59px` 且使用者手動設為 `60px`，總間距也只會是 `60px`，絕不會疊加成 `119px`。
2. **`backdrop-filter` 效能與層級**：`<header>` 維持現有 `z-40`，各 Modal 維持 `z-50`（`MemberModal` 確認框 `z-60`），層級關係不變。
3. **WebLoader 原生設定優先排查**：建議同步檢查該 WebLoader App 本身是否有「Safe Area / 顯示狀態列」開關；若能從 App 側正確傳遞 Safe Area，前端即可全程由第一層自動適配，無需手動設定固定 px。
