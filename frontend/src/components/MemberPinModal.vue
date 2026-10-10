<script setup>
import { ref, watch } from 'vue'
import { api } from '@/services/api'
import MemberAvatar from '@/components/MemberAvatar.vue'

const props = defineProps({
  show: Boolean,
  member: Object,
  title: {
    type: String,
    default: '輸入個人 PIN 碼',
  },
  description: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['close', 'confirmed'])

const pin = ref('')
const error = ref('')
const loading = ref(false)

watch(() => props.show, (newVal) => {
  if (newVal) {
    pin.value = ''
    error.value = ''
    loading.value = false
  }
})

function appendDigit(digit) {
  if (pin.value.length < 4) {
    pin.value += digit
    error.value = ''
    if (pin.value.length === 4) {
      verifyAndConfirm()
    }
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

async function verifyAndConfirm() {
  if (!props.member || !props.member.id) {
    error.value = '尚未選擇對象成員'
    return
  }
  if (!pin.value || pin.value.length < 4) {
    error.value = '請輸入 4 位數 PIN 碼'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const res = await api.verifyMemberPin(props.member.id, pin.value)
    emit('confirmed', { pin: pin.value, role: res.role })
    emit('close')
    clearPin()
  } catch (err) {
    error.value = err.message || 'PIN 碼錯誤，請重新輸入'
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
    verifyAndConfirm()
  } else if (e.key === 'Escape') {
    emit('close')
  }
}
</script>

<template>
  <div
    v-if="show"
    class="pin-modal-backdrop fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm select-none"
    @keydown="handleKeydown"
    @dblclick.prevent
    tabindex="0"
  >
    <div
      class="pin-modal-card bg-white rounded-3xl shadow-2xl max-w-sm w-full p-6 text-center animate-in fade-in zoom-in duration-200 select-none touch-manipulation"
      @dblclick.prevent
    >
      <!-- 頭像與圖示 -->
      <div class="relative w-16 h-16 mx-auto mb-3">
        <MemberAvatar :avatar="member?.avatar" :name="member?.name" size="xl" class="mx-auto shadow-inner" />
        <div class="absolute -bottom-1 -right-1 w-6 h-6 bg-white rounded-full shadow-sm flex items-center justify-center text-xs border border-gray-100">
          🔑
        </div>
      </div>

      <h3 class="text-xl font-bold text-gray-800 mb-1">
        {{ title || `驗證「${member?.name}」身分` }}
      </h3>
      <p class="text-xs text-gray-500 mb-6">
        {{ description || `請輸入「${member?.name}」的 4 位數 PIN 碼以確認操作` }}
      </p>

      <!-- PIN 碼顯示點點 -->
      <div class="flex justify-center space-x-4 mb-6 select-none">
        <div
          v-for="i in 4"
          :key="i"
          class="w-4 h-4 rounded-full border-2 transition-all duration-200"
          :class="pin.length >= i ? 'bg-frog-500 border-frog-500 scale-110' : 'border-gray-300 bg-gray-100'"
        ></div>
      </div>

      <!-- 錯誤訊息提示 -->
      <p v-if="error" class="text-xs text-red-500 font-bold mb-4 animate-shake">
        {{ error }}
      </p>

      <!-- 數字鍵盤 (關閉連點 2 下放大 touch-action: manipulation) -->
      <div class="grid grid-cols-3 gap-3 mb-6 select-none touch-manipulation">
        <button
          v-for="num in [1, 2, 3, 4, 5, 6, 7, 8, 9]"
          :key="num"
          @click="appendDigit(num.toString())"
          @dblclick.prevent
          type="button"
          class="pin-keypad-btn h-14 rounded-2xl bg-gray-50 hover:bg-frog-50 active:bg-frog-100 active:scale-95 text-xl font-semibold text-gray-700 hover:text-frog-700 transition shadow-sm border border-gray-100 select-none touch-manipulation cursor-pointer"
        >
          {{ num }}
        </button>
        <button
          @click="clearPin"
          @dblclick.prevent
          type="button"
          class="pin-keypad-btn h-14 rounded-2xl bg-gray-100 hover:bg-gray-200 active:bg-gray-300 active:scale-95 text-sm font-semibold text-gray-600 transition select-none touch-manipulation cursor-pointer"
        >
          清除
        </button>
        <button
          @click="appendDigit('0')"
          @dblclick.prevent
          type="button"
          class="pin-keypad-btn h-14 rounded-2xl bg-gray-50 hover:bg-frog-50 active:bg-frog-100 active:scale-95 text-xl font-semibold text-gray-700 hover:text-frog-700 transition shadow-sm border border-gray-100 select-none touch-manipulation cursor-pointer"
        >
          0
        </button>
        <button
          @click="deleteDigit"
          @dblclick.prevent
          type="button"
          class="pin-keypad-btn h-14 rounded-2xl bg-gray-100 hover:bg-gray-200 active:bg-gray-300 active:scale-95 text-base font-semibold text-gray-600 transition select-none touch-manipulation cursor-pointer"
        >
          ⌫
        </button>
      </div>

      <!-- 操作按鈕 -->
      <div class="flex space-x-3 select-none touch-manipulation">
        <button
          @click="$emit('close')"
          @dblclick.prevent
          type="button"
          class="flex-1 py-3 px-4 rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50 active:bg-gray-100 font-medium text-xs transition select-none touch-manipulation cursor-pointer"
        >
          取消
        </button>
        <button
          @click="verifyAndConfirm"
          @dblclick.prevent
          :disabled="loading || pin.length < 4"
          type="button"
          class="flex-1 py-3 px-4 rounded-xl bg-frog-500 hover:bg-frog-600 active:bg-frog-700 active:scale-98 text-white font-bold text-xs transition disabled:opacity-50 shadow-md shadow-frog-200 select-none touch-manipulation cursor-pointer"
        >
          {{ loading ? '驗證中...' : '確認' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pin-modal-backdrop {
  touch-action: none;
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  user-select: none;
}

.pin-modal-card,
.pin-modal-card * {
  touch-action: manipulation !important;
  -webkit-touch-callout: none !important;
  -webkit-user-select: none !important;
  user-select: none !important;
  -webkit-tap-highlight-color: transparent !important;
}

.pin-keypad-btn {
  touch-action: manipulation !important;
  -webkit-touch-callout: none !important;
  -webkit-user-select: none !important;
  user-select: none !important;
  -webkit-tap-highlight-color: transparent !important;
}
</style>
