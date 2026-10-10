<script setup>
import { ref, watch, computed } from 'vue'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import MemberAvatar from '@/components/MemberAvatar.vue'
import AvatarCropperModal from '@/components/AvatarCropperModal.vue'

const props = defineProps({
  show: Boolean,
})
const emit = defineEmits(['close', 'memberUpdated'])

const authStore = useAuthStore()
const themeStore = useThemeStore()

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
const originalAvatar = ref('🐸')
const pinCode = ref('')
const isActive = ref(true)

// 自訂頭像三合一選擇器狀態
const avatarTab = ref('upload') // 'upload' | 'frog' | 'emoji'
const selectedFile = ref(null)
const filePreviewUrl = ref('')
const fileInputRef = ref(null)
const uploading = ref(false)

// ROI 圓圈裁切器狀態
const showCropper = ref(false)
const rawImageSrc = ref('')
const latestUploadedAvatar = ref(null) // { url, filename, size_kb, created_at }

function isImageAvatar(av) {
  if (!av) return false
  const a = av.trim()
  return a.startsWith('/') || a.startsWith('http') || a.startsWith('data:')
}

function triggerFileInput() {
  if (fileInputRef.value) {
    fileInputRef.value.click()
  }
}

function handleFileSelect(event) {
  const file = event.target.files?.[0]
  if (!file) return
  if (file.size > 10 * 1024 * 1024) {
    errorMsg.value = '圖片大小超過 10MB，請挑選較小的相片！'
    return
  }
  if (rawImageSrc.value && rawImageSrc.value.startsWith('blob:')) {
    URL.revokeObjectURL(rawImageSrc.value)
  }
  rawImageSrc.value = URL.createObjectURL(file)
  showCropper.value = true
  errorMsg.value = ''
  if (event.target) {
    event.target.value = ''
  }
}

async function handleCropped({ blob, dataUrl, file }) {
  showCropper.value = false
  uploading.value = true
  errorMsg.value = ''
  try {
    // 立即將裁切壓製後之圖片上傳並保存至歷史相片庫
    const res = await api.uploadCustomAvatarToGallery(file)
    latestUploadedAvatar.value = res
    // 重新整理歷史相片庫列表，剛上傳之相片立即呈現在列表中第一位
    await loadCustomAvatars()
    // 注意：尚不要套用，維持 avatar.value 不變！
    successMsg.value = '✅ 相片已裁切並加入自訂相片庫！點選相片或點擊「立即套用」即可生效。'
    setTimeout(() => { successMsg.value = '' }, 4000)
  } catch (err) {
    errorMsg.value = err.message || '相片處理並加入相片庫失敗'
  } finally {
    uploading.value = false
  }
}

async function applyAvatar(targetUrl) {
  avatar.value = targetUrl
  // 若處於編輯既有成員模式，立即儲存更新至資料庫
  if (editingMemberId.value) {
    loading.value = true
    errorMsg.value = ''
    try {
      await api.updateMemberAvatar(editingMemberId.value, targetUrl)
      originalAvatar.value = targetUrl
      if (authStore.unlockedMemberId === editingMemberId.value) {
        authStore.updateUnlockedMember({ avatar: targetUrl })
      }
      successMsg.value = `✅ 已成功套用為「${name.value}」的代表頭像！`
      setTimeout(() => { successMsg.value = '' }, 3000)
      emit('memberUpdated')
      await loadMembers()
    } catch (err) {
      errorMsg.value = err.message || '套用頭像失敗'
    } finally {
      loading.value = false
    }
  } else {
    // 新增成員模式：套用至表單頭像預覽
    successMsg.value = '✅ 已套用至頭像預覽！'
    setTimeout(() => { successMsg.value = '' }, 3000)
  }
}

// 自訂頭像相片庫狀態 (上限 100 個)
const customAvatars = ref([])
const customAvatarsCount = ref(0)
const customAvatarsMax = ref(100)
const loadingGallery = ref(false)

async function loadCustomAvatars() {
  loadingGallery.value = true
  try {
    const res = await api.getCustomAvatarsGallery()
    customAvatars.value = res.avatars || []
    customAvatarsCount.value = res.total || 0
    customAvatarsMax.value = res.max_allowed || 100
  } catch (err) {
    console.error('載入歷史頭像庫失敗:', err)
  } finally {
    loadingGallery.value = false
  }
}

