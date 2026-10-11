<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import ParentPinModal from '@/components/ParentPinModal.vue'
import SystemSettingsModal from '@/components/SystemSettingsModal.vue'
import MemberModal from '@/components/MemberModal.vue'
import ThemeModal from '@/components/ThemeModal.vue'
import BadgeUnlockModal from '@/components/BadgeUnlockModal.vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/services/api'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const showPinModal = ref(false)
const showSystemModal = ref(false)
const showMemberModal = ref(false)
const showThemeModal = ref(false)
const themeModalTab = ref('icon')

const showPendingBadgeModal = ref(false)
const pendingBadges = ref([])

function handleOpenThemeModal(tab = 'icon') {
  themeModalTab.value = tab
  showThemeModal.value = true
}

async function checkPendingBadges(memberId) {
  if (!memberId || authStore.isParent) return
  try {
    const list = await api.getPendingBadges(memberId)
    if (list && list.length > 0) {
      pendingBadges.value = list
      showPendingBadgeModal.value = true
    }
  } catch (err) {
    console.error('查詢待通知成就失敗:', err)
  }
}

async function handleClosePendingBadges() {
  showPendingBadgeModal.value = false
  const mId = authStore.unlockedMemberId
  pendingBadges.value = []
  if (mId) {
    try {
      await api.ackBadges(mId)
    } catch (err) {
      console.error('確認成就通知失敗:', err)
    }
  }
}

// 監聽登入/解鎖狀態：當小孩用戶登入時，自動查詢是否有待通知之成就
watch(
  () => [authStore.unlockedMemberId, authStore.isChild],
  ([mId, isChild]) => {
    if (mId && isChild) {
      checkPendingBadges(mId)
    } else {
      showPendingBadgeModal.value = false
      pendingBadges.value = []
    }
  },
  { immediate: true }
)

// 頁面路徑切換時，若小孩處於登入狀態且尚未顯示彈窗，檢查是否有新審核通過之成就
watch(
  () => route.path,
  () => {
    if (authStore.unlockedMemberId && authStore.isChild && !showPendingBadgeModal.value) {
      checkPendingBadges(authStore.unlockedMemberId)
    }
  }
)

function handleVisibilityChange() {
  if (document.visibilityState === 'visible' && authStore.unlockedMemberId && authStore.isChild && !showPendingBadgeModal.value) {
    checkPendingBadges(authStore.unlockedMemberId)
  }
}

onMounted(() => {
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})

// 監聽解鎖與權限狀態變更：閒置逾時鎖定或權限失效時，若當前路由需要權限，自動安全跳轉至存摺頁面
watch(
  () => [authStore.isUnlocked, authStore.isParent],
  ([unlocked, isParent]) => {
    if (route.meta.requiresParent && !isParent) {
      router.push('/ledger')
    } else if (route.meta.requiresUnlock && !unlocked) {
      router.push('/ledger')
    }
  }
)
</script>

<template>
  <div class="min-h-screen flex flex-col bg-gray-50 text-gray-800">
    <!-- 頂部導航列 -->
    <Navbar
      @open-pin-modal="showPinModal = true"
      @open-system-modal="showSystemModal = true"
      @open-member-modal="showMemberModal = true"
      @open-theme-modal="handleOpenThemeModal"
    />

    <!-- 主要內容區 -->
    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
      <router-view @open-pin-modal="showPinModal = true" />
    </main>

    <!-- 家長 PIN 碼安全鎖彈窗 -->
    <ParentPinModal
      :show="showPinModal"
      @close="showPinModal = false"
      @unlocked="showPinModal = false"
    />

    <!-- 系統設定與維運中心彈窗 -->
    <SystemSettingsModal
      :show="showSystemModal"
      @close="showSystemModal = false"
    />

    <!-- 家庭成員管理彈窗 (FR-2 / FR-13) -->
    <MemberModal
      :show="showMemberModal"
      @close="showMemberModal = false"
      @member-updated="authStore.triggerMemberRefresh()"
    />

    <!-- 10 款特色佈景主題與青蛙圖示選擇彈窗 -->
    <ThemeModal
      :show="showThemeModal"
      :initial-tab="themeModalTab"
      @close="showThemeModal = false"
    />

    <!-- 成就達成慶祝通知彈窗 (小孩登入時提醒) -->
    <BadgeUnlockModal
      v-if="showPendingBadgeModal"
      :badges="pendingBadges"
      @close="handleClosePendingBadges"
    />

    <!-- 底部版權宣告 -->
    <footer class="py-4 text-center text-xs text-gray-400 border-t border-gray-100">
      🐸 Frog Kudos 家庭積分獎勵系統 &copy; 2026 | 單一連接埠整合架構
    </footer>
  </div>
</template>
