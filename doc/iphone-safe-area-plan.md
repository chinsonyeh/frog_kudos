# iPhone 動態島與 WebLoader 安全區域（Safe Area）UI 適配實作計畫

> **建立日期**：2026-11-22  
> **目標系統**：Frog Kudos 家庭積分獎勵系統（Vue 3 + Vite + Tailwind CSS 3）  
> **基準版本**：`v1.0.4`（Commit `87134bc`）  
> **測試/部署主機**：`192.168.50.3`（開發：`~/Code/frog_kudos` -> `https://kudos.chinson.idv.tw:8443` / 正式：`~/frog_kudos` -> `https://kudos.chinson.idv.tw`）

---

## 1. 背景與問題描述

當使用者在具備 **動態島（Dynamic Island）** 或 **瀏海（Notch）** 的 iPhone 上，透過 **WebLoader 類型的全螢幕網頁載入程式**（底層多為 iOS `WKWebView`）或 PWA 獨立模式開啟 Frog Kudos 時，頁面上方內容容易被動態島與系統狀態列遮擋，導致頂部導覽列與彈窗右上角關閉按鈕難以辨識與點擊。

### 1.1 現況架構根因分析

1. **已宣告 `viewport-fit=cover`，但全站尚未套用 `env(safe-area-inset-*)`**
   - `frontend/index.html`（第 5 行）已設定 `viewport-fit=cover`，會使 iOS WebKit 將畫面延伸至實體螢幕邊緣（覆蓋頂部約 `59px` 動態島 / `47px` 瀏海與底部約 `34px` Home Indicator）。
   - 然而 `frontend/src/` 所有樣式與元件均未使用 `env(safe-area-inset-top/bottom/left/right)`。
2. **頂部導覽列直接貼齊 `y = 0`**
   - `frontend/src/components/Navbar.vue`（第 66–68 行）使用 `<header class="sticky top-0 z-40 ...">` 與 `h-16`（`64px`），Logo、標題、身分模式膠囊與 `🎨`/`⚙️` 按鈕會直接落入動態島遮蔽區。
3. **全螢幕彈窗（Modal）未考量上下安全區且部分缺乏高度上限（共 12 個檔案、14 處遮罩）**
   - 14 處彈窗外層皆為 `fixed inset-0` 搭配固定 `p-4` / `p-3 sm:p-4` / `p-3 sm:p-6`；其中 6 處內層高度上限為 `max-h-[90vh]` 或 `max-h-[92vh]`，其餘 8 處甚至沒有設定 `max-h` 與 `overflow-y-auto`。
   - 在 iPhone 15 / 16（直向視窗高約 `852px`）上，`92vh` 上下僅各剩約 `34px`，小於動態島高度（`~59px`）；橫向模式（視窗高僅約 `393px`）時，無高度上限或含固定 `min-h-[250px]` 的彈窗更會直接上下溢位裁切。
4. **行動端導覽列結構偏高**
   - `frontend/src/components/Navbar.vue`（第 194–219 行）的行動端導覽列雖註解為「底部快速導航」，但實際仍位於頂部 `<header>` 內。加上頂部安全區後，頂部 sticky 區塊總高將達約 `59 + 64 + 52 ≈ 175px`（超過螢幕高度 20%）。
5. **路由重導向會丟棄初始查詢參數**
   - `frontend/src/router/index.js`（第 11–17 行與第 58–67 行）在根路徑 `/` 重導向至 `/ledger` 或 `/record`，以及權限守衛 `next('/ledger')` 時未保留 `query`，若只在 Vue 元件或 store 掛載後讀取 `?top_inset=`，參數會在導航前遺失。
6. **低耦合優勢**
   - 盤點 `frontend/src/views/` 下所有頁面（`GuideView`、`LedgerView`、`QuickEntryView`、`RewardsView`、`RulesView`），**均無次級 `sticky top-16` 定位元件**，調整 `<header>` 高度與安全區不會引發頁面內部錯位。

### 1.2 WebLoader 類程式的兩種底層行為

| 情境 | iOS `WKWebView` 行為 | `env(safe-area-inset-top)` 實測值 | 對應處理策略 |
| :--- | :--- | :--- | :--- |
| **情境 A（標準 WKWebView / PWA）** | 畫面延伸至實體邊緣，且正確向 WebKit 傳遞 Safe Area | 動態島約 `59px`、瀏海約 `47px`、一般瀏覽器 `0px` | **第一層**：標準 CSS `env(safe-area-inset-*)` 自動避讓 |
| **情境 B（非標準 WebLoader）** | 原生層設為無視 Safe Area（如 `contentInsetAdjustmentBehavior = .never`），畫面延伸至動態島下，但未傳遞安全區給網頁 | 永遠回傳 `0px` | **第二層**：同步前置解析 URL 參數 + 本機裝置設定 + 謹慎滿版偵測備援 |

