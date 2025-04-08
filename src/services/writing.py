from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
import uuid
import json
from datetime import datetime, timedelta
import os
import asyncio
from pathlib import Path
import logging

# 使用相对导入
from src.models.writing import WritingProject, WritingSection, CollaborationInvite, ProjectStatus
from src.models.user import User
from src.models.paper import Paper, Tag
from src.core.deps import get_db
from src.core.config import settings
from src.services import ai_assistant as assistant_service

def get_project_by_id(db: Session, project_id: str, user_id: Optional[str] = None) -> Optional[WritingProject]:
    """通过ID获取写作项目"""
    query = db.query(WritingProject).filter(WritingProject.id == project_id)
    if user_id:
        query = query.filter(
            (WritingProject.owner_id == user_id) | 
            (WritingProject.collaborators.any(User.id == user_id))
        )
    return query.first()

def get_projects(
    db: Session, 
    user_id: str, 
    skip: int = 0, 
    limit: int = 100,
    query: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    include_collaborated: bool = True
) -> List[WritingProject]:
    """获取用户的写作项目列表"""
    if include_collaborated:
        project_query = db.query(WritingProject).filter(
            (WritingProject.owner_id == user_id) | 
                    (WritingProject.collaborators.any(User.id == user_id))
        )
    else:
        project_query = db.query(WritingProject).filter(WritingProject.owner_id == user_id)
    
    # 如果有搜索字符串
    if query:
        search = f"%{query}%"
        project_query = project_query.filter(
            (WritingProject.title.ilike(search)) |
            (WritingProject.description.ilike(search))
        )
    
    # 排序
    if sort_order.lower() == "desc":
        project_query = project_query.order_by(desc(getattr(WritingProject, sort_by)))
    else:
        project_query = project_query.order_by(asc(getattr(WritingProject, sort_by)))
    
    return project_query.offset(skip).limit(limit).all()

