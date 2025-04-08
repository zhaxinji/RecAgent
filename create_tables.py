"""
全面的数据库表结构创建脚本 - agent_rec项目

此脚本将基于models目录中的所有模型定义创建完整的数据库表结构。
它包括用户、论文、实验、写作项目等所有表。
"""
import os
import sys
import importlib
import logging
import urllib.parse

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # 获取父目录
sys.path.insert(0, current_dir)  # 将当前目录添加到路径的最前面
sys.path.insert(0, parent_dir)   # 将父目录添加到路径的最前面

print(f"当前目录: {current_dir}")
print(f"Python路径: {sys.path}")

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(current_dir, ".env"))
    logger.info("成功加载.env文件")
except ImportError:
    logger.warning("无法导入dotenv库，请确保环境变量已正确设置")
except Exception as e:
    logger.warning(f"加载.env文件失败: {e}")

# 创建自定义的数据库URL处理函数
def get_safe_db_url(db_url):
    """处理数据库URL中的特殊字符，确保正确编码"""
    try:
        if "postgresql://" in db_url:
            # 分解URL并对用户名和密码进行编码
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
                    
                    # 处理参数
                    if "?" in hostpart:
                        host_part, params_part = hostpart.split("?", 1)
                        return f"{protocol}://{userpass}@{host_part}?{params_part}"
                    else:
                        return f"{protocol}://{userpass}@{hostpart}"
        
        # 如果没有特殊处理，返回原始URL
        return db_url
    except Exception as e:
        logger.error(f"处理数据库URL时出错: {e}")
        return db_url

# 导入设置模块
try:
    try:
        from src.core.config import settings
        logger.info("成功导入settings")
    except ImportError:
        from agent_rec.src.core.config import settings
        logger.info("使用替代路径导入settings")
    
    try:
        from sqlalchemy import text, create_engine, inspect
        logger.info("成功导入sqlalchemy")
    except ImportError:
        logger.error("无法导入sqlalchemy，请确保已安装此依赖")
        sys.exit(1)
    
    # 创建自定义引擎，处理URL编码问题
    original_db_url = settings.DATABASE_URL
    safe_db_url = get_safe_db_url(original_db_url)
    logger.info(f"原始数据库URL: {original_db_url}")
    logger.info(f"安全处理后的URL: {safe_db_url}")
    
    # 创建引擎
    engine = create_engine(safe_db_url)
    
    try:
        from src.db.base import Base, SessionLocal
        logger.info("成功导入Base类")
    except ImportError:
        try:
            from agent_rec.src.db.base import Base, SessionLocal
            logger.info("使用替代路径导入Base类")
        except ImportError:
            logger.error("无法导入Base类，请检查项目结构")
            sys.exit(1)
