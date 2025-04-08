from datetime import datetime, timedelta
from typing import Any, Optional, Union, Dict
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import uuid

from src.core.config import settings
from src.db.base import get_db
from src.models.user import User
from src.schemas.user import UserCreate, TokenPayload

# 密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 密码Bearer，设置token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)

def authenticate_user(
    db: Session, 
    username_or_email: str, 
    password: str,
    is_email: bool = False
) -> Optional[User]:
    """认证用户"""
    if is_email:
        # 通过邮箱查找
        user = db.query(User).filter(User.email == username_or_email).first()
    else:
        # 尝试通过用户名或邮箱查找
        user = db.query(User).filter(
            (User.name == username_or_email) | (User.email == username_or_email)
        ).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    # 确保用户的profile字段正确初始化
    if user.profile is None:
        user.profile = {}
        
    # 确保关键字段存在
    profile_defaults = {
        "institution": "",
        "research_interests": [],
        "website": "",
        "location": "",
        "bio": "",
        "social_links": {}
    }
    
    # 添加缺失的默认字段
    needs_update = False
    for key, default_value in profile_defaults.items():
        if key not in user.profile:
            user.profile[key] = default_value
            needs_update = True
    
    # 如果有字段更新，保存用户
    if needs_update:
        db.commit()
        db.refresh(user)
    
    return user

def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的身份认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
        
        token_data = TokenPayload(sub=user_id)
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == token_data.sub).first()
    
    if user is None:
        raise credentials_exception
    
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用"
        )
    return current_user

def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """获取当前超级用户"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限"
        )
    return current_user

def register_new_user(
    db: Session, 
    user_data: UserCreate
) -> Optional[User]:
    """注册新用户"""
    # 检查邮箱是否已存在
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        return None
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    
    # 生成邮箱验证令牌
    verification_token = create_email_verification_token(str(uuid.uuid4()))
    
    # 初始化profile信息
    profile = user_data.profile or {}
    
    # 确保关键字段存在
    profile_defaults = {
        "institution": "",
        "research_interests": [],
        "website": "",
        "location": "",
        "bio": "",
        "social_links": {}
    }
    
    # 添加缺失的默认字段
    for key, default_value in profile_defaults.items():
        if key not in profile:
            profile[key] = default_value
    
    user = User(
        id=str(uuid.uuid4()),
        email=user_data.email,
        name=user_data.name,
        hashed_password=hashed_password,
        profile=profile,
        verification_token=verification_token,
        email_verified=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user

def create_password_reset_token(user_id: str) -> str:
    """
    创建密码重置令牌
    
    参数:
        user_id: 用户ID
        
    返回:
        生成的密码重置令牌
    """
    expires = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    to_encode = {
        "exp": expires.timestamp(),
        "nbf": datetime.utcnow().timestamp(),
        "sub": user_id,
        "type": "password_reset"
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password_reset_token(token: str) -> Optional[str]:
    """
    验证密码重置令牌
    
    参数:
        token: 密码重置令牌
        
    返回:
        如果令牌有效，返回用户ID，否则返回None
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # 检查令牌类型
        if payload.get("type") != "password_reset":
            return None
            
        user_id: str = payload.get("sub")
        return user_id
    except JWTError:
        return None

def reset_user_password(db: Session, user_id: str, new_password: str) -> bool:
    """
    重置用户密码
    
    参数:
        db: 数据库会话
        user_id: 用户ID
        new_password: 新密码
        
    返回:
        重置是否成功
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
        
    # 哈希新密码
    hashed_password = get_password_hash(new_password)
    user.hashed_password = hashed_password
    
    # 清除密码重置令牌
    user.password_reset_token = None
    user.password_reset_expires = None
    
    try:
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False

def create_email_verification_token(user_id: str) -> str:
    """
    创建邮箱验证令牌
    
    参数:
        user_id: 用户ID
        
    返回:
        生成的邮箱验证令牌
    """
    expires = datetime.utcnow() + timedelta(hours=24)
    to_encode = {
        "exp": expires.timestamp(),
        "nbf": datetime.utcnow().timestamp(),
        "sub": user_id,
        "type": "email_verification"
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_email_token(token: str) -> Optional[str]:
    """
    验证邮箱验证令牌
    
    参数:
        token: 邮箱验证令牌
        
    返回:
        如果令牌有效，返回用户ID，否则返回None
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # 检查令牌类型
        if payload.get("type") != "email_verification":
            return None
            
        user_id: str = payload.get("sub")
        return user_id
    except JWTError:
        return None

def verify_user_email(db: Session, user_id: str) -> bool:
    """
    验证用户邮箱
    
    参数:
        db: 数据库会话
        user_id: 用户ID
        
    返回:
        验证是否成功
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    user.email_verified = True
    user.verification_token = None
    
    try:
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False 