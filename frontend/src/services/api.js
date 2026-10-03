import { useAuthStore } from '@/stores/auth'

const BASE_URL = '/api'

async function request(endpoint, options = {}) {
  const authStore = useAuthStore()
  const headers = { ...options.headers }

  // 如果為家長模式且有 PIN 碼，自動附加 X-Parent-PIN Header
  if (authStore.isParent && authStore.parentPin) {
    headers['X-Parent-PIN'] = authStore.parentPin
  }

  // 判斷是否為 FormData (檔案上傳)
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  const config = {
    ...options,
    headers,
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, config)

  if (!response.ok) {
    let errorDetail = '請求失敗'
    try {
      const errorJson = await response.json()
      errorDetail = errorJson.detail || errorJson.message || JSON.stringify(errorJson)
    } catch {
      errorDetail = await response.text()
    }
    throw new Error(errorDetail)
  }

  // 支援二進位下載 (CSV 等)
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('text/csv') || contentType.includes('application/octet-stream')) {
    return await response.blob()
  }

  return await response.json()
}

export const api = {
  // 成員管理
  getMembers: (includeInactive = false) =>
    request(`/members?include_inactive=${includeInactive}`),
  createMember: (data) =>
    request('/members', { method: 'POST', body: JSON.stringify(data) }),
  updateMember: (id, data) =>
    request(`/members/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  updateMemberAvatar: (id, avatar) =>
    request(`/members/${id}/avatar`, { method: 'PATCH', body: JSON.stringify({ avatar }) }),
  changeMemberPin: (id, data) =>
    request(`/members/${id}/change-pin`, { method: 'POST', body: JSON.stringify(data) }),
  deleteMember: (id, pin) =>
    request(`/members/${id}${pin ? `?parent_pin=${encodeURIComponent(pin)}` : ''}`, { method: 'DELETE' }),
  getMemberBadges: (id) =>
    request(`/members/${id}/badges`),

  // 分類管理
  getCategories: () =>
    request('/categories'),
  createCategory: (data) =>
    request('/categories', { method: 'POST', body: JSON.stringify(data) }),

  // 規則管理
  getRules: (memberId = null, onlyActive = true) => {
    const params = new URLSearchParams()
    if (memberId) params.append('member_id', memberId)
    params.append('only_active', onlyActive)
    return request(`/rules?${params.toString()}`)
  },
  createRule: (data) =>
    request('/rules', { method: 'POST', body: JSON.stringify(data) }),
  updateRule: (id, data) =>
    request(`/rules/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteRule: (id) =>
    request(`/rules/${id}`, { method: 'DELETE' }),

  // 成就與存摺流水帳
  previewKudos: (data) =>
    request('/kudos/preview', { method: 'POST', body: JSON.stringify(data) }),
  recordKudos: (data) =>
    request('/kudos/record', { method: 'POST', body: JSON.stringify(data) }),
  getLedgerHistory: (memberId = null, limit = 50) => {
    const params = new URLSearchParams()
    if (memberId) params.append('member_id', memberId)
    params.append('limit', limit)
    return request(`/kudos/history?${params.toString()}`)
  },
  exportLedgerUrl: (memberId = null, startDate = null, endDate = null) => {
    const params = new URLSearchParams()
    if (memberId) params.append('member_id', memberId)
    if (startDate) params.append('start_date', startDate)
    if (endDate) params.append('end_date', endDate)
    return `/api/kudos/export?${params.toString()}`
  },
  previewBatchAdjust: (data) =>
    request('/kudos/batch-preview', { method: 'POST', body: JSON.stringify(data) }),
  executeBatchAdjust: (data) =>
    request('/kudos/batch-adjust', { method: 'POST', body: JSON.stringify(data) }),

  // 獎品商城與兌換
  getItems: (all = false) =>
    request(`/items?all=${all}`),
  createItem: (data) =>
    request('/items', { method: 'POST', body: JSON.stringify(data) }),
  updateItem: (id, data) =>
    request(`/items/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteItem: (id) =>
    request(`/items/${id}`, { method: 'DELETE' }),

  // 兌換審核
  requestRedemption: (data) =>
    request('/redemptions', { method: 'POST', body: JSON.stringify(data) }),
  getRedemptions: (memberId = null, status = null) => {
    const params = new URLSearchParams()
    if (memberId) params.append('member_id', memberId)
    if (status) params.append('status', status)
    return request(`/redemptions?${params.toString()}`)
  },
  reviewRedemption: (id, data) =>
    request(`/redemptions/${id}/review`, { method: 'POST', body: JSON.stringify(data) }),

  // 系統維運與升級
  getSystemConfig: () =>
    request('/system/config'),
  saveSystemConfig: (data) =>
    request('/system/config', { method: 'PUT', body: JSON.stringify(data) }),
  triggerBackup: (data = {}) =>
    request('/system/backup', { method: 'POST', body: JSON.stringify(data) }),
  getBackups: (targetPath = null) =>
    request(`/system/backups${targetPath ? `?target_path=${encodeURIComponent(targetPath)}` : ''}`),
  testLine: () =>
    request('/system/line/test', { method: 'POST', body: JSON.stringify({}) }),
  getVersion: () =>
    request('/system/version'),
  triggerUpgrade: (data = {}) =>
    request('/system/upgrade', { method: 'POST', body: JSON.stringify(data) }),
  uploadPackage: (formData) =>
    request('/system/upload-package', { method: 'POST', body: formData }),
  getUpgradeStatus: () =>
    request('/system/upgrade-status'),
  verifyParentPin: (pin) =>
    request('/system/verify-pin', {
      method: 'POST',
      body: JSON.stringify({ parent_pin: pin }),
    }),
  verifyMemberPin: (memberId, pin) =>
    request('/system/verify-member-pin', {
      method: 'POST',
      body: JSON.stringify({ member_id: memberId, pin }),
    }),

  // 成就勳章管理 (FR-18)
  getBadges: (all = true) =>
    request(`/badges?all=${all}`),
  createBadge: (data) =>
    request('/badges', { method: 'POST', body: JSON.stringify(data) }),
  updateBadge: (id, data) =>
    request(`/badges/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteBadge: (id, parentPin = null) =>
    request(`/badges/${id}${parentPin ? `?parent_pin=${encodeURIComponent(parentPin)}` : ''}`, { method: 'DELETE' }),
  toggleMemberBadge: (badgeKey, memberId, unlock = null, parentPin = null) =>
    request(`/badges/${badgeKey}/toggle/${memberId}`, {
      method: 'POST',
      body: JSON.stringify({ unlock, parent_pin: parentPin }),
    }),
}
