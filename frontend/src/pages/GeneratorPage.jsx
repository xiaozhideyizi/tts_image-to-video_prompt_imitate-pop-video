import { useState } from 'react'
import { promptApi } from '../api'

// ========== 平台配置 ==========
const PLATFORM_OPTIONS = {
  ecommerce: {
    label: '🛒 电商平台',
    platforms: [
      { value: 'taobao', label: '淘系（淘宝/天猫）' },
      { value: 'pinduoduo', label: '拼多多' },
      { value: 'jd', label: '京东' },
      { value: 'douyin_ec', label: '抖音电商' },
    ],
  },
  domestic_social: {
    label: '📱 国内社媒',
    platforms: [
      { value: 'xiaohongshu', label: '小红书' },
      { value: 'douyin', label: '抖音' },
      { value: 'shipinhao', label: '视频号' },
      { value: 'bilibili', label: 'B站' },
    ],
  },
  overseas: {
    label: '🌍 国外社媒',
    platforms: [
      { value: 'tiktok', label: 'TikTok' },
      { value: 'instagram', label: 'Instagram Reels' },
      { value: 'youtube', label: 'YouTube Shorts' },
      { value: 'facebook', label: 'Facebook Reels' },
    ],
  },
}

const PLATFORM_PROFILES = {
  taobao:         { ratio: '3:4',  resolution: '1080x1440', duration: '15s',  lang: 'chinese', orientation: 'portrait' },
  pinduoduo:      { ratio: '1:1',  resolution: '1080x1080', duration: '15s',  lang: 'chinese', orientation: 'square' },
  jd:             { ratio: '3:4',  resolution: '1080x1440', duration: '20s',  lang: 'chinese', orientation: 'portrait' },
  douyin_ec:      { ratio: '9:16', resolution: '1080x1920', duration: '20s',  lang: 'chinese', orientation: 'vertical' },
  xiaohongshu:    { ratio: '3:4',  resolution: '1080x1440', duration: '25s',  lang: 'chinese', orientation: 'portrait' },
  douyin:         { ratio: '9:16', resolution: '1080x1920', duration: '20s',  lang: 'chinese', orientation: 'vertical' },
  shipinhao:      { ratio: '9:16', resolution: '1080x1920', duration: '25s',  lang: 'chinese', orientation: 'vertical' },
  bilibili:       { ratio: '16:9', resolution: '1920x1080', duration: '45s',  lang: 'chinese', orientation: 'landscape' },
  tiktok:         { ratio: '9:16', resolution: '1080x1920', duration: '15s',  lang: 'english', orientation: 'vertical' },
  instagram:      { ratio: '9:16', resolution: '1080x1920', duration: '15s',  lang: 'english', orientation: 'vertical' },
  youtube:        { ratio: '9:16', resolution: '1080x1920', duration: '30s',  lang: 'english', orientation: 'vertical' },
  facebook:       { ratio: '9:16', resolution: '1080x1920', duration: '20s',  lang: 'english', orientation: 'vertical' },
}

// ========== 口播字幕选项 ==========
const VOICEOVER_SUBTITLE_OPTIONS = [
  { value: 'voice_no_sub', label: '口播无字幕', desc: '有配音旁白，无字幕叠加' },
  { value: 'voice_with_sub', label: '口播有字幕', desc: '有配音旁白，叠加字幕' },
  { value: 'no_voice_with_sub', label: '无口播有字幕', desc: '无配音，纯字幕展示' },
  { value: 'no_voice_no_sub', label: '无口播无字幕', desc: '纯画面，无配音无字幕' },
]

