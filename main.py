import logging
import sys
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# 在文件开始部分添加详细日志配置
logging.basicConfig(level=logging.DEBUG)

try:
    from src.api.auth import router as auth_router
    from src.api.user import router as user_router
    from src.api.users import router as users_router
    from src.api.papers import router as papers_router
    from src.api.assistant import router as assistant_router
    from src.api.experiments import router as experiments_router
    from src.api.writing import router as writing_router
    from src.core.config import settings
    from src.db.init_db import init_db
except Exception as e:
    print("导入模块时出错:", str(e))
    print("错误详情:")
    traceback.print_exc()
    sys.exit(1)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="RecAgent API - Research Assistant and Paper Management Tool",
    version="0.1.0",
    openapi_url=f"{settings.API_PREFIX}/openapi.json"
)

# CORS 中间件配置
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 添加直接用户信息API，绕过复杂的路由配置
from src.core.deps import get_current_user, get_db
from src.models.user import User
from sqlalchemy.orm import Session
from fastapi import Depends, Body
from typing import List

@app.get("/api/userinfo")
async def get_user_info_direct(current_user: User = Depends(get_current_user)):
    """直接获取用户信息，绕过复杂路由"""
    print(f"直接API - 获取用户信息: 用户名={current_user.name}, ID={current_user.id}")
    
    # 获取用户的profile数据
    profile = current_user.profile or {}
    
    # 返回用户信息
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "avatar": current_user.avatar,
        "institution": profile.get("institution", ""),
        "research_interests": profile.get("research_interests", []),
        "join_date": current_user.created_at.strftime("%Y-%m-%d") if current_user.created_at else "",
        "is_active": current_user.is_active,
        "email_verified": current_user.email_verified,
        "bio": profile.get("bio", ""),
        "website": profile.get("website", ""),
        "location": profile.get("location", ""),
        "social_links": profile.get("social_links", {})
    }

@app.post("/api/init-profile")
async def initialize_user_profile_direct(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """直接初始化用户资料，绕过复杂路由"""
    print(f"直接API - 初始化用户资料: 用户名={current_user.name}, ID={current_user.id}")
    
    # 确保profile字段存在
    if not hasattr(current_user, 'profile') or current_user.profile is None:
        current_user.profile = {}
    
    # 初始化研究信息
    if "institution" not in current_user.profile:
        current_user.profile["institution"] = ""
    
    if "research_interests" not in current_user.profile:
        current_user.profile["research_interests"] = []
    
    # 确保其他字段也有初始值
    profile_defaults = {
        "website": "",
        "location": "",
        "bio": "",
        "social_links": {}
    }
    
    for key, default_value in profile_defaults.items():
        if key not in current_user.profile:
            current_user.profile[key] = default_value
    
    # 保存更新
    db.commit()
    db.refresh(current_user)
    
    # 返回更新后的用户资料
    return get_user_info_direct(current_user)

@app.put("/api/update-research")
async def update_research_info_direct(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """直接更新用户研究信息，绕过复杂路由"""
    print(f"直接API - 更新研究信息: 用户名={current_user.name}, 数据={data}")
    
    # 从请求体中获取数据
    institution = data.get("institution", "")
    research_interests = data.get("research_interests", [])
    
    # 确保research_interests是列表类型
    if isinstance(research_interests, str):
        research_interests = [research_interests] if research_interests else []
    
    print(f"处理后的数据: 机构={institution}, 研究方向(类型:{type(research_interests)})={research_interests}")
    
    # 确保profile字段存在
    if not hasattr(current_user, 'profile') or current_user.profile is None:
        current_user.profile = {}
    
    # 深拷贝现有的profile以避免引用问题
    profile = dict(current_user.profile)
    
    # 更新研究信息
    profile["institution"] = institution
    profile["research_interests"] = research_interests
    
    # 将更新后的profile重新赋值给用户
    current_user.profile = profile
    
    # 打印最终要保存的数据
    print(f"要保存的用户资料: 用户ID={current_user.id}")
    print(f"  - 机构: {current_user.profile.get('institution')}")
    print(f"  - 研究方向: {current_user.profile.get('research_interests')}")
    
    # 保存更新
    db.commit()
    db.refresh(current_user)
    
    # 检查更新后的数据
    print(f"保存后的用户资料: 用户ID={current_user.id}")
    print(f"  - 机构: {current_user.profile.get('institution')}")
    print(f"  - 研究方向: {current_user.profile.get('research_interests')}")
    
    # 返回更新后的用户资料 - 加上await关键字
    return await get_user_info_direct(current_user)

@app.put("/api/update-password")
async def update_password(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户密码API"""
    print(f"更新密码API - 用户:{current_user.name}, ID:{current_user.id}")
    
    # 从请求体中获取数据
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")
    
    if not current_password or not new_password:
        print("密码字段为空")
        raise HTTPException(
            status_code=400, 
            detail="当前密码和新密码不能为空"
        )
    
    # 验证当前密码，从services.auth模块导入函数
    from src.services.auth import verify_password, get_password_hash
    
    if not verify_password(current_password, current_user.hashed_password):
        print("当前密码验证失败")
        raise HTTPException(
            status_code=400,
            detail="当前密码不正确"
        )
    
    # 更新为新密码
    current_user.hashed_password = get_password_hash(new_password)
    
    # 保存更新
    try:
        db.commit()
        db.refresh(current_user)
        print("密码更新成功")
        return {"message": "密码已成功更新"}
    except Exception as e:
        print(f"密码更新失败: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"密码更新失败: {str(e)}"
        )

# 添加路由
try:
    app.include_router(auth_router, prefix=settings.API_PREFIX)
    app.include_router(user_router, prefix=settings.API_PREFIX)
    app.include_router(users_router, prefix=settings.API_PREFIX)
    app.include_router(papers_router, prefix=settings.API_PREFIX)
    app.include_router(assistant_router, prefix=settings.API_PREFIX)
    app.include_router(experiments_router, prefix=settings.API_PREFIX)
    app.include_router(writing_router, prefix=settings.API_PREFIX)
except Exception as e:
    print("添加路由时出错:", str(e))
    print("错误详情:")
    traceback.print_exc()
    sys.exit(1)

@app.on_event("startup")
async def startup_event():
    try:
        # 初始化数据库（如果需要）
        from src.db.base import SessionLocal
        db = SessionLocal()
        try:
            # 暂时注释掉初始化数据库的代码
            # init_db(db)
            print("后端服务启动成功")
        finally:
            db.close()
    except Exception as e:
        print("启动事件处理出错:", str(e))
        print("错误详情:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run("main:app", host="0.0.0.0", port=settings.SERVER_PORT, reload=settings.DEBUG)
    except Exception as e:
        print("启动服务时出错:", str(e))
        print("错误详情:")
        traceback.print_exc()
        sys.exit(1) 