<div align="center">

# 🎬 PopVideo Prompt Generator

### AI驱动的短视频提示词生成器 — 上传素材，一键生成爆款视频提示词

[![Live Demo](https://img.shields.io/badge/🚀_在线体验-Live_Demo-blue?style=for-the-badge)](https://advideo-imitate.netlify.app)
[![Backend API](https://img.shields.io/badge/📖_API文档-Swagger-green?style=flat-square)](https://incredible-alignment-production-4ba5.up.railway.app/docs)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

</div>

---

## ✨ 一句话介绍

**PopVideo Prompt Generator** 是一个全栈 AI 应用，帮你从"想做一个短视频"到"拿到可直接投喂给视频生成模型的提示词"，全程不超过 30 秒。上传产品图片或参考视频，选择目标平台，AI 自动分析素材并生成多风格、高还原度的视频提示词。

## 🎯 它解决了什么问题？

做短视频最难的不是拍，是**写提示词**。把一个产品卖点转化成 AI 视频生成模型（Kling、Seedance、Google Veo）能理解的专业提示词，通常需要：
- 🕐 反复试错 30+ 分钟
- 📝 手写 500+ 词的英文描述
- 🔄 多次调整风格、分镜、转场
- 🌍 针对不同平台重新适配（抖音竖屏 vs B站横屏）

**PopVideo 把这个过程压缩到一次点击。**

## 🖼️ 功能亮点

| 功能 | 说明 |
|------|------|
| 🤖 **AI 图片分析** | 上传产品图，自动识别产品名称、卖点、使用场景 |
| 🎨 **8 种风格模板** | 痛点解决流 / UGC种草风 / 产品场景展示 / 暴力测试风 / 情绪共鸣流 / 极速快剪流 / 高端大片风 / 搞笑反转风 |
| 📐 **12 平台适配** | 抖音 / 小红书 / TikTok / Instagram / YouTube Shorts / 淘宝 / 京东 等 |
| 🌏 **20+ 市场语言** | 中国大陆 / 美国 / 日本 / 东南亚 / 中东 等，自动匹配语言和风格 |
| 🎬 **智能分段** | 根据视频模型（Kling 15s / Seedance 15s / Google Veo 10s）自动拆分镜头 |
| 🔄 **AI 降级兜底** | 智谱 API 超时/失败时自动切换本地规则引擎，保证 100% 可用 |
| 📜 **历史记录** | 云端存储生成历史，随时回溯 |
| 🔗 **一键分享** | 生成分享链接，团队无需登录即可查看 |

## 🚀 在线体验

**👉 [https://advideo-imitate.netlify.app](https://advideo-imitate.netlify.app)**

1. 选择目标平台（如：抖音）
2. 输入产品名称 + 卖点（或上传图片让 AI 自动识别）
3. 点击生成 → 秒出 3 条风格各异的提示词
4. 复制提示词，投喂给你的视频生成模型

## 🛠️ 技术栈

```
Frontend:  React 18 · Vite · React Router 6 · Axios
Backend:   Python FastAPI · Uvicorn · SQLAlchemy (async) · asyncpg
AI:        智谱 GLM-4-flash / GLM-4V-flash + 本地规则引擎降级
Auth:      JWT (python-jose + bcrypt)
Database:  PostgreSQL (生产) · SQLite (开发)
Deploy:    Netlify (前端) · Railway (后端)
```

### 架构亮点

- **异步全链路**：FastAPI + asyncpg + SQLAlchemy async，从请求到数据库全异步无阻塞
- **AI 超时保护**：`asyncio.wait_for` 90s 超时 + 自动降级，杜绝前端超时
- **零依赖提示词引擎**：本地规则引擎 500+ 词输出，不依赖任何外部 API 也能生成专业提示词
- **平台感知**：每个平台有独立配置（分辨率、时长、画幅比、语言），提示词自动适配
- **智能风格匹配**：基于关键词评分的 `_match_style_label()` 算法，根据产品语义自动分配最合适的视频风格

## ⚡ 快速开始

### 本地开发

```bash
# 1. 启动后端
cd backend
cp .env.example .env          # 填入 ZHIPUAI_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 2. 启动前端
cd frontend
npm install
npm run dev
```

### 一键部署

<details>
<summary>📱 Railway + Netlify 部署（5 分钟）</summary>

**后端 (Railway)：**
1. 新建项目 → 连接 GitHub 仓库
2. Root Directory 设为 `backend`
3. 添加 PostgreSQL 服务
4. 环境变量：`SECRET_KEY` / `ZHIPUAI_API_KEY` / `DATABASE_URL`
5. Builder: Nixpacks，Start: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`

**前端 (Netlify)：**
1. 导入 GitHub 仓库
2. Base directory: `frontend` / Build: `npm run build` / Publish: `frontend/dist`
3. 环境变量：`VITE_API_URL` = 你的 Railway 后端 URL

</details>

## 📁 项目结构

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口 + CORS + 生命周期
│   │   ├── config.py            # Pydantic Settings 环境变量
│   │   ├── database.py          # 异步引擎 + 会话工厂
│   │   ├── models.py            # User / PromptHistory ORM
│   │   ├── auth.py              # JWT + bcrypt 鉴权
│   │   └── routers/
│   │       ├── auth.py          # 注册 / 登录 / 用户信息
│   │       └── prompts.py       # 核心：提示词生成 + AI 降级 + 风格匹配
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                 # Axios 封装 + Token 拦截器
│   │   ├── context/             # AuthContext 登录态管理
│   │   ├── components/          # Layout 全局布局
│   │   └── pages/
│   │       ├── GeneratorPage.jsx  # 🎯 核心页面：步骤式生成器
│   │       ├── HistoryPage.jsx    # 历史记录
│   │       └── SharePage.jsx      # 分享查看
│   └── vite.config.js
├── railway.toml
└── netlify.toml
```

## 🧠 核心算法

### 提示词生成流程

```
用户输入 → 平台配置注入 → AI/本地双通道
  ├── AI 通道：GLM-4-flash 生成 → JSON 解析 → 后处理校验 → 输出
  └── 本地通道：500+ 词规则引擎 → 风格智能匹配 → 分段拆分 → 输出
```

### 风格智能匹配

基于产品名称和卖点的关键词评分系统，自动匹配最合适的视频风格：

| 风格 | 典型关键词 |
|------|-----------|
| 痛点解决流 | 痛点、问题、解决、困扰 |
| UGC种草风 | 推荐种草、真实、亲测 |
| 暴力测试风 | 耐用、防水、防摔、极限 |
| 情绪共鸣流 | 温馨、感动、治愈、催泪 |
| 高端大片风 | 奢华、质感、高端、旗舰 |
| 搞笑反转风 | 搞笑、反转、意想不到 |

## 📊 API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/prompts/generate` | 生成提示词（支持图片/视频上传） |
| POST | `/api/prompts/analyze-image` | AI 图片分析 → 产品信息 |
| GET | `/api/prompts/history` | 查询历史记录 |
| POST | `/api/prompts/history/{id}/share` | 生成分享链接 |
| GET | `/api/prompts/share/{token}` | 查看分享（无需登录） |
| GET | `/health` | 健康检查 |

完整文档：[Swagger UI](https://incredible-alignment-production-4ba5.up.railway.app/docs)

## 🤝 贡献

欢迎 PR！开发流程：

1. Fork → 2. Feature Branch → 3. Commit → 4. PR

## 📄 License

MIT License - 自由使用、修改和分发。

---

<div align="center">

**如果这个项目对你有帮助，给个 ⭐ Star 吧！**

Made with ❤️ for short-video creators

</div>
