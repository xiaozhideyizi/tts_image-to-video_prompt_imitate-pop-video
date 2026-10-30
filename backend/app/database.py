from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import inspect, text
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
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
            ("video_filename", "VARCHAR(255)"),
            ("video_content_type", "VARCHAR(100)"),
            ("image_data", "BYTEA"),
            ("image_filename", "VARCHAR(255)"),
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
