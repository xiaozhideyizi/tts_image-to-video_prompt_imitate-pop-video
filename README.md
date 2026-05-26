**#TikTok爆款复刻机**

> 从本地 HTML 工具升级为完整全栈 Web 应用，支持用户体系、AI 生成、云端存储与团队分享

## 在线访问

- **前端**: https://advideo-imitate.netlify.app
- **后端 API**: https://incredible-alignment-production-4ba5.up.railway.app
- **API 文档**: https://incredible-alignment-production-4ba5.up.railway.app/docs

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | React 18 + Vite + React Router | SPA 单页应用，响应式布局 |
| **后端** | Python FastAPI + Uvicorn | 异步高性能 API 服务 |
| **数据库** | PostgreSQL (生产) / SQLite (开发) | SQLAlchemy async ORM + asyncpg 驱动 |
| **AI 引擎** | 智谱 GLM-4-flash | AI 提示词生成，本地规则降级兜底 |
| **认证** | JWT (python-jose + passlib/bcrypt) | 注册/登录/Token 鉴权 |
| **前端部署** | Netlify | 自动构建 + CDN 加速 |
| **后端部署** | Railway | Docker 容器 + 托管 PostgreSQL |
| **代码仓库** | GitHub | xiaozhideyizi/tts_image-to-video_prompt_imitate-pop-video |

## 快速启动（本地开发）

### 1. 启动后端

```bash
cd backend

# 创建 .env 文件
cp .env.example .env
# 编辑 .env，填入你的 ZHIPUAI_API_KEY

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --port 8000
```

后端运行在 http://localhost:8000
API 文档在 http://localhost:8000/docs

### 2. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端运行在 http://localhost:5173

## 部署指南

### 后端部署（Railway）

1. 在 [Railway](https://railway.app) 创建新项目，连接 GitHub 仓库
2. 设置 **Root Directory** 为 `backend`
3. 添加 PostgreSQL 服务
4. 设置环境变量：
   - `SECRET_KEY` = 随机字符串（`openssl rand -hex 32`）
   - `ZHIPUAI_API_KEY` = 你的智谱 API Key
   - `DATABASE_URL` = Railway PostgreSQL 提供的连接字符串（代码自动转换 `postgres://` → `postgresql+asyncpg://`）
   - `CORS_ORIGINS` = 前端域名（如 `https://advideo-imitate.netlify.app`）
5. Builder 选 **Nixpacks**，startCommand: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`

> ⚠️ 注意：Railway `rootDirectory=backend` 时，startCommand **不能**包含 `cd backend`

### 前端部署（Netlify）

1. 在 [Netlify](https://netlify.com) 导入 GitHub 仓库
2. Build settings:
   - Base directory: `frontend`
   - Build command: `npm run build`
   - Publish directory: `frontend/dist`
3. 环境变量：
   - `VITE_API_URL` = 后端 URL（如 `https://your-backend.railway.app`）

## 功能列表

- [x] 用户注册 / 登录（JWT 鉴权）
- [x] 本地规则模式生成提示词（无需 API Key）
- [x] AI 模式生成提示词（智谱 GLM-4-flash）
- [x] AI 失败自动降级到本地规则
- [x] 历史记录云存储（PostgreSQL）
- [x] 生成分享链接（无需登录可查看）
- [x] 删除历史记录
- [x] 响应式布局（移动端适配）

## 项目结构

```
prompt-generator-cloud/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口 + 生命周期
│   │   ├── config.py        # 环境变量配置 + DB URL 自动转换
│   │   ├── database.py      # 异步数据库引擎
│   │   ├── models.py        # SQLAlchemy 模型 (User, PromptHistory)
│   │   ├── auth.py          # JWT 创建/验证 + 密码哈希
│   │   └── routers/
│   │       ├── auth.py      # POST /api/auth/register, /token; GET /me
│   │       └── prompts.py   # POST /generate; GET /history; POST/GET /share
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # 路由配置
│   │   ├── api/              # API 客户端封装
│   │   │   ├── client.js     # Axios 实例 + Token 拦截器
│   │   │   └── index.js      # API 方法导出
│   │   ├── context/          # React Context
│   │   │   └── AuthContext.jsx  # 登录状态管理
│   │   ├── components/
│   │   │   └── Layout.jsx    # 全局布局 + 导航
│   │   └── pages/
│   │       ├── LoginPage.jsx     # 登录/注册
│   │       ├── GeneratorPage.jsx # 提示词生成器
│   │       ├── HistoryPage.jsx   # 历史记录
│   │       └── SharePage.jsx     # 分享查看
│   ├── package.json
│   └── vite.config.js
├── railway.toml              # Railway 部署配置
└── vercel.json               # Netlify 部署配置
```

## API 概览

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/auth/register` | 用户注册 | ❌ |
| POST | `/api/auth/token` | 用户登录 | ❌ |
| GET | `/api/auth/me` | 获取当前用户 | ✅ |
| POST | `/api/prompts/generate` | 生成提示词 | ✅ |
| GET | `/api/prompts/history` | 查询历史记录 | ✅ |
| POST | `/api/prompts/history/{id}/share` | 生成分享链接 | ✅ |
| GET | `/api/prompts/share/{token}` | 查看分享内容 | ❌ |
| DELETE | `/api/prompts/history/{id}` | 删除历史记录 | ✅ |
| GET | `/health` | 健康检查 | ❌ |
