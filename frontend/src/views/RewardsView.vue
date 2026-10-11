<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import MemberPinModal from '@/components/MemberPinModal.vue'
import MemberAvatar from '@/components/MemberAvatar.vue'
import ImageViewModal from '@/components/ImageViewModal.vue'

const route = useRoute()
const authStore = useAuthStore()

const showMemberPinModal = ref(false)
const pendingRedeemItem = ref(null)
const previewImageModal = ref({ show: false, url: '', title: '', subtitle: '' })

function openImageModal(url, title = '查驗照片', subtitle = '') {
  previewImageModal.value = { show: true, url, title, subtitle }
}

const activeTab = ref('items') // 'items' | 'review'
const reviewSubTab = ref('kudos') // 'kudos' | 'redemptions'
const members = ref([])
const selectedMemberId = ref(null)
const currentMember = computed(() => members.value.find(m => m.id === selectedMemberId.value) || null)

const items = ref([])
const activeItems = computed(() => items.value.filter(item => item.is_active))
const inactiveItems = computed(() => items.value.filter(item => !item.is_active))
const showInactiveSection = ref(false)

const pendingKudos = ref([])
const pendingRedemptions = ref([])
const totalPendingCount = computed(() => pendingKudos.value.length + pendingRedemptions.value.length)
const loading = ref(false)
const toastMsg = ref('')
const errorMsg = ref('')

// 新增/編輯獎品彈窗
const showItemModal = ref(false)
const editingItem = ref(null)
const itemForm = ref({ title: '', description: '', cost_points: 50, icon: '🎁' })

// 審核退回備註彈窗
const showRejectModal = ref(false)
const rejectTargetType = ref('redemption') // 'redemption' | 'kudos'
const rejectingTargetId = ref(null)
const rejectReason = ref('')

onMounted(async () => {
  if (route.query.tab === 'review') {
    activeTab.value = 'review'
  }
  await loadInitialData()
})

// 監聽家長鎖狀態變更，自動更新品項與待審核清單
watch(() => authStore.isParent, async (isParent) => {
  await loadItems()
  if (isParent) {
    await loadPendingReviews()
  }
})

async function loadInitialData() {
  loading.value = true
  try {
    members.value = await api.getMembers(false)
    if (members.value.length > 0) {
      if (authStore.selectedMemberId && members.value.some(m => m.id === authStore.selectedMemberId)) {
        selectedMemberId.value = authStore.selectedMemberId
      } else {
        selectedMemberId.value = members.value[0].id
        authStore.setSelectedMemberId(selectedMemberId.value)
      }
    }
    await loadItems()
    if (authStore.isParent) {
      await loadPendingReviews()
    }
  } catch (err) {
    console.error('載入商城失敗', err)
  } finally {
    loading.value = false
  }
}

async function loadItems() {
  // 家長模式載入完整資料 (由前端 computed 分流上架中與已下架)；小孩模式僅載入上架品項
  items.value = await api.getItems(authStore.isParent)
}

async function loadPendingReviews() {
  try {
    const [kList, rList] = await Promise.all([
      api.getPendingKudos(),
      api.getRedemptions(null, 'PENDING'),
    ])
    pendingKudos.value = kList
    pendingRedemptions.value = rList
    if (pendingKudos.value.length === 0 && pendingRedemptions.value.length > 0) {
      reviewSubTab.value = 'redemptions'
    } else if (pendingKudos.value.length > 0 && pendingRedemptions.value.length === 0) {
      reviewSubTab.value = 'kudos'
    }
  } catch (err) {
    console.error('載入待審核清單失敗', err)
  }
}

watch(() => authStore.unlockedMemberId, (newId) => {
  if (authStore.isChild && newId) {
    selectedMemberId.value = newId
  }
})

