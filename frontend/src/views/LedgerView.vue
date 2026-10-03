<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import BatchAdjustModal from '@/components/BatchAdjustModal.vue'
import BadgeUnlockModal from '@/components/BadgeUnlockModal.vue'
import MemberModal from '@/components/MemberModal.vue'
import BadgeManageModal from '@/components/BadgeManageModal.vue'

const authStore = useAuthStore()

const showMemberModal = ref(false)
const showBadgeManageModal = ref(false)
const members = ref([])
const selectedMemberId = ref(null)
const currentMember = computed(() => members.value.find(m => m.id === selectedMemberId.value) || null)

const badges = ref([])
const ledgerItems = ref([])
const rewardItems = ref([])
const loading = ref(false)

const showBatchModal = ref(false)
const showBadgeModal = ref(false)
const unlockedBadges = ref([])

// 監聽全域成員異動，自動重新載入成員與存摺清單
watch(() => authStore.memberRefreshKey, async () => {
  await loadInitialData()
})

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
      await loadMemberDetails()
    }
    // 載入獎品商城以計算願望進度條
    rewardItems.value = await api.getItems(false)
  } catch (err) {
    console.error('載入存摺資訊失敗', err)
  } finally {
    loading.value = false
  }
}

async function loadMemberDetails() {
  if (!selectedMemberId.value) return
  try {
    const [bList, lList] = await Promise.all([
      api.getMemberBadges(selectedMemberId.value),
      api.getLedgerHistory(selectedMemberId.value, 100),
    ])
    badges.value = bList
    ledgerItems.value = lList
  } catch (err) {
    console.error('載入明細失敗', err)
  }
}

function handleSelectMember(id) {
  selectedMemberId.value = id
  authStore.setSelectedMemberId(id)
  loadMemberDetails()
}

// 下一個願望目標計算
const nextRewardGoal = computed(() => {
  if (!currentMember.value || rewardItems.value.length === 0) return null
  const curr = currentMember.value.current_points
  // 尋找高於目前點數的最近獎品
  const higherItems = rewardItems.value
    .filter(i => i.cost_points > curr)
    .sort((a, b) => a.cost_points - b.cost_points)

  if (higherItems.length > 0) {
    const target = higherItems[0]
    const needed = target.cost_points - curr
    const percent = Math.min(100, Math.floor((curr / target.cost_points) * 100))
    return {
      title: target.title,
      cost_points: target.cost_points,
      needed,
      percent,
    }
  }

  // 若已超過所有品項，取最高目標
  const maxItem = [...rewardItems.value].sort((a, b) => b.cost_points - a.cost_points)[0]
  return {
    title: maxItem ? maxItem.title : '達成全部願望！',
    cost_points: maxItem ? maxItem.cost_points : curr,
    needed: 0,
    percent: 100,
  }
})

function handleDownloadCsv() {
  if (!selectedMemberId.value) return
  const url = api.exportLedgerUrl(selectedMemberId.value)
  window.open(url, '_blank')
}

async function onAdjusted() {
  await loadInitialData()
}

