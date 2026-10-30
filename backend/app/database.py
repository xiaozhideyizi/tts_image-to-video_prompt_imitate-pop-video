from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
import ssl
from app.config import settings


def database_connection_options(raw_url):
    url = make_url(raw_url)
    options = {"echo": False, "pool_pre_ping": True}
    if url.drivername == "postgresql+asyncpg":
        query = dict(url.query)
        ssl_mode = query.pop("sslmode", None)
        # Neon 的 libpq 连接串包含此参数，asyncpg 不接受该关键字。
        query.pop("channel_binding", None)
        connect_args = {"timeout": 15, "command_timeout": 30}
        if ssl_mode:
            if ssl_mode == "disable":
                connect_args["ssl"] = False
            elif ssl_mode in {"require", "verify-ca", "verify-full"}:
                # 云端始终验证服务器证书和主机名。
                connect_args["ssl"] = ssl.create_default_context()
            else:
                raise ValueError("请使用 sslmode=require 或 verify-full 连接云端 PostgreSQL")
        url = url.set(query=query)
        options.update(connect_args=connect_args, pool_recycle=240, pool_size=3, max_overflow=2)
    return url, options


database_url, engine_options = database_connection_options(settings.database_url)
engine = create_async_engine(database_url, **engine_options)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        from app import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
        
        # 自动迁移：为已有的 prompt_histories 表添加新字段（如果不存在）
        migrations = [
            # 原有字段
            ("platform", "VARCHAR(50)"),
            ("voiceover_subtitle", "VARCHAR(50)"),
            ("audio_option", "VARCHAR(50)"),
            ("video_model", "VARCHAR(50)"),
            # 文件存储字段
            ("video_data", "BYTEA"),
            ("video_filename", "TEXT"),
            ("video_content_type", "VARCHAR(100)"),
            ("image_data", "BYTEA"),
            ("image_filename", "TEXT"),
            ("image_content_type", "VARCHAR(100)"),
            # 评测指标字段
            ("generated_count", "INTEGER DEFAULT 0"),
            ("adopted_count", "INTEGER DEFAULT 0"),
            ("violation_reason", "TEXT"),
            ("style_weights", "TEXT"),
        ]
        existing_columns = await conn.run_sync(
            lambda sync_conn: {
                column["name"]
                for column in inspect(sync_conn).get_columns("prompt_histories")
            }
        )
        for col_name, col_type in migrations:
            if col_name in existing_columns:
                continue
            # PostgreSQL 中捕获重复字段异常也会使整个事务失效，因此先查表结构。
            await conn.execute(
                text(f"ALTER TABLE prompt_histories ADD COLUMN {col_name} {col_type}")
            )
            print(f"[MIGRATION] Added column: prompt_histories.{col_name}")
