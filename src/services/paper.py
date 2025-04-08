from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc, Boolean, Column, String, Integer, DateTime, ForeignKey, Text, Table, JSON, func, text
from fastapi import UploadFile, HTTPException, status
import uuid
import os
import json
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
import io
import shutil
import pypdf
import httpx
from sqlalchemy import text
from sqlalchemy.sql import func

from src.models.paper import Paper, Tag, Note, paper_tags, Category
from src.models.user import User
from src.core.config import settings
from src.db.base import Base

# 论文CRUD操作
def get_paper_by_id(db: Session, paper_id: str, user_id: Optional[str] = None) -> Optional[Paper]:
    """通过ID获取论文"""
    query = db.query(Paper).filter(Paper.id == paper_id)
    if user_id:
        query = query.filter(Paper.owner_id == user_id)
    return query.first()

def get_papers(
    db: Session, 
    user_id: str, 
    skip: int = 0, 
    limit: int = 100,
    query: Optional[str] = None,
    tag_ids: Optional[List[str]] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> List[Paper]:
    """获取用户的论文列表"""
    paper_query = db.query(Paper).filter(Paper.owner_id == user_id)
    
    # 如果有搜索字符串
    if query:
        search = f"%{query}%"
        paper_query = paper_query.filter(
            or_(
                Paper.title.ilike(search),
                Paper.abstract.ilike(search),
                Paper.content.ilike(search),
            )
        )
    
    # 如果有标签过滤
    if tag_ids:
        for tag_id in tag_ids:
            paper_query = paper_query.filter(Paper.tags.any(Tag.id == tag_id))
    
    # 排序
    if sort_order.lower() == "desc":
        paper_query = paper_query.order_by(desc(getattr(Paper, sort_by)))
    else:
        paper_query = paper_query.order_by(asc(getattr(Paper, sort_by)))
    
    return paper_query.offset(skip).limit(limit).all()

def create_paper(
    db: Session, 
    user_id: str, 
    title: str,
    abstract: Optional[str] = None,
    authors: Optional[List[Dict[str, str]]] = None,
    publication_date: Optional[datetime] = None,
    journal: Optional[str] = None,
    conference: Optional[str] = None,
    doi: Optional[str] = None,
    url: Optional[str] = None,
    file_path: Optional[str] = None,
    thumbnail_path: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    content: Optional[str] = None,
    file_size: Optional[int] = None,
    source: str = "upload"
) -> Paper:
    """创建新论文"""
    # 确保数据库中存在analysis_progress字段
    try:
        # 首先检查字段是否存在
        db.execute(text("ALTER TABLE papers ADD COLUMN IF NOT EXISTS analysis_progress INTEGER DEFAULT 0"))
        db.commit()
    except Exception as e:
        print(f"添加analysis_progress字段时出错: {str(e)}")
        # 错误不影响继续执行
    
    # 打印日志帮助调试
    print(f"创建论文记录: title={title}, user_id={user_id}, file_path={file_path}")
    
    try:
        db_paper = Paper(
            id=str(uuid.uuid4()),
            title=title,
            abstract=abstract,
            authors=authors,
            publication_date=publication_date,
            journal=journal,
            conference=conference,
            doi=doi,
            url=url,
            file_path=file_path,
            thumbnail_path=thumbnail_path,
            paper_metadata=metadata,
            owner_id=user_id,
            content=content,
            file_size=file_size,
            source=source,
            analysis_progress=0  # 初始化分析进度为0
        )
        
        # 处理标签
        if tags:
            for tag_name in tags:
                # 查找或创建标签
                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                if not tag:
                    tag = Tag(id=str(uuid.uuid4()), name=tag_name)
                    db.add(tag)
                db_paper.tags.append(tag)
        
        print(f"准备添加论文记录: id={db_paper.id}")
        db.add(db_paper)
        print(f"提交到数据库")
        db.commit()
        print(f"刷新实例")
        db.refresh(db_paper)
        return db_paper
    except Exception as e:
        print(f"创建论文记录时出错: {str(e)}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
        db.rollback()
        raise e

def update_paper(
    db: Session, 
    paper_id: str, 
    user_id: str, 
    update_data: Dict[str, Any]
) -> Optional[Paper]:
    """更新论文信息"""
    paper = get_paper_by_id(db, paper_id, user_id)
    if not paper:
        return None
    
    # 添加调试日志
    print(f"更新论文 ID: {paper_id}, 数据: {update_data}")
    
    # 类型检查与转换
    # 1. 检查tags字段
    if "tags" in update_data:
        # 确保tags是列表
        if not isinstance(update_data["tags"], list):
            print(f"警告: tags不是列表类型, 当前类型: {type(update_data['tags'])}")
            # 尝试转换字符串为列表
            if isinstance(update_data["tags"], str):
                update_data["tags"] = [tag.strip() for tag in update_data["tags"].split(",") if tag.strip()]
                print(f"已转换tags字符串为列表: {update_data['tags']}")
            else:
                # 不是字符串也不是列表，使用空列表
                print(f"无法转换tags为列表，使用空列表")
                update_data["tags"] = []
        
        # 清除现有标签
        paper.tags = []
        
        # 添加新标签
        for tag_name in update_data["tags"]:
            # 查找或创建标签
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                tag = Tag(id=str(uuid.uuid4()), name=tag_name)
                db.add(tag)
            paper.tags.append(tag)
        
        # 从更新数据中删除标签字段
        del update_data["tags"]
    
    # 2. 检查authors字段
    if "authors" in update_data:
        # 确保authors是列表
        if not isinstance(update_data["authors"], list):
            print(f"警告: authors不是列表类型, 当前类型: {type(update_data['authors'])}")
            # 尝试转换字符串为列表
            if isinstance(update_data["authors"], str):
                # 将逗号分隔的作者列表转换为字典列表
                update_data["authors"] = [{"name": name.strip()} for name in update_data["authors"].split(",") if name.strip()]
                print(f"已转换authors字符串为列表: {update_data['authors']}")
            else:
                # 不是字符串也不是列表，使用空列表
                print(f"无法转换authors为列表，使用空列表")
                update_data["authors"] = []
    
    # 3. 检查notes字段
    if "notes" in update_data:
        # 重要: notes在schema中是字符串字段，但在Paper模型中是关系字段(List[Note])
        # 需要将notes从更新数据中移除，避免类型不匹配错误
        print(f"检测到notes字段更新，值类型: {type(update_data['notes'])}")
        
        # 保存notes值，然后从更新数据中删除
        notes_value = update_data.pop("notes")
        print(f"已从更新数据中移除notes字段，值: {notes_value}")
        
        # 如果需要，这里可以添加代码处理notes关系
        # 例如，创建一个Note对象并关联到paper
        # 但当前的前端实现似乎是想直接更新notes字段而非关系
        # 如果需要，可以在这里添加适当的处理逻辑
    
    # 4. 检查其他字段的null值
    for key, value in list(update_data.items()):
        if value is None:
            print(f"将字段 {key} 的None值替换为合适的默认值")
            if key in ["abstract", "journal", "conference", "doi", "url"]:
                update_data[key] = ""  # 字符串字段用空字符串
    
    # 更新其他字段
    for key, value in update_data.items():
        if hasattr(paper, key):
            try:
                setattr(paper, key, value)
                print(f"已更新字段 {key} = {value}")
            except Exception as e:
                print(f"更新字段 {key} 失败: {str(e)}, 值类型: {type(value)}")
                raise ValueError(f"更新字段 {key} 失败: {str(e)}")
    
    try:
        db.commit()
        db.refresh(paper)
        print(f"已成功更新论文: {paper.id}")
        return paper
    except Exception as e:
        db.rollback()
        print(f"提交更新失败: {str(e)}")
        raise e

def set_paper_favorite(
    db: Session, 
    paper_id: str, 
    user_id: str, 
    is_favorite: bool
) -> Optional[Paper]:
    """设置论文收藏状态"""
    # 查找论文
    paper = get_paper_by_id(db, paper_id, user_id)
    if not paper:
        print(f"设置收藏状态失败: 论文未找到 (paper_id={paper_id}, user_id={user_id})")
        return None
    
    # 记录操作
    print(f"设置论文 {paper_id} 的收藏状态为: {is_favorite}")
    
    try:
        # 更新收藏状态
        paper.is_favorite = is_favorite
        db.commit()
        db.refresh(paper)
        print(f"成功更新论文 {paper_id} 的收藏状态为: {is_favorite}")
        return paper
    except Exception as e:
        db.rollback()
        print(f"设置收藏状态失败: {str(e)}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
        raise e

def delete_paper(db: Session, paper_id: str, user_id: str) -> bool:
    """删除论文"""
    print(f"尝试删除论文 paper_id={paper_id}, user_id={user_id}")
    
    # 首先验证论文是否存在并属于当前用户 - 使用原生SQL避免任何懒加载
    check_paper_sql = text("""
        SELECT id, title, file_path, thumbnail_path 
        FROM papers 
        WHERE id = :paper_id AND owner_id = :user_id
    """)
    
    result = db.execute(check_paper_sql, {"paper_id": paper_id, "user_id": user_id})
    paper_data = result.fetchone()
    
    if not paper_data:
        print(f"论文未找到: paper_id={paper_id}")
        return False
    
    # 使用字典而不是ORM对象存储论文信息
    paper_info = {
        "id": paper_data[0],
        "title": paper_data[1],
        "file_path": paper_data[2],
        "thumbnail_path": paper_data[3]
    }
    
    try:
        print(f"准备删除论文: id={paper_info['id']}, title={paper_info['title']}")
        
        # 1. 首先尝试删除物理文件
        if paper_info["file_path"]:
            try:
                delete_file_from_storage(paper_info["file_path"])
                print(f"已删除物理文件: {paper_info['file_path']}")
            except Exception as e:
                print(f"删除物理文件失败 {paper_info['file_path']}: {e}")
        
        if paper_info["thumbnail_path"]:
            try:
                delete_file_from_storage(paper_info["thumbnail_path"])
                print(f"已删除缩略图: {paper_info['thumbnail_path']}")
            except Exception as e:
                print(f"删除缩略图失败 {paper_info['thumbnail_path']}: {e}")
        
        # 2. 使用原生SQL按顺序删除所有关联数据，确保每个SQL语句都有try/except处理
        
        # 设置事务隔离级别
        try:
            db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        except Exception as e:
            print(f"设置事务隔离级别失败(忽略): {e}")
        
        # 删除笔记 (notes表)
        try:
            db.execute(
                text("DELETE FROM notes WHERE paper_id = :paper_id"),
                {"paper_id": paper_id}
            )
            print(f"已删除论文相关笔记")
        except Exception as e:
            print(f"删除笔记失败(忽略): {e}")
        
        # 删除标注 (annotations表)
        try:
            db.execute(
                text("DELETE FROM annotations WHERE paper_id = :paper_id"),
                {"paper_id": paper_id}
            )
            print(f"已删除论文相关标注")
        except Exception as e:
            print(f"删除标注失败(忽略): {e}")
        
        # 更新concept_explanations表 - 使用TRY语句包装，避免表不存在错误
        try:
            db.execute(text("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'concept_explanations' AND column_name = 'paper_id'
                    ) THEN
                        UPDATE concept_explanations SET paper_id = NULL WHERE paper_id = :paper_id;
                    END IF;
                EXCEPTION WHEN undefined_table THEN
                    -- 表不存在，忽略错误
                END;
                $$
            """), {"paper_id": paper_id})
            print(f"已处理concept_explanations表关联")
        except Exception as e:
            print(f"处理concept_explanations表失败(忽略): {e}")
        
        # 删除论文-标签关联 (paper_tags表)
        try:
            db.execute(
                text("DELETE FROM paper_tags WHERE paper_id = :paper_id"),
                {"paper_id": paper_id}
            )
            print(f"已删除论文-标签关联")
        except Exception as e:
            print(f"删除论文-标签关联失败(忽略): {e}")
        
        # 删除论文-分类关联 (paper_categories表)
        try:
            db.execute(
                text("DELETE FROM paper_categories WHERE paper_id = :paper_id"),
                {"paper_id": paper_id}
            )
            print(f"已删除论文-分类关联")
        except Exception as e:
            print(f"删除论文-分类关联失败(忽略): {e}")
        
        # 更新experiments表关联
        try:
            db.execute(
                text("UPDATE experiments SET paper_id = NULL WHERE paper_id = :paper_id"),
                {"paper_id": paper_id}
            )
            print(f"已清除experiments表中的关联")
        except Exception as e:
            print(f"清除experiments表关联失败(忽略): {e}")
        
        # 处理任何其他可能的关联表 (冗余但安全的检查)
        # 查询所有引用papers表的外键
        try:
            fk_query = text("""
                SELECT tc.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_catalog = kcu.constraint_catalog
                  AND tc.constraint_schema = kcu.constraint_schema
                  AND tc.constraint_name = kcu.constraint_name
                JOIN information_schema.referential_constraints rc
                  ON tc.constraint_catalog = rc.constraint_catalog
                  AND tc.constraint_schema = rc.constraint_schema
                  AND tc.constraint_name = rc.constraint_name
                JOIN information_schema.table_constraints tc2
                  ON rc.unique_constraint_catalog = tc2.constraint_catalog
                  AND rc.unique_constraint_schema = tc2.constraint_schema
                  AND rc.unique_constraint_name = tc2.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc2.table_name = 'papers'
                AND kcu.column_name = 'paper_id';
            """)
            
            fk_results = db.execute(fk_query)
            for table_name, column_name in fk_results:
                if table_name not in ['notes', 'annotations', 'paper_tags', 'paper_categories', 'experiments']:
                    try:
                        # 如果是SET NULL外键，则更新为NULL
                        db.execute(
                            text(f"UPDATE {table_name} SET {column_name} = NULL WHERE {column_name} = :paper_id"),
                            {"paper_id": paper_id}
                        )
                        print(f"已清除表 {table_name} 中的关联")
                    except Exception as fk_error:
                        print(f"清除表 {table_name} 关联失败(忽略): {fk_error}")
        except Exception as fk_query_error:
            print(f"查询外键关系失败(忽略): {fk_query_error}")
        
        # 最后删除论文本身
        db.execute(
            text("DELETE FROM papers WHERE id = :paper_id AND owner_id = :user_id"),
            {"paper_id": paper_id, "user_id": user_id}
        )
        print(f"已删除论文记录")
        
        # 提交事务
        db.commit()
        print(f"删除论文成功: {paper_id}")
        return True
            
    except Exception as e:
        # 发生错误时回滚更改
        db.rollback()
        import traceback
        print(f"删除论文失败: {str(e)}")
        print(f"错误堆栈: {traceback.format_exc()}")
        # 继续抛出异常，以便上层处理
        raise e

# 标签操作
def get_tags(db: Session, user_id: str) -> List[Tuple[Tag, int]]:
    """获取用户的所有标签及每个标签的论文数量"""
    tags_with_count = db.query(
        Tag, 
        func.count(paper_tags.c.paper_id).label('paper_count')
    ).join(
        paper_tags, 
        Tag.id == paper_tags.c.tag_id
    ).join(
        Paper, 
        and_(
            Paper.id == paper_tags.c.paper_id,
            Paper.owner_id == user_id
        )
    ).filter(
        Tag.owner_id == user_id
    ).group_by(Tag.id).all()
    
    return tags_with_count

def create_tag(db: Session, name: str, color: Optional[str] = None) -> Tag:
    """创建新标签"""
    tag = Tag(id=str(uuid.uuid4()), name=name, color=color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag

def update_tag(db: Session, tag_id: str, name: Optional[str] = None, color: Optional[str] = None) -> Optional[Tag]:
    """更新标签信息"""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        return None
    
    if name:
        tag.name = name
    if color:
        tag.color = color
    
    db.commit()
    db.refresh(tag)
    return tag

def delete_tag(db: Session, tag_id: str) -> bool:
    """删除标签"""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        return False
    
    db.delete(tag)
    db.commit()
    return True

# 笔记操作
def get_notes_by_paper(db: Session, paper_id: str, user_id: str) -> List[Note]:
    """获取论文的所有笔记"""
    paper = get_paper_by_id(db, paper_id, user_id)
    if not paper:
        return []
    
    return paper.notes

def create_note(
    db: Session, 
    paper_id: str, 
    user_id: str,
    content: str,
    page_number: Optional[int] = None,
    position_data: Optional[Dict[str, Any]] = None
) -> Optional[Note]:
    """创建论文笔记"""
    paper = get_paper_by_id(db, paper_id, user_id)
    if not paper:
        return None
    
    note = Note(
        id=str(uuid.uuid4()),
        content=content,
        page_number=page_number,
        position_data=position_data,
        paper_id=paper_id
    )
    
    db.add(note)
    db.commit()
    db.refresh(note)
    return note

def update_note(
    db: Session, 
    note_id: str,
    user_id: str,
    update_data: Dict[str, Any]
) -> Optional[Note]:
    """更新笔记信息"""
    # 找到笔记及其所属论文
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        return None
    
    # 验证论文所有者
    paper = get_paper_by_id(db, note.paper_id, user_id)
    if not paper:
        return None
    
    # 更新字段
    for key, value in update_data.items():
        if hasattr(note, key):
            setattr(note, key, value)
    
    db.commit()
    db.refresh(note)
    return note

def delete_note(db: Session, note_id: str, user_id: str) -> bool:
    """删除笔记"""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        return False
    
    # 验证论文所有者
    paper = get_paper_by_id(db, note.paper_id, user_id)
    if not paper:
        return False
    
    db.delete(note)
    db.commit()
    return True

# 文件存储操作（保留这些函数的空壳以避免破坏兼容性）
def get_s3_client():
    """获取S3客户端（已废弃）"""
    print("警告：MinIO存储已被禁用，使用本地文件存储代替")
    return None

def upload_file_to_storage(file_path: str, content_type: str, file_data: bytes) -> str:
    """上传文件到存储（已废弃，改为本地存储）"""
    print("警告：MinIO存储已被禁用，使用本地文件存储代替")
    # 确保目录存在
    dir_path = os.path.dirname(file_path)
    if dir_path:
        os.makedirs(os.path.join("uploads", dir_path), exist_ok=True)
    local_path = os.path.join("uploads", file_path)
    with open(local_path, "wb") as f:
        f.write(file_data)
    return local_path

def delete_file_from_storage(file_path: str) -> bool:
    """从存储中删除文件（已废弃，改为本地删除）"""
    print("警告：MinIO存储已被禁用，使用本地文件存储代替")
    if file_path.startswith("uploads/"):
        if os.path.exists(file_path):
            os.unlink(file_path)
            return True
    return False

def get_file_from_storage(file_path: str) -> bytes:
    """从存储中获取文件内容（已废弃，改为本地读取）"""
    print("警告：MinIO存储已被禁用，使用本地文件存储代替")
    if file_path.startswith("uploads/"):
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                return f.read()
    elif os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return f.read()
    raise FileNotFoundError(f"文件未找到: {file_path}")

# 论文内容提取
def extract_paper_content(file_path: str) -> Tuple[str, Dict[str, Any]]:
    """从PDF文件中提取文本内容和元数据"""
    try:
        # 如果是文件路径
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                file_content = f.read()
        else:
            # 从存储中获取文件
            try:
                file_content = get_file_from_storage(file_path)
            except Exception as e:
                print(f"从存储获取文件失败: {e}")
                raise
        
        # 使用PyPDF读取PDF
        with io.BytesIO(file_content) as f:
            reader = pypdf.PdfReader(f)
            
            # 提取文本内容
            content = ""
            for page in reader.pages:
                page_text = page.extract_text() or ""
                # 删除空字符和控制字符
                page_text = ''.join(char for char in page_text if ord(char) >= 32 or char == '\n')
                content += page_text + "\n\n"
            
            # 提取元数据
            metadata = {}
            if reader.metadata:
                for key, value in reader.metadata.items():
                    if key.startswith('/'):
                        key = key[1:]
                    # 过滤元数据值中的无效字符
                    if isinstance(value, str):
                        value = ''.join(char for char in value if ord(char) >= 32 or char == '\n')
                    metadata[key] = value
            
            print(f"提取内容长度: {len(content)}, 元数据条目数: {len(metadata)}")
            return content, metadata
    except Exception as e:
        print(f"内容提取失败: {str(e)}")
        # 返回空内容而不是抛出异常，允许上传继续
        return "", {}

# 添加缺失的PDF提取函数
def extract_pdf_metadata(file_path: str) -> Dict[str, Any]:
    """提取PDF文件的元数据"""
    try:
        with open(file_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            metadata = {}
            if reader.metadata:
                for key, value in reader.metadata.items():
                    if key.startswith('/'):
                        key = key[1:]
                    if isinstance(value, str):
                        value = ''.join(char for char in value if ord(char) >= 32 or char == '\n')
                    metadata[key] = value
            return metadata
    except Exception as e:
        print(f"提取PDF元数据失败: {str(e)}")
        return {}

def extract_pdf_text(file_path: str) -> str:
    """提取PDF文件的文本内容，增强版"""
    try:
        import pypdf
        import re
        
        with open(file_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            
            # 获取总页数
            total_pages = len(reader.pages)
            print(f"PDF文件共有 {total_pages} 页")
            
            content = ""
            for page_num, page in enumerate(reader.pages):
                # 提取原始文本
                page_text = page.extract_text() or ""
                
                # 处理特殊字符
                page_text = ''.join(char for char in page_text if ord(char) >= 32 or char == '\n')
                
                # 尝试检测和处理分栏
                if '\n' in page_text:
                    lines = page_text.split('\n')
                    # 计算平均行长度
                    avg_line_len = sum(len(line) for line in lines) / max(1, len(lines))
                    # 如果平均行长度太短，可能是分栏，尝试合并
                    if avg_line_len < 40 and len(lines) > 15:
                        # 简单合并策略：尝试将偶数行和奇数行分别合并
                        page_text = _merge_columns(lines)
                
                # 去除页码和页眉/页脚
                page_text = _clean_page_text(page_text, page_num+1, total_pages)
                
                # 添加处理后的文本
                content += page_text + "\n\n"
            
            # 后处理：清理过多的空行、连字符等
            content = re.sub(r'\n{3,}', '\n\n', content)  # 替换多个连续空行为两个空行
            content = re.sub(r'(\w)-\n(\w)', r'\1\2', content)  # 处理连字符
            
            print(f"成功提取文本，总长度: {len(content)} 字符")
            return content
    except Exception as e:
        print(f"提取PDF文本内容失败: {str(e)}")
        print(f"错误堆栈: {traceback.format_exc()}")
        return ""

def _clean_page_text(text: str, page_num: int, total_pages: int) -> str:
    """清理页面文本，去除页码和页眉/页脚"""
    import re
    
    # 去除页码
    text = re.sub(rf'\b{page_num}\b', '', text)
    
    # 尝试识别和去除页眉/页脚
    lines = text.split('\n')
    if len(lines) > 10:  # 只在有足够行数的页面处理
        # 假设页眉是前1-2行，页脚是后1-3行
        inner_lines = lines[2:-3]
        # 如果页眉/页脚中含有论文ID、页码等，尝试去除
        common_patterns = [
            r'Page \d+ of \d+',
            r'\d+/\d+',
            r'©\d{4}',
            r'ISBN:',
            r'DOI:',
            r'Vol\.\s*\d+',
            r'No\.\s*\d+'
        ]
        
        # 去除页眉页脚中的通用模式
        for i in range(min(2, len(lines))):
            for pattern in common_patterns:
                lines[i] = re.sub(pattern, '', lines[i])
        
        for i in range(max(0, len(lines)-3), len(lines)):
            for pattern in common_patterns:
                if i < len(lines):  # 防止索引越界
                    lines[i] = re.sub(pattern, '', lines[i])
    
    return '\n'.join(lines)

def _merge_columns(lines: list) -> str:
    """尝试合并分栏内容"""
    # 估计每列的行数
    num_lines = len(lines)
    if num_lines < 10:  # 行数太少，可能不是分栏
        return '\n'.join(lines)
    
    # 分别处理奇数和偶数行，这是最简单的列合并方法
    left_column = []
    right_column = []
    mid_point = num_lines // 2
    
    for i, line in enumerate(lines):
        if i < mid_point:
            left_column.append(line)
        else:
            right_column.append(line)
    
    # 合并两列
    merged_text = ""
    for i in range(min(len(left_column), len(right_column))):
        if left_column[i].strip() and right_column[i].strip():
            # 两列都有内容，合并
            merged_text += left_column[i] + " " + right_column[i] + "\n"
        else:
            # 任一列为空，使用非空列
            merged_text += (left_column[i] if left_column[i].strip() else right_column[i]) + "\n"
    
    # 添加剩余行
    if len(left_column) > len(right_column):
        for i in range(len(right_column), len(left_column)):
            merged_text += left_column[i] + "\n"
    elif len(right_column) > len(left_column):
        for i in range(len(left_column), len(right_column)):
            merged_text += right_column[i] + "\n"
    
    return merged_text

def upload_to_minio(file_path: str, object_name: str) -> str:
    """上传文件到MinIO存储（这里改为本地存储）"""
    # 确保上传目录存在
    upload_dir = os.path.join("uploads", os.path.dirname(object_name))
    os.makedirs(upload_dir, exist_ok=True)
    
    # 复制文件到上传目录
    upload_path = os.path.join("uploads", object_name)
    shutil.copy2(file_path, upload_path)
    
    return upload_path

# 论文上传处理
async def upload_paper_file(
    db: Session,
    file: UploadFile,
    user_id: str,
    title: Optional[str] = None,
    extract_content: bool = True,
    analyze_content: bool = False,
    folder_id: Optional[str] = None,
    category_ids: Optional[List[str]] = None
) -> Paper:
    """上传论文文件并提取内容"""
    # 确保数据库中存在analysis_progress字段
    try:
        # 首先检查字段是否存在
        db.execute(text("ALTER TABLE papers ADD COLUMN IF NOT EXISTS analysis_progress INTEGER DEFAULT 0"))
        db.commit()
    except Exception as e:
        print(f"添加analysis_progress字段时出错: {str(e)}")
        # 错误不影响继续执行
    
    # 保存文件到临时位置
    temp_file_id = str(uuid.uuid4())
    temp_file_path = os.path.join("temp", f"{temp_file_id}.pdf")
    
    # 创建临时目录（如果不存在）
    os.makedirs("temp", exist_ok=True)
    
    try:
        # 写入临时文件
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"临时文件保存到: {temp_file_path}")
        
        # 提取文件元数据
        file_metadata = {}
        try:
            file_metadata = extract_pdf_metadata(temp_file_path)
            print(f"提取到PDF元数据: {file_metadata}")
        except Exception as metadata_error:
            print(f"提取PDF元数据失败: {str(metadata_error)}")
        
        # 从元数据中提取论文标题（如果未提供）
        if not title and file_metadata.get('Title'):
            title = file_metadata.get('Title')
        
        # 如果仍然没有标题，使用文件名
        if not title:
            title = file.filename.rsplit('.', 1)[0] if '.' in file.filename else file.filename
        
        print(f"使用标题: {title}")
        
        # 提取PDF内容（如果需要）
        content = None
        if extract_content:
            try:
                content = extract_pdf_text(temp_file_path)
                print(f"提取到PDF内容: {len(content)} 字符")
            except Exception as extract_error:
                print(f"提取PDF内容失败: {str(extract_error)}")
        
        # 获取文件大小
        file_size = os.path.getsize(temp_file_path)
        
        # 上传到存储
        try:
            file_path = upload_to_minio(temp_file_path, f"papers/{user_id}/{temp_file_id}.pdf")
            print(f"文件上传到存储: {file_path}")
        except Exception as storage_error:
            print(f"上传到存储失败: {str(storage_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"上传文件到存储服务失败: {str(storage_error)}"
            )
        
        # 创建缩略图（异步进行，不影响主流程）
        thumbnail_path = None
        
        # 创建论文记录 - 正确调用create_paper函数
        try:
            paper = create_paper(
                db=db,
                user_id=user_id,
                title=title,
                content=content,
                file_path=file_path,
                thumbnail_path=thumbnail_path,
                file_size=file_size,
                metadata=file_metadata,
                source="upload"
            )
            print(f"论文记录创建成功: {paper.id}")
        except Exception as db_error:
            print(f"创建论文记录失败: {str(db_error)}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建论文记录失败: {str(db_error)}"
            )
        
        # 如果提供了分类ID，添加到论文的分类中
        if category_ids:
            for category_id in category_ids:
                category = db.query(Category).filter(
                    Category.id == category_id,
                    Category.owner_id == user_id
                ).first()
                
                if category:
                    paper.categories.append(category)
            
            db.commit()
        
        # 更新文件夹ID（如果提供）
        if folder_id and folder_id != paper.folder_id:
            paper.folder_id = folder_id
            db.commit()
        
        # 如果需要分析内容，启动异步分析任务
        if analyze_content and content:
            # 这里可以启动异步任务
            pass
        
        return paper
    finally:
        # 清理临时文件
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"已删除临时文件: {temp_file_path}")

# 论文文件下载
async def get_paper_file(db: Session, paper_id: str, user_id: str):
    """获取论文文件或内容"""
    paper = get_paper_by_id(db, paper_id, user_id)
    if not paper:
        print(f"未找到论文 ID: {paper_id}")
        return None
    
    try:
        # 检查是否有文件路径
        if paper.file_path and os.path.exists(paper.file_path):
            print(f"找到论文文件路径: {paper.file_path}")
            # 返回本地文件路径
            return {
                "file_type": "local",
                "file_path": paper.file_path,
                "file_name": Path(paper.file_path).name,
                "content_type": "application/pdf"
            }
        else:
            # 如果没有文件但有内容，生成临时PDF
            if paper.content:
                print(f"论文没有原始文件，但有内容，尝试生成PDF")
                # 确保临时目录存在
                os.makedirs(settings.TEMP_DIR, exist_ok=True)
                temp_file_name = f"{uuid.uuid4()}.pdf"
                temp_file_path = os.path.join(settings.TEMP_DIR, temp_file_name)
                print(f"临时PDF文件路径: {temp_file_path}")
                
                # 生成一个简单的PDF文件
                try:
                    from reportlab.lib.pagesizes import letter
                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                    from reportlab.lib.styles import getSampleStyleSheet
                    
                    doc = SimpleDocTemplate(temp_file_path, pagesize=letter)
                    styles = getSampleStyleSheet()
                    story = []
                    
                    # 添加标题
                    print(f"添加论文标题到PDF: {paper.title}")
                    story.append(Paragraph(paper.title, styles['Title']))
                    story.append(Spacer(1, 12))
                    
                    # 添加作者信息
                    if paper.authors and isinstance(paper.authors, list):
                        print(f"添加作者信息到PDF")
                        authors_text = ", ".join([author.get('name', '') for author in paper.authors])
                        story.append(Paragraph(authors_text, styles['Normal']))
                        story.append(Spacer(1, 12))
                    
                    # 添加摘要
                    if paper.abstract:
                        print(f"添加摘要到PDF")
                        story.append(Paragraph("<b>摘要</b>", styles['Heading2']))
                        story.append(Paragraph(paper.abstract, styles['Normal']))
                        story.append(Spacer(1, 12))
                    
                    # 添加内容
                    print(f"添加论文内容到PDF，内容长度: {len(paper.content)}")
                    content_paragraphs = paper.content.split('\n\n')
                    for paragraph in content_paragraphs[:100]:  # 限制段落数量避免过大
                        if paragraph.strip():
                            story.append(Paragraph(paragraph, styles['Normal']))
                            story.append(Spacer(1, 6))
                    
                    print(f"开始构建PDF文档")
                    doc.build(story)
                    print(f"PDF生成成功: {temp_file_path}")
                    
                    # 返回生成的PDF
                    return {
                        "file_type": "temp",
                        "file_path": temp_file_path,
                        "file_name": f"{paper.title}.pdf",
                        "content_type": "application/pdf"
                    }
                except Exception as e:
                    print(f"生成PDF失败，详细错误: {str(e)}")
                    import traceback
                    print(f"错误堆栈: {traceback.format_exc()}")
                    
                    # 如果生成PDF失败，返回纯文本
                    return {
                        "file_type": "content",
                        "content": paper.content,
                        "file_name": f"{paper.title}.txt",
                        "content_type": "text/plain"
                    }
            else:
                # 既没有文件也没有内容
                print(f"论文既没有文件也没有内容: {paper_id}")
                return None
    except Exception as e:
        print(f"获取文件失败: {str(e)}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
        return None

# 添加新的函数以支持前端
def get_user_papers(
    db: Session,
    user_id: str,
    query: Optional[str] = None,
    tags: Optional[List[str]] = None,
    favorite: Optional[bool] = None,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    skip: int = 0,
    limit: int = 20
) -> Tuple[List[Paper], int]:
    """获取用户的论文列表及总数"""
    paper_query = db.query(Paper).filter(Paper.owner_id == user_id)
    
    # 搜索
    if query:
        search = f"%{query}%"
        paper_query = paper_query.filter(
            or_(
                Paper.title.ilike(search),
                Paper.abstract.ilike(search),
                Paper.content.ilike(search),
            )
        )
    
    # 标签过滤
    if tags:
        for tag_name in tags:
            paper_query = paper_query.filter(Paper.tags.any(Tag.name == tag_name))
    
    # 收藏过滤
    if favorite is not None:
        paper_query = paper_query.filter(Paper.is_favorite == favorite)
    
    # 计算总数
    total = paper_query.count()
    
    # 排序
    if sort_order.lower() == "desc":
        paper_query = paper_query.order_by(desc(getattr(Paper, sort_by)))
    else:
        paper_query = paper_query.order_by(asc(getattr(Paper, sort_by)))
    
    # 分页
    papers = paper_query.offset(skip).limit(limit).all()
    
    return papers, total 