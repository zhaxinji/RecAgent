from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator
from datetime import datetime, timedelta
import re

from src.schemas.assistant import AIProviderEnum

# 基础用户模型
class UserBase(BaseModel):
    email: EmailStr
    name: str
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    profile: Optional[Dict[str, Any]] = None
    avatar: Optional[str] = None  # 可以是URL或Base64字符串

# 创建用户时的输入数据
class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def password_validation(cls, v):
        if len(v) < 8:
            raise ValueError('密码长度不能少于8位')
        if not re.search(r'[A-Z]', v):
            raise ValueError('密码需要包含至少一个大写字母')
        if not re.search(r'[a-z]', v):
            raise ValueError('密码需要包含至少一个小写字母')
        if not re.search(r'[0-9]', v):
            raise ValueError('密码需要包含至少一个数字')
        return v

# 用户更新数据
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    
    @validator('password')
    def password_validation(cls, v):
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError('密码长度不能少于8位')
        if not re.search(r'[A-Z]', v):
            raise ValueError('密码需要包含至少一个大写字母')
        if not re.search(r'[a-z]', v):
            raise ValueError('密码需要包含至少一个小写字母')
        if not re.search(r'[0-9]', v):
            raise ValueError('密码需要包含至少一个数字')
        return v

# 用户资料更新模型
class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    institution: Optional[str] = None
    research_interests: Optional[List[str]] = None
    website: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None
    
    @validator('website')
    def validate_website(cls, v):
        if v is not None and v and not (v.startswith('http://') or v.startswith('https://')):
            v = 'https://' + v
        return v
    
    @validator('social_links')
    def validate_social_links(cls, v):
        if v is not None:
            allowed_platforms = {'github', 'twitter', 'linkedin', 'facebook', 'scholar', 'orcid', 'researchgate', 'wechat', 'weibo'}
            for platform, url in v.items():
                if platform not in allowed_platforms:
                    raise ValueError(f'不支持的社交平台: {platform}')
                if url and not (url.startswith('http://') or url.startswith('https://')):
                    v[platform] = 'https://' + url
        return v

class UserInDB(UserBase):
    id: str
    hashed_password: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    email_verified: bool = False
    avatar: Optional[str] = None
    
    class Config:
        orm_mode = True

# 用户详细资料响应模型
class UserProfileResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    avatar: Optional[str] = None
    institution: Optional[str] = None
    research_interests: Optional[List[str]] = None
    website: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None
    is_active: bool
    email_verified: bool
    created_at: datetime
    projects_count: int = 0
    papers_count: int = 0
    experiments_count: int = 0
    
    class Config:
        orm_mode = True

# 用户信息响应
class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    email_verified: bool
    avatar: Optional[str] = None

    class Config:
        orm_mode = True

# 用户登录请求
class UserLogin(BaseModel):
    username_or_email: str
    password: str

# Token响应
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Token内容
class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None

# 密码重置请求
class PasswordResetRequest(BaseModel):
    email: EmailStr

# 验证密码重置token
class PasswordResetVerify(BaseModel):
    token: str
    new_password: str
    
    @validator('new_password')
    def password_validation(cls, v):
        if len(v) < 8:
            raise ValueError('密码长度不能少于8位')
        if not re.search(r'[A-Z]', v):
            raise ValueError('密码需要包含至少一个大写字母')
        if not re.search(r'[a-z]', v):
            raise ValueError('密码需要包含至少一个小写字母')
        if not re.search(r'[0-9]', v):
            raise ValueError('密码需要包含至少一个数字')
        return v

# 邮箱验证请求
class EmailVerificationRequest(BaseModel):
    token: str

# API密钥基础模型
class APIKeyBase(BaseModel):
    name: str = Field(..., description="API密钥名称")

# 创建API密钥请求
class APIKeyCreate(APIKeyBase):
    pass

# API密钥响应
class APIKeyResponse(APIKeyBase):
    id: str
    key: str
    last_used_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        orm_mode = True

class AISettingsBase(BaseModel):
    """AI设置基础模型"""
    default_provider: Optional[AIProviderEnum] = None
    openai_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    custom_settings: Optional[Dict[str, Any]] = None

class AISettingsUpdate(AISettingsBase):
    """AI设置更新模型"""
    pass

class AISettingsResponse(AISettingsBase):
    """AI设置响应模型"""
    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True 