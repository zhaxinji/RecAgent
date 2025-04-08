"""
RecAgent写作功能示例：生成论文结构并创建写作项目
"""

import asyncio
import json
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.writing import (
    generate_writing_prompt,
    generate_paper_structure,
    create_writing_project,
    add_chapter_to_project,
    generate_content_for_chapter,
    get_writing_projects,
)
from src.db.session import get_session
from src.models.user import get_user_by_email

async def main():
    print("RecAgent 写作功能示例")
    print("=" * 60)
    
    # 初始化数据库会话
    async with get_session() as session:
        # 获取用户ID (示例中使用测试用户)
        user = await get_user_by_email(session, "test@example.com")
        if not user:
            print("错误: 测试用户不存在，请先创建测试用户")
            return
        
        user_id = str(user.id)
        print(f"使用用户ID: {user_id}")
        
        # 步骤1: 生成论文结构
        print("\n步骤1: 生成论文结构")
        structure_params = {
            "title": "基于深度学习的协同过滤推荐系统研究",
            "abstract": "本文研究了深度学习在协同过滤推荐系统中的应用，提出了一种基于神经网络的新型推荐算法。",
            "keywords": ["深度学习", "推荐系统", "协同过滤", "神经网络"],
            "research_area": "推荐系统",
            "paper_type": "research",
            "target_journal": "IEEE Transactions on Neural Networks and Learning Systems",
            "custom_requirements": "需要包含实验结果与现有方法的对比分析"
        }
        
        paper_structure = await generate_paper_structure(**structure_params)
        print("已生成论文结构")
        print(f"预计字数: {paper_structure['estimated_word_count']}")
        
        # 打印论文结构
        print("\n论文结构:")
        for i, section in enumerate(paper_structure['sections'], 1):
            print(f"{i}. {section['title']} ({section['word_count']}字)")
            print(f"   描述: {section['description']}")
            print(f"   要点: {', '.join(section['key_points'])}")
        
        # 步骤2: 创建写作项目
        print("\n步骤2: 创建写作项目")
        project_data = {
            "title": structure_params["title"],
            "description": structure_params["abstract"],
            "user_id": user_id,
            "metadata": {
                "paper_type": structure_params["paper_type"],
                "target_journal": structure_params["target_journal"],
                "keywords": structure_params["keywords"],
                "research_area": structure_params["research_area"],
                "structure": paper_structure
            }
        }
        
        project = await create_writing_project(**project_data)
        project_id = project["id"]
        print(f"写作项目已创建，ID: {project_id}")
        print(f"项目标题: {project['title']}")
        
        # 步骤3: 为项目添加章节
        print("\n步骤3: 为项目添加章节")
        chapters = []
        for section in paper_structure['sections']:
            chapter_data = {
                "project_id": project_id,
                "title": section['title'],
                "description": section['description'],
                "user_id": user_id,
                "order": len(chapters) + 1,
                "metadata": {
                    "word_count": section['word_count'],
                    "key_points": section['key_points']
                }
            }
            
            chapter = await add_chapter_to_project(**chapter_data)
            chapters.append(chapter)
            print(f"添加章节: {chapter['title']}")
        
        # 步骤4: 为某个章节生成写作提示和内容
        print("\n步骤4: 为引言章节生成写作提示")
        intro_chapter = next((c for c in chapters if "引言" in c['title'] or "介绍" in c['title']), chapters[0])
        
        prompt_params = {
            "prompt_type": "introduction",
            "context": structure_params["abstract"],
            "references": [],  # 实际使用时可以传入参考文献ID
            "style": "academic",
            "custom_requirements": "需要清晰地说明研究背景、动机和主要贡献"
        }
        
        prompt_result = await generate_writing_prompt(**prompt_params)
        prompt = prompt_result["prompt"]
        suggestions = prompt_result["suggestions"]
        
        print("写作提示生成成功")
        print("提示预览:")
        print(prompt[:300] + "...\n")
        
        print("写作建议:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")
        
        # 步骤5: 为某个章节生成内容
        print("\n步骤5: 为引言章节生成内容")
        content_params = {
            "chapter_id": intro_chapter["id"],
            "user_id": user_id,
            "writing_prompt": prompt,
            "key_points": intro_chapter["metadata"]["key_points"],
            "target_word_count": intro_chapter["metadata"]["word_count"]
        }
        
        content = await generate_content_for_chapter(**content_params)
        
        print("内容生成成功")
        print("内容预览:")
        content_preview = content.split("\n")[:5]
        print("\n".join(content_preview) + "\n... [内容省略] ...\n")
        
        # 步骤6: 获取用户所有写作项目
        print("\n步骤6: 获取用户写作项目列表")
        projects = await get_writing_projects(user_id)
        print(f"用户共有 {len(projects)} 个写作项目")
        
        for i, proj in enumerate(projects, 1):
            print(f"{i}. {proj['title']} (ID: {proj['id']})")
            print(f"   创建时间: {proj['created_at']}")
            print(f"   更新时间: {proj['updated_at']}")
            print(f"   章节数量: {len(proj.get('chapters', []))}")
            print()

if __name__ == "__main__":
    asyncio.run(main()) 