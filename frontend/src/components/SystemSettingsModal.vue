<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  show: Boolean,
})
const emit = defineEmits(['close'])

const authStore = useAuthStore()
const activeTab = ref('backup') // 'backup' | 'version' | 'line'

// Tab 1: 備份
const backupDir = ref('')
const autoBackup = ref(true)
const retentionCount = ref(10)
const backupsList = ref([])
const backupLoading = ref(false)
const backupSuccessMsg = ref('')

// Tab 2: 版本與升級
const versionInfo = ref({ current_version: 'v1.0.1', latest_version: null, has_update: false, release_notes: '', download_url: null })
const checkingVersion = ref(false)
const upgrading = ref(false)
const upgradeStatus = ref({ status: 'IDLE', progress: 0, current_step: '待命中', logs: [] })
let pollInterval = null
const offlineFile = ref(null)

// Tab 3: LINE
const lineToken = ref('')
const lineUserId = ref('')
const lineLoading = ref(false)
const lineTestMsg = ref('')

const error = ref('')

watch(
  () => props.show,
  async (newVal) => {
    if (newVal) {
      await loadInitialData()
    } else {
      if (pollInterval) {
        clearInterval(pollInterval)
        pollInterval = null
      }
    }
  },
  { immediate: true }
)

async function loadInitialData() {
  error.value = ''
  try {
    const cfg = await api.getSystemConfig()
    backupDir.value = cfg.backup_dir
    autoBackup.value = cfg.auto_backup
    retentionCount.value = cfg.retention_count
    lineUserId.value = cfg.line_user_id || ''

    await loadBackups()
    await checkVersion()
  } catch (err) {
    error.value = err.message || '載入設定失敗'
  }
}

async function loadBackups() {
  try {
    backupsList.value = await api.getBackups(backupDir.value)
  } catch (err) {
    console.error('載入備份清單失敗', err)
  }
}

async function handleSaveBackupConfig() {
  error.value = ''
  try {
    await api.saveSystemConfig({
      backup_dir: backupDir.value,
      auto_backup: autoBackup.value,
      retention_count: parseInt(retentionCount.value, 10),
    })
    backupSuccessMsg.value = '備份設定已儲存！'
    setTimeout(() => { backupSuccessMsg.value = '' }, 3000)
    await loadBackups()
  } catch (err) {
    error.value = err.message || '儲存失敗'
  }
}

async function handleTriggerBackup() {
  backupLoading.value = true
  error.value = ''
  try {
    const res = await api.triggerBackup({ target_path: backupDir.value })
    backupSuccessMsg.value = `✅ 備份成功！檔案: ${res.backup_file} (${res.file_size})`
    await loadBackups()
  } catch (err) {
    error.value = err.message || '立即備份失敗'
  } finally {
    backupLoading.value = false
  }
}

async function checkVersion() {
  checkingVersion.value = true
  try {
    versionInfo.value = await api.getVersion()
  } catch (err) {
    console.error('檢查版本失敗', err)
  } finally {
    checkingVersion.value = false
  }
}

function startPollingUpgrade() {
  upgrading.value = true
  if (pollInterval) clearInterval(pollInterval)
  pollInterval = setInterval(async () => {
    try {
      const st = await api.getUpgradeStatus()
      upgradeStatus.value = st
      if (st.status === 'COMPLETED' || st.status === 'FAILED') {
        clearInterval(pollInterval)
        pollInterval = null
        upgrading.value = false
      }
    } catch {
      // 升級伺服器重啟中可能短暫斷線
    }
  }, 1000)
}

async function handleAutoUpgrade() {
  error.value = ''
  try {
    await api.triggerUpgrade({ package_url: versionInfo.value.download_url })
    startPollingUpgrade()
  } catch (err) {
    error.value = err.message || '啟動自動升級失敗'
  }
}

async function handleUploadPackage(e) {
  const file = e.target.files[0]
  if (!file) return
  error.value = ''
  const fd = new FormData()
  fd.append('file', file)
  if (authStore.parentPin) fd.append('parent_pin', authStore.parentPin)

  try {
    await api.uploadPackage(fd)
    startPollingUpgrade()
  } catch (err) {
    error.value = err.message || '上傳升級套件失敗'
  }
}

