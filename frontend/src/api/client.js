import axios from 'axios'

// 开发环境用 /api（Vite proxy 转发到 localhost:8000）
// 生产环境用 VITE_API_URL（Railway 后端地址）
const apiBase = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: apiBase,
  timeout: 60000,
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
