<script setup>
import { ref, watch } from 'vue'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  show: Boolean,
})
const emit = defineEmits(['close', 'memberUpdated'])

const authStore = useAuthStore()

const viewMode = ref('list') // 'list' | 'form'
const formMode = ref('create') // 'create' | 'edit'
const membersList = ref([])
const loading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

// 表單資料
const editingMemberId = ref(null)
const name = ref('')
const role = ref('child')
const avatar = ref('🐸')
const pinCode = ref('')
const isActive = ref(true)

const commonAvatars = ['🐸', '👧', '👦', '👨', '👩', '👶', '🐱', '🐶', '🐼', '🐰', '🦁', '🦄', '🚀', '🌟', '🎨', '⚽']

watch(() => props.show, (newVal) => {
  if (newVal) {
    loadMembers()
    viewMode.value = 'list'
    errorMsg.value = ''
    successMsg.value = ''
  }
})

async function loadMembers() {
  loading.value = true
  try {
    membersList.value = await api.getMembers(true) // 包含停用成員
  } catch (err) {
    errorMsg.value = err.message || '載入成員失敗'
  } finally {
    loading.value = false
  }
}

function openCreateForm() {
  formMode.value = 'create'
  editingMemberId.value = null
  name.value = ''
  role.value = 'child'
  avatar.value = '🐸'
  pinCode.value = ''
  isActive.value = true
  errorMsg.value = ''
  viewMode.value = 'form'
}

function openEditForm(member) {
  formMode.value = 'edit'
  editingMemberId.value = member.id
  name.value = member.name
  role.value = member.role
  avatar.value = member.avatar || '🐸'
  pinCode.value = ''
  isActive.value = member.is_active
  errorMsg.value = ''
  viewMode.value = 'form'
}

async function handleSave() {
  if (!name.value.trim()) {
    errorMsg.value = '請輸入成員姓名'
    return
  }

  if (formMode.value === 'create' && role.value === 'parent' && (!pinCode.value || pinCode.value.length < 4)) {
    errorMsg.value = '新增家長角色時必須設定 4 碼 PIN 碼'
    return
  }

  loading.value = true
  errorMsg.value = ''

  try {
    if (formMode.value === 'create') {
      await api.createMember({
        name: name.value.trim(),
        role: role.value,
        avatar: avatar.value,
        pin_code: role.value === 'parent' ? pinCode.value : null,
        parent_pin: authStore.parentPin,
      })
      successMsg.value = `✅ 已成功新增家庭成員「${name.value}」！`
    } else {
      await api.updateMember(editingMemberId.value, {
        name: name.value.trim(),
        role: role.value,
        avatar: avatar.value,
        pin_code: pinCode.value ? pinCode.value : undefined,
        is_active: isActive.value,
        parent_pin: authStore.parentPin,
      })
      successMsg.value = `✅ 已更新成員「${name.value}」資訊！`
    }

    setTimeout(() => { successMsg.value = '' }, 3000)
    emit('memberUpdated')
    await loadMembers()
    viewMode.value = 'list'
  } catch (err) {
    errorMsg.value = err.message || '操作失敗'
  } finally {
    loading.value = false
  }
}

