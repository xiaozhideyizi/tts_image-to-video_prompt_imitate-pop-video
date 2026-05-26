import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import GeneratorPage from './pages/GeneratorPage'
import HistoryPage from './pages/HistoryPage'
import SharePage from './pages/SharePage'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/share/:token" element={<SharePage />} />
          <Route element={<Layout />}>
            <Route path="/" element={<GeneratorPage />} />
            <Route path="/history" element={<HistoryPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
