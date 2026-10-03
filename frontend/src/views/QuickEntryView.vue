<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { triggerConfetti } from '@/components/Confetti'
import BadgeUnlockModal from '@/components/BadgeUnlockModal.vue'
import MemberPinModal from '@/components/MemberPinModal.vue'

const authStore = useAuthStore()

const showMemberPinModal = ref(false)
const pendingKudosData = ref(null)

const members = ref([])
const selectedMember = ref(null)
const mode = ref('RULE') // 'RULE' | 'CUSTOM'

// 監聽全域成員異動事件，自動重新整理成員名單
watch(() => authStore.memberRefreshKey, () => {
  loadMembers()
})

// 模式 A 規則選單欄位
const availableRules = ref([])
const selectedRuleId = ref('')
const targetName = ref('')
const conditionValue = ref('')
const previewResult = ref(null)
const previewLoading = ref(false)
const adjustedPoints = ref(null)

const memberCustomRules = computed(() =>
  availableRules.value.filter(r => r.member_id === selectedMember.value?.id)
)
const globalRules = computed(() =>
  availableRules.value.filter(r => !r.member_id)
)

// 模式 B 欄位
const customTitle = ref('')
const customPoints = ref(20)

// 備註與登記人
const note = ref('')
const submitting = ref(false)
const toastMsg = ref('')
const errorMsg = ref('')
const unlockedBadges = ref([])
const showBadgeModal = ref(false)

let debounceTimer = null

onMounted(async () => {
  await loadMembers()
})

async function loadMembers() {
  try {
    members.value = await api.getMembers(false)
    if (members.value.length > 0) {
      if (authStore.selectedMemberId) {
        selectedMember.value = members.value.find(m => m.id === authStore.selectedMemberId) || members.value[0]
      } else {
        selectedMember.value = members.value[0]
        authStore.setSelectedMemberId(selectedMember.value.id)
      }
      await loadRulesForMember()
    }
  } catch (err) {
    console.error('載入成員失敗', err)
  }
}

watch(() => authStore.unlockedMemberId, (newId) => {
  if (authStore.isChild && newId && members.value.length > 0) {
    const target = members.value.find(m => m.id === newId)
    if (target) {
      selectMember(target)
    }
  }
})

async function selectMember(m) {
  if (authStore.isChild && m.id !== authStore.unlockedMemberId) {
    errorMsg.value = `目前以「${authStore.unlockedMember?.name}」身分解鎖，不可切換幫其他成員登記！`
    return
  }
  selectedMember.value = m
  authStore.setSelectedMemberId(m.id)
  await loadRulesForMember()
}

async function loadRulesForMember() {
  if (!selectedMember.value) {
    availableRules.value = []
    selectedRuleId.value = ''
    return
  }
  try {
    const list = await api.getRules(selectedMember.value.id, true)
    availableRules.value = list
    if (list.length > 0) {
      // 預設選取第一條可用規則
      selectRule(list[0])
    } else {
      selectedRuleId.value = ''
      targetName.value = ''
      conditionValue.value = ''
      adjustedPoints.value = 0
      previewResult.value = null
    }
  } catch (err) {
    console.error('載入成員規則失敗', err)
  }
}

function selectRule(rule) {
  if (!rule) return
  selectedRuleId.value = rule.id
  targetName.value = rule.target_name
  conditionValue.value = rule.condition_value
  adjustedPoints.value = rule.reward_points
  previewResult.value = {
    matched: true,
    suggested_points: rule.reward_points,
    rule_id: rule.id,
    rule_name: `${rule.target_name} (${rule.condition_value}) - ${rule.description || ''}`.trim().replace(/ -$/, ''),
  }
}

function onRuleSelectChange() {
  const rule = availableRules.value.find(r => r.id === selectedRuleId.value)
  if (rule) {
    selectRule(rule)
  }
}

