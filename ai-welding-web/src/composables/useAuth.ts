import { computed, ref } from 'vue'

export type Role = 'student' | 'teacher'

export type CurrentUser = {
  id: string
  identity_code: string
  username: string
  role: Role
  is_approved: boolean
  avatar?: string | null
}

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:28100'

/** 模块级状态，供路由守卫与组件共用 */
export const currentUser = ref<CurrentUser | null>(null)
const loading = ref(false)
const message = ref('')
const isError = ref(false)

export function useAuth() {
  async function parseResponseBody(res: Response) {
    const contentType = res.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      return res.json()
    }
    const text = await res.text()
    return { message: text || `HTTP ${res.status}` }
  }

  const isLoggedIn = computed(() => !!currentUser.value)

  function setFeedback(text: string, error = false) {
    message.value = text
    isError.value = error
  }

  function saveTokens(accessToken: string, refreshToken: string) {
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('refresh_token', refreshToken)
  }

  function clearTokens() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  async function request(path: string, options: RequestInit = {}) {
    const token = localStorage.getItem('access_token')
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    }
    if (token) headers.Authorization = `Bearer ${token}`
    return fetch(`${API_BASE_URL}${path}`, { ...options, headers })
  }

  async function refreshTokenIfNeeded() {
    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) return false
    const res = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!res.ok) {
      clearTokens()
      return false
    }
    const data = await res.json()
    saveTokens(data.access_token, data.refresh_token)
    return true
  }

  async function fetchWhoami() {
    let res = await request('/api/auth/whoami')
    if (res.status === 401) {
      const refreshed = await refreshTokenIfNeeded()
      if (!refreshed) return false
      res = await request('/api/auth/whoami')
    }
    if (!res.ok) return false
    currentUser.value = await res.json()
    return true
  }

  async function restoreSession() {
    const hasToken =
      !!localStorage.getItem('access_token') || !!localStorage.getItem('refresh_token')
    if (!hasToken) return
    const ok = await fetchWhoami()
    if (!ok) clearTokens()
  }

  async function login(
    payload: { identity_code: string; password: string },
    role: Role,
  ) {
    if (!payload.identity_code || !payload.password) {
      setFeedback('请输入身份编号和密码', true)
      return false
    }
    loading.value = true
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await parseResponseBody(res)
      if (!res.ok) {
        setFeedback(data.message || '登录失败', true)
        return false
      }

      if (data.user.role !== role) {
        setFeedback('你选择的身份与账号不一致，请切换后再登录', true)
        return false
      }

      saveTokens(data.tokens.access_token, data.tokens.refresh_token)
      currentUser.value = data.user
      setFeedback('登录成功')
      return true
    } catch {
      setFeedback(`网络异常，请检查后端地址或跨域配置（当前: ${API_BASE_URL}）`, true)
      return false
    } finally {
      loading.value = false
    }
  }

  async function registerTeacher(payload: {
    identity_code: string
    username: string
    password: string
    tel?: string
  }) {
    if (!payload.identity_code || !payload.username || !payload.password) {
      setFeedback('请填写完整的教师注册信息', true)
      return false
    }
    loading.value = true
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/register/teacher`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await parseResponseBody(res)
      if (!res.ok) {
        setFeedback(data.message || '注册失败', true)
        return false
      }
      setFeedback('注册成功，等待管理员审核通过后即可登录')
      return true
    } catch {
      setFeedback(`网络异常，请检查后端地址或跨域配置（当前: ${API_BASE_URL}）`, true)
      return false
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    loading.value = true
    try {
      const refreshToken = localStorage.getItem('refresh_token')
      await request('/api/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
    } finally {
      clearTokens()
      currentUser.value = null
      loading.value = false
      setFeedback('已退出登录')
    }
  }

  return {
    currentUser,
    loading,
    message,
    isError,
    isLoggedIn,
    setFeedback,
    restoreSession,
    login,
    registerTeacher,
    logout,
  }
}
