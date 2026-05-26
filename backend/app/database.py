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
        
        # 自动迁移：为已有的 prompt_history 表添加新字段（如果不存在）
        migrations = [
            ("platform", "VARCHAR(50)"),
            ("voiceover_subtitle", "VARCHAR(50)"),
            ("audio_option", "VARCHAR(50)"),
        ]
        for col_name, col_type in migrations:
            try:
                await conn.execute(
                    text(f"ALTER TABLE prompt_history ADD COLUMN {col_name} {col_type}")
                )
                print(f"[MIGRATION] Added column: prompt_history.{col_name}")
            except Exception:
                # 字段已存在则跳过
                pass
