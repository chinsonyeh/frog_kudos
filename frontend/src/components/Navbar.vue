<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import MemberAvatar from '@/components/MemberAvatar.vue'

const emit = defineEmits(['openPinModal', 'openSystemModal', 'openMemberModal', 'openThemeModal'])

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const themeStore = useThemeStore()

const currentPath = computed(() => route.path)

const navItems = computed(() => {
  if (authStore.isParent) {
    return [
      { type: 'link', name: '點數登記', path: '/record', icon: '📝' },
      { type: 'link', name: '榮譽存摺', path: '/ledger', icon: '🏆' },
      { type: 'link', name: '商城與審核', path: '/rewards', icon: '🎁' },
      { type: 'button', name: '家庭成員', action: () => emit('openMemberModal'), icon: '👥', title: '管理家庭成員清單與自訂成員' },
      { type: 'link', name: '規則管理', path: '/rules', icon: '⚙️' },
      { type: 'link', name: '使用說明', path: '/guide', icon: '📖' },
    ]
  } else if (authStore.isChild) {
    return [
      { type: 'link', name: '點數登記', path: '/record', icon: '📝' },
      { type: 'link', name: '榮譽存摺', path: '/ledger', icon: '🏆' },
      { type: 'link', name: '兌換商城', path: '/rewards', icon: '🎁' },
      { type: 'button', name: '個人成員', action: () => emit('openMemberModal'), avatar: authStore.unlockedMember?.avatar || '👤', icon: '👤', title: '變更個人代表頭像與 PIN 碼' },
      { type: 'link', name: '使用說明', path: '/guide', icon: '📖' },
    ]
  } else {
    // 訪客模式：移除家庭成員按鈕、兌換商城按鈕、點數登記按鈕，僅允許看榮譽點數頁面與使用說明
    return [
      { type: 'link', name: '榮譽存摺', path: '/ledger', icon: '🏆' },
      { type: 'link', name: '使用說明', path: '/guide', icon: '📖' },
    ]
  }
})

function handleModeToggle() {
  if (authStore.isUnlocked) {
    authStore.lock()
    if (route.path !== '/ledger' && route.path !== '/guide') {
      router.push('/ledger')
    }
  } else {
    emit('openPinModal')
  }
}

function handleOpenSystem() {
  if (authStore.isParent) {
    emit('openSystemModal')
  } else {
    emit('openPinModal')
  }
}
</script>