function handleSelectMember(id) {
  if (authStore.isChild && id !== authStore.unlockedMemberId) {
    errorMsg.value = `目前以「${authStore.unlockedMember?.name}」身分解鎖，不可切換幫其他手足兌換！`
    return
  }
  selectedMemberId.value = id
  authStore.setSelectedMemberId(id)
}

async function handleApplyRedemption(item) {
  if (!currentMember.value) return
  if (currentMember.value.current_points < item.cost_points) {
    errorMsg.value = `點數不足，還差 ${item.cost_points - currentMember.value.current_points} 點`
    return
  }

  errorMsg.value = ''

  // 1. 小孩解鎖模式：直接送出兌換申請 (後端透過 Session Token 驗證)
  if (authStore.isChild) {
    await executeRedemption(item, '')
    return
  }

  // 2. 未解鎖訪客模式：彈出 PIN 碼鍵盤驗證
  if (!authStore.isUnlocked) {
    pendingRedeemItem.value = item
    showMemberPinModal.value = true
    return
  }

  // 3. 家長模式：直接以家長 PIN 送出
  await executeRedemption(item, authStore.parentPin)
}

async function onMemberPinConfirmed({ pin }) {
  if (!pendingRedeemItem.value) return
  await executeRedemption(pendingRedeemItem.value, pin)
}

async function executeRedemption(item, pin) {
  errorMsg.value = ''
  try {
    await api.requestRedemption({
      member_id: currentMember.value.id,
      item_id: item.id,
      note: '小孩自主發起心願兌換',
      pin: pin,
    })
    toastMsg.value = `🎉 已成功送出「${item.title}」兌換申請！請提醒家長審核核銷。`
    setTimeout(() => { toastMsg.value = '' }, 4000)

    // 重新載入成員餘額與審核清單
    members.value = await api.getMembers(false)
    if (authStore.isParent) {
      await loadPendingReviews()
    }
    pendingRedeemItem.value = null
  } catch (err) {
    errorMsg.value = err.message || '申請兌換失敗'
  }
}

async function handleApproveKudos(kudos) {
  errorMsg.value = ''
  try {
    await api.reviewKudos(kudos.id, {
      action: 'APPROVE',
      review_note: '家長已核准',
      parent_pin: authStore.parentPin,
    })
    toastMsg.value = `✅ 已核准「${kudos.member_name || ''}」的點數申請 (+${kudos.points_awarded} 點)！`
    setTimeout(() => { toastMsg.value = '' }, 3000)
    await loadPendingReviews()
    members.value = await api.getMembers(false)
  } catch (err) {
    errorMsg.value = err.message || '審核加點失敗'
  }
}

function openRejectKudosModal(kudos) {
  rejectTargetType.value = 'kudos'
  rejectingTargetId.value = kudos.id
  rejectReason.value = '未完全達成要求'
  showRejectModal.value = true
}

async function handleApproveRedemption(id) {
  errorMsg.value = ''
  try {
    await api.reviewRedemption(id, {
      action: 'COMPLETE',
      review_note: '家長已確認兌現',
      parent_pin: authStore.parentPin,
    })
    toastMsg.value = '✅ 兌換申請已核准兌現！'
    setTimeout(() => { toastMsg.value = '' }, 3000)
    await loadPendingReviews()
    members.value = await api.getMembers(false)
  } catch (err) {
    errorMsg.value = err.message || '審核失敗'
  }
}

function openRejectModal(id) {
  rejectTargetType.value = 'redemption'
  rejectingTargetId.value = id
  rejectReason.value = '作業未完成'
  showRejectModal.value = true
}

