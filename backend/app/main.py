import logging
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text
from app.database import init_db, engine
from app.routers import auth, prompts


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 数据库不可用时让部署明确失败，避免一个无法登录的实例被判定健康。
    await init_db()
    app.state.database_ready = True
    try:
        yield
    finally:
        app.state.database_ready = False
        await engine.dispose()


app = FastAPI(
    title="广告爆款复刻机 API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS - 直接允许所有来源（demo项目，简化部署）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth.router)
app.include_router(prompts.router)


@app.get("/")
async def root():
    return {"status": "ok", "message": "广告爆款复刻机 API v2.0"}


@app.get("/health")
async def health():
    if not getattr(app.state, "database_ready", False):
        raise HTTPException(status_code=503, detail="数据库尚未就绪")
    try:
        async def check_database():
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        await asyncio.wait_for(check_database(), timeout=5)
    except Exception:
        logging.getLogger(__name__).exception("Database health check failed")
        raise HTTPException(status_code=503, detail="数据库暂时不可用")
    return {"status": "healthy", "database": "ok"}
