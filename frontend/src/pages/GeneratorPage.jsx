import { useState, useRef, useEffect } from 'react'
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

const VOICEOVER_SUBTITLE_OPTIONS = [
  { value: 'voice_no_sub', label: '口播无字幕' },
  { value: 'voice_with_sub', label: '口播有字幕' },
  { value: 'no_voice_with_sub', label: '无口播有字幕' },
  { value: 'no_voice_no_sub', label: '无口播无字幕' },
]

const SELLING_POINT_PRESETS = []  // 预设卖点已移除，全部由AI推荐

// 级联市场数据 — 国家 → 语言
const MARKET_CASCADE = {
  singapore:    { label: '新加坡', languages: [{ value: 'english', label: '英语' }, { value: 'chinese', label: '中文' }, { value: 'malay', label: '马来语' }] },
  uk:           { label: '英国', languages: [{ value: 'english', label: '英语' }] },
  usa:          { label: '美国', languages: [{ value: 'english', label: '英语' }, { value: 'spanish', label: '西班牙语' }] },
  saudi:        { label: '沙特阿拉伯', languages: [{ value: 'arabic', label: '阿拉伯语' }, { value: 'english', label: '英语' }] },
  uae:          { label: '阿联酋', languages: [{ value: 'arabic', label: '阿拉伯语' }, { value: 'english', label: '英语' }] },
  france:       { label: '法国', languages: [{ value: 'french', label: '法语' }, { value: 'english', label: '英语' }] },
  germany:      { label: '德国', languages: [{ value: 'german', label: '德语' }, { value: 'english', label: '英语' }] },
  italy:        { label: '意大利', languages: [{ value: 'italian', label: '意大利语' }, { value: 'english', label: '英语' }] },
  spain:        { label: '西班牙', languages: [{ value: 'spanish', label: '西班牙语' }, { value: 'english', label: '英语' }] },
  russia:       { label: '俄罗斯', languages: [{ value: 'russian', label: '俄语' }, { value: 'english', label: '英语' }] },
  japan:        { label: '日本', languages: [{ value: 'japanese', label: '日语' }, { value: 'english', label: '英语' }] },
  korea:        { label: '韩国', languages: [{ value: 'korean', label: '韩语' }, { value: 'english', label: '英语' }] },
  china:        { label: '中国大陆', languages: [{ value: 'chinese', label: '中文' }] },
  taiwan:       { label: '中国台湾', languages: [{ value: 'chinese', label: '中文' }, { value: 'english', label: '英语' }] },
  hongkong:     { label: '中国香港', languages: [{ value: 'chinese', label: '中文' }, { value: 'english', label: '英语' }] },
  thailand:     { label: '泰国', languages: [{ value: 'thai', label: '泰语' }, { value: 'english', label: '英语' }] },
  vietnam:      { label: '越南', languages: [{ value: 'vietnamese', label: '越南语' }, { value: 'english', label: '英语' }] },
  indonesia:    { label: '印尼', languages: [{ value: 'indonesian', label: '印尼语' }, { value: 'english', label: '英语' }] },
  philippines:  { label: '菲律宾', languages: [{ value: 'english', label: '英语' }, { value: 'filipino', label: '菲律宾语' }] },
  malaysia:     { label: '马来西亚', languages: [{ value: 'malay', label: '马来语' }, { value: 'chinese', label: '中文' }, { value: 'english', label: '英语' }] },
  brazil:       { label: '巴西', languages: [{ value: 'portuguese', label: '葡萄牙语' }, { value: 'english', label: '英语' }] },
  mexico:       { label: '墨西哥', languages: [{ value: 'spanish', label: '西班牙语' }, { value: 'english', label: '英语' }] },
  australia:    { label: '澳大利亚', languages: [{ value: 'english', label: '英语' }] },
  canada:       { label: '加拿大', languages: [{ value: 'english', label: '英语' }, { value: 'french', label: '法语' }] },
  india:        { label: '印度', languages: [{ value: 'english', label: '英语' }, { value: 'hindi', label: '印地语' }] },
  turkey:       { label: '土耳其', languages: [{ value: 'turkish', label: '土耳其语' }, { value: 'english', label: '英语' }] },
  global:       { label: '全球', languages: [{ value: 'english', label: '英语' }] },
}

