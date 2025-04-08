from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from src.schemas.experiment import (
    ExperimentCreate, 
    ExperimentUpdate, 
    ExperimentResponse, 
    ExperimentListResponse,
    ExperimentResultResponse
)
from src.services import experiment as experiment_service
from src.models.experiment import ExperimentStatus
from src.core.deps import get_db, get_current_user
from src.models.user import User

router = APIRouter(prefix="/experiments", tags=["experiments"])

@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    data: ExperimentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新实验
    """
    experiment = experiment_service.create_experiment(
        db=db,
        user_id=current_user.id,
        paper_id=data.paper_id,
        name=data.name,
        description=data.description,
        code=data.code,
        status=ExperimentStatus.DRAFT,
        metadata=data.metadata
    )
    return experiment

@router.get("", response_model=ExperimentListResponse)
async def get_experiments(
    paper_id: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的实验列表
    """
    experiment_status = None
    if status:
        try:
            experiment_status = ExperimentStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的实验状态: {status}"
            )
    
    experiments = experiment_service.get_experiments(
        db=db,
        user_id=current_user.id,
        paper_id=paper_id,
        status=experiment_status,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    total = len(experiments)  # 简化计算，实际应使用count查询
    
    return {
        "items": experiments,
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "size": limit
    }

@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    通过ID获取实验
    """
    experiment = experiment_service.get_experiment_by_id(db, experiment_id, current_user.id)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实验未找到"
        )
    return experiment

@router.patch("/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(
    experiment_id: str,
    data: ExperimentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新实验信息
    """
    updated_experiment = experiment_service.update_experiment(
        db=db,
        experiment_id=experiment_id,
        user_id=current_user.id,
        update_data=data.dict(exclude_unset=True)
    )
    
    if not updated_experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实验未找到或无权限修改"
        )
    
    return updated_experiment

