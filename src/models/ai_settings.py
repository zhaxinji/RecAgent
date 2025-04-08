from sqlalchemy import Column, String, DateTime, Boolean, JSON, Table, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from src.db.base import Base

class AISettings(Base):
    __tablename__ = "ai_settings"
    __table_args__ = {'extend_existing': True}
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    default_provider = Column(String, default="deepseek")
    openai_api_key = Column(String, nullable=True)
    deepseek_api_key = Column(String, nullable=True)
    claude_api_key = Column(String, nullable=True)
    custom_settings = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    user = relationship("User", back_populates="ai_settings")
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value) 