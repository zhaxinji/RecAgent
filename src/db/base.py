from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import urllib.parse

try:
    from ..core.config import settings
except ImportError:
    from agent_rec.src.core.config import settings

# 处理数据库URL中可能的编码问题
def get_safe_db_url():
    """返回安全的数据库URL，处理编码问题"""
    db_url = settings.DATABASE_URL
    
    if "postgresql://" in db_url:
        # 分解URL并对密码进行编码
        parts = db_url.split("://", 1)
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
    
    return db_url

SQLALCHEMY_DATABASE_URL = get_safe_db_url()

# 创建SQLAlchemy引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建Base类，所有模型都将继承此类
Base = declarative_base()

# 依赖项函数，用于获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 