> **關鍵原則**：**不可**為了避開動態島而單純移除 `viewport-fit=cover`。在多數強制全螢幕的 WebLoader 中，移除 `viewport-fit=cover` 不會縮回視窗，反而會使 WebKit 強制將 `env(safe-area-inset-top)` 歸零，失去自動適配能力。

---

## 2. 分層架構設計

採用 **三層式漸進改造**：第一、二層為本次核心必做項目；**第三層為第一、二層實機驗收完成後的獨立後續迭代**。

### 第一層（必做）：標準 Safe Area CSS 系統

#### 2.1 統一 CSS 變數與工具類別（`frontend/src/style.css`）
在 `:root` 建立統一的安全區變數層，所有元件只引用 `--app-safe-*`，並透過 `@media (orientation: landscape)` 明確區分直向與橫向，避免 `--top-inset-override` 在橫向旋轉時造成頂部過大空白與畫面破版：

```css
:root {
  --safe-top: env(safe-area-inset-top, 0px);
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  --safe-left: env(safe-area-inset-left, 0px);
  --safe-right: env(safe-area-inset-right, 0px);

  /* 第二層 WebLoader 備援覆寫值（預設必為 0px，由 URL 參數或本機設定注入） */
  --top-inset-override: 0px;

  /* 實際生效的頂部安全距離：直向時取系統值與備援值之較大者 */
  --app-safe-top: max(var(--safe-top), var(--top-inset-override));
  --app-safe-bottom: var(--safe-bottom);
  --app-safe-left: var(--safe-left);
  --app-safe-right: var(--safe-right);
}

/* 橫向旋轉時，動態島／瀏海位於左右兩側而非頂端：停用直向覆寫值，歸回系統值 */
@media (orientation: landscape) {
  :root {
    --app-safe-top: var(--safe-top);
  }
}
```

> **CSS 單位強制規則**：任何 JavaScript 寫入 `--top-inset-override` 時**一律必須帶 `px` 單位**（例如 `'59px'`、歸零必為 `'0px'`），**嚴禁寫入無單位 `'0'` 或空字串 `''`**，避免 iOS WebKit 解析 `max(var(--safe-top), var(--top-inset-override))` 時整條宣告失效。

同時於 `@layer utilities` 定義共用類別，避免重複散落 inline style 或工具類衝突：
- `.min-h-app`（取代同元素並寫 `min-h-screen min-h-[100dvh]` 的反模式）：
  ```css
  .min-h-app {
    min-height: 100vh;
    min-height: 100dvh;
  }
  ```
- `.pt-safe-top`：`padding-top: var(--app-safe-top);`
- `.pb-safe-bottom`：`padding-bottom: var(--app-safe-bottom);`
- `.px-safe`：`padding-left: var(--app-safe-left); padding-right: var(--app-safe-right);`
- `.px-safe-page`（供 `<main>` 使用，於各響應式斷點取基礎邊距與安全區較大值，避免橫向雙重留白且與 `<header>` 對齊）：
  ```css
  .px-safe-page {
    padding-left: max(1rem, var(--app-safe-left));
    padding-right: max(1rem, var(--app-safe-right));
  }
  @media (min-width: 640px) {
    .px-safe-page {
      padding-left: max(1.5rem, var(--app-safe-left));
      padding-right: max(1.5rem, var(--app-safe-right));
    }
  }
  @media (min-width: 1024px) {
    .px-safe-page {
      padding-left: max(2rem, var(--app-safe-left));
      padding-right: max(2rem, var(--app-safe-right));
    }
  }
  ```
- `.modal-safe-backdrop`（統一控管所有全螢幕彈窗遮罩之四邊安全留白）：
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

#### 2.3 全站 14 處彈窗統一安全邊界與內部捲動
針對以下 12 個檔案中的 **14 處全螢幕遮罩（`fixed inset-0`）**，統一落實下列規範：

1. **遮罩外層強制清除舊 Padding**：
   - 所有 14 處遮罩**必須完全移除**原本的 `p-4`、`p-3`、`sm:p-4`、`sm:p-6`，統一改由 `.modal-safe-backdrop` 控管四邊間距。
   - **特別注意**：`ImageViewModal.vue:40` 的 `sm:p-6` 若未移除，於手機橫向（寬度 `>= 640px`）會覆蓋 `.modal-safe-backdrop`，導致安全區失效。
