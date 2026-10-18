const TOKEN_KEY = 'autumnmail.token'

function captureToken() {
  const hash = new URLSearchParams(location.hash.replace(/^#/, ''))
  const query = new URLSearchParams(location.search)
  const token = hash.get('token') || query.get('token')
  if (!token) return
  sessionStorage.setItem(TOKEN_KEY, token)
  query.delete('token')
  const search = query.toString()
  history.replaceState(null, '', location.pathname + (search ? `?${search}` : ''))
}

captureToken()

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY) || ''
}

async function request(path, { method = 'GET', body, raw = false } = {}) {
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const token = getToken()
  if (token) headers['X-App-Token'] = token

  const response = await fetch(`/api${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (!response.ok) {
    let detail = `请求失败（${response.status}）`
    try {
      const payload = await response.json()
      if (payload && payload.detail) detail = payload.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }

  return raw ? response : response.json()
}

export const api = {
  bootstrap: () => request('/bootstrap'),
  dashboard: () => request('/dashboard'),
  opportunities: (params = {}) =>
    request(`/opportunities?${new URLSearchParams(params).toString()}`),
  opportunity: (id) => request(`/opportunities/${id}`),
  events: (params = {}) =>
    request(`/events?${new URLSearchParams(params).toString()}`),
  updateEvent: (id, status) =>
    request(`/events/${id}`, { method: 'PATCH', body: { status } }),
  review: () => request('/review'),
  resolveReview: (id, payload) =>
    request(`/review/${id}`, { method: 'POST', body: payload }),
  accounts: () => request('/accounts'),
  addAccount: (payload) => request('/accounts', { method: 'POST', body: payload }),
  testAccountDraft: (payload) =>
    request('/accounts/test', { method: 'POST', body: payload }),
  deleteAccount: (id) => request(`/accounts/${id}`, { method: 'DELETE' }),
  testAccount: (id) => request(`/accounts/${id}/test`, { method: 'POST' }),
  syncAccount: (id) => request(`/accounts/${id}/sync`, { method: 'POST' }),
  messages: (params = {}) =>
    request(`/messages?${new URLSearchParams(params).toString()}`),
  settings: () => request('/settings'),
  saveSettings: (payload) => request('/settings', { method: 'PUT', body: payload }),
  sync: () => request('/sync', { method: 'POST' }),
  resetDemo: () => request('/demo/reset', { method: 'POST' }),
  meta: () => request('/meta'),
  download: async (path, filename) => {
    const response = await request(path, { raw: true })
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
  },
}