async function handleDeleteCustomAvatar(item) {
  if (!confirm(`確定要從自訂頭像庫刪除這張相片嗎？`)) return
  try {
    await api.deleteCustomAvatar(item.filename)
    if (avatar.value === item.url) {
      avatar.value = '🐸'
      originalAvatar.value = '🐸'
    }
    if (latestUploadedAvatar.value && latestUploadedAvatar.value.filename === item.filename) {
      latestUploadedAvatar.value = null
    }
    await loadCustomAvatars()
    await loadMembers()
    emit('memberUpdated')
  } catch (err) {
    errorMsg.value = err.message || '刪除頭像失敗'
  }
}

// 監聽分頁切換，若切換至相片上傳則載入相片庫
watch(avatarTab, (newTab) => {
  if (newTab === 'upload') {
    loadCustomAvatars()
  }
})

// 修改 PIN 碼專用欄位
const oldPin = ref('')
const newPin = ref('')
const confirmPin = ref('')

// 豐富多元的代表頭像分類清單 (包含 250+ 款熱門、動物、角色、人物、運動、美食、自然 Emoji)
const avatarCategories = [
  {
    name: '熱門精選',
    icon: '🔥',
    avatars: [
      '🐸', '👧', '👦', '👨', '👩', '👶', '🐱', '🐶',
      '🐼', '🐰', '🦁', '🐯', '🐻', '🐨', '🦊', '🦄',
      '🐲', '🦖', '🚀', '🌟', '🌈', '🎨', '⚽', '🏀',
      '🎮', '🍦', '🍕', '🌸', '👑', '🦸', '🧙', '🎸'
    ]
  },
  {
    name: '動物萌寵',
    icon: '🐶',
    avatars: [
      '🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼',
      '🐨', '🐯', '🦁', '🐮', '🐷', '🐸', '🐵', '🐔',
      '🐧', '🐦', '🐤', '🦆', '🦅', '🦉', '🐺', '🐗',
      '🐴', '🦄', '🐝', '🐛', '🦋', '🐢', '🐍', '🐙',
      '🦑', '🦀', '🐡', '🐠', '🐬', '🐳', '🦈', '🦭',
      '🐊', '🐆', '🦓', '🐘', '🦏', '🦒', '🦘', '🦔'
    ]
  },
  {
    name: '角色奇幻',
    icon: '🧙',
    avatars: [
      '👑', '👸', '🤴', '🦸', '🦸‍♀️', '🦸‍♂️', '🦹', '🦹‍♂️',
      '🧙', '🧙‍♀️', '🧙‍♂️', '🧚', '🧚‍♀️', '🧚‍♂️', '🧝', '🧝‍♀️',
      '🧜', '🧜‍♀️', '🥷', '🧑‍🚀', '🧑‍🔬', '🧑‍🎨', '🧑‍🍳', '🧑‍🚒',
      '🧑‍✈️', '🕵️', '🤖', '👽', '👻', '👾', '🐲', '🐉',
      '🦖', '🦕', '🤠', '🥳', '😎', '🤩', '🧐', '😇'
    ]
  },
  {
    name: '人物家庭',
    icon: '👧',
    avatars: [
      '👧', '👦', '👶', '👨', '👩', '🧑', '👱', '👱‍♀️',
      '👴', '👵', '🧓', '👨‍🦰', '👩‍🦰', '👨‍🦱', '👩‍🦱', '👨‍🦳',
      '👩‍🦳', '🧔', '👳', '🧕', '👨‍👩‍👦', '👨‍👩‍👧', '👨‍👩‍👧‍👦', '👩‍👦',
      '😺', '😸', '😻', '🥰', '🤗', '🤓', '✨', '💖'
    ]
  },
  {
    name: '運動休閒',
    icon: '⚽',
    avatars: [
      '⚽', '🏀', '🏈', '⚾', '🎾', '🏐', '🏓', '🏸',
      '🥊', '🥋', '🛹', '🛴', '🚲', '🏎️', '🏍️', '🧗',
      '🏄', '🏊', '🎿', '🏹', '🎣', '🎯', '🎳', '🎮',
      '🕹️', '🎲', '🧩', '🎨', '🎤', '🎧', '🎸', '🎹',
      '🥁', '🎷', '🎺', '🎻', '🏆', '🥇', '🏅', '🎖️'
    ]
  },
  {
    name: '美食甜點',
    icon: '🍦',
    avatars: [
      '🍦', '🍧', '🍨', '🍩', '🍪', '🎂', '🍰', '🧁',
      '🍫', '🍬', '🍭', '🍮', '🍯', '🍿', '🍕', '🍔',
      '🍟', '🌭', '🥪', '🌮', '🌯', '🍙', '🍣', '🍜',
      '🍝', '🥟', '🍱', '🥞', '🧇', '🍓', '🍉', '🍇',
      '🍎', '🍒', '🍑', '🥭', '🍍', '🍌', '🥑', '🧋'
    ]
  },
  {
    name: '自然宇宙',
    icon: '🚀',
    avatars: [
      '🌟', '⭐', '✨', '⚡', '☄️', '🚀', '🛸', '🪐',
      '☀️', '🌙', '🌌', '🌠', '🌈', '🌤️', '❄️', '🔥',
      '💧', '🌊', '🌋', '🍀', '🌸', '🌺', '🌻', '🌹',
      '🌷', '🍄', '🌲', '🌴', '🍁', '🍂', '💎', '🔮'
    ]
  }
]

