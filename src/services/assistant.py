from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import uuid
import re
import json
import logging
import time

from src.models.assistant import AssistantSession, AssistantMessage, MessageRole as ModelMessageRole, AssistantType as ModelAssistantType, ResearchAnalysis
from src.schemas.assistant import (
    SessionCreate, 
    SessionUpdate, 
    MessageCreate, 
    MessageRole,
)
from src.models.paper import Paper
from src.services import ai_assistant

# 获取AI助手实例的辅助函数
def get_ai_assistant(provider: Optional[str] = None):
    """获取AI助手实例，可选择指定提供商"""
    return ai_assistant.ai_assistant

# 会话管理函数
def create_session(
    db: Session, 
    user_id: str, 
    session_data: SessionCreate
) -> AssistantSession:
    """创建新的研究助手会话"""
    print("创建会话，数据:", session_data)
    print("会话类型:", session_data.session_type)
    print("会话类型类型:", type(session_data.session_type))
    
    # 如果session_type是一个枚举对象，获取它的值
    session_type = session_data.session_type
    if isinstance(session_type, ModelAssistantType):
        session_type = session_type.value
        print("转换后的会话类型:", session_type)
    
    db_session = AssistantSession(
        owner_id=user_id,
        title=session_data.title,
        session_type=session_type,  # 使用转换后的值
        context=session_data.context,
        paper_id=session_data.paper_id
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_session(db: Session, session_id: str, user_id: str) -> Optional[AssistantSession]:
    """获取指定会话"""
    return db.query(AssistantSession).filter(
        AssistantSession.id == session_id,
        AssistantSession.owner_id == user_id
    ).first()

def get_sessions(
    db: Session, 
    user_id: str, 
    skip: int = 0, 
    limit: int = 100,
    active_only: bool = True
) -> List[AssistantSession]:
    """获取用户的会话列表"""
    query = db.query(AssistantSession).filter(
        AssistantSession.owner_id == user_id
    )
    
    if active_only:
        query = query.filter(AssistantSession.is_active == True)
    
    return query.order_by(desc(AssistantSession.last_message_at)).offset(skip).limit(limit).all()

def get_session_with_messages(
    db: Session, 
    session_id: str, 
    user_id: str,
    message_limit: int = 50
) -> Optional[AssistantSession]:
    """获取会话及其消息"""
    session = get_session(db, session_id, user_id)
    if session:
        # 获取最近的消息
        session.messages = db.query(AssistantMessage).filter(
            AssistantMessage.session_id == session_id
        ).order_by(
            AssistantMessage.sequence
        ).limit(message_limit).all()
    return session

def update_session(
    db: Session, 
    session_id: str, 
    user_id: str, 
    session_data: SessionUpdate
) -> Optional[AssistantSession]:
    """更新会话信息"""
    session = get_session(db, session_id, user_id)
    if not session:
        return None
        
    update_data = session_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(session, key, value)
    
    # 更新时间
    session.updated_at = datetime.now()
    
    db.commit()
    db.refresh(session)
    return session

def delete_session(db: Session, session_id: str, user_id: str) -> bool:
    """删除会话（软删除，标记为非活动）"""
    session = get_session(db, session_id, user_id)
    if not session:
        return False
    
    session.is_active = False
    session.updated_at = datetime.now()
    db.commit()
    return True

def hard_delete_session(db: Session, session_id: str, user_id: str) -> bool:
    """硬删除会话及其所有消息"""
    session = get_session(db, session_id, user_id)
    if not session:
        return False
    
    db.delete(session)
    db.commit()
    return True

# 消息管理函数
def create_message(
    db: Session, 
    session_id: str,
    message_data: MessageCreate
) -> AssistantMessage:
    """创建新消息"""
    # 获取当前会话的最大序号
    max_sequence = db.query(func.max(AssistantMessage.sequence)).filter(
        AssistantMessage.session_id == session_id
    ).scalar() or 0
    
    # 确保metadata不为None
    metadata = message_data.message_metadata or {}
    
    # 将pydantic模型中的role值转换为数据库枚举类型
    role_value = message_data.role.value if hasattr(message_data.role, 'value') else message_data.role
    db_role = ModelMessageRole(role_value)
    
    # 创建新消息
    db_message = AssistantMessage(
        session_id=session_id,
        role=db_role,
        content=message_data.content,
        message_metadata=metadata,
        sequence=max_sequence + 1
    )
    db.add(db_message)
    
    # 更新会话的最后消息时间
    session = db.query(AssistantSession).filter(AssistantSession.id == session_id).first()
    if session:
        session.last_message_at = datetime.now()
    
    db.commit()
    db.refresh(db_message)
    return db_message

def get_messages(
    db: Session, 
    session_id: str, 
    skip: int = 0, 
    limit: int = 100
) -> List[AssistantMessage]:
    """获取会话的消息列表"""
    return db.query(AssistantMessage).filter(
        AssistantMessage.session_id == session_id
    ).order_by(
        AssistantMessage.sequence
    ).offset(skip).limit(limit).all()

def get_message(db: Session, message_id: str) -> Optional[AssistantMessage]:
    """获取指定消息"""
    return db.query(AssistantMessage).filter(AssistantMessage.id == message_id).first()

def delete_message(db: Session, message_id: str) -> bool:
    """删除指定消息"""
    message = get_message(db, message_id)
    if not message:
        return False
    
    db.delete(message)
    db.commit()
    return True

# 研究空白分析服务
async def analyze_research_gaps(
    db: Session,
    user_id: str,
    domain: str,
    perspective: str,
    paper_ids: Optional[List[str]] = None,
    additional_context: Optional[str] = None
) -> Tuple[AssistantSession, Dict[str, Any]]:
    """分析研究领域的空白"""
    # 创建会话
    session = create_session(
        db,
        user_id,
        SessionCreate(
            title=f"{domain}领域研究空白分析",
            session_type="research_gap",  # 使用字符串值
            context={
                "domain": domain,
                "perspective": perspective,
                "paper_ids": paper_ids
            }
        )
    )
    
    # 添加用户请求消息
    user_message = create_message(
        db,
        session.id,
        MessageCreate(
            role=MessageRole.USER,
            content=f"请分析{domain}领域从{perspective}角度的研究空白。"
        )
    )
    
    # 收集相关论文的信息
    papers_info = []
    if paper_ids:
        for paper_id in paper_ids:
            paper = db.query(Paper).filter(Paper.id == paper_id).first()
            if paper:
                papers_info.append({
                    "id": paper.id,
                    "title": paper.title,
                    "abstract": paper.abstract,
                    "content": paper.content[:5000] if paper.content else None  # 限制内容长度
                })
    
    try:
        # 调用AI服务分析研究空白
        # 这里使用模拟数据，实际实现需要调用真实的AI服务
        analysis_result = await get_research_gap_analysis(domain, perspective, papers_info, additional_context)
        
        # 确保分析结果具有一致的结构
        if "researchGaps" not in analysis_result and "research_gaps" in analysis_result:
            analysis_result["researchGaps"] = analysis_result.pop("research_gaps")
        
        for gap in analysis_result.get("researchGaps", []):
            if "potentialDirections" not in gap and "potential_directions" in gap:
                gap["potentialDirections"] = gap.pop("potential_directions")
        
        # 保存分析结果
        research_analysis = ResearchAnalysis(
            owner_id=user_id,
            session_id=session.id,
            analysis_type="research_gap",
            title=f"{domain}领域研究空白分析",
            domain=domain,
            summary=analysis_result["summary"],
            content=analysis_result["researchGaps"],
            references=analysis_result.get("references", [])
        )
        db.add(research_analysis)
        
        # 添加助手回复消息
        response_content = f"## {domain}领域研究空白分析\n\n{analysis_result['summary']}\n\n"
        for gap in analysis_result["researchGaps"]:
            response_content += f"### {gap['title']}\n{gap['description']}\n\n"
        
        assistant_message = create_message(
            db,
            session.id,
            MessageCreate(
                role=MessageRole.ASSISTANT,
                content=response_content,
                message_metadata={"analysis": analysis_result}
            )
        )
        
        # 更新会话结果
        session.result = analysis_result
        db.commit()
        
        return session, analysis_result
    except Exception as e:
        # 处理错误，创建错误消息
        error_message = create_message(
            db,
            session.id,
            MessageCreate(
                role=MessageRole.ASSISTANT,
                content=f"抱歉，分析研究空白时遇到了问题: {str(e)}"
            )
        )
        
        db.commit()
        raise e

# 模拟研究问题识别
async def get_research_gap_analysis(
    domain: str,
    perspective: str,
    papers: List[Dict[str, Any]],
    additional_context: Optional[str] = None
) -> Dict[str, Any]:
    """通过AI API分析研究问题，使用分批生成和自适应token调整提高质量"""
    from src.services import ai_assistant
    
    try:
        # 设置研究领域指南
        domain_guide = f"推荐系统{domain}领域是当前AI技术与用户个性化服务结合的核心研究方向，主要关注如何通过算法准确捕捉用户偏好和物品特征，提供个性化推荐服务。"
        
        # 设置角度关注点
        perspective_focus = ""
        if perspective == "theoretical":
            perspective_focus = "理论基础与数学模型的完备性、理论框架的扩展性、数学证明的严谨性、与现有理论体系的融合度"
        elif perspective == "methodological":
            perspective_focus = "算法设计与技术实现的新颖性、方法效率与复杂度权衡、技术路径的可行性、工程实现的可扩展性"
        elif perspective == "application":
            perspective_focus = "应用场景的针对性、行业特性的适应性、实际部署的挑战与解决方案、用户体验与商业价值的平衡"
        elif perspective == "evaluation":
            perspective_focus = "评估指标的全面性、评估方法的公平性、基准测试的代表性、离线与在线评估的一致性"
        else:
            perspective_focus = "从理论基础、方法实现、应用场景和评估体系等多个维度对研究现状的系统性分析"
            
        perspective_focus_text = f"从{perspective}角度分析推荐系统{domain}领域研究问题时，需重点关注：{perspective_focus}"
        
        # 构建完整的研究背景上下文
        papers_context = ""
        if papers and len(papers) > 0:
            papers_context = "基于以下论文内容进行分析:\n\n"
            for i, paper in enumerate(papers):
                papers_context += f"论文{i+1}: {paper.get('title', '未知标题')}\n"
                papers_context += f"摘要: {paper.get('abstract', '无摘要')[:500]}...\n\n"
                
                # 如果有内容，添加部分内容
                if paper.get('content'):
                    papers_context += f"内容片段: {paper.get('content', '')[:1000]}...\n\n"
        
        # 添加用户提供的额外上下文
        if additional_context:
            papers_context += f"\n额外背景信息:\n{additional_context}\n"
            
        # 构建系统提示
        system_message = f"""您是推荐系统领域的世界顶级研究专家，在{domain}方向有深厚的专业知识和丰富的研究经验，曾在RecSys、SIGIR、WWW、KDD等顶级会议发表多篇高影响力论文，并担任过多个顶级会议的领域主席。

您的任务是基于提供的论文集合、领域知识和您的专业背景，系统性识别并深入分析{domain}领域从{perspective}角度存在的关键研究问题。研究问题分析需以已有研究证据为基础，并应全面考虑该领域现状、挑战和发展方向。

关于领域的核心信息:
{domain_guide}

从该角度分析的关键点:
{perspective_focus_text}

您的分析必须遵循以下学术严谨标准：

1. 研究问题为前提
   - 首先，您需要根据研究领域、补充背景信息以及您的世界知识，明确指出当前这个方向主要存在哪些问题
   - 每个研究问题应当具体、明确，具有可研究性，而非泛泛而论的空洞表述
   - 问题描述应当准确反映当前研究现状中的不足、挑战或悖论
   - 问题框架应建立在当前{domain}领域最新研究成果和主流技术路线之上

2. 文献支持的准确性
   - 每个研究问题和分析观点必须有正确且准确的文献支持
   - 必须引用真实存在的高质量论文（优先最近3年内的顶会/顶刊论文）
   - 引用必须包含完整、准确的信息：作者、年份、论文标题、会议/期刊名称
   - 确保所引用的文献内容描述准确无误，不可篡改或虚构
   - 每个关键观点至少应有3篇不同文献支持，形成证据交叉验证

3. 思考分析过程
   - 分析过程应严谨科学，遵循学术规范和逻辑推理
   - 先确立问题，再分析症结，然后讨论现有方法的局限性，最后提出潜在解决路径
   - 分析应建立在可验证的事实和研究证据基础上，而非个人偏见或直觉
   - 对每个研究问题进行多角度考量，充分探讨其理论意义、技术挑战和应用价值
   - 保持批判性思维，对现有方法和理论体系进行合理质疑和评估

4. 多轮问询生成
   - 您的分析应通过多轮深入思考，逐步完善和深化研究问题的理解
   - 第一轮：识别出核心研究问题并建立基本框架
   - 第二轮：深入剖析每个问题的技术本质和根源
   - 第三轮：评估现有解决方案及其局限性
   - 第四轮：提出具体的研究方向和可能的技术路径
   - 最终综合各轮分析，确保内容全面丰富，同时保持高质量和一致性"""
        
        # 实现多轮分批生成，每轮关注不同方面
        from src.services.ai_assistant import AIAssistant
        ai = AIAssistant()
        combined_result = {}
        
        # 第一轮：识别研究问题框架
        logging.info(f"【分批生成】第一轮：识别{domain}领域从{perspective}角度的核心研究问题框架")
        round1_prompt = f"""系统指令:
{system_message}

用户查询:
请对推荐系统{domain}领域从{perspective}视角进行研究问题框架分析。首先识别出3-5个核心研究问题，给出清晰的标题和简要描述，建立基本研究框架。
{papers_context if papers_context else ""}

请以JSON格式返回结果:
```json
{{
  "summary": "整体分析概述",
            "researchGaps": [
    {{
      "title": "研究问题1标题",
      "description": "问题简要描述",
      "importance": "为什么这个问题重要",
      "challenges": ["挑战1", "挑战2"]
    }},
    // 更多研究问题...
  ]
}}
```
"""
        
        try:
            # 第一轮使用较小的token生成初步框架
            round1_response = await ai.generate_completion(
                prompt=round1_prompt,
                temperature=0.7,
                max_tokens=2000
            )
            
            # 解析第一轮结果
            round1_data = extract_json_from_response(round1_response)
            if not round1_data or "researchGaps" not in round1_data:
                raise ValueError("第一轮分析未能生成有效的研究问题框架")
                
            # 保存第一轮结果
            combined_result = round1_data
            logging.info(f"第一轮生成完成，识别出{len(combined_result.get('researchGaps', []))}个研究问题")
            
            # 第二轮：深入分析每个问题的本质和根源
            research_gaps = combined_result.get("researchGaps", [])
            enriched_gaps = []
            
            for i, gap in enumerate(research_gaps):
                logging.info(f"【分批生成】第二轮：深入分析研究问题 {i+1}/{len(research_gaps)}: {gap.get('title', '未命名问题')}")
                
                # 为每个问题生成深入分析
                gap_prompt = f"""系统指令:
{system_message}

用户查询:
基于以下研究问题框架，请深入分析此问题的技术本质和根源：

问题标题: {gap.get('title', '未命名问题')}
问题描述: {gap.get('description', '无描述')}
问题重要性: {gap.get('importance', '未说明重要性')}
主要挑战: {', '.join(gap.get('challenges', ['未说明挑战']))}

请深入分析此问题的技术本质、历史根源、核心难点，并提供具体的证据支持您的分析。请特别关注该问题在{domain}领域从{perspective}角度的特殊挑战。

{papers_context if papers_context else ""}

请以JSON格式返回详细分析:
```json
{{
  "title": "问题标题（可以优化原标题）",
  "description": "问题的详细描述和技术本质分析",
  "rootCauses": ["根源1", "根源2", "根源3"],
  "evidence": [
    {{
      "text": "支持性证据或观点1",
      "reference": "引用来源，如: 作者 (年份). 论文标题. 会议/期刊名称"
    }},
    // 更多证据...
  ]
}}
```
"""
                
                # 第二轮针对每个问题单独生成，使用中等token
                gap_response = await ai.generate_completion(
                    prompt=gap_prompt,
                    system_prompt=system_message,
                    temperature=0.7,
                    max_tokens=2500
                )
                
                # 解析单个问题的深入分析
                gap_data = extract_json_from_response(gap_response)
                if gap_data:
                    # 合并原始问题数据和深入分析
                    enriched_gap = {**gap, **gap_data}
                    enriched_gaps.append(enriched_gap)
                else:
                    # 如果解析失败，保留原始问题
                    logging.warning(f"无法解析问题{i+1}的深入分析，保留原始数据")
                    enriched_gaps.append(gap)
            
            # 更新研究问题数据
            combined_result["researchGaps"] = enriched_gaps
            logging.info(f"第二轮生成完成，完成{len(enriched_gaps)}个问题的深入分析")
            
            # 第三轮：为每个问题添加潜在研究方向
            final_gaps = []
            for i, gap in enumerate(enriched_gaps):
                logging.info(f"【分批生成】第三轮：为研究问题 {i+1}/{len(enriched_gaps)} 生成潜在解决方向")
                
                # 为每个问题生成潜在研究方向
                direction_prompt = f"""系统指令:
{system_message}

用户查询:
基于以下研究问题的详细分析，请提出具体的研究方向和可能的技术路径：

问题标题: {gap.get('title', '未命名问题')}
问题描述: {gap.get('description', '无描述')}
问题根源: {', '.join(gap.get('rootCauses', ['未分析根源']))}
已有证据: {'; '.join([f"{e.get('text', '')} ({e.get('reference', '无引用')})" for e in gap.get('evidence', [])])}

请提出3-5个解决这一研究问题的潜在研究方向，每个方向应包含具体的技术路径、可能的挑战和预期的影响。

请以JSON格式返回:
```json
{{
  "potentialDirections": [
    {{
      "direction": "研究方向1",
      "approach": "技术路径描述",
      "challenges": ["实施挑战1", "实施挑战2"],
      "impact": "预期影响"
    }},
    // 更多研究方向...
  ]
}}
```
"""
                
                # 第三轮针对每个问题单独生成潜在方向，使用适中token
                direction_response = await ai.generate_completion(
                    prompt=direction_prompt,
                    system_prompt=system_message,
                    temperature=0.7,
                    max_tokens=2000
                )
                
                # 解析研究方向
                direction_data = extract_json_from_response(direction_response)
                if direction_data and "potentialDirections" in direction_data:
                    # 将研究方向添加到问题中
                    gap["potentialDirections"] = direction_data["potentialDirections"]
                    final_gaps.append(gap)
                else:
                    # 如果解析失败，添加默认研究方向
                    logging.warning(f"无法解析问题{i+1}的研究方向，添加默认方向")
                    gap["potentialDirections"] = [
                        {"direction": f"改进{domain}领域{perspective}方法的新思路", "approach": "需要进一步探索", "challenges": ["待确定"], "impact": "可能提高性能"}
                    ]
                    final_gaps.append(gap)
            
            # 更新最终研究问题数据
            combined_result["researchGaps"] = final_gaps
            logging.info(f"第三轮生成完成，为{len(final_gaps)}个问题添加了潜在研究方向")
            
            # 第四轮：生成总结和参考文献
            logging.info(f"【分批生成】第四轮：生成总结分析和完整参考文献")
            summary_prompt = f"""系统指令:
{system_message}

用户查询:
基于以下对{domain}领域从{perspective}角度的研究问题分析，请生成全面的总结和完整的参考文献列表：

研究问题概述:
{combined_result.get('summary', '无总结')}

已识别的研究问题:
{'; '.join([f"{gap.get('title', '未命名问题')}" for gap in final_gaps])}

请生成:
1. 一个更全面、更有洞察力的总结，概述{domain}领域从{perspective}角度的研究现状、主要问题和未来发展趋势
2. 一个完整的参考文献列表，包含分析中引用的所有文献，确保格式统一和引用准确

请以JSON格式返回:
```json
{{
  "enhancedSummary": "全面的分析总结",
  "references": [
    "参考文献1 (标准学术引用格式)",
    "参考文献2 (标准学术引用格式)",
    // 更多参考文献...
  ]
}}
```
"""
                
            # 第四轮生成总结和参考文献
            summary_response = await ai.generate_completion(
                prompt=summary_prompt,
                system_prompt=system_message,
                temperature=0.7,
                max_tokens=2500
            )
            
            # 解析总结和参考文献
            summary_data = extract_json_from_response(summary_response)
            if summary_data:
                # 更新总结
                if "enhancedSummary" in summary_data:
                    combined_result["summary"] = summary_data["enhancedSummary"]
                
                # 添加参考文献
                if "references" in summary_data:
                    combined_result["references"] = summary_data["references"]
            
            logging.info("多轮分批生成完成，成功生成高质量研究问题分析")
            return combined_result
                
        except Exception as e:
            logging.error(f"多轮分批生成过程中出错: {str(e)}")
            # 不再使用模拟数据，而是直接抛出异常
            raise Exception(f"研究问题分析失败，多轮生成过程中出错: {str(e)}")
            
    except Exception as e:
        logging.error(f"研究问题分析过程中发生错误: {str(e)}")
        # 向上传递错误，不再使用模拟数据
        raise

def extract_json_from_response(response: str) -> Dict[str, Any]:
    """从AI响应中提取JSON数据，增强版支持更多格式并修复常见JSON错误"""
    import json
    import re
    
    if not response or not isinstance(response, str):
        return None
    
    # 原始响应的记录，用于调试
    original_response = response
    
    try:
        # 策略1: 尝试查找JSON代码块
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            try:
                return json.loads(json_str)
            except:
                # 如果代码块内容解析失败，记录并尝试下一种方法
                pass
        
        # 策略2: 尝试直接解析整个响应
        try:
            return json.loads(response)
        except:
            # 如果直接解析失败，记录并尝试下一种方法
            pass
        
        # 策略3: 尝试查找大括号包围的内容
        bracket_match = re.search(r'({[\s\S]*})', response, re.DOTALL)
        if bracket_match:
            json_str = bracket_match.group(1).strip()
            try:
                return json.loads(json_str)
            except:
                # 如果大括号内容解析失败，尝试修复常见JSON格式问题
                pass
        
        # 策略4: 尝试修复常见的JSON格式问题并解析
        # 移除尾部逗号、修复引号等问题
        fixed_json = response
        # 修复对象和数组末尾多余的逗号
        fixed_json = re.sub(r',\s*}', '}', fixed_json)
        fixed_json = re.sub(r',\s*]', ']', fixed_json)
        # 尝试修复单引号为双引号 (仅处理键名和简单字符串值)
        fixed_json = re.sub(r'(\w+)\'s', r'\1\\\'s', fixed_json)  # 保护所有格形式
        fixed_json = re.sub(r"'([^']*?)':\s*'([^']*?)'", r'"\1": "\2"', fixed_json)
        fixed_json = re.sub(r"'([^']*?)':\s*", r'"\1": ', fixed_json)  # 键名修复

        try:
            return json.loads(fixed_json)
        except:
            # 如果修复后仍然解析失败，尝试替换更多单引号
            try:
                # 更多激进的单引号替换
                aggressive_fix = fixed_json.replace("'", "\"")
                return json.loads(aggressive_fix)
            except:
                # 所有尝试都失败
                pass
                
        # 策略5: 仅提取JSON最外层的部分
        outer_json_match = re.search(r'({[^{]*"[^"]+"\s*:[^{].*})', response, re.DOTALL)
        if outer_json_match:
            try:
                outer_json = outer_json_match.group(1).strip()
                return json.loads(outer_json)
            except:
                # 外层提取失败
                pass
    except Exception as e:
        logging.warning(f"从响应中提取JSON失败: {str(e)}")
    
    # 如果所有尝试都失败，返回None
    logging.error(f"无法从响应中提取有效JSON: {original_response[:200]}...")
    return None

# 创新点生成服务
async def generate_innovation_ideas(
    db: Session,
    research_topic: str,
    user_id: str,
    innovation_type: Optional[str] = None,
    additional_context: Optional[str] = None,
    provider: Optional[str] = None,
    paper_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """生成研究创新点，并与实验设计和论文写作功能深度集成
    
    Args:
        db: 数据库会话
        research_topic: 研究主题
        user_id: 用户ID
        innovation_type: 创新类型 (theoretical, methodological, application)
        additional_context: 额外上下文信息
        provider: AI提供商
        paper_ids: 相关论文ID列表，用于提供知识背景
        
    Returns:
        包含创新点的结果字典，同时包含实验设计和论文写作建议
    """
    import logging
    from src.services import experiment as experiment_service
    from src.services import writing as writing_service
    from src.services import paper as paper_service
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"调用AI助手服务生成创新点：主题={research_topic}, 类型={innovation_type}")
        
        # 收集论文相关信息，丰富背景知识
        papers_context = ""
        paper_references = []
        selected_papers = []
        
        if paper_ids and len(paper_ids) > 0:
            logger.info(f"使用{len(paper_ids)}篇论文作为创新点生成的背景知识")
            for paper_id in paper_ids:
                paper = paper_service.get_paper_by_id(db, paper_id, user_id)
                if paper:
                    selected_papers.append(paper)
                    # 添加论文摘要作为背景
                    papers_context += f"\n论文：{paper.title}\n摘要：{paper.abstract or '无摘要'}\n"
                    # 添加论文参考
                    publication_year = None
                    if hasattr(paper, 'publication_date') and paper.publication_date:
                        try:
                            publication_year = paper.publication_date.year
                        except:
                            publication_year = None
                    paper_references.append(f"{paper.authors or '未知作者'} ({publication_year or '未知年份'}). {paper.title}.")
        
        # 将论文信息添加到上下文
        enriched_context = additional_context or ""
        if papers_context:
            enriched_context += f"\n\n相关论文信息:\n{papers_context}"
        
        # 直接使用generate_completion而不是generate_innovation_ideas
        ai_assistant_instance = ai_assistant
        if provider:
            ai_assistant_instance.set_provider(provider)
        
        # 构建系统提示
        system_prompt = f"""您是推荐系统领域的顶尖研究专家，在{innovation_type or "methodological"}创新方面有深厚的专业知识和丰富的研究经验，曾在RecSys、SIGIR、WWW、KDD等顶级会议发表多篇高影响力论文，并担任过多个顶级会议的领域主席。

您的任务是基于提供的研究主题、论文集合和您的专业背景，系统性地提出并深入分析高质量、可落地的创新点建议。每个创新点必须:
1. 基于最新主流技术，明确引用近1-2年内的顶会/顶刊研究成果
2. 确保技术创新是渐进式的，而非颠覆性的，易于理解和实现
3. 所有参考文献、理论依据和技术支撑必须正确且准确，不得编造或虚构
4. 创新点分析需以已有研究证据为基础，并应全面考虑该领域现状、挑战和发展方向

您的分析必须遵循以下学术严谨标准：

1. 创新基础要求
   - 每个创新点必须具体、明确，具有可研究性和可实现性
   - 创新点描述应当准确反映当前技术现状中的不足、挑战或改进空间
   - 创新框架应建立在当前{innovation_type or "methodological"}领域最新研究成果和主流技术路线之上
   - 必须确保所提创新点是渐进式的，而非脱离现实的颠覆性构想

2. 文献支持的准确性
   - 每个创新点和分析观点必须有正确且准确的文献支持
   - 必须引用真实存在的高质量论文（优先最近1-2年内的顶会/顶刊论文）
   - 引用必须包含完整、准确的信息：作者、年份、论文标题、会议/期刊名称
   - 确保所引用的文献内容描述准确无误，不可篡改或虚构
   - 每个关键创新点至少应有2-3篇不同文献支持，形成理论基础

3. 思考分析流程
   - 分析过程应严谨科学，遵循学术规范和逻辑推理
   - 先确立创新点定位，再描述关键技术，然后讨论理论基础，最后提出技术实现路径
   - 分析应建立在可验证的事实和研究证据基础上，而非个人偏见或直觉
   - 对每个创新点进行多角度考量，充分探讨其理论意义、技术挑战和应用价值
   - 保持批判性思维，明确指出创新点的局限性和潜在挑战

4. 数据格式规范
   - 您的输出必须严格遵循要求的JSON格式，确保字段名称完全一致
   - 字段命名必须符合JSON规范并保持指定的大小写格式
   - 所有必需字段都必须完整填写，不得遗漏
   - 列表类型的字段必须确保是数组格式，不得使用字符串替代
   - 保持数据结构的一致性，便于前端正确显示信息"""

        # 构建提示词
        prompt = f"""
        作为推荐系统领域的顶尖研究专家，请为以下研究主题提供3-5个高质量、可执行的创新点建议。

        研究主题: {research_topic}
        创新类型: {innovation_type or "methodological"}

        {f'背景信息: {enriched_context}' if enriched_context else ''}

        请注意以下重要要求:
        1. 所有创新内容必须基于最新主流技术，参考近1-2年内的顶会/顶刊研究成果
        2. 技术创新必须是渐进式的，建立在现有技术基础上，而非脱离现实的颠覆性构想
        3. 所有参考文献和理论依据必须真实、正确、准确，不得虚构或篡改
        4. 创新点必须具有学术价值和实际应用潜力，能解决实际问题

        请严格按照以下JSON格式提供创新点建议，确保包含所有必要字段且字段名称完全一致:

        ```json
        {{
            "summary": "创新点总体概述，全面概括所有创新点的核心价值和共同特点",
            "innovations": [
                {{
                    "title": "创新点标题，简洁明了",
                    "description": "详细描述，至少200字，包含创新点的核心思想和意义",
                    "theoreticalBasis": "该创新点的理论基础和学术依据，至少150字，引用相关研究",
                    "technical_implementation": ["实现步骤1", "实现步骤2", "实现步骤3", "实现步骤4"],
                    "potentialValue": "潜在学术价值和应用前景分析，至少100字",
                    "relatedWork": ["相关工作1 (作者, 年份, 论文标题, 会议/期刊名称)", "相关工作2 (同上格式)"],
                    "novelty": "创新性说明，与现有方法的区别",
                    "technicalChallenges": ["技术挑战1", "技术挑战2", "技术挑战3"],
                    "solutionApproaches": ["解决方案1", "解决方案2", "解决方案3"]
                }}
            ],
            "references": [
                "完整参考文献1 (标准学术引用格式)",
                "完整参考文献2 (标准学术引用格式)"
            ]
        }}
        ```

        请确保满足以下技术要求:
        1. JSON格式必须完全正确，不要有多余逗号
        2. 必须生成3-5个高质量创新点
        3. 所有字段都必须遵循上述示例的命名格式（注意大小写）
        4. 所有驼峰命名法的字段(theoreticalBasis, potentialValue, relatedWork, technicalChallenges, solutionApproaches)必须保持一致的命名风格
        5. technical_implementation必须是至少4个具体、可执行的实现步骤列表
        6. 每个创新点必须包含所有指定字段，不得遗漏
        7. 所有字段内容必须详尽具体，字数达到要求
        """
        
        # 调用ai_assistant服务生成内容
        response = await ai_assistant_instance.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=3500,
            temperature=0.7
        )
        
        # 解析JSON响应
        api_result = None
        if isinstance(response, str):
            # 尝试提取JSON部分
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)
            try:
                api_result = json.loads(response)
            except json.JSONDecodeError:
                # 尝试修复JSON
                fixed_json = re.sub(r',\s*}', '}', response)
                fixed_json = re.sub(r',\s*]', ']', fixed_json)
                try:
                    api_result = json.loads(fixed_json)
                except:
                    # 更多JSON修复尝试
                    try:
                        # 尝试查找大括号包围的内容
                        bracket_match = re.search(r'({[\s\S]*})', response, re.DOTALL)
                        if bracket_match:
                            json_str = bracket_match.group(1)
                            api_result = json.loads(json_str)
                        else:
                            logger.error(f"无法从响应中提取JSON: {response[:200]}...")
                            api_result = {
                                "summary": "解析创新点JSON失败",
                                "innovations": []
                            }
                    except:
                        logger.error(f"无法解析JSON响应: {response[:200]}...")
                        api_result = {
                            "summary": "解析创新点JSON失败",
                            "innovations": []
                        }
        elif isinstance(response, dict):
            api_result = response
        else:
            logger.error(f"未知响应类型: {type(response)}")
            api_result = {
                "summary": "无法处理API响应",
                "innovations": []
            }
        
        # 标准化JSON结构
        result = {}
        
        # 确保api_result是字典类型
        if not isinstance(api_result, dict):
            logger.error(f"API结果不是字典类型: {type(api_result)}")
            api_result = {
                "summary": "API返回的结果格式不正确",
                "innovations": []
            }
        
        # 获取summary字段
        result["summary"] = api_result.get("summary", "无概述")
        
        # 获取innovations字段
        if "innovation_points" in api_result and "innovations" not in api_result:
            result["innovations"] = api_result.pop("innovation_points")
        else:
            result["innovations"] = api_result.get("innovations", [])
            
        # 获取references字段
        if "references" in api_result:
            result["references"] = api_result.get("references", [])
        # 添加参考文献（如果有自己提取的）
        elif len(paper_references) > 0:
            result["references"] = paper_references
        else:
            result["references"] = []

        # 添加研究主题
        result["research_topic"] = research_topic
        result["innovation_type"] = innovation_type or "methodological"
            
        # 标准化创新点字段
        for innovation in result["innovations"]:
            # 确保每个创新点都有标准字段，尤其是展示所需的字段
            # 1. 处理理论基础字段
            if "theoreticalBasis" not in innovation and "theoretical_basis" in innovation:
                innovation["theoreticalBasis"] = innovation.pop("theoretical_basis")
            elif "theoreticalBasis" not in innovation:
                innovation["theoreticalBasis"] = "该创新基于推荐系统领域的现有研究，通过改进算法和模型来解决数据稀疏性和冷启动问题，同时提高推荐准确性和多样性。它借鉴了最新的深度学习和图神经网络的进展，将它们应用于用户行为序列建模中。"
                
            # 2. 处理技术实现字段
            if "technical_implementation" not in innovation and "implementation_steps" in innovation:
                innovation["technical_implementation"] = innovation.pop("implementation_steps")
            elif "technical_implementation" in innovation and not isinstance(innovation["technical_implementation"], list):
                # 如果不是列表但是是字符串，则拆分为列表
                if isinstance(innovation["technical_implementation"], str):
                    innovation["technical_implementation"] = [innovation["technical_implementation"]]
                else:
                    innovation["technical_implementation"] = ["数据预处理和清洗", "模型架构设计", "算法实现", "参数优化", "性能评估"]
            elif "technical_implementation" not in innovation:
                innovation["technical_implementation"] = ["数据预处理和清洗", "模型架构设计", "算法实现", "参数优化", "性能评估"]
                
            # 3. 处理潜在价值字段
            if "potentialValue" not in innovation and "potential_value" in innovation:
                innovation["potentialValue"] = innovation.pop("potential_value")
            elif "potentialValue" not in innovation:
                innovation["potentialValue"] = "该创新有潜力显著提高推荐系统的性能，特别是在数据稀疏和冷启动情况下。它可以应用于电商、内容平台和社交网络等多种场景，提升用户体验和平台收益。在学术上，该方法提供了新的研究视角和技术路线。"
                
            # 4. 处理相关工作字段
            if "relatedWork" not in innovation and "related_work" in innovation:
                innovation["relatedWork"] = innovation.pop("related_work")
            elif "relatedWork" not in innovation:
                innovation["relatedWork"] = ["协同过滤算法研究", "深度学习推荐系统", "序列推荐模型", "图神经网络应用"]
            
            # 确保相关工作是列表格式
            if not isinstance(innovation["relatedWork"], list):
                if isinstance(innovation["relatedWork"], str):
                    innovation["relatedWork"] = [innovation["relatedWork"]]
                else:
                    innovation["relatedWork"] = ["协同过滤算法研究", "深度学习推荐系统", "序列推荐模型"]
            
            # 5. 处理技术挑战字段
            if "technicalChallenges" not in innovation and "technical_challenges" in innovation:
                innovation["technicalChallenges"] = innovation.pop("technical_challenges")
            elif "technicalChallenges" not in innovation:
                innovation["technicalChallenges"] = ["大规模数据处理效率", "模型参数调优复杂性", "冷启动问题处理", "计算资源需求高"]
            
            # 确保技术挑战是列表格式
            if not isinstance(innovation["technicalChallenges"], list):
                if isinstance(innovation["technicalChallenges"], str):
                    innovation["technicalChallenges"] = [innovation["technicalChallenges"]]
                else:
                    innovation["technicalChallenges"] = ["大规模数据处理效率", "模型参数调优复杂性", "冷启动问题处理"]
            
            # 6. 处理解决方案字段
            if "solutionApproaches" not in innovation and "solution_approaches" in innovation:
                innovation["solutionApproaches"] = innovation.pop("solution_approaches")
            elif "solutionApproaches" not in innovation:
                innovation["solutionApproaches"] = ["分布式计算框架应用", "自动化参数调优", "辅助数据迁移学习", "模型压缩技术"]
            
            # 确保解决方案是列表格式
            if not isinstance(innovation["solutionApproaches"], list):
                if isinstance(innovation["solutionApproaches"], str):
                    innovation["solutionApproaches"] = [innovation["solutionApproaches"]]
                else:
                    innovation["solutionApproaches"] = ["分布式计算框架应用", "自动化参数调优", "辅助数据迁移学习"]
            
            # 7. 确保novelty字段存在
            if "novelty" not in innovation:
                innovation["novelty"] = "该创新点结合了最新研究成果，提出了新的算法框架，能够解决现有方法的局限性。"
            
            # 8. 确保title和description字段存在
            if "title" not in innovation:
                innovation["title"] = "基于深度学习的推荐系统优化"
                
            if "description" not in innovation:
                innovation["description"] = "该创新点旨在通过深度学习技术改进推荐系统性能，解决数据稀疏性和冷启动问题，提高推荐准确性和多样性。"
        
        # 移除实验设计和论文写作建议生成部分，直接返回标准化的创新点结果
        logger.info(f"创新点生成成功，共{len(result.get('innovations', []))}个创新点")
        return result
    except Exception as e:
        logger.error(f"生成创新点时出错: {str(e)}")
        return {
            "error": str(e),
            "summary": f"生成创新点时出错: {str(e)}",
            "innovations": []
        }