@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(
    experiment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除实验
    """
    result = experiment_service.delete_experiment(db, experiment_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实验未找到或无权限删除"
        )
    return None

@router.post("/{experiment_id}/run", response_model=ExperimentResultResponse)
async def run_experiment(
    experiment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    运行实验
    """
    try:
        result = await experiment_service.run_experiment(db, experiment_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"运行实验失败: {str(e)}"
        )

@router.get("/{experiment_id}/results", response_model=List[ExperimentResultResponse])
async def get_experiment_results(
    experiment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取实验的所有运行结果
    """
    experiment = experiment_service.get_experiment_by_id(db, experiment_id, current_user.id)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实验未找到"
        )
    
    results = experiment_service.get_experiment_results(db, experiment_id, current_user.id)
    return results

@router.get("/{experiment_id}/latest-result", response_model=ExperimentResultResponse)
async def get_latest_experiment_result(
    experiment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取实验的最新运行结果
    """
    experiment = experiment_service.get_experiment_by_id(db, experiment_id, current_user.id)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实验未找到"
        )
    
    result = experiment_service.get_latest_experiment_result(db, experiment_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该实验暂无运行结果"
        )
    
    return result

class TemplateRequest(BaseModel):
    paper_id: Optional[str] = None
    template_type: str = "basic"
    language: str = "python"
    framework: str = "pytorch"

@router.post("/template", response_model=Dict[str, Any])
async def generate_template(
    request: TemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成实验代码模板
    
    - template_type: 模板类型，目前支持'basic'
    - language: 编程语言，支持'python', 'r', 'julia'
    - framework: 框架，取决于语言
    - paper_id: 可选，关联的论文ID
    """
    try:
        # 检查语言是否支持
        if request.language not in experiment_service.SUPPORTED_LANGUAGES:
            raise ValueError(f"不支持的编程语言: {request.language}")
        
        # 检查框架是否支持
        if request.framework and request.framework not in experiment_service.SUPPORTED_FRAMEWORKS.get(request.language, []):
            raise ValueError(f"不支持的框架 {request.framework} 用于 {request.language}")
        
        template_code = await experiment_service.generate_experiment_template(
            db,
            current_user.id,
            paper_id=request.paper_id,
            template_type=request.template_type,
            language=request.language,
            framework=request.framework
        )
        
        return {
            "code": template_code,
            "language": request.language,
            "framework": request.framework
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成模板失败: {str(e)}"
        )

# 新增用于支持前端ExperimentDesigner组件的API

# 研究领域数据
RESEARCH_DOMAINS = [
    {"value": "sequential", "label": "序列推荐", "description": "基于用户行为序列的推荐方法"},
    {"value": "graph", "label": "图神经网络推荐", "description": "利用图结构建模用户物品关系的推荐方法"},
    {"value": "multi_modal", "label": "多模态推荐", "description": "融合文本、图像等多种模态信息的推荐方法"},
    {"value": "knowledge", "label": "知识图谱推荐", "description": "利用外部知识图谱增强的推荐方法"},
    {"value": "contrastive", "label": "对比学习推荐", "description": "应用对比学习进行表示学习的推荐方法"},
    {"value": "cold_start", "label": "冷启动推荐", "description": "解决用户或物品冷启动问题的推荐方法"},
    {"value": "cross_domain", "label": "跨域推荐", "description": "利用跨领域信息进行推荐的方法"},
    {"value": "explainable", "label": "可解释性推荐", "description": "提供推荐理由的可解释推荐方法"}
]

# 数据集类型
DATASET_TYPES = [
    {"value": "explicit", "label": "显式反馈", "description": "包含用户明确评分的数据集"},
    {"value": "implicit", "label": "隐式反馈", "description": "包含用户点击、浏览等行为的数据集"},
    {"value": "sequential", "label": "序列数据", "description": "包含时序用户行为的数据集"},
    {"value": "kg", "label": "知识图谱增强", "description": "包含知识图谱信息的数据集"},
    {"value": "social", "label": "社交网络增强", "description": "包含社交关系的数据集"},
    {"value": "multi_modal", "label": "多模态数据", "description": "包含文本、图像等多模态信息的数据集"}
]

# 评估指标
METRICS = [
    {"value": "accuracy", "label": "准确率指标", "metrics": ["HR@K", "NDCG@K", "Precision@K", "Recall@K", "MAP@K", "MRR"]},
    {"value": "diversity", "label": "多样性指标", "metrics": ["ILD", "Coverage", "Entropy", "Gini"]},
    {"value": "novelty", "label": "新颖性指标", "metrics": ["Novelty@K", "Unexpectedness", "Serendipity"]},
    {"value": "efficiency", "label": "效率指标", "metrics": ["Training Time", "Inference Time", "Memory Usage"]},
    {"value": "fairness", "label": "公平性指标", "metrics": ["Statistical Parity", "Equal Opportunity", "Disparate Impact"]}
]

@router.get("/domains", response_model=List[Dict[str, Any]])
async def get_research_domains():
    """
    获取推荐系统研究领域列表
    """
    return RESEARCH_DOMAINS

@router.get("/dataset-types", response_model=List[Dict[str, Any]])
async def get_dataset_types():
    """
    获取数据集类型列表
    """
    return DATASET_TYPES

@router.get("/metrics", response_model=List[Dict[str, Any]])
async def get_metrics():
    """
    获取评估指标列表
    """
    return METRICS

class ExperimentDesignRequest(BaseModel):
    domain: str = Field(..., description="研究领域")
    datasetType: str = Field(..., description="数据集类型")
    metricType: str = Field(..., description="评估指标类型")
    methodDescription: Optional[str] = Field(None, description="方法描述或特殊需求")

class ExperimentDesignResponse(BaseModel):
    domain: str = Field(..., description="研究领域")
    experimentTitle: str = Field(..., description="实验标题")
    overview: str = Field(..., description="实验概述")
    datasets: List[Dict[str, str]] = Field(..., description="推荐数据集")
    baselines: List[Dict[str, str]] = Field(..., description="基线方法")
    metrics: List[Dict[str, Any]] = Field(..., description="评估指标")
    experimentSetup: Dict[str, Any] = Field(..., description="实验设置")
    implementationDetails: Dict[str, Any] = Field(..., description="实现细节")
    analysisPlans: List[str] = Field(..., description="分析计划")
    limitations: List[str] = Field(..., description="局限性讨论")

@router.post("/design", response_model=ExperimentDesignResponse)
async def generate_experiment_design(
    request: ExperimentDesignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成实验设计方案
    
    基于研究领域、数据集类型和评估指标，生成完整的实验设计方案
    """
    try:
        # 调用服务生成实验设计
        design = await experiment_service.generate_experiment_design(
            domain=request.domain,
            dataset_type=request.datasetType,
            metric_type=request.metricType,
            method_description=request.methodDescription,
            user_id=str(current_user.id)
        )
        
        return design
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成实验设计方案失败: {str(e)}"
        ) 