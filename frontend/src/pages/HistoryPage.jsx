import { useEffect, useState } from 'react'
import { promptApi } from '../api'

export default function HistoryPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [shareLinks, setShareLinks] = useState({})
  const [expanded, setExpanded] = useState({})

  const load = async () => {
    setLoading(true)
    try {
      const res = await promptApi.getHistory()
      setItems(res.data.items)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleShare = async (id) => {
    if (shareLinks[id]) return
    try {
      const res = await promptApi.createShareLink(id)
      const token = res.data.share_token
      const url = `${window.location.origin}/share/${token}`
      setShareLinks(s => ({ ...s, [id]: url }))
    } catch {
      alert('生成分享链接失败')
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('确认删除这条记录？')) return
    try {
      await promptApi.deleteHistory(id)
      setItems(i => i.filter(h => h.id !== id))
    } catch {
      alert('删除失败')
    }
  }

  const toggleExpand = (id) => setExpanded(e => ({ ...e, [id]: !e[id] }))

  const formatDate = (iso) => {
    const d = new Date(iso)
    return d.toLocaleString('zh-CN')
  }

  if (loading) return (
    <div style={{textAlign:'center',paddingTop:80}}>
      <div className="spinner" style={{margin:'0 auto 16px'}} />
      <div>加载中...</div>
    </div>
  )

  return (
    <div>
      <h1 className="page-title" style={{marginBottom:28}}>📋 生成历史</h1>
      {items.length === 0 ? (
        <div className="empty-state">
          <div className="icon">🗂️</div>
          <div>还没有生成记录，去生成第一个提示词吧！</div>
        </div>
      ) : (
        <div className="history-list">
          {items.map(h => {
            const prompts = JSON.parse(h.prompts_json || '[]')
            return (
              <div key={h.id} className="history-card" style={{flexDirection:'column',alignItems:'stretch'}}>
                <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',gap:16}}>
                  <div className="history-card-info">
                    <h3>{h.product_name}</h3>
                    <p>{formatDate(h.created_at)} · 共 {prompts.length} 条方案</p>
                  </div>
                  <div className="history-card-actions">
                    <button className="btn-sm btn-ghost" onClick={() => toggleExpand(h.id)}>
                      {expanded[h.id] ? '收起' : '查看'}
                    </button>
                    <button className="btn-sm btn-ghost" onClick={() => handleShare(h.id)}>
                      🔗 分享
                    </button>
                    <button className="btn-sm btn-danger" onClick={() => handleDelete(h.id)}>
                      删除
                    </button>
                  </div>
                </div>

                {shareLinks[h.id] && (
                  <div className="share-banner">
                    ✅ 分享链接已生成：<br />
                    <a href={shareLinks[h.id]} target="_blank" rel="noreferrer" style={{color:'#00d4ff'}}>
                      {shareLinks[h.id]}
                    </a>
                    <button className="btn-sm btn-ghost" style={{marginLeft:10,fontSize:'0.8em'}} onClick={() => navigator.clipboard.writeText(shareLinks[h.id])}>
                      复制
                    </button>
                  </div>
                )}

                {expanded[h.id] && (
                  <div style={{marginTop:14,display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(300px,1fr))',gap:12}}>
                    {prompts.map((p, i) => (
                      <div key={i} style={{background:'rgba(0,0,0,0.3)',borderRadius:10,padding:14}}>
                        <div style={{fontWeight:'bold',color:'#00d4ff',marginBottom:8,fontSize:'0.9em'}}>方案 {p.index || i+1}</div>
                        <div style={{fontSize:'0.82em',lineHeight:1.6,color:'#ccc',whiteSpace:'pre-wrap'}}>{p.finalPrompt}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
