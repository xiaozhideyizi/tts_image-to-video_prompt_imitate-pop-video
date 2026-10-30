import axios from 'axios'

// VITE_API_URL 可填写后端域名或以 /api 结尾的地址。
// 未配置时走同源 /api，开发环境由 Vite 代理转发。
const configuredUrl = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '')
const apiBase = configuredUrl
  ? (configuredUrl.endsWith('/api') ? configuredUrl : `${configuredUrl}/api`)
  : '/api'

const api = axios.create({
  baseURL: apiBase,
  timeout: 120000, // AI视觉模型较慢，超时设为2分钟
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const isAuthRequest = /^\/auth\/(token|register)$/.test(err.config?.url || '')
    if (err.response?.status === 401 && !isAuthRequest) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api
