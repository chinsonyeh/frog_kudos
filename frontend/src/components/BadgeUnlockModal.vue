<script setup>
import { onMounted } from 'vue'
import { triggerConfetti } from '@/components/Confetti'

const props = defineProps({
  badges: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['close'])

onMounted(() => {
  triggerConfetti()
})
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-300">
    <div class="bg-white rounded-3xl shadow-2xl max-w-md w-full p-8 text-center relative overflow-hidden border-4 border-yellow-300">
      <!-- 閃爍光芒背景 -->
      <div class="absolute -top-24 -left-24 w-48 h-48 bg-yellow-100 rounded-full blur-2xl opacity-60"></div>
      <div class="absolute -bottom-24 -right-24 w-48 h-48 bg-frog-100 rounded-full blur-2xl opacity-60"></div>

      <div class="relative z-10">
        <div class="text-6xl mb-3 animate-bounce">
          🎉
        </div>
        <h2 class="text-2xl font-black text-gray-800 mb-1">
          恭喜解鎖全新里程碑勳章！
        </h2>
        <p class="text-sm text-gray-500 mb-6">
          你的堅持與努力獲得了專屬榮譽認證！
        </p>

        <!-- 勳章卡片清單 -->
        <div class="space-y-4 mb-6">
          <div
            v-for="b in badges"
            :key="b.badge_key"
            class="p-4 rounded-2xl bg-gradient-to-r from-yellow-50 to-amber-50 border border-yellow-200 flex items-center space-x-4 shadow-sm"
          >
            <div class="w-14 h-14 rounded-2xl bg-yellow-400 text-white flex items-center justify-center text-3xl shadow-md flex-shrink-0">
              {{ b.icon || '🏅' }}
            </div>
            <div class="text-left flex-1">
              <h4 class="font-bold text-gray-800 text-base flex items-center gap-1.5">
                {{ b.title }}
                <span class="text-xs bg-yellow-200 text-yellow-800 px-2 py-0.5 rounded-full font-semibold">NEW!</span>
              </h4>
              <p class="text-xs text-gray-600 mt-0.5">{{ b.description }}</p>
            </div>
          </div>
        </div>

        <button
          @click="$emit('close')"
          class="w-full py-3.5 px-6 rounded-2xl bg-gradient-to-r from-frog-500 to-emerald-600 hover:from-frog-600 hover:to-emerald-700 text-white font-bold text-base shadow-lg shadow-frog-200 transition transform hover:-translate-y-0.5 active:translate-y-0"
        >
          太棒了！收下榮譽 🌟
        </button>
      </div>
    </div>
  </div>
</template>
