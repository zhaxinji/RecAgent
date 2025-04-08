import os
import shutil
import uuid
from typing import Optional
from datetime import datetime
from fastapi import UploadFile
import aiofiles
import mimetypes
from PIL import Image

from src.core.config import settings

# 确保存储目录存在
os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

async def upload_file_to_storage(
    file: UploadFile, 
    folder: str = "uploads", 
    allowed_types: list = None, 
    max_size: int = 10 * 1024 * 1024,  # 默认10MB
    filename_override: Optional[str] = None
) -> str:
    """
    上传文件到存储系统
    
    Args:
        file: 上传的文件
        folder: 存储文件夹路径
        allowed_types: 允许的文件类型列表，如 ['image/jpeg', 'image/png']
        max_size: 最大文件大小（字节）
        filename_override: 覆盖生成的文件名
        
    Returns:
        文件的URL路径
    """
    # 验证文件类型
    if allowed_types and file.content_type not in allowed_types:
        raise ValueError(f"不支持的文件类型: {file.content_type}")
    
    # 获取文件内容
    contents = await file.read()
    
    # 验证文件大小
    if len(contents) > max_size:
        raise ValueError(f"文件太大，最大允许大小为 {max_size/1024/1024}MB")
    
    # 重置文件指针
    await file.seek(0)
    
    # 创建存储目录
    storage_dir = os.path.join(settings.MEDIA_ROOT, folder)
    os.makedirs(storage_dir, exist_ok=True)
    
    # 生成唯一的文件名
    if filename_override:
        base_filename = filename_override
    else:
        base_filename = f"{uuid.uuid4().hex}"
    
    # 从原始文件名中提取扩展名
    original_extension = os.path.splitext(file.filename)[1] if file.filename else ""
    
    # 如果没有扩展名，尝试从MIME类型获取
    if not original_extension:
        extension = mimetypes.guess_extension(file.content_type) or ""
    else:
        extension = original_extension
    
    # 组合完整文件名
    filename = f"{base_filename}{extension}"
    file_path = os.path.join(storage_dir, filename)
    
    # 异步写入文件
    async with aiofiles.open(file_path, 'wb') as out_file:
        while contents := await file.read(1024):
            await out_file.write(contents)
    
    # 处理图片优化（如果是图片文件）
    if file.content_type.startswith('image/'):
        try:
            optimize_image(file_path)
        except Exception as e:
            print(f"图片优化失败: {str(e)}")
    
    # 返回相对URL路径
    relative_path = os.path.join(folder, filename).replace('\\', '/')
    url_path = f"{settings.MEDIA_URL}{relative_path}"
    
    return url_path

def optimize_image(file_path: str, max_width: int = 1200, quality: int = 85):
    """优化图片文件，调整大小并压缩"""
    try:
        with Image.open(file_path) as img:
            # 检查是否需要调整大小
            if img.width > max_width:
                # 计算新高度，保持宽高比
                height_ratio = img.height / img.width
                new_height = int(max_width * height_ratio)
                img = img.resize((max_width, new_height), Image.LANCZOS)
            
            # 保存优化后的图片
            img.save(file_path, optimize=True, quality=quality)
    except Exception as e:
        # 如果处理失败，保持原图不变
        print(f"图片优化失败: {str(e)}")

async def delete_file_from_storage(file_path: str) -> bool:
    """
    从存储系统中删除文件
    
    Args:
        file_path: 文件的相对路径（不包含MEDIA_URL前缀）
        
    Returns:
        成功删除返回True，否则False
    """
    try:
        # 构建完整路径
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        # 检查文件是否存在
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False
    except Exception as e:
        print(f"删除文件失败: {str(e)}")
        return False 