export default function GeneratorPage() {
  const [form, setForm] = useState({
    platform: 'douyin',
    voiceover_subtitle: 'voice_with_sub',
    product_name: '',
    target_market: 'china',
    target_language: 'chinese',
    selling_points: '',
    video_script: '',
    bgm_style: '',
    audio_option: 'voiceover',
    count: 3,
    use_ai: true,
  })
  const [prompts, setPrompts] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState({})

  const update = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const currentProfile = PLATFORM_PROFILES[form.platform] || PLATFORM_PROFILES.douyin

  const getCurrentCategory = () => {
    for (const [catKey, cat] of Object.entries(PLATFORM_OPTIONS)) {
      if (cat.platforms.some(p => p.value === form.platform)) return catKey
    }
    return 'domestic_social'
  }

  const handleCategoryChange = (catKey) => {
    const firstPlatform = PLATFORM_OPTIONS[catKey].platforms[0].value
    update('platform', firstPlatform)
    if (catKey === 'overseas') {
      update('target_language', 'english')
      update('target_market', 'usa')
    } else {
      update('target_language', 'chinese')
      update('target_market', 'china')
    }
  }

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
    <div className="generator-page">
      {/* 页面标题 */}
      <div className="generator-header">
        <h1 className="page-title">TikTok爆款复刻机</h1>
        <p className="page-subtitle">上传视频，AI一键生成同款提示词</p>
      </div>

      {/* 三栏布局 */}
      <div className="generator-layout">

        {/* ====== 左侧：上传区 ====== */}
        <div className="generator-left">
          <div className="panel-card">
            <div className="panel-title">📤 素材上传</div>

            {/* 对标视频上传 */}
            <div className="upload-box">
              <div className="upload-icon">🎬</div>
              <div className="upload-label">上传对标视频</div>
              <div className="upload-hint">支持 MP4 / MOV，最大 100MB</div>
              <button className="upload-btn">选择视频文件</button>
            </div>

            {/* 产品图片上传 */}
            <div className="upload-box" style={{marginTop:16}}>
              <div className="upload-icon">🖼️</div>
              <div className="upload-label">上传产品图片</div>
              <div className="upload-hint">支持 JPG / PNG，建议高清</div>
              <button className="upload-btn">选择图片文件</button>
            </div>

            <div className="upload-note">
              💡 上传素材后，AI将分析视频风格并适配到您的产品
            </div>
          </div>
        </div>

        {/* ====== 中间：参数配置区 ====== */}
        <div className="generator-center">
          <div className="panel-card">
            <div className="panel-title">⚙️ 参数配置</div>

            {error && <div className="error-msg" style={{marginBottom:14}}>{error}</div>}

            {/* --- 平台选择 --- */}
            <div className="config-group">
              <label className="config-label">🎯 目标平台</label>
              <div className="platform-tabs">
                {Object.entries(PLATFORM_OPTIONS).map(([catKey, cat]) => (
                  <button
                    key={catKey}
                    className={`platform-tab ${getCurrentCategory() === catKey ? 'active' : ''}`}
                    onClick={() => handleCategoryChange(catKey)}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
              <select
                className="config-select"
                value={form.platform}
                onChange={e => update('platform', e.target.value)}
              >
                {PLATFORM_OPTIONS[getCurrentCategory()].platforms.map(p => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
              <div className="platform-meta">
                <span className="meta-tag">{currentProfile.orientation} {currentProfile.ratio}</span>
                <span className="meta-tag">{currentProfile.resolution}</span>
                <span className="meta-tag">{currentProfile.duration}</span>
              </div>
            </div>

            {/* --- 口播字幕 --- */}
            <div className="config-group">
              <label className="config-label">🎙️ 口播 & 字幕</label>
              <select
                className="config-select"
                value={form.voiceover_subtitle}
                onChange={e => update('voiceover_subtitle', e.target.value)}
              >
                {VOICEOVER_SUBTITLE_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label} — {opt.desc}
                  </option>
                ))}
              </select>
            </div>

            {/* --- 产品信息 --- */}
            <div className="config-group">
              <label className="config-label">📝 产品信息</label>
              <div className="config-grid-2">
                <div className="config-field">
                  <label>商品名称 *</label>
                  <input
                    value={form.product_name}
                    onChange={e => update('product_name', e.target.value)}
                    placeholder="例：无线蓝牙耳机"
                  />
                </div>
                <div className="config-field">
                  <label>核心卖点</label>
                  <input
                    value={form.selling_points}
                    onChange={e => update('selling_points', e.target.value)}
                    placeholder="降噪, 30小时续航, 防水"
                  />
                </div>
              </div>
            </div>

            {/* --- 目标市场 & 语言 --- */}
            <div className="config-group">
              <label className="config-label">🌐 市场 & 语言</label>
              <div className="config-grid-2">
                <div className="config-field">
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
                <div className="config-field">
                  <label>目标语言</label>
                  <select value={form.target_language} onChange={e => update('target_language', e.target.value)}>
                    <option value="chinese">中文</option>
                    <option value="english">English</option>
                    <option value="japanese">日语</option>
                    <option value="korean">韩语</option>
                    <option value="spanish">西班牙语</option>
                  </select>
                </div>
              </div>
            </div>

            {/* --- 音频 & BGM --- */}
            <div className="config-group">
              <label className="config-label">🎵 音频配置</label>
              <div className="config-grid-2">
                <div className="config-field">
                  <label>音频选项</label>
                  <select value={form.audio_option} onChange={e => update('audio_option', e.target.value)}>
                    <option value="voiceover">口播配音</option>
                    <option value="music">背景音乐</option>
                    <option value="both">配音+音乐</option>
                    <option value="none">无音频</option>
                  </select>
                </div>
                <div className="config-field">
                  <label>背景音乐风格</label>
                  <input
                    value={form.bgm_style}
                    onChange={e => update('bgm_style', e.target.value)}
                    placeholder="电子音乐, 轻快流行"
                  />
                </div>
              </div>
            </div>

            {/* --- 口播文案 --- */}
            <div className="config-group">
              <div className="config-field full">
                <label>口播/展示文案</label>
                <textarea
                  value={form.video_script}
                  onChange={e => update('video_script', e.target.value)}
                  placeholder="输入口播或展示内容..."
                  rows={3}
                />
              </div>
            </div>

            {/* --- 生成控制 --- */}
            <div className="config-group">
              <div className="generate-controls">
                <div className="count-control">
                  <label>生成数量</label>
                  <input
                    type="range" min={1} max={5}
                    value={form.count}
                    onChange={e => update('count', +e.target.value)}
                  />
                  <span className="count-badge">{form.count}</span>
                </div>
                <label className="ai-checkbox">
                  <input
                    type="checkbox"
                    checked={form.use_ai}
                    onChange={e => update('use_ai', e.target.checked)}
                  />
                  使用 AI 智能生成
                </label>
              </div>
            </div>

            <button className="generate-btn-main" onClick={handleGenerate} disabled={loading}>
              {loading ? '⏳ AI 生成中...' : '🚀 生成爆款提示词'}
            </button>
          </div>
        </div>

        {/* ====== 右侧：结果预览区 ====== */}
        <div className="generator-right">
          <div className="panel-card">
            <div className="panel-title">📋 生成结果</div>

            {loading && (
              <div className="result-loading">
                <div className="spinner" />
                <div>AI 正在创作中...</div>
              </div>
            )}

            {!loading && prompts.length === 0 && (
              <div className="result-empty">
                <div className="empty-icon">✨</div>
                <div>填写配置后点击生成</div>
                <div className="empty-hint">AI 将为您生成适配目标平台的视频提示词</div>
              </div>
            )}

            {prompts.map((p, idx) => (
              <div className="result-card-compact" key={idx}>
                <div className="result-card-header">
                  <span className="result-badge">方案 {p.index || idx + 1}</span>
                  <button className="copy-btn-sm" onClick={() => handleCopy(idx, p.finalPrompt)}>
                    {copied[idx] ? '✓ 已复制' : '📋 复制'}
                  </button>
                </div>
                {p.audit && (
                  <div className="result-meta-line">
                    <span className="meta-audit">🛡️ {p.audit}</span>
                  </div>
                )}
                {p.audioPlan && (
                  <div className="result-meta-line">
                    <span className="meta-audio">🎧 {p.audioPlan}</span>
                  </div>
                )}
                {p.dynamicStrategy && (
                  <div className="result-meta-line">
                    <span className="meta-dynamic">⚡ {p.dynamicStrategy}</span>
                  </div>
                )}
                <div className="result-prompt-text">{p.finalPrompt}</div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}