function triggerPreviewDebounced() {
  if (mode.value !== 'RULE') return
  if (debounceTimer) clearTimeout(debounceTimer)

  debounceTimer = setTimeout(async () => {
    if (!selectedMember.value || !targetName.value.trim()) {
      previewResult.value = null
      return
    }

    previewLoading.value = true
    try {
      const res = await api.previewKudos({
        member_id: selectedMember.value.id,
        target_name: targetName.value.trim(),
        condition_value: conditionValue.value ? conditionValue.value.trim() : null,
      })
      previewResult.value = res
      adjustedPoints.value = res.suggested_points
    } catch {
      previewResult.value = null
    } finally {
      previewLoading.value = false
    }
  }, 300)
}

watch([conditionValue], () => {
  // 僅當手動微調 conditionValue 時觸發重新比對
  triggerPreviewDebounced()
})

async function handleSubmit() {
  if (!selectedMember.value) {
    errorMsg.value = '請選擇登記對象'
    return
  }

  errorMsg.value = ''

  let pointsToAward = 0
  let finalTarget = ''
  let finalCondition = '自訂'
  let ruleId = null

  if (mode.value === 'RULE') {
    if (!targetName.value.trim()) {
      errorMsg.value = '請填寫目標項目'
      return
    }
    finalTarget = targetName.value.trim()
    finalCondition = conditionValue.value ? conditionValue.value.trim() : '自訂'
    pointsToAward = adjustedPoints.value !== null ? adjustedPoints.value : (previewResult.value ? previewResult.value.suggested_points : 0)
    ruleId = selectedRuleId.value || previewResult.value?.rule_id || null
  } else {
    if (!customTitle.value.trim()) {
      errorMsg.value = '請填寫自訂事項名稱'
      return
    }
    finalTarget = customTitle.value.trim()
    pointsToAward = parseInt(customPoints.value, 10)
  }

  const payload = {
    member_id: selectedMember.value.id,
    rule_id: ruleId,
    target_name: finalTarget,
    condition_value: finalCondition,
    points_awarded: pointsToAward,
    note: note.value.trim() || null,
  }

  // 1. 小孩解鎖模式：直接以獨立會話發送 (後端驗證 Session Token)
  if (authStore.isChild) {
    if (pointsToAward <= 0) {
      errorMsg.value = '小孩僅能申請增加自身點數，不可自訂扣點'
      return
    }
    if (selectedMember.value.id !== authStore.unlockedMemberId) {
      errorMsg.value = '您僅能為自己的帳號申請點數'
      return
    }
    await executeKudosSubmit({
      ...payload,
      recorded_by: authStore.unlockedMember?.name || 'Child',
    })
    return
  }

  // 2. 未解鎖訪客模式：點數必須 > 0，並彈出 PIN 碼鍵盤驗證
  if (!authStore.isUnlocked) {
    if (pointsToAward <= 0) {
      errorMsg.value = '未解鎖狀態僅能申請增加自身點數，扣點需家長安全鎖'
      return
    }
    pendingKudosData.value = payload
    showMemberPinModal.value = true
    return
  }

  // 3. 家長模式：直接以家長 PIN / Session 發送
  await executeKudosSubmit({
    ...payload,
    parent_pin: authStore.parentPin,
    recorded_by: 'Parent',
  })
}

async function onMemberPinConfirmed({ pin }) {
  if (!pendingKudosData.value) return
  await executeKudosSubmit({
    ...pendingKudosData.value,
    pin: pin,
    recorded_by: selectedMember.value?.name || 'Child',
  })
}

