import logging
from sqlalchemy.orm import Session

from src.core.config import settings
from src.db.base import Base, engine
from src.models import User
from src.services.auth import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db(db: Session) -> None:
    """初始化数据库，创建表并添加初始数据"""
    try:
        # 创建数据库表
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully.")
        
        # 检查是否需要创建超级用户
        create_superuser(db)
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        raise

def create_superuser(db: Session) -> None:
    """检查并创建超级用户"""
    if settings.FIRST_SUPERUSER_EMAIL and settings.FIRST_SUPERUSER_PASSWORD:
        # 检查用户是否已存在
        user = db.query(User).filter(User.email == settings.FIRST_SUPERUSER_EMAIL).first()
        if not user:
            logger.info(f"Creating superuser {settings.FIRST_SUPERUSER_EMAIL}")
            user_name = settings.FIRST_SUPERUSER_EMAIL.split("@")[0]
            user_obj = User(
                email=settings.FIRST_SUPERUSER_EMAIL,
                name=user_name,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                is_superuser=True,
            )
            db.add(user_obj)
            db.commit()
            logger.info(f"Superuser {settings.FIRST_SUPERUSER_EMAIL} created successfully")
        else:
            logger.info(f"Superuser {settings.FIRST_SUPERUSER_EMAIL} already exists")

def main() -> None:
    """主函数用于独立运行时初始化数据库"""
    from src.db.base import SessionLocal
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()

if __name__ == "__main__":
    main() 