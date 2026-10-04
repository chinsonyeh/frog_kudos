<script setup>
import { ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/services/api'

const props = defineProps({
  show: Boolean,
})
const emit = defineEmits(['close', 'unlocked'])

const authStore = useAuthStore()

// 步驟：'select_member' (選擇角色) | 'enter_pin' (輸入 PIN 碼)
const step = ref('select_member')
const members = ref([])
const selectedMember = ref(null)

const pin = ref('')
const error = ref('')
const loading = ref(false)

watch(
  () => props.show,
  async (newVal) => {
    if (newVal) {
      await initModal()
    }
  },
  { immediate: true }
)

async function initModal() {
  pin.value = ''
  error.value = ''
  loading.value = false
  try {
    const list = await api.getMembers(false)
    members.value = list || []
    if (members.value.length > 0) {
      // 若目前已有選取的成員，可預設為該成員
      step.value = 'select_member'
      selectedMember.value = null
    } else {
      // 系統無成員時，直接進入通用家長解鎖
      step.value = 'enter_pin'
      selectedMember.value = null
    }
  } catch (err) {
    console.error('取得成員失敗:', err)
    step.value = 'enter_pin'
    selectedMember.value = null
  }
}

function chooseMember(m) {
  selectedMember.value = m
  step.value = 'enter_pin'
  pin.value = ''
  error.value = ''
}

function goBackToSelectMember() {
  step.value = 'select_member'
  pin.value = ''
  error.value = ''
}

function appendDigit(digit) {
  if (pin.value.length < 4) {
    pin.value += digit
    error.value = ''
    if (pin.value.length === 4) {
      verifyAndUnlock()
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

async function verifyAndUnlock() {
  if (!pin.value || pin.value.length < 4) {
    error.value = '請輸入 4 位數 PIN 碼'
    return
  }

  loading.value = true
  error.value = ''

  try {
    let res
    if (selectedMember.value) {
      // 以特定成員 (家長或小孩) 身分驗證並簽發專屬 Session Token
      res = await api.verifyParentPin({
        member_id: selectedMember.value.id,
        pin: pin.value,
      })
      authStore.unlock(res, res.session_token || '', pin.value)
    } else {
      // 傳統通用家長驗證
      res = await api.verifyParentPin(pin.value)
      authStore.unlockParent(pin.value, res.session_token || '')
    }

    emit('unlocked')
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
  if (e.key === 'Escape') {
    emit('close')
    return
  }
  if (step.value === 'enter_pin') {
    if (e.key >= '0' && e.key <= '9') {
      appendDigit(e.key)
    } else if (e.key === 'Backspace') {
      deleteDigit()
    } else if (e.key === 'Enter') {
      verifyAndUnlock()
    }
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
      class="pin-modal-card bg-white rounded-3xl shadow-2xl max-w-sm w-full p-6 text-center animate-in fade-in zoom-in duration-200 select-none touch-manipulation relative"
      @dblclick.prevent
    >
      <!-- 【步驟 1: 選擇解鎖成員身分】 -->
      <div v-if="step === 'select_member'" class="space-y-5">
        <div class="w-16 h-16 bg-frog-100 rounded-full flex items-center justify-center mx-auto text-3xl shadow-inner">
          👥
        </div>
        <div>
          <h3 class="text-xl font-bold text-gray-800">請選擇解鎖角色身分</h3>
          <p class="text-xs text-gray-500 mt-1">點選您的身分並輸入專屬 PIN 碼以解鎖對應功能</p>
        </div>

        <div class="space-y-2.5 max-h-72 overflow-y-auto pr-1">
          <button
            v-for="m in members"
            :key="m.id"
            @click="chooseMember(m)"
            type="button"
            class="w-full p-3.5 rounded-2xl border-2 border-gray-100 hover:border-frog-400 bg-gray-50/60 hover:bg-frog-50/40 active:scale-98 transition flex items-center justify-between text-left cursor-pointer group shadow-sm"
          >
            <div class="flex items-center space-x-3">
              <div class="w-12 h-12 rounded-2xl bg-white border border-gray-100 flex items-center justify-center text-2xl shadow-sm group-hover:scale-110 transition">
                {{ m.avatar }}
              </div>
              <div>
                <div class="font-bold text-gray-800 text-base leading-tight">{{ m.name }}</div>
                <div class="text-[11px] font-semibold mt-0.5" :class="m.role === 'parent' ? 'text-amber-600' : 'text-frog-600'">
                  {{ m.role === 'parent' ? '👑 家長管理帳號' : '👦 小孩專屬帳號' }}
                </div>
              </div>
            </div>
            <div class="text-gray-400 group-hover:text-frog-600 transition font-bold text-lg pr-1">
              ➔
            </div>
          </button>
        </div>

        <div class="pt-2">
          <button
            @click="$emit('close')"
            type="button"
            class="w-full py-3 px-4 rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50 font-medium transition cursor-pointer"
          >
            取消
          </button>
        </div>
      </div>

      <!-- 【步驟 2: 輸入 PIN 碼】 -->
      <div v-else-if="step === 'enter_pin'">
        <!-- 返回選成員按鈕 -->
        <button
          v-if="members.length > 0"
          @click="goBackToSelectMember"
          type="button"
          class="absolute top-5 left-5 text-xs text-gray-500 hover:text-gray-800 flex items-center space-x-1 font-semibold transition cursor-pointer"
        >
          <span>←</span>
          <span>切換角色</span>
        </button>

        <div class="w-16 h-16 bg-frog-100 rounded-full flex items-center justify-center mx-auto mb-3 text-3xl shadow-inner">
          {{ selectedMember ? selectedMember.avatar : '🔐' }}
        </div>
        <h3 class="text-xl font-bold text-gray-800 mb-0.5">
          {{ selectedMember ? `「${selectedMember.name}」身分解鎖` : '家長安全管理鎖' }}
        </h3>
        <p class="text-xs text-gray-500 mb-5">
          {{ selectedMember?.role === 'parent'
            ? '請輸入 4 位數家長管理 PIN 碼'
            : (selectedMember ? '請輸入 4 位數個人 PIN 碼 (預設 0000)' : '請輸入 4 位數家長管理 PIN 碼')
          }}
        </p>

        <!-- PIN 碼顯示點點 -->
        <div class="flex justify-center space-x-4 mb-5 select-none">
          <div
            v-for="i in 4"
            :key="i"
            class="w-4 h-4 rounded-full border-2 transition-all duration-200"
            :class="pin.length >= i ? 'bg-frog-500 border-frog-500 scale-110' : 'border-gray-300 bg-gray-100'"
          ></div>
        </div>

        <!-- 錯誤訊息提示 -->
        <p v-if="error" class="text-xs text-red-500 font-semibold mb-3 animate-shake">
          {{ error }}
        </p>

        <!-- 數字鍵盤 (關閉連點 2 下放大 touch-action: manipulation) -->
        <div class="grid grid-cols-3 gap-2.5 mb-5 select-none touch-manipulation">
          <button
            v-for="num in [1, 2, 3, 4, 5, 6, 7, 8, 9]"
            :key="num"
            @click="appendDigit(num.toString())"
            @dblclick.prevent
            type="button"
            class="pin-keypad-btn h-13 rounded-2xl bg-gray-50 hover:bg-frog-50 active:bg-frog-100 active:scale-95 text-xl font-semibold text-gray-700 hover:text-frog-700 transition shadow-sm border border-gray-100 select-none touch-manipulation cursor-pointer"
          >
            {{ num }}
          </button>
          <button
            @click="clearPin"
            @dblclick.prevent
            type="button"
            class="pin-keypad-btn h-13 rounded-2xl bg-gray-100 hover:bg-gray-200 active:bg-gray-300 active:scale-95 text-xs font-semibold text-gray-600 transition select-none touch-manipulation cursor-pointer"
          >
            清除
          </button>
          <button
            @click="appendDigit('0')"
            @dblclick.prevent
            type="button"
            class="pin-keypad-btn h-13 rounded-2xl bg-gray-50 hover:bg-frog-50 active:bg-frog-100 active:scale-95 text-xl font-semibold text-gray-700 hover:text-frog-700 transition shadow-sm border border-gray-100 select-none touch-manipulation cursor-pointer"
          >
            0
          </button>
          <button
            @click="deleteDigit"
            @dblclick.prevent
            type="button"
            class="pin-keypad-btn h-13 rounded-2xl bg-gray-100 hover:bg-gray-200 active:bg-gray-300 active:scale-95 text-base font-semibold text-gray-600 transition select-none touch-manipulation cursor-pointer"
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
            class="flex-1 py-2.5 px-4 rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50 active:bg-gray-100 font-medium text-sm transition select-none touch-manipulation cursor-pointer"
          >
            取消
          </button>
          <button
            @click="verifyAndUnlock"
            @dblclick.prevent
            :disabled="loading || pin.length < 4"
            type="button"
            class="flex-1 py-2.5 px-4 rounded-xl bg-frog-500 hover:bg-frog-600 active:bg-frog-700 active:scale-98 text-white font-bold text-sm transition disabled:opacity-50 shadow-md shadow-frog-200 select-none touch-manipulation cursor-pointer"
          >
            {{ loading ? '驗證中...' : '解鎖確認' }}
          </button>
        </div>
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
