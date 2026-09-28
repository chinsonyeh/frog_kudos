<script setup>
import { ref, watch, onMounted } from 'vue'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  show: Boolean,
  members: {
    type: Array,
    default: () => [],
  },
  initialMemberId: {
    type: String,
    default: null,
  },
})

const emit = defineEmits(['close', 'adjusted', 'unlockedBadges'])
const authStore = useAuthStore()

const memberId = ref('')
const targetName = ref('社會科')
const startDate = ref('')
const endDate = ref('')
const mode = ref('OFFSET') // 'FIXED' | 'OFFSET'
const adjustValue = ref(5)
const reason = ref('')
const parentPinInput = ref('')

const loadingPreview = ref(false)
const loadingSubmit = ref(false)
const previewResult = ref(null)
const error = ref('')

onMounted(() => {
  // 預設日期區間為當月
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  startDate.value = `${y}-${m}-01`
  endDate.value = `${y}-${m}-${d}`

  if (props.initialMemberId) {
    memberId.value = props.initialMemberId
  } else if (props.members.length > 0) {
    memberId.value = props.members[0].id
  }
})

watch(() => props.initialMemberId, (newVal) => {
  if (newVal) memberId.value = newVal
})

async function runPreview() {
  if (!memberId.value) {
    error.value = '請選擇篩選對象成員'
    return
  }
  if (!targetName.value.trim()) {
    error.value = '請輸入欲調整之目標項目名稱'
    return
  }
  if (!startDate.value || !endDate.value) {
    error.value = '請設定時間區間'
    return
  }

  loadingPreview.value = true
  error.value = ''
  previewResult.value = null

  try {
    const res = await api.previewBatchAdjust({
      member_id: memberId.value,
      target_name: targetName.value.trim(),
      start_date: startDate.value,
      end_date: endDate.value,
      mode: mode.value,
      value: parseInt(adjustValue.value, 10),
    })
    previewResult.value = res
  } catch (err) {
    error.value = err.message || '試算失敗'
  } finally {
    loadingPreview.value = false
  }
}

async function submitBatchAdjust() {
  const pin = parentPinInput.value || authStore.parentPin
  if (!pin) {
    error.value = '請輸入家長 PIN 碼'
    return
  }
  if (!reason.value.trim()) {
    error.value = '請填寫批次調整原因說明'
    return
  }

  loadingSubmit.value = true
  error.value = ''

  try {
    const res = await api.executeBatchAdjust({
      member_id: memberId.value,
      target_name: targetName.value.trim(),
      start_date: startDate.value,
      end_date: endDate.value,
      mode: mode.value,
      value: parseInt(adjustValue.value, 10),
      reason: reason.value.trim(),
      parent_pin: pin,
    })

    emit('adjusted', res)
    if (res.newly_unlocked_badges && res.newly_unlocked_badges.length > 0) {
      emit('unlockedBadges', res.newly_unlocked_badges)
    }
    emit('close')
  } catch (err) {
    error.value = err.message || '批次調整執行失敗'
  } finally {
    loadingSubmit.value = false
  }
}
</script>

