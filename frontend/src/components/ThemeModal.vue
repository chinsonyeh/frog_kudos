<script setup>
import { ref, watch } from 'vue'
import { useThemeStore } from '@/stores/theme'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/services/api'

const props = defineProps({
  show: Boolean,
  initialTab: {
    type: String,
    default: 'icon',
  },
})
const emit = defineEmits(['close'])

const themeStore = useThemeStore()
const authStore = useAuthStore()

const activeTab = ref(props.initialTab || 'icon')
const pwaLoading = ref(false)
const pwaSuccessMsg = ref('')
const pwaErrorMsg = ref('')

watch(
  () => props.initialTab,
  (newTab) => {
    if (newTab) activeTab.value = newTab
  }
)

function selectLogoIcon(iconId) {
  themeStore.setLogoIcon(iconId)
  pwaSuccessMsg.value = ''
  pwaErrorMsg.value = ''
}

function selectTheme(themeId) {
  themeStore.setTheme(themeId)
}

async function applyToSystemPwa() {
  if (!authStore.isParent) return
  pwaLoading.value = true
  pwaSuccessMsg.value = ''
  pwaErrorMsg.value = ''
  try {
    const res = await api.updateSystemIcon(themeStore.currentLogoId)
    pwaSuccessMsg.value = res.message || '已成功套用為全站 PWA / 桌面 App 圖示！'
  } catch (err) {
    pwaErrorMsg.value = err.message || '套用全站圖示失敗'
  } finally {
    pwaLoading.value = false
  }
}
</script>

