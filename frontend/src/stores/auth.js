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
    initialSession.isParent &&
    (initialSession.sessionToken || initialSession.parentPin) &&
    initialElapsed < IDLE_TIMEOUT_MS
  )

  // 家長鎖解鎖狀態、此瀏覽器專屬之獨立 Session Token 與 PIN 碼
  const isParent = ref(isSessionValid)
  const sessionToken = ref(isSessionValid ? (initialSession.sessionToken || '') : '')
  const parentPin = ref(isSessionValid ? (initialSession.parentPin || '') : '')

  // 目前選取的成員
  const selectedMemberId = ref(initialSession?.selectedMemberId || null)

  const lastActiveTime = ref(isSessionValid ? initialSession.lastActiveTime : Date.now())
  const remainingSeconds = ref(
    isSessionValid
      ? Math.max(0, Math.floor((IDLE_TIMEOUT_MS - initialElapsed) / 1000))
      : 15 * 60
  )

  let timerInterval = null
  let eventListenersAttached = false

  function persistSession() {
    if (isParent.value) {
      writeSession({
        isParent: true,
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
      if (!isParent.value) return
      const elapsed = Date.now() - lastActiveTime.value
      const remain = Math.max(0, Math.floor((IDLE_TIMEOUT_MS - elapsed) / 1000))
      remainingSeconds.value = remain

      if (elapsed >= IDLE_TIMEOUT_MS) {
        lockParent()
      }
    }

    timerInterval = setInterval(updateTimer, 1000)

    // 監聽使用者互動事件以重設閒置時間
    if (!eventListenersAttached && typeof window !== 'undefined') {
      eventListenersAttached = true
      const events = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll']
      events.forEach(evt => {
        window.addEventListener(evt, () => {
          if (isParent.value) {
            lastActiveTime.value = Date.now()
            persistSession()
          }
        }, { passive: true })
      })
    }
  }

  // 若網頁重新整理時仍處於有效 Session 期間，自動重啟閒置計時器
  if (isSessionValid) {
    startIdleMonitor()
  }

  function unlockParent(pin, token = '') {
    isParent.value = true
    parentPin.value = pin
    sessionToken.value = token
    resetIdleTimer()
    startIdleMonitor()
  }

  function lockParent() {
    const tokenToRevoke = sessionToken.value
    isParent.value = false
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

  function setSelectedMemberId(id) {
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

  return {
    isParent,
    sessionToken,
    parentPin,
    selectedMemberId,
    remainingSeconds,
    remainingMinutesFormatted,
    memberRefreshKey,
    unlockParent,
    lockParent,
    resetIdleTimer,
    setSelectedMemberId,
    triggerMemberRefresh,
  }
})
