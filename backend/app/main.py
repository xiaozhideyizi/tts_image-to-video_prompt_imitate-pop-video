import sys
import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import init_db
from app.config import settings
from app.routers import auth, prompts


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print(f"[STARTUP] CORS origins: {settings.cors_origins_list}")
        print(f"[STARTUP] Connecting to database: {settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url}")
        await init_db()
        print("[STARTUP] Database initialized successfully.")
    except Exception as e:
        print(f"[STARTUP ERROR] Database init failed: {e}", file=sys.stderr)
        traceback.print_exc()
        # 不阻止应用启动，让非数据库接口仍可访问
    yield


app = FastAPI(
    title="广告爆款复刻机 API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(prompts.router)


@app.get("/")
async def root():
    return {"status": "ok", "message": "广告爆款复刻机 API v2.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
