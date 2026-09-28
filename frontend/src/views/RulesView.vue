<script setup>
import { ref, onMounted, computed } from 'vue'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const members = ref([])
const categories = ref([])
const selectedTab = ref('global') // 'global' | member_id
const rules = ref([])
const loading = ref(false)
const errorMsg = ref('')

// 新增/編輯規則彈窗
const showRuleModal = ref(false)
const editingRule = ref(null)
const ruleForm = ref({
  member_id: null,
  category_id: null,
  target_name: '',
  match_type: 'NUM_GTE',
  condition_value: '100',
  reward_points: 50,
  description: '',
})

onMounted(async () => {
  await loadInitialData()
})

async function loadInitialData() {
  loading.value = true
  try {
    const [mList, cList] = await Promise.all([
      api.getMembers(false),
      api.getCategories(),
    ])
    members.value = mList
    categories.value = cList

    if (members.value.length > 0) {
      selectedTab.value = members.value[0].id
    }
    await loadRules()
  } catch (err) {
    console.error('載入規則資料失敗', err)
  } finally {
    loading.value = false
  }
}

async function loadRules() {
  const mId = selectedTab.value === 'global' ? null : selectedTab.value
  const allRules = await api.getRules(mId, false)
  if (selectedTab.value === 'global') {
    rules.value = allRules.filter(r => r.member_id === null)
  } else {
    rules.value = allRules.filter(r => r.member_id === selectedTab.value)
  }
}

function handleTabChange(tab) {
  selectedTab.value = tab
  loadRules()
}

function openCreateRuleModal() {
  editingRule.value = null
  ruleForm.value = {
    member_id: selectedTab.value === 'global' ? null : selectedTab.value,
    category_id: categories.value.length > 0 ? categories.value[0].id : null,
    target_name: '',
    match_type: 'NUM_GTE',
    condition_value: '100',
    reward_points: 50,
    description: '',
  }
  showRuleModal.value = true
}

function openEditRuleModal(rule) {
  editingRule.value = rule
  ruleForm.value = {
    member_id: rule.member_id,
    category_id: rule.category_id,
    target_name: rule.target_name,
    match_type: rule.match_type,
    condition_value: rule.condition_value,
    reward_points: rule.reward_points,
    description: rule.description || '',
  }
  showRuleModal.value = true
}

async function handleSaveRule() {
  if (!ruleForm.value.target_name.trim()) {
    errorMsg.value = '請填寫目標項目名稱'
    return
  }
  errorMsg.value = ''
  try {
    if (editingRule.value) {
      await api.updateRule(editingRule.value.id, {
        ...ruleForm.value,
        parent_pin: authStore.parentPin,
      })
    } else {
      await api.createRule({
        ...ruleForm.value,
        parent_pin: authStore.parentPin,
      })
    }
    showRuleModal.value = false
    await loadRules()
  } catch (err) {
    errorMsg.value = err.message || '儲存規則失敗'
  }
}

async function handleDeleteRule(id) {
  if (!confirm('確定要刪除此規則嗎？此操作不溯及既往歷史已發放點數。')) return
  try {
    await api.deleteRule(id)
    await loadRules()
  } catch (err) {
    errorMsg.value = err.message || '刪除規則失敗'
  }
}

