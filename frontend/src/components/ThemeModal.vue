<script setup>
import { useThemeStore } from '@/stores/theme'

const props = defineProps({
  show: Boolean,
})
const emit = defineEmits(['close'])

const themeStore = useThemeStore()

function selectTheme(themeId) {
  themeStore.setTheme(themeId)
}
</script>

<template>
  <div
    v-if="show"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
    @click.self="$emit('close')"
  >
    <div class="bg-white rounded-3xl shadow-2xl max-w-2xl w-full p-6 sm:p-8 max-h-[90vh] flex flex-col">
      <!-- 頂部標題區 -->
      <div class="flex items-center justify-between pb-4 border-b border-gray-100 flex-shrink-0">
        <div class="flex items-center space-x-2">
          <span class="text-2xl">🎨</span>
          <div>
            <h3 class="text-lg font-black text-gray-900 leading-tight">個人風格佈景主題</h3>
            <p class="text-xs text-gray-500">10 款特色主題任選，為您的裝置換上專屬色彩！</p>
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

      <!-- 10 款主題清單 (滾動區域) -->
      <div class="flex-1 overflow-y-auto py-4 space-y-3 pr-1">
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
          <span>設定僅儲存於當前瀏覽器中，不同裝置各自獨立、互不干擾。</span>
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
