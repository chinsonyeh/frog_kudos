<script setup>
import { ref, onMounted, computed } from 'vue'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const activeTab = ref('items') // 'items' | 'review'
const members = ref([])
const selectedMemberId = ref(null)
const currentMember = computed(() => members.value.find(m => m.id === selectedMemberId.value) || null)

const items = ref([])
const pendingRedemptions = ref([])
const loading = ref(false)
const toastMsg = ref('')
const errorMsg = ref('')

// 新增/編輯獎品彈窗
const showItemModal = ref(false)
const editingItem = ref(null)
const itemForm = ref({ title: '', description: '', cost_points: 50, icon: '🎁' })

// 審核備註彈窗
const showRejectModal = ref(false)
const rejectingRedemptionId = ref(null)
const rejectReason = ref('')

onMounted(async () => {
  await loadInitialData()
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
  items.value = await api.getItems(authStore.isParent)
}

async function loadPendingReviews() {
  pendingRedemptions.value = await api.getRedemptions(null, 'PENDING')
}

function handleSelectMember(id) {
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
  try {
    await api.requestRedemption({
      member_id: currentMember.value.id,
      item_id: item.id,
      note: '小孩自主發起心願兌換',
    })
    toastMsg.value = `🎉 已成功送出「${item.title}」兌換申請！請提醒家長審核核銷。`
    setTimeout(() => { toastMsg.value = '' }, 4000)

    // 重新載入成員餘額與審核清單
    members.value = await api.getMembers(false)
    if (authStore.isParent) {
      await loadPendingReviews()
    }
  } catch (err) {
    errorMsg.value = err.message || '申請兌換失敗'
  }
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
  rejectingRedemptionId.value = id
  rejectReason.value = '作業未完成'
  showRejectModal.value = true
}

async function handleConfirmReject() {
  if (!rejectingRedemptionId.value) return
  errorMsg.value = ''
  try {
    await api.reviewRedemption(rejectingRedemptionId.value, {
      action: 'REJECT',
      review_note: rejectReason.value.trim() || '家長退回申請',
      parent_pin: authStore.parentPin,
    })
    toastMsg.value = '🛑 已退回兌換申請，點數已全額退還給成員錢包！'
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

async function handleDeleteItem(id) {
  if (!confirm('確定要下架此獎品嗎？')) return
  try {
    await api.deleteItem(id)
    await loadItems()
  } catch (err) {
    errorMsg.value = err.message || '下架失敗'
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <!-- Toast 成功通知 -->
    <div
      v-if="toastMsg"
      class="p-4 bg-emerald-500 text-white rounded-2xl shadow-lg shadow-emerald-200 flex items-center justify-between font-bold animate-in fade-in slide-in-from-top-4 duration-300"
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
      <div class="flex space-x-2 overflow-x-auto pb-1 sm:pb-0">
        <button
          v-for="m in members"
          :key="m.id"
          @click="handleSelectMember(m.id)"
          class="flex items-center space-x-2 px-4 py-2 rounded-2xl text-sm font-bold transition flex-shrink-0"
          :class="selectedMemberId === m.id
            ? 'bg-frog-500 text-white shadow-md shadow-frog-200'
            : 'bg-gray-100 hover:bg-gray-200 text-gray-700'"
        >
          <span>{{ m.avatar }}</span>
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
            v-if="pendingRedemptions.length > 0"
            class="px-2 py-0.5 rounded-full text-xs bg-red-500 text-white font-mono"
          >
            {{ pendingRedemptions.length }}
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
    <div v-if="activeTab === 'items'" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
      <div
        v-for="item in items"
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
            @click="handleApplyRedemption(item)"
            :disabled="!currentMember || currentMember.current_points < item.cost_points"
            class="w-full py-2.5 rounded-xl font-bold text-xs transition flex items-center justify-center space-x-1"
            :class="currentMember && currentMember.current_points >= item.cost_points
              ? 'bg-frog-500 hover:bg-frog-600 text-white shadow-md shadow-frog-200'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'"
          >
            <span>
              {{ currentMember && currentMember.current_points >= item.cost_points
                ? '🟢 申請兌換 (凍結扣點)'
                : `還差 ${currentMember ? item.cost_points - currentMember.current_points : 0} 點` }}
            </span>
          </button>

          <!-- 家長編輯/刪除按鈕 -->
          <div v-if="authStore.isParent" class="flex justify-end space-x-2 mt-3 pt-2 border-t border-gray-50 text-xs">
            <button @click="openEditItemModal(item)" class="text-gray-500 hover:text-gray-800">編輯</button>
            <span class="text-gray-200">|</span>
            <button @click="handleDeleteItem(item.id)" class="text-red-500 hover:text-red-700">下架</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 【分頁 2: 待審核兌換申請 (家長專區)】 -->
    <div v-if="activeTab === 'review'" class="space-y-4">
      <div v-if="pendingRedemptions.length === 0" class="bg-white rounded-3xl p-12 text-center text-gray-400 text-sm">
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
            class="flex-1 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white font-bold text-xs shadow-md shadow-emerald-200 transition"
          >
            🟢 核准兌現 (COMPLETED)
          </button>
          <button
            @click="openRejectModal(r.id)"
            class="flex-1 py-2.5 rounded-xl bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 font-bold text-xs transition"
          >
            🔴 退回申請並退點 (REJECTED)
          </button>
        </div>
      </div>
    </div>

    <!-- 退回原因彈窗 -->
    <div v-if="showRejectModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div class="bg-white rounded-3xl p-6 max-w-sm w-full space-y-4 shadow-2xl">
        <h4 class="font-bold text-gray-900 text-base">退回申請與全額退點說明</h4>
        <p class="text-xs text-gray-500">退回後，系統會在同一資料庫交易中自動全額將點數退回給成員錢包。</p>
        <input
          v-model="rejectReason"
          type="text"
          placeholder="請輸入退回原因 (如: 作業未寫完)"
          class="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 text-sm font-medium"
        />
        <div class="flex space-x-3">
          <button @click="showRejectModal = false" class="flex-1 py-2 rounded-xl border text-xs font-semibold text-gray-600">取消</button>
          <button @click="handleConfirmReject" class="flex-1 py-2 rounded-xl bg-red-600 text-white text-xs font-bold shadow-md">確認退回</button>
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