2. **既有 6 處高卡片改用 `max-h-full`**：
   - 將原本內層卡片的 `max-h-[90vh]` / `max-h-[92vh]` 一律改為 `max-h-full`，讓外層 `.modal-safe-backdrop` 扣除安全區後的剩餘高度真正成為內層卡片的高度上限。
3. **其餘 8 處原本無高度上限的內層卡片一併加上 `max-h-full overflow-y-auto`**：
   - 包含 `AvatarCropperModal.vue:273–278`、`ParentPinModal.vue:144–152, 303–308`、`MemberPinModal.vue:95–103, 197–202`、`BadgeUnlockModal.vue:20–21`、`MemberModal.vue:1130–1132`、`RewardsView.vue:721–722, 743–744`、`RulesView.vue:237–238`，確保在 iPhone SE 或橫向低高度視窗下仍可完整捲動操作，不裁切按鈕。
4. **特殊互動與佈局修正**：
   - **`ParentPinModal.vue`（L144–152, L303–308）、`MemberPinModal.vue`（L95–103, L197–202）、`AvatarCropperModal.vue`（L273–278）**：需妥善處理卡片內部捲動與 `touch-action: none` 的互動——內層卡片加上 `max-h-full overflow-y-auto overscroll-contain`，並於橫向或低高度視窗適度壓縮垂直間距（例如 `landscape:py-4` / 較緊湊間距）；`AvatarCropperModal` 應將 `touch-none` 限縮於裁切畫布區域而非整層外罩，避免阻斷卡片在橫向模式下的捲動。
   - **`BadgeUnlockModal.vue`（L20–21）**：原本內層卡片設有 `overflow-hidden` 以裁切背景裝飾光暈，須將背景光暈改包於獨立的 `absolute inset-0 overflow-hidden pointer-events-none rounded-3xl` 圖層中，卡片本體改用 `max-h-full overflow-y-auto`，避免多枚勳章或橫向模式時底部確認按鈕被 `overflow-hidden` 切斷。
   - **`ImageViewModal.vue`（L40–43, L80, L84）**：外層遮罩移除 `p-3 sm:p-6` 改套用 `.modal-safe-backdrop`；內層卡片 `max-h-[92vh]` 改為 `max-h-full`；圖片主體容器（L80）將 `min-h-[250px]` 改為 `min-h-0`（保留 `flex-1 min-h-0`）；`<img>`（L84）將 `max-h-[72vh]` 改為 `max-h-full`，確保橫向模式與小螢幕不會撐爆卡片。
   - **`MemberModal.vue`（L1130–1132）**：此處為「家長快速解鎖提權彈窗（`showUnlockPrompt`）」，並將原本無效的 `z-60` 修正為 `z-[60]`（Tailwind CSS v3.4 預設無 `z-60` 類別，會退回無 `z-index` 風險）。

