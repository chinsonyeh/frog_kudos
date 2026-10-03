import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  // 家長鎖解鎖狀態與 PIN 碼
  const isParent = ref(false)
  const parentPin = ref('')

  // 目前選取的成員
  const selectedMemberId = ref(null)

  // 15 分鐘無操作自動安全鎖定 (FR-13)
  const IDLE_TIMEOUT_MS = 15 * 60 * 1000 // 15 分鐘
  const lastActiveTime = ref(Date.now())
  const remainingSeconds = ref(15 * 60)

  let timerInterval = null

  function resetIdleTimer() {
    lastActiveTime.value = Date.now()
    remainingSeconds.value = Math.floor(IDLE_TIMEOUT_MS / 1000)
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

    // 監聽使用者互動事件
    const events = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll']
    events.forEach(evt => {
      window.addEventListener(evt, () => {
        if (isParent.value) {
          lastActiveTime.value = Date.now()
        }
      }, { passive: true })
    })
  }

  function unlockParent(pin) {
    isParent.value = true
    parentPin.value = pin
    resetIdleTimer()
    startIdleMonitor()
  }

  function lockParent() {
    isParent.value = false
    parentPin.value = ''
    if (timerInterval) {
      clearInterval(timerInterval)
      timerInterval = null
    }
  }

  function setSelectedMemberId(id) {
    selectedMemberId.value = id
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
