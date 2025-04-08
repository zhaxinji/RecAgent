"""
RecAgent研究空白分析功能示例：识别推荐系统研究中的空白和机会
"""

import asyncio
import json
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 从assistant.py导入更新的实现，而不是ai_assistant.py
from src.services.assistant import analyze_research_gaps
from src.services.paper import get_paper_by_id, search_papers
from src.db.session import get_session
from src.models.user import get_user_by_email

async def main():
    print("RecAgent 研究空白分析功能示例")
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
        
        # 步骤1: 搜索相关论文
        print("\n步骤1: 搜索相关论文")
        search_query = "推荐系统 深度学习 冷启动问题"
        search_params = {
            "query": search_query,
            "user_id": user_id,
            "limit": 5,
            "offset": 0,
            "sort_by": "relevance"
        }
        
        search_results = await search_papers(**search_params)
        print(f"搜索结果: 共找到 {search_results['total']} 篇相关论文")
        
        paper_ids = []
        for i, paper in enumerate(search_results['papers'], 1):
            paper_ids.append(paper['id'])
            print(f"{i}. {paper['title']} (ID: {paper['id']})")
            print(f"   作者: {', '.join(paper['authors'])}")
            print(f"   年份: {paper['year']}")
            print(f"   引用数: {paper.get('citation_count', 'N/A')}")
            print()
        
        if not paper_ids:
            print("未找到相关论文，请先导入论文到系统中")
            return
        
        # 步骤2: 定义研究领域和角度
        print("\n步骤2: 定义研究领域和角度")
        research_domain = "推荐系统中的冷启动问题"
        research_perspective = "跨域知识迁移视角"
        additional_context = """
        我正在研究如何利用跨域知识迁移来解决推荐系统中的冷启动问题。
        特别关注用户偏好如何从一个领域迁移到另一个领域，以及如何结合图神经网络处理异构数据。
        希望找出现有方法的局限性和可能的创新方向。
        """
        
        print(f"研究领域: {research_domain}")
        print(f"研究角度: {research_perspective}")
        
        # 步骤3: 分析研究空白
        print("\n步骤3: 分析研究空白")
        analysis_params = {
            "paper_ids": paper_ids,
            "domain": research_domain,
            "perspective": research_perspective,
            "additional_context": additional_context,
            "user_id": user_id,
        }
        
        print("开始分析研究空白，这可能需要一些时间...")
        analysis_result = await analyze_research_gaps(**analysis_params)
        
        # 步骤4: 展示分析结果
        print("\n步骤4: 研究空白分析结果")
        print(f"领域: {analysis_result['domain']}")
        print(f"视角: {analysis_result['perspective']}")
        print(f"\n总结: {analysis_result['summary']}\n")
        
        print("识别出的研究空白:")
        for i, gap in enumerate(analysis_result['research_gaps'], 1):
            print(f"\n研究空白 {i}: {gap['title']}")
            print(f"描述: {gap['description']}")
            print("证据:")
            for evidence in gap['evidence']:
                print(f" - {evidence}")
            print("潜在研究方向:")
            for direction in gap['potential_directions']:
                print(f" - {direction}")
        
        print("\n相关论文:")
        for i, paper in enumerate(analysis_result['related_papers'], 1):
            print(f"{i}. {paper['title']} ({paper['year']})")
            print(f"   相关性: {paper['relevance']}")
            if 'key_findings' in paper:
                print(f"   主要发现: {paper['key_findings']}")
            print()

if __name__ == "__main__":
    asyncio.run(main()) 