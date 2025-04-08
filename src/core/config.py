import os
from typing import List, Union, Optional, Dict, Any
from pydantic import AnyHttpUrl, validator, EmailStr, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import urllib.parse
import secrets

# 加载环境变量
load_dotenv()

class Settings(BaseSettings):
    # 基本设置
    PROJECT_NAME: str = "Agent-REC"
    API_V1_STR: str = "/api"
    API_PREFIX: str = "/api"  # 添加API_PREFIX作为API_V1_STR的别名
    
    # 服务器设置
    SERVER_HOST: str = "http://localhost:8001"  # 修改为字符串类型
    SERVER_PORT: int = 8001
    DEBUG: bool = True if os.getenv("DEBUG", "False").lower() == "true" else False
    
    # 数据库设置
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "recagent")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    
    @validator("DATABASE_URL", pre=True)
    def encode_database_url(cls, v: str) -> str:
        """确保数据库URL正确编码"""
        # 如果使用环境变量中的DATABASE_URL
        if "postgresql://" in v:
            # 分解URL并对每个组件进行编码
            parts = v.split("://", 1)
            if len(parts) == 2:
                protocol, rest = parts
                # 分离用户名密码和主机部分
                if "@" in rest:
                    userpass, hostpart = rest.split("@", 1)
                    # 编码用户名和密码
                    if ":" in userpass:
                        user, password = userpass.split(":", 1)
                        user = urllib.parse.quote_plus(user)
                        password = urllib.parse.quote_plus(password)
                        userpass = f"{user}:{password}"
                    return f"{protocol}://{userpass}@{hostpart}"
        return v
    
    # 安全设置
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    ALGORITHM: str = "HS256"
    
    # 超级用户设置
    FIRST_SUPERUSER_EMAIL: str = os.getenv("FIRST_SUPERUSER_EMAIL", "")
    FIRST_SUPERUSER_PASSWORD: str = os.getenv("FIRST_SUPERUSER_PASSWORD", "")
    
    # CORS设置
    BACKEND_CORS_ORIGINS: List[str] = []
    CORS_ORIGINS: List[str] = []  # 添加CORS_ORIGINS作为BACKEND_CORS_ORIGINS的别名

    @field_validator("BACKEND_CORS_ORIGINS", mode='before')
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
        
    @field_validator("CORS_ORIGINS", mode='before')
    def assemble_cors_origins_alias(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # AI模型设置
    # 默认AI提供商
    DEFAULT_AI_PROVIDER: str = os.getenv("AI_PROVIDER", "deepseek")
    
    # DeepSeek配置
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_BASE: str = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    # OpenAI配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Claude配置
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_API_BASE: str = os.getenv("CLAUDE_API_BASE", "https://api.anthropic.com/v1")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-3-haiku")
    
    # 默认LLM模型 - 用于论文分析
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", DEEPSEEK_MODEL)
    
    # 模型配置映射
    AI_PROVIDERS: Dict[str, Dict[str, Any]] = {
        "deepseek": {
            "api_key": DEEPSEEK_API_KEY,
            "api_base": DEEPSEEK_API_BASE,
            "model": DEEPSEEK_MODEL,
        },
        "openai": {
            "api_key": OPENAI_API_KEY,
            "api_base": OPENAI_API_BASE,
            "model": OPENAI_MODEL,
            "embedding_model": OPENAI_EMBEDDING_MODEL
        },
        "claude": {
            "api_key": CLAUDE_API_KEY,
            "api_base": CLAUDE_API_BASE,
            "model": CLAUDE_MODEL,
        }
    }
    
    # LLM API密钥 - 用于论文分析，根据默认提供商自动选择
    @property
    def LLM_API_KEY(self) -> str:
        provider = self.DEFAULT_AI_PROVIDER
        if provider in self.AI_PROVIDERS:
            return self.AI_PROVIDERS[provider]["api_key"]
        return ""
    
    # 存储设置
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 20 * 1024 * 1024  # 20MB
    TEMP_DIR: str = "temp"
    
    # Redis设置
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    
    # ElasticSearch设置
    ES_HOST: str = os.getenv("ES_HOST", "localhost")
    ES_PORT: int = int(os.getenv("ES_PORT", "9200"))
    ES_USER: str = os.getenv("ES_USER", "")
    ES_PASSWORD: str = os.getenv("ES_PASSWORD", "")
    
    # MinIO设置
    MINIO_HOST: str = os.getenv("MINIO_HOST", "localhost")
    MINIO_PORT: str = os.getenv("MINIO_PORT", "9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "recagent")
    
    # 前端URL（用于重置密码链接等）
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # 邮件设置
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "True").lower() == "true"
    EMAILS_FROM_EMAIL: str = os.getenv("EMAILS_FROM_EMAIL", "noreply@recagent.com")
    EMAILS_FROM_NAME: str = os.getenv("EMAILS_FROM_NAME", "RecAgent")
    
    # 密码重置设置
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_HOURS", "24"))

    # API配置
    API_VERSION: str = "v1"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    
    # 全文检索配置
    SEARCH_INDEXDIR: str = "search_index"
    
    # 代理URL配置
    PROXY_URL: Optional[str] = "http://127.0.0.1:7890"

    # 媒体文件存储配置
    MEDIA_ROOT: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "media")
    MEDIA_URL: str = "/media/"
    
    # 最大上传文件大小 (10MB)
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    
    # 允许的图片类型
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    
    # 允许的文档类型
    ALLOWED_DOCUMENT_TYPES: List[str] = [
        "application/pdf", 
        "application/msword", 
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ]
    
    # AI服务配置
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None
    
    # 配置模型
    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "extra": "ignore"  # 允许额外字段
    }


# 创建全局设置对象
settings = Settings() 