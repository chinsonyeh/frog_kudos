<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { triggerConfetti } from '@/components/Confetti'
import BadgeUnlockModal from '@/components/BadgeUnlockModal.vue'
import MemberPinModal from '@/components/MemberPinModal.vue'
import MemberAvatar from '@/components/MemberAvatar.vue'
import ImageViewModal from '@/components/ImageViewModal.vue'

const authStore = useAuthStore()

const showMemberPinModal = ref(false)
const pendingKudosData = ref(null)

const photoInputCamera = ref(null)
const photoInputFile = ref(null)
const proofImageUrl = ref('')
const proofLocalPreview = ref('')
const uploadingPhoto = ref(false)
const showImagePreviewModal = ref(false)

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
const pendingKudosCount = ref(0)

let debounceTimer = null

onMounted(async () => {
  await loadMembers()
  if (authStore.isParent) {
    await loadPendingKudosCount()
  }
})

watch(() => authStore.isParent, async (isParent) => {
  if (isParent) {
    await loadPendingKudosCount()
  }
})

async function loadPendingKudosCount() {
  if (!authStore.isParent) {
    pendingKudosCount.value = 0
    return
  }
  try {
    const list = await api.getPendingKudos()
    pendingKudosCount.value = list.length
  } catch (err) {
    console.error('載入待審核點數失敗', err)
  }
}

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

function triggerCamera() {
  photoInputCamera.value?.click()
}

function triggerFilePicker() {
  photoInputFile.value?.click()
}

async function handlePhotoSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return
  event.target.value = ''

  if (file.size > 15 * 1024 * 1024) {
    errorMsg.value = '照片檔案過大，請選擇 15MB 以內之照片'
    return
  }

  proofLocalPreview.value = URL.createObjectURL(file)
  uploadingPhoto.value = true
  errorMsg.value = ''

  try {
    const res = await api.uploadProofPhoto(file, selectedMember.value?.id)
    proofImageUrl.value = res.url
  } catch (err) {
    errorMsg.value = err.message || '照片上傳失敗，請稍後再試'
    proofLocalPreview.value = ''
    proofImageUrl.value = ''
  } finally {
    uploadingPhoto.value = false
  }
}

function removeProofPhoto() {
  proofImageUrl.value = ''
  proofLocalPreview.value = ''
}

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
    image_url: proofImageUrl.value || null,
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

    if (res.status === 'PENDING') {
      toastMsg.value = `📝 已送出 ${selectedMember.value.name} 的點數申請（+${data.points_awarded} 點）！已排程通知家長審核，審核通過後即入帳 😊`
    } else {
      // 成功慶祝動效 (家長發放或直接 APPROVED)
      if (data.points_awarded > 0) {
        triggerConfetti()
      }
      toastMsg.value = `🎉 已成功為 ${selectedMember.value.name} ${data.points_awarded >= 0 ? `增加 ${data.points_awarded}` : `扣除 ${-data.points_awarded}`} 點！`
    }
    setTimeout(() => { toastMsg.value = '' }, 4000)

    // 清理輸入
    note.value = ''
    proofImageUrl.value = ''
    proofLocalPreview.value = ''
    if (mode.value === 'CUSTOM') {
      customTitle.value = ''
    }
    pendingKudosData.value = null

    // 檢查是否有新解鎖勳章：達成時該用戶正好在登入狀況時立即通知（非家長代為登記）
    if (res.newly_unlocked_badges && res.newly_unlocked_badges.length > 0) {
      if (!authStore.isParent && authStore.unlockedMemberId === selectedMember.value?.id) {
        unlockedBadges.value = res.newly_unlocked_badges
        showBadgeModal.value = true
      }
    }

    // 重新載入成員餘額
    await loadMembers()
    if (authStore.isParent) {
      await loadPendingKudosCount()
    }
  } catch (err) {
    errorMsg.value = err.message || '登記點數失敗'
  } finally {
    submitting.value = false
  }
}

