<script setup>
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/services/api'

const props = defineProps({
  show: Boolean,
})
const emit = defineEmits(['close', 'unlocked'])

const authStore = useAuthStore()
const pin = ref('')
const error = ref('')
const loading = ref(false)

function appendDigit(digit) {
  if (pin.value.length < 6) {
    pin.value += digit
    error.value = ''
  }
}

function deleteDigit() {
  pin.value = pin.value.slice(0, -1)
  error.value = ''
}

function clearPin() {
  pin.value = ''
  error.value = ''
}

async function verifyAndUnlock() {
  if (!pin.value) {
    error.value = '請輸入家長 PIN 碼'
    return
  }

  loading.value = true
  error.value = ''

  try {
    // 透過觸發系統設定驗證 PIN 碼
    authStore.unlockParent(pin.value)
    // 試探性發起需要 PIN 的輕量請求檢驗 PIN 碼有效性
    await api.getBackups()
    emit('unlocked')
    emit('close')
    clearPin()
  } catch (err) {
    authStore.lockParent()
    error.value = 'PIN 碼錯誤，請重新輸入'
    pin.value = ''
  } finally {
    loading.value = false
  }
}

function handleKeydown(e) {
  if (e.key >= '0' && e.key <= '9') {
    appendDigit(e.key)
  } else if (e.key === 'Backspace') {
    deleteDigit()
  } else if (e.key === 'Enter') {
    verifyAndUnlock()
  } else if (e.key === 'Escape') {
    emit('close')
  }
}
</script>

<template>
  <div
    v-if="show"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
    @keydown="handleKeydown"
    tabindex="0"
  >
    <div class="bg-white rounded-3xl shadow-2xl max-w-sm w-full p-6 text-center animate-in fade-in zoom-in duration-200">
      <div class="w-16 h-16 bg-frog-100 rounded-full flex items-center justify-center mx-auto mb-4 text-3xl shadow-inner">
        🔐
      </div>
      <h3 class="text-xl font-bold text-gray-800 mb-1">家長安全管理鎖</h3>
      <p class="text-sm text-gray-500 mb-6">請輸入 4 位數家長管理 PIN 碼以解鎖進階功能</p>

      <!-- PIN 碼顯示點點 -->
      <div class="flex justify-center space-x-4 mb-6">
        <div
          v-for="i in 4"
          :key="i"
          class="w-4 h-4 rounded-full border-2 transition-all duration-200"
          :class="pin.length >= i ? 'bg-frog-500 border-frog-500 scale-110' : 'border-gray-300 bg-gray-100'"
        ></div>
      </div>

      <!-- 錯誤訊息提示 -->
      <p v-if="error" class="text-sm text-red-500 font-medium mb-4 animate-shake">
        {{ error }}
      </p>

      <!-- 數字鍵盤 -->
      <div class="grid grid-cols-3 gap-3 mb-6">
        <button
          v-for="num in [1, 2, 3, 4, 5, 6, 7, 8, 9]"
          :key="num"
          @click="appendDigit(num.toString())"
          type="button"
          class="h-14 rounded-2xl bg-gray-50 hover:bg-frog-50 active:bg-frog-100 text-xl font-semibold text-gray-700 hover:text-frog-700 transition shadow-sm border border-gray-100"
        >
          {{ num }}
        </button>
        <button
          @click="clearPin"
          type="button"
          class="h-14 rounded-2xl bg-gray-100 hover:bg-gray-200 text-sm font-semibold text-gray-600 transition"
        >
          清除
        </button>
        <button
          @click="appendDigit('0')"
          type="button"
          class="h-14 rounded-2xl bg-gray-50 hover:bg-frog-50 active:bg-frog-100 text-xl font-semibold text-gray-700 hover:text-frog-700 transition shadow-sm border border-gray-100"
        >
          0
        </button>
        <button
          @click="deleteDigit"
          type="button"
          class="h-14 rounded-2xl bg-gray-100 hover:bg-gray-200 text-base font-semibold text-gray-600 transition"
        >
          ⌫
        </button>
      </div>

      <!-- 操作按鈕 -->
      <div class="flex space-x-3">
        <button
          @click="$emit('close')"
          type="button"
          class="flex-1 py-3 px-4 rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50 font-medium transition"
        >
          取消
        </button>
        <button
          @click="verifyAndUnlock"
          :disabled="loading || pin.length < 4"
          type="button"
          class="flex-1 py-3 px-4 rounded-xl bg-frog-500 hover:bg-frog-600 active:bg-frog-700 text-white font-bold transition disabled:opacity-50 shadow-md shadow-frog-200"
        >
          {{ loading ? '驗證中...' : '解鎖確認' }}
        </button>
      </div>
    </div>
  </div>
</template>