except Exception as e:
    logger.error(f"导入必要模块时出错: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 动态导入所有模型
def import_all_models():
    """导入所有模型文件以确保它们都注册到Base中"""
    # 直接导入模型
    imported_models = []
    
    # 尝试导入用户模型
    try:
        try:
            from src.models.user import User, APIKey
            imported_models.extend(["User", "APIKey"])
        except ImportError:
            from agent_rec.src.models.user import User, APIKey
            imported_models.extend(["User", "APIKey"])
        logger.info("成功导入用户模型")
    except ImportError as e:
        logger.error(f"无法导入用户模型: {e}")
        return False
    
    # 尝试导入论文模型
    try:
        try:
            from src.models.paper import Paper, Tag, Note, Category, Annotation, Folder
            imported_models.extend(["Paper", "Tag", "Note", "Category", "Annotation", "Folder"])
        except ImportError:
            from agent_rec.src.models.paper import Paper, Tag, Note, Category, Annotation, Folder
            imported_models.extend(["Paper", "Tag", "Note", "Category", "Annotation", "Folder"])
        logger.info("成功导入论文模型")
    except ImportError as e:
        logger.error(f"无法导入论文模型: {e}")
    
    # 尝试导入实验模型
    try:
        try:
            from src.models.experiment import Experiment, ExperimentRun
            imported_models.extend(["Experiment", "ExperimentRun"])
        except ImportError:
            from agent_rec.src.models.experiment import Experiment, ExperimentRun
            imported_models.extend(["Experiment", "ExperimentRun"])
        logger.info("成功导入实验模型")
    except ImportError as e:
        logger.error(f"无法导入实验模型: {e}")
    
    # 尝试导入写作模型
    try:
        try:
            from src.models.writing import WritingProject, WritingSection, WritingReference
            imported_models.extend(["WritingProject", "WritingSection", "WritingReference"])
        except ImportError:
            from agent_rec.src.models.writing import WritingProject, WritingSection, WritingReference
            imported_models.extend(["WritingProject", "WritingSection", "WritingReference"])
        logger.info("成功导入写作模型")
    except ImportError as e:
        logger.error(f"无法导入写作模型: {e}")
    
    # 尝试导入助手模型
    try:
        try:
            from src.models.assistant import AssistantSession, AssistantMessage
            imported_models.extend(["AssistantSession", "AssistantMessage"])
        except ImportError:
            from agent_rec.src.models.assistant import AssistantSession, AssistantMessage
            imported_models.extend(["AssistantSession", "AssistantMessage"])
        logger.info("成功导入助手模型")
    except ImportError as e:
        logger.error(f"无法导入助手模型: {e}")
    
    # 尝试导入AI设置模型
    try:
        try:
            from src.models.ai_settings import AISettings
            imported_models.append("AISettings")
        except ImportError:
            from agent_rec.src.models.ai_settings import AISettings
            imported_models.append("AISettings")
        logger.info("成功导入AI设置模型")
    except ImportError as e:
        logger.error(f"无法导入AI设置模型: {e}")
    
    # 打印导入的模型
    logger.info(f"成功导入的模型: {imported_models}")
    
    # 打印元数据中的表
    tables = list(Base.metadata.tables.keys())
    logger.info(f"Base.metadata中的表: {tables}")
    
    return len(imported_models) > 0 and len(tables) > 0

# 连接数据库并创建表
def create_tables():
    """创建所有表"""
    try:
        # 使用已导入的engine
        logger.info(f"连接到数据库...")
        
        # 测试连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("数据库连接成功")
        
        # 安全处理可能导致问题的索引
        try:
            with engine.connect() as conn:
                conn.execute(text("DROP INDEX IF EXISTS ix_ai_settings_id"))
                conn.commit()
                logger.info("已安全处理潜在的索引问题")
        except Exception as e:
            logger.warning(f"处理索引时出现问题: {e}")
        
        # 打印将要创建的所有表
        tables_to_create = Base.metadata.tables.keys()
        logger.info(f"即将创建的表: {sorted(list(tables_to_create))}")
        
        # 创建所有表
        logger.info("开始创建所有表...")
        Base.metadata.create_all(bind=engine)
        
        # 验证表创建结果
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"成功创建的表: {sorted(tables)}")
        
        # 检查是否所有表都已创建
        expected_tables = ["users", "papers", "tags", "notes", "categories", 
                          "folders", "experiments", "annotations", "api_keys", 
                          "writing_projects", "assistant_sessions", "ai_settings"]
        
        missing_tables = [table for table in expected_tables if table not in tables]
        if missing_tables:
            logger.warning(f"以下表可能未创建: {missing_tables}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"创建表时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# 创建初始超级用户
def create_superuser():
    """创建超级管理员账户"""
    try:
        # 使用已导入的SessionLocal
        
        # 检查环境变量中是否有超级用户配置
        if not hasattr(settings, "FIRST_SUPERUSER_EMAIL") or not settings.FIRST_SUPERUSER_EMAIL:
            logger.warning("未配置超级用户邮箱，跳过创建超级用户")
            return False
        
        if not hasattr(settings, "FIRST_SUPERUSER_PASSWORD") or not settings.FIRST_SUPERUSER_PASSWORD:
            logger.warning("未配置超级用户密码，跳过创建超级用户")
            return False
        
        # 导入用户模型和密码哈希函数
        try:
            from src.models.user import User
            from src.services.auth import get_password_hash
        except ImportError:
            from agent_rec.src.models.user import User
            from agent_rec.src.services.auth import get_password_hash
        
        # 创建会话
        db = SessionLocal()
        
        # 检查是否已存在超级用户
        existing_user = db.query(User).filter(User.email == settings.FIRST_SUPERUSER_EMAIL).first()
        if existing_user:
            logger.info(f"超级用户 {settings.FIRST_SUPERUSER_EMAIL} 已存在")
            db.close()
            return True
        
        # 创建超级用户
        logger.info(f"创建超级用户: {settings.FIRST_SUPERUSER_EMAIL}")
        admin = User(
            email=settings.FIRST_SUPERUSER_EMAIL,
            name="管理员",
            hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            is_active=True,
            is_superuser=True,
            email_verified=True,
            profile={"institution": "RecAgent", "research_interests": ["推荐系统研究"]}
        )
        
        # 保存到数据库
        db.add(admin)
        db.commit()
        db.close()
        
        logger.info("超级用户创建成功")
        return True
    except Exception as e:
        logger.error(f"创建超级用户时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始创建数据库表结构...")
    # 导入所有模型
    if not import_all_models():
        logger.error("导入模型失败，无法创建表")
        sys.exit(1)
    
    # 创建所有表
    if not create_tables():
        logger.error("创建表结构失败")
        sys.exit(1)
    
    # 创建超级用户
    create_superuser()
    
    logger.info("✅ 数据库表结构创建成功")
    print("✅ 数据库表结构创建成功!") 