<template>
  <header class="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-gray-100 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <!-- Logo 與品牌 -->
        <div class="flex items-center space-x-3">
          <!-- 頁面左上青蛙圖示 (支援即時更換不同青蛙造型) -->
          <div
            @click.stop="emit('openThemeModal', 'icon')"
            class="w-10 h-10 rounded-2xl overflow-hidden shadow-inner flex items-center justify-center relative group cursor-pointer border border-frog-200/60 bg-frog-50 hover:ring-2 hover:ring-frog-400 transition transform active:scale-95 flex-shrink-0"
            title="點擊更換青蛙圖示與風格配色 🎨"
          >
            <img
              v-if="themeStore.currentLogo?.src"
              :src="themeStore.currentLogo.src"
              :alt="themeStore.currentLogo.name"
              class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
            />
            <span v-else class="text-2xl">🐸</span>
            
            <!-- 懸浮提示小指示 -->
            <span class="absolute bottom-0 right-0 bg-black/60 text-white text-[8px] rounded-tl-md px-1 opacity-0 group-hover:opacity-100 transition-opacity">
              🎨
            </span>
          </div>

          <div class="cursor-pointer" @click="router.push(authStore.isParent ? '/record' : '/ledger')">
            <h1 class="text-lg font-black tracking-tight text-gray-900 leading-none">
              Frog Kudos
            </h1>
            <span class="text-[10px] font-semibold text-frog-600 uppercase tracking-wider">
              家庭積分獎勵系統
            </span>
          </div>
        </div>

        <!-- 桌面版主要導航 Navigation Links -->
        <nav class="hidden md:flex space-x-1 lg:space-x-2 items-center">
          <template v-for="item in navItems" :key="item.name">
            <router-link
              v-if="item.type === 'link'"
              :to="item.path"
              class="px-4 py-2 rounded-xl text-sm font-semibold transition flex items-center space-x-1.5"
              :class="currentPath === item.path ? 'bg-frog-50 text-frog-700 shadow-sm' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'"
            >
              <span>{{ item.icon }}</span>
              <span>{{ item.name }}</span>
            </router-link>
            <button
              v-else-if="item.type === 'button'"
              @click="item.action"
              type="button"
              class="px-4 py-2 rounded-xl text-sm font-semibold transition flex items-center space-x-1.5 text-gray-600 hover:text-gray-900 hover:bg-gray-50 active:bg-gray-100 cursor-pointer"
              :title="item.title || item.name"
            >
              <MemberAvatar v-if="item.avatar" :avatar="item.avatar" size="xs" />
              <span v-else>{{ item.icon }}</span>
              <span>{{ item.name }}</span>
            </button>
          </template>
        </nav>

        <!-- 右側：模式切換與設定按鈕 -->
        <div class="flex items-center space-x-2 sm:space-x-3">
          <!-- 1. 家長解鎖狀態 -->
          <div
            v-if="authStore.isParent"
            class="flex items-center bg-frog-50 border border-frog-200 text-frog-800 rounded-full px-3 py-1.5 text-xs font-semibold shadow-sm"
          >
            <span class="mr-1.5">👑 家長模式</span>
            <span class="text-frog-600 font-mono text-[11px] mr-2">({{ authStore.remainingMinutesFormatted }})</span>
            <button
              @click="handleModeToggle"
              class="text-frog-700 hover:text-red-600 transition underline underline-offset-2 ml-1 cursor-pointer"
              title="立即手動鎖定並退回訪客模式"
            >
              🔒 鎖定
            </button>
          </div>

          <!-- 2. 小孩解鎖狀態 -->
          <div
            v-else-if="authStore.isChild"
            class="flex items-center space-x-1.5 bg-frog-50 border border-frog-200 text-frog-800 rounded-full px-3 py-1.5 text-xs font-semibold shadow-sm"
          >
            <MemberAvatar :avatar="authStore.unlockedMember?.avatar" :name="authStore.unlockedMember?.name" size="xs" />
            <span>{{ authStore.unlockedMember?.name }} (小孩模式)</span>
            <span class="text-frog-600 font-mono text-[11px] mr-1">({{ authStore.remainingMinutesFormatted }})</span>
            <button
              @click="handleModeToggle"
              class="text-frog-700 hover:text-red-600 transition underline underline-offset-2 ml-1 cursor-pointer"
              title="立即手動鎖定並退出小孩帳號"
            >
              🔒 鎖定
            </button>
          </div>

          <!-- 3. 未解鎖 / 訪客模式 -->
          <button
            v-else
            @click="handleModeToggle"
            class="flex items-center space-x-1.5 bg-gray-100 hover:bg-gray-200 active:bg-gray-300 text-gray-700 rounded-full px-3 py-1.5 text-xs font-semibold transition cursor-pointer"
          >
            <span>👦 訪客模式</span>
            <span class="text-gray-400">|</span>
            <span class="text-frog-700 font-bold hover:underline">🔐 解鎖</span>
          </button>

          <!-- 佈景主題切換按鈕 (🎨 10 款特色主題) -->
          <button
            @click="emit('openThemeModal', 'theme')"
            class="w-9 h-9 rounded-xl border border-gray-200 flex items-center justify-center text-gray-600 hover:text-gray-900 hover:bg-gray-50 active:bg-gray-100 transition shadow-sm cursor-pointer"
            title="更換個人佈景主題與青蛙圖示"
          >
            🎨
          </button>

          <!-- 系統設定齒輪按鈕 -->
          <button
            @click="handleOpenSystem"
            class="w-9 h-9 rounded-xl border border-gray-200 flex items-center justify-center text-gray-600 hover:text-gray-900 hover:bg-gray-50 active:bg-gray-100 transition shadow-sm cursor-pointer"
            title="系統設定、備份與升級維運 (需家長權限)"
          >
            ⚙️
          </button>
        </div>
      </div>
    </div>

    <!-- 行動裝置底部快速導航 (Mobile Tab Bar) -->
    <div class="md:hidden border-t border-gray-100 bg-white/95 px-2 py-1.5 flex justify-around overflow-x-auto shadow-sm">
      <template v-for="item in navItems" :key="item.name">
        <router-link
          v-if="item.type === 'link'"
          :to="item.path"
          class="flex flex-col items-center py-1 px-2 rounded-lg text-xs font-medium transition whitespace-nowrap flex-shrink-0"
          :class="currentPath === item.path ? 'text-frog-600 font-bold' : 'text-gray-500 hover:text-gray-800'"
        >
          <span class="text-lg leading-none mb-0.5">{{ item.icon }}</span>
          <span>{{ item.name }}</span>
        </router-link>
        <button
          v-else-if="item.type === 'button'"
          @click="item.action"
          type="button"
          class="flex flex-col items-center py-1 px-2 rounded-lg text-xs font-medium text-gray-500 hover:text-gray-800 transition cursor-pointer whitespace-nowrap flex-shrink-0"
        >
          <div v-if="item.avatar" class="w-5 h-5 mb-0.5 flex items-center justify-center">
            <MemberAvatar :avatar="item.avatar" size="xs" />
          </div>
          <span v-else class="text-lg leading-none mb-0.5">{{ item.icon }}</span>
          <span>{{ item.name }}</span>
        </button>
      </template>
    </div>
  </header>
</template>
