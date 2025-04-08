from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, func, Text
from sqlalchemy.orm import relationship, validates
from sqlalchemy.schema import Table
import re

try:
    from ..db.base import Base
except ImportError:
    from agent_rec.src.db.base import Base

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    avatar = Column(String, nullable=True)
    profile = Column(JSON, nullable=True, default=dict)
    
    # 密码重置相关
    password_reset_token = Column(String, nullable=True, index=True)
    password_reset_expires = Column(DateTime, nullable=True)
    email_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)

    # 关系
    papers = relationship("Paper", back_populates="owner", cascade="all, delete-orphan")
    experiments = relationship("Experiment", back_populates="owner", cascade="all, delete-orphan")
    writing_projects = relationship("WritingProject", back_populates="owner", cascade="all, delete-orphan")
    collaborated_projects = relationship("WritingProject", secondary="project_collaborators", back_populates="collaborators")
    tags = relationship("Tag", back_populates="owner", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="owner", cascade="all, delete-orphan")
    folders = relationship("Folder", back_populates="owner", cascade="all, delete-orphan")
    ai_settings = relationship("AISettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        # 确保profile字段存在并初始化
        if 'profile' not in kwargs:
            kwargs['profile'] = {}
        
        # 设置默认值
        profile = kwargs.get('profile', {})
        if not profile:
            profile = {}
            
        # 添加默认的扩展信息
        if 'institution' not in profile:
            profile['institution'] = ""
        if 'research_interests' not in profile:
            profile['research_interests'] = []
        if 'website' not in profile:
            profile['website'] = ""
        if 'location' not in profile:
            profile['location'] = ""
        if 'bio' not in profile:
            profile['bio'] = ""
        if 'social_links' not in profile:
            profile['social_links'] = {}
            
        kwargs['profile'] = profile
        
        # 设置所有属性
        for key, value in kwargs.items():
            setattr(self, key, value)
            
    @validates('email')
    def validate_email(self, key, email):
        if not email:
            raise ValueError("邮箱不能为空")
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("邮箱格式不正确")
        return email
        
    def to_dict(self):
        """将用户对象转换为字典"""
        # 获取用户的profile数据，如果不存在则创建空字典
        profile = getattr(self, 'profile', {}) or {}
        
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "created_at": self.created_at,
            "email_verified": self.email_verified,
            "avatar": self.avatar,
            "institution": self.get_institution(),
            "research_interests": self.get_research_interests(),
            "website": profile.get("website", ""),
            "location": profile.get("location", ""),
            "bio": profile.get("bio", ""),
            "social_links": profile.get("social_links", {}),
            "projects_count": len(self.writing_projects) if self.writing_projects else 0,
            "papers_count": len(self.papers) if self.papers else 0,
            "experiments_count": len(self.experiments) if self.experiments else 0
        }

    def get_research_interests(self) -> list:
        """获取用户的研究方向列表"""
        if not hasattr(self, 'profile') or self.profile is None:
            return []
        
        interests = self.profile.get('research_interests', [])
        
        # 确保返回的是列表
        if isinstance(interests, str):
            # 如果是字符串，尝试按逗号分割
            return [i.strip() for i in interests.split(',') if i.strip()]
        elif isinstance(interests, list):
            return interests
        elif interests:  # 如果是其他非空值
            return [str(interests)]
        else:
            return []

    @property
    def research_interests(self) -> list:
        """研究方向属性"""
        return self.get_research_interests()

    def get_institution(self) -> str:
        """获取用户所属机构"""
        if not hasattr(self, 'profile') or self.profile is None:
            return ""
        
        return self.profile.get('institution', '')

    @property
    def institution(self) -> str:
        """所属机构属性"""
        return self.get_institution()

class APIKey(Base):
    """API密钥模型"""
    __tablename__ = "api_keys"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    key = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # 关系
    user = relationship("User", back_populates="api_keys") 