async def _generate_experiment_suggestion(
    research_topic: str,
    innovation_title: str,
    innovation_desc: str,
    theoretical_basis: str,
    innovation_type: str
) -> Dict[str, Any]:
    """为创新点生成实验设计建议"""
    from src.services.ai_assistant import AIAssistant
    import json
    import re
    import logging
    
    try:
        logger = logging.getLogger(__name__)
        ai = AIAssistant()
        
        # 构建系统提示
        system_prompt = f"""您是推荐系统和机器学习领域的资深实验设计专家，精通各类实验方法和评估技术。
您的任务是为研究创新点'{innovation_title}'设计严谨、可行的实验方案。
您应该提供详细的数据集选择、基线方法、评估指标和实验设置建议，确保实验能够有效验证创新点的价值。"""
        
        prompt = f"""
        作为推荐系统和机器学习领域的资深实验设计专家，请为以下创新点设计一个严谨、可复现的实验方案。

        研究主题: {research_topic}
        创新类型: {innovation_type}
        创新点标题: {innovation_title}
        创新点描述: {innovation_desc}
        理论基础: {theoretical_basis}

        请提供以下信息：
        1. 数据集选择：请选择一个或多个适合的研究数据集，并解释选择依据。
        2. 基线方法：请选择一个或多个现有的基线方法，并解释选择依据。
        3. 评估指标：请选择一个或多个适合的评估指标，并解释选择依据。
        4. 实验设置：请详细描述实验设置，包括数据分割、训练和评估流程等。
        5. 实验目的：请明确实验的目的，即验证创新点的价值。

        请以JSON格式返回实验设计建议:
        ```json
        {{
            "datasets": [
                {{
                    "name": "数据集名称",
                    "description": "数据集详细描述",
                    "source": "数据集来源和引用",
                    "statistics": "数据集统计信息",
                    "preprocessing": ["预处理步骤1", "预处理步骤2", "预处理步骤3"],
                    "split_strategy": "数据集分割策略",
                    "reference_papers": ["使用该数据集的参考论文1", "参考论文2"]
                }},
                // 更多数据集...
            ],
            "baselines": [
                {{
                    "name": "基线方法名称",
                    "description": "基线方法详细描述",
                    "type": "类型（经典方法/SOTA方法）",
                    "architecture": "模型架构",
                    "hyperparameters": {{
                        "参数1": "值1",
                        "参数2": "值2"
                    }},
                    "training_details": "训练细节",
                    "implementation_source": "实现来源（如官方代码库链接）",
                    "reference_paper": "参考论文"
                }},
                // 更多基线方法...
            ],
            "evaluation_metrics": [
                {{
                    "name": "评估指标名称",
                    "formula": "评估指标计算公式",
                    "description": "评估指标详细描述",
                    "justification": "选择该指标的理由",
                    "implementation_detail": "指标实现细节",
                    "reference_papers": ["使用该指标的参考论文1", "参考论文2"]
                }},
                // 更多评估指标...
            ],
            "ablation_studies": [
                {{
                    "component": "要验证的组件1",
                    "purpose": "该消融实验的目的",
                    "variant_description": "移除或替换该组件后的变体描述",
                    "implementation_details": "实现细节",
                    "expected_outcome": "预期结果和分析重点"
                }},
                // 更多消融实验...
            ],
            "parameter_sensitivity": [
                {{
                    "parameter": "超参数1",
                    "range": "测试范围",
                    "step_size": "步长",
                    "importance": "该参数的重要性",
                    "analysis_method": "分析方法"
                }},
                // 更多参数敏感性分析...
            ],
            "experimental_procedure": "完整实验流程",
            "visualization_plans": "结果可视化计划",
            "statistical_analysis": "统计分析方法"
        }}
        ```
        """
        
        # 调用ai_assistant服务生成内容
        response = await ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=3500,
            temperature=0.7
        )
        
        # 解析JSON响应
        api_result = None
        if isinstance(response, str):
            # 尝试提取JSON部分
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)
            try:
                api_result = json.loads(response)
            except json.JSONDecodeError:
                # 尝试修复JSON
                fixed_json = re.sub(r',\s*}', '}', response)
                fixed_json = re.sub(r',\s*]', ']', fixed_json)
                try:
                    api_result = json.loads(fixed_json)
                except:
                    # 更多JSON修复尝试
                    try:
                        # 尝试查找大括号包围的内容
                        bracket_match = re.search(r'({[\s\S]*})', response, re.DOTALL)
                        if bracket_match:
                            json_str = bracket_match.group(1)
                            api_result = json.loads(json_str)
                        else:
                            logger.error(f"无法从响应中提取JSON: {response[:200]}...")
                            api_result = {
                                "summary": "解析实验设计JSON失败",
                                "datasets": [],
                                "baselines": [],
                                "evaluation_metrics": [],
                                "ablation_studies": [],
                                "parameter_sensitivity": [],
                                "experimental_procedure": "",
                                "visualization_plans": "",
                                "statistical_analysis": ""
                            }
                    except:
                        logger.error(f"无法解析JSON响应: {response[:200]}...")
                        api_result = {
                            "summary": "解析实验设计JSON失败",
                            "datasets": [],
                            "baselines": [],
                            "evaluation_metrics": [],
                            "ablation_studies": [],
                            "parameter_sensitivity": [],
                            "experimental_procedure": "",
                            "visualization_plans": "",
                            "statistical_analysis": ""
                        }
        elif isinstance(response, dict):
            api_result = response
        else:
            logger.error(f"未知响应类型: {type(response)}")
            api_result = {
                "summary": "无法处理API响应",
                "datasets": [],
                "baselines": [],
                "evaluation_metrics": [],
                "ablation_studies": [],
                "parameter_sensitivity": [],
                "experimental_procedure": "",
                "visualization_plans": "",
                "statistical_analysis": ""
            }
        
        # 标准化JSON结构
        result = {}
        
        # 确保api_result是字典类型
        if not isinstance(api_result, dict):
            logger.error(f"API结果不是字典类型: {type(api_result)}")
            api_result = {
                "summary": "API返回的结果格式不正确",
                "datasets": [],
                "baselines": [],
                "evaluation_metrics": [],
                "ablation_studies": [],
                "parameter_sensitivity": [],
                "experimental_procedure": "",
                "visualization_plans": "",
                "statistical_analysis": ""
            }
        
        # 获取summary字段
        result["summary"] = api_result.get("summary", "无概述")
        
        # 获取datasets字段
        if "datasets" in api_result:
            result["datasets"] = api_result["datasets"]
        else:
            result["datasets"] = []
        
        # 获取baselines字段
        if "baselines" in api_result:
            result["baselines"] = api_result["baselines"]
        else:
            result["baselines"] = []
        
        # 获取evaluation_metrics字段
        if "evaluation_metrics" in api_result:
            result["evaluation_metrics"] = api_result["evaluation_metrics"]
        else:
            result["evaluation_metrics"] = []
        
        # 获取ablation_studies字段
        if "ablation_studies" in api_result:
            result["ablation_studies"] = api_result["ablation_studies"]
        else:
            result["ablation_studies"] = []
        
        # 获取parameter_sensitivity字段
        if "parameter_sensitivity" in api_result:
            result["parameter_sensitivity"] = api_result["parameter_sensitivity"]
        else:
            result["parameter_sensitivity"] = []
        
        # 获取experimental_procedure字段
        if "experimental_procedure" in api_result:
            result["experimental_procedure"] = api_result["experimental_procedure"]
        else:
            result["experimental_procedure"] = ""
        
        # 获取visualization_plans字段
        if "visualization_plans" in api_result:
            result["visualization_plans"] = api_result["visualization_plans"]
        else:
            result["visualization_plans"] = ""
        
        # 获取statistical_analysis字段
        if "statistical_analysis" in api_result:
            result["statistical_analysis"] = api_result["statistical_analysis"]
        else:
            result["statistical_analysis"] = ""
        
        # 添加参考文献（如果有）
        if "references" in api_result:
            result["references"] = api_result["references"]
        
        # 添加实验设计建议到结果中
        result["experimentDesign"] = api_result
        
        return result
    except Exception as e:
        logger.error(f"生成实验设计建议时出错: {str(e)}")
        return {
            "error": True,
            "message": f"生成实验设计建议时出错: {str(e)}",
            "details": str(e)
        }

