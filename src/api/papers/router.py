import os, sys
from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query, Response, Body, Request
from fastapi.responses import StreamingResponse, FileResponse
from starlette.background import BackgroundTask
from sqlalchemy.orm import Session
import json
from datetime import datetime, date
import io
import uuid
import shutil
import tempfile
import re
import traceback

from src.core.deps import get_db, get_current_user
from src.models.user import User
from src.models.paper import Paper, Tag, Note, paper_tags, paper_categories, Folder, Category, Annotation
from src.services import paper as paper_service
from src.services import ai_assistant as assistant_service
from src.schemas.paper import (
    PaperCreate, PaperUpdate, PaperResponse, 
    TagCreate, TagResponse, 
    NoteCreate, NoteUpdate, NoteResponse,
    UploadResponse, PaperSearchRequest,
    PaperContentResponse,
    PaperUpload,
    PaperImportUrl,
    PaperImportDoi,
    PaperImportArxiv,
    PapersListResponse,
    PaperTagsUpdate,
    AnnotationCreate,
    AnnotationUpdate,
    AnnotationResponse,
    PaperAnalysisRequest,
    PaperAnalysisResponse,
    ExternalSearchRequest,
    ExternalSearchResponse,
    FolderCreate,
    FolderResponse,
    FolderUpdate,
    CategoryCreate,
    CategoryResponse,
    SearchSourceEnum,
    PaperMetadataResponse,
    TagUpdate
)
from src.utils.file_utils import save_uploaded_file, get_pdf_content, create_thumbnail

router = APIRouter(prefix="/papers", tags=["papers"])

