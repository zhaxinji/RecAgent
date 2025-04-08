#!/usr/bin/env python3
"""
数据库迁移脚本 - 添加论文分析进度字段
"""
import sys
import os

# 添加项目目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from src.core.config import settings

def main():
    """
    执行数据库迁移，为papers表添加analysis_progress字段
    """
    print("开始执行数据库迁移...")
    
    try:
        # 创建数据库连接
        # 获取正确的数据库URI
        db_uri = settings.DATABASE_URL
        print(f"连接到数据库: {db_uri}")
        engine = create_engine(db_uri)
        
        with engine.connect() as conn:
            # 检查字段是否已存在
            check_sql = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'papers' 
            AND column_name = 'analysis_progress'
            """)
            
            result = conn.execute(check_sql)
            if result.fetchone() is None:
                print("字段 'analysis_progress' 不存在，现在添加...")
                
                # 添加字段
                conn.execute(text("""
                ALTER TABLE papers 
                ADD COLUMN IF NOT EXISTS analysis_progress INTEGER DEFAULT 0
                """))
                
                conn.commit()
                print("字段添加成功!")
            else:
                print("字段 'analysis_progress' 已存在，无需添加")
        
        print("数据库迁移完成")
        return True
    
    except Exception as e:
        print(f"数据库迁移失败: {str(e)}")
        import traceback
        print("异常详情:", traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 