def create_project(
    db: Session, 
    owner_id: str,
    title: str,
    description: Optional[str] = None,
    template: Optional[str] = None,
    related_papers: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> WritingProject:
    """创建新写作项目"""
    # 构建项目描述，包括用户提供的描述和元数据（如相关论文）
    project_desc = description or ""
    
    # 如果有元数据或相关论文，添加到描述中
    meta_info = {}
    if metadata:
        meta_info.update(metadata)
    if related_papers:
        meta_info['related_papers'] = related_papers
    
    if meta_info:
        # 如果有元数据，添加到描述末尾（使用JSON格式）
        import json
        if project_desc:
            project_desc += "\n\n<!-- METADATA: " + json.dumps(meta_info) + " -->"
        else:
            project_desc = "<!-- METADATA: " + json.dumps(meta_info) + " -->"
    
    project = WritingProject(
        id=str(uuid.uuid4()),
        owner_id=owner_id,
        title=title,
        description=project_desc,
        status=ProjectStatus.DRAFT
    )
    
    db.add(project)
    
    # 如果有模板，创建初始章节
    if template:
        if template == "research_paper":
            sections = [
                {"title": "摘要", "order": 0, "content": ""},
                {"title": "介绍", "order": 1, "content": ""},
                {"title": "相关工作", "order": 2, "content": ""},
                {"title": "方法", "order": 3, "content": ""},
                {"title": "实验", "order": 4, "content": ""},
                {"title": "结果", "order": 5, "content": ""},
                {"title": "讨论", "order": 6, "content": ""},
                {"title": "结论", "order": 7, "content": ""},
                {"title": "参考文献", "order": 8, "content": ""}
            ]
        elif template == "thesis":
            sections = [
                {"title": "摘要", "order": 0, "content": ""},
                {"title": "第1章 绪论", "order": 1, "content": ""},
                {"title": "第2章 文献综述", "order": 2, "content": ""},
                {"title": "第3章 研究方法", "order": 3, "content": ""},
                {"title": "第4章 研究结果", "order": 4, "content": ""},
                {"title": "第5章 分析与讨论", "order": 5, "content": ""},
                {"title": "第6章 结论与展望", "order": 6, "content": ""},
                {"title": "参考文献", "order": 7, "content": ""}
            ]
        elif template == "report":
            sections = [
                {"title": "摘要", "order": 0, "content": ""},
                {"title": "背景", "order": 1, "content": ""},
                {"title": "目标", "order": 2, "content": ""},
                {"title": "方法", "order": 3, "content": ""},
                {"title": "发现", "order": 4, "content": ""},
                {"title": "建议", "order": 5, "content": ""},
                {"title": "结论", "order": 6, "content": ""}
            ]
        else:
            sections = []
        
        for section_data in sections:
            section = WritingSection(
                id=str(uuid.uuid4()),
                project_id=project.id,
                title=section_data["title"],
                order=section_data["order"],
                content=section_data["content"]
            )
            db.add(section)
    
    db.commit()
    db.refresh(project)
    return project

def update_project(
    db: Session, 
    project_id: str, 
    user_id: str, 
    update_data: Dict[str, Any]
) -> Optional[WritingProject]:
    """更新写作项目信息"""
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        return None
    
    # 只有所有者可以更新项目的某些字段
    is_owner = project.owner_id == user_id
    
    # 如果不是所有者，移除敏感字段
    if not is_owner:
        for field in ["owner_id", "collaborators"]:
            if field in update_data:
                del update_data[field]
    
    # 更新其他字段
    for key, value in update_data.items():
        if hasattr(project, key):
            setattr(project, key, value)
    
    db.commit()
    db.refresh(project)
    return project

def delete_project(db: Session, project_id: str, user_id: str) -> bool:
    """删除写作项目"""
    project = get_project_by_id(db, project_id, user_id)
    if not project or project.owner_id != user_id:
        return False
    
    # 删除相关章节
    db.query(WritingSection).filter(WritingSection.project_id == project_id).delete()
    
    # 删除协作邀请
    db.query(CollaborationInvite).filter(CollaborationInvite.project_id == project_id).delete()
    
    db.delete(project)
    db.commit()
    return True

# 章节操作
def get_section_by_id(db: Session, section_id: str, user_id: str) -> Optional[WritingSection]:
    """通过ID获取章节"""
    section = db.query(WritingSection).filter(WritingSection.id == section_id).first()
    if not section:
        return None
    
    # 验证用户是否有权访问该章节的项目
    project = get_project_by_id(db, section.project_id, user_id)
    if not project:
        return None
    
    return section

def get_sections(db: Session, project_id: str, user_id: str) -> List[WritingSection]:
    """获取项目的所有章节"""
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        return []
    
    return db.query(WritingSection).filter(
        WritingSection.project_id == project_id
    ).order_by(WritingSection.order).all()

def create_section(
    db: Session, 
    project_id: str, 
    user_id: str,
    title: str,
    content: str = "",
    order: Optional[int] = None
) -> Optional[WritingSection]:
    """创建项目章节"""
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        return None
    
    # 如果未指定顺序，则放在最后
    if order is None:
        last_section = db.query(WritingSection).filter(
            WritingSection.project_id == project_id
        ).order_by(desc(WritingSection.order)).first()
        
        if last_section:
            order = last_section.order + 1
        else:
            order = 0
    
    section = WritingSection(
        id=str(uuid.uuid4()),
        project_id=project_id,
        title=title,
        content=content,
        order=order
    )
    
    db.add(section)
    db.commit()
    db.refresh(section)
    return section

def update_section(
    db: Session, 
    section_id: str,
    user_id: str,
    update_data: Dict[str, Any]
) -> Optional[WritingSection]:
    """更新章节信息"""
    section = get_section_by_id(db, section_id, user_id)
    if not section:
        return None
    
    # 更新字段
    for key, value in update_data.items():
        if hasattr(section, key):
            setattr(section, key, value)
    
    # 如果更新了顺序，需要调整其他章节
    if "order" in update_data:
        reorder_sections(db, section.project_id)
    
    db.commit()
    db.refresh(section)
    return section

def delete_section(db: Session, section_id: str, user_id: str) -> bool:
    """删除章节"""
    section = get_section_by_id(db, section_id, user_id)
    if not section:
        return False
    
    project_id = section.project_id
    db.delete(section)
    db.commit()
    
    # 重新排序剩余章节
    reorder_sections(db, project_id)
    
    return True

def reorder_sections(db: Session, project_id: str) -> None:
    """重新排序项目章节"""
    sections = db.query(WritingSection).filter(
        WritingSection.project_id == project_id
    ).order_by(WritingSection.order).all()
    
    for i, section in enumerate(sections):
        if section.order != i:
            section.order = i
    
    db.commit()

# 协作相关操作
def invite_collaborator(
    db: Session, 
    project_id: str, 
    owner_id: str, 
    collaborator_email: str,
    message: Optional[str] = None
) -> Optional[CollaborationInvite]:
    """邀请协作者加入项目"""
    # 验证项目所有权
    project = get_project_by_id(db, project_id, owner_id)
    if not project or project.owner_id != owner_id:
        return None
    
    # 查找被邀请用户
    user = db.query(User).filter(User.email == collaborator_email).first()
    
    # 创建邀请
    invite = CollaborationInvite(
        id=str(uuid.uuid4()),
        project_id=project_id,
        inviter_id=owner_id,
        invitee_email=collaborator_email,
        invitee_id=user.id if user else None,
        message=message,
        status="pending",
        expires_at=datetime.now() + timedelta(days=7)
    )
    
    db.add(invite)
    db.commit()
    db.refresh(invite)
    
    # TODO: 发送邀请邮件
    
    return invite

def accept_invitation(db: Session, invite_id: str, user_id: str) -> bool:
    """接受协作邀请"""
    invite = db.query(CollaborationInvite).filter(
        CollaborationInvite.id == invite_id,
        (CollaborationInvite.invitee_id == user_id) |
        (CollaborationInvite.invitee_email == db.query(User).filter(User.id == user_id).first().email)
    ).first()
    
    if not invite or invite.status != "pending" or invite.expires_at < datetime.now():
        return False
    
    # 更新邀请状态
    invite.status = "accepted"
    invite.responded_at = datetime.now()
    
    # 将用户添加为协作者
    project = get_project_by_id(db, invite.project_id)
    if not project:
        return False
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    if user not in project.collaborators:
        project.collaborators.append(user)
    
    db.commit()
    return True

def reject_invitation(db: Session, invite_id: str, user_id: str) -> bool:
    """拒绝协作邀请"""
    invite = db.query(CollaborationInvite).filter(
        CollaborationInvite.id == invite_id,
        (CollaborationInvite.invitee_id == user_id) |
        (CollaborationInvite.invitee_email == db.query(User).filter(User.id == user_id).first().email)
    ).first()
    
    if not invite or invite.status != "pending":
        return False
    
    invite.status = "rejected"
    invite.responded_at = datetime.now()
    
    db.commit()
    return True

def remove_collaborator(db: Session, project_id: str, owner_id: str, collaborator_id: str) -> bool:
    """从项目中移除协作者"""
    project = get_project_by_id(db, project_id, owner_id)
    if not project or project.owner_id != owner_id:
        return False
    
    user = db.query(User).filter(User.id == collaborator_id).first()
    if not user:
        return False
    
    if user in project.collaborators:
        project.collaborators.remove(user)
        db.commit()
        return True
    
    return False

# AI 辅助写作
async def generate_section_content(
    db: Session,
    section_id: str,
    user_id: str,
    prompt: str,
    paper_id: Optional[str] = None
) -> Optional[str]:
    """使用AI生成章节内容"""
    section = get_section_by_id(db, section_id, user_id)
    if not section:
        return None
    
    project = get_project_by_id(db, section.project_id, user_id)
    if not project:
        return None
    
    # 构建上下文
    context = f"项目标题: {project.title}\n"
    if project.description:
        context += f"项目描述: {project.description}\n"
    
    context += f"当前章节: {section.title}\n"
    if section.content:
        context += f"当前内容: {section.content}\n"
    
    # 获取其他章节标题作为参考
    other_sections = get_sections(db, project.id, user_id)
    if other_sections:
        context += "其他章节:\n"
        for s in other_sections:
            if s.id != section.id:
                context += f"- {s.title}\n"
    
    # 如果指定了相关论文，获取其内容
    paper_content = ""
    if paper_id:
        from src.services import paper as paper_service
        paper = paper_service.get_paper_by_id(db, paper_id, user_id)
        if paper and paper.content:
            paper_content = f"参考论文: {paper.title}\n{paper.content[:5000]}...\n"
    
    # 调用AI助手
    try:
        # 这里使用OpenAI API生成内容
        # 注意: 这里直接调用API而不是通过assistant_service
        # 以避免循环导入的问题
        
        # 构建完整提示词
        full_prompt = f"""
        请根据以下信息和提示生成学术写作内容。
        
        {context}
        
        {paper_content if paper_content else ''}
        
        用户提示: {prompt}
        
        请生成适合{section.title}章节的内容。内容应该学术性强，逻辑清晰，符合该类型文档的写作规范。
        """
        
        # 直接调用OpenAI API
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.OPENAI_API_BASE}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
                },
                json={
                    "model": settings.OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": "你是一个专业的学术写作助手，擅长生成高质量的学术内容。"},
                        {"role": "user", "content": full_prompt}
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.4
                },
                timeout=60.0
            )
            
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"].strip()
            
            # 更新章节内容
            if section.content:
                section.content += "\n\n" + content
            else:
                section.content = content
            
            db.commit()
            db.refresh(section)
            
            return content
            
    except Exception as e:
        raise Exception(f"生成内容失败: {str(e)}")