async function handleConfirmReject() {
  if (!rejectingTargetId.value) return
  errorMsg.value = ''
  try {
    if (rejectTargetType.value === 'kudos') {
      await api.reviewKudos(rejectingTargetId.value, {
        action: 'REJECT',
        review_note: rejectReason.value.trim() || '家長退回申請',
        parent_pin: authStore.parentPin,
      })
      toastMsg.value = '🛑 已退回點數申請！'
    } else {
      await api.reviewRedemption(rejectingTargetId.value, {
        action: 'REJECT',
        review_note: rejectReason.value.trim() || '家長退回申請',
        parent_pin: authStore.parentPin,
      })
      toastMsg.value = '🛑 已退回兌換申請，點數已全額退還給成員錢包！'
    }
    setTimeout(() => { toastMsg.value = '' }, 4000)
    showRejectModal.value = false
    await loadPendingReviews()
    members.value = await api.getMembers(false)
  } catch (err) {
    errorMsg.value = err.message || '退回失敗'
  }
}

// 獎品編輯/新增
function openCreateItemModal() {
  editingItem.value = null
  itemForm.value = { title: '', description: '', cost_points: 50, icon: '🎮' }
  showItemModal.value = true
}

function openEditItemModal(item) {
  editingItem.value = item
  itemForm.value = {
    title: item.title,
    description: item.description || '',
    cost_points: item.cost_points,
    icon: item.icon,
  }
  showItemModal.value = true
}

async function handleSaveItem() {
  if (!itemForm.value.title.trim()) return
  try {
    if (editingItem.value) {
      await api.updateItem(editingItem.value.id, {
        ...itemForm.value,
        parent_pin: authStore.parentPin,
      })
    } else {
      await api.createItem({
        ...itemForm.value,
        parent_pin: authStore.parentPin,
      })
    }
    showItemModal.value = false
    await loadItems()
  } catch (err) {
    errorMsg.value = err.message || '儲存品項失敗'
  }
}

async function handleDeleteItem(item) {
  if (!confirm(`確定要下架「${item.title}」嗎？下架後該獎品將從商城隱藏，小孩將無法兌換。`)) return
  try {
    await api.deleteItem(item.id)
    toastMsg.value = `📦「${item.title}」已成功下架！`
    setTimeout(() => { toastMsg.value = '' }, 3000)
    await loadItems()
  } catch (err) {
    errorMsg.value = err.message || '下架失敗'
  }
}

async function handleRestoreItem(item) {
  try {
    await api.updateItem(item.id, {
      is_active: true,
      parent_pin: authStore.parentPin,
    })
    toastMsg.value = `🎉 已重新上架「${item.title}」！`
    setTimeout(() => { toastMsg.value = '' }, 3000)
    await loadItems()
  } catch (err) {
    errorMsg.value = err.message || '重新上架失敗'
  }
}

