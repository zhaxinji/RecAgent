from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uvicorn
import os
import logging
from sqlalchemy import text
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.api import api_router
from src.core.config import settings
from src.db.base import get_db, engine

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RecAgent API",
    description="RecAgent - 学术研究助手API",
    version="0.1.0",
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Content-Disposition"]
)

# 挂载静态文件
upload_dir = Path(settings.UPLOAD_DIR)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

# 挂载API路由
app.include_router(api_router, prefix=settings.API_PREFIX)

# 检查数据库表结构
@app.on_event("startup")
async def check_database_structure():
    """启动时检查数据库表结构，确保字段存在"""
    logger.info("检查数据库表结构...")
    
    try:
        # 获取数据库连接
        db = next(get_db())
        
        # 检查papers表的analysis_progress字段
        try:
            result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'papers' 
            AND column_name = 'analysis_progress'
            """))
            
            if result.fetchone() is None:
                logger.warning("papers表缺少analysis_progress字段，正在添加...")
                
                # 添加字段
                db.execute(text("""
                ALTER TABLE papers 
                ADD COLUMN IF NOT EXISTS analysis_progress INTEGER DEFAULT 0
                """))
                
                db.commit()
                logger.info("字段添加成功!")
            else:
                logger.info("papers表结构正常")
        except Exception as e:
            logger.error(f"检查papers表结构时出错: {str(e)}")
    
    except Exception as e:
        logger.error(f"数据库检查失败: {str(e)}")
    
    logger.info("数据库检查完成")

# 注册异常处理
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )

# 自定义OpenAPI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/")
async def root():
    return {
        "app": "RecAgent",
        "version": app.version,
        "message": "RecAgent学术研究助手API正在运行",
        "documentation": f"{settings.SERVER_HOST}/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    ) 