| # | 檔案路徑 | 行號位置 | 修改明細 |
| :-: | :--- | :--- | :--- |
| 1 | `frontend/src/components/MemberModal.vue` | L604–605 | 主彈窗：外層移除 `p-4` 套用 `.modal-safe-backdrop`；內層 `max-h-[90vh]` -> `max-h-full` |
| 2 | `frontend/src/components/MemberModal.vue` | L1130–1132 | **家長快速解鎖提權彈窗（`showUnlockPrompt`）**：外層移除 `p-4` 套用 `.modal-safe-backdrop`，並將無效的 `z-60` 改為 `z-[60]`；內層加上 `max-h-full overflow-y-auto` |
| 3 | `frontend/src/components/SystemSettingsModal.vue` | L217–218 | 系統設定彈窗：外層移除 `p-4` 套用 `.modal-safe-backdrop`；內層 `max-h-[90vh]` -> `max-h-full` |
| 4 | `frontend/src/components/ThemeModal.vue` | L60–63 | 佈景主題彈窗：外層移除 `p-4` 套用 `.modal-safe-backdrop`；內層 `max-h-[92vh]` -> `max-h-full` |
| 5 | `frontend/src/components/ImageViewModal.vue` | L40–43, L80, L84 | 圖片預覽彈窗：外層移除 `p-3 sm:p-6` 套用 `.modal-safe-backdrop`；內層 `max-h-[92vh]` -> `max-h-full`；L80 圖片容器 `min-h-[250px]` -> `min-h-0`（搭配 `flex-1 min-h-0`）；L84 `<img>` `max-h-[72vh]` -> `max-h-full` |
| 6 | `frontend/src/components/BadgeManageModal.vue` | L232–233 | 成就管理彈窗：外層移除 `p-4` 套用 `.modal-safe-backdrop`；內層 `max-h-[90vh]` -> `max-h-full` |
| 7 | `frontend/src/components/BatchAdjustModal.vue` | L143–144 | 批次調整彈窗：外層移除 `p-4` 套用 `.modal-safe-backdrop`；內層 `max-h-[90vh]` -> `max-h-full` |
| 8 | `frontend/src/components/AvatarCropperModal.vue` | L273–278 | 頭像裁切彈窗：外層移除 `p-3 sm:p-4` 套用 `.modal-safe-backdrop`；內層加上 `max-h-full overflow-y-auto overscroll-contain`，並將 `touch-none` 限縮於裁切畫布以維持橫向可捲動 |
| 9 | `frontend/src/components/BadgeUnlockModal.vue` | L20–21 | 成就解鎖慶祝彈窗：外層移除 `p-4` 套用 `.modal-safe-backdrop`；背景光暈改獨立 `overflow-hidden` 裝飾層，卡片改為 `max-h-full overflow-y-auto` 確保按鈕不被切斷 |
| 10 | `frontend/src/components/ParentPinModal.vue` | L144–152, L303–308 | 家長 PIN 碼解鎖彈窗：外層移除 `p-4` 套用 `.modal-safe-backdrop`；內層加上 `max-h-full overflow-y-auto overscroll-contain`，妥善處理與外層 `touch-action: none` 之捲動互動及橫向間距壓縮 |
| 11 | `frontend/src/components/MemberPinModal.vue` | L95–103, L197–202 | 成員 PIN 碼驗證彈窗：外層移除 `p-4` 套用 `.modal-safe-backdrop`；內層加上 `max-h-full overflow-y-auto overscroll-contain`，妥善處理與外層 `touch-action: none` 之捲動互動及橫向間距壓縮 |
| 12 | `frontend/src/views/RewardsView.vue` | L721–722 | 退回原因彈窗：外層移除 `p-4` 套用 `.modal-safe-backdrop`；內層加上 `max-h-full overflow-y-auto` |
| 13 | `frontend/src/views/RewardsView.vue` | L743–744 | 新增/編輯獎品彈窗：外層移除 `p-4` 套用 `.modal-safe-backdrop`；內層加上 `max-h-full overflow-y-auto` |
| 14 | `frontend/src/views/RulesView.vue` | L237–238 | 新增/編輯規則彈窗：外層移除 `p-4` 套用 `.modal-safe-backdrop`；內層加上 `max-h-full overflow-y-auto` |

#### 2.4 根容器、橫向安全區、頁尾與 iOS 狀態列（`frontend/index.html`、`frontend/src/App.vue`）
- **統一 `.min-h-app` 並同時套用至 `<body>` 與 `App.vue`**：
  - 將 `frontend/index.html:37` 的 `<body>` 與 `frontend/src/App.vue:109` 的根 `<div>` 原本的 `min-h-screen`，**同時改為 `.min-h-app`**（使用 `style.css` 定義的 `min-height: 100vh; min-height: 100dvh;` 漸進降級，避免在同元素並寫 `min-h-screen min-h-[100dvh]` 造成編譯順序依賴與虛假捲軸）。
- **橫向模式 `<main>` 與 `<footer>` 左右安全區**：
  - `frontend/src/App.vue:119` 的 `<main>`：移除原本的 `px-4 sm:px-6 lg:px-8`，改套用 `.px-safe-page`（使用 `max(1rem / 1.5rem / 2rem, var(--app-safe-left/right))`），避免在橫向模式產生雙重留白，且與 `<header>` 左右安全線對齊。
  - `frontend/src/App.vue:158` 的 `<footer>`：補上左右安全區 `padding-left: max(1rem, var(--app-safe-left))`、`padding-right: max(1rem, var(--app-safe-right))`（可併入共用工具類），並加上底部安全區 `padding-bottom: calc(1rem + var(--app-safe-bottom))`，避免版權文字貼近 Home Indicator 或被橫向圓角裁切。
- **維持 iOS 狀態列樣式為 `default`**：
  - `frontend/index.html:27` 明確維持 `<meta name="apple-mobile-web-app-status-bar-style" content="default" />`，**不可改為 `black-translucent`**，避免本站淺色毛玻璃頂部搭配白色系統文字導致狀態列時間與電量資訊難以辨識。

---

### 第二層（必做）：WebLoader 情境 B 備援機制

為確保即使 WebLoader 原生層回傳 `env(safe-area-inset-top) = 0px` 仍能妥善避讓，設計優先順序與資料格式一致的備援機制（**僅影響設定該項的單一裝置，不影響桌機、Android 與一般 Safari**）：

