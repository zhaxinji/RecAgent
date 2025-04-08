from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import shutil
import os
from pathlib import Path
import uuid

from src.core.deps import get_db, get_current_user
from src.services.auth import get_current_active_user, get_current_superuser
from src.services.user import (
    get_user_by_id, 
    get_users, 
    update_user, 
    delete_user,
    create_api_key,
    get_user_api_keys,
    delete_api_key,
    update_user_avatar,
    delete_user_avatar
)
from src.models.user import User
from src.schemas.user import UserResponse, UserUpdate, APIKeyCreate, APIKeyResponse, AISettingsResponse, AISettingsUpdate
from src.services import ai_settings as ai_settings_service
from src.core.config import settings

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户信息
    """
    return current_user

@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新当前用户信息
    """
    # 这里需要实现用户信息更新逻辑
    # 示例实现：
    for key, value in user_data.dict(exclude_unset=True).items():
        if hasattr(current_user, key):
            setattr(current_user, key, value)
    
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.get("/me/ai-settings", response_model=AISettingsResponse)
async def get_user_ai_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的AI设置
    """
    settings = ai_settings_service.get_or_create_user_ai_settings(db, current_user.id)
    return settings

@router.patch("/me/ai-settings", response_model=AISettingsResponse)
async def update_user_ai_settings(
    settings_data: AISettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新用户的AI设置
    """
    settings = ai_settings_service.create_or_update_ai_settings(
        db, 
        current_user.id, 
        settings_data.dict(exclude_unset=True)
    )
    return settings

@router.put("/me", response_model=UserResponse)
def update_user_info(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    更新当前用户信息
    
    - **email**: 新的电子邮箱（可选）
    - **name**: 新的用户名（可选）
    - **password**: 新的密码（可选）
    - **profile**: 新的个人资料（可选）
    """
    updated_user = update_user(db, current_user.id, user_in.dict(exclude_unset=True))
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return updated_user

@router.get("/{user_id}", response_model=UserResponse)
def read_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取指定用户信息
    
    - **user_id**: 要获取的用户ID
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.get("/", response_model=List[UserResponse])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    获取用户列表（仅超级用户）
    
    - **skip**: 跳过的记录数
    - **limit**: 返回的最大记录数
    """
    users = get_users(db, skip=skip, limit=limit)
    return users

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    删除用户（仅超级用户）
    
    - **user_id**: 要删除的用户ID
    """
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    success = delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return None

# API密钥相关路由
@router.post("/me/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
def create_user_api_key(
    api_key_in: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    创建API密钥
    
    - **name**: API密钥名称
    """
    api_key = create_api_key(db, current_user.id, api_key_in.name)
    return api_key

@router.get("/me/api-keys", response_model=List[APIKeyResponse])
def read_user_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户的所有API密钥"""
    return get_user_api_keys(db, current_user.id)

@router.delete("/me/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user_api_key(
    api_key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    删除API密钥
    
    - **api_key_id**: 要删除的API密钥ID
    """
    success = delete_api_key(db, api_key_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    return None

@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    上传用户头像
    
    - **file**: 头像图片文件
    """
    # 检查文件类型
    allowed_extensions = [".jpg", ".jpeg", ".png", ".gif"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的文件类型，只允许jpg、jpeg、png和gif"
        )
    
    # 创建保存文件的目录
    upload_dir = Path(settings.UPLOAD_DIR) / "avatars"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成唯一文件名
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = upload_dir / unique_filename
    
    # 保存文件
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传失败: {str(e)}"
        )
    finally:
        file.file.close()
    
    # 更新用户头像路径
    avatar_url = f"/uploads/avatars/{unique_filename}"
    updated_user = update_user_avatar(db, current_user.id, avatar_url)
    
    return updated_user

@router.delete("/me/avatar", response_model=UserResponse)
async def remove_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除用户头像"""
    updated_user = delete_user_avatar(db, current_user.id)
    return updated_user 