async function handleDelete(member) {
  if (!confirm(`確定要刪除或停用成員「${member.name}」嗎？\n\n若該成員已有歷史點數紀錄，系統將自動安全轉為「停用狀態」以完整保全審計帳本；若為全新無紀錄成員則實體刪除。`)) {
    return
  }

  loading.value = true
  errorMsg.value = ''

  try {
    const res = await api.deleteMember(member.id, authStore.parentPin)
    successMsg.value = `✅ ${res.message || '操作成功'}`
    setTimeout(() => { successMsg.value = '' }, 3000)
    emit('memberUpdated')
    await loadMembers()
  } catch (err) {
    errorMsg.value = err.message || '刪除失敗'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
    <div class="bg-white rounded-3xl shadow-2xl max-w-lg w-full p-6 sm:p-8 max-h-[90vh] flex flex-col">
      <!-- 頂部 Header -->
      <div class="flex items-center justify-between pb-4 border-b border-gray-100 flex-shrink-0">
        <div class="flex items-center space-x-2">
          <span class="text-2xl">👨‍👩‍👧</span>
          <h3 class="text-lg font-bold text-gray-900">
            {{ viewMode === 'list' ? '家庭成員管理' : (formMode === 'create' ? '新增家庭成員' : '編輯成員資訊') }}
          </h3>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 text-xl font-bold">
          ✕
        </button>
      </div>

      <!-- 成功提示 -->
      <div v-if="successMsg" class="my-3 p-3 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-xl text-xs font-semibold">
        {{ successMsg }}
      </div>

      <!-- 錯誤提示 -->
      <div v-if="errorMsg" class="my-3 p-3 bg-red-50 text-red-600 border border-red-200 rounded-xl text-xs font-semibold">
        {{ errorMsg }}
      </div>

      <!-- 【模式 1: 成員清單】 -->
      <div v-if="viewMode === 'list'" class="flex-1 overflow-y-auto py-4 space-y-4">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-gray-500 uppercase tracking-wider">目前家庭成員清單 ({{ membersList.length }})</span>
          <button
            @click="openCreateForm"
            class="px-3.5 py-1.5 rounded-xl bg-frog-500 hover:bg-frog-600 text-white font-bold text-xs shadow-sm transition flex items-center space-x-1"
          >
            <span>+ 新增成員</span>
          </button>
        </div>

        <div class="space-y-2.5">
          <div
            v-for="m in membersList"
            :key="m.id"
            class="p-4 rounded-2xl border transition flex items-center justify-between"
            :class="m.is_active ? 'bg-gray-50 border-gray-100 hover:border-gray-200' : 'bg-gray-100/60 border-gray-200 opacity-60'"
          >
            <div class="flex items-center space-x-3">
              <span class="text-3xl">{{ m.avatar }}</span>
              <div>
                <div class="flex items-center space-x-2">
                  <span class="font-bold text-gray-900 text-base leading-tight">{{ m.name }}</span>
                  <span
                    class="text-[10px] font-bold px-2 py-0.5 rounded-full"
                    :class="m.role === 'parent' ? 'bg-blue-100 text-blue-800' : 'bg-frog-100 text-frog-800'"
                  >
                    {{ m.role === 'parent' ? '家長' : '小孩' }}
                  </span>
                  <span
                    v-if="!m.is_active"
                    class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-gray-200 text-gray-600"
                  >
                    已停用
                  </span>
                </div>
                <div class="text-xs text-gray-500 mt-1 flex space-x-3">
                  <span>🪙 可用: <strong>{{ m.current_points }}</strong> 點</span>
                  <span>🌟 累計: <strong>{{ m.total_earned_points }}</strong> 點</span>
                </div>
              </div>
            </div>

            <!-- 操作按鈕 -->
            <div class="flex items-center space-x-2">
              <button
                @click="openEditForm(m)"
                class="px-3 py-1.5 rounded-xl border border-gray-200 text-xs font-semibold text-gray-700 hover:bg-white transition"
              >
                編輯
              </button>
              <button
                @click="handleDelete(m)"
                class="px-3 py-1.5 rounded-xl border border-red-200 text-xs font-semibold text-red-600 hover:bg-red-50 transition"
              >
                {{ m.is_active ? '刪除/停用' : '刪除' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 【模式 2: 表單 (新增/編輯)】 -->
      <div v-else class="flex-1 overflow-y-auto py-4 space-y-4">
        <!-- 姓名 -->
        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            成員姓名 / 暱稱
          </label>
          <input
            v-model="name"
            type="text"
            placeholder="例如: Ian, Amy, Mom, Dad"
            class="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white text-sm font-medium focus:ring-2 focus:ring-frog-500 transition"
          />
        </div>

        <!-- 角色 -->
        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            角色類型
          </label>
          <div class="grid grid-cols-2 gap-3">
            <label
              class="flex items-center space-x-2 p-3 rounded-xl border cursor-pointer transition text-xs font-medium"
              :class="role === 'child' ? 'border-frog-500 bg-frog-50/50 text-frog-800 font-bold' : 'border-gray-200 text-gray-600'"
            >
              <input type="radio" v-model="role" value="child" class="text-frog-600" />
              <span>👦 小孩 (預設唯讀/成就存摺)</span>
            </label>
            <label
              class="flex items-center space-x-2 p-3 rounded-xl border cursor-pointer transition text-xs font-medium"
              :class="role === 'parent' ? 'border-blue-500 bg-blue-50/50 text-blue-800 font-bold' : 'border-gray-200 text-gray-600'"
            >
              <input type="radio" v-model="role" value="parent" class="text-blue-600" />
              <span>👨 家長 (管理員/需 4 碼 PIN)</span>
            </label>
          </div>
        </div>

        <!-- 頭像選擇 -->
        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            代表頭像 Emoji (目前: <span class="text-xl">{{ avatar }}</span>)
          </label>
          <div class="flex flex-wrap gap-2 mb-2 p-3 bg-gray-50 rounded-2xl border border-gray-100">
            <button
              v-for="av in commonAvatars"
              :key="av"
              type="button"
              @click="avatar = av"
              class="w-9 h-9 rounded-xl flex items-center justify-center text-xl transition hover:scale-110"
              :class="avatar === av ? 'bg-frog-200 shadow-inner' : 'hover:bg-white'"
            >
              {{ av }}
            </button>
          </div>
        </div>

        <!-- 家長 PIN 碼 (若為家長角色) -->
        <div v-if="role === 'parent'">
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            家長安全鎖 4 位數 PIN 碼 {{ formMode === 'edit' ? '(留空表示不變更)' : '' }}
          </label>
          <input
            v-model="pinCode"
            type="password"
            maxlength="6"
            placeholder="請輸入 4 位數 PIN 碼"
            class="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white text-sm font-mono tracking-widest"
          />
        </div>

        <!-- 啟用狀態 (編輯模式) -->
        <div v-if="formMode === 'edit'" class="flex items-center justify-between p-3 bg-gray-50 rounded-xl border border-gray-100">
          <span class="text-xs font-bold text-gray-700">帳號啟用狀態：</span>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" v-model="isActive" class="sr-only peer" />
            <div class="w-10 h-5 bg-gray-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-frog-500"></div>
          </label>
        </div>

        <!-- 表單操作按鈕 -->
        <div class="flex space-x-3 pt-3">
          <button
            @click="viewMode = 'list'"
            type="button"
            class="flex-1 py-2.5 rounded-xl border border-gray-200 text-xs font-bold text-gray-600 hover:bg-gray-50 transition"
          >
            返回成員列表
          </button>
          <button
            @click="handleSave"
            :disabled="loading"
            type="button"
            class="flex-1 py-2.5 rounded-xl bg-frog-500 hover:bg-frog-600 text-white font-bold text-xs shadow-md shadow-frog-200 transition disabled:opacity-50"
          >
            {{ loading ? '儲存中...' : (formMode === 'create' ? '確認新增' : '儲存修改') }}
          </button>
        </div>
      </div>

      <!-- 底部關閉 (在列表模式) -->
      <div v-if="viewMode === 'list'" class="pt-4 border-t border-gray-100 flex-shrink-0">
        <button
          @click="$emit('close')"
          class="w-full py-2.5 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold text-xs transition"
        >
          完成關閉
        </button>
      </div>
    </div>
  </div>
</template>
