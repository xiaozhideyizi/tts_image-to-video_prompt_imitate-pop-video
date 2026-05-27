from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

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
    created_at = Column(DateTime, server_default=func.now())
    share_token = Column(String(64), unique=True, nullable=True)

    # 文件存储（二进制存 PostgreSQL）
    video_data = Column(LargeBinary, nullable=True)
    video_filename = Column(String(255), nullable=True)
    video_content_type = Column(String(100), nullable=True)
    image_data = Column(LargeBinary, nullable=True)
    image_filename = Column(String(255), nullable=True)
    image_content_type = Column(String(100), nullable=True)

    # 评测指标
    generated_count = Column(Integer, default=0)     # 生成提示词数量
    adopted_count = Column(Integer, default=0)        # 被采纳次数
    violation_reason = Column(Text, nullable=True)    # 违规原因（一票否决）
    style_weights = Column(Text, nullable=True)       # JSON: 风格权重 {"camera_x":1.2, ...}

    owner = relationship("User", back_populates="histories")