// ========== 步骤定义 ==========
const STEPS = [
  { key: 'upload', label: '上传素材', icon: '📤' },
  { key: 'platform', label: '选择平台', icon: '🎯' },
  { key: 'product', label: '产品配置', icon: '📝' },
  { key: 'generate', label: '生成提示词', icon: '🚀' },
]

export default function GeneratorPage() {
  const [step, setStep] = useState(0)
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
  const [videoFile, setVideoFile] = useState(null)
  const [imageFile, setImageFile] = useState(null)
  const [videoPreview, setVideoPreview] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [prompts, setPrompts] = useState([])
  const [historyId, setHistoryId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState({})
  const [customSellingPoint, setCustomSellingPoint] = useState('')
  const [customMarket, setCustomMarket] = useState('')
  const [violationModal, setViolationModal] = useState(null) // {promptIndex, historyId}
  const [violationReason, setViolationReason] = useState('')
  const [stats, setStats] = useState(null)

  // AI分析结果
  const [aiAnalysis, setAiAnalysis] = useState(null) // {product_name, product_desc, selling_points:[]}
  const [analyzing, setAnalyzing] = useState(false)

  // 级联市场选择器状态
  const [marketOpen, setMarketOpen] = useState(false)
  const [selectedCountry, setSelectedCountry] = useState('usa')
  const [selectedLang, setSelectedLang] = useState('english')

  const videoInputRef = useRef(null)
  const imageInputRef = useRef(null)

  const update = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const currentProfile = PLATFORM_PROFILES[form.platform] || PLATFORM_PROFILES.douyin

  const getCurrentCategory = () => {
    for (const [catKey, cat] of Object.entries(PLATFORM_OPTIONS)) {
      if (cat.platforms.some(p => p.value === form.platform)) return catKey
    }
    return 'domestic_social'
  }

  // 加载评测统计
  useEffect(() => {
    promptApi.getStats().then(res => setStats(res.data)).catch(() => {})
  }, [])

  // 视频选择
  const handleVideoSelect = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > 100 * 1024 * 1024) { setError('视频文件不能超过 100MB'); return }
    setVideoFile(file)
    setVideoPreview(URL.createObjectURL(file))
    setError('')
  }

  // 图片选择 + AI分析
  const handleImageSelect = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > 10 * 1024 * 1024) { setError('图片文件不能超过 10MB'); return }
    setImageFile(file)
    setImagePreview(URL.createObjectURL(file))
    setError('')

    // AI分析产品图片
    setAnalyzing(true)
    try {
      const fd = new FormData()
      fd.append('image', file)
      const res = await promptApi.analyzeImage(fd)
      setAiAnalysis(res.data)
      // 自动填充产品名称（如果用户还没填）
      if (res.data.product_name && !form.product_name) {
        update('product_name', res.data.product_name)
      }
    } catch (err) {
      console.log('AI分析失败:', err)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleClearVideo = () => {
    setVideoFile(null)
    if (videoPreview) URL.revokeObjectURL(videoPreview)
    setVideoPreview(null)
    if (videoInputRef.current) videoInputRef.current.value = ''
  }

  const handleClearImage = () => {
    setImageFile(null)
    if (imagePreview) URL.revokeObjectURL(imagePreview)
    setImagePreview(null)
    if (imageInputRef.current) imageInputRef.current.value = ''
  }

  const handleCategoryChange = (catKey) => {
    update('platform', PLATFORM_OPTIONS[catKey].platforms[0].value)
    if (catKey === 'overseas') {
      setSelectedCountry('usa')
      setSelectedLang('english')
      update('target_language', 'english')
      update('target_market', 'usa')
    } else {
      setSelectedCountry('china')
      setSelectedLang('chinese')
      update('target_language', 'chinese')
      update('target_market', 'china')
    }
  }

  // 卖点选择
  const toggleSellingPoint = (point) => {
    const current = form.selling_points ? form.selling_points.split(',').map(s => s.trim()).filter(Boolean) : []
    if (current.includes(point)) {
      update('selling_points', current.filter(p => p !== point).join(','))
    } else {
      update('selling_points', [...current, point].join(','))
    }
  }

  // 修改AI推荐卖点（直接编辑）
  const updateAiSellingPoint = (index, newValue) => {
    if (!aiAnalysis) return
    const oldPoints = [...(aiAnalysis.selling_points || [])]
    const oldValue = oldPoints[index]
    // 更新AI分析数据
    oldPoints[index] = newValue
    setAiAnalysis({ ...aiAnalysis, selling_points: oldPoints })
    // 更新已选卖点（如果旧值被选中了，替换为新值）
    const current = form.selling_points ? form.selling_points.split(',').map(s => s.trim()).filter(Boolean) : []
    if (current.includes(oldValue)) {
      const updated = current.map(p => p === oldValue ? newValue : p)
      update('selling_points', updated.join(','))
    }
  }

  // 删除AI推荐卖点
  const removeAiSellingPoint = (index) => {
    if (!aiAnalysis) return
    const oldPoints = [...(aiAnalysis.selling_points || [])]
    const removed = oldPoints[index]
    oldPoints.splice(index, 1)
    setAiAnalysis({ ...aiAnalysis, selling_points: oldPoints })
    // 从已选中移除
    const current = form.selling_points ? form.selling_points.split(',').map(s => s.trim()).filter(Boolean) : []
    update('selling_points', current.filter(p => p !== removed).join(','))
  }

  const addCustomSellingPoint = () => {
    if (!customSellingPoint.trim()) return
    const current = form.selling_points ? form.selling_points.split(',').map(s => s.trim()).filter(Boolean) : []
    if (!current.includes(customSellingPoint.trim())) {
      update('selling_points', [...current, customSellingPoint.trim()].join(','))
    }
    setCustomSellingPoint('')
  }

  // 级联市场选择
  const selectCountry = (countryKey) => {
    setSelectedCountry(countryKey)
    update('target_market', countryKey)
    // 默认选该国的第一种语言
    const firstLang = MARKET_CASCADE[countryKey]?.languages[0]?.value || 'english'
    setSelectedLang(firstLang)
    update('target_language', firstLang)
  }

  const selectLanguage = (langKey) => {
    setSelectedLang(langKey)
    update('target_language', langKey)
  }

  const getMarketDisplay = () => {
    const c = MARKET_CASCADE[selectedCountry]
    if (!c) return ''
    const l = c.languages.find(x => x.value === selectedLang)
    return `${c.label} / ${l?.label || ''}`
  }

  // 生成
  const handleGenerate = async () => {
    if (!form.product_name.trim()) { setError('请输入商品名称'); return }
    if (!imageFile) { setError('请上传产品图片'); return }
    setError('')
    setLoading(true)
    setPrompts([])
    try {
      const fd = new FormData()
      // 文本字段
      fd.append('product_name', form.product_name)
      fd.append('target_market', form.target_market)
      fd.append('target_language', form.target_language)
      fd.append('platform', form.platform)
      fd.append('voiceover_subtitle', form.voiceover_subtitle)
      fd.append('selling_points', form.selling_points)
      fd.append('video_script', form.video_script)
      fd.append('bgm_style', form.bgm_style)
      fd.append('audio_option', form.audio_option)
      fd.append('count', form.count)
      fd.append('use_ai', form.use_ai)
      // 文件
      if (videoFile) fd.append('video', videoFile)
      if (imageFile) fd.append('image', imageFile)

      const res = await promptApi.generate(fd)
      setPrompts(res.data.prompts)
      setHistoryId(res.data.history_id)
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

  // 采纳
  const handleAdopt = async (promptIndex) => {
    if (!historyId) return
    try {
      await promptApi.adopt(historyId, promptIndex)
      alert(`✅ 方案 ${promptIndex} 已采纳！风格权重已提升`)
      // 刷新统计
      const res = await promptApi.getStats()
      setStats(res.data)
    } catch (err) {
      alert('采纳失败：' + (err.response?.data?.detail || '请重试'))
    }
  }

  // 违规
  const handleViolation = async () => {
    if (!violationModal || !violationReason.trim()) return
    try {
      await promptApi.reportViolation(violationModal.historyId, violationModal.promptIndex, violationReason)
      alert(`⚠️ 方案 ${violationModal.promptIndex} 已标记违规。原因将作为后续生成的前置约束。`)
      setViolationModal(null)
      setViolationReason('')
      const res = await promptApi.getStats()
      setStats(res.data)
    } catch (err) {
      alert('操作失败：' + (err.response?.data?.detail || '请重试'))
    }
  }

  // 步骤是否可前进
  const canNext = () => {
    if (step === 0) return imageFile !== null  // 至少要有产品图片
    if (step === 1) return true
    if (step === 2) return form.product_name.trim() !== ''
    return true
  }

  const durSec = parseInt(currentProfile.duration)

  return (
    <div className="generator-page">
      {/* 标题 */}
      <div className="generator-header">
        <h1 className="page-title">广告爆款复刻机</h1>
        <p className="page-subtitle">上传视频，AI一键生成同款提示词</p>
      </div>

      {/* 步骤条 */}
      <div className="step-bar">
        {STEPS.map((s, i) => (
          <div
            key={s.key}
            className={`step-item ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}
            onClick={() => i <= step && setStep(i)}
          >
            <div className="step-icon">{i < step ? '✓' : s.icon}</div>
            <div className="step-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* 评测统计栏 */}
      {stats && (
        <div className="stats-bar">
          <span className="stat-item">📊 采纳率 <strong>{stats.adoption_rate}%</strong></span>
          <span className="stat-item">⚠️ 违规率 <strong>{stats.violation_rate}%</strong></span>
          <span className="stat-item">✅ 质量率 <strong>{stats.quality_rate}%</strong></span>
          <span className="stat-item">📝 累计生成 <strong>{stats.total_generated}</strong></span>
        </div>
      )}

      {error && <div className="error-msg">{error}</div>}

      {/* ========== Step 0: 上传素材 ========== */}
      {step === 0 && (
        <div className="step-content">
          <div className="step-title">📤 第一步：上传素材</div>
          <div className="step-desc">上传参考视频（模仿风格）和产品图片（生成主体），至少需要产品图片</div>

          <div className="upload-grid">
            {/* 参考视频 */}
            <div className="upload-box">
              <input ref={videoInputRef} type="file" accept="video/mp4,video/quicktime,video/webm" style={{ display: 'none' }} onChange={handleVideoSelect} />
              {videoPreview ? (
                <div className="upload-preview">
                  <video src={videoPreview} controls style={{ width: '100%', borderRadius: 8, maxHeight: 200 }} />
                  <div className="upload-file-info">
                    <span>📹 {videoFile?.name}</span>
                    <span className="upload-file-size">{videoFile ? (videoFile.size / 1024 / 1024).toFixed(1) + ' MB' : ''}</span>
                  </div>
                  <button className="upload-btn-clear" onClick={handleClearVideo}>✕ 移除</button>
                </div>
              ) : (
                <div className="upload-placeholder" onClick={() => videoInputRef.current?.click()}>
                  <div className="upload-icon">🎬</div>
                  <div className="upload-label">上传参考视频</div>
                  <div className="upload-hint">模仿风格、分镜、转场、动效<br/>不会复制人物</div>
                  <button className="upload-btn" onClick={(e) => { e.stopPropagation(); videoInputRef.current?.click() }}>选择视频</button>
                </div>
              )}
            </div>

            {/* 产品图片 */}
            <div className="upload-box">
              <input ref={imageInputRef} type="file" accept="image/jpeg,image/png,image/webp" style={{ display: 'none' }} onChange={handleImageSelect} />
              {imagePreview ? (
                <div className="upload-preview">
                  <img src={imagePreview} alt="产品图片" style={{ width: '100%', borderRadius: 8, maxHeight: 200, objectFit: 'contain' }} />
                  <div className="upload-file-info">
                    <span>🖼️ {imageFile?.name}</span>
                    <span className="upload-file-size">{imageFile ? (imageFile.size / 1024 / 1024).toFixed(1) + ' MB' : ''}</span>
                  </div>
                  <button className="upload-btn-clear" onClick={handleClearImage}>✕ 移除</button>
                </div>
              ) : (
                <div className="upload-placeholder required" onClick={() => imageInputRef.current?.click()}>
                  <div className="upload-icon">🖼️</div>
                  <div className="upload-label">上传产品图片 *</div>
                  <div className="upload-hint">AI将以此为产品主体<br/>生成视频提示词</div>
                  <button className="upload-btn" onClick={(e) => { e.stopPropagation(); imageInputRef.current?.click() }}>选择图片</button>
                </div>
              )}
            </div>
          </div>

          <div className="step-note">💡 参考视频只模仿风格、分镜、转场和动效，不会复制视频中的人物。模特根据商品卖点和投放市场本土化原创。</div>

          <div className="step-actions">
            <button className="step-next" disabled={!canNext()} onClick={() => setStep(1)}>
              下一步：选择平台 →
            </button>
          </div>
        </div>
      )}

      {/* ========== Step 1: 选择平台 ========== */}
      {step === 1 && (
        <div className="step-content">
          <div className="step-title">🎯 第二步：选择投放平台</div>
          <div className="step-desc">不同平台有不同的画面比例、时长和调性要求</div>

          <div className="platform-tabs">
            {Object.entries(PLATFORM_OPTIONS).map(([catKey, cat]) => (
              <button key={catKey} className={`platform-tab ${getCurrentCategory() === catKey ? 'active' : ''}`} onClick={() => handleCategoryChange(catKey)}>
                {cat.label}
              </button>
            ))}
          </div>

          <div className="platform-grid">
            {PLATFORM_OPTIONS[getCurrentCategory()].platforms.map(p => (
              <button key={p.value} className={`platform-card ${form.platform === p.value ? 'selected' : ''}`} onClick={() => update('platform', p.value)}>
                <div className="platform-card-label">{p.label}</div>
                <div className="platform-card-meta">
                  {PLATFORM_PROFILES[p.value]?.ratio} · {PLATFORM_PROFILES[p.value]?.duration}
                </div>
              </button>
            ))}
          </div>

          <div className="platform-info">
            <span>📐 {currentProfile.orientation} {currentProfile.ratio}</span>
            <span>📺 {currentProfile.resolution}</span>
            <span>⏱️ {currentProfile.duration}</span>
            {durSec > 12 && <span className="group-badge">将分为 {Math.ceil(durSec / 12)} 个 12s 片段</span>}
          </div>

          <div className="config-group" style={{ marginTop: 16 }}>
            <label className="config-label">🎙️ 口播 & 字幕</label>
            <div className="voiceover-grid">
              {VOICEOVER_SUBTITLE_OPTIONS.map(opt => (
                <button key={opt.value} className={`voiceover-chip ${form.voiceover_subtitle === opt.value ? 'selected' : ''}`} onClick={() => update('voiceover_subtitle', opt.value)}>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="step-actions">
            <button className="step-back" onClick={() => setStep(0)}>← 上一步</button>
            <button className="step-next" onClick={() => setStep(2)}>下一步：产品配置 →</button>
          </div>
        </div>
      )}

      {/* ========== Step 2: 产品配置 ========== */}
      {step === 2 && (
        <div className="step-content">
          <div className="step-title">📝 第三步：产品配置</div>
          <div className="step-desc">告诉AI你的产品是什么、卖点和投放市场</div>

          {/* AI分析结果展示 */}
          {analyzing && (
            <div className="ai-analyzing">
              <div className="spinner-sm" />
              <span>AI 正在分析产品图片...</span>
            </div>
          )}
          {aiAnalysis && (
            <div className="ai-analysis-card">
              <div className="ai-analysis-title">🤖 AI 产品分析结果</div>
              {aiAnalysis.product_name && (
                <div className="ai-analysis-row"><span>产品名称：</span><strong>{aiAnalysis.product_name}</strong></div>
              )}
              {aiAnalysis.product_desc && (
                <div className="ai-analysis-row"><span>产品描述：</span>{aiAnalysis.product_desc}</div>
              )}
              {aiAnalysis.selling_points?.length > 0 && (
                <div className="ai-analysis-row">
                  <span>AI推荐卖点：</span>
                  <div className="ai-sp-tags">
                    {aiAnalysis.selling_points.map((sp, i) => (
                      <span key={i} className="ai-sp-tag">{sp}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="config-group">
            <label className="config-label">📦 商品名称 *</label>
            <input className="config-input" value={form.product_name} onChange={e => update('product_name', e.target.value)} placeholder="例：无线蓝牙耳机" />
          </div>

          <div className="config-group">
            <label className="config-label">💡 核心卖点（AI推荐，可编辑修改，可多选）</label>
            {!aiAnalysis && !analyzing && (
              <div className="sp-empty-hint">上传产品图片后，AI将自动分析推荐卖点</div>
            )}
            <div className="sp-ai-list">
              {aiAnalysis?.selling_points?.map((p, i) => {
                const isSelected = (form.selling_points || '').split(',').map(s => s.trim()).includes(p)
                return (
                  <div key={i} className={`sp-ai-row ${isSelected ? 'selected' : ''}`}>
                    <button className={`sp-ai-check ${isSelected ? 'checked' : ''}`} onClick={() => toggleSellingPoint(p)}>
                      {isSelected ? '✓' : ''}
                    </button>
                    <input
                      className="sp-ai-input"
                      value={p}
                      onChange={e => updateAiSellingPoint(i, e.target.value)}
                    />
                    <button className="sp-ai-del" onClick={() => removeAiSellingPoint(i)}>✕</button>
                  </div>
                )
              })}
            </div>
            <div className="custom-input-row">
              <input value={customSellingPoint} onChange={e => setCustomSellingPoint(e.target.value)} placeholder="添加自定义卖点..." onKeyDown={e => e.key === 'Enter' && addCustomSellingPoint()} />
              <button className="add-btn" onClick={addCustomSellingPoint}>+ 添加</button>
            </div>
            {form.selling_points && (
              <div className="selected-tags">
                <span className="tag-label">已选：</span>
                {form.selling_points.split(',').map(s => s.trim()).filter(Boolean).map((s, i) => (
                  <span key={i} className="tag">{s} <span className="tag-x" onClick={() => toggleSellingPoint(s)}>✕</span></span>
                ))}
              </div>
            )}
          </div>

          {/* 级联市场选择器 */}
          <div className="config-group">
            <label className="config-label">🌍 投放市场 & 语言</label>
            <div className="cascade-market">
              {/* 触发按钮 */}
              <div className="cascade-trigger" onClick={() => setMarketOpen(!marketOpen)}>
                <span>{getMarketDisplay() || '请选择投放市场'}</span>
                <span className="cascade-arrow">{marketOpen ? '▲' : '▼'}</span>
              </div>

              {/* 级联面板 */}
              {marketOpen && (
                <div className="cascade-panel">
                  <div className="cascade-left">
                    <div className="cascade-section-title">国家/地区</div>
                    <div className="cascade-list">
                      {Object.entries(MARKET_CASCADE).map(([key, val]) => (
                        <div
                          key={key}
                          className={`cascade-item ${selectedCountry === key ? 'active' : ''}`}
                          onClick={() => selectCountry(key)}
                        >
                          {val.label}
                          <span className="cascade-item-arrow">›</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="cascade-right">
                    <div className="cascade-section-title">语言</div>
                    <div className="cascade-list">
                      {MARKET_CASCADE[selectedCountry]?.languages.map((lang) => (
                        <div
                          key={lang.value}
                          className={`cascade-item ${selectedLang === lang.value ? 'active' : ''}`}
                          onClick={() => selectLanguage(lang.value)}
                        >
                          {lang.label}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
            <div className="market-note">👥 模特将根据投放市场本土化生成，不会复制参考视频人物</div>
          </div>

          <div className="config-group">
            <label className="config-label">🎵 音频 & 文案（可选）</label>
            <div className="config-grid-2">
              <div className="config-field">
                <label>背景音乐风格</label>
                <input value={form.bgm_style} onChange={e => update('bgm_style', e.target.value)} placeholder="电子音乐, 轻快流行" />
              </div>
              <div className="config-field">
                <label>音频选项</label>
                <select value={form.audio_option} onChange={e => update('audio_option', e.target.value)}>
                  <option value="voiceover">口播配音</option>
                  <option value="music">背景音乐</option>
                  <option value="both">配音+音乐</option>
                  <option value="none">无音频</option>
                </select>
              </div>
            </div>
            <div className="config-field full" style={{ marginTop: 8 }}>
              <label>口播/展示文案</label>
              <textarea value={form.video_script} onChange={e => update('video_script', e.target.value)} placeholder="输入口播或展示内容..." rows={3} />
            </div>
          </div>

          <div className="config-group">
            <label className="config-label">🔧 生成控制</label>
            <div className="generate-controls">
              <div className="count-control">
                <label>生成数量</label>
                <input type="range" min={1} max={5} value={form.count} onChange={e => update('count', +e.target.value)} />
                <span className="count-badge">{form.count}</span>
              </div>
              <label className="ai-checkbox">
                <input type="checkbox" checked={form.use_ai} onChange={e => update('use_ai', e.target.checked)} />
                使用 AI 智能生成
              </label>
            </div>
          </div>

          <div className="step-actions">
            <button className="step-back" onClick={() => setStep(1)}>← 上一步</button>
            <button className="step-next" disabled={!canNext()} onClick={() => setStep(3)}>下一步：生成 →</button>
          </div>
        </div>
      )}

      {/* ========== Step 3: 生成结果 ========== */}
      {step === 3 && (
        <div className="step-content">
          <div className="step-title">🚀 第四步：生成提示词</div>
          <div className="step-desc">确认配置后点击生成，AI将为您的产品生成适配目标平台的视频提示词</div>

          <div className="summary-card">
            <div className="summary-row"><span>📦 产品：</span><strong>{form.product_name}</strong></div>
            <div className="summary-row"><span>💡 卖点：</span><strong>{form.selling_points || '未设置'}</strong></div>
            <div className="summary-row"><span>🎯 平台：</span><strong>{PLATFORM_PROFILES[form.platform]?.ratio} {currentProfile.duration}</strong></div>
            <div className="summary-row"><span>🌍 市场：</span><strong>{getMarketDisplay()}</strong></div>
            <div className="summary-row"><span>🖼️ 产品图：</span><strong>{imageFile ? '✅ 已上传' : '❌ 未上传'}</strong></div>
            <div className="summary-row"><span>🎬 参考视频：</span><strong>{videoFile ? '✅ 已上传' : '无'}</strong></div>
          </div>

          <button className="generate-btn-main" onClick={handleGenerate} disabled={loading}>
            {loading ? '⏳ AI 生成中...' : '🚀 生成爆款提示词'}
          </button>

          {loading && (
            <div className="result-loading">
              <div className="spinner" />
              <div>AI 正在分析素材并创作提示词...</div>
            </div>
          )}

          {prompts.length > 0 && (
            <div className="results-area">
              {prompts.map((p, idx) => (
                <div className="result-card" key={idx}>
                  <div className="result-card-header">
                    <span className="result-badge">方案 {p.index || idx + 1}</span>
                    <div className="result-actions">
                      <button className="action-btn adopt" onClick={() => handleAdopt(p.index || idx + 1)} title="采纳此方案">👍 采纳</button>
                      <button className="action-btn violation" onClick={() => setViolationModal({ promptIndex: p.index || idx + 1, historyId })} title="报告违规">⚠️ 违规</button>
                      <button className="copy-btn-sm" onClick={() => handleCopy(idx, p.finalPrompt)}>
                        {copied[idx] ? '✓ 已复制' : '📋 复制'}
                      </button>
                    </div>
                  </div>
                  {p.audit && <div className="result-meta-line"><span className="meta-audit">🛡️ {p.audit}</span></div>}
                  {p.audioPlan && <div className="result-meta-line"><span className="meta-audio">🎧 {p.audioPlan}</span></div>}
                  {p.dynamicStrategy && <div className="result-meta-line"><span className="meta-dynamic">⚡ {p.dynamicStrategy}</span></div>}

                  {/* 分组分段展示 */}
                  {p.promptGroups && p.totalGroups > 1 ? (
                    <div className="prompt-groups">
                      <div className="groups-header">
                        📑 共 {p.totalGroups} 个分段（每段12s），分别传给视频模型
                      </div>
                      {p.promptGroups.map((g, gi) => (
                        <div key={gi} className="prompt-group">
                          <div className="group-label">片段 {gi + 1}/{p.totalGroups}</div>
                          <div className="group-text">{g}</div>
                          <button className="copy-btn-sm" onClick={() => handleCopy(`${idx}-${gi}`, g)}>
                            {copied[`${idx}-${gi}`] ? '✓ 已复制' : '📋 复制此段'}
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="result-prompt-text">{p.finalPrompt}</div>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="step-actions">
            <button className="step-back" onClick={() => setStep(2)}>← 修改配置</button>
            {prompts.length > 0 && <button className="step-next" onClick={handleGenerate} disabled={loading}>🔄 重新生成</button>}
          </div>
        </div>
      )}

      {/* ========== 违规弹窗 ========== */}
      {violationModal && (
        <div className="modal-overlay" onClick={() => setViolationModal(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-title">⚠️ 报告违规 — 方案 {violationModal.promptIndex}</div>
            <div className="modal-desc">违规提示词将被一票否决。违规原因将作为后续生成的约束条件。</div>
            <textarea className="modal-input" value={violationReason} onChange={e => setViolationReason(e.target.value)} placeholder="请描述违规原因，如：含有色情暗示、侵权内容、虚假宣传..." rows={4} />
            <div className="modal-actions">
              <button className="modal-cancel" onClick={() => setViolationModal(null)}>取消</button>
              <button className="modal-confirm" disabled={!violationReason.trim()} onClick={handleViolation}>确认违规</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
