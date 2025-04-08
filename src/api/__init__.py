# API初始化文件 
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.api.auth import router as auth_router
from src.api.papers import router as papers_router
# from src.api.projects import router as projects_router
# from src.api.tags import router as tags_router
# from src.api.categories import router as categories_router
# from src.api.folders import router as folders_router
from src.api.writing import router as writing_router
from src.api.experiments import router as experiments_router
# from src.api.integrations import router as integrations_router
from src.api.users import router as users_router
# from src.api.ai import router as ai_router
# from src.api.images import router as images_router
# from src.api.settings import router as settings_router

from src.api.users.router import get_user_info, get_user_profile, update_research_info, initialize_user_profile
from src.core.deps import get_current_user

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(papers_router, prefix="/papers", tags=["papers"])
# api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
# api_router.include_router(tags_router, prefix="/tags", tags=["tags"])
# api_router.include_router(categories_router, prefix="/categories", tags=["categories"])
# api_router.include_router(folders_router, prefix="/folders", tags=["folders"])
api_router.include_router(writing_router, prefix="/writing", tags=["writing"])
api_router.include_router(experiments_router, prefix="/experiments", tags=["experiments"])
# api_router.include_router(integrations_router, prefix="/integrations", tags=["integrations"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
# api_router.include_router(ai_router, prefix="/ai", tags=["ai"])
# api_router.include_router(images_router, prefix="/images", tags=["images"])
# api_router.include_router(settings_router, prefix="/settings", tags=["settings"])

# 直接暴露用户信息API，方便前端调用
@api_router.get("/userinfo")
async def userinfo_endpoint(current_user = Depends(get_current_user)):
    """直接暴露用户信息API，强制返回真实数据"""
    # 获取用户的profile数据
    profile = current_user.profile or {}
    
    # 确保research_interests是列表
    research_interests = current_user.get_research_interests()
    if not isinstance(research_interests, list):
        if research_interests:
            research_interests = [research_interests]
        else:
            research_interests = []
    
    # 打印调试信息
    print(f"userinfo_endpoint - 用户:{current_user.name}, 研究方向:{research_interests}(类型:{type(research_interests)})")
    
    # 返回用户信息
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "avatar": current_user.avatar,
        "institution": current_user.get_institution() or "",
        "research_interests": research_interests,
        "join_date": current_user.created_at.strftime("%Y-%m-%d") if current_user.created_at else "",
        "is_active": current_user.is_active,
        "email_verified": current_user.email_verified,
        "bio": profile.get("bio", ""),
        "website": profile.get("website", ""),
        "location": profile.get("location", ""),
        "social_links": profile.get("social_links", {})
    }

@api_router.get("/profile")
async def profile_endpoint(current_user = Depends(get_current_user)):
    """直接暴露用户资料API"""
    return get_user_profile(current_user)

@api_router.put("/update-research")
async def update_research_endpoint(
    data: dict,
    current_user = Depends(get_current_user),
):
    """直接暴露更新研究信息API，支持JSON请求体"""
    institution = data.get("institution", "")
    research_interests = data.get("research_interests", [])
    print(f"更新研究信息: 机构={institution}, 方向={research_interests}")
    return update_research_info(institution, research_interests, current_user)

@api_router.post("/init-profile")
async def init_profile_endpoint(current_user = Depends(get_current_user)):
    """直接暴露初始化用户资料API"""
    return initialize_user_profile(current_user)

# 添加前端可访问的简单测试端点
@api_router.get("/test")
async def test_api():
    """测试API是否正常工作"""
    return JSONResponse(
        content={
            "status": "success",
            "message": "API工作正常！请使用/api/userinfo获取真实用户数据",
            "timestamp": "2025-04-03"
        },
        status_code=200
    )

# 其他API路由
# from src.api.auth import router as auth_router
# from src.api.users import router as users_router
# from src.api.papers import router as papers_router
# from src.api.experiments import router as experiments_router
# from src.api.writing import router as writing_router
# from src.api.assistant import router as assistant_router

# api_router.include_router(auth_router.router, prefix="/auth", tags=["认证"])
# api_router.include_router(users_router.router, prefix="/users", tags=["用户"])
# api_router.include_router(papers_router.router, prefix="/papers", tags=["论文"])
# api_router.include_router(experiments_router.router, prefix="/experiments", tags=["实验"])
# api_router.include_router(writing_router.router, prefix="/writing", tags=["写作"])
# api_router.include_router(assistant_router.router, prefix="/assistant", tags=["AI助手"]) 