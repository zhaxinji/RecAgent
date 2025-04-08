import logging
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from sqlalchemy.schema import DropTable, CreateTable

from src.core.config import settings
from src.db.base import Base, engine, SessionLocal

# 导入所有模型，确保在创建表之前已经定义了所有模型和关系
from src.models.user import User, APIKey
from src.models.paper import Paper, Tag, Category, Note, Annotation, Folder
from src.models.ai_settings import AISettings
# 导入其他可能需要的模型
try:
    from src.models.writing import WritingProject
    from src.models.experiment import Experiment
except ImportError:
    logging.warning("部分模型导入失败，可能在创建数据库表时出现问题")

from src.services.auth import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def drop_all_tables(db: Session) -> None:
    """删除所有现有表"""
    try:
        logger.info("正在删除所有现有表...")
        # PostgreSQL方式删除所有表
        
        # 获取所有表名
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        # 禁用外键约束 (PostgreSQL方式)
        db.execute(text("SET session_replication_role = 'replica';"))
        
        # 删除所有表
        for table_name in table_names:
            logger.info(f"删除表: {table_name}")
            db.execute(text(f"DROP TABLE IF EXISTS \"{table_name}\" CASCADE;"))
        
        # 重新启用外键约束
        db.execute(text("SET session_replication_role = 'origin';"))
        db.commit()
        logger.info("所有表已成功删除")
    except Exception as e:
        logger.error(f"删除表时出错: {e}")
        db.rollback()
        raise

def rebuild_db(db: Session) -> None:
    """重建数据库表并添加初始数据"""
    try:
        # 重新创建所有表
        logger.info("创建数据库表...")
        # 确保所有模型已被导入和映射
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建成功。")
        
        # 检查数据库表结构
        inspect_tables(db)
        
        # 创建超级用户
        create_superuser(db)
    except Exception as e:
        logger.error(f"数据库初始化过程中出错: {e}")
        raise

def inspect_tables(db: Session) -> None:
    """检查并打印数据库表结构"""
    inspector = inspect(engine)
    for table_name in inspector.get_table_names():
        logger.info(f"表: {table_name}")
        for column in inspector.get_columns(table_name):
            logger.info(f"  - 列: {column['name']}, 类型: {column['type']}")

def create_superuser(db: Session) -> None:
    """检查并创建超级用户"""
    if settings.FIRST_SUPERUSER_EMAIL and settings.FIRST_SUPERUSER_PASSWORD:
        # 检查用户是否已存在
        user = db.query(User).filter(User.email == settings.FIRST_SUPERUSER_EMAIL).first()
        if not user:
            logger.info(f"创建超级用户 {settings.FIRST_SUPERUSER_EMAIL}")
            user_name = settings.FIRST_SUPERUSER_EMAIL.split("@")[0]
            user_obj = User(
                email=settings.FIRST_SUPERUSER_EMAIL,
                name=user_name,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                is_superuser=True,
            )
            db.add(user_obj)
            db.commit()
            logger.info(f"超级用户 {settings.FIRST_SUPERUSER_EMAIL} 创建成功")
        else:
            logger.info(f"超级用户 {settings.FIRST_SUPERUSER_EMAIL} 已存在")

def main() -> None:
    """主函数用于独立运行时初始化数据库"""
    db = SessionLocal()
    try:
        # 确认操作
        confirmation = input("注意: 这将删除所有现有表并重新创建它们。所有数据将丢失！是否继续? (y/n): ")
        if confirmation.lower() != 'y':
            logger.info("操作已取消")
            return
        
        # 删除所有表
        drop_all_tables(db)
        
        # 重建数据库
        rebuild_db(db)
        
        logger.info("数据库重建完成！")
    finally:
        db.close()

if __name__ == "__main__":
    main() 