<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
    <div class="bg-white rounded-3xl shadow-2xl max-w-xl w-full p-6 sm:p-8 max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
        <div class="flex items-center space-x-2">
          <span class="text-2xl">🛠</span>
          <h3 class="text-lg font-bold text-gray-900">歷史積分批次統一調整工具</h3>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 text-xl font-bold">
          ✕
        </button>
      </div>

      <div class="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 mb-6">
        ℹ️ 說明：此功能將依篩選條件「統一批次修改」歷史已發放的點數紀錄並同步更新成員可用餘額與累計總額。
      </div>

      <!-- 表單設定 -->
      <div class="space-y-4 mb-6">
        <!-- 1. 成員 -->
        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            1. 篩選對象 (Member)
          </label>
          <select
            v-model="memberId"
            class="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-frog-500 font-medium text-sm transition"
          >
            <option v-for="m in members" :key="m.id" :value="m.id">
              {{ m.avatar }} {{ m.name }} (目前餘額: {{ m.current_points }} 點)
            </option>
          </select>
        </div>

        <!-- 2. 目標項目 -->
        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            2. 目標項目 (Target Name)
          </label>
          <input
            v-model="targetName"
            type="text"
            placeholder="例如: 社會科, 數學科, 整理房間"
            class="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-frog-500 font-medium text-sm transition"
          />
        </div>

        <!-- 3. 時間區間 -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              3. 起始日期
            </label>
            <input
              v-model="startDate"
              type="date"
              class="w-full px-3.5 py-2 rounded-xl border border-gray-200 bg-gray-50 text-sm font-medium focus:ring-2 focus:ring-frog-500"
            />
          </div>
          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              截止日期 (包含當天)
            </label>
            <input
              v-model="endDate"
              type="date"
              class="w-full px-3.5 py-2 rounded-xl border border-gray-200 bg-gray-50 text-sm font-medium focus:ring-2 focus:ring-frog-500"
            />
          </div>
        </div>

        <!-- 4. 調整模式 -->
        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">
            4. 調整模式 (Mode)
          </label>
          <div class="grid grid-cols-2 gap-3">
            <label
              class="flex items-center space-x-2 p-3 rounded-xl border cursor-pointer transition text-xs font-medium"
              :class="mode === 'OFFSET' ? 'border-frog-500 bg-frog-50/50 text-frog-800 font-bold' : 'border-gray-200 text-gray-600'"
            >
              <input type="radio" v-model="mode" value="OFFSET" class="text-frog-600" />
              <span>統一增減點數 (Offset)</span>
            </label>
            <label
              class="flex items-center space-x-2 p-3 rounded-xl border cursor-pointer transition text-xs font-medium"
              :class="mode === 'FIXED' ? 'border-frog-500 bg-frog-50/50 text-frog-800 font-bold' : 'border-gray-200 text-gray-600'"
            >
              <input type="radio" v-model="mode" value="FIXED" class="text-frog-600" />
              <span>設為固定點數 (Fixed)</span>
            </label>
          </div>
        </div>

        <!-- 調整數值 -->
        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            {{ mode === 'OFFSET' ? '每筆增減點數 (支援負數扣除)' : '每筆新點數' }}
          </label>
          <input
            v-model="adjustValue"
            type="number"
            class="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-frog-500 font-medium text-sm transition"
          />
        </div>

        <!-- 5. 調整原因說明 -->
        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            5. 調整原因說明 (審計備註)
          </label>
          <input
            v-model="reason"
            type="text"
            placeholder="例如: 段考加碼補發 / 規則門檻調整"
            class="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-frog-500 font-medium text-sm transition"
          />
        </div>
      </div>

      <!-- 試算影響範圍按鈕 -->
      <button
        @click="runPreview"
        :disabled="loadingPreview"
        type="button"
        class="w-full py-2.5 px-4 mb-4 rounded-xl border border-frog-400 bg-frog-50 text-frog-700 hover:bg-frog-100 font-bold text-sm transition shadow-sm"
      >
        {{ loadingPreview ? '試算中...' : '🔍 試算影響範圍 (Preview)' }}
      </button>

      <!-- 試算結果呈現 -->
      <div v-if="previewResult" class="p-4 rounded-2xl bg-gray-50 border border-gray-200 mb-6 text-sm">
        <h4 class="font-bold text-gray-800 mb-2 flex items-center justify-between">
          <span>📊 試算結果摘要：</span>
          <span class="text-xs font-mono px-2 py-0.5 rounded bg-gray-200 text-gray-700">共 {{ previewResult.affected_count }} 筆</span>
        </h4>
        <div class="grid grid-cols-3 gap-2 text-center py-2 border-y border-gray-200/60 my-2">
          <div>
            <div class="text-xs text-gray-500">原總點數</div>
            <div class="font-bold text-gray-700">{{ previewResult.original_total }} 點</div>
          </div>
          <div>
            <div class="text-xs text-gray-500">新總點數</div>
            <div class="font-bold text-frog-600">{{ previewResult.new_total }} 點</div>
          </div>
          <div>
            <div class="text-xs text-gray-500">總差額 (Δ)</div>
            <div class="font-bold font-mono" :class="previewResult.delta >= 0 ? 'text-emerald-600' : 'text-red-500'">
              {{ previewResult.delta >= 0 ? `+${previewResult.delta}` : previewResult.delta }} 點
            </div>
          </div>
        </div>

        <!-- 影響細節預覽清單 -->
        <div v-if="previewResult.items.length > 0" class="max-h-36 overflow-y-auto space-y-1.5 mt-2 pr-1">
          <div
            v-for="item in previewResult.items"
            :key="item.id"
            class="text-xs flex items-center justify-between p-2 rounded-lg bg-white border border-gray-100"
          >
            <span class="text-gray-500">{{ item.created_at.slice(0, 10) }} | {{ item.target_name }} ({{ item.condition }})</span>
            <span class="font-mono font-semibold">
              {{ item.old_points }} ➔ <span class="text-frog-600">{{ item.new_points }} 點</span>
            </span>
          </div>
        </div>
      </div>

      <!-- 錯誤提示 -->
      <p v-if="error" class="text-xs text-red-500 font-semibold mb-4 text-center">
        {{ error }}
      </p>

      <!-- 家長 PIN 碼確認 (若尚未在 Pinia 存儲) -->
      <div v-if="!authStore.parentPin" class="mb-4">
        <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
          請輸入家長 PIN 碼確認授權
        </label>
        <input
          v-model="parentPinInput"
          type="password"
          maxlength="6"
          placeholder="4 碼家長 PIN"
          class="w-full px-3.5 py-2 rounded-xl border border-gray-200 text-sm font-medium"
        />
      </div>

      <!-- 操作按鈕 -->
      <div class="flex space-x-3">
        <button
          @click="$emit('close')"
          type="button"
          class="flex-1 py-3 px-4 rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50 font-medium text-sm transition"
        >
          取消
        </button>
        <button
          @click="submitBatchAdjust"
          :disabled="loadingSubmit || !previewResult || previewResult.affected_count === 0"
          type="button"
          class="flex-1 py-3 px-4 rounded-xl bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-white font-bold text-sm transition disabled:opacity-50 shadow-md shadow-amber-200"
        >
          {{ loadingSubmit ? '執行中...' : '⚠️ 確認執行批次調整' }}
        </button>
      </div>
    </div>
  </div>
</template>
