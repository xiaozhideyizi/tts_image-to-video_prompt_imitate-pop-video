import { NavLink, Outlet, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()

  if (!user) return <Navigate to="/login" replace />

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">🎬 广告爆款复刻机</div>
        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>
            🚀 生成工具
          </NavLink>
          <NavLink to="/history" className={({ isActive }) => isActive ? 'active' : ''}>
            📋 历史记录
          </NavLink>
        </nav>
        <div className="sidebar-user">
          <strong>{user.username}</strong>
          {user.email}
          <button className="btn-sm btn-ghost" style={{marginTop:10,width:'100%'}} onClick={logout}>
            退出登录
          </button>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