const activeAvatarCategory = ref('熱門精選')
const commonAvatars = avatarCategories[0].avatars
const displayedAvatars = computed(() => {
  const cat = avatarCategories.find(c => c.name === activeAvatarCategory.value)
  return cat ? cat.avatars : avatarCategories[0].avatars
})

watch(() => props.show, (newVal) => {
  if (newVal) {
    loadMembers()
    loadCustomAvatars()
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
  originalAvatar.value = '🐸'
  latestUploadedAvatar.value = null
  avatarTab.value = 'frog'
  selectedFile.value = null
  filePreviewUrl.value = ''
  rawImageSrc.value = ''
  showCropper.value = false
  activeAvatarCategory.value = '熱門精選'
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
  originalAvatar.value = member.avatar || '🐸'
  latestUploadedAvatar.value = null
  selectedFile.value = null
  filePreviewUrl.value = ''
  showCropper.value = false
  if (isImageAvatar(avatar.value)) {
    avatarTab.value = avatar.value.includes('/icons/gallery/') ? 'frog' : 'upload'
    rawImageSrc.value = avatar.value.includes('/icons/gallery/') ? '' : avatar.value
  } else {
    avatarTab.value = 'emoji'
    rawImageSrc.value = ''
  }
  const matchedCat = avatarCategories.find(c => c.avatars.includes(avatar.value))
  activeAvatarCategory.value = matchedCat ? matchedCat.name : '熱門精選'
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
      let finalAvatar = avatar.value
      await api.updateMemberAvatar(editingMemberId.value, finalAvatar)
      originalAvatar.value = finalAvatar
      if (authStore.unlockedMemberId === editingMemberId.value) {
        authStore.updateUnlockedMember({ avatar: finalAvatar })
      }
      successMsg.value = `✅ 已成功更換「${name.value}」的代表頭像！`
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
      const created = await api.createMember({
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
      originalAvatar.value = updated.avatar
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
    errorMsg.value = err.message || '儲存成員失敗'
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
      <div v-if="successMsg" class="my-3 p-3 bg-frog-50 text-frog-800 border border-frog-200 rounded-xl text-xs font-semibold">
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
              <MemberAvatar
                :avatar="m.avatar"
                size="lg"
                :alt="m.name"
                class="transition"
                :class="(authStore.isUnlocked && (!authStore.isChild || m.id === authStore.unlockedMemberId)) ? 'hover:scale-110' : ''"
                :title="authStore.isUnlocked ? '點擊更換頭像' : ''"
              />
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

          <!-- 代表頭像自訂設定 (三合一：相片上傳、10 款青蛙、Emoji) -->
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider">
                {{ authStore.isParent ? '代表頭像自訂' : `為「${name}」設定代表頭像` }}
              </label>
              <span class="text-[11px] text-gray-400">支援相片上傳、青蛙公仔與 Emoji</span>
            </div>

            <!-- 當前頭像即時大預覽卡片 -->
            <div class="flex items-center space-x-3.5 p-3.5 bg-frog-50/70 rounded-2xl border border-frog-200/80 mb-3">
              <MemberAvatar :avatar="avatar" size="xl" :alt="name" class="shadow-sm" />
              <div class="flex-1 min-w-0">
                <div class="flex items-center space-x-2">
                  <span class="font-bold text-gray-900 text-sm">目前代表頭像</span>
                  <span class="text-[10px] bg-frog-500 text-white font-bold px-2 py-0.5 rounded-full">即時預覽</span>
                </div>
                <p class="text-xs text-gray-500 mt-0.5 truncate">
                  {{ isImageAvatar(avatar) ? '已選用自訂相片 / 青蛙造型' : `目前 Emoji：${avatar || '🐸'}` }}
                </p>
              </div>
              <button
                v-if="editingMemberId && avatar !== originalAvatar"
                type="button"
                @click="applyAvatar(avatar)"
                :disabled="loading"
                class="px-3 py-1.5 rounded-xl bg-frog-500 hover:bg-frog-600 text-white font-bold text-xs shadow-xs transition cursor-pointer flex-shrink-0 disabled:opacity-50"
              >
                {{ loading ? '套用中...' : '👉 立即套用' }}
              </button>
              <button
                v-if="avatar !== '🐸'"
                type="button"
                @click="avatar = '🐸'; selectedFile = null"
                class="text-xs text-gray-400 hover:text-red-500 transition px-2 py-1 rounded-lg hover:bg-white cursor-pointer"
                title="重設為預設青蛙 Emoji"
              >
                重設
              </button>
            </div>

            <!-- 三合一分頁切換列 -->
            <div class="flex space-x-1.5 p-1 bg-gray-100 rounded-xl mb-3">
              <button
                type="button"
                @click="avatarTab = 'upload'"
                class="flex-1 py-1.5 text-xs font-bold rounded-lg transition flex items-center justify-center space-x-1 cursor-pointer"
                :class="avatarTab === 'upload' ? 'bg-white text-frog-700 shadow-xs' : 'text-gray-500 hover:text-gray-800'"
              >
                <span>📸</span>
                <span>自訂照片上傳</span>
              </button>
              <button
                type="button"
                @click="avatarTab = 'frog'"
                class="flex-1 py-1.5 text-xs font-bold rounded-lg transition flex items-center justify-center space-x-1 cursor-pointer"
                :class="avatarTab === 'frog' ? 'bg-white text-frog-700 shadow-xs' : 'text-gray-500 hover:text-gray-800'"
              >
                <span>🐸</span>
                <span>10 款青蛙公仔</span>
              </button>
              <button
                type="button"
                @click="avatarTab = 'emoji'"
                class="flex-1 py-1.5 text-xs font-bold rounded-lg transition flex items-center justify-center space-x-1 cursor-pointer"
                :class="avatarTab === 'emoji' ? 'bg-white text-frog-700 shadow-xs' : 'text-gray-500 hover:text-gray-800'"
              >
                <span>🎨</span>
                <span>Emoji 選擇庫</span>
              </button>
            </div>

            <!-- 【分頁 1：照片上傳】 -->
            <div v-if="avatarTab === 'upload'" class="space-y-3 p-3 bg-gray-50 rounded-2xl border border-gray-100 mb-2">
              <div
                @click="triggerFileInput"
                class="border-2 border-dashed border-gray-200 hover:border-frog-400 rounded-2xl p-4 text-center cursor-pointer transition bg-white group"
              >
                <input
                  ref="fileInputRef"
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  class="hidden"
                  @change="handleFileSelect"
                />
                <div class="space-y-1.5">
                  <div class="text-3xl group-hover:scale-110 transition-transform">📷</div>
                  <div class="text-xs font-bold text-gray-700">點擊選取相簿照片或大頭貼</div>
                  <div class="text-[11px] text-gray-400">支援 JPG、PNG、WebP，系統將自動居中圓形裁切與壓製 (上限 5MB)</div>
                </div>
              </div>

              <!-- 上傳處理中提示 -->
              <div v-if="uploading" class="p-3 bg-frog-50 border border-frog-200 rounded-xl text-center text-xs font-bold text-frog-700 flex items-center justify-center space-x-2">
                <span class="animate-spin text-base">⏳</span>
                <span>裁切相片壓製中，正在加入自訂相片庫...</span>
              </div>

              <!-- 剛裁切完成之相片 (已加入相片庫，尚未套用 / 已套用) -->
              <div v-if="latestUploadedAvatar" class="p-3 bg-white rounded-xl border-2 transition shadow-xs" :class="avatar === latestUploadedAvatar.url ? 'border-frog-500 bg-frog-50/40' : 'border-frog-200'">
                <div class="flex items-center justify-between gap-2">
                  <div class="flex items-center space-x-2.5 min-w-0">
                    <img :src="latestUploadedAvatar.url" class="w-12 h-12 rounded-full object-cover border-2 border-frog-400 shadow-xs flex-shrink-0" />
                    <div class="min-w-0 text-xs text-left">
                      <div class="font-bold text-gray-800 flex items-center space-x-1.5">
                        <span>剛裁切完成之相片</span>
                        <span class="text-[10px] text-gray-400 font-normal">({{ latestUploadedAvatar.size_kb }} KB)</span>
                      </div>
                      <div class="text-[11px] font-semibold mt-0.5">
                        <span v-if="avatar === latestUploadedAvatar.url" class="text-frog-600 flex items-center space-x-1">
                          <span>✓</span>
                          <span>目前已套用為此成員代表頭像</span>
                        </span>
                        <span v-else class="text-amber-600">
                          已加入相片庫（尚未套用）
                        </span>
                      </div>
                    </div>
                  </div>

                  <div class="flex items-center space-x-1.5 flex-shrink-0">
                    <!-- 重新微調裁切按鈕 -->
                    <button
                      v-if="rawImageSrc"
                      type="button"
                      @click="showCropper = true"
                      class="px-2.5 py-1.5 rounded-lg border border-gray-200 hover:border-frog-400 bg-gray-50 hover:bg-frog-50/50 text-gray-700 hover:text-frog-700 font-bold text-xs shadow-2xs transition flex items-center space-x-1 cursor-pointer"
                      title="調整 ROI 圓圈位置與放大縮小"
                    >
                      <span>✂️</span>
                      <span>微調</span>
                    </button>

                    <!-- 立即套用按鈕 -->
                    <button
                      v-if="avatar !== latestUploadedAvatar.url"
                      type="button"
                      @click="applyAvatar(latestUploadedAvatar.url)"
                      :disabled="loading"
                      class="px-3.5 py-1.5 rounded-lg bg-frog-500 hover:bg-frog-600 text-white font-bold text-xs shadow-xs transition flex-shrink-0 cursor-pointer disabled:opacity-50"
                    >
                      {{ loading ? '套用中...' : '👉 立即套用' }}
                    </button>
                    <span v-else class="px-2.5 py-1.5 rounded-lg bg-frog-100 text-frog-800 font-bold text-xs">
                      已套用
                    </span>
                  </div>
                </div>
              </div>

              <!-- 已儲存之自訂頭像庫 (上限 100 個) -->
              <div class="space-y-2 pt-2 border-t border-gray-200/60">
                <div class="flex items-center justify-between text-xs font-bold text-gray-700">
                  <span class="flex items-center space-x-1.5">
                    <span>🖼️</span>
                    <span>已儲存的自訂相片庫</span>
                  </span>
                  <span class="font-mono text-[11px]" :class="customAvatarsCount >= 100 ? 'text-red-600 font-black' : 'text-gray-400'">
                    {{ customAvatarsCount }} / {{ customAvatarsMax }} 張
                  </span>
                </div>

                <!-- 達到 100 個上限警告 -->
                <div v-if="customAvatarsCount >= 100" class="p-2 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-[11px] font-semibold text-left">
                  ⚠️ 已達 100 個儲存上限！請點選右上角 ✕ 刪除不需要的舊頭像以釋出空間。
                </div>

                <!-- 頭像清單 (縮圖網格) -->
                <div v-if="customAvatars.length > 0" class="grid grid-cols-4 sm:grid-cols-5 gap-2 max-h-48 overflow-y-auto pr-1 p-1">
                  <div
                    v-for="item in customAvatars"
                    :key="item.filename"
                    class="relative group rounded-2xl border-2 transition overflow-hidden cursor-pointer aspect-square"
                    :class="avatar === item.url ? 'border-frog-500 ring-2 ring-frog-400/40 shadow-xs scale-102' : 'border-gray-200 hover:border-gray-300 bg-white'"
                    @click="avatar = item.url; selectedFile = null"
                    :title="`點擊套用此頭像 (${item.size_kb} KB)`"
                  >
                    <img :src="item.url" class="w-full h-full object-cover" />

                    <!-- 當前選取勾勾標記 -->
                    <div v-if="avatar === item.url" class="absolute top-1 left-1 bg-frog-500 text-white w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold shadow-xs">
                      ✓
                    </div>

                    <!-- 刪除按鈕 (手機一律可見，電腦 Hover 顯示) -->
                    <button
                      type="button"
                      @click.stop="handleDeleteCustomAvatar(item)"
                      class="absolute top-1 right-1 w-5 h-5 bg-black/60 hover:bg-red-600 active:bg-red-700 text-white rounded-full flex items-center justify-center text-[10px] font-bold transition opacity-80 sm:opacity-0 sm:group-hover:opacity-100 cursor-pointer shadow-xs"
                      title="從頭像庫永久刪除此相片"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                <div v-else class="text-center py-4 text-xs text-gray-400 bg-white rounded-2xl border border-dashed border-gray-200">
                  尚無儲存的自訂頭像，每次上傳裁切後皆會自動保存於此（上限 100 張）
                </div>
              </div>
            </div>

            <!-- 【分頁 2：10 款青蛙公仔庫】 -->
            <div v-else-if="avatarTab === 'frog'" class="space-y-2 p-3 bg-gray-50 rounded-2xl border border-gray-100 mb-2">
              <div class="text-[11px] text-gray-500 mb-1">
                點選以下任一原創 3D 青蛙造型，立即設為個人代表頭像：
              </div>
              <div class="grid grid-cols-2 sm:grid-cols-5 gap-2 max-h-56 overflow-y-auto pr-1">
                <button
                  v-for="frog in themeStore.logoIcons"
                  :key="frog.id"
                  type="button"
                  @click="avatar = frog.src; selectedFile = null"
                  class="p-2 rounded-xl border-2 transition text-center flex flex-col items-center space-y-1 cursor-pointer"
                  :class="avatar === frog.src ? 'border-frog-500 bg-frog-50 shadow-xs' : 'border-gray-200 bg-white hover:border-gray-300'"
                >
                  <img :src="frog.src" :alt="frog.name" class="w-11 h-11 rounded-xl object-cover shadow-xs" />
                  <span class="text-[10px] font-bold text-gray-800 truncate w-full">{{ frog.name }}</span>
                </button>
              </div>
            </div>

            <!-- 【分頁 3：Emoji 選擇庫與自訂輸入】 -->
            <div v-else class="space-y-2.5 mb-2">
              <div class="flex items-center space-x-2">
                <input
                  v-model="avatar"
                  type="text"
                  maxlength="20"
                  placeholder="或直接鍵盤輸入任意 Emoji / 字母符號"
                  class="flex-1 px-3 py-2 rounded-xl border border-gray-200 bg-white text-xs font-medium focus:outline-none focus:border-frog-500 focus:ring-1 focus:ring-frog-200"
                />
              </div>

              <!-- 分類標籤切換列 -->
              <div class="flex items-center space-x-1.5 overflow-x-auto pb-1">
                <button
                  v-for="cat in avatarCategories"
                  :key="cat.name"
                  type="button"
                  @click="activeAvatarCategory = cat.name"
                  class="px-2.5 py-1 rounded-xl text-xs font-bold transition flex items-center space-x-1 flex-shrink-0 cursor-pointer"
                  :class="activeAvatarCategory === cat.name
                    ? 'bg-frog-500 text-white shadow-xs'
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-600'"
                >
                  <span>{{ cat.icon }}</span>
                  <span>{{ cat.name }}</span>
                </button>
              </div>

              <!-- Emoji 方格選擇區 -->
              <div class="flex flex-wrap gap-2 p-3 bg-gray-50 rounded-2xl border border-gray-100 max-h-44 overflow-y-auto">
                <button
                  v-for="av in displayedAvatars"
                  :key="av"
                  type="button"
                  @click="avatar = av; selectedFile = null"
                  class="w-10 h-10 rounded-xl flex items-center justify-center text-2xl transition hover:scale-110 cursor-pointer"
                  :class="avatar === av ? 'bg-frog-200 ring-2 ring-frog-500 shadow-inner' : 'hover:bg-white bg-white/70 shadow-xs'"
                >
                  {{ av }}
                </button>
              </div>
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

  <!-- 圓形 ROI 頭像相片互動式裁切器 -->
  <AvatarCropperModal
    :show="showCropper"
    :image-src="rawImageSrc"
    @close="showCropper = false"
    @crop="handleCropped"
  />
</template>
