import { useState } from 'react'
import { promptApi } from '../api'

export default function GeneratorPage() {
  const [form, setForm] = useState({
    product_name: '',
    target_market: 'china',
    target_language: 'chinese',
    selling_points: '',
    video_script: '',
    bgm_style: '',
    count: 3,
    use_ai: true,
  })
  const [prompts, setPrompts] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState({})

  const update = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const handleGenerate = async () => {
    if (!form.product_name.trim()) { setError('请输入商品名称'); return }
    setError('')
    setLoading(true)
    setPrompts([])
    try {
      const res = await promptApi.generate(form)
      setPrompts(res.data.prompts)
    } catch (err) {
      setError(err.response?.data?.detail || '生成失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async (idx, text) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(c => ({ ...c, [idx]: true }))
      setTimeout(() => setCopied(c => ({ ...c, [idx]: false })), 2000)
    } catch {
      alert('复制失败，请手动选择文本')
    }
  }

  return (
    <div>
      <h1 className="page-title">TikTok爆款复刻机</h1>
      <p style={{textAlign:'center',color:'#888',marginTop:-8,marginBottom:16,fontSize:14}}>上传视频，AI一键生成同款提示词</p>

      <div className="input-section">
        <div className="section-title">📝 产品信息</div>

        {error && <div className="error-msg" style={{marginBottom:16}}>{error}</div>}

        <div className="form-grid">
          <div className="form-group">
            <label>商品名称 *</label>
            <input value={form.product_name} onChange={e => update('product_name', e.target.value)} placeholder="例：无线蓝牙耳机" />
          </div>
          <div className="form-group">
            <label>目标市场</label>
            <select value={form.target_market} onChange={e => update('target_market', e.target.value)}>
              <option value="china">中国</option>
              <option value="usa">美国</option>
              <option value="europe">欧洲</option>
              <option value="japan">日本</option>
              <option value="korea">韩国</option>
              <option value="southeast_asia">东南亚</option>
              <option value="global">全球</option>
            </select>
          </div>
          <div className="form-group">
            <label>目标语言</label>
            <select value={form.target_language} onChange={e => update('target_language', e.target.value)}>
              <option value="chinese">中文</option>
              <option value="english">English</option>
              <option value="japanese">日语</option>
              <option value="korean">韩语</option>
              <option value="spanish">西班牙语</option>
            </select>
          </div>
          <div className="form-group two-cols">
            <label>核心卖点（逗号分隔）</label>
            <input value={form.selling_points} onChange={e => update('selling_points', e.target.value)} placeholder="例：降噪, 30小时续航, 防水" />
          </div>
          <div className="form-group">
            <label>音频选项</label>
            <select value={form.audio_option} onChange={e => update('audio_option', e.target.value)}>
              <option value="voiceover">口播配音</option>
              <option value="music">背景音乐</option>
              <option value="both">配音+音乐</option>
              <option value="none">无音频</option>
            </select>
          </div>
          <div className="form-group full-width">
            <label>视频口播文案</label>
            <textarea value={form.video_script} onChange={e => update('video_script', e.target.value)} placeholder="输入口播或展示内容..." />
          </div>
          <div className="form-group full-width">
            <label>背景音乐风格</label>
            <input value={form.bgm_style} onChange={e => update('bgm_style', e.target.value)} placeholder="例：电子音乐, 轻快流行, 氛围感" />
          </div>
        </div>

        <div className="prompt-count">
          <label>生成数量：</label>
          <input type="range" min={1} max={5} value={form.count} onChange={e => update('count', +e.target.value)} />
          <span className="count-display">{form.count}</span>
        </div>

        <div className="ai-toggle">
          <input type="checkbox" id="useAI" checked={form.use_ai} onChange={e => update('use_ai', e.target.checked)} />
          <label htmlFor="useAI">使用 AI 智能生成（调用 GLM 大模型，效果更好）</label>
        </div>

        <button className="generate-btn" onClick={handleGenerate} disabled={loading}>
          {loading ? '⏳ 生成中...' : '🚀 生成动态提示词'}
        </button>
      </div>

      <div className="results-section">
        {loading && (
          <div className="loading-area">
            <div className="spinner" />
            <div>AI 正在创作中，请稍候...</div>
          </div>
        )}
        {!loading && prompts.length === 0 && (
          <div className="empty-state">
            <div className="icon">✨</div>
            <div>填写产品信息后，点击生成按钮</div>
          </div>
        )}
        {prompts.map((p, idx) => (
          <div className="result-card" key={idx}>
            <div className="result-header">
              <span className="result-number">方案 {p.index || idx + 1}</span>
              <button className="copy-btn" onClick={() => handleCopy(idx, p.finalPrompt)}>
                {copied[idx] ? '✓ 已复制' : '📋 复制'}
              </button>
            </div>
            {p.audit && (
              <div className="audit-section">
                <h4>🛡️ 素材审计</h4>
                {p.audit}
              </div>
            )}
            <div className="av-plan-section">
              <h4>🎧 视听方案</h4>
              {p.audioPlan}<br />
              {p.dynamicStrategy && <><strong>⚡ 去静止策略：</strong>{p.dynamicStrategy}</>}
            </div>
            <div className="prompt-content">{p.finalPrompt}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
