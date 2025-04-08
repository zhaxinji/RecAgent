from sqlalchemy import Boolean, Column, String, Integer, DateTime, ForeignKey, Text, Table, JSON
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
import uuid

from src.db.base import Base

# 论文-标签关联表
paper_tags = Table(
    'paper_tags',
    Base.metadata,
    Column('paper_id', String, ForeignKey('papers.id', ondelete="CASCADE")),
    Column('tag_id', String, ForeignKey('tags.id', ondelete="CASCADE")),
    extend_existing=True
)

# 新增论文分类关联表
paper_categories = Table(
    'paper_categories',
    Base.metadata,
    Column('paper_id', String, ForeignKey('papers.id', ondelete="CASCADE")),
    Column('category_id', String, ForeignKey('categories.id', ondelete="CASCADE")),
    extend_existing=True
)

class Paper(Base):
    """论文模型"""
    __tablename__ = "papers"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, index=True)
    abstract = Column(Text, nullable=True)
    authors = Column(JSON, nullable=True)  # 存储作者列表为JSON
    publication_date = Column(DateTime(timezone=True), nullable=True)
    journal = Column(String, nullable=True)
    conference = Column(String, nullable=True)
    doi = Column(String, nullable=True, index=True)
    url = Column(String, nullable=True)
    file_path = Column(String, nullable=True)  # 指向MinIO中的PDF文件
    thumbnail_path = Column(String, nullable=True)  # 指向MinIO中的缩略图
    content = Column(Text, nullable=True)  # 提取的文本内容
    paper_metadata = Column(JSON, nullable=True)  # 附加元数据
    file_size = Column(Integer, nullable=True)  # 文件大小（字节）
    source = Column(String, nullable=True, default="upload")  # 论文来源：upload, url, doi, arxiv, manual
    is_favorite = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 论文分析部分
    sections = Column(JSON, nullable=True)  # 论文章节结构
    methodology = Column(JSON, nullable=True)  # 方法论详细信息
    experiments = Column(JSON, nullable=True)  # 实验设计和结果
    references = Column(JSON, nullable=True)  # 参考文献列表
    code_implementation = Column(Text, nullable=True)  # 代码实现示例
    key_findings = Column(JSON, nullable=True)  # 关键发现
    weaknesses = Column(JSON, nullable=True)  # 局限性
    future_work = Column(JSON, nullable=True)  # 未来工作方向，使用JSON类型以支持复杂结构
    analysis_status = Column(String, nullable=True)  # 分析状态
    analysis_progress = Column(Integer, default=0)  # 分析进度（0-100）
    analysis_date = Column(DateTime(timezone=True), nullable=True)  # 分析完成时间
    
    # 外键
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    folder_id = Column(String, ForeignKey("folders.id", ondelete="SET NULL"), nullable=True)  # 所属文件夹
    
    # 关系
    owner = relationship("User", back_populates="papers")
    tags = relationship("Tag", secondary=paper_tags, back_populates="papers")
    categories = relationship("Category", secondary=paper_categories, back_populates="papers")
    notes = relationship("Note", back_populates="paper", cascade="all, delete-orphan")
    annotations = relationship("Annotation", back_populates="paper", cascade="all, delete-orphan")
    experiments = relationship("Experiment", back_populates="paper")
    folder = relationship("Folder", back_populates="papers")

class Tag(Base):
    """标签模型"""
    __tablename__ = "tags"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True, nullable=False)
    color = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    
    # 关系
    owner = relationship("User", back_populates="tags")
    papers = relationship("Paper", secondary=paper_tags, back_populates="tags")

class Category(Base):
    """论文分类模型"""
    __tablename__ = "categories"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    parent_id = Column(String, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    
    # 关系
    owner = relationship("User", back_populates="categories")
    papers = relationship("Paper", secondary=paper_categories, back_populates="categories")
    children = relationship("Category", backref=backref("parent", remote_side=[id]))

class Note(Base):
    """笔记模型"""
    __tablename__ = "notes"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    position_data = Column(JSON, nullable=True)  # 存储笔记在PDF中的位置数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 外键
    paper_id = Column(String, ForeignKey("papers.id", ondelete="CASCADE"))
    
    # 关系
    paper = relationship("Paper", back_populates="notes")

class Annotation(Base):
    """标注模型"""
    __tablename__ = "annotations"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    content = Column(Text, nullable=True)  # 标注内容或评论
    highlight_text = Column(Text, nullable=False)  # 高亮的文本
    page_number = Column(Integer, nullable=False)
    position_data = Column(JSON, nullable=False)  # 标注在PDF中的位置数据
    color = Column(String, nullable=True, default="yellow")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 外键
    paper_id = Column(String, ForeignKey("papers.id", ondelete="CASCADE"))
    
    # 关系
    paper = relationship("Paper", back_populates="annotations")

class Folder(Base):
    """文件夹模型"""
    __tablename__ = "folders"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    parent_id = Column(String, ForeignKey("folders.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    
    # 关系
    owner = relationship("User", back_populates="folders")
    papers = relationship("Paper", back_populates="folder")
    children = relationship("Folder", backref=backref("parent", remote_side=[id]), cascade="all, delete-orphan") 