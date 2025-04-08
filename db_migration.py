"""
数据库迁移脚本，用于解决现有数据库与模型字段不一致问题
"""
import sys
import os
import logging

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from sqlalchemy import create_engine, text
from src.core.config import settings
from src.db.base import Base
from alembic import command
from alembic.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """执行数据库迁移"""
    try:
        # 创建数据库连接
        engine = create_engine(settings.DATABASE_URL)
        
        # 检查Experiment表是否存在
        with engine.connect() as conn:
            result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'experiments')"))
            table_exists = result.scalar()
        
        if table_exists:
            logger.info("Experiment表已存在，检查是否需要添加缺失字段")
            
            # 检查owner_id字段是否存在
            with engine.connect() as conn:
                result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'experiments' AND column_name = 'owner_id')"))
                owner_id_exists = result.scalar()
            
            if not owner_id_exists:
                logger.info("添加owner_id字段")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE experiments ADD COLUMN owner_id VARCHAR REFERENCES users(id) ON DELETE CASCADE"))
                    conn.commit()
                    logger.info("owner_id字段添加成功")
            else:
                logger.info("owner_id字段已存在")
                
            # 检查title字段是否存在（如果模型使用title但数据库是name）
            with engine.connect() as conn:
                result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'experiments' AND column_name = 'title')"))
                title_exists = result.scalar()
                
                result2 = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'experiments' AND column_name = 'name')"))
                name_exists = result2.scalar()
            
            if not title_exists and name_exists:
                logger.info("将name字段重命名为title")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE experiments RENAME COLUMN name TO title"))
                    conn.commit()
                    logger.info("字段重命名成功")
            elif not title_exists:
                logger.info("添加title字段")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE experiments ADD COLUMN title VARCHAR NOT NULL DEFAULT '未命名实验'"))
                    conn.commit()
                    logger.info("title字段添加成功")
            else:
                logger.info("title字段已存在")
                
            # 检查parameters字段是否存在（如果模型使用parameters但数据库是metadata）
            with engine.connect() as conn:
                result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'experiments' AND column_name = 'parameters')"))
                parameters_exists = result.scalar()
                
                result2 = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'experiments' AND column_name = 'metadata')"))
                metadata_exists = result2.scalar()
            
            if not parameters_exists and metadata_exists:
                logger.info("将metadata字段重命名为parameters")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE experiments RENAME COLUMN metadata TO parameters"))
                    conn.commit()
                    logger.info("字段重命名成功")
            elif not parameters_exists:
                logger.info("添加parameters字段")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE experiments ADD COLUMN parameters JSONB"))
                    conn.commit()
                    logger.info("parameters字段添加成功")
            else:
                logger.info("parameters字段已存在")
        
        else:
            logger.info("Experiment表不存在，将通过Alembic创建")
            # 使用Alembic创建所有表
            alembic_cfg = Config(os.path.join(current_dir, "alembic.ini"))
            command.upgrade(alembic_cfg, "head")
            logger.info("数据库表创建成功")
        
        logger.info("数据库迁移完成")
        
    except Exception as e:
        logger.error(f"数据库迁移出错: {str(e)}")
        raise

if __name__ == "__main__":
    run_migration() 