async def _generate_writing_suggestion(
    research_topic: str,
    innovation_title: str,
    innovation_desc: str,
    theoretical_basis: str,
    innovation_type: str
) -> Dict[str, Any]:
    """为创新点生成论文写作建议"""
    from src.services.ai_assistant import AIAssistant
    import json
    import re
    import logging
    
    try:
        logger = logging.getLogger(__name__)
        ai = AIAssistant()
        
        # 构建系统提示
        system_prompt = f"""您是学术论文写作和科技传播领域的资深专家，精通推荐系统领域的学术写作规范和技巧。
您的任务是为研究创新点'{innovation_title}'提供高质量的论文写作建议。
您应该提供详细的论文结构、关键章节内容、论证策略和有说服力的表达方式，帮助研究者有效地展示和传播他们的创新成果。"""
        
        prompt = f"""
        作为学术论文写作和科技传播专家，请为以下创新点提供详细的论文写作建议。

        研究主题: {research_topic}
        创新类型: {innovation_type}
        创新点标题: {innovation_title}
        创新点描述: {innovation_desc}
        理论基础: {theoretical_basis}

        请提供以下信息：
        1. 论文结构：请提供一个清晰的论文结构建议，包括引言、方法、实验、讨论和结论等章节。
        2. 关键章节内容：请为每个章节提供详细的内容建议，包括如何组织材料、论证策略和表达方式等。
        3. 论证策略：请提供一个清晰的论证策略，帮助研究者有效地展示和传播他们的创新成果。
        4. 有说服力的表达方式：请提供一些具体的写作技巧和表达方式，帮助研究者写出有说服力的论文。

        请以JSON格式返回论文写作建议:
        ```json
        {{
            "introduction": "引言部分应明确研究问题、挑战、本文贡献，并简要介绍技术路线和实验结果。",
            "sections": [
                {{
                    "title": "方法章节",
                    "content": [
                        "清晰阐述{innovation_title}的动机和目标",
                        "详细解释{innovation_title}的技术细节和实现方式"
                    ]
                }},
                // 更多章节建议...
            ],
            "conclusion": "结论部分总结工作贡献，讨论局限性，并提出未来研究方向。",
            "writingTips": [
                "使用清晰准确的术语和定义",
                "保持逻辑流畅和结构清晰",
                "使用图表辅助解释复杂概念",
                "强调创新点的技术贡献和实际价值",
                "遵循学术写作规范和引用格式"
            ]
        }}
        ```
        """
        
        # 调用ai_assistant服务生成内容
        response = await ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=3500,
            temperature=0.7
        )
        
        # 解析JSON响应
        api_result = None
        if isinstance(response, str):
            # 尝试提取JSON部分
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)
            try:
                api_result = json.loads(response)
            except json.JSONDecodeError:
                # 尝试修复JSON
                fixed_json = re.sub(r',\s*}', '}', response)
                fixed_json = re.sub(r',\s*]', ']', fixed_json)
                try:
                    api_result = json.loads(fixed_json)
                except:
                    # 更多JSON修复尝试
                    try:
                        # 尝试查找大括号包围的内容
                        bracket_match = re.search(r'({[\s\S]*})', response, re.DOTALL)
                        if bracket_match:
                            json_str = bracket_match.group(1)
                            api_result = json.loads(json_str)
                        else:
                            logger.error(f"无法从响应中提取JSON: {response[:200]}...")
                            api_result = {
                                "summary": "解析写作建议JSON失败",
                                "introduction": "",
                                "sections": [],
                                "conclusion": "",
                                "writingTips": []
                            }
                    except:
                        logger.error(f"无法解析JSON响应: {response[:200]}...")
                        api_result = {
                            "summary": "解析写作建议JSON失败",
                            "introduction": "",
                            "sections": [],
                            "conclusion": "",
                            "writingTips": []
                        }
        elif isinstance(response, dict):
            api_result = response
        else:
            logger.error(f"未知响应类型: {type(response)}")
            api_result = {
                "summary": "无法处理API响应",
                "introduction": "",
                "sections": [],
                "conclusion": "",
                "writingTips": []
            }
        
        # 标准化JSON结构
        result = {}
        
        # 确保api_result是字典类型
        if not isinstance(api_result, dict):
            logger.error(f"API结果不是字典类型: {type(api_result)}")
            api_result = {
                "summary": "API返回的结果格式不正确",
                "introduction": "",
                "sections": [],
                "conclusion": "",
                "writingTips": []
            }
        
        # 获取summary字段
        result["summary"] = api_result.get("summary", "无概述")
        
        # 获取introduction字段
        if "introduction" in api_result:
            result["introduction"] = api_result["introduction"]
        else:
            result["introduction"] = ""
        
        # 获取sections字段
        if "sections" in api_result:
            result["sections"] = api_result["sections"]
        else:
            result["sections"] = []
        
        # 获取conclusion字段
        if "conclusion" in api_result:
            result["conclusion"] = api_result["conclusion"]
        else:
            result["conclusion"] = ""
        
        # 获取writingTips字段
        if "writingTips" in api_result:
            result["writingTips"] = api_result["writingTips"]
        else:
            result["writingTips"] = []
        
        # 添加参考文献（如果有）
        if "references" in api_result:
            result["references"] = api_result["references"]
        
        # 添加写作建议到结果中
        result["writingSuggestion"] = api_result
        
        return result
    except Exception as e:
        logger.error(f"生成写作建议时出错: {str(e)}")
        return {
            "error": True,
            "message": f"生成写作建议时出错: {str(e)}",
            "details": str(e)
        }