function onUnlockedBadges(bList) {
  unlockedBadges.value = bList
  showBadgeModal.value = true
}
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <!-- 成就彈窗 -->
    <BadgeUnlockModal
      v-if="showBadgeModal"
      :badges="unlockedBadges"
      @close="showBadgeModal = false"
    />

    <!-- 批次調整彈窗 -->
    <BatchAdjustModal
      :show="showBatchModal"
      :members="members"
      :initial-member-id="selectedMemberId"
      @close="showBatchModal = false"
      @adjusted="onAdjusted"
      @unlocked-badges="onUnlockedBadges"
    />

    <!-- 成員管理彈窗 -->
    <MemberModal
      :show="showMemberModal"
      @close="showMemberModal = false"
      @member-updated="loadInitialData"
    />

    <!-- 勳章管理與編輯彈窗 (FR-18) -->
    <BadgeManageModal
      :show="showBadgeManageModal"
      :current-member="currentMember"
      @close="showBadgeManageModal = false"
      @badges-updated="loadMemberDetails"
    />

    <!-- 頂部標題與成員切換選單 -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-4 sm:p-6 rounded-3xl border border-gray-100 shadow-sm">
      <!-- 成員標籤列 -->
      <div class="flex items-center space-x-2 overflow-x-auto pb-1 sm:pb-0">
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

        <!-- 家長管理成員按鈕 / 未解鎖時更換頭像按鈕 -->
        <button
          v-if="authStore.isParent"
          @click="showMemberModal = true"
          class="flex items-center space-x-1 px-3 py-2 rounded-2xl text-xs font-bold border border-dashed border-gray-300 hover:border-frog-500 hover:bg-frog-50/50 text-gray-500 hover:text-frog-700 transition flex-shrink-0 cursor-pointer"
          title="新增或維護家庭成員"
        >
          <span>+ 管理成員</span>
        </button>
        <button
          v-else
          @click="showMemberModal = true"
          class="flex items-center space-x-1 px-3 py-2 rounded-2xl text-xs font-bold border border-dashed border-gray-300 hover:border-frog-500 hover:bg-frog-50/50 text-gray-500 hover:text-frog-700 transition flex-shrink-0 cursor-pointer"
          title="更換成員代表頭像"
        >
          <span>🎨 更換頭像</span>
        </button>
      </div>

      <!-- 操作按鈕群 -->
      <div class="flex items-center space-x-2">
        <button
          @click="handleDownloadCsv"
          class="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl border border-gray-200 bg-white hover:bg-gray-50 active:bg-gray-100 text-gray-700 text-xs font-bold transition shadow-sm"
          title="匯出綜合存摺 CSV 檔案"
        >
          <span>📥</span>
          <span>匯出存摺 (CSV)</span>
        </button>

        <button
          v-if="authStore.isParent"
          @click="showBatchModal = true"
          class="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 text-xs font-bold transition shadow-sm"
          title="依時間與項目批次統一調整歷史積分"
        >
          <span>🛠</span>
          <span>批次調整歷史積分</span>
        </button>
      </div>
    </div>

    <!-- 成員餘額與願望進度卡片 -->
    <div v-if="currentMember" class="bg-gradient-to-br from-emerald-500 to-teal-700 text-white rounded-3xl p-6 sm:p-8 shadow-xl shadow-emerald-900/10 relative overflow-hidden">
      <!-- 背景光暈裝飾 -->
      <div class="absolute -right-10 -bottom-10 w-44 h-44 bg-white/10 rounded-full blur-2xl"></div>

      <div class="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div>
          <div class="flex items-center space-x-3 mb-2">
            <span
              @click="showMemberModal = true"
              class="text-4xl sm:text-5xl cursor-pointer hover:scale-110 active:scale-95 transition"
              title="點擊更換頭像"
            >{{ currentMember.avatar }}</span>
            <div>
              <div class="flex items-center space-x-2">
                <h3 class="text-2xl font-black tracking-tight">{{ currentMember.name }} 的點數存摺</h3>
                <button
                  @click="showMemberModal = true"
                  type="button"
                  class="text-[11px] bg-white/20 hover:bg-white/30 text-white px-2 py-0.5 rounded-lg font-bold transition cursor-pointer"
                  title="更換代表頭像"
                >
                  🎨 更換頭像
                </button>
              </div>
              <span class="text-xs font-medium text-emerald-100">持續累積自主自律成果</span>
            </div>
          </div>
        </div>

        <!-- 雙軌點數看板 -->
        <div class="flex space-x-4 bg-white/10 backdrop-blur-md p-3.5 rounded-2xl border border-white/20">
          <div class="text-center px-3">
            <span class="text-[11px] uppercase tracking-wider text-emerald-100 font-bold block">目前可用點數</span>
            <span class="text-2xl sm:text-3xl font-black font-mono">🪙 {{ currentMember.current_points }}</span>
          </div>
          <div class="w-px bg-white/20"></div>
          <div class="text-center px-3">
            <span class="text-[11px] uppercase tracking-wider text-emerald-100 font-bold block">歷史累計總榮譽</span>
            <span class="text-2xl sm:text-3xl font-black font-mono">🌟 {{ currentMember.total_earned_points }}</span>
          </div>
        </div>
      </div>

      <!-- 下一個大獎願望進度條 -->
      <div v-if="nextRewardGoal" class="mt-6 pt-5 border-t border-white/15">
        <div class="flex items-center justify-between text-xs font-bold mb-2">
          <span>🎯 下一個願望大獎：{{ nextRewardGoal.title }} ({{ nextRewardGoal.cost_points }} 點)</span>
          <span>
            {{ nextRewardGoal.needed > 0 ? `還差 ${nextRewardGoal.needed} 點` : '🎉 已達成兌換門檻！' }}
          </span>
        </div>
        <div class="w-full bg-black/20 rounded-full h-3 p-0.5 overflow-hidden">
          <div
            class="bg-gradient-to-r from-yellow-300 to-amber-400 h-full rounded-full transition-all duration-500 shadow-sm"
            :style="{ width: `${nextRewardGoal.percent}%` }"
          ></div>
        </div>
      </div>
    </div>

    <!-- 🏅 里程碑成就勳章牆 (Milestone Badges - FR-18) -->
    <div class="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-gray-100">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-bold text-gray-500 uppercase tracking-wider flex items-center gap-1.5">
          <span>🏅 榮譽成就勳章牆 (Milestone Badges)</span>
        </h3>
        <div class="flex items-center space-x-3">
          <span class="text-xs font-semibold text-gray-400">已解鎖 {{ badges.filter(b => b.unlocked).length }} / {{ badges.length }}</span>
          <button
            v-if="authStore.isParent"
            @click="showBadgeManageModal = true"
            class="text-xs font-bold text-frog-600 hover:text-frog-800 transition flex items-center space-x-1"
          >
            <span>⚙️ 編輯 / 管理勳章</span>
          </button>
        </div>
      </div>

      <div class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-3 sm:gap-4">
        <div
          v-for="b in badges"
          :key="b.badge_key"
          class="p-4 rounded-2xl border transition-all duration-200 flex flex-col items-center text-center relative overflow-hidden group"
          :class="b.unlocked
            ? 'bg-gradient-to-b from-amber-50/60 to-yellow-50/30 border-amber-200 shadow-sm'
            : 'bg-gray-50/60 border-gray-100 opacity-60 grayscale'"
        >
          <!-- 家長模式下的快速編輯按鈕 -->
          <button
            v-if="authStore.isParent"
            @click.stop="showBadgeManageModal = true"
            class="absolute top-1.5 right-1.5 opacity-0 group-hover:opacity-100 text-gray-400 hover:text-frog-600 text-xs p-1 rounded-lg hover:bg-white/80 transition shadow-sm"
            title="編輯勳章"
          >
            ✏️
          </button>

          <div
            class="w-14 h-14 rounded-2xl flex items-center justify-center text-3xl mb-2.5 shadow-sm"
            :class="b.unlocked ? 'bg-amber-400 text-white shadow-amber-200' : 'bg-gray-200 text-gray-400'"
          >
            {{ b.icon }}
          </div>
          <h5 class="text-xs font-bold text-gray-800 leading-tight mb-0.5">{{ b.title }}</h5>
          <p class="text-[11px] text-gray-500 mb-2">{{ b.description }}</p>

          <!-- 達成狀態 -->
          <div class="w-full mt-auto">
            <span
              v-if="b.unlocked"
              class="inline-block px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800"
            >
              ✨ 已解鎖
            </span>
            <div v-else class="space-y-1">
              <div class="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                <div
                  class="bg-frog-500 h-1.5 rounded-full"
                  :style="{ width: `${Math.min(100, Math.floor((b.progress / b.target) * 100))}%` }"
                ></div>
              </div>
              <span class="text-[10px] text-gray-400 font-mono font-semibold">{{ b.progress }}/{{ b.target }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 點數歷史流水帳 (Immutable Ledger - FR-6) -->
    <div class="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-gray-100">
      <h3 class="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4">
        點數歷史流水帳 (Immutable Ledger)
      </h3>

      <div v-if="ledgerItems.length === 0" class="p-8 text-center text-gray-400 text-sm">
        目前尚無任何點數流水紀錄
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="item in ledgerItems"
          :key="item.id"
          class="p-4 rounded-2xl border border-gray-100 hover:border-gray-200 transition bg-gray-50/40 hover:bg-gray-50 flex items-center justify-between"
        >
          <div class="space-y-1">
            <div class="flex items-center space-x-2">
              <span class="font-bold text-gray-800 text-sm sm:text-base">{{ item.title }}</span>
              <span class="text-xs px-2 py-0.5 rounded-lg font-semibold"
                :class="item.record_type === 'KUDOS' ? 'bg-emerald-100 text-emerald-800' : 'bg-purple-100 text-purple-800'"
              >
                {{ item.record_type === 'KUDOS' ? '成就' : '兌換' }}
              </span>
              <span class="text-xs text-gray-500 font-medium">({{ item.condition_or_status }})</span>
            </div>

            <div class="text-xs text-gray-500 flex flex-wrap gap-x-3 gap-y-1">
              <span>🕒 {{ item.created_at.slice(0, 16).replace('T', ' ') }}</span>
              <span v-if="item.note">📝 備註: {{ item.note }}</span>
              <span>👤 經辦人: {{ item.actor }}</span>
            </div>
          </div>

          <!-- 點數增減顯示 -->
          <div class="text-right flex-shrink-0 ml-3">
            <span
              class="text-base sm:text-lg font-black font-mono"
              :class="item.points > 0 ? 'text-emerald-600' : (item.points < 0 ? 'text-red-500' : 'text-gray-400')"
            >
              {{ item.points > 0 ? `+${item.points}` : item.points }} 點
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
