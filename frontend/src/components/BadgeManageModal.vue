<script setup>
import { ref, watch, computed } from 'vue'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  show: Boolean,
  currentMember: {
    type: Object,
    default: null,
  },
})
const emit = defineEmits(['close', 'badgesUpdated'])

const authStore = useAuthStore()

const viewMode = ref('list') // 'list' | 'form'
const formMode = ref('create') // 'create' | 'edit'
const badgesList = ref([])
const loading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

// 表單欄位
const editingBadgeId = ref(null)
const badgeKey = ref('')
const title = ref('')
const description = ref('')
const icon = ref('🏅')
const conditionType = ref('TOTAL_POINTS')
const targetValue = ref(5000)
const sortOrder = ref(10)
const isActive = ref(true)
const parentPinInput = ref('')

const commonIcons = [
  '🌟', '🏆', '🧹', '👑', '💎', '🎖️', '🚀', '⚡',
  '🔥', '🔮', '🌈', '🌠', '🛡️', '🔱', '🪐', '📖',
  '🏃', '🎨', '🎯', '🥇', '💪', '🌱', '☀️', '💯'
]

const conditionOptions = [
  { value: 'TOTAL_POINTS', label: '🪙 累計獲得總點數 (Milestone Points)' },
  { value: 'PERFECT_SCORE_COUNT', label: '🏆 科目滿分次數 (Perfect Scores)' },
  { value: 'CHORE_POINTS', label: '🧹 家事或生活常規點數 (Chores)' },
  { value: 'CUSTOM', label: '✨ 自訂條件 / 家長手動頒發 (Custom)' },
]

watch(() => props.show, (newVal) => {
  if (newVal) {
    loadBadges()
    viewMode.value = 'list'
    errorMsg.value = ''
    successMsg.value = ''
  }
})

async function loadBadges() {
  loading.value = true
  try {
    badgesList.value = await api.getBadges(true)
  } catch (err) {
    errorMsg.value = err.message || '載入勳章失敗'
  } finally {
    loading.value = false
  }
}

function openCreateForm() {
  formMode.value = 'create'
  editingBadgeId.value = null
  badgeKey.value = ''
  title.value = ''
  description.value = ''
  icon.value = '🏅'
  conditionType.value = 'TOTAL_POINTS'
  targetValue.value = 5000
  sortOrder.value = (badgesList.value.length + 1) * 5
  isActive.value = true
  parentPinInput.value = ''
  errorMsg.value = ''
  viewMode.value = 'form'
}

function openEditForm(badge) {
  formMode.value = 'edit'
  editingBadgeId.value = badge.id
  badgeKey.value = badge.badge_key
  title.value = badge.title
  description.value = badge.description
  icon.value = badge.icon || '🏅'
  conditionType.value = badge.condition_type || 'TOTAL_POINTS'
  targetValue.value = badge.target_value
  sortOrder.value = badge.sort_order ?? 0
  isActive.value = badge.is_active
  parentPinInput.value = ''
  errorMsg.value = ''
  viewMode.value = 'form'
}

// 自動根據條件類型與門檻輔助填寫
function onConditionChange() {
  if (conditionType.value === 'TOTAL_POINTS' && !title.value) {
    title.value = `里程碑蛙`
    description.value = `累計獲得 ${Number(targetValue.value).toLocaleString()} 點`
  } else if (conditionType.value === 'PERFECT_SCORE_COUNT' && !title.value) {
    title.value = `滿分高手蛙`
    description.value = `科目滿分達 ${targetValue.value} 次`
  } else if (conditionType.value === 'CHORE_POINTS' && !title.value) {
    title.value = `家事達人蛙`
    description.value = `生活常規或家事協助累計獲得 ${targetValue.value} 點`
  }
}

function onTargetChange() {
  if (conditionType.value === 'TOTAL_POINTS' && (!description.value || description.value.startsWith('累計獲得'))) {
    description.value = `累計獲得 ${Number(targetValue.value).toLocaleString()} 點`
  }
}