#### 2.5 優先順序、同步預載與統一 Schema

1. **URL 查詢參數（最高優先，強制由 `frontend/index.html` 同步預載腳本解析）**
   - **為何不可等到 Vue 掛載才讀 URL**：`frontend/src/router/index.js`（第 11–17 行的根路徑 `/` redirect 與第 58–67 行的 `beforeEach` 權限守衛）在重導向至 `/ledger` 或 `/record` 時會丟棄 query string。若未於 Vue Router 初始化前攔截，使用者以 `/?top_inset=59` 進入時參數將直接遺失。
   - **同步 inline script 行為（`frontend/index.html` 第 9–16 行擴充）**：在 `<head>` 內、Vue 與 Vue Router 啟動之前，同步解析 `window.location.search` 的 `top_inset` 參數並寫入 `localStorage` 與 `--top-inset-override`（同時消除首屏 FOUC / CLS 跳動）：
     - `?top_inset=<N>`（`N` 為 `0`～`120` 整數，如 `?top_inset=59`）：寫入 `localStorage['frog_kudos_top_inset'] = 'custom:' + N`，並設定 `--top-inset-override` 為 `N + 'px'`。
     - `?top_inset=auto`：重置並清除先前的手動／URL 覆寫，寫入 `localStorage['frog_kudos_top_inset'] = 'auto'`，並將 `--top-inset-override` 設為 `'0px'`。
     - 非法數值（如負數、超過 `120`、非數字字串）：忽略參數並回退讀取既有 `localStorage['frog_kudos_top_inset']`。
   - **使用方式**：在 iPhone WebLoader 將啟動網址設為 `https://kudos.chinson.idv.tw/?top_inset=59`（或開發測試環境 `https://kudos.chinson.idv.tw:8443/?top_inset=59`）即可零操作生效；如需恢復自動偵測，開啟 `?top_inset=auto` 即可重置。

2. **統一 `localStorage` Schema（`index.html` 與 `theme.js` 嚴格共用）**
   - 單一鍵名：`frog_kudos_top_inset`
   - 合法儲存格式與對應 CSS 覆寫值（寫入 `--top-inset-override` 一律含 `px` 單位，歸零必為 `'0px'`）：

   | `localStorage['frog_kudos_top_inset']` 值 | 語意 | 對應 `--top-inset-override` | 備註 |
   | :--- | :--- | :--- | :--- |
   | `'auto'`（預設） | 系統自動偵測 | `'0px'`（若觸發 2.5.4 啟發式則暫態注入） | `?top_inset=auto` 轉存此值 |
   | `'notch'` | iPhone 瀏海機型備援 | `'48px'` | 僅直向生效 |
   | `'island'` | iPhone 動態島機型備援 | `'60px'` | 僅直向生效 |
   | `'custom:<N>'`（`N` 為 `0`～`120` 整數） | URL 指定或使用者自訂 | `'<N>px'`（例：`'59px'`、`'0px'`） | `?top_inset=<N>` 轉存此值 |

3. **本機裝置顯示設定與 `ThemeModal.vue` 互動設計**
   - 擴充 `frontend/src/stores/theme.js`（既有本機裝置設定 store，不需家長權限）管理上述 `frog_kudos_top_inset` Schema、即時更新 `--top-inset-override`，並計算目前**生效來源**（如「系統自動 `env()`」、「滿版啟發式備援」、「預設：動態島」、「預設：瀏海」、「自訂／URL 指定」）與**實際套用數值（px）**。
   - 在 `frontend/src/components/ThemeModal.vue` 新增第三分頁：
     - **窄螢幕分頁標籤防折行**：3 個分頁按鈕改用精簡短標籤（例如 `🐸 圖示`、`🎨 主題`、`📱 顯示`），避免在 375px 窄螢幕上折行或擠壓。
     - **開啟狀態同步**：於 `watch(() => props.show)` 在彈窗開啟時同步依 `props.initialTab` 重設 `activeTab`（補足原本僅監聽 `props.initialTab` 的缺口）。
     - **即時診斷資訊**：顯示目前瀏覽器實測的 `env(safe-area-inset-top)` 數值、目前生效來源與實際生效頂部安全距離（px），方便實機排查與微調（支援 `自動` / `瀏海 48px` / `動態島 60px` / 自訂滑桿 `0`～`120px`）。

