import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { promptApi } from '../api'

export default function SharePage() {
  const { token } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    promptApi.getShared(token)
      .then(res => setData(res.data))
      .catch(() => setError('分享链接无效或已失效'))
  }, [token])

  if (error) return (
    <div style={{textAlign:'center',paddingTop:100,color:'#ff8080'}}>{error}</div>
  )

  if (!data) return (
    <div style={{textAlign:'center',paddingTop:80}}>
      <div className="spinner" style={{margin:'0 auto 16px'}} />
      <div>加载中...</div>
    </div>
  )

  const prompts = JSON.parse(data.prompts_json || '[]')

  return (
    <div style={{maxWidth:1200,margin:'0 auto',padding:30}}>
      <h1 className="page-title">🎬 {data.product_name}</h1>
      <p style={{textAlign:'center',color:'#888',marginBottom:28,fontSize:'0.9em'}}>
        分享自 · {new Date(data.created_at).toLocaleString('zh-CN')}
      </p>
      <div className="results-section">
        {prompts.map((p, i) => (
          <div className="result-card" key={i}>
            <div className="result-header">
              <span className="result-number">方案 {p.index || i+1}</span>
              <button className="copy-btn" onClick={() => navigator.clipboard.writeText(p.finalPrompt)}>📋 复制</button>
            </div>
            {p.audioPlan && (
              <div className="av-plan-section">
                <h4>🎧 视听方案</h4>
                {p.audioPlan}
              </div>
            )}
            <div className="prompt-content">{p.finalPrompt}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
