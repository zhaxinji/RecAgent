import asyncio
from fastapi import BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session
from log import logger
from api.models.paper import Paper
from api.schemas.paper import Schema
from api.services.paper import paper_service
from api.utils.auth import get_current_user
from api.utils.database import get_db
from datetime import datetime

@router.post("/{paper_id}/analyze", response_model=Schema.GenericResponseModel)
async def analyze_paper_endpoint(
    paper_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    """
    分析论文API端点，支持异步处理和超时控制
    """
    try:
        # 检查是否已经在分析中
        paper = db.query(Paper).filter(Paper.id == paper_id, Paper.owner_id == current_user.id).first()
        if not paper:
            return {"status": "error", "message": "论文不存在或无权访问"}
            
        if paper.analysis_status == "processing":
            return {"status": "info", "message": "该论文正在分析中，请稍后查看结果"}
            
        # 设置分析超时保护，最长时间30分钟
        max_analysis_time = 30 * 60  # 30分钟
        
        # 创建异步分析任务
        async def analyze_with_timeout():
            # 创建一个独立的任务来执行分析
            try:
                analysis_task = asyncio.create_task(
                    paper_service.analyze_paper(db, paper_id, current_user.id)
                )
                
                # 设置超时
                try:
                    await asyncio.wait_for(analysis_task, timeout=max_analysis_time)
                    logger.info(f"论文 {paper_id} 分析完成")
                except asyncio.TimeoutError:
                    # 超时处理
                    logger.error(f"论文 {paper_id} 分析超时")
                    paper = db.query(Paper).filter(Paper.id == paper_id).first()
                    if paper:
                        paper.analysis_status = "failed"
                        paper.analysis_error = "分析超时，请尝试缩减论文内容或分段分析"
                        db.commit()
            except Exception as e:
                # 捕获其他异常
                logger.error(f"论文 {paper_id} 分析出错: {str(e)}")
                paper = db.query(Paper).filter(Paper.id == paper_id).first()
                if paper:
                    paper.analysis_status = "failed"
                    paper.analysis_error = f"分析出错: {str(e)[:200]}"
                    db.commit()
        
        # 添加到后台任务
        background_tasks.add_task(analyze_with_timeout)
        
        return {"status": "success", "message": "论文分析已开始，请稍后查看结果"}
    except Exception as e:
        logger.error(f"启动论文分析出错: {str(e)}")
        return {"status": "error", "message": f"启动论文分析出错: {str(e)}"}

# 添加新端点，用于将分析过的论文添加到文献库
@router.post("/{paper_id}/add-to-library", response_model=PaperResponse)
async def add_to_library(
    paper_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    将已分析的上传论文添加到用户的文献库
    """
    try:
        # 查找论文
        paper = paper_service.get_paper_by_id(db, paper_id, current_user.id)
        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到指定论文"
            )
            
        # 修改论文字段，将source从'upload'修改为'library'以标记为已添加到文献库
        updated_data = {
            "source": "library",
            "updated_at": datetime.now()
        }
        
        # 更新论文
        updated_paper = paper_service.update_paper(
            db=db, 
            paper_id=paper_id, 
            user_id=current_user.id, 
            update_data=updated_data
        )
        
        if not updated_paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="更新论文失败"
            )
        
        # 构建响应数据
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
            "source": updated_paper.source if hasattr(updated_paper, 'source') and updated_paper.source else "library",
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"添加到文献库失败: {str(e)}"
        ) 