async def improve_writing(
    db: Session,
    section_id: str,
    user_id: str,
    improvement_type: str
) -> Optional[str]:
    """改进写作内容"""
    section = get_section_by_id(db, section_id, user_id)
    if not section or not section.content:
        return None
    
    # 根据不同改进类型构建提示词
    prompts = {
        "grammar": "请修正以下文本中的语法错误，确保语言流畅、正确。不要改变原文的含义。",
        "clarity": "请改进以下文本以增强其清晰度和可读性。使表达更加直接、精确，减少冗余和复杂性。",
        "academic": "请将以下文本改写为更学术、更正式的风格。使用适当的学术术语，保持客观、精确的语言。",
        "concise": "请将以下文本改写得更加简洁。去除不必要的词汇和冗余表达，但保留所有重要信息。",
        "expand": "请扩展以下文本，添加更多细节、解释和论证。使内容更加全面、深入，但保持连贯性。"
    }
    
    prompt = prompts.get(improvement_type, "请改进以下文本，提高其质量和专业性。")
    
    try:
        # 调用OpenAI API
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.OPENAI_API_BASE}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
                },
                json={
                    "model": settings.OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": "你是一个专业的学术写作助手，擅长改进学术文本。"},
                        {"role": "user", "content": f"{prompt}\n\n{section.content}"}
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.3
                },
                timeout=60.0
            )
            
            response_data = response.json()
            improved_content = response_data["choices"][0]["message"]["content"].strip()
            
            # 更新章节内容
            section.content = improved_content
            db.commit()
            db.refresh(section)
            
            return improved_content
            
    except Exception as e:
        raise Exception(f"改进内容失败: {str(e)}")

def export_project(db: Session, project_id: str, user_id: str, format: str = "markdown") -> Dict[str, Any]:
    """导出写作项目"""
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        raise ValueError("项目未找到或无权访问")
    
    sections = get_sections(db, project_id, user_id)
    
    if format == "markdown":
        content = f"# {project.title}\n\n"
        if project.description:
            content += f"{project.description}\n\n"
        
        for section in sections:
            content += f"## {section.title}\n\n{section.content}\n\n"
        
        return {
            "project_id": project.id,
            "title": project.title,
            "format": "markdown",
            "content": content,
            "filename": f"{project.title.replace(' ', '_')}.md"
        }
    
    elif format == "json":
        sections_data = []
        for section in sections:
            sections_data.append({
                "id": section.id,
                "title": section.title,
                "order": section.order,
                "content": section.content
            })
        
        data = {
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
            "owner_id": project.owner_id,
            "sections": sections_data
        }
        
        return {
            "project_id": project.id,
            "title": project.title,
            "format": "json",
            "content": json.dumps(data, indent=2),
            "filename": f"{project.title.replace(' ', '_')}.json"
        }
    
    else:
        raise ValueError(f"不支持的导出格式: {format}")

