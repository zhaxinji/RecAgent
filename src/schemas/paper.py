from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from enum import Enum

# 论文来源枚举
class PaperSourceEnum(str, Enum):
    UPLOAD = "upload"       # 用户上传
    URL = "url"             # 网址导入
    DOI = "doi"             # DOI导入
    ARXIV = "arxiv"         # arXiv导入
    MANUAL = "manual"       # 手动创建

# 分析状态枚举
class AnalysisStatusEnum(str, Enum):
    PENDING = "pending"     # 等待分析
    PROCESSING = "processing" # 分析中
    COMPLETED = "completed" # 分析完成
    FAILED = "failed"       # 分析失败

# 检索数据库枚举
class SearchSourceEnum(str, Enum):
    ARXIV = "arxiv"
    SEMANTICSCHOLAR = "semanticscholar"
    CITESEERX = "citeseerx"
    CORE = "core"
    OPENALEX = "openalex"
    LOCAL = "local"
    # 下面数据库暂不支持
    DBLP = "dblp"
    GOOGLESCHOLAR = "googlescholar"
    OPENAIRE = "openaire"
    MSACADEMIC = "msacademic"
    UNPAYWALL = "unpaywall"

# 作者模型
class Author(BaseModel):
    name: str
    affiliation: Optional[str] = None
    email: Optional[str] = None
    
# 标签模型
class Tag(BaseModel):
    name: str
    color: Optional[str] = None

# 注释模型
class Annotation(BaseModel):
    id: str
    text: str
    page: int
    position: Dict[str, Any]
    color: Optional[str] = None
    created_at: datetime

# 基础论文模型
class PaperBase(BaseModel):
    title: str
    abstract: Optional[str] = None
    authors: Optional[List[Dict[str, str]]] = []
    publication_date: Optional[datetime] = None
    journal: Optional[str] = None
    conference: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    arxiv_id: Optional[str] = None
    tags: Optional[List[str]] = []
    notes: Optional[str] = None

# 论文创建模型
class PaperCreate(PaperBase):
    source: PaperSourceEnum = PaperSourceEnum.MANUAL
    file_path: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}
    folder_id: Optional[str] = None
    category_ids: Optional[List[str]] = []

# 论文更新模型
class PaperUpdate(BaseModel):
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: Optional[List[Dict[str, str]]] = None
    publication_date: Optional[datetime] = None
    journal: Optional[str] = None
    conference: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    folder_id: Optional[str] = None
    category_ids: Optional[List[str]] = None

# 论文上传模型
class PaperUpload(BaseModel):
    title: Optional[str] = None
    source: PaperSourceEnum = PaperSourceEnum.UPLOAD
    extract_content: bool = True
    analyze_content: bool = False
    folder_id: Optional[str] = None
    category_ids: Optional[List[str]] = []

# 论文URL导入模型
class PaperImportUrl(BaseModel):
    url: HttpUrl
    extract_content: bool = True
    analyze_content: bool = False
    folder_id: Optional[str] = None
    category_ids: Optional[List[str]] = []

# 论文DOI导入模型
class PaperImportDoi(BaseModel):
    doi: str
    extract_content: bool = True
    analyze_content: bool = False
    folder_id: Optional[str] = None
    category_ids: Optional[List[str]] = []

# 论文arXiv导入模型
class PaperImportArxiv(BaseModel):
    arxiv_id: str
    extract_content: bool = True
    analyze_content: bool = False
    folder_id: Optional[str] = None
    category_ids: Optional[List[str]] = []

# 论文响应模型
class PaperResponse(PaperBase):
    id: str
    owner_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    file_path: Optional[str] = None
    source: PaperSourceEnum
    has_content: bool
    has_file: bool
    page_count: Optional[int] = None
    metadata: Dict[str, Any] = {}
    is_favorite: bool = False
    folder_id: Optional[str] = None
    folder_name: Optional[str] = None
    categories: List[Dict[str, str]] = []
    last_read_at: Optional[datetime] = None
    analysis_status: Optional[AnalysisStatusEnum] = None
    analysis_progress: Optional[int] = 0
    
    class Config:
        orm_mode = True

# 论文带内容响应模型
class PaperContentResponse(PaperResponse):
    content: Optional[str] = None

# 论文带分析结果的响应模型
class PaperAnalysisResponse(PaperResponse):
    sections: Optional[List[Dict[str, Any]]] = None
    methodology: Optional[Dict[str, Any]] = None
    experiments: Optional[Dict[str, Any]] = None
    references: Optional[List[Dict[str, Any]]] = None
    code_implementation: Optional[str] = None
    key_findings: Optional[List[str]] = None
    weaknesses: Optional[List[Dict[str, Any]]] = None
    future_work: Optional[List[Dict[str, Any]]] = None
    analysis_date: Optional[datetime] = None

