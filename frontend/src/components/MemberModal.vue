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
const formMode = ref('create') // 'create' | 'edit' | 'avatar' | 'change_pin'
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

// 修改 PIN 碼專用欄位
const oldPin = ref('')
const newPin = ref('')
const confirmPin = ref('')

// 豐富多元的代表頭像清單 (32 款動物、角色、運動與趣味 Emoji)
const commonAvatars = [
  '🐸', '👧', '👦', '👨', '👩', '👶', '🐱', '🐶',
  '🐼', '🐰', '🦁', '🐯', '🐻', '🐨', '🦊', '🦄',
  '🐲', '🦖', '🚀', '🌟', '🌈', '🎨', '⚽', '🏀',
  '🎮', '🍦', '🍕', '🌸', '👑', '🦸', '🧙', '🎸'
]

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
    // 若為家長模式則包含停用成員供維護；若為小孩/未解鎖模式僅列出有效成員
    membersList.value = await api.getMembers(authStore.isParent)
  } catch (err) {
    errorMsg.value = err.message || '載入成員失敗'
  } finally {
    loading.value = false
  }
}

function openCreateForm() {
  if (!authStore.isParent) return // 未解鎖時禁止新增成員
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
  if (!authStore.isUnlocked) {
    errorMsg.value = '訪客模式無法更換頭像，請先解鎖！'
    return
  }
  if (authStore.isChild && member.id !== authStore.unlockedMemberId) {
    errorMsg.value = `目前以「${authStore.unlockedMember?.name}」身分解鎖，僅可修改個人代表頭像！`
    return
  }
  // 若未解鎖則僅允許更換頭像 (avatar)
  formMode.value = authStore.isParent ? 'edit' : 'avatar'
  editingMemberId.value = member.id
  name.value = member.name
  role.value = member.role
  avatar.value = member.avatar || '🐸'
  pinCode.value = ''
  isActive.value = member.is_active
  errorMsg.value = ''
  viewMode.value = 'form'
}

function openChangePinForm(member) {
  if (!authStore.isUnlocked) {
    errorMsg.value = '訪客模式無法變更 PIN 碼，請先解鎖！'
    return
  }
  if (authStore.isChild && member.id !== authStore.unlockedMemberId) {
    errorMsg.value = `目前以「${authStore.unlockedMember?.name}」身分解鎖，僅可變更個人 PIN 碼！`
    return
  }
  formMode.value = 'change_pin'
  editingMemberId.value = member.id
  name.value = member.name
  oldPin.value = ''
  newPin.value = ''
  confirmPin.value = ''
  errorMsg.value = ''
  viewMode.value = 'form'
}