4. **謹慎的滿版啟發式自動偵測（整合於 `'auto'` 模式）**
   - **不可持久化**：啟發式偵測結果**嚴禁寫入 `localStorage`**，僅於執行階段暫態注入 `--top-inset-override`，避免日後切換一般 Safari、旋轉螢幕或升級 WebLoader 後殘留固定偏移植。
   - **探針量測時機與即時更新**：必須於 `requestAnimationFrame` 後再讀取隱藏 DOM 探針的 `env(safe-area-inset-top)`（避免 `WKWebView` 冷啟動初期短暫回傳 `0px` 造成誤判），並監聽 `resize` 與 `orientationchange` 事件重新量測探針，確保旋轉後即時更新 `ThemeModal` 顯示的實測值，且於橫向時將暫態覆寫歸回 `'0px'`。
   - **觸發條件（僅在 `'auto'` 模式且同時滿足以下 4 項時才套用暫態補值，例如 `'59px'`）**：
     1. 為 iPhone iOS 裝置（UA / `maxTouchPoints` 判斷）。
     2. 經 `requestAnimationFrame` 後實測 `env(safe-area-inset-top)` 仍為 `0px`。
     3. 處於直向（`window.innerHeight > window.innerWidth`）且 `window.innerHeight >= window.screen.height - 20`（確認 WebView **確實滿版鋪到實體螢幕頂端**，排除一般 Safari 與已被宿主 App 預先內縮的安全 WebView，避免雙重留白）。
     4. 全螢幕長寬比 `Math.max(w, h) / Math.min(w, h) >= 2.0`（以長寬比取代固定解析度白名單，避免 iOS **Display Zoom（顯示器縮放）** 改變邏輯解析度導致白名單誤判；`>= 2.0` 可涵蓋所有全螢幕 Face ID iPhone，並排除 16:9 傳統有 Home 鍵的 iPhone SE 機型）。

---

### 第三層（獨立後續迭代）：行動端導覽與狀態列視覺優化

> **迭代邊界**：本層定位為**第一、二層完成實機驗收後的獨立後續迭代**，不與第一、二層混合開發與部署，以確保核心安全區避讓先穩定上線。

此層可於後續進一步改善加上安全區後的 iPhone 螢幕利用率與單手操作體驗：

1. **將行動端分頁列移至真正底部（Bottom Tab Bar）**
   - 將 `frontend/src/components/Navbar.vue`（第 194–219 行）的 `md:hidden` 分頁列移出 `<header>`，改為 `fixed bottom-0 inset-x-0 z-40 pb-safe-bottom px-safe`，使頂部 `<header>` 高度由 `~175px` 縮減為 `~123px`（含 59px 動態島安全區）。
   - **修正家長 6 項目窄螢幕裁切問題**：家長模式共 6 個導覽項目，改採 `grid grid-cols-6` 搭配 **2 字短標籤**（例如「登記」「存摺」「商城」「規則」「成員」「說明」），取代現行 `justify-around overflow-x-auto`（避免內容寬度超出視窗時 Flexbox `justify-around` 導致左側首項被裁切且無法向左捲動）。
   - **避免底部重複留白**：僅於 `frontend/src/App.vue` 的 `<footer>` 預留**單份**行動底部導覽列高度（搭配 `var(--app-safe-bottom)`），不可在 `<main>` 與 `<footer>` 同時各加一次底部空間。
   - **iOS 軟鍵盤互動注意事項**：實作時須處理 iOS Safari / `WKWebView` 聚焦輸入框彈出軟鍵盤時對 `fixed bottom-0` 導覽列的影響（例如搭配 `visualViewport` 高度變化或 `focusin`/`focusout` 自動隱藏底部列，避免浮在鍵盤上方遮擋表單）。
2. **檢視 `meta[name="theme-color"]` 與頂部 header 銜接**
   - 目前 `frontend/src/stores/theme.js`（第 243–246 行）會將 `theme-color` 設為鮮明主題色，而 `<header>` 為白色毛玻璃；可依第一、二層實機觀察決定保留主題色，或在 header 最頂端加入細微主題漸層／調整配色使頂部融為一體。

---

## 3. 逐檔修改清單

