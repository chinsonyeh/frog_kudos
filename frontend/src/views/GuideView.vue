<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const emit = defineEmits(['openPinModal'])
const router = useRouter()
const authStore = useAuthStore()

function triggerUnlock() {
  emit('openPinModal')
}
</script>

<template>
  <div class="space-y-8 max-w-4xl mx-auto pb-12 animate-in fade-in duration-300">
    <!-- 頂部標題區 (Hero) -->
    <div class="bg-gradient-to-br from-frog-500 via-emerald-600 to-teal-700 text-white rounded-3xl p-6 sm:p-10 shadow-xl shadow-frog-900/10 relative overflow-hidden">
      <div class="absolute -right-12 -bottom-12 w-56 h-56 bg-white/10 rounded-full blur-3xl pointer-events-none"></div>

      <div class="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div class="space-y-2">
          <div class="inline-flex items-center space-x-2 bg-white/20 backdrop-blur-md px-3 py-1 rounded-full text-xs font-bold tracking-wide">
            <span>🐸</span>
            <span>Frog Kudos 家庭指南</span>
          </div>
          <h2 class="text-2xl sm:text-3xl font-black tracking-tight">系統使用說明書</h2>
          <p class="text-emerald-100 text-sm sm:text-base max-w-xl">
            歡迎使用 Frog Kudos 家庭積分獎勵系統！本系統採用身分權限劃分與各瀏覽器獨立會話機制。跟著以下 3 個步驟，輕鬆上手解鎖、點數登記與心願兌換！
          </p>
        </div>

        <div class="flex-shrink-0 flex flex-col sm:flex-row gap-2">
          <button
            v-if="!authStore.isUnlocked"
            @click="triggerUnlock"
            type="button"
            class="px-5 py-3 rounded-2xl bg-white text-frog-700 font-bold text-sm shadow-md hover:bg-emerald-50 active:scale-95 transition flex items-center justify-center space-x-2 cursor-pointer"
          >
            <span>🔐</span>
            <span>立即解鎖身分</span>
          </button>
          <button
            @click="router.push('/ledger')"
            type="button"
            class="px-5 py-3 rounded-2xl bg-white/20 hover:bg-white/30 text-white font-bold text-sm backdrop-blur-md transition flex items-center justify-center space-x-1.5 cursor-pointer"
          >
            <span>🏆</span>
            <span>查看榮譽存摺</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 步驟 1: 如何解鎖身分 -->
    <div class="bg-white rounded-3xl p-6 sm:p-8 border border-gray-100 shadow-sm space-y-4">
      <div class="flex items-center space-x-3 pb-3 border-b border-gray-100">
        <div class="w-12 h-12 rounded-2xl bg-frog-100 text-frog-700 flex items-center justify-center text-2xl font-black shadow-inner">
          1
        </div>
        <div>
          <h3 class="text-lg font-bold text-gray-900 flex items-center gap-2">
            <span>🔐 如何解鎖身分？</span>
            <span class="text-xs bg-frog-100 text-frog-800 font-semibold px-2 py-0.5 rounded-full">第一步</span>
          </h3>
          <p class="text-xs text-gray-500">訪客模式僅供瀏覽存摺，解鎖個人帳號後即可享有登記與心願兌換功能</p>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
        <div class="p-4 rounded-2xl bg-gray-50 border border-gray-100 space-y-2">
          <div class="w-8 h-8 rounded-xl bg-white flex items-center justify-center font-bold text-frog-600 shadow-sm text-sm">
            Step 1
          </div>
          <h4 class="font-bold text-gray-800 text-sm">點擊右上角解鎖</h4>
          <p class="text-xs text-gray-500 leading-relaxed">
            在頂部導航列右上角，點選「<strong>👦 訪客模式 | 🔐 解鎖</strong>」按鈕開啟解鎖彈窗。
          </p>
        </div>

        <div class="p-4 rounded-2xl bg-gray-50 border border-gray-100 space-y-2">
          <div class="w-8 h-8 rounded-xl bg-white flex items-center justify-center font-bold text-frog-600 shadow-sm text-sm">
            Step 2
          </div>
          <h4 class="font-bold text-gray-800 text-sm">選擇您的角色身分</h4>
          <p class="text-xs text-gray-500 leading-relaxed">
            在成員清單中點擊自己的角色：<strong>家長</strong> 或 <strong>小孩成員</strong>。
          </p>
        </div>

        <div class="p-4 rounded-2xl bg-gray-50 border border-gray-100 space-y-2">
          <div class="w-8 h-8 rounded-xl bg-white flex items-center justify-center font-bold text-frog-600 shadow-sm text-sm">
            Step 3
          </div>
          <h4 class="font-bold text-gray-800 text-sm">輸入 4 位數 PIN 碼</h4>
          <p class="text-xs text-gray-500 leading-relaxed">
            使用鍵盤輸入 4 碼 PIN 碼（小孩帳戶預設為 <strong>0000</strong>，家長輸入家長管理碼）即可完成解鎖！
          </p>
        </div>
      </div>

      <div class="p-4 bg-emerald-50/60 rounded-2xl border border-emerald-100 text-xs text-emerald-800 space-y-1">
        <div class="font-bold flex items-center gap-1.5">
          <span>💡</span>
          <span>獨立會話與安全鎖定機制：</span>
        </div>
        <p class="leading-relaxed text-emerald-700">
          解鎖是專屬當前瀏覽器的「獨立會話（Session）」，不同手機、平板或電腦分頁互不干擾。系統內建 <strong>15 分鐘無操作自動安全鎖定</strong>，保障全家人的隱私與安全。
        </p>
      </div>
    </div>

    <!-- 步驟 2: 如何申請加點 -->
    <div class="bg-white rounded-3xl p-6 sm:p-8 border border-gray-100 shadow-sm space-y-4">
      <div class="flex items-center space-x-3 pb-3 border-b border-gray-100">
        <div class="w-12 h-12 rounded-2xl bg-amber-100 text-amber-800 flex items-center justify-center text-2xl font-black shadow-inner">
          2
        </div>
        <div>
          <h3 class="text-lg font-bold text-gray-900 flex items-center gap-2">
            <span>📝 如何進行點數登記？</span>
            <span class="text-xs bg-amber-100 text-amber-800 font-semibold px-2 py-0.5 rounded-full">第二步</span>
          </h3>
          <p class="text-xs text-gray-500">小孩自律主動完成任務自主登記，或由家長評估表現發放點數獎勵</p>
        </div>
      </div>

      <div class="space-y-3 pt-1">
        <div class="flex items-start space-x-3 p-3.5 rounded-2xl bg-gray-50 border border-gray-100">
          <span class="text-xl">🎯</span>
          <div>
            <h4 class="font-bold text-gray-800 text-sm">1. 前往「點數登記」頁面</h4>
            <p class="text-xs text-gray-500 mt-0.5">
              解鎖帳號後，上方導航列會出現「<strong>📝 點數登記</strong>」選單。點選進入後，小孩帳號會<strong>自動鎖定為該小孩自身</strong>（無法切換幫手足登記，保障公平）；家長帳號則可自由切換要登記點數的對象。
            </p>
          </div>
        </div>

        <div class="flex items-start space-x-3 p-3.5 rounded-2xl bg-gray-50 border border-gray-100">
          <span class="text-xl">⚙️</span>
          <div>
            <h4 class="font-bold text-gray-800 text-sm">2. 選擇規則或自訂事項</h4>
            <p class="text-xs text-gray-500 mt-0.5">
              可點擊上方<strong>常用規則快捷按鈕</strong>（如：主動折棉被、完成作業、閱讀課外書等），點數將自動試算帶出；也可以切換至<strong>自由臨時事項</strong>自行輸入名稱與獎勵點數。
            </p>
          </div>
        </div>

        <div class="flex items-start space-x-3 p-3.5 rounded-2xl bg-gray-50 border border-gray-100">
          <span class="text-xl">🚀</span>
          <div>
            <h4 class="font-bold text-gray-800 text-sm">3. 一鍵確認送出</h4>
            <p class="text-xs text-gray-500 mt-0.5">
              可依需求填寫備註（例如：「今天小考 100 分」），點擊下方「<strong>📝 確認申請點數</strong>」。由於您已事先解鎖登入，<strong>無需重複輸入密碼</strong>，點數將直接計入個人存摺與累計總點數！
            </p>
          </div>
        </div>
      </div>

      <div class="p-4 bg-amber-50/60 rounded-2xl border border-amber-100 text-xs text-amber-900 space-y-1">
        <div class="font-bold flex items-center gap-1.5">
          <span>⚠️</span>
          <span>小孩帳號權限安全規則：</span>
        </div>
        <p class="leading-relaxed text-amber-800">
          小孩帳戶<strong>僅能申請增加自身點數（點數必須為正數）</strong>，嚴禁自訂扣點；扣點處罰為家長專屬權限。同時後端設有防偽檢核，小孩無法跨帳號幫其他手足登記。
        </p>
      </div>
    </div>

    <!-- 步驟 3: 如何申請兌換 -->
    <div class="bg-white rounded-3xl p-6 sm:p-8 border border-gray-100 shadow-sm space-y-4">
      <div class="flex items-center space-x-3 pb-3 border-b border-gray-100">
        <div class="w-12 h-12 rounded-2xl bg-blue-100 text-blue-800 flex items-center justify-center text-2xl font-black shadow-inner">
          3
        </div>
        <div>
          <h3 class="text-lg font-bold text-gray-900 flex items-center gap-2">
            <span>🎁 如何申請心願兌換？</span>
            <span class="text-xs bg-blue-100 text-blue-800 font-semibold px-2 py-0.5 rounded-full">第三步</span>
          </h3>
          <p class="text-xs text-gray-500">平時努力累積的榮譽點數，可以在商城兌換心儀的禮物與特權獎勵</p>
        </div>
      </div>

      <div class="space-y-3 pt-1">
        <div class="flex items-start space-x-3 p-3.5 rounded-2xl bg-gray-50 border border-gray-100">
          <span class="text-xl">🛍️</span>
          <div>
            <h4 class="font-bold text-gray-800 text-sm">1. 前往「兌換商城」</h4>
            <p class="text-xs text-gray-500 mt-0.5">
              解鎖小孩帳號後，上方導航點選「<strong>🎁 兌換商城</strong>」。頂部會顯示您的專屬<strong>可用點數錢包</strong>，並列出所有上架中的心願獎品。
            </p>
          </div>
        </div>

        <div class="flex items-start space-x-3 p-3.5 rounded-2xl bg-gray-50 border border-gray-100">
          <span class="text-xl">✨</span>
          <div>
            <h4 class="font-bold text-gray-800 text-sm">2. 挑選心願品項並送出兌換</h4>
            <p class="text-xs text-gray-500 mt-0.5">
              瀏覽喜歡的商品（例如冰淇淋、SWITCH 遊戲時間、週末出遊等），確認可用點數充足後，點擊「<strong>🎁 兌換</strong>」按鈕。
            </p>
          </div>
        </div>

        <div class="flex items-start space-x-3 p-3.5 rounded-2xl bg-gray-50 border border-gray-100">
          <span class="text-xl">👨‍👩‍👧</span>
          <div>
            <h4 class="font-bold text-gray-800 text-sm">3. 預扣點數並提醒家長核銷</h4>
            <p class="text-xs text-gray-500 mt-0.5">
              系統將暫時預扣該獎品點數，並產生一筆「<strong>待審核 (PENDING)</strong>」兌換紀錄。請提醒爸爸媽媽以家長身分解鎖後，至商城「待審核申請」進行核銷兌現！
            </p>
          </div>
        </div>
      </div>

      <div class="p-4 bg-blue-50/60 rounded-2xl border border-blue-100 text-xs text-blue-900 space-y-1">
        <div class="font-bold flex items-center gap-1.5">
          <span>🔒</span>
          <span>兌換安全與審核機制：</span>
        </div>
        <p class="leading-relaxed text-blue-800">
          每一位小孩僅能使用自己的點數錢包兌換，不可跨成員使用他人點數。若家長審核駁回（如當日作業未完成），預扣點數將<strong>100% 全額自動退回</strong>個人錢包。
        </p>
      </div>
    </div>

    <!-- 常見問答 (FAQ) -->
    <div class="bg-white rounded-3xl p-6 sm:p-8 border border-gray-100 shadow-sm space-y-4">
      <h3 class="text-base font-bold text-gray-800 flex items-center space-x-2 pb-3 border-b border-gray-100">
        <span>❓</span>
        <span>常見問題 FAQ</span>
      </h3>

      <div class="space-y-4 text-sm">
        <div class="p-4 rounded-2xl bg-gray-50 border border-gray-100 space-y-1">
          <h4 class="font-bold text-gray-900 text-xs sm:text-sm">Q: 小孩如果忘記 PIN 碼該怎麼辦？</h4>
          <p class="text-xs text-gray-600 leading-relaxed">
            請爸爸媽媽以<strong>家長身分解鎖</strong>後，點選上方「家庭成員」清單，找到該小孩的卡片點擊「🔑 PIN」，即可直接為小孩重設新的 4 位數 PIN 碼。
          </p>
        </div>

        <div class="p-4 rounded-2xl bg-gray-50 border border-gray-100 space-y-1">
          <h4 class="font-bold text-gray-900 text-xs sm:text-sm">Q: 如何更換自己的頭像或自行變更 PIN 碼？</h4>
          <p class="text-xs text-gray-600 leading-relaxed">
            以您的小孩身分解鎖後，導航列會出現「<strong>個人成員</strong>」按鈕。點入後僅能編輯自己的代表頭像 Emoji，或輸入舊 PIN 碼變更為新密碼，無法變更其他人的資料。
          </p>
        </div>

        <div class="p-4 rounded-2xl bg-gray-50 border border-gray-100 space-y-1">
          <h4 class="font-bold text-gray-900 text-xs sm:text-sm">Q: 為什麼在訪客模式看不到兌換商城和點數登記？</h4>
          <p class="text-xs text-gray-600 leading-relaxed">
            為了保護家庭帳號安全，訪客模式僅提供查看「榮譽存摺」。請點擊右上角的「<strong>🔐 解鎖</strong>」按鈕，選擇登入您的角色身分，專屬功能就會立即顯現！
          </p>
        </div>
      </div>
    </div>

    <!-- 底部引導按鈕 -->
    <div class="flex flex-col sm:flex-row items-center justify-center gap-3 pt-4">
      <button
        v-if="!authStore.isUnlocked"
        @click="triggerUnlock"
        type="button"
        class="w-full sm:w-auto px-8 py-3.5 rounded-2xl bg-frog-500 hover:bg-frog-600 text-white font-bold text-sm shadow-md shadow-frog-200 active:scale-98 transition flex items-center justify-center space-x-2 cursor-pointer"
      >
        <span>🔐</span>
        <span>立即解鎖身分開始使用</span>
      </button>
      <button
        @click="router.push('/ledger')"
        type="button"
        class="w-full sm:w-auto px-8 py-3.5 rounded-2xl bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 font-bold text-sm shadow-sm transition flex items-center justify-center space-x-2 cursor-pointer"
      >
        <span>🏆</span>
        <span>返回榮譽點數存摺</span>
      </button>
    </div>
  </div>
</template>
