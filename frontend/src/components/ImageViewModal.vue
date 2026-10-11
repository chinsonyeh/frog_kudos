<script setup>
import { onMounted, onUnmounted } from 'vue'

const props = defineProps({
  show: Boolean,
  imageUrl: {
    type: String,
    default: '',
  },
  title: {
    type: String,
    default: '查驗照片',
  },
  subtitle: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['close'])

function handleKeyDown(e) {
  if (e.key === 'Escape' && props.show) {
    emit('close')
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<template>
  <div
    v-if="show && imageUrl"
    class="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/80 backdrop-blur-md animate-in fade-in duration-200"
    @click.self="$emit('close')"
  >
    <div class="bg-gray-900/90 border border-white/20 rounded-3xl shadow-2xl max-w-3xl w-full p-4 sm:p-6 flex flex-col max-h-[92vh] overflow-hidden">
      <!-- 頂部資訊列 -->
      <div class="flex items-center justify-between pb-3 border-b border-gray-700/60 mb-3 flex-shrink-0">
        <div class="flex items-center space-x-2.5 min-w-0">
          <span class="text-2xl">📸</span>
          <div class="min-w-0">
            <h3 class="text-sm sm:text-base font-bold text-white truncate">
              {{ title }}
            </h3>
            <p v-if="subtitle" class="text-xs text-gray-400 truncate mt-0.5">
              {{ subtitle }}
            </p>
          </div>
        </div>

        <div class="flex items-center space-x-2 flex-shrink-0">
          <a
            :href="imageUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="px-2.5 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white text-xs font-semibold transition flex items-center space-x-1"
            title="在新分頁開啟完整原圖"
          >
            <span>🔗 原圖</span>
          </a>
          <button
            @click="$emit('close')"
            type="button"
            class="w-8 h-8 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white text-base font-bold flex items-center justify-center transition"
            title="關閉 (Esc)"
          >
            ✕
          </button>
        </div>
      </div>

      <!-- 圖片主體 -->
      <div class="flex-1 overflow-auto flex items-center justify-center bg-black/50 rounded-2xl p-2 min-h-[250px]">
        <img
          :src="imageUrl"
          :alt="title"
          class="max-h-[72vh] max-w-full rounded-xl object-contain shadow-lg"
          loading="lazy"
        />
      </div>

      <!-- 底部關閉按鈕 -->
      <div class="pt-3 flex justify-end flex-shrink-0">
        <button
          @click="$emit('close')"
          type="button"
          class="px-5 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-bold transition"
        >
          關閉預覽
        </button>
      </div>
    </div>
  </div>
</template>
