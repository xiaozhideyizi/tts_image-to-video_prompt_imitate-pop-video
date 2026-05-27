import api from './client'

export const authApi = {
  register: (data) => api.post('/auth/register', data),
  login: (email, password) => {
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)
    return api.post('/auth/token', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
  me: () => api.get('/auth/me'),
}

export const promptApi = {
  // 获取选项配置
  getOptions: () => api.get('/prompts/options'),

  // AI分析产品图片
  analyzeImage: (formData) => api.post('/prompts/analyze-image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  }),

  // 生成提示词（multipart/form-data，支持文件上传）
  generate: (formData) => api.post('/prompts/generate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,  // 文件上传需更长超时
  }),

  // 历史记录
  getHistory: (page = 1) => api.get(`/prompts/history?page=${page}`),

  // 获取历史视频
  getHistoryVideo: (id) => api.get(`/prompts/history/${id}/video`, { responseType: 'blob' }),

  // 获取历史图片
  getHistoryImage: (id) => api.get(`/prompts/history/${id}/image`, { responseType: 'blob' }),

  // 采纳提示词
  adopt: (id, promptIndex) => {
    const form = new URLSearchParams()
    form.append('prompt_index', promptIndex)
    return api.post(`/prompts/history/${id}/adopt`, form)
  },

  // 报告违规
  reportViolation: (id, promptIndex, reason) => {
    const form = new URLSearchParams()
    form.append('prompt_index', promptIndex)
    form.append('reason', reason)
    return api.post(`/prompts/history/${id}/violation`, form)
  },

  // 获取评测统计
  getStats: () => api.get('/prompts/stats'),

  // 分享
  createShareLink: (id) => api.post(`/prompts/history/${id}/share`),
  getShared: (token) => api.get(`/prompts/share/${token}`),
  deleteHistory: (id) => api.delete(`/prompts/history/${id}`),
}
