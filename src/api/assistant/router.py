from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Response, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import logging
from enum import Enum
import time
import asyncio
import json
from fastapi.responses import JSONResponse
from sqlalchemy import func
import uuid

from src.services import ai_assistant
from src.services import assistant
from src.core.deps import get_db, get_current_user
from src.models.user import User
from src.models.assistant import AssistantMessage, ConceptExplanation
from src.schemas.assistant import (
    PaperAnalysisRequest, PaperAnalysisResponse, 
    SummaryRequest, SummaryResponse,
    ExperimentGenerationRequest, ExperimentGenerationResponse,
    ResearchQuestionsRequest, ResearchQuestionsResponse,
    AIProviderChangeRequest, AIProviderChangeResponse,
    SessionCreate, SessionUpdate, SessionResponse, SessionSummary,
    MessageCreate, MessageResponse, ChatRequest, ChatResponse,
    ResearchGapRequest, ResearchGapResponse,
    InnovationIdeasRequest, InnovationIdeasResponse
)
from src.services import ai_settings as ai_settings_service
from src.services import paper as paper_service
from src.services.ai_assistant_fixed import AIProvider
from src.core.config import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["assistant"])

@router.post("/analyze/{paper_id}", response_model=PaperAnalysisResponse)
async def analyze_paper(
    paper_id: str,
    request: Optional[PaperAnalysisRequest] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    分析论文，提取关键信息和结构
    """
    try:
        provider = None
        if request and request.provider:
            provider = request.provider.value
        
        # 如果用户有自定义API密钥，优先使用用户的密钥
        if provider:
            original_api_key = await ai_settings_service.use_user_api_key(db, current_user.id, provider)
        
        try:
            analysis = await ai_assistant.analyze_paper_content(
                db, 
                paper_id, 
                current_user.id, 
                provider
            )
            
            return {
                "paper_id": paper_id, 
                "analysis": analysis,
                "provider": provider or settings.DEFAULT_AI_PROVIDER
            }
        finally:
            # 恢复全局API密钥
            if provider and original_api_key:
                background_tasks.add_task(
                    ai_settings_service.restore_global_api_key,
                    provider,
                    original_api_key
                )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分析失败: {str(e)}"
        )

@router.post("/summarize/{paper_id}", response_model=SummaryResponse)
async def generate_summary(
    paper_id: str,
    data: SummaryRequest,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成论文摘要
    """
    try:
        provider = None
        if data.provider:
            provider = data.provider.value
        
        # 如果用户有自定义API密钥，优先使用用户的密钥
        if provider:
            original_api_key = await ai_settings_service.use_user_api_key(db, current_user.id, provider)
        
        try:
            summary = await ai_assistant.generate_paper_summary(
                db, 
                paper_id, 
                current_user.id, 
                data.length, 
                provider
            )
            
            return {
                "paper_id": paper_id, 
                "summary": summary,
                "provider": provider or settings.DEFAULT_AI_PROVIDER
            }
        finally:
            # 恢复全局API密钥
            if provider and original_api_key:
                background_tasks.add_task(
                    ai_settings_service.restore_global_api_key,
                    provider,
                    original_api_key
                )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成摘要失败: {str(e)}"
        )

