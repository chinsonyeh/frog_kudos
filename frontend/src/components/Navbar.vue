<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const emit = defineEmits(['openPinModal', 'openSystemModal'])

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const currentPath = computed(() => route.path)

const navLinks = computed(() => {
  if (authStore.isParent) {
    return [
      { name: '快速登記', path: '/record', icon: '📝' },
      { name: '榮譽存摺', path: '/ledger', icon: '🏆' },
      { name: '商城與審核', path: '/rewards', icon: '🎁' },
      { name: '規則管理', path: '/rules', icon: '⚙️' },
    ]
  } else {
    return [
      { name: '榮譽存摺', path: '/ledger', icon: '🏆' },
      { name: '兌換商城', path: '/rewards', icon: '🎁' },
    ]
  }
})

function handleModeToggle() {
  if (authStore.isParent) {
    authStore.lockParent()
    if (route.path === '/record' || route.path === '/rules') {
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

        <!-- 桌面版主要導航 Navigation Links -->
        <nav class="hidden md:flex space-x-1 lg:space-x-2">
          <router-link
            v-for="link in navLinks"
            :key="link.path"
            :to="link.path"
            class="px-4 py-2 rounded-xl text-sm font-semibold transition flex items-center space-x-1.5"
            :class="currentPath === link.path ? 'bg-frog-50 text-frog-700 shadow-sm' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'"
          >
            <span>{{ link.icon }}</span>
            <span>{{ link.name }}</span>
          </router-link>
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
            <span>👦 小孩模式 (唯讀)</span>
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

    <!-- 行動裝置底部快速導航 (Mobile Tab Bar) -->
    <div class="md:hidden border-t border-gray-100 bg-white/95 px-2 py-1.5 flex justify-around shadow-sm">
      <router-link
        v-for="link in navLinks"
        :key="link.path"
        :to="link.path"
        class="flex flex-col items-center py-1 px-3 rounded-lg text-xs font-medium transition"
        :class="currentPath === link.path ? 'text-frog-600 font-bold' : 'text-gray-500 hover:text-gray-800'"
      >
        <span class="text-lg leading-none mb-0.5">{{ link.icon }}</span>
        <span>{{ link.name }}</span>
      </router-link>
    </div>
  </header>
</template>