async def generate_writing_prompt(
    prompt_type: str,
    context: Optional[str] = None,
    references: Optional[List[Dict[str, Any]]] = None,
    style: str = "academic",
    custom_requirements: Optional[str] = None,
    project: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    生成写作提示
    
    参数:
        prompt_type: 提示类型，如'introduction', 'methodology'等
        context: 用户提供的上下文信息
        references: 参考文献列表
        style: 写作风格
        custom_requirements: 自定义要求
        project: 相关项目信息
        
    返回:
        包含生成提示和建议的字典
    """
    # 构建提示模板
    prompt_templates = {
        "introduction": {
            "description": "论文引言部分的写作提示",
            "template": """
请为一篇{research_area}领域的高水平学术论文撰写专业引言部分。
论文标题：{title}

引言部分必须符合以下学术要求：

1. 研究背景：
   - 简明扼要介绍{research_area}领域的研究背景和重要性
   - 使用精准的学术语言描述该领域的发展历程
   - 引用至少3-5篇该领域近期顶会/顶刊论文支持你的叙述

2. 问题陈述：
   - 清晰界定本研究关注的具体问题和挑战
   - 通过文献证据说明该问题的重要性和复杂性
   - 分析现有方法在解决该问题时面临的具体技术瓶颈

3. 主流方法分析：
   - 简明概述解决该问题的主流技术路线
   - 对现有方法进行批判性分析，精确指出其局限性
   - 所有分析必须基于可验证的文献依据，避免主观臆断

4. 研究贡献：
   - 明确列出本研究的2-4项具体贡献
   - 每项贡献必须具体、可验证且有技术深度
   - 避免过度宣传，确保贡献描述准确客观
   - 强调本研究与现有工作的渐进式关联性

5. 技术路线概述：
   - 简要说明本研究采用的方法论和技术路线
   - 解释方法选择的科学依据和理论基础
   - 展示方法与研究问题之间的逻辑关联

6. 论文结构：
   - 简洁概述论文各部分的内容和安排
   - 确保结构符合{research_area}领域高质量论文的标准格式

{context_info}
{reference_info}
{custom_info}

请使用{style}风格，确保引言生动且专业，吸引读者深入阅读全文，但避免不必要的修饰词和过度宣传。实际内容应围绕具体的研究问题和方法展开，避免空泛的表述。
            """
        },
        "methodology": {
            "description": "论文方法部分的写作提示",
            "template": """
请为一篇{research_area}领域的高水平学术论文撰写专业的方法论部分。
论文标题：{title}

方法部分必须符合以下严格学术标准：

1. 方法概述：
   - 提供方法的整体框架和技术路线图
   - 明确阐述各组件之间的逻辑关系和数据流
   - 解释方法设计与研究问题之间的逻辑对应关系
   - 说明方法的理论基础和科学原理

2. 技术细节：
   - 使用精确的数学符号和标准学术术语
   - 提供完整的算法描述或系统架构设计
   - 详细解释关键技术组件的工作机理
   - 包含关键算法的伪代码或流程图
   - 提供必要的数学推导和理论证明

3. 创新点详解：
   - 明确指出哪些部分是对已有方法的改进
   - 详细解释每个创新点的技术原理和具体实现
   - 分析创新点如何解决现有方法的特定局限
   - 说明创新点与已有技术的兼容性和集成方式

4. 方法论证：
   - 解释为何所选方法适合解决目标问题
   - 分析方法的理论优势和技术特点
   - 讨论方法的适用条件和局限性
   - 提供与其他可能方法的比较分析

5. 实现细节：
   - 描述算法实现的技术细节和工程考量
   - 说明关键参数的设计选择和调优策略
   - 讨论可能的实现挑战和解决方案
   - 提供复杂度分析（时间复杂度和空间复杂度）

{context_info}
{reference_info}
{custom_info}

请使用{style}风格，确保内容严谨、专业且详尽。方法描述应当清晰明了，使读者能够理解技术原理并复现研究结果。必须避免模糊不清的描述和含混不定的术语，保持专业学术标准。
            """
        },
        "related_work": {
            "description": "论文相关工作部分的写作提示",
            "template": """
请为一篇{research_area}领域的高水平学术论文撰写专业的相关工作部分。
论文标题：{title}

相关工作部分必须达到以下学术标准：

1. 研究脉络分析：
   - 系统梳理{research_area}领域的研究发展脉络
   - 识别并归纳主要的技术路线和方法类别
   - 根据技术相关性和时间线组织文献，而非简单罗列

2. 分类框架：
   - 采用合理的分类方式组织相关文献
   - 每类方法都应包含代表性工作和最新进展
   - 展示类别之间的关系和技术演进路径
   - 突出与本研究直接相关的方法类别

3. 方法对比：
   - 对每类方法进行深入的技术分析和比较
   - 精确指出各类方法的技术原理、优势和局限
   - 分析评论必须基于文献证据，避免主观判断
   - 使用表格或其他结构化方式进行系统性比较

4. 研究缺口识别：
   - 通过文献分析识别现有方法的具体技术缺口
   - 论证这些缺口的重要性和解决的必要性
   - 说明本研究如何针对这些缺口进行改进
   - 确保缺口分析基于充分的文献证据

5. 与本研究的关系：
   - 明确定位本研究在已有工作中的位置
   - 说明本研究与现有方法的关系（扩展、改进或整合）
   - 解释本研究如何受到现有工作的启发并进一步发展
   - 强调本研究的差异性和创新性，但避免贬低他人工作

{context_info}
{reference_info}
{custom_info}

请使用{style}风格，确保内容全面、客观且有深度。引用应当准确，讨论应当公正。避免简单罗列文献，而应当提供有见地的分析和比较。相关工作部分应当为你的研究创新提供合理的学术背景和理论基础。
            """
        },
        "results": {
            "description": "论文结果部分的写作提示",
            "template": """
请为一篇{research_area}领域的高水平学术论文撰写专业的实验结果部分。
论文标题：{title}

实验结果部分必须符合以下严格学术标准：

1. 实验设置回顾：
   - 简要回顾实验目标和评估方法
   - 列出使用的评估数据集及其关键特性
   - 确认评估指标及其计算方法
   - 说明基线方法的选择理由和实现细节

2. 主要结果呈现：
   - 使用结构化的表格呈现关键量化结果
   - 包含均值和方差/标准差等统计信息
   - 突出显示最佳性能和显著改进
   - 进行适当的统计显著性测试
   - 确保结果的可重现性和可靠性

3. 详细性能分析：
   - 深入分析性能提升的原因和模式
   - 识别方法在不同场景下的表现差异
   - a对比分析与基线方法的性能差异
   - 提供细致的错误分析和案例研究

4. 消融实验：
   - 设计全面的消融实验验证各组件贡献
   - 量化每个创新点对整体性能的影响
   - 分析组件间的相互作用和协同效果
   - 验证关键设计选择的必要性和有效性

5. 参数敏感性分析：
   - 分析关键参数对模型性能的影响
   - 研究模型在不同参数设置下的稳定性
   - 提供参数选择的指导和最佳实践建议
   - 确保结果的稳健性和可靠性

6. 可视化和解释性分析：
   - 提供直观的可视化展示关键结果
   - 使用案例研究说明方法的工作机制
   - 分析方法的决策过程和中间结果
   - 增强对方法工作原理的理解

{context_info}
{reference_info}
{custom_info}

请使用{style}风格，确保内容客观、严谨且详尽。结果呈现应当简洁明了，使用专业的描述语言，避免主观臆断。所有结论必须直接基于实验数据，而非推测。图表应当信息丰富，标注清晰，便于读者理解。
            """
        },
        "discussion": {
            "description": "论文讨论部分的写作提示",
            "template": """
请为一篇{research_area}领域的高水平学术论文撰写专业的讨论部分。
论文标题：{title}

讨论部分必须达到以下学术标准：

1. 结果解释与意义：
   - 深入解释实验结果的学术意义和实际价值
   - 分析结果如何验证或支持研究假设
   - 讨论结果的理论意义和实践应用价值
   - 将结果与研究目标和问题陈述相关联

2. 理论分析与见解：
   - 提供对结果的理论解释和分析框架
   - 讨论结果与现有理论模型的一致性或差异
   - 探讨结果揭示的新模式或规律
   - 提出可能的理论扩展或修正建议

3. 方法优势与创新：
   - 基于实验证据分析方法的技术优势
   - 讨论创新点如何有效解决研究问题
   - 对比分析与现有方法的质量差异
   - 探讨方法的泛化能力和适用范围

4. 局限性分析：
   - 客观分析研究方法和结果的局限性
   - 讨论可能影响结果有效性的因素
   - 提出可能的改进方向和解决策略
   - 展示对研究不足的清醒认识和学术诚实

5. 未来研究方向：
   - 基于当前研究提出有价值的后续研究方向
   - 讨论值得进一步探索的关键问题和挑战
   - 提出可能的技术改进和方法扩展
   - 展望研究领域的潜在发展趋势

6. 更广泛的影响与应用：
   - 讨论研究成果对相关领域的潜在影响
   - 探讨研究方法在其他问题上的应用可能
   - 分析成果对学术界和工业界的价值
   - 提出实际应用的可能路径和策略

{context_info}
{reference_info}
{custom_info}

请使用{style}风格，确保讨论深入、全面且有见地。避免简单重复结果，而应当提供有深度的分析和洞见。讨论应保持客观平衡，既肯定成果又承认局限，展现学术成熟度和严谨性。
            """
        },
        "conclusion": {
            "description": "论文结论部分的写作提示",
            "template": """
请为一篇{research_area}领域的高水平学术论文撰写专业的结论部分。
论文标题：{title}

结论部分必须符合以下学术标准：

1. 研究总结：
   - 简洁精炼地概括研究的核心问题和目标
   - 归纳本研究的关键技术方法和创新点
   - 总结主要实验结果和性能提升
   - 确保与论文其他部分保持一致性

2. 主要贡献强调：
   - 明确列举本研究的2-4项具体学术贡献
   - 解释每项贡献的学术价值和技术意义
   - 说明贡献如何推进{research_area}领域的发展
   - 强调贡献的原创性和重要性，但避免夸大

3. 理论与实践意义：
   - 分析研究成果对学术理论的启示
   - 讨论研究方法的实践应用前景
   - 阐述成果如何解决实际问题或改进现有系统
   - 说明研究如何弥合理论与实践的差距

4. 局限与展望：
   - 简明指出研究的主要局限性
   - 提出2-3个有价值的未来研究方向
   - 展望技术的潜在演进路径
   - 为后续研究提供清晰的指引

{context_info}
{reference_info}
{custom_info}

请使用{style}风格，确保结论简洁有力，突出核心要点。结论应当既回顾过去又展望未来，为整篇论文画上完美的句号。避免引入新的信息或论点，保持与论文主体的一致性。语言应当清晰、肯定且有分量，给读者留下深刻印象。
            """
        },
        "abstract": {
            "description": "论文摘要部分的写作提示",
            "template": """
请为一篇{research_area}领域的高水平学术论文撰写专业的摘要。
论文标题：{title}

摘要必须符合以下严格学术标准：

1. 背景与问题：
   - 用1-2句简明扼要地介绍研究背景
   - 清晰界定本研究关注的具体问题
   - 简要说明该问题的重要性和挑战性
   - 准确定位研究在学术领域中的位置

2. 方法描述：
   - 简洁描述所提出的方法或技术方案
   - 点明关键的技术创新点和理论基础
   - 使用准确的学术术语描述技术路线
   - 避免技术细节，但确保描述准确

3. 主要结果：
   - 简要总结关键的实验结果和发现
   - 量化说明主要性能指标和改进程度
   - 突出与基线方法相比的显著优势
   - 确保结果描述客观准确，避免夸大

4. 结论与贡献：
   - 总结研究的主要理论和实践贡献
   - 简述结果的广泛意义和应用价值
   - 点明研究对领域发展的推动作用
   - 保持简洁，但突出研究的独特价值

摘要长度应控制在500词左右，每个部分比例大致为：背景与问题25%，方法描述30%，主要结果30%，结论与贡献15%。摘要整体应自成一体，言简意赅，不使用缩写（除非是领域通用的），不含引用，避免使用公式，确保语言精炼而信息丰富。

{context_info}
{reference_info}
{custom_info}

请使用{style}风格，确保摘要专业、准确且引人入胜。摘要是论文的第一印象，必须清晰传达研究的核心内容和价值，吸引目标读者深入阅读全文。
            """
        }
    }
    
    # 获取对应的提示模板
    if prompt_type not in prompt_templates:
        raise ValueError(f"不支持的提示类型: {prompt_type}")
        
    template = prompt_templates[prompt_type]["template"]
    
    # 准备模板变量
    title = project.get("title", "【论文标题】") if project else "【论文标题】"
    research_area = project.get("metadata", {}).get("research_area", "推荐系统") if project else "推荐系统"
    
    # 准备上下文信息
    context_info = f"上下文信息:\n{context}" if context else ""
    
    # 准备参考文献信息
    reference_info = ""
    if references and len(references) > 0:
        reference_info = "参考文献:\n"
        for i, ref in enumerate(references[:5]):  # 最多使用5篇参考文献
            reference_info += f"{i+1}. 标题: {ref.get('title', '')}\n"
            if ref.get('abstract'):
                reference_info += f"   摘要: {ref.get('abstract')[:200]}...\n"
    
    # 准备自定义要求信息
    custom_info = f"自定义要求:\n{custom_requirements}" if custom_requirements else ""
    
    # 填充模板
    prompt = template.format(
        title=title,
        research_area=research_area,
        context_info=context_info,
        reference_info=reference_info,
        custom_info=custom_info,
        style=style
    )
    
    # 基于提示类型生成建议方向
    suggestions = []
    if prompt_type == "introduction":
        suggestions = [
            "研究背景概述",
            "研究问题和挑战",
            "现有方法的局限性",
            "提出的方法和贡献",
            "论文结构说明"
        ]
    elif prompt_type == "methodology":
        suggestions = [
            "方法概述和框架",
            "问题定义和符号说明",
            "算法设计和细节",
            "技术创新点",
            "实现细节"
        ]
    elif prompt_type == "related_work":
        suggestions = [
            "相关研究领域概述",
            "传统方法综述",
            "深度学习方法综述",
            "本工作与相关工作的区别",
            "研究空白分析"
        ]
    elif prompt_type == "results":
        suggestions = [
            "实验设置和数据集",
            "主要实验结果",
            "消融实验分析",
            "参数敏感性分析",
            "与基线方法的比较"
        ]
    elif prompt_type == "discussion":
        suggestions = [
            "结果解释和分析",
            "与理论的关联",
            "方法的优势和局限性",
            "实际应用意义",
            "未来研究方向"
        ]
    
    # 使用AI助手生成更具体的建议
    # 这里可以接入AI模型，基于提示生成更个性化的建议
    
    return {
        "prompt": prompt,
        "suggestions": suggestions
    }

async def generate_paper_structure(
    title: str,
    abstract: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    research_area: str = "推荐系统",
    paper_type: str = "research",
    target_journal: Optional[str] = None,
    custom_requirements: Optional[str] = None
) -> Dict[str, Any]:
    """
    生成论文结构
    
    参数:
        title: 论文标题
        abstract: 论文摘要
        keywords: 关键词列表
        research_area: 研究领域
        paper_type: 论文类型
        target_journal: 目标期刊/会议
        custom_requirements: 自定义要求
        
    返回:
        包含章节结构和建议的字典
    """
    # 基本论文结构模板
    basic_structure = {
        "research": [
            {
                "title": "摘要 (Abstract)",
                "description": "简要概述研究背景、方法、结果和结论",
                "word_count": 250,
                "key_points": [
                    "研究背景和问题",
                    "简述方法",
                    "主要结果",
                    "结论与意义"
                ]
            },
            {
                "title": "1. 引言 (Introduction)",
                "description": "介绍研究背景、问题、目标和贡献",
                "word_count": 800,
                "key_points": [
                    "研究背景和意义",
                    "研究问题和挑战",
                    "研究目标",
                    "主要贡献",
                    "论文结构"
                ]
            },
            {
                "title": "2. 相关工作 (Related Work)",
                "description": "综述相关研究领域的主要工作和方法",
                "word_count": 1000,
                "key_points": [
                    "相关研究领域概述",
                    "现有方法分类和比较",
                    "研究空白分析",
                    "本工作与相关工作的联系和区别"
                ]
            },
            {
                "title": "3. 方法 (Methodology)",
                "description": "详细描述提出的方法、模型或算法",
                "word_count": 1500,
                "key_points": [
                    "问题定义和符号说明",
                    "方法概述和框架",
                    "模型或算法详细设计",
                    "技术创新点",
                    "实现细节"
                ]
            },
            {
                "title": "4. 实验 (Experiments)",
                "description": "描述实验设置、数据集、评估指标和实验结果",
                "word_count": 1800,
                "key_points": [
                    "实验设置和环境",
                    "数据集和预处理",
                    "评估指标",
                    "基线方法",
                    "主要实验结果",
                    "消融实验"
                ]
            },
            {
                "title": "5. 讨论 (Discussion)",
                "description": "分析和解释实验结果，讨论方法的优缺点和局限性",
                "word_count": 800,
                "key_points": [
                    "结果分析和解释",
                    "与现有方法的比较",
                    "方法的优势和局限性",
                    "潜在应用场景"
                ]
            },
            {
                "title": "6. 结论 (Conclusion)",
                "description": "总结研究成果和贡献，展望未来研究方向",
                "word_count": 400,
                "key_points": [
                    "研究总结",
                    "主要贡献",
                    "未来研究方向"
                ]
            }
        ],
        "review": [
            {
                "title": "摘要 (Abstract)",
                "description": "简要概述综述范围、方法和主要发现",
                "word_count": 250,
                "key_points": [
                    "综述范围和目标",
                    "综述方法",
                    "主要发现",
                    "结论与未来方向"
                ]
            },
            {
                "title": "1. 引言 (Introduction)",
                "description": "介绍综述主题、背景、目标和组织结构",
                "word_count": 800,
                "key_points": [
                    "研究领域背景",
                    "综述目标和范围",
                    "综述方法",
                    "论文结构"
                ]
            },
            {
                "title": "2. 综述方法 (Survey Methodology)",
                "description": "详细描述文献收集、筛选和分析方法",
                "word_count": 600,
                "key_points": [
                    "文献检索策略",
                    "纳入和排除标准",
                    "分类方法",
                    "分析框架"
                ]
            },
            {
                "title": "3. 研究现状分析 (Analysis of Current Research)",
                "description": "按主题或方法分类分析现有研究",
                "word_count": 2500,
                "key_points": [
                    "主要研究方向",
                    "关键方法和技术",
                    "研究趋势",
                    "方法比较"
                ]
            },
            {
                "title": "4. 研究挑战与问题 (Research Challenges and Issues)",
                "description": "讨论领域中的主要挑战和开放问题",
                "word_count": 1000,
                "key_points": [
                    "技术挑战",
                    "方法局限性",
                    "应用障碍",
                    "开放问题"
                ]
            },
            {
                "title": "5. 未来研究方向 (Future Research Directions)",
                "description": "提出可能的未来研究方向和机会",
                "word_count": 800,
                "key_points": [
                    "新兴研究方向",
                    "潜在突破点",
                    "交叉学科机会",
                    "应用前景"
                ]
            },
            {
                "title": "6. 结论 (Conclusion)",
                "description": "总结综述发现和贡献",
                "word_count": 400,
                "key_points": [
                    "主要发现总结",
                    "综述贡献",
                    "最终建议"
                ]
            }
        ]
    }
    
    # 获取基本结构
    structure_template = basic_structure.get(paper_type, basic_structure["research"])
    
    # 根据研究领域定制章节内容
    if research_area == "推荐系统":
        # 为推荐系统研究领域定制内容
        for section in structure_template:
            if "方法" in section["title"]:
                section["key_points"] = [
                    "推荐系统模型设计",
                    "特征工程和表示学习",
                    "模型框架和算法流程",
                    "训练和推理过程",
                    "技术创新点"
                ]
            elif "相关工作" in section["title"]:
                section["key_points"] = [
                    "传统推荐方法",
                    "深度学习推荐方法",
                    "序列推荐方法",
                    "多模态推荐方法",
                    "本工作与现有方法的区别"
                ]
            elif "实验" in section["title"]:
                section["key_points"] = [
                    "数据集和预处理",
                    "评估指标(如NDCG, Recall, Precision等)",
                    "基线方法",
                    "主要实验结果",
                    "消融实验和参数敏感性分析"
                ]
    
    # 如果有自定义要求，可以通过AI模型进一步定制结构
    # 这里可以接入AI模型进行更复杂的结构生成
    
    # 计算估计总字数
    estimated_length = sum(section.get("word_count", 0) for section in structure_template)
    
    # 生成写作建议
    suggestions = [
        f"标题'{title}'适合采用{paper_type}类型的论文结构",
        f"重点优化和扩展方法和实验部分",
        f"总体建议字数约{estimated_length}字",
        "确保引言部分清晰阐述研究问题和贡献",
        "实验部分需包含充分的对比实验和分析"
    ]
    
    # 如果有特定目标期刊/会议，可以添加相关建议
    if target_journal:
        suggestions.append(f"针对{target_journal}，建议关注其评审重点和格式要求")
    
    return {
        "sections": structure_template,
        "suggestions": suggestions,
        "estimated_length": estimated_length
    }

async def generate_writing_content(
    section: str,
    style: str,
    user_id: Optional[str] = None,
    topic: Optional[str] = None,
    researchProblem: Optional[str] = None,
    methodFeature: Optional[str] = None,
    modelingTarget: Optional[str] = None,
    improvement: Optional[str] = None,
    keyComponent: Optional[str] = None,
    impact: Optional[str] = None,
    additionalContext: Optional[str] = None
) -> Dict[str, Any]:
    """生成论文不同部分的内容"""
    try:
        # 记录请求参数
        logging.info(f"生成写作内容请求 - 部分: {section}, 风格: {style}, 用户: {user_id}")
        logging.debug(f"主题: {topic}, 问题: {researchProblem}, 方法: {methodFeature}")
        
        # 解决部分类型映射
        section_mapping = {
            'abstract': '摘要',
            'introduction': '引言',
            'related_work': '相关工作',
            'methodology': '方法',
            'method': '方法',
            'experiment': '实验',
            'results': '结果',
            'discussion': '讨论',
            'conclusion': '结论'
        }
        
        section_zh = section_mapping.get(section.lower(), section)
        
        # 构建提示上下文
        context = f"""你是一个专业的学术论文写作助手，擅长撰写高质量的{section_zh}部分。

请使用{style}风格撰写一个论文的{section_zh}部分，要求内容连贯、结构清晰、语言规范。
"""

        # 根据部分类型添加不同的上下文
        if topic:
            context += f"\n研究主题: {topic}"
        if researchProblem:
            context += f"\n研究问题: {researchProblem}"
        if methodFeature:
            context += f"\n方法特点: {methodFeature}"
        if modelingTarget:
            context += f"\n建模目标: {modelingTarget}"
        if improvement:
            context += f"\n性能提升: {improvement}"
        if keyComponent:
            context += f"\n关键组件: {keyComponent}"
        if impact:
            context += f"\n研究影响: {impact}"
        if additionalContext:
            context += f"\n额外信息: {additionalContext}"
        
        # 获取写作风格指南
        def get_writing_style_guide(style):
            styles = {
                'academic': '学术风格指南: 使用正式语言，避免第一人称，强调客观性和精确性，使用专业术语，遵循严格的论证结构',
                'technical': '技术风格指南: 重点关注技术细节，使用精确的技术术语，提供明确的算法和方法描述，包含必要的数学公式和图表',
                'explanatory': '解释性风格指南: 使用更通俗易懂的语言，解释复杂概念和术语，使用类比和例子，适当使用第二人称，保持知识的准确性'
            }
            return styles.get(style, styles['academic'])
        
        # 获取特定章节的写作指南
        def get_section_writing_guide(section):
            guides = {
                'abstract': '摘要写作指南: 简明扼要地概括研究目的、方法、结果和意义，不超过300字，不使用引用和专业术语',
                'introduction': '引言写作指南: 介绍研究背景和问题，突出研究意义和创新点，清晰陈述研究目标和方法，概述论文结构',
                'related_work': '相关工作写作指南: 综述相关研究的历史发展和现状，对比不同方法的优缺点，指出现有研究的不足，强调本研究的创新点',
                'method': '方法写作指南: 详细描述研究方法和技术实现细节，使用准确的术语和公式，分步骤阐述研究过程，解释关键决策和参数选择',
                'experiment': '实验写作指南: 描述实验设置、数据集和评估指标，清晰展示实验结果，使用表格和图表，对结果进行客观分析',
                'conclusion': '结论写作指南: 总结研究成果和主要发现，讨论研究局限性，提出未来研究方向，强调研究贡献和实际意义'
            }
            return guides.get(section, '写作指南: 组织内容清晰连贯，使用逻辑严密的论证，适当使用小标题，注意段落间的过渡自然')
            
        # 获取不同部分的写作指导
        style_guide = get_writing_style_guide(style)
        section_guide = get_section_writing_guide(section)
        
        context += f"\n\n{style_guide}\n\n{section_guide}"
        
        # 清晰的输出要求
        context += """

请直接输出你撰写的内容，无需解释、无需引言，格式如下：
{
  "content": "你撰写的论文内容...",
  "suggestions": ["写作建议1", "写作建议2", "写作建议3"]
}
"""
        
        # 解析AI响应
        def parse_ai_response(response):
            try:
                # 提取JSON部分
                import re
                import json
                
                # 尝试解析整体响应
                try:
                    response_data = json.loads(response)
                    if isinstance(response_data, dict) and "content" in response_data:
                        return response_data
                except:
                    pass
                    
                # 尝试从文本中提取JSON
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                    return data
                
                # 如果上面都失败，则将整个响应作为内容
                return {
                    "content": response,
                    "suggestions": []
                }
            except Exception as e:
                logging.error(f"解析AI响应失败: {str(e)}")
                return None
        
        # 调用AI生成内容
        try:
            # 如果是真实环境则调用AI
            if settings.ENVIRONMENT != "test":
                response = await assistant_service.call_ai_assistant(context)
                response_obj = parse_ai_response(response)
                if response_obj:
                    return response_obj
            
            # 这里提供模拟数据（测试环境或AI调用失败时使用）
            mock_content = create_default_section_content(section_zh, topic or "未指定主题", methodFeature or "创新方法")
            mock_suggestions = [
                f"考虑添加更多关于{topic if topic else '研究主题'}的背景信息",
                "使用更多图表来展示结果",
                "强化论文的理论贡献部分"
            ]
            
            return {
                "content": mock_content,
                "suggestions": mock_suggestions
            }
        except Exception as e:
            logging.error(f"解析AI响应时出错: {str(e)}")
            # 确保即使出错也返回有效的格式
            return {
                "content": f"生成内容时遇到错误，请重试。错误: {str(e)}",
                "suggestions": ["请提供更详细的信息", "尝试描述具体的研究问题", "指定研究领域"]
            }
            
    except Exception as e:
        logging.error(f"生成写作内容时出错: {str(e)}")
        # 确保即使出错也返回有效的格式
        return {
            "content": f"生成内容时遇到错误，请重试。错误: {str(e)}",
            "suggestions": ["请提供更详细的信息", "尝试描述具体的研究问题", "指定研究领域"]
        }

async def generate_paper_section(
    section: str,
    style: str = "academic",
    user_id: Optional[str] = None,
    topic: Optional[str] = None,
    researchProblem: Optional[str] = None,
    methodFeature: Optional[str] = None,
    modelingTarget: Optional[str] = None,
    improvement: Optional[str] = None,
    keyComponent: Optional[str] = None,
    impact: Optional[str] = None,
    additionalContext: Optional[str] = None
) -> Dict[str, Any]:
    """
    根据指定参数生成论文章节内容
    
    Args:
        section: 论文部分类型
        style: 写作风格
        user_id: 用户ID
        topic: 研究主题
        researchProblem: 研究问题
        methodFeature: 方法特点
        modelingTarget: 建模目标
        improvement: 性能提升
        keyComponent: 关键组件
        impact: 研究影响
        additionalContext: 额外上下文信息
        
    Returns:
        包含生成内容和写作建议的字典
    """
    import logging
    from src.services import ai_assistant
    
    logger = logging.getLogger(__name__)
    
    logger.info(f"为用户 {user_id} 生成{section}部分的内容，风格: {style}")
    
    # 构建研究主题
    research_topic = topic or "推荐系统"
    if researchProblem:
        research_topic += f"（解决{researchProblem}问题）"
    
    # 构建创新点
    innovation_points = []
    if methodFeature:
        innovation_points.append({
            "title": f"创新的{methodFeature}",
            "description": methodFeature,
            "theoreticalBasis": additionalContext or "基于深度学习和推荐系统理论"
        })
    
    if keyComponent:
        innovation_points.append({
            "title": keyComponent,
            "description": f"实现{keyComponent}以提升模型性能",
            "theoreticalBasis": "基于最新研究成果"
        })
    
    if modelingTarget:
        innovation_points.append({
            "title": f"{modelingTarget}建模",
            "description": f"有效建模{modelingTarget}",
            "theoreticalBasis": "基于用户行为分析"
        })
    
    # 如果没有具体创新点，提供一个默认创新点
    if not innovation_points:
        innovation_points.append({
            "title": "推荐系统优化方法",
            "description": "一种新的推荐算法优化方法",
            "theoreticalBasis": "基于深度学习和推荐系统理论"
        })
    
    # 构建论文大纲（如果需要）
    outline = {
        "title": f"{research_topic}研究",
        "abstract": "摘要部分",
        "sections": [
            {"title": "1. 引言 (Introduction)", "content": ["研究背景", "研究问题", "研究贡献"]},
            {"title": "2. 相关工作 (Related Work)", "content": ["现有方法回顾", "研究差距"]},
            {"title": "3. 方法 (Methodology)", "content": ["问题定义", "模型架构", "技术细节"]},
            {"title": "4. 实验 (Experiments)", "content": ["实验设置", "结果分析", "消融实验"]},
            {"title": "5. 结论 (Conclusion)", "content": ["总结", "未来工作"]}
        ]
    }
    
    # 转换section参数为对应的标题
    section_title_map = {
        "abstract": "摘要 (Abstract)",
        "introduction": "1. 引言 (Introduction)",
        "related_work": "2. 相关工作 (Related Work)",
        "method": "3. 方法 (Methodology)",
        "experiment": "4. 实验 (Experiments)",
        "conclusion": "5. 结论 (Conclusion)"
    }
    
    section_title = section_title_map.get(section, section)
    
    try:
        # 调用AI API生成章节内容
        logger.info(f"调用AI API生成'{section_title}'章节内容")
        
        # 指定语言（根据风格决定）
        language = "zh"  # 默认中文
        
        # 调用AI助手的generate_paper_section函数
        try:
            section_data = await ai_assistant.generate_paper_section(
                research_topic=research_topic,
                section_title=section_title,
                outline=outline,
                innovation_points=innovation_points,
                language=language
            )
            
            # 确保返回了有效数据
            if section_data and isinstance(section_data, dict):
                content = section_data.get("content", "")
                writing_tips = section_data.get("writingTips", [])
                if not writing_tips and "references" in section_data:
                    # 如果没有写作建议但有参考文献，添加一些默认建议
                    writing_tips = ["考虑引用更多相关文献", "确保内容逻辑连贯", "使用专业术语保持学术风格"]
                
                logger.info(f"成功生成'{section_title}'章节内容，长度：{len(content)}字符")
                
                return {
                    "content": content,
                    "suggestions": writing_tips or section_data.get("references", [])
                }
            else:
                # 如果返回不是字典，记录警告并返回默认内容
                logger.warning(f"AI API返回的内容格式不正确: {type(section_data)}")
                return create_default_section_content(section_title, research_topic, innovation_points)
        except Exception as e:
            # 如果AI API调用失败，记录错误并返回默认内容
            logger.error(f"调用AI API生成章节内容失败: {str(e)}")
            return create_default_section_content(section_title, research_topic, innovation_points, error=str(e))
    except Exception as e:
        logger.error(f"生成论文章节内容时出错: {str(e)}", exc_info=True)
        
        # 返回错误信息，而不是默认到模拟数据
        return {
            "error": f"生成'{section_title}'章节时遇到错误: {str(e)}",
            "errorDetails": {
                "message": str(e),
                "type": e.__class__.__name__
            },
            "content": f"生成{section_title}章节内容失败。错误：{str(e)}。请重试或手动编写此部分。",
            "suggestions": [
                "重试生成内容",
                "尝试提供更详细的研究主题信息",
                "手动编写此部分内容",
                "联系管理员解决API调用问题"
            ]
        }

def create_default_section_content(section_title, research_topic, innovation_points, error=None):
    """
    创建默认章节内容，用于API调用失败时提供备选内容
    
    参数:
        section_title: 章节标题
        research_topic: 研究主题
        innovation_points: 创新点信息
        error: 错误信息
    
    返回:
        包含标题和内容的字典
    """
    # 设置默认内容模板
    title = section_title
    
    # 提取研究方向名称
    topic_name = research_topic or "推荐系统"
    
    # 根据章节类型生成不同的内容
    if "摘要" in section_title or "abstract" in section_title.lower():
        content = f"""
# {topic_name}领域研究摘要

本文研究了{topic_name}领域中的关键问题，提出了新的解决方案。我们的方法主要创新点包括...[请在此详细说明您的创新点]。实验结果表明，与现有方法相比，我们的方法在...方面取得了显著改进。

**撰写建议**:
1. 简明扼要，控制在250-300词以内
2. 包含研究背景、问题、方法、结果和意义
3. 强调创新点和贡献
4. 避免引用参考文献
5. 不使用首次出现的缩写
        """
    elif "引言" in section_title or "introduction" in section_title.lower():
        content = f"""
# {topic_name}研究引言

## 研究背景
{topic_name}在...[请描述研究领域背景和重要性]

## 研究问题与挑战
现有{topic_name}方法面临的主要挑战包括...[请描述具体挑战]

## 现有方法局限性
目前的方法存在以下局限性...[请描述现有方法的不足]

## 本文贡献
本文的主要贡献包括:
1. [第一个贡献点]
2. [第二个贡献点]
3. [第三个贡献点]

## 论文结构
本文余下内容安排如下：第二部分介绍相关工作；第三部分详细描述我们提出的方法；第四部分进行实验评估；第五部分总结全文并指出未来研究方向。

**撰写建议**:
1. 清晰界定研究问题和重要性
2. 描述现有方法的局限性
3. 突出本文的创新点和贡献
4. 提供论文结构概述
        """
    elif "相关工作" in section_title or "related work" in section_title.lower():
        content = f"""
# {topic_name}相关研究综述

## 传统方法
在{topic_name}领域，传统方法主要包括...[请描述传统方法]

## 深度学习方法
近年来，深度学习在{topic_name}领域取得了重要进展...[请描述深度学习方法]

## 与本文工作的关系
本文的研究与现有工作的主要区别在于...[请描述您的工作与现有工作的关系]

**撰写建议**:
1. 按照类别或时间顺序组织相关工作
2. 重点关注与您研究最相关的工作
3. 客观分析每种方法的优缺点
4. 说明您的工作如何解决现有工作的不足
5. 展示对相关领域的全面了解
        """
    elif "方法" in section_title or "methodology" in section_title.lower():
        content = f"""
# {topic_name}方法设计

## 问题定义
首先，我们将{topic_name}问题形式化为...[请给出数学定义]

## 系统架构
本文提出的方法整体架构如图1所示，包括以下关键组件：
1. [第一个组件]
2. [第二个组件]
3. [第三个组件]

## 算法细节
[请在此处详细描述您的算法，包括数学公式]

## 训练策略
我们采用以下训练策略优化模型...[请描述训练方法]

**撰写建议**:
1. 提供清晰的问题定义和符号说明
2. 详细解释每个模块的设计原理
3. 突出方法的创新点
4. 使用图表辅助说明系统架构
5. 展示算法的数学基础
        """
    elif "实验" in section_title or "experiment" in section_title.lower():
        content = f"""
# {topic_name}实验评估

## 实验设置
### 数据集
本文使用了以下数据集进行实验:
1. [数据集1]: [简要描述]
2. [数据集2]: [简要描述]

### 评估指标
我们采用以下指标评估模型性能:
- [指标1]
- [指标2]
- [指标3]

### 基线方法
我们将本文方法与以下基线进行比较:
- [基线方法1]
- [基线方法2]
- [基线方法3]

### 参数设置
[描述实验参数设置]

## 主要结果
[请在此处展示并分析主要实验结果]

## 消融实验
为验证各组件的有效性，我们进行了以下消融实验:
[描述消融实验设计和结果]

## 案例分析
[提供代表性案例分析]

**撰写建议**:
1. 详细描述实验设置，确保可复现
2. 使用表格呈现主要结果
3. 设计全面的消融实验验证各组件的有效性
4. 与基线方法进行详细比较和分析
5. 提供深入的案例分析
        """
    elif "结论" in section_title or "conclusion" in section_title.lower():
        content = f"""
# {topic_name}研究结论

## 工作总结
本文研究了{topic_name}领域的关键问题，主要工作包括...[请总结主要工作]

## 主要贡献
本研究的主要贡献包括:
1. [第一个贡献]
2. [第二个贡献]
3. [第三个贡献]

## 局限性
当前研究仍存在以下局限性...[请描述局限性]

## 未来工作
未来我们计划从以下方向继续探索:
1. [未来方向1]
2. [未来方向2]
3. [未来方向3]

**撰写建议**:
1. 简明扼要地总结研究内容和贡献
2. 诚实讨论研究的局限性
3. 提出有价值的未来研究方向
4. 强调研究的理论和实践意义
        """
    else:
        # 其他章节的默认内容
        content = f"""
# {section_title}

[本节内容尚未生成，请根据您的研究内容补充{section_title}相关内容]

**提示**: AI辅助生成内容出现了临时错误。您可以点击"重新生成"按钮尝试再次生成，或者手动编辑此部分内容。

{f"错误信息: {error}" if error else ""}
        """
    
    return {
        "title": title,
        "content": content.strip(),
        "generated": False,
        "note": "此为系统生成的默认内容模板，请基于您的具体研究进行修改和完善。"
    } 