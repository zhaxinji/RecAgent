from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

class AIProviderEnum(str, Enum):
    """AI提供商枚举"""
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    CLAUDE = "claude"

class SummaryRequest(BaseModel):
    """摘要生成请求"""
    length: str = Field("medium", description="摘要长度: short, medium, long")
    provider: Optional[AIProviderEnum] = Field(None, description="AI提供商")

class SummaryResponse(BaseModel):
    """摘要生成响应"""
    paper_id: str
    summary: str
    provider: AIProviderEnum

class PaperAnalysisRequest(BaseModel):
    """论文分析请求"""
    provider: Optional[AIProviderEnum] = Field(None, description="AI提供商")

class PaperAnalysisResponse(BaseModel):
    """论文分析响应"""
    paper_id: str
    analysis: Dict[str, Any]
    provider: AIProviderEnum

class ExperimentGenerationRequest(BaseModel):
    """实验代码生成请求"""
    experiment_name: Optional[str] = Field(None, description="实验名称")
    experiment_description: Optional[str] = Field(None, description="实验描述")
    framework: str = Field("pytorch", description="首选框架，如pytorch, tensorflow等")
    language: str = Field("python", description="编程语言")
    provider: Optional[AIProviderEnum] = Field(None, description="AI提供商")
    paper_id: Optional[str] = Field(None, description="论文ID（可选）")

class ExperimentGenerationResponse(BaseModel):
    """实验代码生成响应"""
    paper_id: Optional[str] = Field(None, description="论文ID")
    experiment_id: str = Field(..., description="实验ID")
    code: str = Field(..., description="生成的代码")
    explanation: Optional[str] = Field(None, description="代码解释")
    provider: str = Field(..., description="使用的AI提供商")
    warning: Optional[str] = Field(None, description="生成过程中的警告信息")

class ResearchQuestionsRequest(BaseModel):
    """研究问题生成请求"""
    count: int = Field(5, ge=1, le=10, description="问题数量")
    provider: Optional[AIProviderEnum] = Field(None, description="AI提供商")

class ResearchQuestionsResponse(BaseModel):
    """研究问题生成响应"""
    paper_id: str
    questions: List[str]
    provider: AIProviderEnum

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class AssistantType(str, Enum):
    GENERAL = "general"
    RESEARCH_GAP = "research_gap"
    INNOVATION = "innovation"
    EXPERIMENT = "experiment"
    WRITING = "writing"

class MessageBase(BaseModel):
    """消息基础模式"""
    role: MessageRole
    content: str
    message_metadata: Optional[Dict[str, Any]] = None

class MessageCreate(MessageBase):
    """创建消息模式"""
    pass

class MessageResponse(MessageBase):
    """消息响应模式"""
    id: str
    session_id: str
    sequence: int
    created_at: datetime

    class Config:
        orm_mode = True

class SessionBase(BaseModel):
    """会话基础模式"""
    title: str
    session_type: AssistantType = AssistantType.GENERAL
    context: Optional[Dict[str, Any]] = None
    paper_id: Optional[str] = None

class SessionCreate(SessionBase):
    """创建会话模式"""
    pass

class SessionUpdate(BaseModel):
    """更新会话模式"""
    title: Optional[str] = None
    is_active: Optional[bool] = None
    context: Optional[Dict[str, Any]] = None

class SessionResponse(SessionBase):
    """会话响应模式"""
    id: str
    owner_id: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    messages: List[MessageResponse] = []
    
    class Config:
        orm_mode = True

class SessionSummary(BaseModel):
    """会话摘要模式，不包含详细消息"""
    id: str
    title: str
    session_type: AssistantType
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    message_count: int
    
    class Config:
        orm_mode = True

class ChatRequest(BaseModel):
    """聊天请求模式"""
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    paper_id: Optional[str] = None

class ChatResponse(BaseModel):
    """聊天响应模式"""
    session_id: str
    message: MessageResponse
    suggestions: Optional[List[str]] = None

