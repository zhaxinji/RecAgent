from fastapi import APIRouter, Depends, HTTPException, status, Body, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional
from datetime import timedelta, datetime

from src.core.deps import get_db
from src.core.config import settings
from src.services.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_active_user,
    register_new_user,
    create_password_reset_token,
    verify_password_reset_token,
    reset_user_password,
    create_email_verification_token,
    verify_email_token,
    verify_user_email
)
from src.models.user import User
from src.schemas.user import Token, UserCreate, UserResponse, EmailVerificationRequest
from src.services.email import send_reset_password_email, send_verification_email, send_welcome_email

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取OAuth2访问令牌
    
    使用用户名和密码获取访问令牌
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.id}, expires_delta=access_token_expires)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/login/email", response_model=Token)
async def login_with_email(
    email: str = Body(..., embed=True),
    password: str = Body(..., embed=True),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    使用邮箱和密码登录
    
    使用邮箱和密码获取访问令牌
    """
    user = authenticate_user(db, email, password, is_email=True)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.id}, expires_delta=access_token_expires)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    background_tasks: BackgroundTasks,
    user_data: UserCreate,
    db: Session = Depends(get_db)
) -> User:
    """
    注册新用户
    
    注册新用户并返回用户信息
    """
    user = register_new_user(db, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱或用户名已被注册"
        )
    
    # 发送验证邮件
    verification_token = user.verification_token
    background_tasks.add_task(
        send_verification_email,
        email=user.email,
        token=verification_token,
        username=user.name
    )
    
    return user

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    获取当前用户信息
    
    获取当前已登录用户的信息
    """
    return current_user

@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """
    刷新访问令牌
    
    使用当前有效令牌获取新的访问令牌
    """
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": current_user.id}, expires_delta=access_token_expires)
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(
    background_tasks: BackgroundTasks,
    email: str = Body(..., embed=True),
    db: Session = Depends(get_db)
) -> None:
    """
    请求密码重置
    
    发送密码重置邮件到用户邮箱
    """
    user = db.query(User).filter(User.email == email).first()
    if user:
        reset_token = create_password_reset_token(user.id)
        # 保存token到用户记录
        user.password_reset_token = reset_token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
        db.commit()
        
        background_tasks.add_task(
            send_reset_password_email,
            email=user.email,
            token=reset_token,
            username=user.name
        )
    # 即使用户不存在也返回成功，防止用户枚举
    return None

@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    token: str = Body(...),
    new_password: str = Body(...),
    db: Session = Depends(get_db)
) -> None:
    """
    重置密码
    
    使用令牌重置用户密码
    """
    user_id = verify_password_reset_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的重置令牌"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 检查token是否与用户记录中的一致，并检查是否过期
    if (user.password_reset_token != token or 
        user.password_reset_expires is None or 
        user.password_reset_expires < datetime.utcnow()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重置令牌已过期或无效"
        )
    
    if not reset_user_password(db, user_id, new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码重置失败"
        )
    
    return None

@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
async def verify_email(
    background_tasks: BackgroundTasks,
    verification_data: EmailVerificationRequest,
    db: Session = Depends(get_db)
) -> None:
    """
    验证用户邮箱
    
    使用令牌验证用户邮箱
    """
    user_id = verify_email_token(verification_data.token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的验证令牌"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    if user.email_verified:
        # 邮箱已验证，直接返回成功
        return None
    
    if user.verification_token != verification_data.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证令牌已过期或无效"
        )
    
    if not verify_user_email(db, user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱验证失败"
        )
    
    # 发送欢迎邮件
    background_tasks.add_task(
        send_welcome_email,
        email=user.email,
        username=user.name
    )
    
    return None

@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
async def resend_verification(
    background_tasks: BackgroundTasks,
    email: str = Body(..., embed=True),
    db: Session = Depends(get_db)
) -> None:
    """
    重新发送验证邮件
    
    向用户邮箱重新发送验证邮件
    """
    user = db.query(User).filter(User.email == email).first()
    if user and not user.email_verified:
        # 生成新的验证令牌
        verification_token = create_email_verification_token(user.id)
        user.verification_token = verification_token
        db.commit()
        
        # 发送验证邮件
        background_tasks.add_task(
            send_verification_email,
            email=user.email,
            token=verification_token,
            username=user.name
        )
    
    # 即使用户不存在或已验证也返回成功，防止用户枚举
    return None 