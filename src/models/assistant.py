from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Enum, Boolean, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from src.db.base import Base

class MessageRole(enum.Enum):
    """消息角色枚举"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    
class AssistantType(str, enum.Enum):
    """研究助手类型枚举"""
    GENERAL = "general"               # 一般对话
    RESEARCH_GAP = "research_gap"     # 研究空白分析
    INNOVATION = "innovation"         # 创新点生成
    EXPERIMENT = "experiment"         # 实验设计
    WRITING = "writing"               # 论文写作辅助

class AssistantSession(Base):
    """研究助手会话模型"""
    __tablename__ = "assistant_sessions"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    session_type = Column(Enum(AssistantType), default=AssistantType.GENERAL)
    context = Column(JSON, nullable=True)  # 会话相关上下文，如研究领域、参考论文等
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    
    # 外键
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    
    # 关系
    owner = relationship("User", backref="assistant_sessions")
    messages = relationship("AssistantMessage", back_populates="session", cascade="all, delete-orphan")
    
    # 可能关联的论文
    paper_id = Column(String, ForeignKey("papers.id", ondelete="SET NULL"), nullable=True)
    paper = relationship("Paper", backref="assistant_sessions")
    
    # 会话结果
    result = Column(JSON, nullable=True)  # 会话结果，如研究空白分析、创新点等
    
class AssistantMessage(Base):
    """助手消息模型"""
    __tablename__ = "assistant_messages"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)  # 消息元数据，如建议、引用等
    sequence = Column(Integer, nullable=False)  # 消息序号，用于排序
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 外键
    session_id = Column(String, ForeignKey("assistant_sessions.id", ondelete="CASCADE"))
    
    # 关系
    session = relationship("AssistantSession", back_populates="messages")

class ResearchAnalysis(Base):
    """研究分析模型，存储研究空白、创新点等分析结果"""
    __tablename__ = "research_analysis"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    analysis_type = Column(String, nullable=False)  # 分析类型，如"research_gap"，"innovation"等
    title = Column(String, nullable=False)
    domain = Column(String, nullable=True)  # 研究领域
    summary = Column(Text, nullable=True)  # 分析摘要
    content = Column(JSON, nullable=False)  # 详细分析内容
    references = Column(JSON, nullable=True)  # 引用的文献
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 外键
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    session_id = Column(String, ForeignKey("assistant_sessions.id", ondelete="SET NULL"), nullable=True)
    
    # 关系
    owner = relationship("User", backref="research_analysis")
    session = relationship("AssistantSession", backref="analysis_results")

class ConceptExplanation(Base):
    """概念解释模型，用于缓存常用概念的解释"""
    __tablename__ = "concept_explanations"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    concept = Column(String, nullable=False, index=True)
    explanation = Column(Text, nullable=False)
    references = Column(JSON, nullable=True)  # 引用的文献或资料
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    access_count = Column(Integer, default=0)  # 访问计数，用于缓存管理
    
    # 新增字段
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    paper_id = Column(String, ForeignKey("papers.id", ondelete="SET NULL"), nullable=True)
    context = Column(Text, nullable=True)  # 提供的上下文
    
    # 关系
    user = relationship("User", backref="concept_explanations")
    paper = relationship("Paper", backref="concept_explanations") 