| 階段 | 檔案 | 修改摘要 |
| :--- | :--- | :--- |
| **第一＋二層** | `frontend/index.html` | 保留 `viewport-fit=cover` 與 `apple-mobile-web-app-status-bar-style="default"`（L27）；`<body>`（L37）由 `min-h-screen` 改為 `.min-h-app`；擴充 `<head>` 同步 inline preloader，在 Vue Router 啟動前解析 `?top_inset=`（`0`～`120` / `auto`）與 `localStorage['frog_kudos_top_inset']`，以含 `px` 單位注入 `--top-inset-override`。 |
| **第一＋二層** | `frontend/src/style.css` | 定義 `--safe-*` / `--top-inset-override` / `--app-safe-*` 與 `@media (orientation: landscape)` 橫向歸零覆寫規則；定義 `.min-h-app`、`.pt-safe-top`、`.pb-safe-bottom`、`.px-safe`、`.px-safe-page`、`.modal-safe-backdrop` 工具類別。 |
| **第一層** | `frontend/src/components/Navbar.vue` | `<header>` 加上 `pt-safe-top px-safe`（維持 `sticky top-0 z-40`）。 |
| **第一層** | `frontend/src/App.vue` | 根容器（L109）由 `min-h-screen` 改為 `.min-h-app`；`<main>`（L119）改用 `.px-safe-page`；`<footer>`（L158）補上左右與底部安全區間距。 |
| **第一層** | 12 個含 Modal 的元件與頁面 | 14 處 `fixed inset-0` 遮罩**完全移除** `p-4`/`p-3`/`sm:p-4`/`sm:p-6` 並套用 `.modal-safe-backdrop`；既有 6 處 `max-h-[90vh]`/`max-h-[92vh]` 改為 `max-h-full`；其餘 8 處補上 `max-h-full overflow-y-auto`（含 `PinModal`/`AvatarCropperModal` 捲動與 `touch-action` 處理、`BadgeUnlockModal` 光暈分離、`ImageViewModal` L80/L84 改 `min-h-0` 與 `max-h-full`、`MemberModal` L1130 改 `z-[60]`）。 |
| **第二層** | `frontend/src/stores/theme.js` | 實作統一 `frog_kudos_top_inset` Schema、含 `px` 單位的 CSS 變數同步、目前生效來源計算、`requestAnimationFrame` + `resize`/`orientationchange` 探針量測，以及不寫入 `localStorage` 且採用長寬比 `>= 2.0` 的滿版啟發式偵測。 |
| **第二層** | `frontend/src/components/ThemeModal.vue` | 新增第三分頁「📱 顯示」（3 分頁採精簡短標籤防 375px 折行）；於 `watch(() => props.show)` 重設 `activeTab`；顯示實測 `env(safe-area-inset-top)`、生效來源與實際套用值，並提供模式切換與自訂滑桿。 |
| **第三層（後續獨立迭代）** | `frontend/src/components/Navbar.vue`、`frontend/src/App.vue` | 將行動端分頁列獨立為 `fixed bottom-0` 底部導覽列（`grid-cols-6` + 2 字短標籤）、僅於 `<footer>` 預留單份底部空間並處理 iOS 軟鍵盤互動。 |

---

## 4. 驗證與部署流程

### 4.1 本機建置與基礎驗證
1. 於 `frontend/` 執行 `npm run build`，確認 Tailwind 編譯與 Vite 打包零錯誤。
2. 以桌機瀏覽器與 DevTools 行動模擬（iPhone 14 Pro / 15 Pro / SE，直向與橫向）：
   - 驗證一般瀏覽器（`--safe-top: 0px`、`--top-inset-override: 0px`）版面與修改前完全一致，無多餘空白。
   - 以根路徑 `/?top_inset=59` 進入，驗證經 Vue Router 重導向至 `/ledger` 後覆寫仍生效、`<header>` 向下避讓、頁面捲動時毛玻璃覆蓋頂端；切換至橫向時驗證 `--app-safe-top` 自動歸回系統值無頂部多餘空白。
   - 以 `/?top_inset=auto` 進入，驗證正確重置 `localStorage['frog_kudos_top_inset']` 為 `'auto'` 並歸零 `--top-inset-override: 0px`。
   - 依序開啟 14 處 Modal（特別是 `ImageViewModal`、`ParentPinModal`、`MemberPinModal`、`AvatarCropperModal`、`BadgeUnlockModal`、`MemberModal` 快速解鎖提權彈窗與 `ThemeModal` 375px 3 分頁），確認直向與橫向皆無裁切、可完整捲動且 `✕` 按鈕可點擊。

### 4.2 測試環境實機驗證（`192.168.50.3` 開發環境）
> 完整部署規範請見 [deployment-workflow.md](./deployment-workflow.md)（原則：**本機開發 -> 推送 GitHub -> SSH 至 `192.168.50.3` 從 GitHub 拉取**）。

| 環境 | 服務名稱 | 本機監聽位址 | Caddy HTTPS 對外網址 |
| :--- | :--- | :--- | :--- |
| **開發測試環境（本階段驗證）** | `frog_kudos_dev.service` | `127.0.0.1:8001` | `https://kudos.chinson.idv.tw:8443` |
| **正式運行環境（驗證通過後再發佈）** | `frog_kudos.service` | `127.0.0.1:8000` | `https://kudos.chinson.idv.tw` |