function getCategoryName(catId) {
  const cat = categories.value.find(c => c.id === catId)
  return cat ? `${cat.icon} ${cat.name}` : '未分類'
}
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <!-- 頂部防呆提示卡片 -->
    <div class="p-4 sm:p-5 rounded-3xl bg-blue-50/70 border border-blue-200 text-blue-900 text-xs sm:text-sm flex items-start space-x-3 shadow-sm">
      <span class="text-xl">ℹ️</span>
      <div class="leading-relaxed">
        <span class="font-bold">重要提醒：</span>
        在此修改或刪除規則，只會影響「未來」的新成就推導；過往已發放的點數紀錄已永久快照存檔，絕不會被修改或破壞。
      </div>
    </div>

    <!-- 規則對象切換選單 -->
    <div class="bg-white p-4 sm:p-6 rounded-3xl border border-gray-100 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div class="flex space-x-2 overflow-x-auto pb-1 sm:pb-0">
        <button
          v-for="m in members"
          :key="m.id"
          @click="handleTabChange(m.id)"
          class="flex items-center space-x-2 px-4 py-2 rounded-2xl text-xs sm:text-sm font-bold transition flex-shrink-0"
          :class="selectedTab === m.id ? 'bg-frog-500 text-white shadow-md shadow-frog-200' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'"
        >
          <span>{{ m.avatar }}</span>
          <span>{{ m.name }} 專屬</span>
        </button>

        <button
          @click="handleTabChange('global')"
          class="flex items-center space-x-2 px-4 py-2 rounded-2xl text-xs sm:text-sm font-bold transition flex-shrink-0"
          :class="selectedTab === 'global' ? 'bg-frog-500 text-white shadow-md shadow-frog-200' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'"
        >
          <span>🌐</span>
          <span>全家通用規則</span>
        </button>
      </div>

      <!-- 家長新增按鈕 -->
      <button
        v-if="authStore.isParent"
        @click="openCreateRuleModal"
        class="px-4 py-2 rounded-xl bg-frog-500 hover:bg-frog-600 text-white text-xs font-bold shadow-md shadow-frog-200 transition flex items-center space-x-1 flex-shrink-0"
      >
        <span>+ 新增規則</span>
      </button>
    </div>

    <!-- 規則清單 -->
    <div class="space-y-3">
      <div v-if="rules.length === 0" class="bg-white rounded-3xl p-12 text-center text-gray-400 text-sm">
        目前此分類下尚未設定任何獎勵規則
      </div>

      <div
        v-for="rule in rules"
        :key="rule.id"
        class="bg-white rounded-3xl p-5 border border-gray-100 shadow-sm hover:shadow-md transition flex flex-col sm:flex-row sm:items-center justify-between gap-4"
      >
        <div class="space-y-1">
          <div class="flex items-center space-x-2">
            <span class="font-bold text-gray-900 text-base">{{ rule.target_name }}</span>
            <span class="text-xs px-2.5 py-0.5 rounded-full bg-gray-100 text-gray-600 font-medium">
              {{ getCategoryName(rule.category_id) }}
            </span>
          </div>

          <div class="text-xs text-gray-500 flex flex-wrap gap-x-3 gap-y-1">
            <span>門檻條件:
              <strong class="text-gray-700">
                {{ rule.match_type === 'NUM_GTE' ? '≥ ' : (rule.match_type === 'NUM_EQ' ? '= ' : '相符: ') }}{{ rule.condition_value }}
              </strong>
            </span>
            <span v-if="rule.description">說明: {{ rule.description }}</span>
          </div>
        </div>

        <div class="flex items-center space-x-4 self-end sm:self-center">
          <div class="text-right">
            <span class="text-lg font-black font-mono text-frog-600">+{{ rule.reward_points }} 點</span>
          </div>

          <!-- 家長操作 -->
          <div v-if="authStore.isParent" class="flex space-x-2">
            <button
              @click="openEditRuleModal(rule)"
              class="px-3 py-1.5 rounded-xl border border-gray-200 text-xs font-semibold text-gray-600 hover:bg-gray-50 transition"
            >
              編輯
            </button>
            <button
              @click="handleDeleteRule(rule.id)"
              class="px-3 py-1.5 rounded-xl border border-red-200 text-xs font-semibold text-red-600 hover:bg-red-50 transition"
            >
              刪除
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 新增/編輯規則彈窗 -->
    <div v-if="showRuleModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div class="bg-white rounded-3xl p-6 sm:p-8 max-w-lg w-full space-y-4 shadow-2xl">
        <h4 class="font-bold text-gray-900 text-base">
          {{ editingRule ? '編輯獎勵規則' : '新增獎勵規則' }}
        </h4>

        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase mb-1">目標項目名稱</label>
          <input
            v-model="ruleForm.target_name"
            type="text"
            placeholder="例如: 社會科, 數學科, 整理房間"
            class="w-full px-3.5 py-2 rounded-xl border border-gray-200 text-sm font-medium"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase mb-1">分類類別</label>
            <select v-model="ruleForm.category_id" class="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm">
              <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.icon }} {{ c.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase mb-1">獎勵點數</label>
            <input v-model="ruleForm.reward_points" type="number" min="0" class="w-full px-3.5 py-2 rounded-xl border border-gray-200 text-sm font-mono" />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase mb-1">比對方式</label>
            <select v-model="ruleForm.match_type" class="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm">
              <option value="NUM_GTE">數值大於等於 (≥)</option>
              <option value="NUM_EQ">數值等於 (=)</option>
              <option value="EXACT">文字完全相符</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase mb-1">門檻值 / 條件</label>
            <input v-model="ruleForm.condition_value" type="text" placeholder="例如: 100 或 完成" class="w-full px-3.5 py-2 rounded-xl border border-gray-200 text-sm" />
          </div>
        </div>

        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase mb-1">規則備註與說明</label>
          <input v-model="ruleForm.description" type="text" placeholder="例如: 段考考卷滿分特別加碼" class="w-full px-3.5 py-2 rounded-xl border border-gray-200 text-sm" />
        </div>

        <p v-if="errorMsg" class="text-xs text-red-500 font-bold text-center">{{ errorMsg }}</p>

        <div class="flex space-x-3 pt-2">
          <button @click="showRuleModal = false" class="flex-1 py-2.5 rounded-xl border text-xs font-semibold text-gray-600">取消</button>
          <button @click="handleSaveRule" class="flex-1 py-2.5 rounded-xl bg-frog-500 text-white text-xs font-bold shadow-md shadow-frog-200">儲存規則</button>
        </div>
      </div>
    </div>
  </div>
</template>