@router.post("/generate-experiment/{paper_id}", response_model=ExperimentGenerationResponse, deprecated=True)
async def generate_experiment_code_deprecated(
    paper_id: str,
    data: ExperimentGenerationRequest,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    已弃用：请使用/generate-experiment端点
    """
    return await generate_experiment_code(data, background_tasks, db, current_user)

@router.post("/generate-experiment", response_model=ExperimentGenerationResponse)
async def generate_experiment_code(
    data: ExperimentGenerationRequest,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成实验代码
    """
    try:
        start_time = time.time()
        logging.info(f"收到实验代码生成请求: 实验名称={data.experiment_name}")
        
        provider = None
        if data.provider:
            provider = data.provider.value
        
        # 如果用户有自定义API密钥，优先使用用户的密钥
        original_api_key = None
        if provider:
            original_api_key = await ai_settings_service.use_user_api_key(db, current_user.id, provider)
            logging.info(f"已设置用户自定义API密钥, 提供商: {provider}")
        
        try:
            # 验证论文是否存在（如果提供了paper_id）
            paper_id = data.paper_id
            
            if paper_id:
                paper = paper_service.get_paper_by_id(db, paper_id, current_user.id)
                if not paper:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="论文未找到或无权访问"
                    )
                
                # 检查论文内容是否充足
                if not paper.content or len(paper.content) < 200:
                    logging.warning(f"论文内容不足: {len(paper.content) if paper.content else 0} 字符")
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={
                            "error": "论文内容不足",
                            "detail": "提供的论文内容太少，无法生成有意义的实验代码"
                        }
                    )
            
            # 使用asyncio.wait_for添加超时控制
            try:
                generation_task = asyncio.create_task(
                    ai_assistant.generate_experiment(
                        db,
                        paper_id,
                        current_user.id,
                        data.experiment_name,
                        data.experiment_description,
                        data.framework or "pytorch",
                        data.language or "python",
                        provider
                    )
                )
                
                # 设置5分钟超时
                result = await asyncio.wait_for(generation_task, timeout=300.0)
                
                end_time = time.time()
                total_time = end_time - start_time
                logging.info(f"实验代码生成完成，耗时: {total_time:.2f}秒")
                
                if "error" in result:
                    # 如果返回了错误信息但仍有代码，则仍返回结果但添加警告信息
                    if "code" in result and result["code"]:
                        logging.warning(f"实验代码生成部分成功: {result.get('error')}")
                        return {
                            "paper_id": paper_id,
                            "experiment_id": result.get("experiment_id", ""),
                            "code": result["code"],
                            "explanation": result.get("explanation", "") + f"\n\n注意: 生成过程中遇到问题: {result.get('error')}",
                            "provider": provider or settings.DEFAULT_AI_PROVIDER,
                            "warning": result.get("error")
                        }
                    else:
                        # 如果没有返回代码，则抛出异常
                        raise Exception(result.get("error", "未知错误"))
                
                return {
                    "paper_id": paper_id,
                    "experiment_id": result.get("experiment_id", ""),
                    "code": result["code"],
                    "explanation": result.get("explanation", ""),
                    "provider": provider or settings.DEFAULT_AI_PROVIDER
                }
                
            except asyncio.TimeoutError:
                logging.error(f"实验代码生成超时 (>300秒)")
                return JSONResponse(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    content={
                        "error": "请求处理超时",
                        "detail": "生成实验代码请求超时，请减少论文内容或简化实验设计"
                    }
                )
                
        except ValueError as e:
            # 已知的值错误
            logging.error(f"生成实验代码值错误: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except HTTPException as e:
            # 直接重新抛出HTTP异常
            raise e
        except Exception as e:
            # 其他未知异常
            logging.error(f"生成实验代码时发生未知错误: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"生成实验代码失败: {str(e)}"
            )
        finally:
            # 恢复全局API密钥
            if provider and original_api_key:
                try:
                    background_tasks.add_task(
                        ai_settings_service.restore_global_api_key,
                        provider,
                        original_api_key
                    )
                except Exception as e:
                    logging.error(f"恢复API密钥失败: {str(e)}")
    
    except HTTPException:
        # 重新抛出HTTPException
        raise
    except Exception as e:
        logging.error(f"处理实验代码生成请求时发生错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求失败: {str(e)}"
        )

@router.post("/research-questions/{paper_id}", response_model=ResearchQuestionsResponse)
async def get_research_questions(
    paper_id: str,
    request: ResearchQuestionsRequest,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    基于论文生成研究问题
    """
    try:
        provider = None
        if request.provider:
            provider = request.provider.value
        
        # 如果用户有自定义API密钥，优先使用用户的密钥
        if provider:
            original_api_key = await ai_settings_service.use_user_api_key(db, current_user.id, provider)
        
        try:
            questions = await ai_assistant.get_research_questions(
                db, 
                paper_id, 
                current_user.id, 
                request.count,
                provider
            )
            
            return {
                "paper_id": paper_id, 
                "questions": questions,
                "provider": provider or settings.DEFAULT_AI_PROVIDER
            }
        finally:
            # 恢复全局API密钥
            if provider and original_api_key:
                background_tasks.add_task(
                    ai_settings_service.restore_global_api_key,
                    provider,
                    original_api_key
                )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成研究问题失败: {str(e)}"
        )

@router.post("/change-provider", response_model=AIProviderChangeResponse)
async def change_ai_provider(
    data: AIProviderChangeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    修改默认的AI提供商
    """
    try:
        result = await ai_assistant.change_ai_provider(data.provider.value)
        return {
            "old_provider": result["old_provider"],
            "new_provider": result["new_provider"],
            "status": result["status"]
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"切换AI提供商失败: {str(e)}"
        )

@router.get("/providers", response_model=Dict[str, str])
async def get_available_providers():
    """
    获取可用的AI提供商列表
    """
    from src.core.config import settings
    
    providers = {
        "default": settings.DEFAULT_AI_PROVIDER,
        "available": list(settings.AI_PROVIDERS.keys())
    }
    
    return providers 

class ResearchGap(BaseModel):
    title: str = Field(..., description="研究空白的标题")
    description: str = Field(..., description="研究空白的详细描述")
    evidence: List[Dict[str, str]] = Field(..., description="支持证据")
    potentialDirections: List[str] = Field(..., description="潜在研究方向")

class ResearchGapRequest(BaseModel):
    paper_ids: List[str] = Field(..., description="论文ID列表")
    domain: str = Field(..., description="研究领域")
    perspective: str = Field(..., description="分析角度")
    additional_context: Optional[str] = Field(None, description="额外背景信息")
    provider: Optional[str] = Field(None, description="AI提供商")

class ResearchGapResponse(BaseModel):
    session_id: str = Field(..., description="会话ID")
    domain: str = Field(..., description="分析的研究领域")
    summary: str = Field(..., description="总体分析概要")
    researchGaps: List[Dict[str, Any]] = Field(..., description="识别的研究空白")
    references: Optional[List[str]] = Field(None, description="参考文献")

# 获取可用的研究领域
@router.get("/research-domains", response_model=List[Dict[str, Any]])
async def get_research_domains():
    """
    获取推荐系统研究领域列表
    """
    return [
        {"value": "sequential", "label": "序列推荐", "description": "基于用户历史行为序列的推荐技术"},
        {"value": "graph", "label": "图神经网络推荐", "description": "基于GNN的推荐系统方法"},
        {"value": "multi_modal", "label": "多模态推荐", "description": "结合图文音视频等多模态信息的推荐"},
        {"value": "knowledge", "label": "知识增强推荐", "description": "融合知识图谱的推荐技术"},
        {"value": "contrastive", "label": "对比学习推荐", "description": "应用对比学习的推荐方法"},
        {"value": "llm", "label": "大模型推荐", "description": "基于大语言模型的推荐系统"},
        {"value": "explainable", "label": "可解释推荐", "description": "可解释性推荐算法研究"},
        {"value": "fairness", "label": "公平推荐", "description": "推荐系统公平性研究"},
        {"value": "cold_start", "label": "冷启动推荐", "description": "解决冷启动问题的推荐技术"},
        {"value": "federated", "label": "联邦推荐", "description": "联邦学习推荐系统"},
        {"value": "reinforcement", "label": "强化学习推荐", "description": "基于强化学习的推荐技术"},
        {"value": "self_supervised", "label": "自监督推荐", "description": "自监督学习在推荐中的应用"}
    ]

# 获取可用的分析角度
@router.get("/analysis-perspectives", response_model=List[Dict[str, Any]])
async def get_analysis_perspectives():
    """
    获取研究空白分析角度列表
    """
    return [
        {"value": "theoretical", "label": "理论缺口", "description": "现有理论框架的局限性和扩展空间"},
        {"value": "methodological", "label": "方法缺口", "description": "算法和技术实现层面的问题和改进空间"},
        {"value": "application", "label": "应用缺口", "description": "特定场景下的适用性问题和新应用方向"},
        {"value": "evaluation", "label": "评估缺口", "description": "实验设计和评价指标的局限性"},
        {"value": "comprehensive", "label": "综合分析", "description": "全面考量各个维度的研究空白"}
    ]

@router.post("/research-gaps/analyze", response_model=ResearchGapResponse)
async def analyze_domain_research_gaps(
    request: ResearchGapRequest,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    分析研究领域的空白
    """
    try:
        # 请求开始时间记录，用于监控性能
        start_time = time.time()
        logging.info(f"研究空白分析请求开始，用户ID: {current_user.id}，领域: {request.domain}")
        
        provider = request.provider
        original_api_key = None
        
        # 如果用户有自定义API密钥，优先使用用户的密钥
        if provider:
            original_api_key = await ai_settings_service.use_user_api_key(db, current_user.id, provider)
        
        try:
            # 收集论文信息
            papers = []
            for paper_id in request.paper_ids:
                paper = paper_service.get_paper_by_id(db, paper_id, current_user.id)
                if paper:
                    papers.append({
                        "id": paper.id,
                        "title": paper.title,
                        "abstract": paper.abstract,
                        "content": paper.content,
                        "authors": paper.authors,
                        "year": paper.publication_date.year if paper.publication_date else None,
                        "publication_date": paper.publication_date.isoformat() if paper.publication_date else None
                    })
            
            # 分析研究空白
            logging.info(f"开始分析研究空白，领域：{request.domain}，角度：{request.perspective}，论文数量：{len(papers)}")
            
            # 使用assistant.py中的实现，而非ai_assistant.py
            try:
                analysis_result = await assistant.analyze_research_gaps(
                    db=db,
                    user_id=current_user.id,
                    domain=request.domain,
                    perspective=request.perspective,
                    paper_ids=request.paper_ids or [],
                    additional_context=request.additional_context
                )
            except Exception as analyze_error:
                logging.error(f"研究问题分析API调用失败: {str(analyze_error)}")
                # 创建会话记录错误
                error_session = assistant.create_session(
                    db,
                    current_user.id,
                    assistant.SessionCreate(
                        title=f"分析出错: {request.domain}领域研究空白",
                        session_type="research_gap",
                        context={
                            "domain": request.domain,
                            "perspective": request.perspective,
                            "error": str(analyze_error)
                        }
                    )
                )
                
                # 添加错误消息
                assistant.create_message(
                    db,
                    error_session.id,
                    assistant.MessageCreate(
                        role=assistant.MessageRole.ASSISTANT,
                        content=f"很抱歉，在分析{request.domain}领域研究问题时发生错误: {str(analyze_error)}\n\n请稍后重试或尝试减少输入内容。"
                    )
                )
                
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "error": "AI分析失败",
                        "detail": str(analyze_error),
                        "session_id": error_session.id
                    }
                )
            
            # 解构返回值，因为analyze_research_gaps返回的是一个元组 (session, result)
            session, analysis_data = analysis_result
            
            # 确保analysis_data已经初始化为字典
            if not isinstance(analysis_data, dict):
                analysis_data = {}
            
            # 确保分析结果具有一致的结构
            if "researchGaps" not in analysis_data and "research_gaps" in analysis_data:
                logging.info("修复字段名：将research_gaps转换为researchGaps")
                analysis_data["researchGaps"] = analysis_data.pop("research_gaps")
            elif "researchGaps" not in analysis_data and "research_gaps" not in analysis_data:
                logging.warning("分析结果缺少研究空白字段，添加空数组")
                analysis_data["researchGaps"] = []
                
            if "summary" not in analysis_data:
                logging.warning("分析结果缺少summary字段，添加默认内容")
                analysis_data["summary"] = "无法获取分析概要，请稍后重试。"
            
            # 规范化每个研究空白的结构
            for gap in analysis_data.get("researchGaps", []):
                if "potentialDirections" not in gap and "potential_directions" in gap:
                    logging.info("修复字段名：将potential_directions转换为potentialDirections")
                    gap["potentialDirections"] = gap.pop("potential_directions")
                    
                # 确保evidence字段存在
                if "evidence" not in gap:
                    gap["evidence"] = []
                    
                # 确保potentialDirections字段存在
                if "potentialDirections" not in gap:
                    gap["potentialDirections"] = []
            
            # 添加助手回复消息
            logging.info("构建助手响应消息")
            response_content = f"## {request.domain}领域研究空白分析\n\n{analysis_data['summary']}\n\n"
            for gap in analysis_data.get("researchGaps", []):
                response_content += f"### {gap.get('title', '未命名研究空白')}\n{gap.get('description', '无描述')}\n\n"
            
            assistant_message = assistant.create_message(
                db,
                session.id,
                assistant.MessageCreate(
                    role=assistant.MessageRole.ASSISTANT,
                    content=response_content,
                    message_metadata={"analysis": analysis_data}
                )
            )
            
            # 更新会话结果
            session.result = analysis_data
            db.commit()
            logging.info("会话结果已保存到数据库")
            
            # 构建符合ResearchGapResponse的响应
            formatted_gaps = []
            for gap in analysis_data.get("researchGaps", []):
                evidence_list = []
                try:
                    for ev in gap.get("evidence", []):
                        if isinstance(ev, dict) and "source" in ev and "content" in ev:
                            evidence_list.append({
                                "text": ev["content"],
                                "reference": ev["source"]
                            })
                        elif isinstance(ev, dict) and "text" in ev and "reference" in ev:
                            evidence_list.append(ev)
                        else:
                            # 兼容性处理
                            evidence_list.append({
                                "text": str(ev),
                                "reference": "未指定来源"
                            })
                except Exception as e:
                    logging.error(f"处理证据数据时出错: {str(e)}")
                    evidence_list = []
                
                potential_directions = []
                try:
                    if isinstance(gap.get("potentialDirections"), list):
                        potential_directions = gap.get("potentialDirections")
                    else:
                        potential_directions = []
                except Exception as e:
                    logging.error(f"处理潜在方向数据时出错: {str(e)}")
                    potential_directions = []
                
                formatted_gaps.append({
                    "title": gap.get("title", "未命名研究空白"),
                    "description": gap.get("description", "无描述"),
                    "evidence": evidence_list,
                    "potentialDirections": potential_directions
                })
            
            # 记录请求总耗时
            end_time = time.time()
            total_time = end_time - start_time
            logging.info(f"研究空白分析请求处理完成，总耗时: {total_time:.2f}秒")
            
            return {
                "session_id": session.id,
                "domain": request.domain, 
                "summary": analysis_data.get("summary", "无总结"),
                "researchGaps": formatted_gaps,
                "references": analysis_data.get("references", [])
            }
        finally:
            # 恢复全局API密钥
            if provider and original_api_key:
                try:
                    background_tasks.add_task(
                        ai_settings_service.restore_global_api_key,
                        provider,
                        original_api_key
                    )
                except Exception as e:
                    logging.error(f"恢复API密钥失败: {str(e)}")
    except ValueError as e:
        logging.error(f"研究空白分析值错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logging.error(f"分析研究空白失败: {str(e)}", exc_info=True)
        # 确保向客户端返回有意义的错误信息
        error_detail = str(e)
        if len(error_detail) > 300:
            error_detail = error_detail[:300] + "..."
            
        # 创建会话记录错误
        try:
            error_session = assistant.create_session(
                db,
                current_user.id,
                assistant.SessionCreate(
                    title=f"处理出错: {request.domain}领域研究空白",
                    session_type="research_gap",
                    context={
                        "domain": request.domain,
                        "perspective": request.perspective,
                        "error": error_detail
                    }
                )
            )
            
            # 添加错误消息
            assistant.create_message(
                db,
                error_session.id,
                assistant.MessageCreate(
                    role=assistant.MessageRole.ASSISTANT,
                    content=f"很抱歉，处理请求时发生错误: {error_detail}\n\n请稍后重试或联系管理员。"
                )
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "处理请求失败",
                    "detail": error_detail,
                    "session_id": error_session.id
                }
            )
        except Exception as inner_e:
            logging.error(f"创建错误会话时发生二次错误: {str(inner_e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"处理请求失败: {error_detail}"
            )

@router.post("/research-problems/analyze", response_model=ResearchGapResponse)
async def analyze_domain_research_problems(
    request: ResearchGapRequest,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    分析研究领域的问题
    """
    try:
        # 请求开始时间记录，用于监控性能
        start_time = time.time()
        logging.info(f"研究问题分析请求开始，用户ID: {current_user.id}，领域: {request.domain}")
        
        provider = request.provider
        original_api_key = None
        
        # 如果用户有自定义API密钥，优先使用用户的密钥
        if provider:
            original_api_key = await ai_settings_service.use_user_api_key(db, current_user.id, provider)
        
        try:
            # 收集论文信息
            papers = []
            for paper_id in request.paper_ids:
                paper = paper_service.get_paper_by_id(db, paper_id, current_user.id)
                if paper:
                    papers.append({
                        "id": paper.id,
                        "title": paper.title,
                        "abstract": paper.abstract,
                        "content": paper.content,
                        "authors": paper.authors,
                        "year": paper.publication_date.year if paper.publication_date else None,
                        "publication_date": paper.publication_date.isoformat() if paper.publication_date else None
                    })
            
            # 分析研究问题
            logging.info(f"开始分析研究问题，领域：{request.domain}，角度：{request.perspective}，论文数量：{len(papers)}")
            
            # 使用assistant.py中的实现，而非ai_assistant.py
            try:
                analysis_result = await assistant.analyze_research_gaps(
                    db=db,
                    user_id=current_user.id,
                    domain=request.domain,
                    perspective=request.perspective,
                    paper_ids=request.paper_ids or [],
                    additional_context=request.additional_context
                )
            except Exception as analyze_error:
                logging.error(f"研究问题分析API调用失败: {str(analyze_error)}")
                # 创建会话记录错误
                error_session = assistant.create_session(
                    db,
                    current_user.id,
                    assistant.SessionCreate(
                        title=f"分析出错: {request.domain}领域研究问题",
                        session_type="research_gap",
                        context={
                            "domain": request.domain,
                            "perspective": request.perspective,
                            "error": str(analyze_error)
                        }
                    )
                )
                
                # 添加错误消息
                assistant.create_message(
                    db,
                    error_session.id,
                    assistant.MessageCreate(
                        role=assistant.MessageRole.ASSISTANT,
                        content=f"很抱歉，在分析{request.domain}领域研究问题时发生错误: {str(analyze_error)}\n\n请稍后重试或尝试减少输入内容。"
                    )
                )
                
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "error": "AI分析失败",
                        "detail": str(analyze_error),
                        "session_id": error_session.id
                    }
                )
            
            # 解构返回值，因为analyze_research_gaps返回的是一个元组 (session, result)
            session, analysis_data = analysis_result
            
            # 确保analysis_data已经初始化为字典
            if not isinstance(analysis_data, dict):
                analysis_data = {}
            
            # 确保分析结果具有一致的结构
            if "researchGaps" not in analysis_data and "research_gaps" in analysis_data:
                logging.info("修复字段名：将research_gaps转换为researchGaps")
                analysis_data["researchGaps"] = analysis_data.pop("research_gaps")
            elif "researchGaps" not in analysis_data and "research_gaps" not in analysis_data:
                logging.warning("分析结果缺少研究问题字段，添加空数组")
                analysis_data["researchGaps"] = []
                
            if "summary" not in analysis_data:
                logging.warning("分析结果缺少summary字段，添加默认内容")
                analysis_data["summary"] = "无法获取分析概要，请稍后重试。"
            
            # 规范化每个研究问题的结构
            for gap in analysis_data.get("researchGaps", []):
                if "potentialDirections" not in gap and "potential_directions" in gap:
                    logging.info("修复字段名：将potential_directions转换为potentialDirections")
                    gap["potentialDirections"] = gap.pop("potential_directions")
                    
                # 确保evidence字段存在
                if "evidence" not in gap:
                    gap["evidence"] = []
                    
                # 确保potentialDirections字段存在
                if "potentialDirections" not in gap:
                    gap["potentialDirections"] = []
            
            # 添加助手回复消息
            logging.info("构建助手响应消息")
            response_content = f"## {request.domain}领域研究问题分析\n\n{analysis_data['summary']}\n\n"
            for gap in analysis_data.get("researchGaps", []):
                response_content += f"### {gap.get('title', '未命名研究问题')}\n{gap.get('description', '无描述')}\n\n"
            
            assistant_message = assistant.create_message(
                db,
                session.id,
                assistant.MessageCreate(
                    role=assistant.MessageRole.ASSISTANT,
                    content=response_content,
                    message_metadata={"analysis": analysis_data}
                )
            )
            
            # 更新会话结果
            session.result = analysis_data
            db.commit()
            logging.info("会话结果已保存到数据库")
            
            # 构建符合ResearchGapResponse的响应
            formatted_gaps = []
            for gap in analysis_data.get("researchGaps", []):
                evidence_list = []
                try:
                    for ev in gap.get("evidence", []):
                        if isinstance(ev, dict) and "source" in ev and "content" in ev:
                            evidence_list.append({
                                "text": ev["content"],
                                "reference": ev["source"]
                            })
                        elif isinstance(ev, dict) and "text" in ev and "reference" in ev:
                            evidence_list.append(ev)
                        else:
                            # 兼容性处理
                            evidence_list.append({
                                "text": str(ev),
                                "reference": "未指定来源"
                            })
                except Exception as e:
                    logging.error(f"处理证据数据时出错: {str(e)}")
                    evidence_list = []
                
                potential_directions = []
                try:
                    if isinstance(gap.get("potentialDirections"), list):
                        potential_directions = gap.get("potentialDirections")
                    else:
                        potential_directions = []
                except Exception as e:
                    logging.error(f"处理潜在方向数据时出错: {str(e)}")
                    potential_directions = []
                
                formatted_gaps.append({
                    "title": gap.get("title", "未命名研究问题"),
                    "description": gap.get("description", "无描述"),
                    "evidence": evidence_list,
                    "potentialDirections": potential_directions
                })
            
            # 记录请求总耗时
            end_time = time.time()
            total_time = end_time - start_time
            logging.info(f"研究问题分析请求处理完成，总耗时: {total_time:.2f}秒")
            
            return {
                "session_id": session.id,
                "domain": request.domain, 
                "summary": analysis_data.get("summary", "无总结"),
                "researchGaps": formatted_gaps,
                "references": analysis_data.get("references", [])
            }
        finally:
            # 恢复全局API密钥
            if provider and original_api_key:
                try:
                    background_tasks.add_task(
                        ai_settings_service.restore_global_api_key,
                        provider,
                        original_api_key
                    )
                except Exception as e:
                    logging.error(f"恢复API密钥失败: {str(e)}")
    except ValueError as e:
        logging.error(f"研究问题分析值错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logging.error(f"研究问题分析未处理错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求时发生错误: {str(e)}"
        )

# 会话管理路由
@router.get("/sessions", response_model=List[SessionSummary])
async def get_user_sessions(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的会话列表
    """
    from src.services.assistant import get_sessions
    from src.schemas.assistant import AssistantType, SessionSummary
    
    sessions = get_sessions(db, current_user.id, skip, limit, active_only)
    
    # 计算每个会话的消息数量
    session_summaries = []
    for session in sessions:
        message_count = db.query(func.count(AssistantMessage.id)).filter(
            AssistantMessage.session_id == session.id
        ).scalar()
        
        summary = SessionSummary(
            id=session.id,
            title=session.title,
            session_type=AssistantType(session.session_type.value),
            created_at=session.created_at,
            updated_at=session.updated_at,
            last_message_at=session.last_message_at,
            message_count=message_count
        )
        session_summaries.append(summary)
    
    return session_summaries

@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_new_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新的会话
    """
    from src.services.assistant import create_session
    from src.schemas.assistant import SessionResponse, AssistantType
    
    db_session = create_session(db, current_user.id, session_data)
    
    # 创建会话响应
    session_response = SessionResponse(
        id=db_session.id,
        title=db_session.title,
        session_type=AssistantType(db_session.session_type.value),
        context=db_session.context,
        paper_id=db_session.paper_id,
        owner_id=db_session.owner_id,
        is_active=db_session.is_active,
        created_at=db_session.created_at,
        updated_at=db_session.updated_at,
        last_message_at=db_session.last_message_at,
        result=db_session.result,
        messages=[]
    )
    
    return session_response

@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session_detail(
    session_id: str,
    message_limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取会话详情，包括消息历史
    """
    from src.services.assistant import get_session_with_messages
    from src.schemas.assistant import MessageRole, AssistantType, MessageResponse, SessionResponse
    
    session = get_session_with_messages(db, session_id, current_user.id, message_limit)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权访问"
        )
    
    # 转换消息列表
    message_responses = []
    for msg in session.messages:
        message_response = MessageResponse(
            id=msg.id,
            session_id=msg.session_id,
            role=MessageRole(msg.role.value),
            content=msg.content,
            message_metadata=msg.message_metadata,
            sequence=msg.sequence,
            created_at=msg.created_at
        )
        message_responses.append(message_response)
    
    # 创建会话响应
    session_response = SessionResponse(
        id=session.id,
        title=session.title,
        session_type=AssistantType(session.session_type.value),
        context=session.context,
        paper_id=session.paper_id,
        owner_id=session.owner_id,
        is_active=session.is_active,
        created_at=session.created_at,
        updated_at=session.updated_at,
        last_message_at=session.last_message_at,
        result=session.result,
        messages=message_responses
    )
    
    return session_response

@router.put("/sessions/{session_id}", response_model=SessionResponse)
async def update_session_info(
    session_id: str,
    session_data: SessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新会话信息
    """
    from src.services.assistant import update_session
    from src.schemas.assistant import SessionResponse, AssistantType
    
    db_session = update_session(db, session_id, current_user.id, session_data)
    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权访问"
        )
    
    # 创建会话响应
    session_response = SessionResponse(
        id=db_session.id,
        title=db_session.title,
        session_type=AssistantType(db_session.session_type.value),
        context=db_session.context,
        paper_id=db_session.paper_id,
        owner_id=db_session.owner_id,
        is_active=db_session.is_active,
        created_at=db_session.created_at,
        updated_at=db_session.updated_at,
        last_message_at=db_session.last_message_at,
        result=db_session.result,
        messages=[]
    )
    
    return session_response

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_session(
    session_id: str,
    hard_delete: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除会话
    """
    from src.services.assistant import delete_session, hard_delete_session
    
    if hard_delete:
        success = hard_delete_session(db, session_id, current_user.id)
    else:
        success = delete_session(db, session_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权访问"
        )
    return None

# 消息相关路由
@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取会话的消息列表
    """
    from src.services.assistant import get_session, get_messages
    from src.schemas.assistant import MessageRole, MessageResponse
    
    session = get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权访问"
        )
    
    db_messages = get_messages(db, session_id, skip, limit)
    
    # 转换消息列表
    message_responses = []
    for msg in db_messages:
        message_response = MessageResponse(
            id=msg.id,
            session_id=msg.session_id,
            role=MessageRole(msg.role.value),
            content=msg.content,
            message_metadata=msg.message_metadata,
            sequence=msg.sequence,
            created_at=msg.created_at
        )
        message_responses.append(message_response)
    
    return message_responses

# 创新点生成请求模型
class InnovationIdeasRequest(BaseModel):
    research_topic: str = Field(..., description="研究主题")
    innovation_type: Optional[str] = Field(None, description="创新类型: theoretical(理论创新), methodological(方法创新), application(应用创新)")
    paper_ids: Optional[List[str]] = Field(None, description="相关论文ID列表")
    additional_context: Optional[str] = Field(None, description="额外上下文信息")
    provider: Optional[AIProvider] = Field(None, description="AI提供商")

# 创新点生成响应模型
class InnovationIdeasResponse(BaseModel):
    domain: str = Field(..., description="研究领域")
    innovationType: str = Field(..., description="创新类型")
    summary: str = Field(..., description="总体概述")
    innovations: List[Dict[str, Any]] = Field(..., description="创新点列表")
    references: Optional[List[str]] = Field(None, description="参考文献")
    provider: str = Field(..., description="AI提供商")

@router.post("/innovation-ideas/generate")
async def generate_innovation_ideas(
    request: InnovationIdeasRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成创新点建议
    """
    try:
        start_time = time.time()
        if not request.research_topic:
            return JSONResponse(
                status_code=400,
                content={"error": "研究主题不能为空"}
            )
        
        # 记录请求
        logging.info(f"收到创新点生成请求: 主题={request.research_topic}, 类型={request.innovation_type or 'methodological'}, 论文数量={len(request.paper_ids or [])}")
        
        # 创建会话
        session_create = SessionCreate(
            title=f"创新点分析: {request.research_topic}",
            session_type="innovation",
            context={
                "research_topic": request.research_topic,
                "innovation_type": request.innovation_type or "methodological",
                "paper_ids": request.paper_ids or []
            }
        )
        db_session = assistant.create_session(db, current_user.id, session_create)
        
        # 开始生成创新点
        ai_result = await assistant.generate_innovation_ideas(
            db=db,
            research_topic=request.research_topic,
            user_id=current_user.id,
            innovation_type=request.innovation_type,
            additional_context=request.additional_context,
            provider=request.provider,
            paper_ids=request.paper_ids
        )
        
        # 直接使用ai_result（已经是字典类型）
        try:
            # 包装响应
            response = {
                "session_id": str(db_session.id),
                "research_topic": request.research_topic,
                "innovation_type": request.innovation_type or "methodological",
                **ai_result
            }
            
            end_time = time.time()
            logging.info(f"创新点生成完成，耗时: {end_time - start_time:.2f}秒，创新点数量: {len(ai_result.get('innovations', []))}")
            
            return response
            
        except Exception as e:
            logging.error(f"处理AI返回结果时出错: {str(e)}")
            logging.error(f"原始返回类型: {type(ai_result)}")
            
            # 返回错误响应
            return JSONResponse(
                status_code=500,
                content={
                    "error": "处理AI响应失败",
                    "details": f"处理返回结果时出错: {str(e)}"
                }
            )
        
    except Exception as e:
        logging.error(f"生成创新点时发生错误: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "服务器处理错误",
                "details": str(e)
            }
        ) 