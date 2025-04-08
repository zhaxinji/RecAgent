from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Response
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import BackgroundTasks
import logging
import json
import re
import traceback

from src.schemas.writing import (
    WritingProjectCreate, 
    WritingProjectUpdate, 
    WritingProjectResponse, 
    WritingProjectListResponse,
    WritingSectionCreate,
    WritingSectionUpdate,
    WritingSectionResponse,
    CollaborationInviteResponse,
    CollaborationInviteCreate,
    ProjectExportResponse,
    SectionContentGenerationRequest,
    SectionContentImprovementRequest
)
from src.services import writing as writing_service
from src.core.deps import get_db, get_current_user
from src.models.user import User
from src.services import ai_settings as ai_settings_service

router = APIRouter(prefix="/writing", tags=["writing"])

# 添加一个专门的调试端点，用于检查API是否正常工作
@router.get("/check", status_code=status.HTTP_200_OK)
async def check_api():
    """
    检查API是否正常工作
    """
    return {"status": "ok", "message": "API工作正常"}

# 为项目列表添加特殊的错误处理
@router.options("/projects")
async def options_projects():
    """
    处理项目列表的预检请求
    """
    return Response(status_code=status.HTTP_200_OK)

# 项目管理接口
@router.post("/projects", response_model=WritingProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: WritingProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新写作项目
    """
    try:
        logging.info(f"用户 {current_user.id} 请求创建项目: {data.title}")
        project = writing_service.create_project(
            db=db,
            owner_id=current_user.id,
            title=data.title,
            description=data.description,
            template=data.template,
            related_papers=data.related_papers
        )
        
        # 确保项目有metadata字段，用于与前端兼容
        if hasattr(project, 'related_papers'):
            setattr(project, 'metadata', {'related_papers': project.related_papers})
        else:
            setattr(project, 'metadata', {})
            
        logging.info(f"项目创建成功: {project.id}")
        return project
    except Exception as e:
        stack_trace = traceback.format_exc()
        error_message = f"创建项目失败: {str(e)}\n{stack_trace}"
        logging.error(error_message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建项目失败: {str(e)}"
        )

@router.get("/projects", response_model=WritingProjectListResponse)
async def get_projects(
    query: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    include_collaborated: bool = True,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的写作项目列表
    """
    try:
        logging.info(f"用户 {current_user.id} 请求获取项目列表")
        # 获取项目列表
        projects = writing_service.get_projects(
            db=db,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            query=query,
            sort_by=sort_by,
            sort_order=sort_order,
            include_collaborated=include_collaborated
        )
        
        # 确保所有项目都有必要的属性，以便前端正确显示
        for project in projects:
            # 处理related_papers属性
            if not hasattr(project, 'related_papers') or project.related_papers is None:
                setattr(project, 'related_papers', [])
            
            # 处理metadata属性
            if not hasattr(project, 'metadata'):
                # 从描述中提取元数据
                meta_data = {}
                if project.description and "<!-- METADATA:" in project.description:
                    try:
                        meta_match = re.search(r'<!-- METADATA: (.*?) -->', project.description)
                        if meta_match:
                            meta_data = json.loads(meta_match.group(1))
                            if not isinstance(meta_data, dict):
                                meta_data = {}
                    except Exception as e:
                        logging.warning(f"解析项目 {project.id} 元数据时出错: {str(e)}")
                
                # 确保related_papers包含在metadata中
                if hasattr(project, 'related_papers') and project.related_papers:
                    meta_data['related_papers'] = project.related_papers
                
                # 确保metadata是一个字典类型
                if not isinstance(meta_data, dict):
                    meta_data = {}
                    
                setattr(project, 'metadata', meta_data)
            elif not isinstance(project.metadata, dict):
                # 如果metadata存在但不是字典，则重置为空字典
                setattr(project, 'metadata', {})
        
        total = len(projects)  # 简化计算，实际应使用count查询
        
        logging.info(f"成功获取到 {total} 个项目")
        return {
            "items": projects,
            "total": total,
            "page": skip // limit + 1 if limit > 0 else 1,
            "size": limit
        }
    except Exception as e:
        stack_trace = traceback.format_exc()
        error_message = f"获取项目列表失败: {str(e)}\n{stack_trace}"
        logging.error(error_message)
        
        # 返回一个空列表，避免前端白屏
        return {
            "items": [],
            "total": 0,
            "page": 1,
            "size": limit
        }

@router.get("/projects-debug")
async def get_projects_debug(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的写作项目列表（调试版本），直接返回JSON
    """
    try:
        logging.info(f"用户 {current_user.id} 请求获取项目列表（调试）")
        # 获取项目列表
        projects = writing_service.get_projects(
            db=db,
            user_id=current_user.id,
            skip=0,
            limit=100,
            query=None,
            sort_by="created_at",
            sort_order="desc",
            include_collaborated=True
        )
        
        # 将每个项目转换为字典
        project_dicts = []
        for project in projects:
            # 提取related_papers
            related_papers = []
            if hasattr(project, 'related_papers') and project.related_papers:
                related_papers = project.related_papers
            
            # 提取元数据
            metadata = {}
            try:
                if project.description and "<!-- METADATA:" in project.description:
                    meta_match = re.search(r'<!-- METADATA: (.*?) -->', project.description)
                    if meta_match:
                        metadata = json.loads(meta_match.group(1))
            except Exception as e:
                logging.warning(f"解析项目 {project.id} 元数据时出错: {str(e)}")
            
            # 确保metadata中包含related_papers
            if related_papers:
                metadata['related_papers'] = related_papers
            
            # 手动构建项目字典
            project_dict = {
                "id": project.id,
                "title": project.title,
                "description": project.description,
                "owner_id": project.owner_id,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                "related_papers": related_papers,
                "metadata": metadata,
                "collaborators": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "email": c.email
                    } for c in project.collaborators
                ] if project.collaborators else []
            }
            project_dicts.append(project_dict)
        
        return {
            "items": project_dicts,
            "total": len(project_dicts),
            "page": 1,
            "size": 100,
            "debug_info": {
                "schema_version": "1.0",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        stack_trace = traceback.format_exc()
        error_message = f"获取项目列表失败（调试）: {str(e)}\n{stack_trace}"
        logging.error(error_message)
        
        # 返回错误信息
        return {
            "error": str(e),
            "stack_trace": stack_trace,
            "items": [],
            "total": 0
        }

@router.get("/projects/{project_id}", response_model=WritingProjectResponse)
async def get_project(
    project_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    通过ID获取写作项目
    """
    try:
        logging.info(f"用户 {current_user.id} 请求获取项目 {project_id}")
        project = writing_service.get_project_by_id(db, project_id, current_user.id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目未找到或无权访问"
            )
        
        # 确保项目有related_papers属性
        if not hasattr(project, 'related_papers') or project.related_papers is None:
            project.related_papers = []
        
        # 确保项目有metadata字段，用于与前端兼容
        if not hasattr(project, 'metadata'):
            # 从描述中提取元数据
            meta_data = {}
            if project.description and "<!-- METADATA:" in project.description:
                try:
                    meta_match = re.search(r'<!-- METADATA: (.*?) -->', project.description)
                    if meta_match:
                        meta_data = json.loads(meta_match.group(1))
                        if not isinstance(meta_data, dict):
                            meta_data = {}
                except Exception as e:
                    logging.warning(f"解析项目 {project.id} 元数据时出错: {str(e)}")
            
            # 确保related_papers包含在metadata中
            if hasattr(project, 'related_papers') and project.related_papers:
                meta_data['related_papers'] = project.related_papers
            
            # 确保metadata是一个字典类型
            if not isinstance(meta_data, dict):
                meta_data = {}
                
            setattr(project, 'metadata', meta_data)
        elif not isinstance(project.metadata, dict):
            # 如果metadata存在但不是字典，则重置为空字典
            setattr(project, 'metadata', {})
            
        logging.info(f"成功获取项目 {project_id}")
        return project
    except HTTPException:
        # 直接重新抛出HTTP异常
        raise
    except Exception as e:
        logging.error(f"获取项目 {project_id} 失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取项目失败: {str(e)}"
        )

@router.patch("/projects/{project_id}", response_model=WritingProjectResponse)
async def update_project(
    project_id: str = Path(...),
    data: WritingProjectUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新写作项目信息
    """
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有提供更新数据"
        )
    
    project = writing_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目未找到或无权修改"
        )
    
    # 从描述中提取现有元数据
    meta_data = {}
    if project.description:
        meta_match = re.search(r'<!-- METADATA: (.*?) -->', project.description)
        if meta_match:
            try:
                meta_data = json.loads(meta_match.group(1))
            except:
                pass
    
    # 更新元数据
    meta_data.update({
        "updated_at": datetime.utcnow().isoformat()
    })
    
    # 如果数据中包含结构相关的字段，则更新到元数据中
    if hasattr(data, "structure"):
        meta_data["structure"] = data.structure
    
    # 更新描述，保留用户描述部分但更新元数据部分
    user_desc = project.description or ""
    if "<!-- METADATA:" in user_desc:
        user_desc = re.sub(r'\n\n<!-- METADATA:.*? -->', '', user_desc)
    
    updated_desc = user_desc + "\n\n<!-- METADATA: " + json.dumps(meta_data) + " -->"
    
    updated_project = writing_service.update_project(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        update_data={
            "description": updated_desc
        }
    )
    
    if not updated_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目未找到或无权修改"
        )
    
    return updated_project

@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除写作项目
    """
    result = writing_service.delete_project(db, project_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目未找到或无权删除"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# 章节管理接口
@router.get("/projects/{project_id}/sections", response_model=List[WritingSectionResponse])
async def get_project_sections(
    project_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取项目的所有章节
    """
    project = writing_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目未找到或无权访问"
        )
    
    sections = writing_service.get_sections(db, project_id, current_user.id)
    return sections

@router.post("/projects/{project_id}/sections", response_model=WritingSectionResponse, status_code=status.HTTP_201_CREATED)
async def create_section(
    project_id: str = Path(...),
    data: WritingSectionCreate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    为项目创建新章节
    """
    section = writing_service.create_section(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        title=data.title,
        content=data.content,
        order=data.order
    )
    
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目未找到或无权访问"
        )
    
    return section

@router.get("/sections/{section_id}", response_model=WritingSectionResponse)
async def get_section(
    section_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    通过ID获取章节
    """
    section = writing_service.get_section_by_id(db, section_id, current_user.id)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="章节未找到或无权访问"
        )
    return section

@router.patch("/sections/{section_id}", response_model=WritingSectionResponse)
async def update_section(
    section_id: str = Path(...),
    data: WritingSectionUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新章节信息
    """
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有提供更新数据"
        )
    
    updated_section = writing_service.update_section(
        db=db,
        section_id=section_id,
        user_id=current_user.id,
        update_data=data.dict(exclude_unset=True)
    )
    
    if not updated_section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="章节未找到或无权修改"
        )
    
    return updated_section

@router.delete("/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(
    section_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除章节
    """
    result = writing_service.delete_section(db, section_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="章节未找到或无权删除"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# 协作管理接口
@router.post("/projects/{project_id}/invite", response_model=CollaborationInviteResponse)
async def invite_collaborator(
    project_id: str = Path(...),
    data: CollaborationInviteCreate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    邀请协作者加入项目
    """
    invite = writing_service.invite_collaborator(
        db=db,
        project_id=project_id,
        owner_id=current_user.id,
        collaborator_email=data.email,
        message=data.message
    )
    
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目未找到或无权邀请协作者"
        )
    
    return invite

@router.post("/invitations/{invite_id}/accept")
async def accept_invitation(
    invite_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    接受协作邀请
    """
    result = writing_service.accept_invitation(db, invite_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法接受邀请，可能邀请已过期或不存在"
        )
    
    return {"message": "已成功接受邀请"}

@router.post("/invitations/{invite_id}/reject")
async def reject_invitation(
    invite_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    拒绝协作邀请
    """
    result = writing_service.reject_invitation(db, invite_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法拒绝邀请，可能邀请已不存在"
        )
    
    return {"message": "已拒绝邀请"}

@router.delete("/projects/{project_id}/collaborators/{collaborator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_collaborator(
    project_id: str = Path(...),
    collaborator_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    从项目中移除协作者
    """
    result = writing_service.remove_collaborator(db, project_id, current_user.id, collaborator_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法移除协作者，可能项目不存在或你不是项目所有者"
        )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# AI 辅助写作接口
@router.post("/sections/{section_id}/generate", response_model=WritingSectionResponse)
async def generate_section_content(
    section_id: str = Path(...),
    data: SectionContentGenerationRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    使用AI生成章节内容
    """
    try:
        content = await writing_service.generate_section_content(
            db=db,
            section_id=section_id,
            user_id=current_user.id,
            prompt=data.prompt,
            paper_id=data.paper_id
        )
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="章节未找到或无权访问"
            )
        
        # 获取更新后的章节
        section = writing_service.get_section_by_id(db, section_id, current_user.id)
        return section
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成内容失败: {str(e)}"
        )

@router.post("/sections/{section_id}/improve", response_model=WritingSectionResponse)
async def improve_section_content(
    section_id: str = Path(...),
    data: SectionContentImprovementRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    使用AI改进章节内容
    """
    try:
        content = await writing_service.improve_writing(
            db=db,
            section_id=section_id,
            user_id=current_user.id,
            improvement_type=data.improvement_type
        )
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="章节未找到或无权访问"
            )
        
        # 获取更新后的章节
        section = writing_service.get_section_by_id(db, section_id, current_user.id)
        return section
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"改进内容失败: {str(e)}"
        )

# 项目导出接口
@router.get("/projects/{project_id}/export", response_model=ProjectExportResponse)
async def export_project(
    project_id: str = Path(...),
    format: str = Query("markdown", regex="^(markdown|json)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    导出写作项目
    """
    try:
        export_data = writing_service.export_project(db, project_id, current_user.id, format)
        return export_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出项目失败: {str(e)}"
        )

class WritingPromptRequest(BaseModel):
    project_id: Optional[str] = None
    prompt_type: str = Field(..., description="提示类型，如'introduction', 'methodology', 'discussion'等")
    context: Optional[str] = Field(None, description="用户提供的上下文信息")
    references: Optional[List[str]] = Field(None, description="参考文献ID列表")
    style: Optional[str] = Field("academic", description="写作风格，如'academic', 'concise', 'detailed'等")
    custom_requirements: Optional[str] = Field(None, description="自定义要求")

class WritingPromptResponse(BaseModel):
    prompt: str = Field(..., description="生成的提示内容")
    suggestions: List[str] = Field(..., description="建议的写作方向")

@router.post("/generate-prompt", response_model=WritingPromptResponse)
async def generate_writing_prompt(
    request: WritingPromptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成论文写作提示
    
    基于用户选择的部分和上下文，生成针对性的写作提示
    """
    try:
        # 获取相关项目
        project = None
        if request.project_id:
            project = writing_service.get_project_by_id(db, request.project_id, current_user.id)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="项目未找到或无权访问"
                )
        
        # 获取参考文献
        references = []
        if request.references:
            from src.services import paper as paper_service
            for paper_id in request.references:
                paper = paper_service.get_paper_by_id(db, paper_id, current_user.id)
                if paper:
                    references.append({
                        "id": paper.id,
                        "title": paper.title,
                        "abstract": paper.abstract,
                        "authors": paper.authors
                    })
        
        # 生成写作提示
        result = await writing_service.generate_writing_prompt(
            prompt_type=request.prompt_type,
            context=request.context,
            references=references,
            style=request.style,
            custom_requirements=request.custom_requirements,
            project=project.to_dict() if project else None
        )
        
        return WritingPromptResponse(
            prompt=result["prompt"],
            suggestions=result["suggestions"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成写作提示失败: {str(e)}"
        )

class PaperStructureRequest(BaseModel):
    title: str = Field(..., description="论文标题")
    abstract: Optional[str] = Field(None, description="论文摘要")
    keywords: Optional[List[str]] = Field(None, description="关键词列表")
    research_area: str = Field(..., description="研究领域")
    paper_type: str = Field("research", description="论文类型，如'research', 'review', 'case-study'等")
    target_journal: Optional[str] = Field(None, description="目标期刊/会议")
    custom_requirements: Optional[str] = Field(None, description="自定义要求")

class SectionOutline(BaseModel):
    title: str = Field(..., description="章节标题")
    description: str = Field(..., description="章节内容描述")
    word_count: Optional[int] = Field(None, description="建议字数")
    key_points: List[str] = Field(..., description="关键点列表")

class PaperStructureResponse(BaseModel):
    sections: List[SectionOutline] = Field(..., description="论文章节结构")
    suggestions: List[str] = Field(..., description="写作建议")
    estimated_length: Optional[int] = Field(None, description="估计总字数")

@router.post("/generate-structure", response_model=PaperStructureResponse)
async def generate_paper_structure(
    request: PaperStructureRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成论文结构
    
    基于论文标题、摘要和研究领域等，生成完整的论文结构框架
    """
    try:
        result = await writing_service.generate_paper_structure(
            title=request.title,
            abstract=request.abstract,
            keywords=request.keywords,
            research_area=request.research_area,
            paper_type=request.paper_type,
            target_journal=request.target_journal,
            custom_requirements=request.custom_requirements
        )
        
        return PaperStructureResponse(
            sections=result["sections"],
            suggestions=result["suggestions"],
            estimated_length=result["estimated_length"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成论文结构失败: {str(e)}"
        )

@router.post("/projects/{project_id}/create-from-structure", response_model=WritingProjectResponse)
async def create_project_from_structure(
    project_id: str,
    structure: PaperStructureResponse,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    从生成的结构创建项目章节
    
    使用生成的论文结构，自动创建项目章节
    """
    project = writing_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目未找到或无权访问"
        )
    
    for i, section in enumerate(structure.sections):
        # 创建章节
        writing_service.create_section(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            title=section.title,
            content=section.description + "\n\n" + "\n".join([f"- {point}" for point in section.key_points]),
            order=i + 1  # 序号从1开始
        )
    
    # 更新项目
    # 从描述中提取现有元数据
    meta_data = {}
    if project.description:
        meta_match = re.search(r'<!-- METADATA: (.*?) -->', project.description)
        if meta_match:
            try:
                meta_data = json.loads(meta_match.group(1))
            except:
                pass
    
    # 更新元数据
    meta_data.update({
        "structure": structure.dict() if hasattr(structure, "dict") else structure,
        "updated_at": datetime.utcnow().isoformat()
    })
    
    # 更新描述，保留用户描述部分但更新元数据部分
    user_desc = project.description or ""
    if "<!-- METADATA:" in user_desc:
        user_desc = re.sub(r'\n\n<!-- METADATA:.*? -->', '', user_desc)
    
    updated_desc = user_desc + "\n\n<!-- METADATA: " + json.dumps(meta_data) + " -->"
    
    updated_project = writing_service.update_project(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        update_data={
            "description": updated_desc
        }
    )
    
    return updated_project

# 新增部分
class ContentGenerationRequest(BaseModel):
    """内容生成请求模型"""
    section_type: str = Field(..., description="论文部分类型")
    writing_style: str = Field("academic", description="写作风格")
    topic: Optional[str] = Field(None, description="研究主题")
    research_problem: Optional[str] = Field(None, description="研究问题")
    method_feature: Optional[str] = Field(None, description="方法特点")
    modeling_target: Optional[str] = Field(None, description="建模目标")
    improvement: Optional[str] = Field(None, description="性能提升")
    key_component: Optional[str] = Field(None, description="关键组件")
    impact: Optional[str] = Field(None, description="研究影响")
    additional_context: Optional[str] = Field(None, description="额外上下文信息")

class ContentGenerationResponse(BaseModel):
    content: str = Field(..., description="生成的内容")
    suggestions: List[str] = Field(..., description="写作建议")

@router.get("/paper-sections")
async def get_paper_sections():
    """
    获取论文部分类型列表
    """
    return [
        {"value": "abstract", "label": "摘要", "description": "概括研究内容、方法和主要结果"},
        {"value": "introduction", "label": "引言", "description": "介绍研究背景、动机和贡献"},
        {"value": "related_work", "label": "相关工作", "description": "总结和评价已有相关研究"},
        {"value": "methodology", "label": "方法论", "description": "详细描述研究方法和实现细节"},
        {"value": "experiment", "label": "实验", "description": "实验设计、结果分析和讨论"},
        {"value": "conclusion", "label": "结论", "description": "总结主要发现和未来工作"}
    ]

@router.get("/writing-styles")
async def get_writing_styles():
    """
    获取写作风格列表
    """
    return [
        {"value": "academic", "label": "学术风格", "description": "严谨、正式的学术论文风格"},
        {"value": "technical", "label": "技术报告风格", "description": "注重技术细节的报告风格"},
        {"value": "explanatory", "label": "解释性风格", "description": "通俗易懂、注重解释的风格"},
        {"value": "concise", "label": "简洁风格", "description": "简明扼要、重点突出的风格"},
        {"value": "detailed", "label": "详尽风格", "description": "详细全面的描述风格"}
    ]

@router.post("/generate-content", response_model=ContentGenerationResponse)
async def generate_content(
    request: ContentGenerationRequest,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user)
):
    """
    基于用户输入的参数生成论文内容
    """
    try:
        logging.info(f"用户 {current_user.id} 请求生成论文内容: {request.section_type}")
        
        # 使用ai_assistant_fixed服务生成内容
        from src.services.ai_assistant_fixed import get_assistant
        
        ai_assistant = get_assistant()
        
        result = await ai_assistant.generate_paper_section(
            section_type=request.section_type,
            writing_style=request.writing_style,
            topic=request.topic,
            research_problem=request.research_problem,
            method_feature=request.method_feature,
            modeling_target=request.modeling_target,
            improvement=request.improvement,
            key_component=request.key_component,
            impact=request.impact,
            additional_context=request.additional_context
        )
        
        # 记录成功生成内容
        logging.info(f"成功生成{request.section_type}内容，长度: {len(result['content'])}")
        
        # 返回生成的内容
        return {
            "content": result["content"],
            "suggestions": result.get("suggestions", [])
        }
        
    except Exception as e:
        stack_trace = traceback.format_exc()
        error_message = f"生成内容失败: {str(e)}\n{stack_trace}"
        logging.error(error_message)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成内容失败: {str(e)}"
        )

@router.get("/projects/{project_id}/debug")
async def get_project_debug(
    project_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取项目详细信息（调试版本）
    """
    try:
        logging.info(f"用户 {current_user.id} 请求获取项目 {project_id} 的调试信息")
        project = writing_service.get_project_by_id(db, project_id, current_user.id)
        if not project:
            return {
                "error": "项目未找到或无权访问",
                "project_id": project_id,
                "user_id": current_user.id,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # 获取项目的所有属性
        project_attrs = {}
        for attr in dir(project):
            if not attr.startswith('_') and attr not in ['metadata', 'registry', 'to_dict']:
                try:
                    value = getattr(project, attr)
                    # 处理复杂对象
                    if callable(value):
                        continue
                    elif hasattr(value, '__dict__'):
                        project_attrs[attr] = str(value)
                    else:
                        project_attrs[attr] = value
                except Exception as e:
                    project_attrs[attr] = f"错误: {str(e)}"
        
        # 提取元数据
        metadata = {}
        try:
            if project.description and "<!-- METADATA:" in project.description:
                meta_match = re.search(r'<!-- METADATA: (.*?) -->', project.description)
                if meta_match:
                    metadata = json.loads(meta_match.group(1))
        except Exception as e:
            metadata = {"error": f"解析元数据时出错: {str(e)}"}
        
        # 使用项目的to_dict方法
        project_dict = None
        try:
            if hasattr(project, 'to_dict') and callable(getattr(project, 'to_dict')):
                project_dict = project.to_dict()
        except Exception as e:
            project_dict = {"error": f"调用to_dict方法出错: {str(e)}"}
        
        return {
            "project_id": project_id,
            "user_id": current_user.id,
            "project_attributes": project_attrs,
            "metadata_extracted": metadata,
            "project_dict": project_dict,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        stack_trace = traceback.format_exc()
        error_message = f"获取项目 {project_id} 调试信息失败: {str(e)}\n{stack_trace}"
        logging.error(error_message)
        
        return {
            "error": str(e),
            "stack_trace": stack_trace,
            "project_id": project_id,
            "user_id": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        } 