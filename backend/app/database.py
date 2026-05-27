from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import text
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
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
        for col_name, col_type in migrations:
            try:
                await conn.execute(
                    text(f"ALTER TABLE prompt_histories ADD COLUMN {col_name} {col_type}")
                )
                print(f"[MIGRATION] Added column: prompt_histories.{col_name}")
            except Exception:
                # 字段已存在则跳过
                pass