async function handleSave() {
  if (!title.value.trim()) {
    errorMsg.value = '請輸入勳章名稱'
    return
  }
  if (!description.value.trim()) {
    errorMsg.value = '請輸入勳章說明'
    return
  }

  const pin = parentPinInput.value || authStore.parentPin
  if (!pin) {
    errorMsg.value = '請輸入家長 PIN 碼'
    return
  }

  loading.value = true
  errorMsg.value = ''

  try {
    if (formMode.value === 'create') {
      await api.createBadge({
        badge_key: badgeKey.value.trim() || null,
        title: title.value.trim(),
        description: description.value.trim(),
        icon: icon.value.trim() || '🏅',
        condition_type: conditionType.value,
        target_value: parseInt(targetValue.value, 10),
        sort_order: parseInt(sortOrder.value, 10) || 0,
        is_active: isActive.value,
        parent_pin: pin,
      })
      successMsg.value = `🎉 已成功新增勳章「${title.value}」！`
    } else {
      await api.updateBadge(editingBadgeId.value, {
        title: title.value.trim(),
        description: description.value.trim(),
        icon: icon.value.trim() || '🏅',
        condition_type: conditionType.value,
        target_value: parseInt(targetValue.value, 10),
        sort_order: parseInt(sortOrder.value, 10) || 0,
        is_active: isActive.value,
        parent_pin: pin,
      })
      successMsg.value = `✅ 已成功更新勳章「${title.value}」！`
    }

    emit('badgesUpdated')
    await loadBadges()
    viewMode.value = 'list'
    setTimeout(() => { successMsg.value = '' }, 3000)
  } catch (err) {
    errorMsg.value = err.message || '儲存失敗'
  } finally {
    loading.value = false
  }
}

async function handleDelete(badge) {
  if (!confirm(`確定要刪除或停用「${badge.title}」勳章嗎？`)) {
    return
  }

  const pin = authStore.parentPin
  loading.value = true
  errorMsg.value = ''

  try {
    const res = await api.deleteBadge(badge.id, pin)
    successMsg.value = res.message || '操作成功'
    emit('badgesUpdated')
    await loadBadges()
    setTimeout(() => { successMsg.value = '' }, 3000)
  } catch (err) {
    errorMsg.value = err.message || '刪除失敗'
  } finally {
    loading.value = false
  }
}

async function handleToggleMember(badge) {
  if (!props.currentMember) return
  const pin = authStore.parentPin
  try {
    const res = await api.toggleMemberBadge(badge.badge_key, props.currentMember.id, null, pin)
    successMsg.value = res.message
    emit('badgesUpdated')
    setTimeout(() => { successMsg.value = '' }, 3000)
  } catch (err) {
    errorMsg.value = err.message || '切換失敗'
  }
}
</script>

