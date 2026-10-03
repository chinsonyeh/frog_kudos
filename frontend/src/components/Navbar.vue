<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const emit = defineEmits(['openPinModal', 'openSystemModal', 'openMemberModal'])

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const currentPath = computed(() => route.path)

const navItems = computed(() => {
  if (authStore.isParent) {
    return [
      { type: 'link', name: '快速登記', path: '/record', icon: '📝' },
      { type: 'link', name: '榮譽存摺', path: '/ledger', icon: '🏆' },
      { type: 'link', name: '商城與審核', path: '/rewards', icon: '🎁' },
      { type: 'button', name: '家庭成員', action: () => emit('openMemberModal'), icon: '👥', title: '管理家庭成員清單與自訂成員' },
      { type: 'link', name: '規則管理', path: '/rules', icon: '⚙️' },
    ]
  } else {
    return [
      { type: 'link', name: '點數登記', path: '/record', icon: '📝' },
      { type: 'link', name: '榮譽存摺', path: '/ledger', icon: '🏆' },
      { type: 'link', name: '兌換商城', path: '/rewards', icon: '🎁' },
      { type: 'button', name: '家庭成員', action: () => emit('openMemberModal'), icon: '👥', title: '更換代表頭像與個人 PIN 碼' },
    ]
  }
})

function handleModeToggle() {
  if (authStore.isParent) {
    authStore.lockParent()
    if (route.path === '/rules') {
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
        <div class="flex items-center space-x-3 cursor-pointer" @click="router.push(authStore.isParent ? '/record' : '/ledger')">
          <div class="w-10 h-10 rounded-2xl bg-frog-100 text-frog-700 flex items-center justify-center text-2xl shadow-inner">
            🐸
          </div>
          <div>
            <h1 class="text-lg font-black tracking-tight text-gray-900 leading-none">
              Frog Kudos
            </h1>
            <span class="text-[10px] font-semibold text-frog-600 uppercase tracking-wider">
              家庭積分獎勵系統
            </span>
          </div>
        </div>

        <!-- 桌面版主要導航 Navigation Links (家庭成員置於規則管理左側) -->
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
              <span>{{ item.icon }}</span>
              <span>{{ item.name }}</span>
            </button>
          </template>
        </nav>

        <!-- 右側：模式切換與設定按鈕 -->
        <div class="flex items-center space-x-2 sm:space-x-3">
          <!-- 模式切換鈕 -->
          <div
            v-if="authStore.isParent"
            class="flex items-center bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-full px-3 py-1.5 text-xs font-semibold shadow-sm"
          >
            <span class="mr-1.5">🔐 家長模式</span>
            <span class="text-emerald-600 font-mono text-[11px] mr-2">({{ authStore.remainingMinutesFormatted }})</span>
            <button
              @click="handleModeToggle"
              class="text-emerald-700 hover:text-red-600 transition underline underline-offset-2 ml-1"
              title="立即手動鎖定並退回小孩模式"
            >
              🔒 鎖定
            </button>
          </div>

          <button
            v-else
            @click="handleModeToggle"
            class="flex items-center space-x-1.5 bg-gray-100 hover:bg-gray-200 active:bg-gray-300 text-gray-700 rounded-full px-3 py-1.5 text-xs font-semibold transition"
          >
            <span>👦 小孩模式</span>
            <span class="text-gray-400">|</span>
            <span class="text-frog-700 font-bold hover:underline">🔐 解鎖</span>
          </button>

          <!-- 系統設定齒輪按鈕 -->
          <button
            @click="handleOpenSystem"
            class="w-9 h-9 rounded-xl border border-gray-200 flex items-center justify-center text-gray-600 hover:text-gray-900 hover:bg-gray-50 active:bg-gray-100 transition shadow-sm"
            title="系統設定、備份與升級維運"
          >
            ⚙️
          </button>
        </div>
      </div>
    </div>

    <!-- 行動裝置底部快速導航 (Mobile Tab Bar) (家庭成員置於規則管理左側) -->
    <div class="md:hidden border-t border-gray-100 bg-white/95 px-2 py-1.5 flex justify-around shadow-sm">
      <template v-for="item in navItems" :key="item.name">
        <router-link
          v-if="item.type === 'link'"
          :to="item.path"
          class="flex flex-col items-center py-1 px-2.5 rounded-lg text-xs font-medium transition"
          :class="currentPath === item.path ? 'text-frog-600 font-bold' : 'text-gray-500 hover:text-gray-800'"
        >
          <span class="text-lg leading-none mb-0.5">{{ item.icon }}</span>
          <span>{{ item.name }}</span>
        </router-link>
        <button
          v-else-if="item.type === 'button'"
          @click="item.action"
          type="button"
          class="flex flex-col items-center py-1 px-2.5 rounded-lg text-xs font-medium text-gray-500 hover:text-gray-800 transition"
        >
          <span class="text-lg leading-none mb-0.5">{{ item.icon }}</span>
          <span>{{ item.name }}</span>
        </button>
      </template>
    </div>
  </header>
</template>
