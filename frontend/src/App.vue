<script setup>
import { ref } from 'vue'
import Navbar from '@/components/Navbar.vue'
import ParentPinModal from '@/components/ParentPinModal.vue'
import SystemSettingsModal from '@/components/SystemSettingsModal.vue'
import MemberModal from '@/components/MemberModal.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const showPinModal = ref(false)
const showSystemModal = ref(false)
const showMemberModal = ref(false)
</script>

<template>
  <div class="min-h-screen flex flex-col bg-gray-50 text-gray-800">
    <!-- 頂部導航列 -->
    <Navbar
      @open-pin-modal="showPinModal = true"
      @open-system-modal="showSystemModal = true"
      @open-member-modal="showMemberModal = true"
    />

    <!-- 主要內容區 -->
    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
      <router-view />
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

    <!-- 底部版權宣告 -->
    <footer class="py-4 text-center text-xs text-gray-400 border-t border-gray-100">
      🐸 Frog Kudos 家庭積分獎勵系統 &copy; 2026 | 單一連接埠整合架構
    </footer>
  </div>
</template>