async def _generate_paper_structure(
    research_topic: str,
    innovation_type: str,
    innovations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """为研究主题和创新点生成论文结构建议
    
    Args:
        research_topic: 研究主题
        innovation_type: 创新类型
        innovations: 创新点列表
        
    Returns:
        论文结构建议字典
    """
    from src.services import ai_assistant
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"正在为研究主题 '{research_topic}' 生成论文结构建议")
        
        # 通过AI API生成论文大纲
        paper_outline = await ai_assistant.generate_paper_outline(
            research_topic, 
            innovations, 
            None, 
            "zh"
        )
        
        logger.info(f"成功通过API获取论文结构建议")
        
        # 添加数据源标记
        paper_outline["dataSource"] = "ai_generated"
        
        return paper_outline
    except Exception as e:
        logger.error(f"通过API生成论文结构时出错: {str(e)}", exc_info=True)
        
        # 不再静默回退到模拟数据，而是返回带有明确错误信息的结果
        return {
            "title": f"{research_topic}论文结构建议 (生成失败)",
            "error": f"在生成论文结构时遇到错误: {str(e)}",
            "errorDetails": {
                "message": str(e),
                "type": e.__class__.__name__,
                "timestamp": str(datetime.now())
            },
            "suggestion": "请重试或联系管理员。如需立即继续，可以参考以下通用论文结构:",
            "fallbackStructure": {
                "sections": [
                    "1. 引言 (Introduction)",
                    "2. 相关工作 (Related Work)",
                    "3. 问题定义 (Problem Definition)",
                    "4. 方法 (Methodology)",
                    "5. 实验 (Experiments)",
                    "6. 结论 (Conclusion)"
                ],
                "note": "这是因API调用失败而提供的基础结构，非针对您的研究主题定制"
            }
        } 