async function handlePermanentDeleteItem(item) {
  if (!confirm(`確定要永久刪除「${item.title}」嗎？若該商品有歷史兌換紀錄，系統將自動保護為下架存檔。`)) return
  try {
    const res = await api.deleteItem(item.id, true)
    toastMsg.value = res.message || '已處理'
    setTimeout(() => { toastMsg.value = '' }, 3000)
    await loadItems()
  } catch (err) {
    errorMsg.value = err.message || '刪除失敗'
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <!-- 成員 PIN 碼驗證彈窗 -->
    <MemberPinModal
      :show="showMemberPinModal"
      :member="currentMember"
      action-title="獎品兌換申請"
      :description="`請輸入「${currentMember?.name}」的 4 位數 PIN 碼以確認兌換「${pendingRedeemItem?.title}」`"
      @close="showMemberPinModal = false"
      @confirmed="onMemberPinConfirmed"
    />

    <!-- 查驗照片全螢幕檢視彈窗 -->
    <ImageViewModal
      :show="previewImageModal.show"
      :image-url="previewImageModal.url"
      :title="previewImageModal.title"
      :subtitle="previewImageModal.subtitle"
      @close="previewImageModal.show = false"
    />
    <!-- Toast 成功通知 -->
    <div
      v-if="toastMsg"
      class="p-4 bg-frog-500 text-white rounded-2xl shadow-lg shadow-frog-200 flex items-center justify-between font-bold animate-in fade-in slide-in-from-top-4 duration-300"
    >
      <span>{{ toastMsg }}</span>
      <button @click="toastMsg = ''" class="text-white/80 hover:text-white">✕</button>
    </div>

    <!-- 錯誤訊息提示 -->
    <div v-if="errorMsg" class="p-3 bg-red-50 text-red-600 rounded-xl text-xs font-semibold text-center">
      {{ errorMsg }}
    </div>

    <!-- 頂部：成員選擇與餘額展示 -->
    <div class="bg-white p-4 sm:p-6 rounded-3xl border border-gray-100 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <!-- 成員按鈕切換 -->
      <div class="flex items-center space-x-2 overflow-x-auto pb-1 sm:pb-0">
        <span v-if="authStore.isChild" class="text-xs font-bold text-frog-700 bg-frog-50 px-2.5 py-1 rounded-full border border-frog-200 mr-1 flex-shrink-0">
          🔒 已鎖定「{{ authStore.unlockedMember?.name }}」
        </span>
        <button
          v-for="m in members"
          :key="m.id"
          @click="handleSelectMember(m.id)"
          type="button"
          class="flex items-center space-x-2 px-4 py-2 rounded-2xl text-sm font-bold transition flex-shrink-0"
          :class="[
            selectedMemberId === m.id
              ? 'bg-frog-500 text-white shadow-md shadow-frog-200 cursor-pointer'
              : (authStore.isChild && m.id !== authStore.unlockedMemberId
                ? 'opacity-40 cursor-not-allowed bg-gray-100 text-gray-500'
                : 'bg-gray-100 hover:bg-gray-200 text-gray-700 cursor-pointer')
          ]"
        >
          <MemberAvatar :avatar="m.avatar" :name="m.name" size="xs" />
          <span>{{ m.name }}</span>
        </button>
      </div>

      <!-- 目前餘額顯示 -->
      <div v-if="currentMember" class="flex items-center space-x-2 bg-frog-50 border border-frog-200 px-4 py-2 rounded-2xl text-frog-800 text-sm font-bold flex-shrink-0">
        <span>🪙 可用點數錢包:</span>
        <span class="text-lg font-black font-mono text-frog-700">{{ currentMember.current_points }} 點</span>
      </div>
    </div>

    <!-- 分頁導航 (家長模式解鎖後顯示「待審核」分頁) -->
    <div class="flex items-center justify-between border-b border-gray-200 pb-3">
      <div class="flex space-x-2">
        <button
          @click="activeTab = 'items'"
          class="px-4 py-2 rounded-xl text-sm font-bold transition flex items-center space-x-1.5"
          :class="activeTab === 'items' ? 'bg-white text-frog-700 shadow-sm border border-gray-200' : 'text-gray-500 hover:text-gray-900'"
        >
          <span>🎁</span>
          <span>可兌換品項清單</span>
        </button>

        <button
          v-if="authStore.isParent"
          @click="activeTab = 'review'; loadPendingReviews()"
          class="px-4 py-2 rounded-xl text-sm font-bold transition flex items-center space-x-1.5"
          :class="activeTab === 'review' ? 'bg-white text-frog-700 shadow-sm border border-gray-200' : 'text-gray-500 hover:text-gray-900'"
        >
          <span>📋</span>
          <span>待審核申請</span>
          <span
            v-if="totalPendingCount > 0"
            class="px-2 py-0.5 rounded-full text-xs bg-red-500 text-white font-mono"
          >
            {{ totalPendingCount }}
          </span>
        </button>
      </div>

      <!-- 家長新增獎品按鈕 -->
      <button
        v-if="authStore.isParent && activeTab === 'items'"
        @click="openCreateItemModal"
        class="px-4 py-2 rounded-xl bg-frog-500 hover:bg-frog-600 text-white text-xs font-bold shadow-md shadow-frog-200 transition"
      >
        + 新增商城獎品
      </button>
    </div>

    <!-- 【分頁 1: 可兌換品項清單】 -->
    <div v-if="activeTab === 'items'" class="space-y-6">
      <!-- 上架中商城獎品清單 -->
      <div v-if="activeItems.length === 0" class="bg-white rounded-3xl p-12 text-center text-gray-400 text-sm border border-gray-100">
        🎁 目前商城沒有上架中的獎品{{ authStore.isParent ? '，請點擊上方按鈕新增獎品或從下方庫存重新上架！' : '，敬請期待家長新增！' }}
      </div>
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <div
          v-for="item in activeItems"
          :key="item.id"
          class="bg-white rounded-3xl p-6 border border-gray-100 shadow-sm hover:shadow-md transition flex flex-col justify-between"
        >
          <div>
            <div class="text-4xl mb-3">{{ item.icon || '🎁' }}</div>
            <h4 class="text-base font-bold text-gray-900 mb-1">{{ item.title }}</h4>
            <p class="text-xs text-gray-500 mb-4 min-h-[32px]">{{ item.description || '暫無額外限制說明' }}</p>
          </div>

          <div class="pt-4 border-t border-gray-100">
            <div class="flex items-center justify-between mb-3">
              <span class="text-xs font-medium text-gray-400">所需點數</span>
              <span class="text-lg font-black font-mono text-frog-600">🪙 {{ item.cost_points }} 點</span>
            </div>

            <!-- 申請兌換按鈕 -->
            <button
              type="button"
              @click="handleApplyRedemption(item)"
              :disabled="!currentMember || currentMember.current_points < item.cost_points"
              class="w-full py-2.5 rounded-xl font-bold text-xs transition flex items-center justify-center space-x-1"
              :class="currentMember && currentMember.current_points >= item.cost_points
                ? 'bg-frog-500 hover:bg-frog-600 text-white shadow-md shadow-frog-200 cursor-pointer'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'"
            >
              <span>
                {{ currentMember && currentMember.current_points >= item.cost_points
                  ? '🟢 申請兌換 (凍結扣點)'
                  : `還差 ${currentMember ? item.cost_points - currentMember.current_points : 0} 點` }}
              </span>
            </button>

            <!-- 家長編輯/下架按鈕 -->
            <div v-if="authStore.isParent" class="flex justify-end space-x-2 mt-3 pt-2 border-t border-gray-50 text-xs">
              <button type="button" @click="openEditItemModal(item)" class="text-gray-500 hover:text-gray-800 cursor-pointer">編輯</button>
              <span class="text-gray-200">|</span>
              <button type="button" @click="handleDeleteItem(item)" class="text-red-500 hover:text-red-700 cursor-pointer">下架</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 家長專屬：已下架商品收合管理區 (可重新上架或永久清除) -->
      <div v-if="authStore.isParent && inactiveItems.length > 0" class="mt-8 pt-6 border-t border-gray-200">
        <button
          type="button"
          @click="showInactiveSection = !showInactiveSection"
          class="flex items-center space-x-2 text-xs font-bold text-gray-600 hover:text-gray-900 transition cursor-pointer select-none"
        >
          <span>{{ showInactiveSection ? '▼' : '▶' }}</span>
          <span>📦 已下架商品庫存 ({{ inactiveItems.length }})</span>
          <span class="text-[11px] text-gray-400 font-normal">（可在此重新上架或永久刪除）</span>
        </button>

        <div v-if="showInactiveSection" class="mt-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          <div
            v-for="item in inactiveItems"
            :key="item.id"
            class="bg-gray-50/80 rounded-3xl p-6 border border-dashed border-gray-300 transition flex flex-col justify-between opacity-80 hover:opacity-100"
          >
            <div>
              <div class="flex items-center justify-between mb-2">
                <span class="text-3xl grayscale">{{ item.icon || '🎁' }}</span>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-gray-200 text-gray-600">已下架</span>
              </div>
              <h4 class="text-sm font-bold text-gray-700 mb-1 line-through">{{ item.title }}</h4>
              <p class="text-xs text-gray-400 mb-4 min-h-[32px]">{{ item.description || '暫無限制說明' }}</p>
            </div>

            <div class="pt-3 border-t border-gray-200">
              <div class="flex items-center justify-between mb-3 text-xs text-gray-500 font-mono">
                <span>所需點數</span>
                <span class="font-bold">🪙 {{ item.cost_points }} 點</span>
              </div>
              <div class="flex space-x-2">
                <button
                  type="button"
                  @click="handleRestoreItem(item)"
                  class="flex-1 py-1.5 rounded-xl bg-frog-50 hover:bg-frog-100 text-frog-700 border border-frog-200 text-xs font-bold transition cursor-pointer"
                >
                  🟢 重新上架
                </button>
                <button
                  type="button"
                  @click="handlePermanentDeleteItem(item)"
                  class="px-2.5 py-1.5 rounded-xl bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 text-xs font-bold transition cursor-pointer"
                  title="永久刪除此無關聯品項"
                >
                  🗑️
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 【分頁 2: 待審核申請 (家長專區)】 -->
    <div v-if="activeTab === 'review'" class="space-y-6">
      <!-- 審核子頁籤切換 -->
      <div class="flex bg-gray-100 p-1 rounded-2xl w-fit text-xs font-bold">
        <button
          @click="reviewSubTab = 'kudos'"
          class="py-2 px-4 rounded-xl transition flex items-center space-x-1.5 cursor-pointer"
          :class="reviewSubTab === 'kudos' ? 'bg-white text-frog-700 shadow-sm' : 'text-gray-500 hover:text-gray-800'"
        >
          <span>🪙 點數加點待審核</span>
          <span
            v-if="pendingKudos.length > 0"
            class="px-1.5 py-0.5 rounded-full text-[10px] bg-amber-500 text-white font-mono"
          >
            {{ pendingKudos.length }}
          </span>
        </button>

        <button
          @click="reviewSubTab = 'redemptions'"
          class="py-2 px-4 rounded-xl transition flex items-center space-x-1.5 cursor-pointer"
          :class="reviewSubTab === 'redemptions' ? 'bg-white text-frog-700 shadow-sm' : 'text-gray-500 hover:text-gray-800'"
        >
          <span>🎁 心願兌換待審核</span>
          <span
            v-if="pendingRedemptions.length > 0"
            class="px-1.5 py-0.5 rounded-full text-[10px] bg-red-500 text-white font-mono"
          >
            {{ pendingRedemptions.length }}
          </span>
        </button>
      </div>

      <!-- 子頁籤 A：點數加點審核 -->
      <div v-if="reviewSubTab === 'kudos'" class="space-y-4">
        <div v-if="pendingKudos.length === 0" class="bg-white rounded-3xl p-12 text-center text-gray-400 text-sm border border-gray-100">
          🎉 目前沒有待審核的點數加點申請！孩子登記的事項都已處理完畢。
        </div>

        <div
          v-for="k in pendingKudos"
          :key="k.id"
          class="bg-white rounded-3xl p-6 border border-amber-200 shadow-sm space-y-4"
        >
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-gray-100">
            <div class="flex items-center space-x-3">
              <span class="text-3xl">🪙</span>
              <div>
                <div class="flex items-center space-x-2">
                  <h4 class="font-bold text-gray-900 text-base">{{ k.target_name }}</h4>
                  <span class="text-xs px-2.5 py-0.5 rounded-full bg-frog-100 text-frog-800 font-bold">
                    {{ k.member_name }}
                  </span>
                </div>
                <div class="text-xs text-gray-500 mt-1 flex flex-wrap items-center gap-x-2">
                  <span>達成條件: {{ k.condition_value || '自訂' }}</span>
                  <span>•</span>
                  <span>申請時間: {{ k.created_at.slice(0, 16).replace('T', ' ') }}</span>
                  <span v-if="k.recorded_by">• 登記人: {{ k.recorded_by }}</span>
                </div>
              </div>
            </div>

            <div class="flex items-center space-x-2">
              <span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-100 text-amber-800">
                ⏳ 待核准 (尚未入帳)
              </span>
              <span class="font-mono font-bold text-frog-600 text-lg">+{{ k.points_awarded }} 點</span>
            </div>
          </div>

          <div v-if="k.note" class="text-xs text-gray-600 bg-gray-50 p-3 rounded-xl">
            💬 申請備註：{{ k.note }}
          </div>

          <!-- 📸 查驗證明照片 -->
          <div
            v-if="k.image_url"
            class="p-3 bg-amber-50/70 rounded-2xl border border-amber-200/80 flex items-center justify-between"
          >
            <div class="flex items-center space-x-3 min-w-0">
              <img
                :src="k.image_url"
                alt="查驗照片"
                class="w-16 h-16 sm:w-20 sm:h-20 object-cover rounded-xl border border-amber-300 cursor-pointer shadow-sm hover:scale-105 transition flex-shrink-0"
                @click="openImageModal(k.image_url, `查驗照片 - ${k.target_name || k.target_name_snapshot}`, `申請成員：${k.member_name || ''}`)"
              />
              <div class="min-w-0">
                <span class="text-xs font-bold text-amber-900 flex items-center gap-1">
                  <span>📸 查驗證明照片</span>
                </span>
                <p class="text-[11px] text-gray-500 mt-0.5">
                  點擊縮圖或按鈕可放大檢視照片細節以供查驗
                </p>
              </div>
            </div>
            <button
              type="button"
              @click="openImageModal(k.image_url, `查驗照片 - ${k.target_name || k.target_name_snapshot}`, `申請成員：${k.member_name || ''}`)"
              class="px-3 py-1.5 rounded-xl bg-white border border-amber-300 text-xs font-bold text-amber-800 hover:bg-amber-100 transition shadow-sm flex-shrink-0 ml-2"
            >
              🔍 放大查看
            </button>
          </div>

          <!-- 審核操作按鈕 -->
          <div class="flex space-x-3 pt-1">
            <button
              @click="handleApproveKudos(k)"
              class="flex-1 py-2.5 rounded-xl bg-frog-500 hover:bg-frog-600 text-white font-bold text-xs shadow-md shadow-frog-200 transition cursor-pointer"
            >
              ✅ 核准加點 (入帳 +{{ k.points_awarded }} 點)
            </button>
            <button
              @click="openRejectKudosModal(k)"
              class="flex-1 py-2.5 rounded-xl bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 font-bold text-xs transition cursor-pointer"
            >
              🔴 退回申請 (不予加點)
            </button>
          </div>
        </div>
      </div>

      <!-- 子頁籤 B：心願兌換審核 -->
      <div v-else-if="reviewSubTab === 'redemptions'" class="space-y-4">
        <div v-if="pendingRedemptions.length === 0" class="bg-white rounded-3xl p-12 text-center text-gray-400 text-sm border border-gray-100">
          🎉 目前沒有待審核的兌換申請！
        </div>

        <div
          v-for="r in pendingRedemptions"
          :key="r.id"
          class="bg-white rounded-3xl p-6 border border-amber-200 shadow-sm space-y-4"
        >
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-gray-100">
            <div class="flex items-center space-x-3">
              <span class="text-3xl">🎮</span>
              <div>
                <h4 class="font-bold text-gray-900 text-base">{{ r.item_title_snapshot }}</h4>
                <span class="text-xs text-gray-500">申請時間: {{ r.created_at.slice(0, 16).replace('T', ' ') }}</span>
              </div>
            </div>

            <div class="flex items-center space-x-2">
              <span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-100 text-amber-800">
                ⏳ 待審核 (點數已先扣除)
              </span>
              <span class="font-mono font-bold text-red-600 text-sm">-{{ r.points_spent }} 點</span>
            </div>
          </div>

          <div v-if="r.review_note" class="text-xs text-gray-600 bg-gray-50 p-3 rounded-xl">
            💬 小孩備註：{{ r.review_note }}
          </div>

          <!-- 審核操作按鈕 -->
          <div class="flex space-x-3 pt-1">
            <button
              @click="handleApproveRedemption(r.id)"
              class="flex-1 py-2.5 rounded-xl bg-frog-500 hover:bg-frog-600 text-white font-bold text-xs shadow-md shadow-frog-200 transition cursor-pointer"
            >
              ✅ 核准兌現 (COMPLETED)
            </button>
            <button
              @click="openRejectModal(r.id)"
              class="flex-1 py-2.5 rounded-xl bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 font-bold text-xs transition cursor-pointer"
            >
              🔴 退回申請並退點 (REJECTED)
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 退回原因彈窗 -->
    <div v-if="showRejectModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div class="bg-white rounded-3xl p-6 max-w-sm w-full space-y-4 shadow-2xl">
        <h4 class="font-bold text-gray-900 text-base">
          {{ rejectTargetType === 'kudos' ? '退回加點申請說明' : '退回兌換申請與全額退點說明' }}
        </h4>
        <p class="text-xs text-gray-500">
          {{ rejectTargetType === 'kudos' ? '退回後，此筆加點申請將標記為已退回，不計入成員錢包與累計總榮譽。' : '退回後，系統會在同一資料庫交易中自動全額將點數退回給成員錢包。' }}
        </p>
        <input
          v-model="rejectReason"
          type="text"
          placeholder="請輸入退回原因 (如: 未完全達成要求 / 作業未完成)"
          class="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm font-medium"
        />
        <div class="flex space-x-3">
          <button @click="showRejectModal = false" class="flex-1 py-2 rounded-xl border text-xs font-semibold text-gray-600 cursor-pointer">取消</button>
          <button @click="handleConfirmReject" class="flex-1 py-2 rounded-xl bg-red-600 text-white text-xs font-bold shadow-md cursor-pointer">確認退回</button>
        </div>
      </div>
    </div>

    <!-- 新增/編輯獎品彈窗 -->
    <div v-if="showItemModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div class="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full space-y-4 shadow-2xl">
        <h4 class="font-bold text-gray-900 text-base">{{ editingItem ? '編輯商城獎品' : '新增商城獎品' }}</h4>
        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase mb-1">獎品名稱</label>
          <input v-model="itemForm.title" type="text" class="w-full px-3.5 py-2 rounded-xl border border-gray-200 text-sm" placeholder="例如: 玩 Switch 1 小時" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase mb-1">所需點數</label>
            <input v-model="itemForm.cost_points" type="number" min="1" class="w-full px-3.5 py-2 rounded-xl border border-gray-200 text-sm font-mono" />
          </div>
          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase mb-1">圖示 Emoji</label>
            <input v-model="itemForm.icon" type="text" class="w-full px-3.5 py-2 rounded-xl border border-gray-200 text-sm text-center text-xl" />
          </div>
        </div>
        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase mb-1">限制說明與備註</label>
          <input v-model="itemForm.description" type="text" class="w-full px-3.5 py-2 rounded-xl border border-gray-200 text-sm" placeholder="例如: 限週末完成作業後使用" />
        </div>
        <div class="flex space-x-3 pt-2">
          <button @click="showItemModal = false" class="flex-1 py-2.5 rounded-xl border text-xs font-semibold text-gray-600">取消</button>
          <button @click="handleSaveItem" class="flex-1 py-2.5 rounded-xl bg-frog-500 text-white text-xs font-bold shadow-md shadow-frog-200">儲存獎品</button>
        </div>
      </div>
    </div>
  </div>
</template>
