import axios from 'axios'

// 生产环境：直连 Railway 后端
// 开发环境：Vite proxy 转发到 localhost:8000
const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const apiBase = isLocalhost
  ? '/api'
  : 'https://incredible-alignment-production-4ba5.up.railway.app/api'

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
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api
