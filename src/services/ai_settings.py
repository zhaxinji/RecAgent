from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import uuid

from src.models.ai_settings import AISettings
from src.models.user import User
from src.core.config import settings

def get_user_ai_settings(db: Session, user_id: str) -> Optional[AISettings]:
    """获取用户的AI设置"""
    return db.query(AISettings).filter(AISettings.user_id == user_id).first()

def create_or_update_ai_settings(
    db: Session, 
    user_id: str, 
    settings_data: Dict[str, Any]
) -> AISettings:
    """创建或更新用户的AI设置"""
    settings = get_user_ai_settings(db, user_id)
    
    if not settings:
        # 创建新设置
        settings = AISettings(
            id=str(uuid.uuid4()),
            user_id=user_id,
            **settings_data
        )
        db.add(settings)
    else:
        # 更新现有设置
        for key, value in settings_data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
    
    db.commit()
    db.refresh(settings)
    
    # 如果更新了默认提供商，同时更新全局AI助手实例
    if "default_provider" in settings_data:
        # 运行时导入避免循环导入
        from src.services.ai_assistant import change_ai_provider
        # 异步调用，但在同步环境中不等待结果
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 运行异步函数
        loop.run_until_complete(change_ai_provider(settings_data["default_provider"]))
    
    return settings

def delete_ai_settings(db: Session, user_id: str) -> bool:
    """删除用户的AI设置"""
    settings = get_user_ai_settings(db, user_id)
    if not settings:
        return False
    
    db.delete(settings)
    db.commit()
    return True

def get_or_create_user_ai_settings(db: Session, user_id: str) -> AISettings:
    """获取或创建用户的AI设置"""
    settings = get_user_ai_settings(db, user_id)
    if not settings:
        settings = create_or_update_ai_settings(db, user_id, {})
    return settings

async def use_user_api_key(db: Session, user_id: str, provider: str) -> bool:
    """使用用户的API密钥临时替换全局设置中的API密钥"""
    settings = get_user_ai_settings(db, user_id)
    if not settings:
        return False
    
    # 根据提供商获取对应的API密钥属性名
    key_attr = f"{provider}_api_key"
    if not hasattr(settings, key_attr) or getattr(settings, key_attr) is None:
        return False
    
    # 获取用户API密钥
    user_api_key = getattr(settings, key_attr)
    
    # 临时保存当前的API密钥
    provider_config = settings.AI_PROVIDERS.get(provider, {})
    original_api_key = provider_config.get("api_key")
    
    # 替换为用户的API密钥
    provider_config["api_key"] = user_api_key
    settings.AI_PROVIDERS[provider] = provider_config
    
    # 如果当前提供商是被替换的提供商，更新AI助手实例的API密钥
    # 运行时导入避免循环导入
    from src.services.ai_assistant import ai_assistant
    if ai_assistant.provider == provider:
        ai_assistant.api_key = user_api_key
    
    # 返回原始API密钥以便在使用完后恢复
    return original_api_key

async def restore_global_api_key(provider: str, original_api_key: str) -> None:
    """恢复全局设置中的API密钥"""
    provider_config = settings.AI_PROVIDERS.get(provider, {})
    provider_config["api_key"] = original_api_key
    settings.AI_PROVIDERS[provider] = provider_config
    
    # 如果当前提供商是被恢复的提供商，更新AI助手实例的API密钥
    # 运行时导入避免循环导入
    from src.services.ai_assistant import ai_assistant
    if ai_assistant.provider == provider:
        ai_assistant.api_key = original_api_key

def get_ai_provider_settings(provider: Optional[str] = None) -> Dict[str, Any]:
    """获取AI提供商的设置"""
    if provider is None:
        provider = settings.DEFAULT_AI_PROVIDER
    
    if provider not in settings.AI_PROVIDERS:
        raise ValueError(f"不支持的AI提供商: {provider}")
    
    return settings.AI_PROVIDERS[provider] 