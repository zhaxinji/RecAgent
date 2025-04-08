from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Body
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import json

from src.core.deps import get_current_user, get_db
from src.models.user import User
from src.schemas.user import UserProfileResponse, UserProfileUpdate
from src.services.auth import verify_password
from src.services.storage import upload_file_to_storage

router = APIRouter()

@router.get("/me/profile", response_model=UserProfileResponse)
def get_user_profile(
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的详细个人资料"""
    # 获取用户的profile数据，如果不存在则创建空字典
    profile = getattr(current_user, 'profile', {}) or {}
    
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar=current_user.avatar,
        institution=profile.get("institution", ""),
        research_interests=profile.get("research_interests", []),
        website=profile.get("website", ""),
        location=profile.get("location", ""),
        bio=profile.get("bio", ""),
        social_links=profile.get("social_links", {}),
        is_active=current_user.is_active,
        email_verified=current_user.email_verified,
        created_at=current_user.created_at,
        projects_count=len(current_user.writing_projects) if current_user.writing_projects else 0,
        papers_count=len(current_user.papers) if current_user.papers else 0,
        experiments_count=len(current_user.experiments) if current_user.experiments else 0
    )

@router.put("/me/profile", response_model=UserProfileResponse)
async def update_user_profile(
    user_data: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新当前用户的个人资料"""
    # 解析用户数据
    user_update = None
    if user_data:
        try:
            user_update_dict = json.loads(user_data)
            user_update = UserProfileUpdate(**user_update_dict)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的JSON数据格式"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"数据验证错误: {str(e)}"
            )
    
    # 处理头像上传
    avatar_url = None
    if avatar:
        try:
            # 确保文件是图片
            content_type = avatar.content_type
            if not content_type.startswith("image/"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="文件必须是图片格式"
                )
            
            # 上传文件到存储服务
            avatar_url = await upload_file_to_storage(
                file=avatar,
                folder=f"avatars/{current_user.id}",
                filename_override=f"avatar_{current_user.id}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"头像上传失败: {str(e)}"
            )
    
    # 更新用户基本信息
    if user_update:
        # 获取基本字段和扩展字段
        basic_fields = {'name', 'avatar'}
        extended_fields = {'institution', 'research_interests', 'website', 'location', 'bio', 'social_links'}
        
        # 更新基本字段
        for field in basic_fields:
            value = getattr(user_update, field, None)
            if value is not None:
                setattr(current_user, field, value)
        
        # 更新扩展字段（存储在profile JSON字段中）
        profile = getattr(current_user, 'profile', {}) or {}
        for field in extended_fields:
            value = getattr(user_update, field, None)
            if value is not None:
                profile[field] = value
        
        # 保存更新后的profile
        current_user.profile = profile
    
    # 如果有新头像，更新头像URL
    if avatar_url:
        current_user.avatar = avatar_url
    
    db.commit()
    db.refresh(current_user)
    
    # 返回更新后的用户资料
    profile = current_user.profile or {}
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar=current_user.avatar,
        institution=profile.get("institution", ""),
        research_interests=profile.get("research_interests", []),
        website=profile.get("website", ""),
        location=profile.get("location", ""),
        bio=profile.get("bio", ""),
        social_links=profile.get("social_links", {}),
        is_active=current_user.is_active,
        email_verified=current_user.email_verified,
        created_at=current_user.created_at,
        projects_count=len(current_user.writing_projects) if current_user.writing_projects else 0,
        papers_count=len(current_user.papers) if current_user.papers else 0,
        experiments_count=len(current_user.experiments) if current_user.experiments else 0
    )