<template>
  <div
    v-if="show"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
    @click.self="$emit('close')"
  >
    <div class="bg-white rounded-3xl shadow-2xl max-w-2xl w-full p-6 sm:p-8 max-h-[92vh] flex flex-col">
      <!-- 頂部標題區 -->
      <div class="flex items-center justify-between pb-3 border-b border-gray-100 flex-shrink-0">
        <div class="flex items-center space-x-2.5">
          <div class="w-10 h-10 rounded-2xl bg-frog-100 text-frog-700 flex items-center justify-center text-xl shadow-inner overflow-hidden">
            <img
              v-if="themeStore.currentLogo?.src"
              :src="themeStore.currentLogo.src"
              :alt="themeStore.currentLogo.name"
              class="w-full h-full object-cover"
            />
            <span v-else>🐸</span>
          </div>
          <div>
            <h3 class="text-lg font-black text-gray-900 leading-tight">青蛙圖示與視覺風格設定</h3>
            <p class="text-xs text-gray-500">10 款原創青蛙標誌與 10 款全站配色，打造個人專屬體驗！</p>
          </div>
        </div>
        <button
          @click="$emit('close')"
          type="button"
          class="text-gray-400 hover:text-gray-600 text-xl font-bold w-9 h-9 rounded-xl hover:bg-gray-100 flex items-center justify-center transition cursor-pointer"
        >
          ✕
        </button>
      </div>

      <!-- 分頁切換選單 -->
      <div class="flex space-x-2 border-b border-gray-100 py-3 flex-shrink-0">
        <button
          @click="activeTab = 'icon'"
          type="button"
          class="flex-1 py-2 px-3 rounded-xl text-xs sm:text-sm font-bold transition flex items-center justify-center space-x-2 cursor-pointer"
          :class="activeTab === 'icon' ? 'bg-frog-500 text-white shadow-md shadow-frog-200' : 'text-gray-600 hover:bg-gray-100'"
        >
          <span>🐸</span>
          <span>頁面左上青蛙圖示 (10 款)</span>
        </button>
        <button
          @click="activeTab = 'theme'"
          type="button"
          class="flex-1 py-2 px-3 rounded-xl text-xs sm:text-sm font-bold transition flex items-center justify-center space-x-2 cursor-pointer"
          :class="activeTab === 'theme' ? 'bg-frog-500 text-white shadow-md shadow-frog-200' : 'text-gray-600 hover:bg-gray-100'"
        >
          <span>🎨</span>
          <span>全站佈景主題 (10 款)</span>
        </button>
      </div>

      <!-- 【分頁 1: 10 款原創青蛙圖示選擇】 -->
      <div v-if="activeTab === 'icon'" class="flex-1 overflow-y-auto py-4 space-y-4 pr-1">
        <!-- 目前選中使用中的青蛙預覽卡片 -->
        <div class="p-4 rounded-2xl bg-frog-50/70 border border-frog-200/80 flex items-center justify-between">
          <div class="flex items-center space-x-3.5">
            <img
              :src="themeStore.currentLogo.src"
              :alt="themeStore.currentLogo.name"
              class="w-14 h-14 rounded-2xl object-cover shadow-md border-2 border-white ring-2 ring-frog-400 flex-shrink-0"
            />
            <div>
              <div class="flex items-center space-x-2">
                <span class="font-bold text-gray-900 text-base">{{ themeStore.currentLogo.name }}</span>
                <span class="text-[11px] bg-frog-500 text-white font-bold px-2 py-0.5 rounded-full shadow-xs">使用中</span>
              </div>
              <p class="text-xs text-gray-600 mt-0.5">{{ themeStore.currentLogo.description }}</p>
            </div>
          </div>
          <div class="text-xs font-mono font-bold text-frog-700 bg-white px-3 py-1.5 rounded-xl border border-frog-200 shadow-xs hidden sm:block">
            {{ themeStore.currentLogo.subtitle }}
          </div>
        </div>

        <!-- 10 款青蛙圖示網格清單 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div
            v-for="icon in themeStore.logoIcons"
            :key="icon.id"
            @click="selectLogoIcon(icon.id)"
            class="group relative p-3 rounded-2xl border-2 transition-all cursor-pointer flex items-center space-x-3"
            :class="
              themeStore.currentLogoId === icon.id
                ? 'border-frog-500 bg-frog-50/60 shadow-md ring-2 ring-frog-500/20'
                : 'border-gray-200/80 bg-white hover:border-gray-300 hover:shadow-xs'
            "
          >
            <!-- 圖示縮圖 -->
            <img
              :src="icon.src"
              :alt="icon.name"
              class="w-14 h-14 rounded-2xl object-cover shadow-sm border border-gray-100 flex-shrink-0 group-hover:scale-105 transition-transform"
            />

            <!-- 文字資訊 -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center space-x-1.5">
                <span class="font-bold text-gray-900 text-sm truncate">{{ icon.name }}</span>
                <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded-md bg-gray-100 text-gray-600 flex-shrink-0">
                  {{ icon.tag }}
                </span>
              </div>
              <p class="text-[11px] text-gray-500 mt-0.5 line-clamp-2 leading-relaxed">
                {{ icon.description }}
              </p>
            </div>

            <!-- 選中勾勾 -->
            <div
              v-if="themeStore.currentLogoId === icon.id"
              class="w-5 h-5 rounded-full bg-frog-500 text-white flex items-center justify-center text-xs font-bold shadow-xs flex-shrink-0 animate-in zoom-in"
            >
              ✓
            </div>
          </div>
        </div>

        <!-- 家長同步為全站 PWA 圖示選項 (FR-4 / PWA 桌面圖示同步) -->
        <div v-if="authStore.isParent" class="mt-4 p-4 rounded-2xl bg-gray-50 border border-gray-200 space-y-2.5">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <div class="flex items-center space-x-1.5">
                <span class="text-sm font-bold text-gray-800">👑 家長進階：同步為全站 PWA / 桌面 App 圖示</span>
                <span class="text-[10px] bg-amber-100 text-amber-800 font-bold px-1.5 py-0.5 rounded-md">家長專屬</span>
              </div>
              <p class="text-xs text-gray-500 mt-0.5">
                將目前選中的「{{ themeStore.currentLogo.name }}」套用為全站手機主畫面圖示與 PWA 啟動圖示。
              </p>
            </div>
            <button
              @click="applyToSystemPwa"
              :disabled="pwaLoading"
              type="button"
              class="px-4 py-2 rounded-xl bg-gray-900 hover:bg-black text-white text-xs font-bold shadow-sm transition flex-shrink-0 flex items-center justify-center space-x-1.5 cursor-pointer disabled:opacity-50"
            >
              <span>{{ pwaLoading ? '⏳ 套用中...' : '📱 同步為 PWA 圖示' }}</span>
            </button>
          </div>

          <p v-if="pwaSuccessMsg" class="text-xs text-frog-600 font-bold flex items-center space-x-1">
            <span>✅</span>
            <span>{{ pwaSuccessMsg }}</span>
          </p>
          <p v-if="pwaErrorMsg" class="text-xs text-red-600 font-bold flex items-center space-x-1">
            <span>❌</span>
            <span>{{ pwaErrorMsg }}</span>
          </p>
        </div>
      </div>

      <!-- 【分頁 2: 10 款全域色彩佈景主題】 -->
      <div v-else-if="activeTab === 'theme'" class="flex-1 overflow-y-auto py-4 space-y-3 pr-1">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div
            v-for="theme in themeStore.themes"
            :key="theme.id"
            @click="selectTheme(theme.id)"
            class="group relative p-3.5 rounded-2xl border-2 transition-all cursor-pointer flex flex-col justify-between"
            :class="
              themeStore.currentTheme === theme.id
                ? 'border-frog-500 bg-frog-50/50 shadow-md shadow-frog-900/5 ring-2 ring-frog-500/20'
                : 'border-gray-200/80 bg-white hover:border-gray-300 hover:shadow-sm'
            "
          >
            <!-- 頂部資訊：Emoji + 名稱 + 標籤 -->
            <div class="flex items-start justify-between">
              <div class="flex items-center space-x-2.5">
                <span class="text-2xl group-hover:scale-110 transition-transform">{{ theme.emoji }}</span>
                <div>
                  <div class="flex items-center space-x-1.5">
                    <span class="font-bold text-gray-900 text-sm">{{ theme.name }}</span>
                    <span
                      class="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                      :style="{
                        backgroundColor: theme.palette[0],
                        color: theme.palette[2],
                      }"
                    >
                      {{ theme.tag }}
                    </span>
                  </div>
                  <p class="text-xs text-gray-500 mt-0.5 line-clamp-1">{{ theme.description }}</p>
                </div>
              </div>

              <!-- 目前選中指示勾勾 -->
              <div
                v-if="themeStore.currentTheme === theme.id"
                class="w-5 h-5 rounded-full bg-frog-500 text-white flex items-center justify-center text-xs font-bold shadow-sm flex-shrink-0 animate-in zoom-in"
              >
                ✓
              </div>
            </div>

            <!-- 色票條形預覽 (三階色譜) -->
            <div class="mt-3 flex items-center space-x-1.5 pt-2 border-t border-gray-100/80">
              <span class="text-[10px] font-medium text-gray-400">色彩預覽:</span>
              <div class="flex items-center space-x-1 flex-1">
                <div
                  v-for="(c, idx) in theme.palette"
                  :key="idx"
                  class="h-3 flex-1 rounded-full shadow-inner"
                  :style="{ backgroundColor: c }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部提示與完成按鈕 -->
      <div class="pt-4 border-t border-gray-100 flex flex-col sm:flex-row items-center justify-between gap-3 flex-shrink-0">
        <div class="text-xs text-gray-500 flex items-center space-x-1.5 text-center sm:text-left">
          <span>💡</span>
          <span>圖示與主題均安全記憶於當前瀏覽器中，每台手機、平板與電腦可獨立自由設定！</span>
        </div>
        <button
          @click="$emit('close')"
          type="button"
          class="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-frog-500 hover:bg-frog-600 text-white text-sm font-bold shadow-sm transition cursor-pointer"
        >
          完成
        </button>
      </div>
    </div>
  </div>
</template>
