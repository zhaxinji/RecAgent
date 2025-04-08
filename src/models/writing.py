from sqlalchemy import Boolean, Column, String, Integer, DateTime, ForeignKey, Text, JSON, Enum, Table
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
import uuid
import enum
import logging

from src.db.base import Base

# 项目-协作者关联表
project_collaborators = Table(
    'project_collaborators',
    Base.metadata,
    Column('project_id', String, ForeignKey('writing_projects.id', ondelete="CASCADE")),
    Column('user_id', String, ForeignKey('users.id', ondelete="CASCADE")),
    extend_existing=True
)

class ProjectStatus(enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class WritingProject(Base):
    """写作项目模型"""
    __tablename__ = "writing_projects"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)  # 描述字段，也用于存储额外元数据
    status = Column(Enum(ProjectStatus), default=ProjectStatus.DRAFT)
    target_word_count = Column(Integer, nullable=True)
    current_word_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deadline = Column(DateTime(timezone=True), nullable=True)
    
    # 外键
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    
    # 关系
    owner = relationship("User", back_populates="writing_projects")
    sections = relationship("WritingSection", back_populates="project")
    references = relationship("WritingReference", back_populates="project")
    invites = relationship("CollaborationInvite", back_populates="project")
    collaborators = relationship("User", secondary=project_collaborators, back_populates="collaborated_projects")
    
    @property
    def related_papers(self):
        """从描述中提取相关论文列表"""
        if not self.description:
            return []
            
        import re
        import json
        
        try:
            if "<!-- METADATA:" not in self.description:
                return []
                
            meta_match = re.search(r'<!-- METADATA: (.*?) -->', self.description)
            if not meta_match:
                return []
                
            metadata_str = meta_match.group(1)
            if not metadata_str or metadata_str.isspace():
                return []
                
            metadata = json.loads(metadata_str)
            if not isinstance(metadata, dict):
                return []
                
            if "related_papers" in metadata and isinstance(metadata["related_papers"], list):
                return metadata["related_papers"]
            else:
                return []
        except json.JSONDecodeError:
            logging.warning(f"JSON解析错误: 项目 {self.id} 的元数据格式不正确")
            return []
        except Exception as e:
            logging.warning(f"提取项目 {self.id} 的相关论文时出错: {str(e)}")
            return []
    
    def to_dict(self):
        """将项目转换为字典表示"""
        # 提取元数据
        metadata = {}
        try:
            if self.description and "<!-- METADATA:" in self.description:
                import re
                import json
                meta_match = re.search(r'<!-- METADATA: (.*?) -->', self.description)
                if meta_match:
                    metadata = json.loads(meta_match.group(1))
                    if not isinstance(metadata, dict):
                        metadata = {}
        except Exception as e:
            logging.warning(f"提取项目 {self.id} 元数据时出错: {str(e)}")
        
        # 确保metadata中包含related_papers
        related_papers = self.related_papers
        if related_papers:
            metadata['related_papers'] = related_papers
            
        # 确保metadata是有效的字典
        if not isinstance(metadata, dict):
            metadata = {}
            
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "owner_id": self.owner_id,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "related_papers": related_papers,
            "metadata": metadata,
            "collaborators": [
                {
                    "id": c.id,
                    "name": c.name,
                    "email": c.email
                } for c in self.collaborators
            ] if self.collaborators else []
        }

class WritingSection(Base):
    """写作章节模型"""
    __tablename__ = "writing_sections"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    order = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 外键
    project_id = Column(String, ForeignKey("writing_projects.id", ondelete="CASCADE"))
    parent_id = Column(String, ForeignKey("writing_sections.id", ondelete="SET NULL"), nullable=True)
    
    # 关系
    project = relationship("WritingProject", back_populates="sections")
    children = relationship("WritingSection", 
                           backref=backref("parent", remote_side=[id]),
                           cascade="all, delete-orphan")
    
class WritingReference(Base):
    """写作引用模型，存储引用的论文或网页内容"""
    __tablename__ = "writing_references"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=True)
    source_type = Column(String, nullable=False)  # 'paper', 'webpage', 'book', etc.
    content = Column(Text, nullable=True)  # 引用的内容
    url = Column(String, nullable=True)
    citation_key = Column(String, nullable=True)  # 引用键，用于学术格式引用
    reference_metadata = Column(JSON, nullable=True)  # 附加元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 外键
    project_id = Column(String, ForeignKey("writing_projects.id", ondelete="CASCADE"))
    
    # 关系
    project = relationship("WritingProject", back_populates="references")

class CollaborationInvite(Base):
    """协作邀请模型"""
    __tablename__ = "collaboration_invites"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("writing_projects.id", ondelete="CASCADE"))
    inviter_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    invitee_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    invitee_email = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, accepted, rejected
    message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # 关系
    project = relationship("WritingProject", back_populates="invites")
    inviter = relationship("User", foreign_keys=[inviter_id])
    invitee = relationship("User", foreign_keys=[invitee_id]) 