async function handleSave() {
  // 修改 PIN 碼模式 (小孩自主變更或家長重設)
  if (formMode.value === 'change_pin') {
    if (!authStore.isParent && !oldPin.value.trim()) {
      errorMsg.value = '請輸入目前使用的 4 位數 PIN 碼'
      return
    }
    if (!newPin.value.trim() || newPin.value.trim().length < 4) {
      errorMsg.value = '新 PIN 碼必須至少為 4 位數字'
      return
    }
    if (newPin.value.trim() !== confirmPin.value.trim()) {
      errorMsg.value = '兩次輸入的新 PIN 碼不一致'
      return
    }

    loading.value = true
    errorMsg.value = ''
    try {
      await api.changeMemberPin(editingMemberId.value, {
        old_pin: oldPin.value.trim() || null,
        new_pin: newPin.value.trim(),
        parent_pin: authStore.parentPin,
      })
      successMsg.value = `✅ 已成功變更「${name.value}」的 PIN 碼！`
      setTimeout(() => { successMsg.value = '' }, 3000)
      emit('memberUpdated')
      await loadMembers()
      viewMode.value = 'list'
    } catch (err) {
      errorMsg.value = err.message || '變更 PIN 碼失敗'
    } finally {
      loading.value = false
    }
    return
  }

  // 未解鎖狀態：僅更換代表頭像 (無須 PIN 碼)
  if (!authStore.isParent || formMode.value === 'avatar') {
    loading.value = true
    errorMsg.value = ''
    try {
      await api.updateMemberAvatar(editingMemberId.value, avatar.value)
      if (authStore.unlockedMemberId === editingMemberId.value) {
        authStore.updateUnlockedMember({ avatar: avatar.value })
      }
      successMsg.value = `✅ 已成功更換「${name.value}」的代表頭像為 ${avatar.value}！`
      setTimeout(() => { successMsg.value = '' }, 3000)
      emit('memberUpdated')
      await loadMembers()
      viewMode.value = 'list'
    } catch (err) {
      errorMsg.value = err.message || '更換頭像失敗'
    } finally {
      loading.value = false
    }
    return
  }

  // 家長管理模式：完整驗證與儲存
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
        pin_code: pinCode.value ? pinCode.value.trim() : (role.value === 'parent' ? null : '0000'),
        parent_pin: authStore.parentPin,
      })
      successMsg.value = `✅ 已成功新增家庭成員「${name.value}」！`
    } else {
      const updated = await api.updateMember(editingMemberId.value, {
        name: name.value.trim(),
        role: role.value,
        avatar: avatar.value,
        pin_code: pinCode.value && pinCode.value.trim() ? pinCode.value.trim() : undefined,
        is_active: isActive.value,
        parent_pin: authStore.parentPin,
      })
      if (authStore.unlockedMemberId === editingMemberId.value) {
        authStore.updateUnlockedMember({
          name: updated.name,
          role: updated.role,
          avatar: updated.avatar,
        })
      }
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
  if (!authStore.isParent) return

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
          <span class="text-2xl">{{ authStore.isParent ? '👨‍👩‍👧' : '🎨' }}</span>
          <h3 class="text-lg font-bold text-gray-900">
            <template v-if="!authStore.isParent">
              {{ viewMode === 'list' ? '更換成員代表頭像 / PIN 碼' : (formMode === 'change_pin' ? `變更「${name}」的個人 PIN 碼` : `為「${name}」挑選代表頭像`) }}
            </template>
            <template v-else>
              {{ viewMode === 'list' ? '家庭成員管理' : (formMode === 'create' ? '新增家庭成員' : (formMode === 'change_pin' ? `變更「${name}」的個人 PIN 碼` : '編輯成員資訊')) }}
            </template>
          </h3>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 text-xl font-bold cursor-pointer">
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
          <span class="text-xs font-bold text-gray-500 uppercase tracking-wider">
            {{ authStore.isParent ? `目前家庭成員清單 (${membersList.length})` : (authStore.isChild ? `已解鎖「${authStore.unlockedMember?.name}」帳號：僅限維護個人頭像與 PIN 碼` : '家庭成員清單 (請先解鎖以進行維護)') }}
          </span>
          <!-- 僅家長模式顯示 + 新增成員；未解鎖與小孩模式嚴格隱藏 -->
          <button
            v-if="authStore.isParent"
            @click="openCreateForm"
            class="px-3.5 py-1.5 rounded-xl bg-frog-500 hover:bg-frog-600 text-white font-bold text-xs shadow-sm transition flex items-center space-x-1 cursor-pointer"
          >
            <span>+ 新增成員</span>
          </button>
        </div>

        <div class="space-y-2.5">
          <div
            v-for="m in membersList"
            :key="m.id"
            @click="(authStore.isUnlocked && (!authStore.isChild || m.id === authStore.unlockedMemberId)) ? openEditForm(m) : null"
            class="p-4 rounded-2xl border transition flex items-center justify-between"
            :class="[
              m.is_active ? 'bg-gray-50 border-gray-100 hover:border-gray-200' : 'bg-gray-100/60 border-gray-200 opacity-60',
              (authStore.isUnlocked && (!authStore.isChild || m.id === authStore.unlockedMemberId)) ? 'cursor-pointer hover:bg-frog-50/50 hover:border-frog-300' : (authStore.isChild && m.id !== authStore.unlockedMemberId ? 'opacity-50 cursor-not-allowed' : '')
            ]"
          >
            <div class="flex items-center space-x-3">
              <span
                class="text-3xl transition"
                :class="(authStore.isUnlocked && (!authStore.isChild || m.id === authStore.unlockedMemberId)) ? 'hover:scale-125' : ''"
                :title="authStore.isUnlocked ? '點擊更換頭像' : ''"
              >
                {{ m.avatar }}
              </span>
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
                    v-if="!m.is_active && authStore.isParent"
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
              <!-- 家長模式：編輯按鈕 -->
              <button
                v-if="authStore.isParent"
                @click.stop="openEditForm(m)"
                type="button"
                class="px-3 py-1.5 rounded-xl border border-gray-200 text-xs font-semibold text-gray-700 hover:bg-white transition cursor-pointer"
              >
                編輯
              </button>
              <!-- 小孩解鎖模式：僅自己的項目顯示更換頭像與修改 PIN 按鈕 -->
              <template v-else-if="authStore.isChild">
                <template v-if="m.id === authStore.unlockedMemberId">
                  <button
                    @click.stop="openEditForm(m)"
                    type="button"
                    class="px-2.5 py-1.5 rounded-xl bg-frog-50 hover:bg-frog-100 border border-frog-200 text-xs font-bold text-frog-700 transition flex items-center space-x-1 cursor-pointer"
                  >
                    <span>🎨 頭像</span>
                  </button>
                  <button
                    @click.stop="openChangePinForm(m)"
                    type="button"
                    class="px-2.5 py-1.5 rounded-xl bg-amber-50 hover:bg-amber-100 border border-amber-200 text-xs font-bold text-amber-700 transition flex items-center space-x-1 cursor-pointer"
                    title="變更個人 PIN 碼"
                  >
                    <span>🔑 PIN</span>
                  </button>
                </template>
                <template v-else>
                  <span class="text-xs text-gray-400 font-medium px-2">🔒 無權限</span>
                </template>
              </template>
              <template v-else>
                <!-- 訪客未解鎖模式：無任何更換頭像按鈕 -->
                <span class="text-xs text-gray-400 font-medium px-2">🔒 請先解鎖</span>
              </template>

              <!-- 僅家長模式顯示刪除/停用按鈕，未解鎖時嚴格隱藏且禁用 -->
              <button
                v-if="authStore.isParent"
                @click.stop="handleDelete(m)"
                type="button"
                class="px-3 py-1.5 rounded-xl border border-red-200 text-xs font-semibold text-red-600 hover:bg-red-50 transition cursor-pointer"
              >
                {{ m.is_active ? '刪除/停用' : '刪除' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 【模式 2: 表單 (新增/編輯/更換頭像/修改 PIN)】 -->
      <div v-else class="flex-1 overflow-y-auto py-4 space-y-4">
        <!-- 變更個人 PIN 碼模式 -->
        <template v-if="formMode === 'change_pin'">
          <div v-if="!authStore.isParent">
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              目前 PIN 碼 (舊密碼，預設為 0000)
            </label>
            <input
              v-model="oldPin"
              type="password"
              maxlength="6"
              placeholder="請輸入目前 4 位數 PIN 碼"
              class="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white text-sm font-mono tracking-widest"
            />
          </div>
          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              設定新 PIN 碼 (4 位數)
            </label>
            <input
              v-model="newPin"
              type="password"
              maxlength="6"
              placeholder="請輸入新 4 位數 PIN 碼"
              class="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white text-sm font-mono tracking-widest"
            />
          </div>
          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              再次確認新 PIN 碼
            </label>
            <input
              v-model="confirmPin"
              type="password"
              maxlength="6"
              placeholder="請再次輸入新 4 位數 PIN 碼"
              class="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white text-sm font-mono tracking-widest"
            />
          </div>
        </template>

        <template v-else>
          <!-- 姓名 (僅家長模式顯示；未解鎖時嚴格隱藏與禁用) -->
          <div v-if="authStore.isParent">
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

          <!-- 角色類型 (僅家長模式顯示；未解鎖時嚴格隱藏與禁用) -->
          <div v-if="authStore.isParent">
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              角色類型
            </label>
            <div class="grid grid-cols-2 gap-3">
              <label
                class="flex items-center space-x-2 p-3 rounded-xl border cursor-pointer transition text-xs font-medium"
                :class="role === 'child' ? 'border-frog-500 bg-frog-50/50 text-frog-800 font-bold' : 'border-gray-200 text-gray-600'"
              >
                <input type="radio" v-model="role" value="child" class="text-frog-600" />
                <span>👦 小孩 (自主申請增加/兌換)</span>
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

          <!-- 代表頭像選擇 (無論是否解鎖皆可自由挑選) -->
          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              {{ authStore.isParent ? `代表頭像 Emoji (目前: ${avatar})` : `為「${name}」選擇代表頭像 (目前: ${avatar})` }}
            </label>
            <div class="flex flex-wrap gap-2 mb-2 p-3 bg-gray-50 rounded-2xl border border-gray-100 max-h-48 overflow-y-auto">
              <button
                v-for="av in commonAvatars"
                :key="av"
                type="button"
                @click="avatar = av"
                class="w-10 h-10 rounded-xl flex items-center justify-center text-2xl transition hover:scale-110 cursor-pointer"
                :class="avatar === av ? 'bg-frog-200 ring-2 ring-frog-500 shadow-inner' : 'hover:bg-white bg-white/70 shadow-xs'"
              >
                {{ av }}
              </button>
            </div>
          </div>

          <!-- PIN 碼設定 (家長模式下為所有成員設定；未解鎖時嚴格隱藏) -->
          <div v-if="authStore.isParent">
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              {{ role === 'parent' ? '家長安全鎖 4 位數 PIN 碼' : '小孩個人專屬 4 位數 PIN 碼 (預設 0000)' }}
              {{ formMode === 'edit' ? '(留空表示不變更)' : '' }}
            </label>
            <input
              v-model="pinCode"
              type="password"
              maxlength="6"
              placeholder="請輸入 4 位數 PIN 碼"
              class="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white text-sm font-mono tracking-widest"
            />
          </div>

          <!-- 啟用狀態 (僅家長編輯模式時顯示；未解鎖時嚴格隱藏) -->
          <div v-if="authStore.isParent && formMode === 'edit'" class="flex items-center justify-between p-3 bg-gray-50 rounded-xl border border-gray-100">
            <span class="text-xs font-bold text-gray-700">帳號啟用狀態：</span>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="isActive" class="sr-only peer" />
              <div class="w-10 h-5 bg-gray-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-frog-500"></div>
            </label>
          </div>
        </template>

        <!-- 表單操作按鈕 -->
        <div class="flex space-x-3 pt-3">
          <button
            @click="viewMode = 'list'"
            type="button"
            class="flex-1 py-2.5 rounded-xl border border-gray-200 text-xs font-bold text-gray-600 hover:bg-gray-50 transition cursor-pointer"
          >
            返回成員列表
          </button>
          <button
            @click="handleSave"
            :disabled="loading"
            type="button"
            class="flex-1 py-2.5 rounded-xl bg-frog-500 hover:bg-frog-600 text-white font-bold text-xs shadow-md shadow-frog-200 transition disabled:opacity-50 cursor-pointer"
          >
            {{ loading ? '儲存中...' : (formMode === 'change_pin' ? '確認變更 PIN 碼' : (authStore.isParent ? (formMode === 'create' ? '確認新增' : '儲存修改') : '確認更換頭像')) }}
          </button>
        </div>
      </div>

      <!-- 底部關閉 (在列表模式) -->
      <div v-if="viewMode === 'list'" class="pt-4 border-t border-gray-100 flex-shrink-0">
        <button
          @click="$emit('close')"
          class="w-full py-2.5 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold text-xs transition cursor-pointer"
        >
          完成關閉
        </button>
      </div>
    </div>
  </div>
</template>