1. 於本機完成修改、測試建置並提交後，先推送至 GitHub（`git push origin master`）。
2. SSH 連線至 `chinsonyeh@192.168.50.3`，於開發目錄 `/home/chinsonyeh/Code/frog_kudos` 執行 `git pull origin master`（保留 `.env`/`venv/`/`uploads/`），接著於 `frontend/` 執行 `npm run build`、重啟 `frog_kudos_dev.service` 並以 `curl -s http://127.0.0.1:8001/api/health` 確認服務健康。
3. 以 iPhone 實機連線至**開發測試網址 `https://kudos.chinson.idv.tw:8443`**（切勿誤連正式環境），依序驗證以下項目：
   - [ ] **WebLoader 預設開啟（無參數）**：檢查 `ThemeModal` 顯示之系統實測 `env(safe-area-inset-top)` 與生效來源，確認是否由第一層或滿版啟發式正確避讓（且啟發式不會寫入 `localStorage`）。
   - [ ] **WebLoader 情境 B 測試**：以 `https://kudos.chinson.idv.tw:8443/?top_inset=59` 開啟，確認自動重導向至 `/ledger` 後仍生效；改開 `?top_inset=auto` 或於 `ThemeModal` 切換模式（自動／瀏海／動態島／自訂），確認重整與換頁後一致生效。
   - [ ] **iOS Safari 一般瀏覽與「加入主畫面」PWA 模式**：確認不會產生雙重留白，且維持 `apple-mobile-web-app-status-bar-style="default"` 時系統狀態列文字（時間、訊號、電量）於淺色毛玻璃頂端清晰可辨。
   - [ ] **橫向旋轉與全站彈窗**：旋轉至橫向確認頂部覆寫自動失效、`<main>` 與 `<footer>` 左右與 `<header>` 對齊不裁切；開啟 `ImageViewModal`、`ParentPinModal`、`MemberPinModal`、`AvatarCropperModal`、`BadgeUnlockModal`、`MemberModal`（含快速解鎖提權彈窗）、`SystemSettingsModal`、`ThemeModal` 等確認皆可正常捲動與關閉。

### 4.3 正式環境發佈
開發環境實機驗證無誤後，依 [deployment-workflow.md](./deployment-workflow.md) 流程發佈至正式目錄 `/home/chinsonyeh/frog_kudos`（正式網址 `https://kudos.chinson.idv.tw`）：

1. **發佈前檢查遠端工作區乾淨**：執行 `./scripts/deploy_to_release.sh v1.0.5` 前，務必先於 `/home/chinsonyeh/Code/frog_kudos` 執行 `git status -sb` 確認工作目錄完全乾淨（因該腳本會執行 `git add -A` 並自動 commit 與 push）。
2. **依賴變更補裝提醒**：若本次改版有更新 `frontend/package.json`，因 `deploy_to_release.sh` 預設僅執行 `npm run build`，須於正式目錄 `/home/chinsonyeh/frog_kudos/frontend` 補跑 `npm install` 後再建置。
3. **發佈後同步本機分支**：腳本會於遠端建立更新 `VERSION` 檔案的 commit 並推上 GitHub，發佈完成後務必回到**本機開發區**執行 `git pull origin master`，避免後續開發產生本機與遠端分叉。

---

## 5. 風險與注意事項

1. **避免雙重留白與單位失效**：CSS 使用 `max(var(--safe-top), var(--top-inset-override))` 而非 `calc(... + ...)`，確保即使系統已回報 `59px` 且使用者手動設為 `60px`，總間距也只會是 `60px`；且寫入 `--top-inset-override` 一律帶 `px`（歸零為 `'0px'`），防止 WebKit `max()` 解析失敗。
2. **橫向模式保護**：透過 `@media (orientation: landscape)` 將 `--app-safe-top` 歸回 `var(--safe-top)`，確保直向手動覆寫不會在橫向造成頂部巨幅空白。
3. **`backdrop-filter` 效能與層級**：`<header>` 維持現有 `z-40`，一般 Modal 維持 `z-50`，`MemberModal` 家長快速解鎖提權彈窗由無效的 `z-60` 修正為 `z-[60]`，確保層級高於主彈窗。
4. **WebLoader 原生設定優先排查**：建議同步檢查該 WebLoader App 本身是否有「Safe Area / 顯示狀態列」開關；若能從 App 側正確傳遞 Safe Area，前端即可全程由第一層自動適配，無需手動設定固定 px。
