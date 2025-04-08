import os
import shutil
import uuid
import tempfile
from typing import Dict, Any, Optional, Tuple
from fastapi import UploadFile
import io

# 尝试导入PyPDF2用于PDF处理
try:
    import PyPDF2
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# 尝试导入PIL用于图像处理
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

async def save_uploaded_file(upload_file: UploadFile, destination_dir: str) -> Dict[str, Any]:
    """
    保存上传的文件到指定目录
    
    Args:
        upload_file: 上传的文件对象
        destination_dir: 目标目录路径
        
    Returns:
        包含文件信息的字典
    """
    # 确保目录存在
    os.makedirs(destination_dir, exist_ok=True)
    
    # 生成唯一文件名
    file_extension = os.path.splitext(upload_file.filename)[1] if upload_file.filename else ""
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(destination_dir, unique_filename)
    
    # 保存文件
    file_size = 0
    with open(file_path, "wb") as f:
        # 读取文件内容
        content = await upload_file.read()
        file_size = len(content)
        f.write(content)
    
    # 返回文件信息
    return {
        "file_path": file_path,
        "file_name": unique_filename,
        "original_name": upload_file.filename,
        "content_type": upload_file.content_type,
        "file_size": file_size
    }

async def get_pdf_content(file_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    从PDF文件中提取文本内容和元数据
    
    Args:
        file_path: PDF文件路径
        
    Returns:
        文本内容和元数据的元组
    """
    if not HAS_PYPDF:
        return "无法提取PDF内容，缺少PyPDF2库", {}
    
    content = ""
    metadata = {}
    
    try:
        with open(file_path, "rb") as f:
            # 创建PDF阅读器对象
            pdf_reader = PyPDF2.PdfReader(f)
            
            # 提取元数据
            if pdf_reader.metadata:
                for key, value in pdf_reader.metadata.items():
                    # 清理元数据键名
                    clean_key = key
                    if key.startswith('/'):
                        clean_key = key[1:]
                    metadata[clean_key] = value
            
            # 提取页数
            metadata["page_count"] = len(pdf_reader.pages)
            
            # 提取文本内容
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    content += page_text + "\n\n"
    except Exception as e:
        return f"PDF提取失败: {str(e)}", {"error": str(e)}
    
    return content, metadata

def create_thumbnail(file_path: str, output_dir: str, max_size: int = 200) -> Optional[str]:
    """
    为PDF文件创建缩略图
    
    Args:
        file_path: PDF文件路径
        output_dir: 输出目录
        max_size: 缩略图最大尺寸
        
    Returns:
        缩略图路径，如果创建失败则返回None
    """
    if not HAS_PIL or not HAS_PYPDF:
        return None
    
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成输出文件路径
        thumbnail_filename = f"{uuid.uuid4()}.jpg"
        thumbnail_path = os.path.join(output_dir, thumbnail_filename)
        
        # 使用PyPDF2打开PDF
        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            if len(pdf_reader.pages) > 0:
                # 这里简化处理，实际上很难直接从PyPDF2获取第一页的图像
                # 实际应用中可能需要使用pdf2image等库
                pass
        
        # 使用默认占位图
        # 创建一个简单的空白图像作为占位符
        img = Image.new('RGB', (max_size, int(max_size*1.414)), color=(245, 245, 245))
        img.save(thumbnail_path, "JPEG")
        
        return thumbnail_path
    except Exception as e:
        print(f"创建缩略图失败: {str(e)}")
        return None

def safe_delete_file(file_path: str) -> bool:
    """
    安全删除文件
    
    Args:
        file_path: 要删除的文件路径
        
    Returns:
        是否成功删除
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        print(f"删除文件失败: {str(e)}")
        return False

def create_temp_directory() -> str:
    """
    创建临时目录
    
    Returns:
        临时目录路径
    """
    temp_dir = tempfile.mkdtemp()
    return temp_dir

def cleanup_temp_directory(temp_dir: str) -> None:
    """
    清理临时目录
    
    Args:
        temp_dir: 临时目录路径
    """
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True) 