async function handleSaveLineConfig() {
  error.value = ''
  try {
    await api.saveSystemConfig({
      line_channel_access_token: lineToken.value || undefined,
      line_user_id: lineUserId.value,
    })
    lineTestMsg.value = 'LINE 通知設定已更新儲存！'
    setTimeout(() => { lineTestMsg.value = '' }, 3000)
  } catch (err) {
    error.value = err.message || '儲存 LINE 設定失敗'
  }
}

async function handleTestLine() {
  lineLoading.value = true
  lineTestMsg.value = ''
  error.value = ''
  try {
    const res = await api.testLine()
    lineTestMsg.value = res.success ? `✅ ${res.message}` : `❌ ${res.message}`
  } catch (err) {
    error.value = err.message || '測試失敗'
  } finally {
    lineLoading.value = false
  }
}

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
    <div class="bg-white rounded-3xl shadow-2xl max-w-2xl w-full p-6 sm:p-8 max-h-[90vh] flex flex-col">
      <!-- 頂部標題與關閉按鈕 -->
      <div class="flex items-center justify-between pb-4 border-b border-gray-100 flex-shrink-0">
        <div class="flex items-center space-x-2">
          <span class="text-2xl">⚙️</span>
          <h3 class="text-lg font-bold text-gray-900">系統設定與維運中心 (家長專區)</h3>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 text-xl font-bold">
          ✕
        </button>
      </div>

      <!-- 分頁切換選單 -->
      <div class="flex space-x-2 border-b border-gray-100 py-3 flex-shrink-0">
        <button
          @click="activeTab = 'backup'"
          class="px-4 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-1.5"
          :class="activeTab === 'backup' ? 'bg-frog-50 text-frog-700 shadow-sm border border-frog-200' : 'text-gray-500 hover:bg-gray-50'"
        >
          <span>💾</span>
          <span>資料庫備份與管理</span>
        </button>
        <button
          @click="activeTab = 'version'"
          class="px-4 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-1.5"
          :class="activeTab === 'version' ? 'bg-frog-50 text-frog-700 shadow-sm border border-frog-200' : 'text-gray-500 hover:bg-gray-50'"
        >
          <span>🔄</span>
          <span>系統版本與升級</span>
        </button>
        <button
          @click="activeTab = 'line'"
          class="px-4 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-1.5"
          :class="activeTab === 'line' ? 'bg-frog-50 text-frog-700 shadow-sm border border-frog-200' : 'text-gray-500 hover:bg-gray-50'"
        >
          <span>📱</span>
          <span>LINE 即時推播通知</span>
        </button>
      </div>

      <!-- 分頁內容區 -->
      <div class="flex-1 overflow-y-auto py-4 space-y-6">
        <!-- 錯誤提示 -->
        <div v-if="error" class="p-3 bg-red-50 text-red-600 rounded-xl text-xs font-semibold">
          {{ error }}
        </div>

        <!-- 【分頁 1: 資料庫備份與管理】 -->
        <div v-if="activeTab === 'backup'" class="space-y-6">
          <div class="space-y-4">
            <div>
              <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
                1. 自訂備份目的地路徑 (支援隨身碟或 NAS 路徑)
              </label>
              <div class="flex space-x-2">
                <input
                  v-model="backupDir"
                  type="text"
                  class="flex-1 px-3.5 py-2 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white text-xs font-mono"
                />
                <button
                  @click="handleSaveBackupConfig"
                  class="px-4 py-2 rounded-xl bg-gray-100 hover:bg-gray-200 text-xs font-bold text-gray-700 transition"
                >
                  儲存路徑
                </button>
              </div>
            </div>

            <!-- 立即備份按鈕 -->
            <div class="p-4 rounded-2xl bg-frog-50/50 border border-frog-100 flex items-center justify-between">
              <div>
                <h5 class="text-sm font-bold text-frog-900">立即建立資料庫完整備份</h5>
                <p class="text-xs text-frog-700 mt-0.5">採用 PostgreSQL Custom Dump 高壓縮格式</p>
              </div>
              <button
                @click="handleTriggerBackup"
                :disabled="backupLoading"
                class="px-4 py-2.5 rounded-xl bg-frog-500 hover:bg-frog-600 text-white font-bold text-xs shadow-md transition disabled:opacity-50"
              >
                {{ backupLoading ? '備份中...' : '📦 立即備份' }}
              </button>
            </div>

            <div v-if="backupSuccessMsg" class="p-3 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-xl text-xs font-semibold">
              {{ backupSuccessMsg }}
            </div>

            <!-- 自動排程與保留輪替 -->
            <div class="p-4 rounded-2xl bg-gray-50 border border-gray-200 space-y-3">
              <h5 class="text-xs font-bold text-gray-800 uppercase tracking-wider">定期自動備份與保留輪替 (FR-16)</h5>
              <div class="flex items-center justify-between text-xs">
                <span>每週日深夜 02:00 自動備份：</span>
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" v-model="autoBackup" class="sr-only peer" />
                  <div class="w-10 h-5 bg-gray-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-frog-500"></div>
                </label>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span>保留備份份數上限 (超過時自動清理舊備份)：</span>
                <input
                  v-model="retentionCount"
                  type="number"
                  min="1"
                  max="100"
                  class="w-20 px-2 py-1 border rounded-lg text-center font-bold"
                />
              </div>
              <button
                @click="handleSaveBackupConfig"
                class="w-full py-2 bg-white hover:bg-gray-100 border border-gray-300 text-gray-700 font-bold text-xs rounded-xl transition"
              >
                儲存排程與保留設定
              </button>
            </div>

            <!-- 歷史備份清單 -->
            <div>
              <h5 class="text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">歷史備份清單 (最新 10 筆)</h5>
              <div v-if="backupsList.length === 0" class="p-4 text-center text-xs text-gray-400 bg-gray-50 rounded-xl">
                目前尚無歷史備份檔案
              </div>
              <div v-else class="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                <div
                  v-for="b in backupsList"
                  :key="b.filename"
                  class="flex items-center justify-between p-2 rounded-lg bg-gray-50 border border-gray-100 text-xs"
                >
                  <span class="font-mono text-gray-700 truncate max-w-[280px]" :title="b.path">
                    📄 {{ b.filename }}
                  </span>
                  <span class="text-gray-500 font-semibold">{{ b.size }}</span>
                </div>
              </div>
              <p class="text-[11px] text-gray-500 mt-2">
                💡 還原指引：為保證資料安全，請於伺服器終端機執行: <code class="bg-gray-100 px-1 py-0.5 rounded text-gray-800">./scripts/restore.sh &lt;備份檔絕對路徑&gt;</code>
              </p>
            </div>
          </div>
        </div>

        <!-- 【分頁 2: 系統版本與升級】 -->
        <div v-if="activeTab === 'version'" class="space-y-6">
          <div class="p-4 rounded-2xl bg-gray-50 border border-gray-200">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs text-gray-500 font-bold uppercase">目前安裝版本</span>
              <span class="font-mono font-bold text-sm bg-frog-100 text-frog-800 px-2 py-0.5 rounded-lg">
                {{ versionInfo.current_version }}
              </span>
            </div>
            <div class="flex items-center justify-between text-xs text-gray-600">
              <span>GitHub 儲存庫:</span>
              <a href="https://github.com/chinsonyeh/frog_kudos" target="_blank" class="text-frog-600 hover:underline">
                chinsonyeh/frog_kudos
              </a>
            </div>
            <button
              @click="checkVersion"
              :disabled="checkingVersion"
              class="w-full mt-3 py-2 bg-white hover:bg-gray-100 border border-gray-300 text-gray-700 font-bold text-xs rounded-xl transition"
            >
              {{ checkingVersion ? '連線檢查中...' : '🔍 檢查 GitHub 最新 Release' }}
            </button>
          </div>

          <!-- 新版本提示 -->
          <div v-if="versionInfo.has_update" class="p-4 rounded-2xl bg-amber-50 border border-amber-200 space-y-3">
            <div class="flex items-center space-x-2 text-amber-900 font-bold text-sm">
              <span>🚀 發現新發行版本：{{ versionInfo.latest_version }}</span>
            </div>
            <div class="text-xs text-amber-800 bg-white/80 p-3 rounded-xl max-h-32 overflow-y-auto whitespace-pre-wrap font-mono">
              {{ versionInfo.release_notes || '包含最新功能修復與穩定度改進' }}
            </div>
            <button
              @click="handleAutoUpgrade"
              :disabled="upgrading"
              class="w-full py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-bold text-xs shadow-md transition"
            >
              🚀 立即從 GitHub 自動平滑升級
            </button>
          </div>

          <!-- 離線套件上傳 -->
          <div class="p-4 rounded-2xl bg-gray-50 border border-gray-200">
            <h5 class="text-xs font-bold text-gray-800 uppercase tracking-wider mb-2">離線套件手動升級 (.tar.gz)</h5>
            <input
              type="file"
              accept=".tar.gz"
              @change="handleUploadPackage"
              class="text-xs text-gray-500 file:mr-3 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-frog-50 file:text-frog-700 hover:file:bg-frog-100"
            />
          </div>

          <!-- 升級進度顯示 -->
          <div v-if="upgrading || upgradeStatus.status !== 'IDLE'" class="p-4 rounded-2xl bg-gray-900 text-white space-y-3">
            <div class="flex items-center justify-between text-xs font-bold">
              <span>升級進度: {{ upgradeStatus.current_step }}</span>
              <span class="font-mono">{{ upgradeStatus.progress }}%</span>
            </div>
            <div class="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
              <div class="bg-frog-500 h-2 rounded-full transition-all duration-300" :style="{ width: `${upgradeStatus.progress}%` }"></div>
            </div>
            <div class="max-h-28 overflow-y-auto text-[11px] font-mono text-gray-300 space-y-0.5">
              <div v-for="(log, idx) in upgradeStatus.logs" :key="idx">{{ log }}</div>
            </div>
          </div>
        </div>

        <!-- 【分頁 3: LINE 即時推播通知】 -->
        <div v-if="activeTab === 'line'" class="space-y-4">
          <div class="p-3 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-xl text-xs">
            📱 設定 LINE Messaging API 憑證，當孩子在商城申請兌換時，系統將即時發送推播通知至家長手機。
          </div>

          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              LINE Channel Access Token
            </label>
            <input
              v-model="lineToken"
              type="password"
              placeholder="貼上 LINE Official Account Channel Access Token"
              class="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 bg-gray-50 text-xs font-mono focus:bg-white focus:ring-2 focus:ring-frog-500"
            />
          </div>

          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              家長 LINE User ID (例如: U1234567890abcdef...)
            </label>
            <input
              v-model="lineUserId"
              type="text"
              placeholder="LINE 開發者後台可查詢的 User ID"
              class="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 bg-gray-50 text-xs font-mono focus:bg-white focus:ring-2 focus:ring-frog-500"
            />
          </div>

          <div v-if="lineTestMsg" class="p-3 bg-gray-100 rounded-xl text-xs font-semibold text-gray-800">
            {{ lineTestMsg }}
          </div>

          <div class="flex space-x-3 pt-2">
            <button
              @click="handleSaveLineConfig"
              class="flex-1 py-2.5 rounded-xl bg-frog-500 hover:bg-frog-600 text-white font-bold text-xs shadow-md transition"
            >
              💾 儲存通知設定
            </button>
            <button
              @click="handleTestLine"
              :disabled="lineLoading"
              class="flex-1 py-2.5 rounded-xl border border-frog-400 bg-frog-50 text-frog-700 hover:bg-frog-100 font-bold text-xs transition"
            >
              {{ lineLoading ? '發送中...' : '📨 發送測試訊息' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 底部關閉按鈕 -->
      <div class="pt-4 border-t border-gray-100 flex-shrink-0">
        <button
          @click="$emit('close')"
          class="w-full py-2.5 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold text-sm transition"
        >
          關閉
        </button>
      </div>
    </div>
  </div>
</template>
