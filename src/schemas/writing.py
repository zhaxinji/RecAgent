from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class TemplateEnum(str, Enum):
    """写作项目模板枚举"""
    RESEARCH_PAPER = "research_paper"
    THESIS = "thesis"
    REPORT = "report"
    EMPTY = "empty"

# 项目相关模型
class WritingProjectBase(BaseModel):
    """写作项目基础模型"""
    title: str = Field(..., description="项目标题")
    description: Optional[str] = Field(None, description="项目描述，同时用于存储元数据")
    related_papers: Optional[List[str]] = Field(None, description="相关论文ID列表")

class WritingProjectCreate(WritingProjectBase):
    """创建写作项目模型"""
    template: Optional[str] = Field(None, description="项目模板")

class WritingProjectUpdate(BaseModel):
    """更新写作项目模型"""
    title: Optional[str] = Field(None, description="项目标题")
    description: Optional[str] = Field(None, description="项目描述，同时用于存储元数据")
    related_papers: Optional[List[str]] = Field(None, description="相关论文ID列表")

class CollaboratorResponse(BaseModel):
    """协作者响应模型"""
    id: str
    name: str
    email: str
    
    class Config:
        orm_mode = True

class WritingProjectResponse(BaseModel):
    """写作项目响应模型"""
    id: str
    title: str
    description: Optional[str] = None
    related_papers: Optional[List[str]] = Field(default_factory=list)
    owner_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    collaborators: List[CollaboratorResponse] = []
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        orm_mode = True
        arbitrary_types_allowed = True

class WritingProjectListResponse(BaseModel):
    """写作项目列表响应模型"""
    items: List[WritingProjectResponse]
    total: int
    page: int
    size: int

# 章节相关模型
class WritingSectionBase(BaseModel):
    """章节基础模型"""
    title: str = Field(..., description="章节标题")
    content: str = Field("", description="章节内容")
    order: Optional[int] = Field(None, description="章节顺序")

class WritingSectionCreate(WritingSectionBase):
    """创建章节模型"""
    pass

class WritingSectionUpdate(BaseModel):
    """更新章节模型"""
    title: Optional[str] = Field(None, description="章节标题")
    content: Optional[str] = Field(None, description="章节内容")
    order: Optional[int] = Field(None, description="章节顺序")

class WritingSectionResponse(WritingSectionBase):
    """章节响应模型"""
    id: str
    project_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

# 协作相关模型
class CollaborationInviteBase(BaseModel):
    """协作邀请基础模型"""
    email: str = Field(..., description="被邀请者邮箱")
    message: Optional[str] = Field(None, description="邀请消息")

class CollaborationInviteCreate(CollaborationInviteBase):
    """创建协作邀请模型"""
    pass

class CollaborationInviteResponse(BaseModel):
    """协作邀请响应模型"""
    id: str
    project_id: str
    inviter_id: str
    invitee_email: str
    invitee_id: Optional[str] = None
    message: Optional[str] = None
    status: str
    created_at: datetime
    expires_at: datetime
    responded_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

# AI 辅助写作相关模型
class SectionContentGenerationRequest(BaseModel):
    """章节内容生成请求"""
    prompt: str = Field(..., description="内容生成提示")
    paper_id: Optional[str] = Field(None, description="参考论文ID")

class SectionContentImprovementRequest(BaseModel):
    """章节内容改进请求"""
    improvement_type: str = Field(..., description="改进类型: grammar, clarity, academic, concise, expand")

# 项目导出相关模型
class ProjectExportResponse(BaseModel):
    """项目导出响应"""
    project_id: str
    title: str
    format: str
    content: str
    filename: str 