# 论文管理接口
@router.post("/", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def create_paper(
    paper_data: PaperCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新论文
    """
    try:
        # 提取PaperCreate对象中的字段，而不是直接传递整个对象
        print(f"正在创建论文: {paper_data.title}")
        paper = paper_service.create_paper(
            db=db, 
            user_id=current_user.id, 
            title=paper_data.title,
            abstract=paper_data.abstract,
            authors=paper_data.authors,
            publication_date=paper_data.publication_date,
            journal=paper_data.journal,
            conference=paper_data.conference,
            doi=paper_data.doi,
            url=paper_data.url,
            file_path=paper_data.file_path,
            tags=paper_data.tags,
            metadata=paper_data.metadata,
            content=paper_data.content,
            source=paper_data.source.value if paper_data.source else "manual"
        )
        
        # 如果论文创建成功且有文件夹ID，更新文件夹关联
        if paper and paper_data.folder_id:
            paper.folder_id = paper_data.folder_id
            db.commit()
            
        # 如果有分类ID，添加分类关联
        if paper and paper_data.category_ids and len(paper_data.category_ids) > 0:
            for category_id in paper_data.category_ids:
                category = db.query(Category).filter(
                    Category.id == category_id,
                    Category.owner_id == current_user.id
                ).first()
                if category:
                    paper.categories.append(category)
            db.commit()
        
        # 不直接返回paper对象，而是构建一个符合PaperResponse的字典
        response_data = {
            "id": paper.id,
            "title": paper.title,
            "abstract": paper.abstract,
            "authors": paper.authors if hasattr(paper, 'authors') and paper.authors else [],
            "publication_date": paper.publication_date,
            "journal": paper.journal,
            "conference": paper.conference,
            "doi": paper.doi,
            "url": paper.url,
            "tags": [tag.name for tag in paper.tags] if hasattr(paper, 'tags') and paper.tags else [],
            "notes": "",  # 确保为空字符串而不是空列表
            "owner_id": paper.owner_id,
            "created_at": paper.created_at,
            "updated_at": paper.updated_at,
            "file_path": paper.file_path,
            "source": paper.source if hasattr(paper, 'source') and paper.source else "manual",
            "has_content": bool(paper.content) if hasattr(paper, 'content') else False,
            "has_file": bool(paper.file_path) if hasattr(paper, 'file_path') else False,
            "page_count": None,  # 默认为None
            "metadata": paper.paper_metadata if hasattr(paper, 'paper_metadata') and paper.paper_metadata else {},
            "is_favorite": paper.is_favorite if hasattr(paper, 'is_favorite') else False,
            "folder_id": paper.folder_id if hasattr(paper, 'folder_id') else None,
            "folder_name": paper.folder.name if hasattr(paper, 'folder') and paper.folder else None,
            "categories": [{"id": cat.id, "name": cat.name} for cat in paper.categories] if hasattr(paper, 'categories') and paper.categories else [],
            "analysis_status": paper.analysis_status if hasattr(paper, 'analysis_status') else None,
            "analysis_progress": paper.analysis_progress if hasattr(paper, 'analysis_progress') else 0
        }
        
        return response_data
    except Exception as e:
        import traceback
        print(f"创建论文失败: {str(e)}")
        print(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建论文失败: {str(e)}"
        )

@router.post("/upload", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def upload_paper(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    extract_content: bool = Form(True),
    analyze_content: bool = Form(True),
    folder_id: Optional[str] = Form(None),
    category_ids: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传论文文件并自动进行内容分析
    """
    try:
        # 解析category_ids（如果提供）
        categories = None
        if category_ids:
            try:
                categories = json.loads(category_ids)
            except:
                categories = category_ids.split(',') if ',' in category_ids else [category_ids]
        
        # 使用修改后的函数签名调用上传服务
        paper = await paper_service.upload_paper_file(
            db=db,
            file=file,
            user_id=current_user.id,
            title=title,
            extract_content=extract_content,
            analyze_content=analyze_content,
            folder_id=folder_id,
            category_ids=categories
        )
        
        # 构建符合PaperResponse的响应对象
        response_data = {
            "id": paper.id,
            "title": paper.title,
            "abstract": paper.abstract,
            "authors": paper.authors if hasattr(paper, 'authors') and paper.authors else [],
            "publication_date": paper.publication_date,
            "journal": paper.journal,
            "conference": paper.conference,
            "doi": paper.doi,
            "url": paper.url,
            "tags": [],  # 默认为空列表
            "notes": "",  # 默认为空字符串
            "owner_id": paper.owner_id,
            "created_at": paper.created_at,
            "updated_at": paper.updated_at,
            "file_path": paper.file_path,
            "source": "upload",  # 设置为上传类型
            "has_content": bool(paper.content),  # 检查是否有内容
            "has_file": bool(paper.file_path),  # 检查是否有文件
            "page_count": None,  # 默认为None
            "metadata": paper.paper_metadata if hasattr(paper, 'paper_metadata') and paper.paper_metadata else {},
            "is_favorite": paper.is_favorite,
            "folder_id": paper.folder_id,  # 使用实际文件夹ID
            "folder_name": None,  # 默认为None
            "categories": [],  # 默认为空列表
            "analysis_status": None,  # 默认为None
            "analysis_progress": paper.analysis_progress if hasattr(paper, 'analysis_progress') else 0
        }
        
        return response_data
    except Exception as e:
        import traceback
        print(f"上传论文失败: {str(e)}")
        print(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"上传论文失败: {str(e)}"
        )

@router.post("/import/url", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def import_paper_from_url(
    import_data: PaperImportUrl,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    从URL导入论文
    """
    try:
        paper = await paper_service.import_paper_from_url(
            db, 
            current_user.id, 
            import_data
        )
        return paper
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"从URL导入论文失败: {str(e)}"
        )

@router.post("/import/doi", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def import_paper_from_doi(
    import_data: PaperImportDoi,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    从DOI导入论文
    """
    try:
        paper = await paper_service.import_paper_from_doi(
            db, 
            current_user.id, 
            import_data
        )
        return paper
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"从DOI导入论文失败: {str(e)}"
        )

@router.post("/import/arxiv", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def import_paper_from_arxiv(
    import_data: PaperImportArxiv,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    从arXiv导入论文
    """
    try:
        paper = await paper_service.import_paper_from_arxiv(
            db, 
            current_user.id, 
            import_data
        )
        return paper
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"从arXiv导入论文失败: {str(e)}"
        )

@router.get("/", response_model=PapersListResponse)
async def list_papers(
    query: Optional[str] = None,
    tags: Optional[str] = None,
    favorite: Optional[bool] = None,
    sort_by: Optional[str] = "updated_at",
    sort_order: Optional[str] = "desc",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的论文列表
    """
    # 解析标签过滤条件
    tag_list = tags.split(",") if tags else None
    
    # 调用服务函数
    papers, total = paper_service.get_user_papers(
        db,
        current_user.id,
        query=query,
        tags=tag_list,
        favorite=favorite,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=(page - 1) * per_page,
        limit=per_page
    )
    
    # 转换为API响应格式
    paper_responses = []
    for paper in papers:
        paper_responses.append({
            "id": paper.id,
            "title": paper.title,
            "abstract": paper.abstract,
            "authors": paper.authors if hasattr(paper, 'authors') and paper.authors else [],
            "publication_date": paper.publication_date,
            "journal": paper.journal,
            "conference": paper.conference,
            "doi": paper.doi,
            "url": paper.url,
            "tags": [tag.name for tag in paper.tags] if hasattr(paper, 'tags') and paper.tags else [],
            "notes": paper.notes if hasattr(paper, 'notes') and isinstance(paper.notes, str) else "",
            "owner_id": paper.owner_id,
            "created_at": paper.created_at,
            "updated_at": paper.updated_at,
            "file_path": paper.file_path,
            "source": paper.source if hasattr(paper, 'source') and paper.source else "manual",
            "has_content": hasattr(paper, 'has_content') and paper.has_content if hasattr(paper, 'has_content') else bool(paper.content),
            "has_file": hasattr(paper, 'has_file') and paper.has_file if hasattr(paper, 'has_file') else bool(paper.file_path),
            "page_count": paper.page_count if hasattr(paper, 'page_count') else None,
            "metadata": paper.paper_metadata if hasattr(paper, 'paper_metadata') and paper.paper_metadata else {},
            "is_favorite": paper.is_favorite if hasattr(paper, 'is_favorite') else False,
            "folder_id": paper.folder_id if hasattr(paper, 'folder_id') else None,
            "folder_name": paper.folder.name if hasattr(paper, 'folder') and paper.folder else None,
            "categories": [{"id": cat.id, "name": cat.name} for cat in paper.categories] if hasattr(paper, 'categories') and paper.categories else [],
            "analysis_status": paper.analysis_status if hasattr(paper, 'analysis_status') else None,
            "analysis_progress": paper.analysis_progress if hasattr(paper, 'analysis_progress') else 0
        })
    
    return {
        "papers": paper_responses,
        "total": total,
        "page": page,
        "per_page": per_page
    }

@router.get("/tags")
async def get_user_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户已使用的所有标签
    """
    tags = paper_service.get_tags(db, current_user.id)
    return tags

@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取论文详情
    """
    paper = paper_service.get_paper_by_id(db, paper_id, current_user.id)
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="论文未找到"
        )
    
    # 确保刷新数据库会话以获取最新进度
    db.refresh(paper)
    
    # 构建符合PaperResponse的响应对象
    response_data = {
        "id": paper.id,
        "title": paper.title,
        "abstract": paper.abstract,
        "authors": paper.authors if hasattr(paper, 'authors') and paper.authors else [],
        "publication_date": paper.publication_date,
        "journal": paper.journal,
        "conference": paper.conference,
        "doi": paper.doi,
        "url": paper.url,
        "tags": [tag.name for tag in paper.tags] if hasattr(paper, 'tags') and paper.tags else [],
        "notes": paper.notes if hasattr(paper, 'notes') and isinstance(paper.notes, str) else "",
        "owner_id": paper.owner_id,
        "created_at": paper.created_at,
        "updated_at": paper.updated_at,
        "file_path": paper.file_path,
        "source": paper.source if hasattr(paper, 'source') and paper.source else "manual",
        "has_content": hasattr(paper, 'has_content') and paper.has_content if hasattr(paper, 'has_content') else bool(paper.content),
        "has_file": hasattr(paper, 'has_file') and paper.has_file if hasattr(paper, 'has_file') else bool(paper.file_path),
        "page_count": paper.page_count if hasattr(paper, 'page_count') else None,
        "metadata": paper.paper_metadata if hasattr(paper, 'paper_metadata') and paper.paper_metadata else {},
        "is_favorite": paper.is_favorite if hasattr(paper, 'is_favorite') else False,
        "folder_id": paper.folder_id if hasattr(paper, 'folder_id') else None,
        "folder_name": paper.folder.name if hasattr(paper, 'folder') and paper.folder else None,
        "categories": [{"id": cat.id, "name": cat.name} for cat in paper.categories] if hasattr(paper, 'categories') and paper.categories else [],
        "analysis_status": paper.analysis_status if hasattr(paper, 'analysis_status') else None,
        "analysis_progress": paper.analysis_progress if hasattr(paper, 'analysis_progress') else 0
    }
    
    # 记录实际返回的进度值，用于调试
    print(f"返回论文详情，ID:{paper_id}, 分析状态:{response_data['analysis_status']}, 分析进度:{response_data['analysis_progress']}%")
    
    return response_data

@router.get("/{paper_id}/content", response_model=PaperContentResponse)
async def get_paper_with_content(
    paper_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取论文详情及内容
    """
    paper = paper_service.get_paper_with_content(db, paper_id, current_user.id)
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="论文未找到"
        )
    return paper

@router.patch("/{paper_id}", response_model=PaperResponse)
async def update_paper(
    paper_id: str,
    paper_data: PaperUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新论文信息
    """
    try:
        updated_paper = paper_service.update_paper(
            db, 
            paper_id, 
            current_user.id, 
            paper_data.dict(exclude_unset=True)
        )
        if not updated_paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="论文未找到"
            )
        
        # 构建符合PaperResponse的响应对象，而不是直接返回ORM对象
        response_data = {
            "id": updated_paper.id,
            "title": updated_paper.title,
            "abstract": updated_paper.abstract,
            "authors": updated_paper.authors if hasattr(updated_paper, 'authors') and updated_paper.authors else [],
            "publication_date": updated_paper.publication_date,
            "journal": updated_paper.journal,
            "conference": updated_paper.conference,
            "doi": updated_paper.doi,
            "url": updated_paper.url,
            "tags": [tag.name for tag in updated_paper.tags] if hasattr(updated_paper, 'tags') and updated_paper.tags else [],
            "notes": updated_paper.notes if hasattr(updated_paper, 'notes') and isinstance(updated_paper.notes, str) else "",
            "owner_id": updated_paper.owner_id,
            "created_at": updated_paper.created_at,
            "updated_at": updated_paper.updated_at,
            "file_path": updated_paper.file_path,
            "source": updated_paper.source if hasattr(updated_paper, 'source') and updated_paper.source else "manual",
            "has_content": hasattr(updated_paper, 'has_content') and updated_paper.has_content if hasattr(updated_paper, 'has_content') else bool(updated_paper.content),
            "has_file": hasattr(updated_paper, 'has_file') and updated_paper.has_file if hasattr(updated_paper, 'has_file') else bool(updated_paper.file_path),
            "page_count": updated_paper.page_count if hasattr(updated_paper, 'page_count') else None,
            "metadata": updated_paper.paper_metadata if hasattr(updated_paper, 'paper_metadata') and updated_paper.paper_metadata else {},
            "is_favorite": updated_paper.is_favorite if hasattr(updated_paper, 'is_favorite') else False,
            "folder_id": updated_paper.folder_id if hasattr(updated_paper, 'folder_id') else None,
            "folder_name": updated_paper.folder.name if hasattr(updated_paper, 'folder') and updated_paper.folder else None,
            "categories": [{"id": cat.id, "name": cat.name} for cat in updated_paper.categories] if hasattr(updated_paper, 'categories') and updated_paper.categories else [],
            "analysis_status": updated_paper.analysis_status if hasattr(updated_paper, 'analysis_status') else None,
            "analysis_progress": updated_paper.analysis_progress if hasattr(updated_paper, 'analysis_progress') else 0
        }
        
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新论文失败: {str(e)}"
        )

@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper(
    paper_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除论文
    """
    success = paper_service.delete_paper(db, paper_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="论文未找到"
        )
    return None

@router.patch("/{paper_id}/tags", response_model=PaperResponse)
async def update_paper_tags(
    paper_id: str,
    tags_update: PaperTagsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新论文标签
    """
    try:
        updated_paper = paper_service.update_paper_tags(
            db, 
            paper_id, 
            current_user.id, 
            tags_update.operations
        )
        if not updated_paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="论文未找到"
            )
            
        # 构建符合PaperResponse的响应对象，而不是直接返回ORM对象
        response_data = {
            "id": updated_paper.id,
            "title": updated_paper.title,
            "abstract": updated_paper.abstract,
            "authors": updated_paper.authors if hasattr(updated_paper, 'authors') and updated_paper.authors else [],
            "publication_date": updated_paper.publication_date,
            "journal": updated_paper.journal,
            "conference": updated_paper.conference,
            "doi": updated_paper.doi,
            "url": updated_paper.url,
            "tags": [tag.name for tag in updated_paper.tags] if hasattr(updated_paper, 'tags') and updated_paper.tags else [],
            "notes": updated_paper.notes if hasattr(updated_paper, 'notes') and isinstance(updated_paper.notes, str) else "",
            "owner_id": updated_paper.owner_id,
            "created_at": updated_paper.created_at,
            "updated_at": updated_paper.updated_at,
            "file_path": updated_paper.file_path,
            "source": updated_paper.source if hasattr(updated_paper, 'source') and updated_paper.source else "manual",
            "has_content": hasattr(updated_paper, 'has_content') and updated_paper.has_content if hasattr(updated_paper, 'has_content') else bool(updated_paper.content),
            "has_file": hasattr(updated_paper, 'has_file') and updated_paper.has_file if hasattr(updated_paper, 'has_file') else bool(updated_paper.file_path),
            "page_count": updated_paper.page_count if hasattr(updated_paper, 'page_count') else None,
            "metadata": updated_paper.paper_metadata if hasattr(updated_paper, 'paper_metadata') and updated_paper.paper_metadata else {},
            "is_favorite": updated_paper.is_favorite if hasattr(updated_paper, 'is_favorite') else False,
            "folder_id": updated_paper.folder_id if hasattr(updated_paper, 'folder_id') else None,
            "folder_name": updated_paper.folder.name if hasattr(updated_paper, 'folder') and updated_paper.folder else None,
            "categories": [{"id": cat.id, "name": cat.name} for cat in updated_paper.categories] if hasattr(updated_paper, 'categories') and updated_paper.categories else [],
            "analysis_status": updated_paper.analysis_status if hasattr(updated_paper, 'analysis_status') else None,
            "analysis_progress": updated_paper.analysis_progress if hasattr(updated_paper, 'analysis_progress') else 0
        }
        
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新标签失败: {str(e)}"
        )

@router.post("/{paper_id}/favorite", response_model=PaperResponse)
async def toggle_favorite(
    paper_id: str,
    is_favorite: bool = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    设置论文收藏状态
    """
    try:
        updated_paper = paper_service.set_paper_favorite(
            db, 
            paper_id, 
            current_user.id, 
            is_favorite
        )
        if not updated_paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="论文未找到"
            )
            
        # 构建符合PaperResponse的响应对象，而不是直接返回ORM对象
        response_data = {
            "id": updated_paper.id,
            "title": updated_paper.title,
            "abstract": updated_paper.abstract,
            "authors": updated_paper.authors if hasattr(updated_paper, 'authors') and updated_paper.authors else [],
            "publication_date": updated_paper.publication_date,
            "journal": updated_paper.journal,
            "conference": updated_paper.conference,
            "doi": updated_paper.doi,
            "url": updated_paper.url,
            "tags": [tag.name for tag in updated_paper.tags] if hasattr(updated_paper, 'tags') and updated_paper.tags else [],
            "notes": updated_paper.notes if hasattr(updated_paper, 'notes') and isinstance(updated_paper.notes, str) else "",
            "owner_id": updated_paper.owner_id,
            "created_at": updated_paper.created_at,
            "updated_at": updated_paper.updated_at,
            "file_path": updated_paper.file_path,
            "source": updated_paper.source if hasattr(updated_paper, 'source') and updated_paper.source else "manual",
            "has_content": hasattr(updated_paper, 'has_content') and updated_paper.has_content if hasattr(updated_paper, 'has_content') else bool(updated_paper.content),
            "has_file": hasattr(updated_paper, 'has_file') and updated_paper.has_file if hasattr(updated_paper, 'has_file') else bool(updated_paper.file_path),
            "page_count": updated_paper.page_count if hasattr(updated_paper, 'page_count') else None,
            "metadata": updated_paper.paper_metadata if hasattr(updated_paper, 'paper_metadata') and updated_paper.paper_metadata else {},
            "is_favorite": updated_paper.is_favorite if hasattr(updated_paper, 'is_favorite') else is_favorite,
            "folder_id": updated_paper.folder_id if hasattr(updated_paper, 'folder_id') else None,
            "folder_name": updated_paper.folder.name if hasattr(updated_paper, 'folder') and updated_paper.folder else None,
            "categories": [{"id": cat.id, "name": cat.name} for cat in updated_paper.categories] if hasattr(updated_paper, 'categories') and updated_paper.categories else [],
            "analysis_status": updated_paper.analysis_status if hasattr(updated_paper, 'analysis_status') else None,
            "analysis_progress": updated_paper.analysis_progress if hasattr(updated_paper, 'analysis_progress') else 0
        }
        
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"设置收藏状态失败: {str(e)}"
        )

@router.post("/{paper_id}/annotations", response_model=AnnotationResponse)
async def create_annotation(
    paper_id: str,
    annotation_data: AnnotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建论文注释
    """
    try:
        annotation = paper_service.create_paper_annotation(
            db, 
            paper_id, 
            current_user.id, 
            annotation_data
        )
        return annotation
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建注释失败: {str(e)}"
        )

@router.get("/{paper_id}/annotations", response_model=List[AnnotationResponse])
async def get_annotations(
    paper_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取论文注释列表
    """
    annotations = paper_service.get_paper_annotations(db, paper_id, current_user.id)
    return annotations

@router.patch("/{paper_id}/annotations/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation(
    paper_id: str,
    annotation_id: str,
    annotation_data: AnnotationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新论文注释
    """
    try:
        updated_annotation = paper_service.update_paper_annotation(
            db, 
            paper_id, 
            annotation_id, 
            current_user.id, 
            annotation_data
        )
        if not updated_annotation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="注释未找到"
            )
        return updated_annotation
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新注释失败: {str(e)}"
        )

@router.delete("/{paper_id}/annotations/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_annotation(
    paper_id: str,
    annotation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除论文注释
    """
    success = paper_service.delete_paper_annotation(db, paper_id, annotation_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="注释未找到"
        )
    return None

@router.get("/{paper_id}/file")
async def download_paper_file(
    paper_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    下载论文文件
    """
    try:
        file_info = await paper_service.get_paper_file(db, paper_id, current_user.id)
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="论文文件未找到"
            )
        
        # 根据文件类型处理
        if file_info["file_type"] == "local":
            # 返回本地文件
            return FileResponse(
                path=file_info["file_path"],
                filename=file_info["file_name"],
                media_type=file_info["content_type"]
            )
        elif file_info["file_type"] == "temp":
            # 返回临时生成的文件，使用后删除
            return FileResponse(
                path=file_info["file_path"],
                filename=file_info["file_name"],
                media_type=file_info["content_type"],
                background=BackgroundTask(lambda: os.unlink(file_info["file_path"]))
            )
        elif file_info["file_type"] == "content":
            # 返回纯文本内容
            return StreamingResponse(
                io.BytesIO(file_info["content"].encode('utf-8')),
                media_type=file_info["content_type"],
                headers={"Content-Disposition": f'attachment; filename="{file_info["file_name"]}"'}
            )
        else:
            # 其他类型
            return StreamingResponse(
                io.BytesIO(file_info["content"]),
                media_type=file_info["content_type"],
                headers={"Content-Disposition": f'attachment; filename="{file_info["file_name"]}"'}
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"获取文件失败: {str(e)}"
        )

# 标签管理接口
@router.get("/tags", response_model=List[TagResponse])
async def get_all_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取所有标签
    """
    tags_with_count = paper_service.get_tags(db, current_user.id)
    result = []
    for tag, count in tags_with_count:
        tag_dict = tag.__dict__
        tag_dict["paper_count"] = count
        result.append(tag_dict)
    return result

@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    data: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新标签
    """
    tag = paper_service.create_tag(db, data.name, data.color)
    return tag

@router.patch("/tags/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: str,
    data: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新标签
    """
    tag = paper_service.update_tag(db, tag_id, data.name, data.color)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="标签未找到"
        )
    return tag

@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除标签
    """
    result = paper_service.delete_tag(db, tag_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="标签未找到"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# 笔记管理接口
@router.get("/{paper_id}/notes", response_model=List[NoteResponse])
async def get_paper_notes(
    paper_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取论文的所有笔记
    """
    notes = paper_service.get_notes_by_paper(db, paper_id, current_user.id)
    return notes

@router.post("/{paper_id}/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_paper_note(
    paper_id: str,
    data: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    为论文创建笔记
    """
    note = paper_service.create_note(
        db=db,
        paper_id=paper_id,
        user_id=current_user.id,
        content=data.content,
        page_number=data.page_number,
        position_data=data.position_data
    )
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="论文未找到或无权限添加笔记"
        )
    
    return note

@router.patch("/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    data: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新笔记
    """
    updated_note = paper_service.update_note(
        db=db,
        note_id=note_id,
        user_id=current_user.id,
        update_data=data.dict(exclude_unset=True)
    )
    
    if not updated_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="笔记未找到或无权限修改"
        )
    
    return updated_note

@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除笔记
    """
    result = paper_service.delete_note(db, note_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="笔记未找到或无权限删除"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# 论文分析API
@router.get("/{paper_id}/analysis")
async def get_paper_analysis(
    paper_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取论文分析结果
    """
    try:
        paper = db.query(Paper).filter(Paper.id == paper_id, Paper.owner_id == current_user.id).first()
        if not paper:
            raise HTTPException(status_code=404, detail="论文不存在")
        
        # 如果分析未开始
        if not paper.analysis_status:
            return {
                "status": "not_started",
                "message": "论文尚未开始分析"
            }
        
        # 如果分析正在进行中
        if paper.analysis_status == "processing":
            return {
                "status": "processing",
                "progress": paper.analysis_progress,
                "message": f"论文分析进行中，当前进度: {paper.analysis_progress}%"
            }
        
        # 如果分析失败
        if paper.analysis_status == "failed":
            error_message = paper.analysis_error if hasattr(paper, 'analysis_error') and paper.analysis_error else "未知错误"
            return {
                "status": "failed",
                "message": f"论文分析失败: {error_message}"
            }
        
        # 到这里，分析状态应该是completed，即使某些字段缺失也继续处理
        # 构建分析数据结构
        analysis_data = {}
        
        # 处理methodology字段，确保它有正确的结构
        if not hasattr(paper, 'methodology') or not paper.methodology:
            analysis_data["methodology"] = {
                "modelArchitecture": "未能提取方法论信息",
                "keyComponents": [],
                "algorithm": "未能提取算法信息",
                "innovations": []
            }
        else:
            analysis_data["methodology"] = paper.methodology
        
        # 处理experiment_data字段
        experiment_data = {}
        if hasattr(paper, 'experiments') and paper.experiments:
            experiment_data = paper.experiments
            
            # 检查是否是旧版本格式（mainResults字段）
            if "mainResults" in experiment_data:
                # 转换到新格式
                if "results_summary" not in experiment_data:
                    experiment_data["results_summary"] = experiment_data.get("mainResults", "")
                
                if "ablation_studies" not in experiment_data and "ablationAnalysis" in experiment_data:
                    experiment_data["ablation_studies"] = experiment_data.get("ablationAnalysis", "")
                
                # 添加新字段
                if "experimental_setup" not in experiment_data:
                    experiment_data["experimental_setup"] = "未提供实验设置信息"
                
                if "analysis" not in experiment_data:
                    experiment_data["analysis"] = "未提供实验分析信息"
            
            # 处理metrics字段，确保它是一个包含name和description的对象列表
            if "metrics" in experiment_data and isinstance(experiment_data["metrics"], list):
                formatted_metrics = []
                for metric in experiment_data["metrics"]:
                    if isinstance(metric, dict) and "name" in metric:
                        formatted_metrics.append(metric)
                    elif isinstance(metric, str):
                        # 如果是字符串，转换为对象
                        formatted_metrics.append({
                            "name": metric,
                            "description": "未提供描述"
                        })
                experiment_data["metrics"] = formatted_metrics
        else:
            # 如果没有experiment_data，创建默认结构
            experiment_data = {
                "datasets": [],
                "metrics": [],
                "baselines": [],
                "experimental_setup": "未提供实验设置信息",
                "results_summary": "未提供实验结果概要",
                "analysis": "未提供实验分析",
                "ablation_studies": ""
            }
        
        # 确保key_findings字段存在
        if not hasattr(paper, 'key_findings') or not paper.key_findings:
            analysis_data["key_findings"] = []
        else:
            analysis_data["key_findings"] = paper.key_findings
        
        # 确保future_work字段存在
        if not hasattr(paper, 'future_work') or not paper.future_work:
            analysis_data["future_work"] = []
        else:
            # 确保future_work是数组格式
            if isinstance(paper.future_work, list):
                analysis_data["future_work"] = paper.future_work
            elif isinstance(paper.future_work, str) and paper.future_work.strip():
                # 如果是非空字符串，将其转换为数组中的一个对象
                analysis_data["future_work"] = [{
                    "direction": "未来研究方向概述",
                    "description": paper.future_work,
                    "source": "paper"
                }]
            else:
                # 其他情况，设为空数组
                analysis_data["future_work"] = []
        
        # 确保code_implementation字段存在
        if not hasattr(paper, 'code_implementation') or not paper.code_implementation:
            analysis_data["code_implementation"] = "未能生成代码实现"
        else:
            analysis_data["code_implementation"] = paper.code_implementation
        
        # 确保weaknesses字段存在
        if not hasattr(paper, 'weaknesses') or not paper.weaknesses:
            analysis_data["weaknesses"] = "未能提取论文局限性"
        else:
            analysis_data["weaknesses"] = paper.weaknesses
        
        # 设置references为空列表，不返回参考文献
        analysis_data["references"] = []
        
        # 更新experiment_data
        analysis_data["experiment_data"] = experiment_data
        
        # 如果有sections字段，也加入
        if hasattr(paper, 'sections') and paper.sections:
            analysis_data["sections"] = paper.sections
        else:
            analysis_data["sections"] = []
        
        # 返回处理后的分析数据
        return {
            "status": "completed",
            "data": analysis_data
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"获取论文分析异常: {str(e)}")
        print(f"异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取论文分析失败: {str(e)}")

@router.post("/{paper_id}/analyze", response_model=PaperAnalysisResponse)
async def analyze_paper(
    paper_id: str,
    analysis_request: Optional[PaperAnalysisRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    分析论文内容并提取关键信息，只提取核心部分（题目、摘要、相关工作和方法论）
    """
    import traceback
    print(f"收到论文分析请求: paper_id={paper_id}, user_id={current_user.id}")
    
    try:
        # 调用论文分析服务
        from src.services import paper_analyzer
        print(f"开始调用paper_analyzer.analyze_paper: paper_id={paper_id}")
        
        # 设置更多参数，生成更完整的内容
        # 使用默认生成中文内容
        os.environ["GENERATE_CHINESE_CONTENT"] = "true"
        os.environ["GENERATE_DETAILED_CONTENT"] = "true"
        
        # 获取分析请求参数 - 默认值全部调整为只分析核心部分
        extract_core_content = True  # 总是提取核心内容
        analyze_experiments = False  # 默认不分析实验部分
        analyze_references = False   # 默认不分析参考文献
        
        # 如果有请求参数，处理这些参数
        if analysis_request:
            print(f"收到分析请求参数: {analysis_request.dict()}")
            # 核心内容提取始终为True
            extract_core_content = True
            
            # 检查是否需要分析实验，但默认为False
            if hasattr(analysis_request, 'experiments') and analysis_request.experiments is not None:
                analyze_experiments = analysis_request.experiments
            
            # 检查是否需要分析参考文献，但默认为False
            if hasattr(analysis_request, 'references') and analysis_request.references is not None:
                analyze_references = analysis_request.references
        
        print(f"分析参数: extract_core_content={extract_core_content}, analyze_experiments={analyze_experiments}, analyze_references={analyze_references}")
        
        # 调用分析函数，传递参数
        paper = await paper_analyzer.analyze_paper(
            db, 
            paper_id, 
            current_user.id,
            extract_core_content=extract_core_content,
            analyze_experiments=analyze_experiments,
            analyze_references=analyze_references
        )
        print(f"paper_analyzer.analyze_paper调用成功: paper_id={paper_id}")
        
        print(f"开始构建分析响应对象: paper_id={paper_id}")
        
        # 处理experiment_data中的metrics字段，确保格式一致
        experiment_data = paper.experiment_data if hasattr(paper, 'experiment_data') and paper.experiment_data else {}
        if isinstance(experiment_data, dict) and "metrics" in experiment_data:
            metrics = experiment_data["metrics"]
            if isinstance(metrics, list) and metrics and isinstance(metrics[0], str):
                # 如果metrics是字符串列表，转换为对象列表
                experiment_data["metrics"] = [{"name": m, "description": "未提供详细描述"} for m in metrics]
        
        # 构建符合PaperAnalysisResponse的响应对象
        response_data = {
            "id": paper.id,
            "title": paper.title,
            "abstract": paper.abstract if hasattr(paper, 'abstract') else None,
            "authors": paper.authors if hasattr(paper, 'authors') and paper.authors else [],
            "publication_date": paper.publication_date if hasattr(paper, 'publication_date') else None,
            "journal": paper.journal if hasattr(paper, 'journal') else None,
            "conference": paper.conference if hasattr(paper, 'conference') else None,
            "doi": paper.doi if hasattr(paper, 'doi') else None,
            "url": paper.url if hasattr(paper, 'url') else None,
            "tags": [tag.name for tag in paper.tags] if hasattr(paper, 'tags') and paper.tags else [],
            "notes": "",  # 默认为空字符串
            "owner_id": paper.owner_id,
            "created_at": paper.created_at if hasattr(paper, 'created_at') else None,
            "updated_at": paper.updated_at if hasattr(paper, 'updated_at') else None,
            "file_path": paper.file_path if hasattr(paper, 'file_path') else None,
            "source": "manual" if not hasattr(paper, 'source') else paper.source,
            "has_content": bool(paper.content) if hasattr(paper, 'content') else False,
            "has_file": bool(paper.file_path) if hasattr(paper, 'file_path') else False,
            "page_count": None,
            "metadata": paper.paper_metadata if hasattr(paper, 'paper_metadata') and paper.paper_metadata else {},
            "is_favorite": paper.is_favorite if hasattr(paper, 'is_favorite') else False,
            "folder_id": paper.folder_id if hasattr(paper, 'folder_id') else None,
            "folder_name": paper.folder.name if hasattr(paper, 'folder') and paper.folder else None,
            "categories": [],
            "analysis_status": paper.analysis_status if hasattr(paper, 'analysis_status') else None,
            "analysis_progress": paper.analysis_progress if hasattr(paper, 'analysis_progress') else 0,
            # 分析结果字段
            "sections": paper.sections if hasattr(paper, 'sections') and paper.sections else [],
            "methodology": paper.methodology if hasattr(paper, 'methodology') and paper.methodology else {
                "modelArchitecture": "未能提取方法论信息",
                "keyComponents": ["未能提取关键组件信息"],
                "algorithms": "未能提取算法流程",
                "innovations": ["未能提取创新点"]
            },
            # 使用已处理的experiment_data，但不在前端显示
            "experiments": experiment_data,
            # 不再显示参考文献
            "references": [],
            "code_implementation": paper.code_implementation if hasattr(paper, 'code_implementation') and paper.code_implementation else "",
            "key_findings": paper.key_findings if hasattr(paper, 'key_findings') and paper.key_findings else [],
            "weaknesses": paper.weaknesses if hasattr(paper, 'weaknesses') and paper.weaknesses else [],
            "future_work": [],  # 默认为空数组
            "analysis_date": paper.analysis_date if hasattr(paper, 'analysis_date') else None
        }
        
        # 确保methodology有正确的结构
        if "methodology" in response_data and response_data["methodology"]:
            if not isinstance(response_data["methodology"], dict):
                response_data["methodology"] = {
                    "modelArchitecture": "解析方法论数据时出错",
                    "keyComponents": [],
                    "algorithm": "解析方法论数据时出错",
                    "innovations": []
                }
            else:
                # 确保所有必要字段都存在
                if "modelArchitecture" not in response_data["methodology"] or not response_data["methodology"]["modelArchitecture"]:
                    response_data["methodology"]["modelArchitecture"] = "未提取到模型架构信息"
                if "keyComponents" not in response_data["methodology"] or not response_data["methodology"]["keyComponents"]:
                    response_data["methodology"]["keyComponents"] = []
                if "algorithm" not in response_data["methodology"] or not response_data["methodology"]["algorithm"]:
                    response_data["methodology"]["algorithm"] = "未提取到算法流程"
                if "innovations" not in response_data["methodology"] or not response_data["methodology"]["innovations"]:
                    response_data["methodology"]["innovations"] = []
        
        # 处理future_work字段
        if hasattr(paper, 'future_work') and paper.future_work:
            if isinstance(paper.future_work, list):
                response_data["future_work"] = paper.future_work
            elif isinstance(paper.future_work, str) and paper.future_work.strip():
                # 将字符串转换为数组中的一个对象
                response_data["future_work"] = [{
                    "direction": "未来研究方向概述",
                    "description": paper.future_work,
                    "source": "paper"
                }]
        
        print(f"构建分析响应对象成功: paper_id={paper_id}")
        return response_data
    except ValueError as e:
        error_msg = f"论文分析参数错误: {str(e)}"
        print(f"{error_msg}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        error_msg = f"论文分析失败: {str(e)}"
        print(f"{error_msg}\n{traceback.format_exc()}")
        # 尝试获取论文并更新其状态
        try:
            paper = db.query(Paper).filter(Paper.id == paper_id, Paper.owner_id == current_user.id).first()
            if paper:
                paper.analysis_status = "failed"  # 使用字符串而不是枚举，以防止潜在的导入问题
                db.commit()
                print(f"在路由处理器中将分析状态更新为failed: paper_id={paper_id}")
        except Exception as status_error:
            print(f"在路由处理器中更新分析状态失败: paper_id={paper_id}, error={str(status_error)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

# 外部论文搜索API
@router.post("/search/external", response_model=ExternalSearchResponse)
async def search_external_papers(
    search_request: ExternalSearchRequest
):
    """
    在外部学术数据库中搜索论文
    """
    try:
        from src.services.paper_search import paper_search_service
        
        # 记录传入的搜索参数
        print(f"搜索请求参数（完整）: {search_request.dict()}")
        
        # 验证搜索查询是否为空
        if not search_request.query.strip() and not search_request.domain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="搜索关键词不能为空，请提供有效的查询词或领域"
            )
        
        # 确保sources是有效的枚举值
        valid_sources = []
        if not search_request.sources or len(search_request.sources) == 0:
            # 如果没有指定源，使用默认值（已移除CiteSeerX）
            print("未指定搜索源，使用默认值 [arxiv, semanticscholar, core, openalex]")
            valid_sources = [
                SearchSourceEnum.ARXIV, 
                SearchSourceEnum.SEMANTICSCHOLAR,
                SearchSourceEnum.CORE,
                SearchSourceEnum.OPENALEX
            ]
        else:
            for source in search_request.sources:
                if isinstance(source, str):
                    try:
                        # 尝试将字符串转换为枚举值
                        valid_source = SearchSourceEnum(source.lower())
                        valid_sources.append(valid_source)
                    except ValueError:
                        print(f"忽略无效的搜索源: {source}")
                else:
                    valid_sources.append(source)
        
        if not valid_sources:
            # 默认使用四个主要数据库（已移除CiteSeerX）
            valid_sources = [
                SearchSourceEnum.ARXIV, 
                SearchSourceEnum.SEMANTICSCHOLAR,
                SearchSourceEnum.CORE,
                SearchSourceEnum.OPENALEX
            ]
        
        print(f"使用有效搜索源: {valid_sources}")
        
        # 设置合理的默认值
        limit = min(search_request.limit or 10, 50)  # 限制最大结果数为50
        offset = max(search_request.offset or 0, 0)  # 确保偏移量非负
        
        # 检查年份范围是否合理
        year_from = search_request.year_from
        year_to = search_request.year_to
        current_year = datetime.now().year
        
        if year_from and year_from > current_year:
            print(f"起始年份 {year_from} 超过当前年份，重置为None")
            year_from = None
        
        if year_to and year_to > current_year:
            print(f"结束年份 {year_to} 超过当前年份，重置为当前年份")
            year_to = current_year
            
        if year_from and year_to and year_from > year_to:
            print(f"起始年份 {year_from} 大于结束年份 {year_to}，交换两个值")
            year_from, year_to = year_to, year_from
        
        # 执行搜索
        results = await paper_search_service.search_papers(
            query=search_request.query,
            sources=valid_sources,
            limit=limit,
            offset=offset,
            year_from=year_from,
            year_to=year_to,
            full_text=search_request.full_text,
            domain=search_request.domain,
            venues=search_request.venues
        )
        
        return results
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        import traceback
        error_detail = f"外部论文搜索失败: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )

# 文件夹管理
@router.post("/folders", response_model=FolderResponse)
async def create_folder(
    folder_data: FolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新文件夹
    """
    try:
        # 检查父文件夹是否存在
        if folder_data.parent_id:
            parent_folder = db.query(Folder).filter(
                Folder.id == folder_data.parent_id,
                Folder.owner_id == current_user.id
            ).first()
            
            if not parent_folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="父文件夹不存在"
                )
        
        # 创建文件夹
        new_folder = Folder(
            id=str(uuid.uuid4()),
            name=folder_data.name,
            parent_id=folder_data.parent_id,
            owner_id=current_user.id
        )
        
        db.add(new_folder)
        db.commit()
        db.refresh(new_folder)
        
        # 计算论文数量
        paper_count = db.query(Paper).filter(Paper.folder_id == new_folder.id).count()
        
        # 构建响应
        response = {
            **new_folder.__dict__,
            "paper_count": paper_count,
            "children": []
        }
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建文件夹失败: {str(e)}"
        )

@router.get("/folders", response_model=List[FolderResponse])
async def list_folders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的文件夹列表
    """
    try:
        # 获取所有顶级文件夹
        top_folders = db.query(Folder).filter(
            Folder.owner_id == current_user.id,
            Folder.parent_id == None
        ).all()
        
        # 递归构建文件夹树
        result = []
        for folder in top_folders:
            folder_dict = folder.__dict__.copy()
            
            # 计算论文数量
            paper_count = db.query(Paper).filter(Paper.folder_id == folder.id).count()
            folder_dict["paper_count"] = paper_count
            
            # 获取子文件夹
            children = get_folder_children(db, folder.id, current_user.id)
            folder_dict["children"] = children
            
            result.append(folder_dict)
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文件夹列表失败: {str(e)}"
        )

def get_folder_children(db: Session, parent_id: str, user_id: str) -> List[Dict[str, Any]]:
    """递归获取文件夹的子文件夹"""
    children = db.query(Folder).filter(
        Folder.parent_id == parent_id,
        Folder.owner_id == user_id
    ).all()
    
    result = []
    for child in children:
        child_dict = child.__dict__.copy()
        
        # 计算论文数量
        paper_count = db.query(Paper).filter(Paper.folder_id == child.id).count()
        child_dict["paper_count"] = paper_count
        
        # 递归获取子文件夹
        grandchildren = get_folder_children(db, child.id, user_id)
        child_dict["children"] = grandchildren
        
        result.append(child_dict)
    
    return result

@router.patch("/folders/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: str,
    folder_data: FolderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新文件夹信息
    """
    try:
        # 查找文件夹
        folder = db.query(Folder).filter(
            Folder.id == folder_id,
            Folder.owner_id == current_user.id
        ).first()
        
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件夹不存在"
            )
        
        # 检查父文件夹是否存在，并避免循环引用
        if folder_data.parent_id:
            if folder_data.parent_id == folder_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="不能将文件夹设为自身的父文件夹"
                )
            
            parent_folder = db.query(Folder).filter(
                Folder.id == folder_data.parent_id,
                Folder.owner_id == current_user.id
            ).first()
            
            if not parent_folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="父文件夹不存在"
                )
            
            # 检查循环引用
            current_parent = parent_folder
            while current_parent.parent_id:
                if current_parent.parent_id == folder_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="不能创建循环引用的文件夹结构"
                    )
                current_parent = db.query(Folder).filter(Folder.id == current_parent.parent_id).first()
        
        # 更新文件夹信息
        if folder_data.name is not None:
            folder.name = folder_data.name
        
        if folder_data.parent_id is not None:
            folder.parent_id = folder_data.parent_id
        
        folder.updated_at = datetime.now()
        
        db.commit()
        db.refresh(folder)
        
        # 计算论文数量
        paper_count = db.query(Paper).filter(Paper.folder_id == folder.id).count()
        
        # 获取子文件夹
        children = get_folder_children(db, folder.id, current_user.id)
        
        # 构建响应
        response = {
            **folder.__dict__,
            "paper_count": paper_count,
            "children": children
        }
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新文件夹失败: {str(e)}"
        )

@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: str,
    move_papers: bool = Query(False, description="是否将文件夹中的论文移至根目录"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除文件夹
    """
    try:
        # 查找文件夹
        folder = db.query(Folder).filter(
            Folder.id == folder_id,
            Folder.owner_id == current_user.id
        ).first()
        
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件夹不存在"
            )
        
        # 处理文件夹中的论文
        if move_papers:
            # 将论文移至根目录
            papers = db.query(Paper).filter(Paper.folder_id == folder_id).all()
            for paper in papers:
                paper.folder_id = None
            db.commit()
        
        # 删除文件夹（cascade 会自动删除子文件夹）
        db.delete(folder)
        db.commit()
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文件夹失败: {str(e)}"
        )

# 分类管理接口
@router.post("/categories", response_model=CategoryResponse)
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新分类
    """
    try:
        # 检查父分类是否存在
        if category_data.parent_id:
            parent_category = db.query(Category).filter(
                Category.id == category_data.parent_id,
                Category.owner_id == current_user.id
            ).first()
            
            if not parent_category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="父分类不存在"
                )
        
        # 创建分类
        new_category = Category(
            id=str(uuid.uuid4()),
            name=category_data.name,
            description=category_data.description,
            parent_id=category_data.parent_id,
            owner_id=current_user.id
        )
        
        db.add(new_category)
        db.commit()
        db.refresh(new_category)
        
        # 构建响应
        response = {
            **new_category.__dict__,
            "paper_count": 0,
            "children": []
        }
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建分类失败: {str(e)}"
        )

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的分类列表
    """
    try:
        # 获取所有顶级分类
        top_categories = db.query(Category).filter(
            Category.owner_id == current_user.id,
            Category.parent_id == None
        ).all()
        
        # 递归构建分类树
        result = []
        for category in top_categories:
            category_dict = category.__dict__.copy()
            
            # 计算论文数量
            paper_count = db.query(paper_categories).filter(
                paper_categories.c.category_id == category.id
            ).count()
            category_dict["paper_count"] = paper_count
            
            # 获取子分类
            children = get_category_children(db, category.id, current_user.id)
            category_dict["children"] = children
            
            result.append(category_dict)
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取分类列表失败: {str(e)}"
        )

def get_category_children(db: Session, parent_id: str, user_id: str) -> List[Dict[str, Any]]:
    """递归获取分类的子分类"""
    children = db.query(Category).filter(
        Category.parent_id == parent_id,
        Category.owner_id == user_id
    ).all()
    
    result = []
    for child in children:
        child_dict = child.__dict__.copy()
        
        # 计算论文数量
        paper_count = db.query(paper_categories).filter(
            paper_categories.c.category_id == child.id
        ).count()
        child_dict["paper_count"] = paper_count
        
        # 递归获取子分类
        grandchildren = get_category_children(db, child.id, user_id)
        child_dict["children"] = grandchildren
        
        result.append(child_dict)
    
    return result 