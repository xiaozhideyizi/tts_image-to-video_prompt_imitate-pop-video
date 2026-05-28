from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    SECRET_KEY: str = "dev-secret-key-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 天
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"
    ZHIPUAI_API_KEY: str = ""
    CORS_ORIGINS: str = (
        "http://localhost:5173,"
        "https://advideo-imitate.netlify.app,"
        "https://superb-babka-50ca8d.netlify.app,"
        "*"
    )

    @property
    def database_url(self) -> str:
        """自动转换 postgres:// → postgresql+asyncpg://"""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
