import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'

export default function LoginPage() {
  const [mode, setMode] = useState('login') // login | register
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, register } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        await login(email, password)
      } else {
        if (!username.trim()) { setError('请填写用户名'); setLoading(false); return }
        await register(email, username, password)
      }
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || '操作失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-box">
        <h2>TikTok爆款复刻机</h2>
        <p style={{textAlign:'center',color:'#888',marginTop:-8,marginBottom:16,fontSize:14}}>上传视频，AI一键生成同款提示词</p>
        {error && <div className="error-msg">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label>邮箱</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="your@email.com" required />
          </div>
          {mode === 'register' && (
            <div className="form-field">
              <label>用户名</label>
              <input type="text" value={username} onChange={e => setUsername(e.target.value)} placeholder="你的昵称" />
            </div>
          )}
          <div className="form-field">
            <label>密码</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="至少6位" minLength={6} required />
          </div>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? '处理中...' : mode === 'login' ? '登录' : '注册'}
          </button>
        </form>
        <div className="auth-switch">
          {mode === 'login' ? '还没有账号？' : '已有账号？'}
          <span onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>
            {mode === 'login' ? '立即注册' : '去登录'}
          </span>
        </div>
      </div>
    </div>
  )
}