async def get_innovation_ideas(
    research_topic: str,
    paper_ids: Optional[List[str]] = None,
    additional_context: Optional[str] = None,
    innovation_type: Optional[str] = None,
    ai_provider: Optional[str] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    生成研究创新点，使用多轮问询和自适应token策略提高质量
    
    Args:
        research_topic: 研究主题
        paper_ids: 论文ID列表
        additional_context: 额外上下文
        innovation_type: 创新类型
        ai_provider: AI提供商
        db: 数据库会话
        
    Returns:
        创新点列表
    """
    
    # 记录开始时间
    start_time = time.time()
    
    # 获取相关论文
    papers_context = ""
    if paper_ids and len(paper_ids) > 0 and db:
        try:
            # 获取论文列表
            papers = get_papers_by_ids(db, paper_ids)
            papers_context = "相关论文概述:\n\n"
            
            # 为每篇论文创建简短摘要
            for i, paper in enumerate(papers):
                papers_context += f"论文 {i+1}：《{paper.title}》\n"
                papers_context += f"摘要: {paper.abstract[:500]}...\n"
                papers_context += f"关键发现: {paper.key_contributions[:300]}...\n\n"
                
        except Exception as e:
            logging.error(f"获取论文信息时出错: {str(e)}")
            papers_context = "无法获取论文信息。"
    
    # 创新类型描述
    innovation_type_desc = ""
    if innovation_type:
        innovation_types = {
            "methodological": "方法论创新 - 改进或提出算法、模型、框架等",
            "theoretical": "理论创新 - 新概念、理论框架、形式化定义等",
            "application": "应用创新 - 新场景、新领域应用、新问题定义等"
        }
        innovation_type_desc = innovation_types.get(innovation_type, "")
    
    # 构建系统提示
    system_prompt = """您是推荐系统领域的世界级研究专家，在技术创新和算法优化方面有深厚的专业背景。您的任务是帮助研究人员找到有价值、有前景且切实可行的研究创新点。

您的分析必须遵循以下准则：

1. 基于主流技术
   - 所有创新点必须建立在当前最新主流技术上，不允许脱离现实技术基础
   - 必须参考近1-2年内顶会（如RecSys、SIGIR、WWW、KDD）发表的重要论文
   - 应当紧跟学术前沿，但避免过于激进的、难以实现的技术路线

2. 渐进式创新
   - 创新必须是现有方法的渐进式改进、组合或拓展，确保可行性和实现路径
   - 每个创新点应明确指出是在哪些现有工作基础上进行改进
   - 应当保持合理的创新力度，不追求"革命性"而脱离现实的构想
   - 优先考虑对现有SOTA方法的改进和超越，而非全新方向

3. 学术价值与实用性平衡
   - 兼顾理论贡献和实际应用潜力
   - 每个创新点必须具有明确的学术价值主张
   - 同时应当考虑工程实现的复杂度和部署难度
   - 建议以"小而精"的改进为主，容易实现且有明确效果提升

4. 文献准确性要求（极其重要）
   - 所有支持文献必须正确且真实存在，不得虚构或杜撰
   - 引用必须包含准确的作者名、发表年份、论文标题和会议/期刊名称
   - 文献内容描述必须与原文一致，不得歪曲或过度解读原文意图
   - 优先引用高引用量、高影响力的工作，确保学术可信度
   - 对于关键创新点，应提供多篇支持文献以增强论证力度

5. 多轮深入思考
   - 您的创新分析将通过多轮深入思考，渐进式地完善和丰富
   - 第一轮：识别研究主题中的创新机会点和基本框架
   - 第二轮：深入剖析每个创新点的技术路径和可行性
   - 第三轮：评估每个创新点的学术价值和实现挑战
   - 第四轮：提供具体的技术实现思路和验证方法
   - 最终综合各轮分析，确保创新点可行、有价值且有具体路径"""
    
    try:
        # 获取AI助手实例
        ai_assistant = get_ai_assistant(provider=ai_provider)
        combined_result = {}
        
        # 第一轮：识别创新机会和基本框架
        logging.info(f"【分批生成】第一轮：识别研究主题'{research_topic}'的创新机会点")
        round1_prompt = f"""系统指令:
{system_prompt}

用户查询:
请分析以下研究主题，识别3-5个最有前景的创新机会点，给出简要描述和创新方向。

研究主题: {research_topic}
{f"创新类型: {innovation_type_desc}" if innovation_type_desc else ""}
{f"额外背景: {additional_context}" if additional_context else ""}

{papers_context}

请以JSON格式返回结果:
```json
{{
  "overview": "整体研究主题分析及创新方向概述",
  "innovations": [
    {{
      "title": "创新点标题",
      "core_concept": "核心概念简述（1-2句话）",
      "innovation_type": "创新类型（方法/理论/应用）",
      "key_insight": "核心洞察"
    }},
    // 更多创新点...
  ]
}}
```
"""
        
        try:
            # 第一轮使用适中token，识别基本创新框架
            round1_response = await ai_assistant.generate_completion(
                prompt=round1_prompt,
                system_prompt=system_prompt,
                max_tokens=2000,
                temperature=0.7
            )
            
            # 解析第一轮结果
            round1_data = extract_json_from_response(round1_response)
            if not round1_data or "innovations" not in round1_data:
                raise ValueError("第一轮分析未能生成有效的创新点框架")
                
            # 保存第一轮结果
            combined_result = round1_data
            logging.info(f"第一轮生成完成，识别出{len(combined_result.get('innovations', []))}个创新点")
            
            # 第二轮：深入分析每个创新点的技术路径
            innovations = combined_result.get("innovations", [])
            enriched_innovations = []
            
            for i, innovation in enumerate(innovations):
                logging.info(f"【分批生成】第二轮：深入分析创新点 {i+1}/{len(innovations)}: {innovation.get('title', '未命名创新点')}")
                
                # 为每个创新点生成技术路径和可行性分析
                innovation_prompt = f"""系统指令:
{system_prompt}

用户查询:
请对以下创新点进行深入的技术路径分析和可行性评估:

创新点标题: {innovation.get('title', '未命名创新点')}
核心概念: {innovation.get('core_concept', '无核心概念')}
创新类型: {innovation.get('innovation_type', '未指定类型')}
核心洞察: {innovation.get('key_insight', '无核心洞察')}

请详细分析该创新点的技术实现路径、技术可行性和所需资源。请确保这是一个渐进式创新，建立在现有主流技术之上，而非脱离现实的构想。

{papers_context if papers_context else ""}

请以JSON格式返回详细分析:
```json
{{
  "title": "优化后的创新点标题",
  "core_concept": "优化后的核心概念",
  "technical_description": "详细的技术描述，包括问题定义、方法步骤、数学基础等",
  "innovation_basis": "该创新所基于的现有研究和技术依据，引用具体论文",
  "existing_methods": ["所基于的现有方法1", "所基于的现有方法2", "所基于的现有方法3"],
  "feasibility_analysis": "技术可行性详细分析，包括数据需求、算法复杂度、计算资源等",
  "implementation_steps": ["实现步骤1", "实现步骤2", "实现步骤3"]
}}
```
"""
                
                # 第二轮针对每个创新点单独生成，使用较大token
                innovation_response = await ai_assistant.generate_completion(
                    prompt=innovation_prompt,
                    system_prompt=system_prompt,
                    temperature=0.7,
                    max_tokens=2500
                )
                
                # 解析单个创新点的深入分析
                innovation_data = extract_json_from_response(innovation_response)
                if innovation_data:
                    # 合并原始创新点数据和深入分析
                    enriched_innovation = {**innovation, **innovation_data}
                    enriched_innovations.append(enriched_innovation)
                else:
                    # 如果解析失败，保留原始创新点
                    logging.warning(f"无法解析创新点{i+1}的深入分析，保留原始数据")
                    enriched_innovations.append(innovation)
            
            # 更新创新点数据
            combined_result["innovations"] = enriched_innovations
            logging.info(f"第二轮生成完成，完成{len(enriched_innovations)}个创新点的技术路径分析")
            
            # 第三轮：评估学术价值和实现挑战
            final_innovations = []
            for i, innovation in enumerate(enriched_innovations):
                logging.info(f"【分批生成】第三轮：评估创新点 {i+1}/{len(enriched_innovations)} 的学术价值和实现挑战")
                
                # 为每个创新点评估学术价值和实现挑战
                evaluation_prompt = f"""系统指令:
{system_prompt}

用户查询:
请评估以下创新点的学术价值和实现挑战:

创新点标题: {innovation.get('title', '未命名创新点')}
核心概念: {innovation.get('core_concept', '无核心概念')}
技术描述: {innovation.get('technical_description', '无技术描述')[:300]}...
创新依据: {innovation.get('innovation_basis', '无创新依据')[:200]}...
现有方法: {', '.join(innovation.get('existing_methods', ['未知']))}
可行性分析: {innovation.get('feasibility_analysis', '无可行性分析')[:200]}...

请评估该创新点的学术价值、与现有研究的区别、可能面临的技术挑战，以及解决这些挑战的潜在思路。

请以JSON格式返回评估结果:
```json
{{
  "differentiators": "与现有研究的具体区别，创新点的独特之处",
  "academic_value": "学术价值和意义的详细评估",
  "technical_challenges": ["技术挑战1", "技术挑战2", "技术挑战3"],
  "solution_approaches": ["解决思路1", "解决思路2", "解决思路3"],
  "expected_performance": "预期性能提升和效果评估",
  "research_impact": "对推荐系统研究领域的潜在影响"
}}
```
"""
                
                # 第三轮针对每个创新点单独评估
                evaluation_response = await ai_assistant.generate_completion(
                    prompt=evaluation_prompt,
                    system_prompt=system_prompt,
                    temperature=0.7,
                    max_tokens=2000
                )
                
                # 解析评估结果
                evaluation_data = extract_json_from_response(evaluation_response)
                if evaluation_data:
                    # 将评估结果添加到创新点
                    complete_innovation = {**innovation, **evaluation_data}
                    final_innovations.append(complete_innovation)
                else:
                    # 如果解析失败，添加默认评估
                    logging.warning(f"无法解析创新点{i+1}的评估结果，添加默认评估")
                    innovation["differentiators"] = "需要进一步分析与现有研究的区别"
                    innovation["academic_value"] = "需要进一步评估学术价值"
                    innovation["technical_challenges"] = ["技术实现挑战待详细分析"]
                    innovation["solution_approaches"] = ["解决思路需进一步探索"]
                    final_innovations.append(innovation)
            
            # 更新最终创新点数据
            combined_result["innovations"] = final_innovations
            logging.info(f"第三轮生成完成，为{len(final_innovations)}个创新点添加了学术价值和挑战评估")
            
            # 第四轮：生成参考文献和最终总结
            logging.info(f"【分批生成】第四轮：生成参考文献和最终总结")
            final_prompt = f"""系统指令:
{system_prompt}

用户查询:
基于以下对研究主题"{research_topic}"的创新点分析，请生成完整的参考文献列表和最终总结:

创新点概述:
{combined_result.get('overview', '无总结')}

已识别的创新点:
{'; '.join([f"{innovation.get('title', '未命名创新点')}" for innovation in final_innovations])}

请生成:
1. 一个完整的参考文献列表，包含分析中引用的所有文献，确保格式统一和引用准确
2. 一个更全面、更有洞察力的总结，强调这些创新点的整体价值和实现可行性

请以JSON格式返回:
```json
{{
  "final_summary": "对所有创新点的全面总结，强调其整体价值和可行性",
  "implementation_strategy": "实现这些创新的整体策略建议",
  "references": [
    "参考文献1 (标准学术引用格式)",
    "参考文献2 (标准学术引用格式)",
    // 更多参考文献...
  ]
}}
```
"""
                
            # 第四轮生成参考文献和最终总结
            final_response = await ai_assistant.generate_completion(
                prompt=final_prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=2500
            )
            
            # 解析最终结果
            final_data = extract_json_from_response(final_response)
            if final_data:
                # 更新最终总结
                if "final_summary" in final_data:
                    combined_result["final_summary"] = final_data["final_summary"]
                
                # 添加实现策略
                if "implementation_strategy" in final_data:
                    combined_result["implementation_strategy"] = final_data["implementation_strategy"]
                    
                # 添加参考文献
                if "references" in final_data:
                    combined_result["references"] = final_data["references"]
            
            # 记录结束时间和处理时间
            end_time = time.time()
            processing_time = end_time - start_time
            
            # 添加元数据
            combined_result["meta"] = {
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "research_topic": research_topic,
                "paper_count": len(paper_ids) if paper_ids else 0,
                "innovation_type": innovation_type,
                "generation_method": "multi_round_batch"
            }
            
            # 转换为前端期望的格式
            session_id = f"innovation_{str(uuid.uuid4())}"
            result_for_frontend = {
                # 标准化的字段
                "session_id": session_id,
                "research_topic": research_topic,
                "innovation_type": innovation_type or "methodological",
                "summary": combined_result.get("overview", "") or combined_result.get("final_summary", ""),
                "final_summary": combined_result.get("final_summary", ""),
                "implementation_strategy": combined_result.get("implementation_strategy", ""),
                "references": combined_result.get("references", []),
                "innovations": [],
                # 元数据
                "meta": combined_result.get("meta", {})
            }
            
            # 标准化创新点数据格式
            for innovation in combined_result.get("innovations", []):
                # 创建标准化创新点对象
                standard_innovation = {
                    "title": "",                    # 必填
                    "description": "",              # 必填
                    "theoreticalBasis": "",        # 必填
                    "technical_implementation": [], # 必填
                    "potential_value": "",          # 必填
                    "related_work": [],             # 必填
                    # 可选字段
                    "innovation_type": None,
                    "key_insight": None,
                    "differentiators": None,
                    "technical_challenges": [],
                    "solution_approaches": [],
                    "feasibility_analysis": None
                }
                
                # 填充标题
                standard_innovation["title"] = innovation.get("title", "未命名创新点")
                
                # 填充描述 - 尝试多个可能的字段名
                for field in ["description", "core_concept", "technical_description", "concept_description"]:
                    if field in innovation and innovation[field]:
                        standard_innovation["description"] = innovation[field]
                        break
                
                if not standard_innovation["description"]:
                    standard_innovation["description"] = "无描述"
                
                # 填充理论基础 - 尝试多个可能的字段名
                for field in ["theoreticalBasis", "theoretical_basis", "innovation_basis", "rationale", "theory"]:
                    if field in innovation and innovation[field]:
                        standard_innovation["theoreticalBasis"] = innovation[field]
                        break
                
                if not standard_innovation["theoreticalBasis"]:
                    standard_innovation["theoreticalBasis"] = "该创新基于推荐系统领域的现有研究，通过改进算法和模型来解决数据稀疏性和冷启动问题，同时提高推荐准确性和多样性。"
                
                # 填充技术实现 - 尝试多个可能的字段名并确保是列表格式
                for field in ["technicalImplementation", "technical_implementation", "implementation_steps", "technical_steps", "implementation"]:
                    if field in innovation:
                        if isinstance(innovation[field], list):
                            standard_innovation["technical_implementation"] = innovation[field]
                            break
                        elif isinstance(innovation[field], str) and innovation[field]:
                            standard_innovation["technical_implementation"] = [innovation[field]]
                            break
                
                # 如果技术实现为空，设置默认值
                if not standard_innovation["technical_implementation"]:
                    standard_innovation["technical_implementation"] = [
                        "分析当前推荐系统面临的关键挑战", 
                        "设计改进的算法架构", 
                        "实现原型系统", 
                        "进行对比实验评估性能"
                    ]
                
                # 填充潜在价值 - 尝试多个可能的字段名或组合
                potential_value = ""
                for field in ["potentialValue", "potential_value", "academic_value", "expected_performance", "research_impact"]:
                    if field in innovation and innovation[field]:
                        if potential_value:
                            potential_value += "\n\n"
                        potential_value += innovation[field]
                
                standard_innovation["potential_value"] = potential_value if potential_value else "该创新有潜力提高推荐系统的性能，解决现有系统的局限性，并为学术界和工业界提供新的研究方向。"
                
                # 为前端展示转换字段命名格式
                standard_innovation["potentialValue"] = standard_innovation.pop("potential_value")
                
                # 填充相关工作 - 尝试多个可能的字段名并确保是列表格式
                for field in ["relatedWork", "related_work", "existing_methods", "related_papers"]:
                    if field in innovation:
                        if isinstance(innovation[field], list):
                            standard_innovation["related_work"] = innovation[field]
                            break
                        elif isinstance(innovation[field], str) and innovation[field]:
                            standard_innovation["related_work"] = [innovation[field]]
                            break
                
                # 如果相关工作为空，设置默认值
                if not standard_innovation["related_work"]:
                    standard_innovation["related_work"] = ["最近推荐系统领域的相关研究", "传统推荐算法", "深度学习推荐系统"]
                
                # 为前端展示转换字段命名格式
                standard_innovation["relatedWork"] = standard_innovation.pop("related_work")
                
                # 填充可选字段
                if "innovation_type" in innovation:
                    standard_innovation["innovation_type"] = innovation["innovation_type"]
                
                if "key_insight" in innovation:
                    standard_innovation["key_insight"] = innovation["key_insight"]
                
                if "differentiators" in innovation:
                    standard_innovation["differentiators"] = innovation["differentiators"]
                
                # 处理技术挑战 - 确保是列表格式
                if "technical_challenges" in innovation:
                    if isinstance(innovation["technical_challenges"], list):
                        standard_innovation["technical_challenges"] = innovation["technical_challenges"]
                    elif isinstance(innovation["technical_challenges"], str) and innovation["technical_challenges"]:
                        standard_innovation["technical_challenges"] = [innovation["technical_challenges"]]
                
                # 如果技术挑战为空，设置默认值
                if not standard_innovation["technical_challenges"]:
                    standard_innovation["technical_challenges"] = [
                        "处理大规模数据的计算效率问题", 
                        "解决数据稀疏性和冷启动问题", 
                        "平衡推荐的准确性和多样性"
                    ]
                
                # 为前端展示转换字段命名格式  
                standard_innovation["technicalChallenges"] = standard_innovation.pop("technical_challenges")
                
                # 处理解决方案 - 确保是列表格式
                if "solution_approaches" in innovation:
                    if isinstance(innovation["solution_approaches"], list):
                        standard_innovation["solution_approaches"] = innovation["solution_approaches"]
                    elif isinstance(innovation["solution_approaches"], str) and innovation["solution_approaches"]:
                        standard_innovation["solution_approaches"] = [innovation["solution_approaches"]]
                
                # 如果解决方案为空，设置默认值
                if not standard_innovation["solution_approaches"]:
                    standard_innovation["solution_approaches"] = [
                        "采用分布式计算框架处理大规模数据", 
                        "结合迁移学习方法解决冷启动问题", 
                        "使用多目标优化技术平衡不同的推荐目标"
                    ]
                
                # 为前端展示转换字段命名格式
                standard_innovation["solutionApproaches"] = standard_innovation.pop("solution_approaches")
                
                # 处理可行性分析
                if "feasibility_analysis" in innovation:
                    standard_innovation["feasibility_analysis"] = innovation["feasibility_analysis"]
                else:
                    standard_innovation["feasibility_analysis"] = "该创新方案在技术上是可行的，可以基于现有技术框架实现，资源需求适中。"
                
                # 为前端展示转换字段命名格式
                standard_innovation["feasibilityAnalysis"] = standard_innovation.pop("feasibility_analysis")
                
                # 添加标准化后的创新点到结果中
                result_for_frontend["innovations"].append(standard_innovation)
            
            logging.info(f"创新点生成完成，处理用时: {processing_time:.2f}秒，生成了{len(result_for_frontend['innovations'])}个标准化创新点")
            
            return result_for_frontend
                
        except Exception as e:
            logging.error(f"多轮分批生成过程中出错: {str(e)}")
            raise Exception(f"创新点生成失败，多轮生成过程中出错: {str(e)}")
            
    except json.JSONDecodeError as e:
        # JSON解析错误处理
        logging.error(f"解析创新点JSON数据失败: {str(e)}")
        logging.debug(f"AI返回的原始响应: {result if 'result' in locals() else '无响应'}")
        
        # 创建简单的错误响应
        return {
            "error": True,
            "message": "无法解析AI返回的创新点数据",
            "details": str(e)
        }
    
    except Exception as e:
        # 通用错误处理
        logging.error(f"生成创新点建议时出错: {str(e)}")
        return {
            "error": True,
            "message": f"生成创新点时出错: {str(e)}",
            "details": str(e)
        }

# 实验设计生成函数
async def get_experiment_design(
    paper_id: Optional[str] = None,
    experiment_name: Optional[str] = None,
    experiment_description: Optional[str] = None,
    framework: str = "pytorch",
    language: str = "python",
    ai_provider: Optional[str] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    生成实验设计方案和代码，使用多轮问询和自适应token策略提高质量
    
    Args:
        paper_id: 论文ID
        experiment_name: 实验名称
        experiment_description: 实验描述
        framework: 框架
        language: 编程语言
        ai_provider: AI提供商
        db: 数据库会话
        
    Returns:
        实验设计方案和代码
    """
    
    # 记录开始时间
    start_time = time.time()
    
    # 获取论文信息
    paper_context = ""
    paper_title = ""
    paper_abstract = ""
    paper_methodology = ""
    
    if paper_id and db:
        try:
            # 获取论文详情
            paper = get_paper_by_id(db, paper_id)
            if paper:
                paper_title = paper.title
                paper_abstract = paper.abstract
                paper_methodology = paper.methodology if hasattr(paper, 'methodology') and paper.methodology else '未提供'
                
                paper_context = f"""
## 论文信息
标题: {paper_title}
摘要: {paper_abstract}
关键贡献: {paper.key_contributions if hasattr(paper, 'key_contributions') and paper.key_contributions else '未提供'}
研究方法: {paper_methodology}
"""
        except Exception as e:
            logging.error(f"获取论文信息时出错: {str(e)}")
            paper_context = "无法获取论文信息。"
    
    # 实验领域识别（从实验名称和描述中推断）
    experiment_domain = "推荐系统"
    if experiment_name:
        for domain in ["序列推荐", "图神经网络", "多模态", "知识图谱", "对比学习", "大语言模型"]:
            if domain in experiment_name or (experiment_description and domain in experiment_description):
                experiment_domain = domain
                break
    
    # 构建系统提示词
    system_prompt = f"""您是推荐系统领域的世界顶级研究专家，在{experiment_domain}方向有深厚的专业知识和丰富的研究经验，曾在RecSys、SIGIR、WWW、KDD等顶级会议发表多篇高引用论文，并担任过多个顶级会议的领域主席和期刊审稿人。

您的任务是设计严谨、规范、可复现的学术实验方案和实现代码。您必须遵循当前学术界的最佳实践和标准，确保实验设计的每个方面都有充分依据，同时确保代码实现高效、可靠且符合研究标准。

您的实验设计必须遵循以下学术准则：

1. 学术严谨性标准
   - 实验设计必须基于最新的学术界主流方法和标准，引用近1-2年内顶会论文的实验设计
   - 所有数据集、基线方法、评估指标必须是该领域公认且广泛使用的
   - 实验设置必须包含详细的超参数配置、训练策略和评估流程
   - 必须设计足够的消融实验，验证方法各组件的有效性
   - 实验结果分析必须包含统计显著性检验和适当的可视化

2. 可复现性要求
   - 提供完整的数据预处理流程，包括数据分割、缺失值处理、特征工程等细节
   - 详细说明环境配置、依赖库版本和硬件需求
   - 包含随机种子设置和多次运行的平均结果报告策略
   - 提供完整的模型初始化和训练流程代码
   - 包含结果保存和加载机制，便于后续分析

3. 基线方法选择标准
   - 必须包含该领域公认的经典方法作为基础基线
   - 必须包含近1-2年内提出的SOTA方法作为先进基线
   - 基线方法的实现必须公平，使用官方实现或广泛认可的复现版本
   - 基线方法的超参数必须经过充分调优，确保公平比较
   - 详细说明每个基线方法的优缺点和适用场景

4. 评估指标选择标准
   - 必须使用该领域公认的主流评估指标，如NDCG@K、Recall@K、Precision@K等
   - 同时考虑准确性指标和多样性/新颖性等辅助指标
   - 离线评估和在线评估指标的关联分析
   - 指标计算方法必须准确，提供计算公式和实现代码
   - 结果报告必须包含95%置信区间或标准差

5. 代码质量和实现标准
   - 代码结构必须清晰，遵循软件工程最佳实践
   - 代码必须高效，避免不必要的计算和内存开销
   - 提供详细的注释和文档字符串
   - 实现必要的日志系统，记录关键训练和评估指标
   - 代码须包含错误处理和边界条件检查

您将通过多轮深入思考，渐进式地完善实验设计和代码实现：
- 第一轮：制定实验目标和整体框架，确定主要研究问题
- 第二轮：选择和设计数据集处理方案和评估指标
- 第三轮：选择和实现基线方法和提出的方法
- 第四轮：设计消融实验和参数敏感性分析
- 第五轮：实现核心代码和结果分析方法"""

    # 更新系统提示词，增加实验学术规范和代码实现要求
    system_prompt = f"""您是推荐系统领域的世界顶级研究专家，在{experiment_domain}方向有深厚的专业知识和丰富的研究经验，曾在RecSys、SIGIR、WWW、KDD等顶级会议发表多篇高引用论文，并担任过多个顶级会议的领域主席和期刊审稿人。

您的任务是设计严谨、规范、可复现的学术实验方案和实现代码。您必须遵循当前学术界的最佳实践和标准，确保实验设计的每个方面都有充分依据，同时确保代码实现高效、可靠且符合研究标准。

您的实验设计必须遵循以下学术准则：

1. 学术严谨性标准
   - 实验设计必须符合学术界公认的实验设计流程，包括假设制定、实验设置、结果验证等完整环节
   - 所有数据集必须是该领域主流标准，引用SIGIR、RecSys、WWW、KDD等顶会近1-2年内论文使用的公开数据集
   - 基线方法选择必须符合主流标准，包括经典方法和最新SOTA方法，保证对比的公平性和全面性
   - 实验设置必须详细描述超参数配置、训练策略、硬件环境、评估协议等必要信息
   - 必须设计多组消融实验，系统验证提出方法各组件的有效性和贡献度

2. 完整实验内容要求
   - 实验目标：明确阐述实验目的、预期验证的假设和验证标准
   - 数据集选择：提供至少3个符合研究目标的主流数据集，包含详细的统计信息和预处理步骤
   - 基线方法：提供至少5个相关基线方法，包括经典方法和最新方法，附带详细的引用信息
   - 评估指标：设计全面的评估体系，包含准确性、多样性、新颖性等维度的指标
   - 实验流程：详细的训练流程、测试流程、参数优化策略和结果统计方法
   - 消融实验：针对方法的各个关键组件设计消融实验，验证各部分的作用
   - 结果分析：提供结果分析方法，包括统计显著性检验、可视化策略等

3. 核心代码实现要求
   - 提供方法核心部分的伪代码和关键算法实现，代码应清晰易懂且遵循最佳实践
   - 代码实现应使用{framework}框架，采用模块化设计，便于复用和扩展
   - 核心算法必须包含数据处理、模型定义、损失函数、训练流程和评估方法等关键组件
   - 提供简洁的示例代码，展示如何使用实现的方法进行训练和测试
   - 确保代码中包含足够的注释，解释关键的实现思路和算法逻辑

4. 数据格式一致性要求
   - 确保生成的实验设计数据格式与前端展示保持一致，使用标准化的字段命名和结构
   - 数据集信息使用以下字段：name, type, size, features, source, preprocessing
   - 基线方法信息使用以下字段：name, description, reference, implementation
   - 评估指标信息使用以下字段：name, description, formula, k (适用于@K类指标)
   - 实验设置信息使用以下字段：trainTestSplit, negativeSampling, hyperparameters, hardware, software
   - 消融实验信息使用以下字段：component, purpose, variants, expectedOutcome
   - 代码示例使用codeSnippet字段，确保是可运行的伪代码实现

您将通过多轮深入思考，渐进式地完善实验设计和代码实现：
- 第一轮：制定实验目标和整体框架，确定主要研究问题和验证假设
- 第二轮：选择符合主流标准的数据集，设计完整的数据处理流程和评估指标体系
- 第三轮：选择公认的基线方法，详细描述提出方法的实现细节和技术原理
- 第四轮：设计全面的消融实验和参数敏感性分析，验证方法各组件的贡献
- 第五轮：实现核心算法的伪代码，包含模型定义、训练流程和评估方法的关键实现

请确保最终的实验设计方案在学术严谨性、完整性、创新性和实用性方面都达到顶级会议的标准。所有内容必须具有可操作性，使其他研究者能够基于您的设计复现实验并验证结果。"""

    try:
        # 获取AI助手实例
        ai_assistant = get_ai_assistant(provider=ai_provider)
        combined_result = {}
        
        # 第一轮：确定实验目标和整体框架
        logging.info(f"【分批生成】第一轮：为实验'{experiment_name or '推荐系统实验'}'制定目标和整体框架")
        round1_prompt = f"""系统指令:
{system_prompt}

用户查询:
请为以下实验设计明确的实验目标和整体框架：

实验名称: {experiment_name or "推荐系统实验"}
{f"实验描述: {experiment_description}" if experiment_description else ""}
编程语言: {language}
框架要求: {framework}

{paper_context}

基于上述信息，请确定这个实验的主要研究问题、假设和评估目标。提供一个全面的实验框架，包括您将在后续实验中使用的主要方法论、技术路线和预期结果。

请以JSON格式返回结果:
```json
{{
  "experiment_title": "具体且学术化的实验标题",
  "research_questions": ["研究问题1", "研究问题2", "研究问题3"],
  "hypotheses": ["假设1", "假设2", "假设3"],
  "objectives": ["实验目标1", "实验目标2", "实验目标3"],
  "methodology_overview": "研究方法概述",
  "technical_approach": "技术路线描述",
  "expected_outcomes": "预期实验结果",
  "research_significance": "研究意义"
}}
```
"""
        
        try:
            # 第一轮使用适中token，确定实验基本框架
            round1_response = await ai_assistant.generate_completion(
                prompt=round1_prompt,
                system_prompt=system_prompt,
                max_tokens=2000,
                temperature=0.7
            )
            
            # 解析第一轮结果
            round1_data = extract_json_from_response(round1_response)
            if not round1_data:
                raise ValueError("第一轮分析未能生成有效的实验框架")
                
            # 保存第一轮结果
            combined_result = round1_data
            logging.info("第一轮生成完成，已确定实验目标和整体框架")
            
            # 第二轮：数据集处理方案和评估指标
            logging.info(f"【分批生成】第二轮：设计数据集处理方案和评估指标")
            round2_prompt = f"""系统指令:
{system_prompt}

用户查询:
基于第一轮确定的实验目标和框架，请详细设计数据集处理方案和评估指标。

实验标题: {combined_result.get('experiment_title', experiment_name or '推荐系统实验')}
研究问题: {', '.join(combined_result.get('research_questions', ['未指定']))}
技术路线: {combined_result.get('technical_approach', '未指定')}

请为该实验选择合适的数据集，详细说明数据预处理流程、数据分割方法，并选择适当的评估指标。所选数据集和指标必须是学术界公认且广泛使用的，请注明每个选择的依据和参考文献。

{paper_context if paper_context else ""}

请以JSON格式返回详细设计:
```json
{{
  "datasets": [
    {{
      "name": "数据集1名称",
      "source": "数据集来源和引用",
      "description": "数据集详细描述",
      "statistics": "数据集统计信息",
      "preprocessing": ["预处理步骤1", "预处理步骤2", "预处理步骤3"],
      "split_strategy": "数据集分割策略",
      "reference_papers": ["使用该数据集的参考论文1", "参考论文2"]
    }},
    // 更多数据集...
  ],
  "evaluation_metrics": [
    {{
      "name": "指标1名称",
      "formula": "指标计算公式",
      "description": "指标详细描述",
      "justification": "选择该指标的理由",
      "implementation_detail": "指标实现细节",
      "reference_papers": ["使用该指标的参考论文1", "参考论文2"]
    }},
    // 更多评估指标...
  ],
  "evaluation_protocol": "完整评估协议描述，包括交叉验证、显著性检验等",
  "data_sampling_strategy": "数据采样策略详细描述"
}}
```
"""
            
            # 第二轮生成
            round2_response = await ai_assistant.generate_completion(
                prompt=round2_prompt,
                system_prompt=system_prompt,
                max_tokens=2500,
                temperature=0.7
            )
            
            # 解析第二轮结果
            round2_data = extract_json_from_response(round2_response)
            if round2_data:
                # 合并到总结果中
                combined_result.update(round2_data)
                logging.info(f"第二轮生成完成，已设计数据集处理方案和评估指标")
            else:
                logging.warning("无法解析第二轮数据，使用默认数据集和评估指标")
                combined_result["datasets"] = [{
                    "name": "MovieLens-1M",
                    "source": "GroupLens Research",
                    "description": "包含6000名用户对4000部电影的100万条评分数据",
                    "preprocessing": ["去除评分为0的记录", "按时间戳排序", "转换为隐式反馈"],
                    "split_strategy": "时序分割，最后一次交互作为测试集"
                }]
                combined_result["evaluation_metrics"] = [{
                    "name": "NDCG@K",
                    "description": "归一化折损累计增益，评估推荐列表的排序质量",
                    "justification": "学术界标准排序质量指标"
                }, {
                    "name": "Recall@K",
                    "description": "推荐列表中命中测试集物品的比例",
                    "justification": "广泛使用的覆盖率指标"
                }]
            
            # 第三轮：基线方法和提出的方法
            logging.info(f"【分批生成】第三轮：确定基线方法和实现细节")
            round3_prompt = f"""系统指令:
{system_prompt}

用户查询:
基于前两轮确定的实验目标、数据集和评估指标，请详细设计基线方法和实现细节。

实验标题: {combined_result.get('experiment_title', experiment_name or '推荐系统实验')}
选择的数据集: {', '.join([d.get('name', '未命名数据集') for d in combined_result.get('datasets', [])])}
评估指标: {', '.join([m.get('name', '未命名指标') for m in combined_result.get('evaluation_metrics', [])])}

请选择合适的基线方法，详细说明每种方法的实现细节、超参数配置和训练流程。所选基线必须包括该领域经典方法和最新SOTA方法，确保公平比较。同时，详细描述您提出的方法（如果适用）或实验的核心实现细节。

{paper_context if paper_context else ""}

请以JSON格式返回详细设计:
```json
{{
  "baseline_methods": [
    {{
      "name": "基线方法1名称",
      "type": "类型（经典方法/SOTA方法）",
      "description": "方法详细描述",
      "architecture": "模型架构",
      "hyperparameters": {{
        "参数1": "值1",
        "参数2": "值2"
      }},
      "training_details": "训练细节",
      "implementation_source": "实现来源（如官方代码库链接）",
      "reference_paper": "参考论文"
    }},
    // 更多基线方法...
  ],
  "proposed_method": {{
    "name": "提出的方法名称",
    "motivation": "方法动机",
    "novelty": "创新点",
    "architecture": "详细架构",
    "algorithm_description": "算法详细描述",
    "hyperparameters": {{
      "参数1": "值1",
      "参数2": "值2"
    }},
    "training_process": "详细训练流程",
    "complexity_analysis": "时间和空间复杂度分析"
  }},
  "implementation_details": {{
    "environment_setup": "环境配置",
    "dependencies": ["依赖库1", "依赖库2"],
    "hardware_requirements": "硬件需求",
    "reproducibility_settings": "可复现性设置（如随机种子）"
  }}
}}
```
"""
            
            # 第三轮生成
            round3_response = await ai_assistant.generate_completion(
                prompt=round3_prompt,
                system_prompt=system_prompt,
                max_tokens=3000,
                temperature=0.7
            )
            
            # 解析第三轮结果
            round3_data = extract_json_from_response(round3_response)
            if round3_data:
                # 合并到总结果中
                combined_result.update(round3_data)
                logging.info(f"第三轮生成完成，已确定基线方法和实现细节")
            else:
                logging.warning("无法解析第三轮数据，使用默认基线方法")
                # 设置默认基线方法
                combined_result["baseline_methods"] = [{
                    "name": "BPR-MF",
                    "type": "经典方法",
                    "description": "贝叶斯个性化排序矩阵分解，经典的隐式反馈推荐方法",
                    "reference_paper": "Rendle et al., 2009. BPR: Bayesian Personalized Ranking from Implicit Feedback. UAI."
                }, {
                    "name": "LightGCN",
                    "type": "SOTA方法",
                    "description": "轻量级图卷积网络，移除了传统GCN中的特征变换和非线性激活",
                    "reference_paper": "He et al., 2020. LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation. SIGIR."
                }]
            
            # 第四轮：消融实验和参数敏感性分析
            logging.info(f"【分批生成】第四轮：设计消融实验和参数敏感性分析")
            round4_prompt = f"""系统指令:
{system_prompt}

用户查询:
基于前三轮的设计，请详细规划消融实验和参数敏感性分析。

实验标题: {combined_result.get('experiment_title', experiment_name or '推荐系统实验')}
提出的方法: {combined_result.get('proposed_method', {}).get('name', '方法未命名')}
核心组件: {combined_result.get('proposed_method', {}).get('architecture', '未详细说明')}

请设计完整的消融实验，以验证提出方法中各个组件的有效性，并设计参数敏感性分析，以研究关键超参数对性能的影响。确保实验设计符合学术界标准，能够全面评估方法的各个方面。

{paper_context if paper_context else ""}

请以JSON格式返回详细设计:
```json
{{
  "ablation_studies": [
    {{
      "component": "要验证的组件1",
      "purpose": "该消融实验的目的",
      "variant_description": "移除或替换该组件后的变体描述",
      "implementation_details": "实现细节",
      "expected_outcome": "预期结果和分析重点"
    }},
    // 更多消融实验...
  ],
  "parameter_sensitivity": [
    {{
      "parameter": "超参数1",
      "range": "测试范围",
      "step_size": "步长",
      "importance": "该参数的重要性",
      "analysis_method": "分析方法"
    }},
    // 更多参数敏感性分析...
  ],
  "experimental_procedure": "完整实验流程",
  "visualization_plans": "结果可视化计划",
  "statistical_analysis": "统计分析方法"
}}
```
"""
            
            # 第四轮生成
            round4_response = await ai_assistant.generate_completion(
                prompt=round4_prompt,
                system_prompt=system_prompt,
                max_tokens=2500,
                temperature=0.7
            )
            
            # 解析第四轮结果
            round4_data = extract_json_from_response(round4_response)
            if round4_data:
                # 合并到总结果中
                combined_result.update(round4_data)
                logging.info(f"第四轮生成完成，已设计消融实验和参数敏感性分析")
            else:
                logging.warning("无法解析第四轮数据，使用默认消融实验设计")
                combined_result["ablation_studies"] = [{
                    "component": "主要组件",
                    "purpose": "验证该组件的必要性",
                    "variant_description": "移除该组件的变体",
                    "expected_outcome": "性能下降，证明该组件的有效性"
                }]
                combined_result["parameter_sensitivity"] = [{
                    "parameter": "嵌入维度",
                    "range": "16, 32, 64, 128, 256",
                    "importance": "影响模型表达能力和过拟合风险"
                }]
            
            # 第五轮：核心代码实现
            logging.info(f"【分批生成】第五轮：实现核心代码和分析方法")
            round5_prompt = f"""系统指令:
{system_prompt}

用户查询:
基于前四轮的设计，请实现核心代码和结果分析方法，特别注意生成符合前端展示需求的标准格式。

实验标题: {combined_result.get('experiment_title', experiment_name or '推荐系统实验')}
框架: {framework}
编程语言: {language}

请提供完整且可运行的核心代码实现，包括数据加载、模型定义、训练和评估流程。代码必须遵循以下要求：

1. 结构清晰：必须分为数据处理、模型定义、训练流程和评估方法四个主要部分
2. 注释完善：每个关键步骤和算法核心部分都要有详细的中文注释
3. 实现完整：包含模型初始化、损失函数定义、优化器配置和训练循环
4. 伪代码可执行：虽是伪代码，但基本结构和语法必须正确
5. 核心算法重点突出：创新点和核心算法部分必须重点详细实现

另外，必须单独提供一个codeSnippet字段，包含最核心的算法实现（如模型定义、特殊层实现或关键损失函数），该部分将直接显示在前端界面中。

请以JSON格式返回实现:
```json
{{
  "code_structure": [
    {{
      "file_name": "data_processor.py",
      "purpose": "数据加载与预处理",
      "code_content": "# 详细的数据处理代码..."
    }},
    {{
      "file_name": "model.py", 
      "purpose": "模型架构定义",
      "code_content": "# 详细的模型定义代码..."
    }},
    {{
      "file_name": "train.py",
      "purpose": "训练流程实现",
      "code_content": "# 详细的训练流程代码..."
    }},
    {{
      "file_name": "evaluate.py",
      "purpose": "评估方法实现",
      "code_content": "# 详细的评估方法代码..."
    }}
  ],
  "codeSnippet": "# 这里放置最核心的算法代码部分，将在前端直接展示\n# 例如模型的核心类定义、关键层实现或创新的损失函数等\n...",
  "usage_example": "# 使用示例代码\n...",
  "visualization_code": "# 结果可视化代码\n...",
  "dependencies": ["numpy", "torch", "pandas", "scikit-learn", "matplotlib"]
}}
```"""

            # 第五轮生成，使用更大token以包纳代码
            round5_response = await ai_assistant.generate_completion(
                prompt=round5_prompt,
                system_prompt=system_prompt,
                max_tokens=4000,
                temperature=0.7
            )
            
            # 解析第五轮结果
            round5_data = extract_json_from_response(round5_response)
            if round5_data:
                # 合并到总结果中
                combined_result.update(round5_data)
                logging.info(f"第五轮生成完成，已实现核心代码和分析方法")
            else:
                logging.warning("无法解析第五轮数据，使用简化版代码实现")
                # 设置简化版代码实现，不影响前四轮的设计
                combined_result["code_structure"] = [{
                    "file_name": "data_processor.py",
                    "purpose": "数据加载与预处理",
                    "code_content": "# 完整代码将在API成功响应时提供\n# 这是占位代码\nimport torch\nimport pandas as pd\nimport numpy as np\n\ndef load_data(dataset_path, split_ratio=0.8):\n    print('加载数据集')\n    # 数据加载和预处理代码\n    return train_data, test_data"
                }, {
                    "file_name": "model.py",
                    "purpose": "模型架构定义",
                    "code_content": "# 模型定义代码\nimport torch\nimport torch.nn as nn\n\nclass RecommendationModel(nn.Module):\n    def __init__(self, user_num, item_num, embedding_dim):\n        super(RecommendationModel, self).__init__()\n        # 模型定义代码\n        self.user_embedding = nn.Embedding(user_num, embedding_dim)\n        self.item_embedding = nn.Embedding(item_num, embedding_dim)\n    \n    def forward(self, user_ids, item_ids):\n        # 前向传播实现\n        return scores"
                }, {
                    "file_name": "train.py",
                    "purpose": "训练流程实现",
                    "code_content": "# 训练代码\nimport torch\nimport torch.optim as optim\nfrom model import RecommendationModel\nfrom data_processor import load_data\n\ndef train(model, train_data, epochs=100, lr=0.001):\n    # 训练流程实现\n    optimizer = optim.Adam(model.parameters(), lr=lr)\n    # 训练循环\n    return model"
                }]
                combined_result["codeSnippet"] = "# 核心模型实现\nclass RecommendationModel(nn.Module):\n    def __init__(self, user_num, item_num, embedding_dim):\n        super(RecommendationModel, self).__init__()\n        self.user_embedding = nn.Embedding(user_num, embedding_dim)\n        self.item_embedding = nn.Embedding(item_num, embedding_dim)\n    \n    def forward(self, user_ids, item_ids):\n        user_embeds = self.user_embedding(user_ids)\n        item_embeds = self.item_embedding(item_ids)\n        scores = torch.sum(user_embeds * item_embeds, dim=1)\n        return scores"
                combined_result["usage_example"] = "# 模型使用示例\nmodel = RecommendationModel(user_num, item_num, embedding_dim=64)\ntrain_data, test_data = load_data('dataset.csv')\ntrained_model = train(model, train_data, epochs=100, lr=0.001)"
                combined_result["dependencies"] = ["numpy", "pandas", "torch", "scikit-learn", "matplotlib"]
            
            # 整合结果，添加元数据
            combined_result["meta"] = {
                "generation_approach": "multi_round",
                "rounds_completed": 5,
                "timestamp": datetime.now().isoformat(),
                "processing_time": time.time() - start_time,
                "experiment_name": experiment_name or "推荐系统实验",
                "framework": framework,
                "language": language,
                "paper_id": paper_id
            }

            # 转换为符合预期的输出结构
            result_for_frontend = {
                "experiment_design": {
                    "title": combined_result.get("experiment_title", experiment_name or "推荐系统实验"),
                    "objectives": combined_result.get("objectives", []),
                    "research_questions": combined_result.get("research_questions", []),
                    "datasets": [d.get("name", "") for d in combined_result.get("datasets", [])],
                    "metrics": [m.get("name", "") for m in combined_result.get("evaluation_metrics", [])],
                    "baselines": [b.get("name", "") for b in combined_result.get("baseline_methods", [])],
                    "experiment_settings": combined_result.get("implementation_details", {}).get("environment_setup", ""),
                    "analysis_methods": combined_result.get("statistical_analysis", "")
                },
                "detailed_design": combined_result,
                "code": "\n\n".join([file.get("code_content", "") for file in combined_result.get("code_structure", [])]),
                "explanation": combined_result.get("experiment_title", "") + "\n\n" + 
                               combined_result.get("methodology_overview", "") + "\n\n" + 
                               "基线方法: " + ", ".join([b.get("name", "") for b in combined_result.get("baseline_methods", [])]) + "\n\n" +
                               "评估指标: " + ", ".join([m.get("name", "") for m in combined_result.get("evaluation_metrics", [])]),
                "meta": combined_result.get("meta", {})
            }

            # 标准化输出结构，确保前端展示格式一致
            result_for_frontend = {
                "domain": combined_result.get("domain", experiment_domain),
                "experimentTitle": combined_result.get("experiment_title", experiment_name or "推荐系统实验"),
                "overview": combined_result.get("methodology_overview", ""),
                
                # 标准化数据集信息
                "datasets": [
                    {
                        "name": d.get("name", "未命名数据集"),
                        "type": d.get("description", d.get("type", "")),
                        "size": d.get("statistics", ""),
                        "features": d.get("features", ""),
                        "source": d.get("source", ""),
                        "preprocessing": ', '.join(d.get("preprocessing", [])) if isinstance(d.get("preprocessing"), list) else d.get("preprocessing", d.get("split_strategy", ""))
                    } for d in combined_result.get("datasets", [])
                ],
                
                # 标准化基线方法信息
                "baselines": [
                    {
                        "name": b.get("name", "未命名方法"),
                        "description": b.get("description", ""),
                        "reference": b.get("reference_paper", b.get("reference", "")),
                        "implementation": b.get("implementation_source", b.get("code_link", ""))
                    } for b in combined_result.get("baseline_methods", [])
                ],
                
                # 标准化评估指标信息
                "evaluationMetrics": [
                    {
                        "name": m.get("name", "未命名指标"),
                        "description": m.get("description", ""),
                        "formula": m.get("formula", ""),
                        "k": [int(m.get("name").split("@")[1])] if "@" in m.get("name", "") else None
                    } for m in combined_result.get("evaluation_metrics", [])
                ],
                
                # 标准化实验设置信息
                "experimentalSettings": {
                    "splitMethod": combined_result.get("evaluation_protocol", {}).get("train_test_split", 
                                 combined_result.get("implementation_details", {}).get("data_split", "")),
                    "negativeHandling": combined_result.get("evaluation_protocol", {}).get("negative_sampling", 
                                      combined_result.get("implementation_details", {}).get("negative_sampling", "")),
                    "trainStrategy": combined_result.get("implementation_details", {}).get("training_strategy", ""),
                    "hardware": combined_result.get("implementation_details", {}).get("hardware_requirements", ""),
                    "software": combined_result.get("implementation_details", {}).get("software_requirements", ""),
                    "hyperparameters": [
                        {"name": "嵌入维度", "value": combined_result.get("implementation_details", {}).get("embedding_dim", "64")},
                        {"name": "学习率", "value": combined_result.get("implementation_details", {}).get("learning_rate", "0.001")},
                        {"name": "批大小", "value": combined_result.get("implementation_details", {}).get("batch_size", "256")},
                        {"name": "训练轮数", "value": combined_result.get("implementation_details", {}).get("epochs", "100")},
                        {"name": "优化器", "value": combined_result.get("implementation_details", {}).get("optimizer", "Adam")}
                    ]
                },
                
                # 标准化消融实验信息
                "ablationStudy": [
                    {
                        "component": a.get("component", "未命名组件"),
                        "purpose": a.get("purpose", a.get("objective", "")),
                        "variants": a.get("variant_description", a.get("variants", [])) if isinstance(a.get("variants", []), list) else [a.get("variant_description", "")],
                        "expectedOutcome": a.get("expected_outcome", "")
                    } for a in combined_result.get("ablation_studies", [])
                ],
                
                # 标准化代码示例
                "codeSnippet": combined_result.get("codeSnippet", 
                             '\n\n'.join([f"# {file.get('file_name')}\n{file.get('code_content', '')[:1000]}..." 
                                          for file in combined_result.get("code_structure", [])[:2]]))
            }
            
            # 记录元数据信息
            result_for_frontend["meta"] = {
                "framework": framework,
                "language": language,
                "generation_time": f"{time.time() - start_time:.2f}秒",
                "experiment_name": experiment_name,
                "paper_id": paper_id
            }
            
            logging.info(f"成功生成实验设计，处理时间: {time.time() - start_time:.2f}秒")
            return result_for_frontend
                
        except Exception as e:
            logging.error(f"多轮分批生成过程中出错: {str(e)}")
            raise Exception(f"实验设计生成失败，多轮生成过程中出错: {str(e)}")
            
    except json.JSONDecodeError as e:
        # JSON解析错误处理
        logging.error(f"解析实验设计JSON数据失败: {str(e)}")
        logging.debug(f"AI返回的原始响应: {result if 'result' in locals() else '无响应'}")
        
        # 创建简单的错误响应
        return {
            "error": True,
            "message": "无法解析AI返回的实验设计数据",
            "details": str(e)
        }
    
    except Exception as e:
        # 通用错误处理
        logging.error(f"生成实验设计时出错: {str(e)}")
        return {
            "error": True,
            "message": f"生成实验设计时出错: {str(e)}",
            "details": str(e)
        } 