async function executeKudosSubmit(data) {
  submitting.value = true
  errorMsg.value = ''

  try {
    const res = await api.recordKudos(data)

    // 成功慶祝動效
    if (data.points_awarded > 0) {
      triggerConfetti()
    }

    toastMsg.value = `🎉 已成功為 ${selectedMember.value.name} ${data.points_awarded >= 0 ? `增加 ${data.points_awarded}` : `扣除 ${-data.points_awarded}`} 點！`
    setTimeout(() => { toastMsg.value = '' }, 4000)

    // 清理輸入
    note.value = ''
    if (mode.value === 'CUSTOM') {
      customTitle.value = ''
    }
    pendingKudosData.value = null

    // 檢查是否有新解鎖勳章
    if (res.newly_unlocked_badges && res.newly_unlocked_badges.length > 0) {
      unlockedBadges.value = res.newly_unlocked_badges
      showBadgeModal.value = true
    }

    // 重新載入成員餘額
    await loadMembers()
  } catch (err) {
    errorMsg.value = err.message || '登記點數失敗'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="max-w-3xl mx-auto space-y-6">
    <!-- 成員 PIN 碼驗證彈窗 -->
    <MemberPinModal
      :show="showMemberPinModal"
      :member="selectedMember"
      action-title="點數申請確認"
      :description="`請輸入「${selectedMember?.name}」的 4 位數 PIN 碼以核准點數申請`"
      @close="showMemberPinModal = false"
      @confirmed="onMemberPinConfirmed"
    />
    <!-- 成就解鎖慶祝彈窗 -->
    <BadgeUnlockModal
      v-if="showBadgeModal"
      :badges="unlockedBadges"
      @close="showBadgeModal = false"
    />

    <!-- Toast 成功通知 -->
    <div
      v-if="toastMsg"
      class="p-4 bg-emerald-500 text-white rounded-2xl shadow-lg shadow-emerald-200 flex items-center justify-between font-bold animate-in fade-in slide-in-from-top-4 duration-300"
    >
      <span>{{ toastMsg }}</span>
      <button @click="toastMsg = ''" class="text-white/80 hover:text-white">✕</button>
    </div>

    <!-- 頂部：選擇對象 -->
    <div class="bg-white rounded-3xl p-6 shadow-sm border border-gray-100">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-sm font-bold text-gray-500 uppercase tracking-wider flex items-center gap-1.5">
          <span>第一步：選擇登記對象</span>
        </h2>
        <span v-if="authStore.isChild" class="text-xs font-bold text-frog-700 bg-frog-50 px-2.5 py-1 rounded-full border border-frog-200">
          🔒 已鎖定「{{ authStore.unlockedMember?.name }}」小孩專屬帳號
        </span>
      </div>

      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        <div
          v-for="m in members"
          :key="m.id"
          @click="selectMember(m)"
          class="p-4 rounded-2xl border-2 transition-all duration-200 flex flex-col items-center text-center relative overflow-hidden"
          :class="[
            selectedMember?.id === m.id
              ? 'border-frog-500 bg-frog-50/40 shadow-md shadow-frog-100 scale-102 ring-2 ring-frog-400/20 cursor-pointer'
              : (authStore.isChild && m.id !== authStore.unlockedMemberId
                ? 'opacity-40 cursor-not-allowed border-gray-100 bg-gray-50/50'
                : 'cursor-pointer border-gray-100 hover:border-gray-200 bg-gray-50/50 hover:bg-gray-50')
          ]"
        >
          <div class="text-4xl mb-2">{{ m.avatar }}</div>
          <span class="font-bold text-gray-800 text-base leading-tight">{{ m.name }}</span>
          <span class="text-xs text-frog-700 font-semibold mt-1">🪙 {{ m.current_points }} 點</span>

          <div
            v-if="selectedMember?.id === m.id"
            class="absolute top-2 right-2 w-2 h-2 rounded-full bg-frog-500"
          ></div>
        </div>
      </div>
    </div>

    <!-- 第二步：模式切換與內容輸入 -->
    <div class="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-gray-100 space-y-6">
      <div class="flex items-center justify-between pb-4 border-b border-gray-100">
        <h3 class="text-sm font-bold text-gray-500 uppercase tracking-wider">
          第二步：登記模式
        </h3>

        <!-- 模式切換按鈕 -->
        <div class="flex bg-gray-100 p-1 rounded-2xl text-xs font-bold">
          <button
            @click="mode = 'RULE'; triggerPreviewDebounced()"
            class="py-1.5 px-3.5 rounded-xl transition"
            :class="mode === 'RULE' ? 'bg-white text-frog-700 shadow-sm' : 'text-gray-500 hover:text-gray-800'"
          >
            依規則自動帶出
          </button>
          <button
            @click="mode = 'CUSTOM'"
            class="py-1.5 px-3.5 rounded-xl transition"
            :class="mode === 'CUSTOM' ? 'bg-white text-frog-700 shadow-sm' : 'text-gray-500 hover:text-gray-800'"
          >
            自由臨時獎懲 (Bonus/扣點)
          </button>
        </div>
      </div>

      <!-- 模式 A：依規則自動帶出 -->
      <div v-if="mode === 'RULE'" class="space-y-5">
        <!-- 快捷點選可用規則 -->
        <div v-if="availableRules.length > 0">
          <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">常用規則快捷點選</label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="rule in availableRules"
              :key="rule.id"
              @click="selectRule(rule)"
              type="button"
              class="px-3 py-1.5 rounded-xl text-xs font-medium transition flex items-center space-x-1.5"
              :class="selectedRuleId === rule.id ? 'bg-frog-500 text-white shadow-sm shadow-frog-200 font-bold' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
            >
              <span>{{ rule.target_name }}</span>
              <span class="opacity-80 text-[11px] font-mono">({{ rule.condition_value }}: +{{ rule.reward_points }}點)</span>
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider">
                1. 目標項目名稱 (選擇規則)
              </label>
              <span v-if="availableRules.length === 0" class="text-xs text-amber-600 font-medium">
                (尚無可用規則)
              </span>
            </div>
            <div class="relative">
              <select
                v-model="selectedRuleId"
                @change="onRuleSelectChange"
                class="w-full px-4 py-3 rounded-2xl border border-gray-200 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-frog-500 font-bold text-sm text-gray-800 transition appearance-none cursor-pointer pr-10"
              >
                <option value="" disabled>請選擇適用的獎勵規則...</option>
                <optgroup v-if="memberCustomRules.length > 0" label="🌟 成員專屬規則">
                  <option
                    v-for="r in memberCustomRules"
                    :key="r.id"
                    :value="r.id"
                  >
                    {{ r.target_name }} (條件: {{ r.condition_value }} ➔ +{{ r.reward_points }} 點){{ r.description ? ` - ${r.description}` : '' }}
                  </option>
                </optgroup>
                <optgroup v-if="globalRules.length > 0" label="🌐 全家通用規則">
                  <option
                    v-for="r in globalRules"
                    :key="r.id"
                    :value="r.id"
                  >
                    {{ r.target_name }} (條件: {{ r.condition_value }} ➔ +{{ r.reward_points }} 點){{ r.description ? ` - ${r.description}` : '' }}
                  </option>
                </optgroup>
              </select>
              <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-gray-400">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
              </div>
            </div>
          </div>

          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              2. 達成成績 / 條件數值 (自動帶出，可微調)
            </label>
            <input
              v-model="conditionValue"
              type="text"
              placeholder="例如: 100, 95, 完成"
              class="w-full px-4 py-3 rounded-2xl border border-gray-200 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-frog-500 font-medium text-sm transition"
            />
          </div>
        </div>

        <!-- 智慧推導即時反饋 (Live Preview Badge) -->
        <div
          class="p-4 rounded-2xl border transition-all duration-300 flex items-center justify-between"
          :class="previewResult?.matched
            ? 'bg-gradient-to-r from-emerald-50 to-frog-50 border-emerald-200 shadow-sm'
            : 'bg-gray-50 border-gray-200 text-gray-500'"
        >
          <div class="flex items-center space-x-3">
            <span class="text-2xl">{{ previewResult?.matched ? '🌟' : '🔍' }}</span>
            <div>
              <div v-if="previewLoading" class="text-xs text-gray-500">
                推導比對中...
              </div>
              <div v-else-if="previewResult?.matched" class="text-xs font-bold text-emerald-900">
                命中規則：{{ previewResult.rule_name }}
              </div>
              <div v-else class="text-xs text-gray-500">
                未命中預設規則 (建議點數 0 點，亦可手動輸入獎勵點數)
              </div>
            </div>
          </div>

          <!-- 建議獎勵點數 (可點擊微調) -->
          <div class="flex items-center space-x-2">
            <span class="text-xs text-gray-500 font-medium">實發點數:</span>
            <input
              v-model="adjustedPoints"
              type="number"
              class="w-20 px-2 py-1.5 text-center font-bold text-lg font-mono rounded-xl border border-emerald-300 bg-white text-emerald-700 focus:ring-2 focus:ring-frog-500"
            />
            <span class="text-xs font-bold text-emerald-800">點</span>
          </div>
        </div>
      </div>

      <!-- 模式 B：自由臨時獎懲 -->
      <div v-else class="space-y-4">
        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            1. 自訂獎懲事項
          </label>
          <input
            v-model="customTitle"
            type="text"
            placeholder="例如: 主動幫忙照顧弟妹 / 未寫完作業偷看電視"
            class="w-full px-4 py-3 rounded-2xl border border-gray-200 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-frog-500 font-medium text-sm transition"
          />
        </div>

        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            2. 點數增減 (正數為獎勵，負數為扣點違規處罰)
          </label>
          <div class="flex items-center space-x-3">
            <input
              v-model="customPoints"
              type="number"
              class="w-32 px-4 py-3 rounded-2xl border border-gray-200 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-frog-500 font-mono font-bold text-base transition"
            />
            <span class="text-xs font-semibold text-gray-500">點</span>
            <div class="flex space-x-1.5">
              <button
                @click="customPoints = 10"
                type="button"
                class="px-2.5 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-xs font-semibold text-gray-600"
              >
                +10
              </button>
              <button
                @click="customPoints = 20"
                type="button"
                class="px-2.5 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-xs font-semibold text-gray-600"
              >
                +20
              </button>
              <button
                v-if="authStore.isParent"
                @click="customPoints = -10"
                type="button"
                class="px-2.5 py-1.5 rounded-lg bg-red-50 hover:bg-red-100 text-xs font-semibold text-red-600"
              >
                -10 (違規扣點)
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 備註說明 -->
      <div>
        <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
          備註說明 (選填)
        </label>
        <input
          v-model="note"
          type="text"
          placeholder="例如: 第一次段考滿分表現優良！"
          class="w-full px-4 py-3 rounded-2xl border border-gray-200 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-frog-500 font-medium text-sm transition"
        />
      </div>

      <!-- 錯誤提示 -->
      <p v-if="errorMsg" class="text-xs text-red-500 font-bold text-center">
        {{ errorMsg }}
      </p>

      <!-- 確認發放按鈕 -->
      <button
        @click="handleSubmit"
        :disabled="submitting || !selectedMember"
        type="button"
        class="w-full py-4 rounded-2xl bg-gradient-to-r from-frog-500 to-emerald-600 hover:from-frog-600 hover:to-emerald-700 text-white font-bold text-base shadow-lg shadow-frog-200 transition transform hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 flex items-center justify-center space-x-2"
      >
        <span>{{ submitting ? '處理中...' : (authStore.isParent ? '🎉 確認發放點數 / 登記獎懲' : (authStore.isChild ? `📝 確認申請點數 (${authStore.unlockedMember?.name} 專屬)` : '📝 確認申請點數 (需輸入個人 PIN 碼)')) }}</span>
      </button>
    </div>
  </div>
</template>
