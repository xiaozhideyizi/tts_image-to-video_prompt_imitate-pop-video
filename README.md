# 动态视频提示词生成器 — 云端版

> 原本地 HTML 工具升级为完整全栈 Web 应用

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 18 + Vite + React Router |
| 后端 | Python FastAPI + SQLAlchemy |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） |
| AI | 智谱 GLM-4-flash |
| 部署 | Vercel（前端）+ Railway/Render（后端）|

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

## 部署到 Vercel + Railway

### 后端部署（Railway 推荐）

1. 在 [Railway](https://railway.app) 创建新项目，连接 GitHub 仓库
2. 选择 `backend` 目录
3. 设置环境变量：
   - `SECRET_KEY` = 随机字符串（可用 `openssl rand -hex 32` 生成）
   - `ZHIPUAI_API_KEY` = 你的智谱 API Key
   - `CORS_ORIGINS` = 你的前端域名（如 `https://your-app.vercel.app`）
   - `DATABASE_URL` = Railway 自动提供的 PostgreSQL URL（改为 `postgresql+asyncpg://...`）
4. 部署完成后记录后端 URL

### 前端部署（Vercel）

1. 在 [Vercel](https://vercel.com) 导入项目
2. 设置 Root Directory 为 `frontend`
3. 设置环境变量：
   - `VITE_API_BASE_URL` = 后端 URL（如 `https://your-backend.railway.app`）
4. 如果使用独立后端，修改 `vite.config.js` 中的 proxy target 为生产后端地址

### 生产数据库切换

将 `backend/.env` 中的 `DATABASE_URL` 改为：
```
postgresql+asyncpg://user:password@host:5432/dbname
```
并安装：`pip install asyncpg`

## 功能列表

- [x] 用户注册 / 登录（JWT）
- [x] 生成提示词（本地规则 + AI 两种模式）
- [x] 历史记录云存储
- [x] 查看 / 展开历史提示词
- [x] 生成分享链接（无需登录可查看）
- [x] 删除历史记录
- [x] 响应式布局（移动端适配）

## 项目结构

```
prompt-generator-cloud/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口
│   │   ├── config.py        # 配置
│   │   ├── database.py      # 数据库连接
│   │   ├── models.py        # 数据模型
│   │   ├── auth.py          # JWT 鉴权
│   │   └── routers/
│   │       ├── auth.py      # 注册/登录接口
│   │       └── prompts.py   # 生成/历史接口
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api/             # API 封装
│   │   ├── context/         # 全局状态
│   │   ├── components/      # 布局组件
│   │   └── pages/           # 页面
│   ├── package.json
│   └── vite.config.js
└── vercel.json
```