@router.get("/me/activity")
def get_user_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户最近活动"""
    # 获取用户最近的项目活动
    recent_projects = []
    if current_user.writing_projects:
        recent_projects = sorted(
            current_user.writing_projects, 
            key=lambda x: x.updated_at, 
            reverse=True
        )[:5]
    
    # 获取用户最近的论文活动
    recent_papers = []
    if current_user.papers:
        recent_papers = sorted(
            current_user.papers,
            key=lambda x: x.updated_at,
            reverse=True
        )[:5]
    
    # 获取用户最近的实验活动
    recent_experiments = []
    if current_user.experiments:
        recent_experiments = sorted(
            current_user.experiments,
            key=lambda x: x.updated_at,
            reverse=True
        )[:5]
    
    # 构建活动响应
    activities = []
    
    # 项目活动
    for project in recent_projects:
        activities.append({
            "id": project.id,
            "type": "project",
            "title": project.title,
            "timestamp": project.updated_at,
            "action": "updated" if project.created_at != project.updated_at else "created"
        })
    
    # 论文活动
    for paper in recent_papers:
        activities.append({
            "id": paper.id,
            "type": "paper",
            "title": paper.title,
            "timestamp": paper.updated_at,
            "action": "updated" if paper.created_at != paper.updated_at else "created"
        })
    
    # 实验活动
    for experiment in recent_experiments:
        activities.append({
            "id": experiment.id,
            "type": "experiment",
            "title": experiment.title,
            "timestamp": experiment.updated_at,
            "action": "updated" if experiment.created_at != experiment.updated_at else "created"
        })
    
    # 按时间排序
    activities = sorted(activities, key=lambda x: x["timestamp"], reverse=True)[:10]
    
    return {"activities": activities}

@router.put("/me/research-info", response_model=UserProfileResponse)
async def update_research_info(
    institution: str = Body(""),
    research_interests: List[str] = Body([]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新用户的研究信息（所属机构和研究方向）"""
    # 确保profile字段存在
    if not hasattr(current_user, 'profile') or current_user.profile is None:
        current_user.profile = {}
    
    # 更新研究信息
    current_user.profile['institution'] = institution
    current_user.profile['research_interests'] = research_interests
    
    # 保存更新
    db.commit()
    db.refresh(current_user)
    
    # 获取用户的完整profile
    profile = current_user.profile or {}
    
    # 返回更新后的用户资料
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar=current_user.avatar,
        institution=profile.get("institution", ""),
        research_interests=profile.get("research_interests", []),
        website=profile.get("website", ""),
        location=profile.get("location", ""),
        bio=profile.get("bio", ""),
        social_links=profile.get("social_links", {}),
        is_active=current_user.is_active,
        email_verified=current_user.email_verified,
        created_at=current_user.created_at,
        projects_count=len(current_user.writing_projects) if current_user.writing_projects else 0,
        papers_count=len(current_user.papers) if current_user.papers else 0,
        experiments_count=len(current_user.experiments) if current_user.experiments else 0
    )

@router.get("/me/debug")
def get_user_debug_info(
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的完整信息（包括原始数据），用于调试"""
    # 收集完整的用户信息
    user_info = {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "is_active": current_user.is_active,
        "email_verified": current_user.email_verified,
        "created_at": str(current_user.created_at),
        "avatar": current_user.avatar,
        "has_profile": hasattr(current_user, 'profile'),
        "profile_type": str(type(current_user.profile)) if hasattr(current_user, 'profile') else "None",
        "profile": current_user.profile if hasattr(current_user, 'profile') else None,
        "profile_keys": list(current_user.profile.keys()) if hasattr(current_user, 'profile') and current_user.profile else [],
        "writing_projects_count": len(current_user.writing_projects) if current_user.writing_projects else 0,
        "papers_count": len(current_user.papers) if current_user.papers else 0,
        "experiments_count": len(current_user.experiments) if current_user.experiments else 0
    }
    
    # 添加类的所有属性
    user_info["class_attributes"] = dir(current_user)
    
    return user_info 

@router.get("/me/info", response_model=Dict[str, Any])
def get_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户的详细信息"""
    print(f"获取用户信息: ID={current_user.id}, 名称={current_user.name}")
    
    # 获取用户的profile数据
    profile = current_user.profile or {}
    
    # 返回用户信息
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "avatar": current_user.avatar,
        "institution": profile.get("institution", ""),
        "research_interests": profile.get("research_interests", []),
        "join_date": current_user.created_at.strftime("%Y-%m-%d") if current_user.created_at else "",
        "is_active": current_user.is_active,
        "email_verified": current_user.email_verified,
        "bio": profile.get("bio", ""),
        "website": profile.get("website", ""),
        "location": profile.get("location", ""),
        "social_links": profile.get("social_links", {})
    }

@router.post("/me/initialize-profile", response_model=UserProfileResponse)
def initialize_user_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """初始化用户的profile数据"""
    print(f"初始化用户资料: ID={current_user.id}, 名称={current_user.name}")
    
    # 确保profile字段存在
    if not hasattr(current_user, 'profile') or current_user.profile is None:
        current_user.profile = {}
    
    # 初始化研究信息
    if "institution" not in current_user.profile:
        current_user.profile["institution"] = ""
    
    if "research_interests" not in current_user.profile:
        current_user.profile["research_interests"] = []
    
    # 确保其他字段也有初始值
    profile_defaults = {
        "website": "",
        "location": "",
        "bio": "",
        "social_links": {}
    }
    
    for key, default_value in profile_defaults.items():
        if key not in current_user.profile:
            current_user.profile[key] = default_value
    
    # 保存更新
    db.commit()
    db.refresh(current_user)
    
    # 返回更新后的用户资料
    return get_user_profile(current_user) 