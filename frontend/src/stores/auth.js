import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const SESSION_KEY = 'frog_kudos_auth'

function readSession() {
  try {
    if (typeof sessionStorage === 'undefined') return null
    const raw = sessionStorage.getItem(SESSION_KEY)
    if (!raw) return null
    return JSON.parse(raw)
  } catch (e) {
    console.error('Failed to read auth session:', e)
    return null
  }
}

function writeSession(data) {
  try {
    if (typeof sessionStorage === 'undefined') return
    if (data) {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(data))
    } else {
      sessionStorage.removeItem(SESSION_KEY)
    }
  } catch (e) {
    console.error('Failed to write auth session:', e)
  }
}

export const useAuthStore = defineStore('auth', () => {
  // 15 分鐘無操作自動安全鎖定 (FR-13)
  const IDLE_TIMEOUT_MS = 15 * 60 * 1000 // 15 分鐘

  const initialSession = readSession()
  const initialElapsed = initialSession?.lastActiveTime ? (Date.now() - initialSession.lastActiveTime) : Infinity
  const isSessionValid = Boolean(
    initialSession &&
    (initialSession.unlockedMember || initialSession.isParent) &&
    (initialSession.sessionToken || initialSession.parentPin) &&
    initialElapsed < IDLE_TIMEOUT_MS
  )

  // 解鎖成員資訊 (含 id, name, role: 'parent' | 'child', avatar)
  let initialMember = null
  if (isSessionValid) {
    if (initialSession.unlockedMember) {
      initialMember = initialSession.unlockedMember
    } else if (initialSession.isParent) {
      initialMember = {
        id: initialSession.selectedMemberId || null,
        name: '家長',
        role: 'parent',
        avatar: '👑',
      }
    }
  }

  const unlockedMember = ref(initialMember)
  const isUnlocked = computed(() => Boolean(unlockedMember.value))
  const isParent = computed(() => unlockedMember.value?.role === 'parent')
  const isChild = computed(() => unlockedMember.value?.role === 'child')
  const unlockedMemberId = computed(() => unlockedMember.value?.id || null)

  // 此瀏覽器專屬之獨立 Session Token 與 PIN 碼
  const sessionToken = ref(isSessionValid ? (initialSession.sessionToken || '') : '')
  const parentPin = ref(isSessionValid ? (initialSession.parentPin || '') : '')

  // 目前選取的成員 (若為小孩解鎖模式，強制鎖定為該小孩)
  const selectedMemberId = ref(
    initialMember?.role === 'child' && initialMember.id
      ? initialMember.id
      : (initialSession?.selectedMemberId || null)
  )

  const lastActiveTime = ref(isSessionValid ? initialSession.lastActiveTime : Date.now())
  const remainingSeconds = ref(
    isSessionValid
      ? Math.max(0, Math.floor((IDLE_TIMEOUT_MS - initialElapsed) / 1000))
      : 15 * 60
  )

  let timerInterval = null
  let eventListenersAttached = false

  function persistSession() {
    if (isUnlocked.value) {
      writeSession({
        unlockedMember: unlockedMember.value,
        isParent: isParent.value,
        sessionToken: sessionToken.value,
        parentPin: parentPin.value,
        lastActiveTime: lastActiveTime.value,
        selectedMemberId: selectedMemberId.value,
      })
    } else {
      writeSession(selectedMemberId.value ? { selectedMemberId: selectedMemberId.value } : null)
    }
  }

  function resetIdleTimer() {
    lastActiveTime.value = Date.now()
    remainingSeconds.value = Math.floor(IDLE_TIMEOUT_MS / 1000)
    persistSession()
  }

  function startIdleMonitor() {
    if (timerInterval) clearInterval(timerInterval)

    const updateTimer = () => {
      if (!isUnlocked.value) return
      const elapsed = Date.now() - lastActiveTime.value
      const remain = Math.max(0, Math.floor((IDLE_TIMEOUT_MS - elapsed) / 1000))
      remainingSeconds.value = remain

      if (elapsed >= IDLE_TIMEOUT_MS) {
        lock()
      }
    }

    timerInterval = setInterval(updateTimer, 1000)

    // 監聽使用者互動事件以重設閒置時間 (加入 5 秒節流避免頻繁寫入 sessionStorage)
    if (!eventListenersAttached && typeof window !== 'undefined') {
      eventListenersAttached = true
      let lastPersist = 0
      const onUserInteraction = () => {
        if (isUnlocked.value) {
          const now = Date.now()
          lastActiveTime.value = now
          if (now - lastPersist > 5000) {
            lastPersist = now
            persistSession()
          }
        }
      }
      const events = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll']
      events.forEach(evt => {
        window.addEventListener(evt, onUserInteraction, { passive: true })
      })
    }
  }

  // 若網頁重新整理時仍處於有效 Session 期間，自動重啟閒置計時器
  if (isSessionValid) {
    startIdleMonitor()
  }

  function unlock(member, token = '', pin = '') {
    const memObj = {
      id: member.id || member.member_id || null,
      name: member.name || member.member_name || (member.role === 'parent' ? '家長' : '小孩'),
      role: member.role || 'parent',
      avatar: member.avatar || member.member_avatar || (member.role === 'parent' ? '👑' : '👦'),
    }
    unlockedMember.value = memObj
    sessionToken.value = token
    parentPin.value = pin

    // 若為小孩模式，強制切換並鎖定目前選取之成員
    if (memObj.role === 'child' && memObj.id) {
      selectedMemberId.value = memObj.id
    }

    resetIdleTimer()
    startIdleMonitor()
  }

  function unlockParent(pin, token = '', member = null) {
    unlock(
      member || { id: null, name: '家長', role: 'parent', avatar: '👑' },
      token,
      pin
    )
  }

  function lock() {
    const tokenToRevoke = sessionToken.value
    unlockedMember.value = null
    sessionToken.value = ''
    parentPin.value = ''
    persistSession()
    if (timerInterval) {
      clearInterval(timerInterval)
      timerInterval = null
    }
    // 非同步通知伺服器端註銷該瀏覽器會話 (各瀏覽器獨立銷毀)
    if (tokenToRevoke && typeof fetch !== 'undefined') {
      fetch('/api/system/lock-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_token: tokenToRevoke }),
      }).catch(() => {})
    }
  }

  function lockParent() {
    lock()
  }

  function setSelectedMemberId(id) {
    // 若為小孩解鎖模式，禁止切換成其他成員
    if (isChild.value && unlockedMemberId.value) {
      selectedMemberId.value = unlockedMemberId.value
      persistSession()
      return
    }
    selectedMemberId.value = id
    persistSession()
  }

  const remainingMinutesFormatted = computed(() => {
    const mins = Math.floor(remainingSeconds.value / 60)
    const secs = remainingSeconds.value % 60
    return `${mins}分${secs < 10 ? '0' : ''}${secs}秒`
  })

  // 全域成員異動更新觸發計數器 (FR-2 / FR-13)
  const memberRefreshKey = ref(0)
  function triggerMemberRefresh() {
    memberRefreshKey.value++
  }

  function updateUnlockedMember(patch) {
    if (unlockedMember.value) {
      unlockedMember.value = { ...unlockedMember.value, ...patch }
      persistSession()
    }
  }

  return {
    unlockedMember,
    isUnlocked,
    isParent,
    isChild,
    unlockedMemberId,
    sessionToken,
    parentPin,
    selectedMemberId,
    remainingSeconds,
    remainingMinutesFormatted,
    memberRefreshKey,
    unlock,
    unlockParent,
    lock,
    lockParent,
    resetIdleTimer,
    setSelectedMemberId,
    triggerMemberRefresh,
    updateUnlockedMember,
  }
})
