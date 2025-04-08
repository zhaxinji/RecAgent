import logging
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.db.rebuild_db import drop_all_tables, rebuild_db
from src.db.base import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_database():
    """重置数据库，删除所有表然后重新创建"""
    logger.info("开始重置数据库...")
    db = SessionLocal()
    try:
        # 删除所有表
        drop_all_tables(db)
        
        # 重建数据库
        rebuild_db(db)
        
        logger.info("数据库重置完成！")
        return True
    except Exception as e:
        logger.error(f"重置数据库时出错: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    # 直接执行重置数据库操作，无需确认
    success = reset_database()
    sys.exit(0 if success else 1) 