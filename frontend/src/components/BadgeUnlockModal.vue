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
          恭喜達成榮譽里程碑成就！
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
              <div class="flex items-center flex-wrap gap-1.5 mb-0.5">
                <h4 class="font-bold text-gray-800 text-base">
                  {{ b.title }}
                </h4>
                <span
                  class="text-xs px-2 py-0.5 rounded-full font-semibold"
                  :class="b.unlocked_count > 1 ? 'bg-purple-100 text-purple-800' : 'bg-yellow-200 text-yellow-800'"
                >
                  {{ b.unlocked_count > 1 ? `第 ${b.unlocked_count} 次達成！` : 'NEW!' }}
                </span>
                <span
                  v-if="b.reward_points > 0"
                  class="text-xs bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-bold flex items-center gap-1 shadow-sm"
                >
                  🎁 +{{ b.reward_points }} 點
                </span>
              </div>
              <p class="text-xs text-gray-600">{{ b.description }}</p>
              <p v-if="b.reward_points > 0" class="text-xs font-bold text-emerald-600 mt-1 flex items-center gap-1">
                <span>🪙 獲得特別獎勵點數已自動記入錢包！</span>
              </p>
              <p v-if="b.is_repeatable" class="text-[11px] font-semibold text-purple-700 mt-0.5 flex items-center gap-1">
                <span>🔄 本成就已重設，可繼續累積邁向下一次達成！</span>
              </p>
            </div>
          </div>
        </div>

        <button
          @click="$emit('close')"
          class="w-full py-3.5 px-6 rounded-2xl bg-gradient-to-r from-frog-500 to-frog-600 hover:from-frog-600 hover:to-frog-700 text-white font-bold text-base shadow-lg shadow-frog-200 transition transform hover:-translate-y-0.5 active:translate-y-0"
        >
          太棒了！收下榮譽 🌟
        </button>
      </div>
    </div>
  </div>
</template>
