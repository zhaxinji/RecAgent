"""
专为PythonAnywhere环境设计的agent_rec数据库迁移脚本

在PythonAnywhere的Bash控制台中运行:
python pythonanywhere_db_setup.py
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text, inspect
import urllib.parse

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(current_dir, ".env"))
    logger.info("成功加载.env文件")
except ImportError:
    logger.warning("无法导入dotenv库，请安装: pip install python-dotenv")
except Exception as e:
    logger.warning(f"加载.env文件失败: {e}")

# 处理数据库URL的函数
def get_safe_db_url(url):
    """处理数据库URL中的特殊字符"""
    if "postgresql://" in url:
        parts = url.split("://", 1)
        if len(parts) == 2:
            protocol, rest = parts
            if "@" in rest:
                userpass, hostpart = rest.split("@", 1)
                if ":" in userpass:
                    user, password = userpass.split(":", 1)
                    user = urllib.parse.quote_plus(user)
                    password = urllib.parse.quote_plus(password)
                    userpass = f"{user}:{password}"
                return f"{protocol}://{userpass}@{hostpart}"
    return url

# 导入配置和模型
try:
    from src.core.config import settings
    from src.db.base import Base
    from src.models.user import User, APIKey
    from src.models.paper import Paper, Tag, Note, Category, Annotation, Folder
    from src.models.experiment import Experiment, ExperimentRun
    from src.models.writing import WritingProject, WritingSection, WritingReference
    from src.models.assistant import AssistantSession, AssistantMessage
    from src.models.ai_settings import AISettings
    from src.services.auth import get_password_hash
    
    logger.info("成功导入所有模型")
except ImportError as e:
    logger.error(f"导入模块失败: {e}")
    sys.exit(1)

def setup_database():
    """设置数据库表结构"""
    try:
        # 创建数据库引擎
        db_url = settings.DATABASE_URL
        safe_url = get_safe_db_url(db_url)
        engine = create_engine(safe_url)
        logger.info(f"连接到数据库: {db_url.split('@')[1] if '@' in db_url else db_url}")
        
        # 测试连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("数据库连接成功!")
        
        # 打印将要创建的表
        tables = list(Base.metadata.tables.keys())
        logger.info(f"将创建以下表: {sorted(tables)}")
        
        # 创建表
        Base.metadata.create_all(bind=engine)
        logger.info("表创建成功!")
        
        # 验证表创建
        inspector = inspect(engine)
        created_tables = inspector.get_table_names()
        logger.info(f"数据库中的表: {sorted(created_tables)}")
        
        return True
    except Exception as e:
        logger.error(f"创建表时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_superuser(engine):
    """创建超级管理员账户"""
    try:
        if not settings.FIRST_SUPERUSER_EMAIL or not settings.FIRST_SUPERUSER_PASSWORD:
            logger.warning("未配置超级用户，跳过创建")
            return False
            
        # 创建会话
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # 检查是否已存在
        existing = db.query(User).filter(User.email == settings.FIRST_SUPERUSER_EMAIL).first()
        if existing:
            logger.info(f"超级用户 {settings.FIRST_SUPERUSER_EMAIL} 已存在")
            return True
            
        # 创建超级用户
        admin = User(
            email=settings.FIRST_SUPERUSER_EMAIL,
            name="管理员",
            hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            is_active=True,
            is_superuser=True,
            email_verified=True,
            profile={"institution": "RecAgent", "research_interests": ["推荐系统研究"]}
        )
        
        db.add(admin)
        db.commit()
        logger.info(f"超级用户 {settings.FIRST_SUPERUSER_EMAIL} 创建成功!")
        return True
    except Exception as e:
        logger.error(f"创建超级用户时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始设置数据库...")
    
    # 获取Base.metadata中的表和模型
    tables = Base.metadata.tables.keys()
    print(f"检测到 {len(tables)} 个表定义")
    
    # 设置数据库
    if setup_database():
        # 创建数据库引擎（用于创建超级用户）
        db_url = settings.DATABASE_URL
        safe_url = get_safe_db_url(db_url)
        engine = create_engine(safe_url)
        
        # 创建超级用户
        create_superuser(engine)
        
        print("✅ 数据库设置完成!")
    else:
        print("❌ 数据库设置失败!") 