from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    histories = relationship("PromptHistory", back_populates="owner", cascade="all, delete-orphan")


class PromptHistory(Base):
    __tablename__ = "prompt_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_name = Column(String(255), nullable=False)
    target_market = Column(String(50))
    target_language = Column(String(50))
    platform = Column(String(50))
    voiceover_subtitle = Column(String(50))
    selling_points = Column(Text)
    video_script = Column(Text)
    bgm_style = Column(String(255))
    audio_option = Column(String(50))
    prompts_json = Column(Text)  # JSON 字符串，存储生成的所有提示词
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    share_token = Column(String(64), unique=True, nullable=True)  # 分享链接 token

    owner = relationship("User", back_populates="histories")
