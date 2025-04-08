from typing import Optional, List, Any, Dict
from sqlalchemy.orm import Session
from datetime import datetime

from src.models.user import User, APIKey
from src.schemas.user import UserCreate, UserUpdate
from src.services.auth import get_password_hash, verify_password
import uuid
import secrets

def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """通过ID获取用户"""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """通过邮箱获取用户"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """通过用户名获取用户"""
    return db.query(User).filter(User.username == username).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """获取用户列表"""
    return db.query(User).offset(skip).limit(limit).all()

def create_user(
    db: Session, 
    email: str, 
    username: str, 
    password: str, 
    full_name: Optional[str] = None,
    is_superuser: bool = False
) -> User:
    """创建新用户"""
    hashed_password = get_password_hash(password)
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        username=username,
        full_name=full_name,
        hashed_password=hashed_password,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, username_or_email: str, password: str) -> Optional[User]:
    """验证用户凭据"""
    user = None
    if "@" in username_or_email:
        user = get_user_by_email(db, username_or_email)
    else:
        user = get_user_by_username(db, username_or_email)
    
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def update_user(db: Session, user_id: str, update_data: dict) -> Optional[User]:
    """更新用户信息"""
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    
    # 更新字段
    for key, value in update_data.items():
        # 如果是密码，需要进行哈希处理
        if key == "password":
            setattr(user, "hashed_password", get_password_hash(value))
        elif hasattr(user, key):
            setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user_id: str) -> bool:
    """删除用户"""
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    
    db.delete(user)
    db.commit()
    return True

# API密钥相关操作
def create_api_key(db: Session, user_id: str, name: str) -> Optional[APIKey]:
    """为用户创建API密钥"""
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    
    api_key = APIKey(
        id=str(uuid.uuid4()),
        key=f"rec_{secrets.token_urlsafe(32)}",
        name=name,
        user_id=user_id
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key

def get_user_api_keys(db: Session, user_id: str) -> List[APIKey]:
    """获取用户的API密钥列表"""
    return db.query(APIKey).filter(APIKey.user_id == user_id).all()

def delete_api_key(db: Session, api_key_id: str, user_id: str) -> bool:
    """删除用户的API密钥"""
    api_key = db.query(APIKey).filter(
        APIKey.id == api_key_id, 
        APIKey.user_id == user_id
    ).first()
    
    if not api_key:
        return False
    
    db.delete(api_key)
    db.commit()
    return True

def update_user_avatar(db: Session, user_id: str, avatar_url: str) -> User:
    """
    更新用户头像
    
    参数:
        db: 数据库会话
        user_id: 用户ID
        avatar_url: 头像URL
        
    返回:
        更新后的用户对象
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
        
    # 如果用户没有profile字段，初始化为空字典
    if user.profile is None:
        user.profile = {}
        
    # 更新头像URL
    user.profile["avatar"] = avatar_url
    
    db.commit()
    db.refresh(user)
    return user

def delete_user_avatar(db: Session, user_id: str) -> User:
    """
    删除用户头像
    
    参数:
        db: 数据库会话
        user_id: 用户ID
        
    返回:
        更新后的用户对象
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.profile:
        return user
        
    # 从profile中移除头像字段
    if "avatar" in user.profile:
        del user.profile["avatar"]
        
    db.commit()
    db.refresh(user)
    return user 