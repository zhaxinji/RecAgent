from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class ExperimentStatusEnum(str, Enum):
    """实验状态枚举"""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

class ExperimentBase(BaseModel):
    """实验基础模型"""
    name: str = Field(..., description="实验名称")
    description: Optional[str] = Field(None, description="实验描述")
    paper_id: str = Field(..., description="关联的论文ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class ExperimentCreate(ExperimentBase):
    """创建实验模型"""
    code: str = Field(..., description="实验代码")

class ExperimentUpdate(BaseModel):
    """更新实验模型"""
    name: Optional[str] = Field(None, description="实验名称")
    description: Optional[str] = Field(None, description="实验描述")
    code: Optional[str] = Field(None, description="实验代码")
    status: Optional[ExperimentStatusEnum] = Field(None, description="实验状态")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class ExperimentResponse(ExperimentBase):
    """实验响应模型"""
    id: str
    user_id: str
    code: str
    status: ExperimentStatusEnum
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class ExperimentListResponse(BaseModel):
    """实验列表响应模型"""
    items: List[ExperimentResponse]
    total: int
    page: int
    size: int

class ExperimentResultBase(BaseModel):
    """实验结果基础模型"""
    experiment_id: str
    stdout: str
    stderr: str
    exit_code: int
    execution_time: Optional[float] = None
    created_at: datetime

class ExperimentResultResponse(ExperimentResultBase):
    """实验结果响应模型"""
    id: str
    status: ExperimentStatusEnum
    
    class Config:
        orm_mode = True 