# 论文列表响应模型
class PapersListResponse(BaseModel):
    papers: List[PaperResponse]
    total: int
    page: int
    per_page: int
    
# 标签操作模型
class TagOperation(BaseModel):
    tag: str
    operation: str = Field(..., description="操作类型: add, remove")

# 论文标签更新模型
class PaperTagsUpdate(BaseModel):
    operations: List[TagOperation]
    
# 论文注释创建模型
class AnnotationCreate(BaseModel):
    text: str
    page: int
    position: Dict[str, Any]
    color: Optional[str] = None

# 论文注释更新模型
class AnnotationUpdate(BaseModel):
    text: Optional[str] = None
    color: Optional[str] = None

# 论文注释响应模型
class AnnotationResponse(BaseModel):
    id: str
    text: str
    page: int
    position: Dict[str, Any]
    color: Optional[str] = None
    created_at: datetime
    paper_id: str
    user_id: str
    
    class Config:
        orm_mode = True

# 标签Schema
class TagBase(BaseModel):
    name: str
    color: Optional[str] = None

class TagCreate(TagBase):
    pass

class TagResponse(TagBase):
    id: str
    created_at: datetime
    paper_count: Optional[int] = 0

    class Config:
        orm_mode = True

# 分类Schema
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: str
    created_at: datetime
    paper_count: Optional[int] = 0
    children: Optional[List['CategoryResponse']] = []

    class Config:
        orm_mode = True

# 文件夹Schema
class FolderBase(BaseModel):
    name: str
    parent_id: Optional[str] = None

class FolderCreate(FolderBase):
    pass

class FolderUpdate(FolderBase):
    pass

class FolderResponse(FolderBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    paper_count: Optional[int] = 0
    children: Optional[List['FolderResponse']] = []

    class Config:
        orm_mode = True

# 笔记Schema
class NoteBase(BaseModel):
    content: str
    page_number: Optional[int] = None
    position_data: Optional[Dict[str, Any]] = None

class NoteCreate(NoteBase):
    pass

class NoteUpdate(BaseModel):
    content: Optional[str] = None
    page_number: Optional[int] = None
    position_data: Optional[Dict[str, Any]] = None

class NoteResponse(NoteBase):
    id: str
    paper_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# 文件上传响应
class UploadResponse(BaseModel):
    file_path: str
    file_size: int
    file_name: str
    content_type: str

# 论文提取请求
class PaperExtractionRequest(BaseModel):
    file_path: str
    extract_content: bool = True  # 是否提取文本内容
    extract_metadata: bool = True  # 是否提取元数据
    analyze_content: bool = False  # 是否进行论文分析

# 论文分析请求
class PaperAnalysisRequest(BaseModel):
    sections: bool = True  # 是否分析章节结构
    methodology: bool = True  # 是否分析方法论
    experiments: bool = False  # 是否分析实验
    references: bool = False  # 是否分析参考文献
    code: bool = True  # 是否生成代码实现
    findings: bool = True  # 是否提取关键发现
    weaknesses: bool = True  # 是否分析局限性
    future_work: bool = True  # 是否提取未来工作
    extract_core_content: bool = True  # 是否仅提取核心内容进行分析，减少处理时间

# 论文搜索请求
class PaperSearchRequest(BaseModel):
    query: str
    fields: Optional[List[str]] = None  # 要搜索的字段
    tags: Optional[List[str]] = None  # 标签过滤
    categories: Optional[List[str]] = None  # 分类过滤
    folders: Optional[List[str]] = None  # 文件夹过滤
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sort_by: Optional[str] = "relevance"
    sort_order: Optional[str] = "desc"
    limit: int = 10
    offset: int = 0
    
# 外部论文检索请求
class ExternalSearchRequest(BaseModel):
    query: str
    sources: List[SearchSourceEnum] = [SearchSourceEnum.ARXIV]
    limit: int = 10
    offset: int = 0
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    full_text: bool = False
    domain: Optional[str] = None
    venues: Optional[List[str]] = None

# 外部论文检索响应
class ExternalSearchResult(BaseModel):
    title: str
    authors: List[Dict[str, str]]
    abstract: Optional[str] = None
    publication_date: Optional[datetime] = None
    venue: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    source: SearchSourceEnum
    
class ExternalSearchResponse(BaseModel):
    results: List[ExternalSearchResult]
    total: int
    query: str

# 标签更新模型
class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None

# 论文元数据响应模型
class PaperMetadataResponse(BaseModel):
    id: str
    title: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    experiment_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        orm_mode = True 