async function handleCloseBadgeModal() {
  showBadgeModal.value = false
  if (selectedMember.value?.id) {
    try {
      await api.ackBadges(selectedMember.value.id)
    } catch (err) {
      console.error('確認成就通知失敗:', err)
    }
  }
  unlockedBadges.value = []
}
</script>

<template>
  <div class="max-w-3xl mx-auto space-y-6">
    <!-- 成員 PIN 碼驗證彈窗 -->
    <MemberPinModal
      :show="showMemberPinModal"
      :member="selectedMember"
      action-title="點數申請確認"
      :description="`請輸入「${selectedMember?.name}」的 4 位數 PIN 碼以確認送出點數申請`"
      @close="showMemberPinModal = false"
      @confirmed="onMemberPinConfirmed"
    />
    <!-- 成就解鎖慶祝彈窗 (登入狀態立即達成) -->
    <BadgeUnlockModal
      v-if="showBadgeModal"
      :badges="unlockedBadges"
      @close="handleCloseBadgeModal"
    />

    <!-- 查驗照片全螢幕檢視彈窗 -->
    <ImageViewModal
      :show="showImagePreviewModal"
      :image-url="proofImageUrl || proofLocalPreview"
      title="查驗照片預覽"
      :subtitle="selectedMember ? `成員：${selectedMember.name} • 項目：${mode === 'RULE' ? (targetName || '尚未填寫') : (customTitle || '自訂獎懲')}` : ''"
      @close="showImagePreviewModal = false"
    />

    <!-- 家長專屬：待審核提示橫幅 -->
    <div
      v-if="authStore.isParent && pendingKudosCount > 0"
      class="p-4 bg-amber-50 border border-amber-200 rounded-2xl flex items-center justify-between text-amber-800 shadow-sm"
    >
      <div class="flex items-center space-x-3">
        <span class="text-2xl">⏳</span>
        <div>
          <p class="font-bold text-sm">目前有 {{ pendingKudosCount }} 筆點數加點申請等待審核！</p>
          <p class="text-xs text-amber-600 mt-0.5">孩子已登記完成事項，請前往商城與審核進行核准或退回。</p>
        </div>
      </div>
      <router-link
        to="/rewards?tab=review"
        class="px-3.5 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-bold transition shadow-sm whitespace-nowrap ml-3"
      >
        前往審核 ➔
      </router-link>
    </div>

    <!-- Toast 成功通知 -->
    <div
      v-if="toastMsg"
      class="p-4 bg-frog-500 text-white rounded-2xl shadow-lg shadow-frog-200 flex items-center justify-between font-bold animate-in fade-in slide-in-from-top-4 duration-300"
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
          <div class="mb-2">
            <MemberAvatar :avatar="m.avatar" :name="m.name" size="xl" />
          </div>
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
            ? 'bg-gradient-to-r from-frog-50 to-frog-100/50 border-frog-200 shadow-sm'
            : 'bg-gray-50 border-gray-200 text-gray-500'"
        >
          <div class="flex items-center space-x-3">
            <span class="text-2xl">{{ previewResult?.matched ? '🌟' : '🔍' }}</span>
            <div>
              <div v-if="previewLoading" class="text-xs text-gray-500">
                推導比對中...
              </div>
              <div v-else-if="previewResult?.matched" class="text-xs font-bold text-frog-900">
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
              class="w-20 px-2 py-1.5 text-center font-bold text-lg font-mono rounded-xl border border-frog-300 bg-white text-frog-700 focus:ring-2 focus:ring-frog-500"
            />
            <span class="text-xs font-bold text-frog-800">點</span>
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

      <!-- 📸 查驗照片拍照與上傳 (供家長查驗) -->
      <div>
        <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5 flex items-center justify-between">
          <span class="flex items-center gap-1">
            <span>📸 查驗照片拍照 / 上傳 (選填)</span>
          </span>
          <span class="text-[11px] text-gray-400 font-normal">考試卷、作業完成或家事照片</span>
        </label>

        <!-- 隱藏原生 File Inputs -->
        <input
          ref="photoInputCamera"
          type="file"
          accept="image/*"
          capture="environment"
          class="hidden"
          @change="handlePhotoSelected"
        />
        <input
          ref="photoInputFile"
          type="file"
          accept="image/*"
          class="hidden"
          @change="handlePhotoSelected"
        />

        <!-- 未選擇照片時的拍照 / 上傳按鈕群組 -->
        <div v-if="!proofLocalPreview && !proofImageUrl" class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          <button
            type="button"
            @click="triggerCamera"
            class="p-3.5 rounded-2xl border-2 border-dashed border-frog-300 hover:border-frog-500 bg-frog-50/50 hover:bg-frog-50 text-frog-800 transition flex items-center justify-center space-x-2 shadow-sm cursor-pointer group"
          >
            <span class="text-xl group-hover:scale-110 transition">📷</span>
            <span class="text-xs font-bold">開啟相機拍照</span>
          </button>

          <button
            type="button"
            @click="triggerFilePicker"
            class="p-3.5 rounded-2xl border-2 border-dashed border-gray-200 hover:border-frog-300 bg-gray-50/60 hover:bg-gray-50 text-gray-700 transition flex items-center justify-center space-x-2 shadow-sm cursor-pointer group"
          >
            <span class="text-xl group-hover:scale-110 transition">🖼️</span>
            <span class="text-xs font-bold">從相簿 / 檔案選取</span>
          </button>
        </div>

        <!-- 已選擇照片的預覽卡片 -->
        <div
          v-else
          class="p-3 bg-gradient-to-r from-frog-50 to-emerald-50 rounded-2xl border border-frog-200 flex items-center justify-between shadow-sm"
        >
          <div class="flex items-center space-x-3 min-w-0">
            <div class="relative flex-shrink-0">
              <img
                :src="proofImageUrl || proofLocalPreview"
                alt="查驗照片"
                class="w-14 h-14 sm:w-16 sm:h-16 object-cover rounded-xl border border-frog-300 shadow-sm cursor-pointer hover:opacity-90 transition"
                @click="showImagePreviewModal = true"
              />
              <div
                v-if="uploadingPhoto"
                class="absolute inset-0 bg-black/40 rounded-xl flex items-center justify-center"
              >
                <span class="text-white text-xs animate-spin">⏳</span>
              </div>
            </div>
            <div class="min-w-0">
              <div class="flex items-center space-x-1.5">
                <span class="text-xs font-bold text-frog-900 truncate">
                  {{ uploadingPhoto ? '照片上傳中...' : '✅ 查驗照片已附加' }}
                </span>
              </div>
              <p class="text-[11px] text-gray-500 mt-0.5 truncate">
                點擊縮圖可檢視大圖，家長審核時可直接查驗
              </p>
            </div>
          </div>

          <div class="flex items-center space-x-1.5 flex-shrink-0 ml-2">
            <button
              type="button"
              @click="showImagePreviewModal = true"
              class="px-2.5 py-1.5 rounded-xl bg-white border border-frog-200 text-frog-700 hover:bg-frog-50 text-xs font-bold transition shadow-sm"
            >
              🔍 查看
            </button>
            <button
              type="button"
              @click="removeProofPhoto"
              class="px-2.5 py-1.5 rounded-xl bg-red-50 hover:bg-red-100 text-red-600 text-xs font-bold transition"
              title="移除照片"
            >
              ✕ 移除
            </button>
          </div>
        </div>
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
        class="w-full py-4 rounded-2xl bg-gradient-to-r from-frog-500 to-frog-600 hover:from-frog-600 hover:to-frog-700 text-white font-bold text-base shadow-lg shadow-frog-200 transition transform hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 flex items-center justify-center space-x-2"
      >
        <span>{{ submitting ? '處理中...' : (authStore.isParent ? '🎉 確認發放點數 / 登記獎懲' : (authStore.isChild ? `📝 送出加點申請（待家長審核）` : '📝 送出加點申請 (需輸入個人 PIN 碼)')) }}</span>
      </button>
    </div>
  </div>
</template>