class ResearchGapRequest(BaseModel):
    """研究空白分析请求模式"""
    domain: str = Field(..., description="研究领域")
    perspective: str = Field(..., description="分析角度")
    paper_ids: Optional[List[str]] = Field(default_factory=list, description="论文ID列表")
    additional_context: Optional[str] = Field(None, description="额外背景信息")
    provider: Optional[str] = Field(None, description="AI提供商")

class ResearchGapItem(BaseModel):
    """研究空白项目"""
    title: str = Field(..., description="研究空白的标题")
    description: str = Field(..., description="研究空白的详细描述")
    evidence: List[Dict[str, str]] = Field(..., description="支持证据")
    potentialDirections: List[str] = Field(..., description="潜在研究方向")

class ResearchGapResponse(BaseModel):
    """研究空白分析响应模式"""
    session_id: str = Field(..., description="会话ID")
    domain: str = Field(..., description="分析的研究领域")
    summary: str = Field(..., description="总体分析概要")
    researchGaps: List[ResearchGapItem] = Field(..., description="识别的研究空白")
    references: List[str] = Field(..., description="引用的参考文献")

class InnovationIdeasRequest(BaseModel):
    """创新点生成请求模式"""
    research_topic: str = Field(..., description="研究主题")
    paper_ids: Optional[List[str]] = Field(None, description="相关论文ID列表")
    innovation_type: Optional[str] = Field(None, description="创新类型")
    additional_context: Optional[str] = Field(None, description="额外背景信息")
    provider: Optional[str] = Field(None, description="AI提供商")

class ExperimentDesignRequest(BaseModel):
    """实验设计生成请求模式"""
    paper_id: Optional[str] = Field(None, description="论文ID")
    experiment_name: str = Field(..., description="实验名称")
    experiment_description: Optional[str] = Field(None, description="实验描述")
    framework: str = Field("pytorch", description="框架")
    language: str = Field("python", description="编程语言")
    provider: Optional[str] = Field(None, description="AI提供商")

class InnovationIdea(BaseModel):
    """创新点项目"""
    title: str = Field(..., description="创新点标题")
    description: str = Field(..., description="创新点详细描述")
    theoretical_basis: str = Field(..., description="创新点的理论基础")
    technical_implementation: List[str] = Field(..., description="技术实现步骤")
    potential_value: str = Field(..., description="潜在价值和学术意义")
    related_work: List[str] = Field(..., description="相关工作")
    
    # 可选字段
    innovation_type: Optional[str] = Field(None, description="创新类型")
    key_insight: Optional[str] = Field(None, description="核心洞察")
    differentiators: Optional[str] = Field(None, description="与现有研究的区别")
    technical_challenges: Optional[List[str]] = Field(None, description="技术挑战")
    solution_approaches: Optional[List[str]] = Field(None, description="解决方案")
    feasibility_analysis: Optional[str] = Field(None, description="可行性分析")

class InnovationIdeasResponse(BaseModel):
    """创新点生成响应模式"""
    session_id: str = Field(..., description="会话ID")
    research_topic: str = Field(..., description="研究主题")
    innovation_type: Optional[str] = Field(None, description="创新类型")
    summary: str = Field(..., description="总体概要")
    innovations: List[InnovationIdea] = Field(..., description="生成的创新点")
    references: List[str] = Field(..., description="引用的参考文献")
    implementation_strategy: Optional[str] = Field(None, description="实现策略")
    final_summary: Optional[str] = Field(None, description="最终总结")

class AIProviderChangeRequest(BaseModel):
    """更改AI提供商请求"""
    provider: AIProviderEnum = Field(..., description="新的AI提供商")

class AIProviderChangeResponse(BaseModel):
    """更改AI提供商响应"""
    old_provider: AIProviderEnum
    new_provider: AIProviderEnum
    status: str 