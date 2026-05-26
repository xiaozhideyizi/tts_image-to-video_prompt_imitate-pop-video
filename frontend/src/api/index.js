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
  generate: (data) => api.post('/prompts/generate', data),
  getHistory: (page = 1) => api.get(`/prompts/history?page=${page}`),
  createShareLink: (id) => api.post(`/prompts/history/${id}/share`),
  getShared: (token) => api.get(`/prompts/share/${token}`),
  deleteHistory: (id) => api.delete(`/prompts/history/${id}`),
}