<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
    <div class="bg-white rounded-3xl shadow-2xl max-w-2xl w-full p-6 sm:p-8 max-h-[90vh] overflow-y-auto">
      <!-- 頂部標題與返回/關閉 -->
      <div class="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
        <div class="flex items-center space-x-2">
          <button
            v-if="viewMode === 'form'"
            @click="viewMode = 'list'"
            class="text-gray-400 hover:text-gray-700 font-bold mr-1"
          >
            ←
          </button>
          <span class="text-2xl">🎖️</span>
          <div>
            <h3 class="text-lg font-bold text-gray-900">
              {{ viewMode === 'form' ? (formMode === 'create' ? '新增成就勳章與里程碑' : '編輯成就勳章') : '榮譽成就勳章牆管理' }}
            </h3>
            <p class="text-xs text-gray-400">
              自訂各項點數里程碑 (5,000 ~ 100,000 點) 及特殊榮譽條件
            </p>
          </div>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 text-xl font-bold">
          ✕
        </button>
      </div>

      <!-- 成功提示 -->
      <div v-if="successMsg" class="mb-4 p-3 bg-emerald-50 text-emerald-700 text-xs font-bold rounded-2xl border border-emerald-200">
        {{ successMsg }}
      </div>

      <!-- 錯誤提示 -->
      <div v-if="errorMsg" class="mb-4 p-3 bg-red-50 text-red-600 text-xs font-bold rounded-2xl border border-red-200">
        {{ errorMsg }}
      </div>

      <!-- ================= 模式 1：清單瀏覽 ================= -->
      <div v-if="viewMode === 'list'" class="space-y-4">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-gray-500 uppercase tracking-wider">
            共 {{ badgesList.length }} 個成就勳章
          </span>
          <button
            @click="openCreateForm"
            class="px-3.5 py-1.5 rounded-xl bg-frog-500 hover:bg-frog-600 text-white text-xs font-bold shadow-sm shadow-frog-200 transition flex items-center space-x-1"
          >
            <span>+ 新增勳章 / 里程碑</span>
          </button>
        </div>

        <div v-if="loading && badgesList.length === 0" class="p-8 text-center text-gray-400 text-sm">
          載入中...
        </div>

        <div v-else class="space-y-2.5">
          <div
            v-for="b in badgesList"
            :key="b.id"
            class="p-3.5 rounded-2xl border transition-all flex items-center justify-between"
            :class="b.is_active ? 'bg-white border-gray-100 hover:border-frog-200 shadow-sm' : 'bg-gray-50/60 border-gray-100 opacity-60'"
          >
            <!-- 左側 Icon 與名稱 -->
            <div class="flex items-center space-x-3 min-w-0">
              <div class="w-12 h-12 rounded-2xl bg-amber-50 border border-amber-200/60 flex items-center justify-center text-2xl flex-shrink-0 shadow-sm">
                {{ b.icon }}
              </div>
              <div class="min-w-0">
                <div class="flex items-center space-x-2">
                  <h4 class="font-bold text-gray-900 text-sm truncate">{{ b.title }}</h4>
                  <span
                    v-if="!b.is_active"
                    class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-gray-200 text-gray-600"
                  >
                    已停用
                  </span>
                  <span
                    class="px-2 py-0.5 rounded-full text-[10px] font-bold"
                    :class="b.condition_type === 'TOTAL_POINTS' ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800'"
                  >
                    {{ b.condition_type === 'TOTAL_POINTS' ? `🪙 ${Number(b.target_value).toLocaleString()} 點` : `${b.target_value} 次/點` }}
                  </span>
                </div>
                <p class="text-xs text-gray-500 truncate mt-0.5">{{ b.description }}</p>
              </div>
            </div>

            <!-- 右側操作按鈕 -->
            <div class="flex items-center space-x-1.5 flex-shrink-0">
              <button
                @click="openEditForm(b)"
                class="px-2.5 py-1.5 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold transition"
                title="編輯勳章"
              >
                ✏️ 編輯
              </button>
              <button
                @click="handleDelete(b)"
                class="px-2.5 py-1.5 rounded-xl bg-red-50 hover:bg-red-100 text-red-600 text-xs font-semibold transition"
                title="刪除或停用勳章"
              >
                🗑️
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- ================= 模式 2：新增 / 編輯表單 ================= -->
      <div v-else class="space-y-4">
        <!-- 勳章圖示 Emoji -->
        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            勳章圖示 (點選常用或直接自訂 Emoji)
          </label>
          <div class="flex items-center space-x-3 mb-2">
            <div class="w-14 h-14 rounded-2xl bg-amber-50 border-2 border-amber-300 flex items-center justify-center text-3xl shadow-sm">
              {{ icon }}
            </div>
            <input
              v-model="icon"
              type="text"
              maxlength="10"
              class="w-24 px-3 py-2 rounded-xl border border-gray-200 text-center font-bold text-lg focus:ring-2 focus:ring-frog-500"
              placeholder="圖示"
            />
          </div>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="e in commonIcons"
              :key="e"
              @click="icon = e"
              type="button"
              class="w-8 h-8 rounded-xl border text-base flex items-center justify-center hover:scale-110 transition"
              :class="icon === e ? 'border-amber-400 bg-amber-50 shadow-sm' : 'border-gray-200 bg-gray-50'"
            >
              {{ e }}
            </button>
          </div>
        </div>

        <!-- 條件類型與門檻數值 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              達成條件類型
            </label>
            <select
              v-model="conditionType"
              @change="onConditionChange"
              class="w-full px-4 py-3 rounded-2xl border border-gray-200 bg-gray-50 font-bold text-sm focus:bg-white focus:ring-2 focus:ring-frog-500 cursor-pointer"
            >
              <option v-for="opt in conditionOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              目標門檻數值 (點數或次數)
            </label>
            <input
              v-model="targetValue"
              @input="onTargetChange"
              type="number"
              min="1"
              step="1"
              placeholder="例如: 5000, 10000, 50000"
              class="w-full px-4 py-3 rounded-2xl border border-gray-200 bg-gray-50 font-mono font-bold text-sm focus:bg-white focus:ring-2 focus:ring-frog-500"
            />
          </div>
        </div>

        <!-- 勳章名稱與說明 -->
        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            勳章名稱
          </label>
          <input
            v-model="title"
            type="text"
            placeholder="例如: 五千非凡蛙、十萬不朽蛙、晨讀小達人"
            class="w-full px-4 py-3 rounded-2xl border border-gray-200 bg-gray-50 font-bold text-sm focus:bg-white focus:ring-2 focus:ring-frog-500"
          />
        </div>

        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            勳章達成說明
          </label>
          <input
            v-model="description"
            type="text"
            placeholder="例如: 累計獲得 5,000 點"
            class="w-full px-4 py-3 rounded-2xl border border-gray-200 bg-gray-50 font-medium text-sm focus:bg-white focus:ring-2 focus:ring-frog-500"
          />
        </div>

        <!-- 排序權重與啟用狀態 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              排序權重 (越小越靠前)
            </label>
            <input
              v-model="sortOrder"
              type="number"
              class="w-full px-4 py-3 rounded-2xl border border-gray-200 bg-gray-50 font-mono font-medium text-sm focus:bg-white focus:ring-2 focus:ring-frog-500"
            />
          </div>

          <div class="flex items-center space-x-3 pt-6">
            <input
              v-model="isActive"
              id="badge-active"
              type="checkbox"
              class="w-5 h-5 rounded-lg text-frog-600 focus:ring-frog-500 cursor-pointer"
            />
            <label for="badge-active" class="text-sm font-bold text-gray-700 cursor-pointer">
              啟用此成就勳章
            </label>
          </div>
        </div>

        <!-- 家長 PIN 碼確認 (若未暫存) -->
        <div v-if="!authStore.parentPin">
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            家長安全鎖 PIN 碼
          </label>
          <input
            v-model="parentPinInput"
            type="password"
            maxlength="4"
            placeholder="請輸入 4 位數 PIN 碼"
            class="w-full px-4 py-3 rounded-2xl border border-gray-200 bg-gray-50 font-mono font-bold text-center tracking-widest text-base focus:bg-white focus:ring-2 focus:ring-frog-500"
          />
        </div>

        <!-- 按鈕操作列 -->
        <div class="flex space-x-3 pt-4 border-t border-gray-100">
          <button
            @click="viewMode = 'list'"
            type="button"
            class="flex-1 py-3.5 rounded-2xl bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold text-sm transition"
          >
            取消
          </button>
          <button
            @click="handleSave"
            :disabled="loading"
            type="button"
            class="flex-1 py-3.5 rounded-2xl bg-gradient-to-r from-frog-500 to-emerald-600 hover:from-frog-600 hover:to-emerald-700 text-white font-bold text-sm shadow-lg shadow-frog-200 transition disabled:opacity-50"
          >
            {{ loading ? '處理中...' : (formMode === 'create' ? '確認新增勳章' : '儲存變更') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
