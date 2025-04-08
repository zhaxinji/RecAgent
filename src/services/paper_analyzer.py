from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
import httpx
import json
from datetime import datetime
import re
import os
import traceback
from src.models.paper import Paper
from src.core.config import settings
from src.services.ai_assistant import AIAssistant
import asyncio
import hashlib
import random
import inspect

# 打印当前配置信息，便于调试
print(f"当前AI提供商: {settings.DEFAULT_AI_PROVIDER}")
print(f"当前LLM模型: {settings.DEFAULT_LLM_MODEL}")

# 打印API密钥的一部分，隐藏大部分内容
api_key = settings.LLM_API_KEY
if api_key:
    masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "****"
    print(f"已配置API密钥: {masked_key}")
else:
    print("警告: 未配置API密钥")

# 分析状态
class AnalysisStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # 部分完成状态

# 大模型调用设置
LLM_MODEL = settings.DEFAULT_LLM_MODEL
LLM_API_KEY = settings.LLM_API_KEY
ANALYSIS_TEMPERATURE = 0.2

# 分析阶段枚举 - 与前端进度条匹配
ANALYSIS_STAGES = {
    "INIT": 0,              # 初始化
    "PREPARE": 5,           # 准备阶段
    "FILTER": 8,            # 内容过滤
    "SECTIONS": 10,         # 章节结构提取
    "SECTIONS_DONE": 15,    # 章节提取完成
    "METHOD_PREPARE": 20,   # 准备方法论分析
    "METHOD_EXTRACT": 25,   # 提取方法论相关文本
    "METHOD_ANALYZE": 30,   # 分析方法论
    "METHODOLOGY": 40,      # 方法论分析完成
    "EXPERIMENTS": 50,      # 实验分析
    "FINDINGS": 65,         # 关键发现分析
    "WEAKNESSES": 75,       # 弱点分析
    "FUTURE_WORK": 85,      # 未来工作分析
    "CODE": 90,             # 代码生成
    "REFERENCES": 95,       # 引用分析
    "COMPLETE": 100         # 完成
}

# 创建全局AI助手实例
ai_assistant_instance = None
try:
    ai_assistant_instance = AIAssistant(provider=settings.DEFAULT_AI_PROVIDER)
    print(f"全局AI助手实例初始化成功")
except Exception as e:
    print(f"全局AI助手实例初始化失败: {str(e)}")

# 主分析入口函数
async def analyze_paper(db: Session, paper_id: str, user_id: str, extract_core_content: bool = True, 
                  analyze_experiments: bool = False, analyze_references: bool = False) -> Paper:
    """
    分析论文，提取结构、方法论、实验设计等信息
    使用增强的错误处理和内容管理策略
    
    Args:
        db: 数据库会话
        paper_id: 论文ID
        user_id: 用户ID
        extract_core_content: 是否只提取核心内容进行分析，减少处理时间
        analyze_experiments: 是否分析实验部分，默认为False
        analyze_references: 是否分析参考文献部分，默认为False
    """
    # 添加调试日志
    print(f"开始分析论文，paper_id={paper_id}, user_id={user_id}")
    print(f"参数设置: extract_core_content={extract_core_content}, analyze_experiments={analyze_experiments}, analyze_references={analyze_references}")
    print(f"使用模型: {LLM_MODEL}, API提供商: {settings.DEFAULT_AI_PROVIDER}")
    
    # 每个阶段的重试次数
    max_stage_retries = 3
    
    try:
        # 获取论文信息
        paper = db.query(Paper).filter(Paper.id == paper_id, Paper.owner_id == user_id).first()
        
        if not paper:
            print(f"论文不存在或无权访问: paper_id={paper_id}")
            raise ValueError("论文不存在或无权访问")
            
        if not paper.content:
            print(f"论文内容为空，无法进行分析: paper_id={paper_id}")
            raise ValueError("论文内容为空，无法进行分析")
        
        # 检查PDF内容长度并优化
        content_length = len(paper.content)
        print(f"论文内容长度: {content_length} 字符")
        
        # 更新分析状态和初始进度
        paper.analysis_status = AnalysisStatus.PROCESSING
        
        # 添加进度字段（如果不存在）
        if not hasattr(paper, 'analysis_progress'):
            db.execute(text("ALTER TABLE papers ADD COLUMN IF NOT EXISTS analysis_progress INTEGER DEFAULT 0"))
            db.commit()
        
        # 设置初始进度
        setattr(paper, 'analysis_progress', ANALYSIS_STAGES["INIT"])
        db.commit()
        print(f"更新论文状态为PROCESSING，进度为{ANALYSIS_STAGES['INIT']}%: paper_id={paper_id}")
        
        # 内容太长时进行预处理
        if content_length > 100000:
            print(f"论文内容过长，进行智能过滤")
            paper.content = smart_filter_paper_content(paper.content)
            print(f"过滤后内容长度: {len(paper.content)} 字符")
            # 更新进度到5%
            setattr(paper, 'analysis_progress', ANALYSIS_STAGES["PREPARE"])
            db.commit()
            print(f"更新进度：论文内容过滤完成，进度{ANALYSIS_STAGES['PREPARE']}%")
        
        # 提取核心内容
        paper_content = paper.content
        core_content = paper_content
        
        if extract_core_content:
            print(f"启用核心内容提取，原始内容长度: {len(paper_content)}")
            # 更新进度
            setattr(paper, 'analysis_progress', ANALYSIS_STAGES["FILTER"])
            db.commit()
            print(f"更新进度：开始核心内容提取，进度{ANALYSIS_STAGES['FILTER']}%")
            
            try:
                # 包装在try-except中以防提取失败
                core_content = extract_paper_core_content(paper_content)
                print(f"核心内容提取完成，提取后长度: {len(core_content)}")
            except Exception as e:
                print(f"核心内容提取失败，将使用原始内容: {str(e)}")
                core_content = paper_content
            
            # 更新进度到章节分析起点
            setattr(paper, 'analysis_progress', ANALYSIS_STAGES["SECTIONS"])
            db.commit()
            print(f"更新进度：核心内容提取完成，进度{ANALYSIS_STAGES['SECTIONS']}%")
        
        try:
            # 初始化AI助手（如果全局实例不可用）
            ai = ai_assistant_instance
            if ai is None:
                try:
                    ai = AIAssistant(provider=settings.DEFAULT_AI_PROVIDER)
                    print(f"新建AI助手实例初始化成功，使用提供商: {settings.DEFAULT_AI_PROVIDER}")
                except Exception as ai_init_error:
                    print(f"AI助手初始化失败: {str(ai_init_error)}")
                    print(f"错误堆栈: {traceback.format_exc()}")
                    raise ai_init_error
            
            # 获取现有分析进度
            current_stage = getattr(paper, 'analysis_progress', 0)
            print(f"当前分析进度: {current_stage}%")
            
            # 根据参数配置需要执行的任务
            tasks = [
                # 元组格式: (阶段名称, 阶段进度值, 异步函数, 函数参数, 结果字段名, 是否必需)
                ("SECTIONS", ANALYSIS_STAGES["SECTIONS"], 
                 extract_paper_sections, (core_content, paper.title, ai), 'sections', False),
                 
                ("METHODOLOGY", ANALYSIS_STAGES["METHODOLOGY"], 
                 extract_methodology, (core_content, paper.title, ai), 'methodology', True),
                 
                ("FINDINGS", ANALYSIS_STAGES["FINDINGS"], 
                 extract_key_findings, (core_content, ai), 'key_findings', True),
                 
                ("WEAKNESSES", ANALYSIS_STAGES["WEAKNESSES"], 
                 extract_weaknesses, (core_content, paper.title, ai), 'weaknesses', False),
                 
                ("FUTURE_WORK", ANALYSIS_STAGES["FUTURE_WORK"], 
                 extract_future_work, (core_content, paper.title, ai), 'future_work', False),
            ]
                 
            # 添加实验部分分析（可选）
            if analyze_experiments:
                tasks.append(
                ("EXPERIMENTS", ANALYSIS_STAGES["EXPERIMENTS"], 
                     extract_experiments, (core_content, ai), 'experiment_data', False)
                )
            else:
                # 不分析实验，直接设置默认值
                paper.experiment_data = {"datasets": [], "metrics": [], "results": "未进行实验部分分析"}
                print(f"跳过实验分析，设置默认值")
            
            # 跳过参考文献分析（如果不需要）
            if not analyze_references:
                paper.references = []
                print(f"跳过参考文献分析，设置为空列表")
            
            # 逐个执行分析任务
            for stage_name, stage_progress, stage_func, stage_args, result_field, is_required in tasks:
                # 如果当前进度已经超过这个阶段，则跳过
                if current_stage >= stage_progress:
                    print(f"跳过已完成的阶段 {stage_name}，当前进度 {current_stage}% >= {stage_progress}%")
                    continue
                
                # 更新进度为该阶段的起始值
                setattr(paper, 'analysis_progress', stage_progress)
                db.commit()
                print(f"开始{stage_name}阶段分析，进度: {stage_progress}%")
                
                # 特别处理方法论分析阶段
                if stage_name == "METHODOLOGY":
                    # 设置准备方法论分析进度
                    setattr(paper, 'analysis_progress', ANALYSIS_STAGES["METHOD_PREPARE"])
                    db.commit()
                    print(f"更新进度：准备方法论分析，进度{ANALYSIS_STAGES['METHOD_PREPARE']}%")
                
                # 执行这个阶段的分析，支持重试
                print(f"开始{stage_name}阶段分析: paper_id={paper_id}")
                stage_successful = False
                retry_count = 0
                stage_result = None
                
                while not stage_successful and retry_count < max_stage_retries:
                    try:
                        # 如果有重试，添加重试信息
                        if retry_count > 0:
                            print(f"重试{stage_name}阶段分析 (第{retry_count+1}次): paper_id={paper_id}")
                            
                            # 对于必需阶段，每次重试都减少内容长度
                            if is_required and retry_count > 1:
                                args_list = list(stage_args)
                                # 减少内容长度
                                if len(args_list) > 0 and isinstance(args_list[0], str) and len(args_list[0]) > 10000:
                                    # 每次重试减少25%内容
                                    reduction_factor = 0.75
                                    new_content = args_list[0][:int(len(args_list[0]) * reduction_factor)]
                                    args_list[0] = new_content
                                    print(f"内容太长，减少到 {len(new_content)} 字符 ({int(reduction_factor*100)}%)")
                                    stage_args = tuple(args_list)
                        
                        # 调用相应的分析函数
                        stage_result = await stage_func(*stage_args)
                        
                        # 检查结果是否有效
                        if is_valid_result(stage_result, result_field):
                            # 将结果保存到论文对象中
                            setattr(paper, result_field, stage_result)
                            db.commit()
                            print(f"{stage_name}阶段分析完成，结果有效")
                            stage_successful = True
                        else:
                            # 结果无效，可能需要重试
                            print(f"{stage_name}阶段结果无效，可能需要重试")
                            retry_count += 1
                    except Exception as e:
                        print(f"{stage_name}阶段分析失败: {str(e)}")
                        print(f"错误堆栈: {traceback.format_exc()}")
                        retry_count += 1
                
                # 如果所有重试都失败，但这个阶段是必需的，则设置默认值
                if not stage_successful and is_required:
                    print(f"{stage_name}阶段分析失败后设置默认值")
                    if result_field == 'methodology':
                        default_value = {
                            "modelArchitecture": "未能从论文中提取方法论信息。",
                            "keyComponents": [{"name": "未能提取组件", "description": "无法从论文中提取组件信息"}],
                            "algorithm": "未能提取算法流程信息。",
                            "innovations": ["未能提取创新点信息"]
                        }
                    elif result_field == 'key_findings':
                        default_value = ["未能从论文中提取关键发现。"]
                    elif result_field == 'weaknesses':
                        default_value = [{"type": "未知", "description": "未能从论文中提取弱点信息。", 
                                          "impact": "无法评估影响", "improvement": "无法提供改进建议"}]
                    elif result_field == 'future_work':
                        default_value = [{"direction": "未知", "description": "未能从论文中提取未来工作方向。"}]
                    elif result_field == 'sections':
                        default_value = [{"title": "未能提取章节结构", "level": 1, "summary": "无法从论文中提取章节结构信息。"}]
                    else:
                        default_value = None
                    
                    if default_value is not None:
                        setattr(paper, result_field, default_value)
                        db.commit()
                        print(f"为{result_field}设置了默认值")
                
                # 特别处理方法论分析后的代码实现环节
                if stage_name == "METHODOLOGY" and (stage_successful or is_required):
                    # 方法论分析完成后，更新进度
                    setattr(paper, 'analysis_progress', ANALYSIS_STAGES["METHODOLOGY"])
                    db.commit()
                    print(f"方法论分析完成，进度{ANALYSIS_STAGES['METHODOLOGY']}%")
            
            # 所有主要分析完成后，生成代码实现
            try:
                # 更新进度到代码生成阶段
                setattr(paper, 'analysis_progress', ANALYSIS_STAGES["CODE"])
                db.commit()
                print(f"开始代码实现生成，进度{ANALYSIS_STAGES['CODE']}%")
                
                # 获取方法论信息
                methodology_info = {}
                if hasattr(paper, 'methodology') and paper.methodology:
                    if isinstance(paper.methodology, str):
                        try:
                            methodology_info = json.loads(paper.methodology)
                        except:
                            methodology_info = {"modelArchitecture": paper.methodology}
                    elif isinstance(paper.methodology, dict):
                        methodology_info = paper.methodology
                
                # 生成代码实现
                code_implementation = await extract_code_implementation(
                    core_content,
                    paper.title,
                    methodology_info,
                    ai
                )
                
                # 保存代码实现
                paper.code_implementation = code_implementation
                db.commit()
                print(f"代码实现生成完成，长度: {len(code_implementation)}")
            except Exception as e:
                print(f"代码实现生成失败: {str(e)}")
                print(f"错误堆栈: {traceback.format_exc()}")
                # 设置默认代码
                paper.code_implementation = f"""# {paper.title} - 代码框架
# 提取代码实现时出错: {str(e)}

import torch
import torch.nn as nn

# 请根据论文内容自行实现模型
"""
                db.commit()
                print("设置了默认代码实现")
            
            # 所有分析完成，标记为已完成状态
            setattr(paper, 'analysis_progress', ANALYSIS_STAGES["COMPLETE"])
            paper.analysis_status = AnalysisStatus.COMPLETED
            paper.analysis_completed_at = datetime.utcnow()
            db.commit()
            
            print(f"论文分析全部完成: paper_id={paper_id}")
            
            # 打印分析结果摘要
            try:
                methodology_summary = "成功" if hasattr(paper, 'methodology') and paper.methodology else "失败"
                sections_count = len(paper.sections) if hasattr(paper, 'sections') and paper.sections else 0
                findings_count = len(paper.key_findings) if hasattr(paper, 'key_findings') and paper.key_findings else 0
                
                print(f"分析结果摘要:")
                print(f"  - 章节结构: {sections_count}个章节")
                print(f"  - 方法论分析: {methodology_summary}")
                print(f"  - 关键发现: {findings_count}条")
                print(f"  - 代码实现: {'成功' if hasattr(paper, 'code_implementation') and len(paper.code_implementation) > 100 else '失败'}")
            except Exception as e:
                print(f"打印结果摘要时出错: {str(e)}")
            
            return paper
            
        except Exception as analysis_error:
            print(f"分析过程中发生错误: paper_id={paper_id}, error={str(analysis_error)}")
            print(f"分析异常堆栈: {traceback.format_exc()}")
            
            # 获取当前进度
            current_progress = getattr(paper, 'analysis_progress', 0)
            
            # 如果至少完成了部分分析，将状态标记为部分完成而不是失败
            if current_progress >= ANALYSIS_STAGES["METHODOLOGY"]:
                paper.analysis_status = AnalysisStatus.PARTIAL
                print(f"已完成部分分析，进度为{current_progress}%，标记为部分完成状态")
            else:
                paper.analysis_status = AnalysisStatus.FAILED
                print(f"分析过程失败，进度为{current_progress}%，标记为失败状态")
                
            db.commit()
            raise analysis_error
            
    except Exception as e:
        print(f"论文分析总体失败: paper_id={paper_id}, error={str(e)}")
        print(f"总体异常堆栈: {traceback.format_exc()}")
        
        # 尝试更新状态，但可能会因为事务问题而失败
        try:
            paper = db.query(Paper).filter(Paper.id == paper_id, Paper.owner_id == user_id).first()
            if paper:
                # 检查是否已经有部分进度
                current_progress = getattr(paper, 'analysis_progress', 0)
                if current_progress >= ANALYSIS_STAGES["METHODOLOGY"]:
                    paper.analysis_status = AnalysisStatus.PARTIAL
                else:
                    paper.analysis_status = AnalysisStatus.FAILED
                db.commit()
                print(f"更新分析状态（异常处理）: paper_id={paper_id}, status={paper.analysis_status}")
        except Exception as status_error:
            print(f"更新状态失败: paper_id={paper_id}, error={str(status_error)}")
        
        raise e

def is_valid_result(result, field_name):
    """检查分析结果是否有效"""
    if result is None:
        return False
        
    if field_name == 'methodology':
        # 检查方法论字段
        if not isinstance(result, dict):
            return False
        required_keys = ["modelArchitecture", "keyComponents", "algorithm", "innovations"]
        return all(key in result for key in required_keys)
        
    elif field_name == 'key_findings':
        # 检查关键发现字段
        if not isinstance(result, list):
            return False
        return len(result) > 0
        
    elif field_name == 'sections':
        # 检查章节结构
        if not isinstance(result, list):
            return False
        return len(result) > 0 and all(isinstance(item, dict) and "title" in item for item in result)
        
    elif field_name == 'experiment_data':
        # 检查实验数据
        if not isinstance(result, dict):
            return False
        return any(key in result for key in ["datasets", "metrics", "baselines", "results"])
        
    elif field_name == 'weaknesses':
        # 检查弱点
        if not isinstance(result, list):
            return False
        return len(result) > 0
        
    elif field_name == 'future_work':
        # 检查未来工作
        if not isinstance(result, list):
            return False
        return len(result) > 0
    
    # 默认假设有效
    return True

# 智能过滤函数
def smart_filter_paper_content(content: str) -> str:
    """
    智能过滤论文内容，去除冗余信息和格式问题
    
    Args:
        content: 原始论文内容
    
    Returns:
        过滤后的论文内容
    """
    # 如果内容较短，直接返回
    if len(content) < 30000:
        return content
    
    # 移除多余的空白行和空格
    content = re.sub(r'\n\s*\n', '\n\n', content)
    
    # 删除页码和页眉页脚
    content = re.sub(r'\n\d+\s*\n', '\n', content)
    content = re.sub(r'\n-\s*\d+\s*-\s*\n', '\n', content)
    
    # 如果仍然太长，保留前10000和后20000字符
    if len(content) > 50000:
        middle_part_length = 20000
        return content[:20000] + "\n...[内容过长，部分省略]...\n" + content[-middle_part_length:]
    
    return content

# 核心内容提取函数
def extract_paper_core_content(content: str, char_limit: int = 30000) -> str:
    """
    提取论文的核心内容，包括标题、摘要、引言、相关工作和方法论
    
    Args:
        content: 论文全文内容
        char_limit: 字符数限制，默认30000字符
    
    Returns:
        提取的核心内容
    """
    print(f"开始提取核心内容，原始长度: {len(content)}")
    
    # 定义要提取的部分
    section_patterns = [
        # 标题和作者（通常在开头）
        r'(?i)^.*?(?=abstract)',
        # 摘要部分
        r'(?i)abstract.*?(?=(?:introduction|(?:\d+\.?\s+)?intro\b|(?:\d+\.?\s+)?introduction))',
        # 引言部分
        r'(?i)(?:introduction|(?:\d+\.?\s+)?intro\b|(?:\d+\.?\s+)?introduction).*?(?=(?:related|(?:\d+\.?\s+)?related|background|(?:\d+\.?\s+)?background))',
        # 相关工作或背景
        r'(?i)(?:related|(?:\d+\.?\s+)?related|background|(?:\d+\.?\s+)?background).*?(?=(?:method|(?:\d+\.?\s+)?method|approach|(?:\d+\.?\s+)?approach|proposed|(?:\d+\.?\s+)?proposed))',
        # 方法或方法论部分
        r'(?i)(?:method|(?:\d+\.?\s+)?method|approach|(?:\d+\.?\s+)?approach|proposed|(?:\d+\.?\s+)?proposed).*?(?=(?:experiment|(?:\d+\.?\s+)?experiment|evaluation|(?:\d+\.?\s+)?evaluation|result|(?:\d+\.?\s+)?result))'
    ]
    
    # 存储提取的片段
    extracted_parts = []
    
    # 对每个模式进行匹配
    for pattern in section_patterns:
        matches = re.search(pattern, content, re.DOTALL)
        if matches:
            part = matches.group(0)
            if len(part) > 100:  # 确保片段有足够长度
                extracted_parts.append(part)
                print(f"提取到部分: 长度={len(part)}, 开头={part[:50]}...")
    
    # 如果没有提取到足够的部分，返回原始内容
    if sum(len(part) for part in extracted_parts) < len(content) * 0.3:
        print("提取内容不足，将使用原始内容")
        
        # 如果原始内容太长，截取一部分
        if len(content) > char_limit:
            return content[:char_limit]
        return content
    
    # 组合提取的部分
    combined = "\n\n".join(extracted_parts)
    
    # 如果组合后内容仍然太长，截取
    if len(combined) > char_limit:
        combined = combined[:char_limit]
        print(f"提取后内容仍超过字符限制，截断至{char_limit}字符")
    
    print(f"核心内容提取完成，提取后长度: {len(combined)}")
    return combined

# 章节结构提取函数
async def extract_paper_sections(content: str, title: str, ai: AIAssistant) -> List[Dict[str, Any]]:
    """
    从论文中提取章节结构和摘要
    
    Args:
        content: 论文内容
        title: 论文标题
        ai: AI助手实例
    
    Returns:
        章节结构列表，每个章节包含标题、级别和摘要
    """
    print(f"开始提取论文 '{title}' 的章节结构")
    
    # 设置提示词
    prompt = f"""
    请使用中文分析以下论文的章节结构，并为每个主要章节提供简短摘要。
    论文标题: {title}
    
    请以JSON格式返回章节结构，每个章节包含以下字段：
    1. title: 章节标题
    2. level: 章节级别 (1为最高级，2为次级，以此类推)
    3. summary: 对章节内容的简短摘要 (50-100字)
    
    确保包含所有主要章节，包括摘要、引言、相关工作、方法论、实验、结果、讨论、结论等。
    
    论文内容:
    {content[:50000]}  # 限制内容长度以避免超出模型上下文长度
    
    回复格式示例:
    [
      {"title": "摘要", "level": 1, "summary": "概述了论文的主要内容和贡献..."},
      {"title": "1. 引言", "level": 1, "summary": "介绍了研究背景和问题..."},
      ...
    ]
    
    请确保返回格式正确的JSON数组，不要包含其他解释文字。所有内容必须使用中文。
    """
    
    try:
        # 调用AI进行分析 - 使用generate_completion代替async_chat
        system_message = "你是一个专业的学术论文分析助手，擅长提取论文结构和内容。请以JSON格式返回中文分析结果。"
        response = await ai.generate_completion(
            prompt, 
            temperature=ANALYSIS_TEMPERATURE,
            system_prompt=system_message
        )
        
        # 打印返回的原始结果，用于调试
        print(f"章节提取原始结果: {response[:500]}...")
        
        # 提取JSON部分
        json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
        if json_match:
            response = json_match.group(0)
            print(f"成功提取JSON部分，长度: {len(response)}")
        else:
            print("未能从响应中找到有效的JSON部分")
            # 尝试备用的正则表达式
            backup_match = re.search(r'\[[\s\S]*\]', response, re.DOTALL)
            if backup_match:
                response = backup_match.group(0)
                print(f"使用备用正则表达式提取JSON部分，长度: {len(response)}")
        
        # 解析JSON
        try:
            sections = json.loads(response)
            print(f"JSON解析成功，获取到 {len(sections)} 个章节项目")
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {str(e)}")
            # 尝试修复常见的JSON格式问题
            fixed_response = response.replace("'", '"').replace("，", ",").replace("：", ":")
            try:
                sections = json.loads(fixed_response)
                print(f"JSON修复并解析成功，获取到 {len(sections)} 个章节项目")
            except:
                raise ValueError(f"无法解析章节结构JSON: {str(e)}")
        
        # 验证数据结构
        valid_sections = []
        for section in sections:
            if isinstance(section, dict) and 'title' in section and 'level' in section and 'summary' in section:
                # 确保数据类型正确
                section['level'] = int(section['level']) if str(section['level']).isdigit() else 1
                valid_sections.append(section)
                print(f"有效章节: {section['title']} (级别 {section['level']})")
            else:
                print(f"跳过无效章节项目: {section}")
        
        print(f"成功提取 {len(valid_sections)} 个有效章节")
        return valid_sections
    
    except Exception as e:
        print(f"提取论文章节结构失败: {str(e)}")
        print(f"错误堆栈: {traceback.format_exc()}")
        # 返回默认结构
        return [
            {"title": "论文结构提取失败", "level": 1, "summary": f"无法从论文中提取章节结构: {str(e)}"},
            {"title": "摘要", "level": 1, "summary": "论文摘要部分"},
            {"title": "引言", "level": 1, "summary": "论文引言部分"},
            {"title": "方法", "level": 1, "summary": "论文方法部分"},
            {"title": "结果", "level": 1, "summary": "论文结果部分"},
            {"title": "结论", "level": 1, "summary": "论文结论部分"}
        ]

# 方法论提取函数
async def extract_methodology(content: str, title: str, ai: AIAssistant) -> Dict[str, Any]:
    """
    从论文中提取方法论信息，包括模型架构、关键组件、算法和创新点
    
    Args:
        content: 论文内容
        title: 论文标题
        ai: AI助手实例
    
    Returns:
        方法论信息字典
    """
    print(f"开始提取论文 '{title}' 的方法论")
    
    # 提取方法部分（如果内容太长）
    method_content = content
    if len(content) > 20000:
        # 尝试只提取方法相关章节
        pattern = r'(?i)(?:method|approach|proposed|methodology|model|architecture|framework).*?(?=(?:experiment|evaluation|result|conclusion))'
        matches = re.search(pattern, content, re.DOTALL)
        if matches and len(matches.group(0)) > 5000:
            method_content = matches.group(0)
            print(f"提取方法部分，长度: {len(method_content)}")
        else:
            # 如果无法提取，使用前20000字符
            method_content = content[:20000]
            print(f"无法提取方法部分，使用前20000字符")
    
    # 设置提示词
    prompt = f"""
    请使用中文分析以下论文中的方法论部分，提取关键信息。
    论文标题: {title}
    
    请关注以下方面：
    1. 模型架构: 论文提出的模型或方法的总体架构
    2. 关键组件: 模型或方法中的主要组件及其功能
    3. 算法流程: 方法的实现步骤或算法流程
    4. 创新点: 论文的技术创新点或方法论贡献
    
    以JSON格式返回以下信息:
    {{
      "modelArchitecture": "模型架构的详细描述",
      "keyComponents": [
        {{"name": "组件1名称", "description": "组件1的详细描述"}},
        {{"name": "组件2名称", "description": "组件2的详细描述"}},
        ...
      ],
      "algorithm": "算法流程的详细描述",
      "innovations": ["创新点1", "创新点2", ...]
    }}
    
    论文内容（方法部分）:
    {method_content}
    
    请确保所有内容使用中文回答，并只返回JSON对象，不要包含其他解释文字。
    """
    
    try:
        # 调用AI进行分析 - 使用generate_completion代替async_chat
        system_message = "你是一个专业的学术论文分析助手，擅长提取深度学习和机器学习方法论。请使用中文以JSON格式返回分析结果。"
        response = await ai.generate_completion(
            prompt, 
            temperature=ANALYSIS_TEMPERATURE,
            system_prompt=system_message
        )
        
        # 打印响应开头，便于调试
        print(f"方法论提取原始结果: {response[:300]}...")
        
        # 提取JSON部分
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            response = json_match.group(0)
            print(f"成功提取JSON部分，长度: {len(response)}")
        else:
            print("未能从响应中找到有效的JSON部分")
        
        # 解析JSON
        try:
            methodology = json.loads(response)
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {str(e)}")
            # 尝试修复常见的JSON格式问题
            fixed_response = response.replace("'", '"').replace("，", ",").replace("：", ":")
            methodology = json.loads(fixed_response)
            print("JSON修复并解析成功")
        
        # 验证字段
        required_fields = ["modelArchitecture", "keyComponents", "algorithm", "innovations"]
        for field in required_fields:
            if field not in methodology:
                methodology[field] = "未能从论文中提取" if field != "keyComponents" and field != "innovations" else []
                print(f"添加缺失字段: {field}")
        
        # 确保keyComponents格式正确
        if "keyComponents" in methodology:
            if not isinstance(methodology["keyComponents"], list):
                methodology["keyComponents"] = []
                print("keyComponents格式不正确，重置为空列表")
            
            # 验证每个组件格式
            valid_components = []
            for component in methodology["keyComponents"]:
                if isinstance(component, dict) and "name" in component and "description" in component:
                    valid_components.append(component)
                elif isinstance(component, dict) and "name" in component:
                    component["description"] = "未提供描述"
                    valid_components.append(component)
                elif isinstance(component, str):
                    valid_components.append({"name": component, "description": "未提供描述"})
            
            methodology["keyComponents"] = valid_components or [{"name": "未能提取组件", "description": "未能从论文中提取关键组件"}]
            print(f"验证后的keyComponents数量: {len(methodology['keyComponents'])}")
        
        # 确保innovations是字符串列表
        if "innovations" in methodology:
            if not isinstance(methodology["innovations"], list):
                if isinstance(methodology["innovations"], str):
                    methodology["innovations"] = [methodology["innovations"]]
                else:
                    methodology["innovations"] = ["未能从论文中提取创新点"]
                print("innovations格式不正确，已修正")
            
            # 确保列表中的每个元素都是字符串
            methodology["innovations"] = [str(item) for item in methodology["innovations"]]
            print(f"验证后的innovations数量: {len(methodology['innovations'])}")
        
        print(f"成功提取方法论信息，包含 {len(methodology.get('keyComponents', []))} 个关键组件")
        return methodology
    
    except Exception as e:
        print(f"提取论文方法论失败: {str(e)}")
        print(f"错误堆栈: {traceback.format_exc()}")
        # 返回默认数据
        return {
            "modelArchitecture": f"未能从论文中提取方法论信息。错误: {str(e)}",
            "keyComponents": [{"name": "未能提取组件", "description": "无法从论文中提取组件信息"}],
            "algorithm": "未能提取算法流程信息。",
            "innovations": ["未能提取创新点信息"]
        }

# 关键发现提取函数
async def extract_key_findings(content: str, ai: AIAssistant) -> List[str]:
    """
    从论文中提取关键发现
    
    Args:
        content: 论文内容
        ai: AI助手实例
    
    Returns:
        关键发现列表
    """
    print("开始提取论文的关键发现")
    
    # 尝试提取结果和讨论部分
    results_content = content
    if len(content) > 20000:
        # 尝试只提取结果相关章节
        pattern = r'(?i)(?:result|experiment|evaluation|discussion|ablation).*?(?=(?:conclusion|limitation|future|reference))'
        matches = re.search(pattern, content, re.DOTALL)
        if matches and len(matches.group(0)) > 3000:
            results_content = matches.group(0)
            print(f"提取结果部分，长度: {len(results_content)}")
        else:
            # 如果无法提取，使用后15000字符
            results_content = content[-15000:]
            print(f"无法提取结果部分，使用后15000字符")
    
    # 设置提示词
    prompt = f"""
    请使用中文从以下论文中提取关键发现和结果。
    
    请关注以下方面：
    1. 实验结果和主要发现
    2. 性能比较和提升
    3. 主要结论和洞见
    
    以JSON数组格式返回关键发现列表:
    [
      "发现1: ...",
      "发现2: ...",
      ...
    ]
    
    论文内容（结果部分）:
    {results_content}
    
    请确保所有内容使用中文回答，并只返回JSON数组，不要包含其他解释文字。
    """
    
    try:
        # 调用AI进行分析 - 使用generate_completion代替async_chat
        system_message = "你是一个专业的学术论文分析助手，擅长提取论文的关键发现和结果。请使用中文以JSON格式返回分析结果。"
        response = await ai.generate_completion(
            prompt, 
            temperature=ANALYSIS_TEMPERATURE,
            system_prompt=system_message
        )
        
        # 打印原始响应开头
        print(f"关键发现提取原始结果: {response[:200]}...")
        
        # 提取JSON部分
        json_match = re.search(r'\[\s*".*"\s*\]', response, re.DOTALL)
        if json_match:
            response = json_match.group(0)
            print(f"成功提取JSON部分，长度: {len(response)}")
        else:
            print("未能使用第一种模式找到有效的JSON部分，尝试备用模式")
            # 尝试更宽松的模式
            json_match = re.search(r'\[[\s\S]*\]', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)
                print(f"使用备用模式提取JSON部分，长度: {len(response)}")
        
        # 解析JSON
        try:
            findings = json.loads(response)
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {str(e)}")
            # 尝试修复常见的JSON格式问题
            fixed_response = response.replace("'", '"').replace("，", ",")
            findings = json.loads(fixed_response)
            print("JSON修复并解析成功")
        
        # 确保是字符串列表
        if isinstance(findings, list):
            findings = [str(item) for item in findings if item]
            print(f"成功提取 {len(findings)} 个关键发现")
        else:
            print(f"解析出的JSON不是列表，而是 {type(findings)}")
            findings = ["未能正确解析论文的关键发现"]
        
        return findings
    
    except Exception as e:
        print(f"提取论文关键发现失败: {str(e)}")
        print(f"错误堆栈: {traceback.format_exc()}")
        # 返回默认数据
        return ["未能从论文中提取关键发现和结果。"]

# 弱点分析函数
async def extract_weaknesses(content: str, title: str, ai: AIAssistant) -> List[Dict[str, str]]:
    """
    从论文中提取方法/模型的弱点和局限性
    
    Args:
        content: 论文内容
        title: 论文标题
        ai: AI助手实例
    
    Returns:
        弱点信息列表，每个弱点包含类型、描述、影响和改进建议
    """
    print(f"开始提取论文 '{title}' 的弱点和局限性")
    
    # 尝试提取讨论和局限性部分
    limitation_content = content
    if len(content) > 20000:
        # 尝试只提取局限性相关章节
        pattern = r'(?i)(?:limitation|discussion|drawback|future|conclusion).*?(?=(?:reference|appendix|acknowledgment))'
        matches = re.search(pattern, content, re.DOTALL)
        if matches and len(matches.group(0)) > 1000:
            limitation_content = matches.group(0)
            print(f"提取局限性部分，长度: {len(limitation_content)}")
        else:
            # 如果无法提取，使用后10000字符
            limitation_content = content[-10000:]
            print(f"无法提取局限性部分，使用后10000字符")
    
    # 设置提示词
    prompt = f"""
    请使用中文分析以下论文中提到的或可能存在的弱点和局限性。
    论文标题: {title}
    
    请关注以下方面：
    1. 论文自己提到的局限性
    2. 方法和模型的潜在弱点
    3. 实验设计或评估的局限
    4. 可能的改进方向
    
    以JSON数组格式返回弱点列表，每个弱点包含以下字段:
    [
      {{
        "type": "弱点类型/类别",
        "description": "详细描述弱点",
        "impact": "此弱点的影响",
        "improvement": "可能的改进方法"
      }},
      ...
    ]
    
    论文内容（局限性部分）:
    {limitation_content}
    
    请确保所有内容使用中文回答，并只返回JSON数组，不要包含其他解释文字。
    """
    
    try:
        # 调用AI进行分析 - 使用generate_completion代替async_chat
        system_message = "你是一个专业的学术论文评审员，擅长发现研究工作的弱点和局限性。请使用中文以JSON格式返回分析结果。"
        response = await ai.generate_completion(
            prompt, 
            temperature=ANALYSIS_TEMPERATURE,
            system_prompt=system_message
        )
        
        # 打印原始响应开头
        print(f"弱点分析提取原始结果: {response[:200]}...")
        
        # 提取JSON部分
        json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
        if json_match:
            response = json_match.group(0)
            print(f"成功提取JSON部分，长度: {len(response)}")
        else:
            print("未能使用第一种模式找到有效的JSON部分，尝试备用模式")
            # 尝试更宽松的模式
            json_match = re.search(r'\[[\s\S]*\]', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)
                print(f"使用备用模式提取JSON部分，长度: {len(response)}")
        
        # 解析JSON
        try:
            weaknesses = json.loads(response)
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {str(e)}")
            # 尝试修复常见的JSON格式问题
            fixed_response = response.replace("'", '"').replace("，", ",").replace("：", ":")
            weaknesses = json.loads(fixed_response)
            print("JSON修复并解析成功")
        
        # 验证数据结构
        valid_weaknesses = []
        for weakness in weaknesses:
            if isinstance(weakness, dict):
                # 确保必要字段存在
                valid_weakness = {
                    "type": weakness.get("type", "未分类"),
                    "description": weakness.get("description", "未提供描述"),
                    "impact": weakness.get("impact", "未评估影响"),
                    "improvement": weakness.get("improvement", "未提供改进建议")
                }
                valid_weaknesses.append(valid_weakness)
                print(f"有效弱点: {valid_weakness['type']}")
        
        print(f"成功提取 {len(valid_weaknesses)} 个弱点")
        return valid_weaknesses
    
    except Exception as e:
        print(f"提取论文弱点失败: {str(e)}")
        print(f"错误堆栈: {traceback.format_exc()}")
        # 返回默认数据
        return [
            {
                "type": "未知",
                "description": "未能从论文中提取弱点和局限性信息。",
                "impact": "无法评估影响",
                "improvement": "无法提供改进建议"
            }
        ]

# 未来工作提取函数
async def extract_future_work(content: str, title: str, ai: AIAssistant) -> List[Dict[str, str]]:
    """
    从论文中提取未来工作和研究方向
    
    Args:
        content: 论文内容
        title: 论文标题
        ai: AI助手实例
    
    Returns:
        未来工作列表，每个项目包含方向和描述
    """
    print(f"开始提取论文 '{title}' 的未来工作方向")
    
    # 尝试提取结论和未来工作部分
    future_content = content
    if len(content) > 20000:
        # 尝试只提取未来工作相关章节
        pattern = r'(?i)(?:future|conclusion|discussion).*?(?=(?:reference|appendix|acknowledgment))'
        matches = re.search(pattern, content, re.DOTALL)
        if matches and len(matches.group(0)) > 1000:
            future_content = matches.group(0)
            print(f"提取未来工作部分，长度: {len(future_content)}")
        else:
            # 如果无法提取，使用后8000字符
            future_content = content[-8000:]
            print(f"无法提取未来工作部分，使用后8000字符")
    
    # 设置提示词
    prompt = f"""
    请使用中文分析以下论文中提到的未来工作和研究方向。
    论文标题: {title}
    
    请关注以下方面：
    1. 作者明确提出的未来工作
    2. 论文暗示的潜在研究方向
    3. 当前工作的可能扩展
    
    以JSON数组格式返回未来工作列表，每个方向包含以下字段:
    [
      {{
        "direction": "研究方向",
        "description": "详细描述该方向的内容和意义"
      }},
      ...
    ]
    
    论文内容（结论和未来工作部分）:
    {future_content}
    
    请确保所有内容使用中文回答，并只返回JSON数组，不要包含其他解释文字。
    """
    
    try:
        # 调用AI进行分析 - 使用generate_completion代替async_chat
        system_message = "你是一个专业的学术研究顾问，擅长分析研究工作的未来发展方向。请使用中文以JSON格式返回分析结果。"
        response = await ai.generate_completion(
            prompt, 
            temperature=ANALYSIS_TEMPERATURE,
            system_prompt=system_message
        )
        
        # 打印原始响应开头
        print(f"未来工作提取原始结果: {response[:200]}...")
        
        # 提取JSON部分
        json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
        if json_match:
            response = json_match.group(0)
            print(f"成功提取JSON部分，长度: {len(response)}")
        else:
            print("未能使用第一种模式找到有效的JSON部分，尝试备用模式")
            # 尝试更宽松的模式
            json_match = re.search(r'\[[\s\S]*\]', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)
                print(f"使用备用模式提取JSON部分，长度: {len(response)}")
        
        # 解析JSON
        try:
            future_work = json.loads(response)
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {str(e)}")
            # 尝试修复常见的JSON格式问题
            fixed_response = response.replace("'", '"').replace("，", ",").replace("：", ":")
            future_work = json.loads(fixed_response)
            print("JSON修复并解析成功")
        
        # 验证数据结构
        valid_directions = []
        for direction in future_work:
            if isinstance(direction, dict):
                # 确保必要字段存在
                valid_direction = {
                    "direction": direction.get("direction", "未指定方向"),
                    "description": direction.get("description", "未提供描述")
                }
                valid_directions.append(valid_direction)
                print(f"有效未来方向: {valid_direction['direction']}")
        
        print(f"成功提取 {len(valid_directions)} 个未来工作方向")
        return valid_directions
    
    except Exception as e:
        print(f"提取论文未来工作方向失败: {str(e)}")
        print(f"错误堆栈: {traceback.format_exc()}")
        # 返回默认数据
        return [
            {
                "direction": "未知",
                "description": "未能从论文中提取未来工作方向。"
            }
        ]

# 实验数据提取函数（可选）
async def extract_experiments(content: str, ai: AIAssistant) -> Dict[str, Any]:
    """
    从论文中提取实验设计、数据集、基线和结果
    
    Args:
        content: 论文内容
        ai: AI助手实例
    
    Returns:
        实验数据信息字典
    """
    print("开始提取论文的实验数据")
    
    # 尝试提取实验部分
    exp_content = content
    if len(content) > 20000:
        # 尝试只提取实验相关章节
        pattern = r'(?i)(?:experiment|evaluation|result|implementation|setup).*?(?=(?:conclusion|discussion|limitation|future))'
        matches = re.search(pattern, content, re.DOTALL)
        if matches and len(matches.group(0)) > 3000:
            exp_content = matches.group(0)
            print(f"提取实验部分，长度: {len(exp_content)}")
        else:
            # 使用中间部分
            mid_point = len(content) // 2
            exp_content = content[mid_point-10000:mid_point+10000]
            print(f"无法提取实验部分，使用中间20000字符")
    
    # 设置提示词
    prompt = f"""
    从以下论文中提取实验设计和结果的关键信息。
    
    请关注以下方面：
    1. 使用的数据集
    2. 基线方法/对比方法
    3. 评估指标
    4. 主要实验结果
    5. 消融研究结果（如果有）
    
    以JSON格式返回以下信息:
    {{
      "datasets": ["数据集1", "数据集2", ...],
      "baselines": ["基线方法1", "基线方法2", ...],
      "metrics": ["评估指标1", "评估指标2", ...],
      "mainResults": "主要实验结果的详细描述",
      "ablationAnalysis": "消融研究结果的详细描述（如果有）"
    }}
    
    论文内容（实验部分）:
    {exp_content}
    
    只返回JSON对象，不要包含其他解释文字。
    """
    
    try:
        # 调用AI进行分析 - 使用generate_completion代替async_chat
        system_message = "你是一个专业的实验设计和数据分析专家，擅长从学术论文中提取实验信息。请以JSON格式返回分析结果。"
        response = await ai.generate_completion(
            prompt, 
            temperature=ANALYSIS_TEMPERATURE,
            system_prompt=system_message
        )
        
        # 提取JSON部分
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            response = json_match.group(0)
        
        # 解析JSON
        exp_data = json.loads(response)
        
        # 验证字段
        for field in ["datasets", "baselines", "metrics"]:
            if field not in exp_data or not isinstance(exp_data[field], list):
                exp_data[field] = []
        
        for field in ["mainResults", "ablationAnalysis"]:
            if field not in exp_data or not isinstance(exp_data[field], str):
                exp_data[field] = "未能从论文中提取相关信息"
        
        print(f"成功提取实验数据，包含 {len(exp_data.get('datasets', []))} 个数据集, {len(exp_data.get('metrics', []))} 个评估指标")
        return exp_data
    
    except Exception as e:
        print(f"提取论文实验数据失败: {str(e)}")
        # 返回默认数据
        return {
            "datasets": [],
            "baselines": [],
            "metrics": [],
            "mainResults": "未能从论文中提取实验结果信息。",
            "ablationAnalysis": "未能从论文中提取消融研究信息。"
        }

# 代码实现提取函数
async def extract_code_implementation(content: str, title: str, methodology: Dict[str, Any], ai: AIAssistant) -> str:
    """
    基于论文内容和方法论生成代码实现
    
    Args:
        content: 论文内容
        title: 论文标题
        methodology: 方法论信息
        ai: AI助手实例
    
    Returns:
        生成的代码实现
    """
    print(f"开始为论文 '{title}' 生成代码实现")
    
    # 从方法论中提取关键信息
    model_arch = methodology.get("modelArchitecture", "未提供")
    key_components = methodology.get("keyComponents", [])
    algorithm = methodology.get("algorithm", "未提供")
    
    # 组合关键组件信息
    components_text = ""
    for comp in key_components:
        if isinstance(comp, dict):
            comp_name = comp.get("name", "未命名组件")
            comp_desc = comp.get("description", "未提供描述")
            components_text += f"- {comp_name}: {comp_desc}\n"
    
    # 设置提示词
    prompt = f"""
    请基于以下论文的方法论和技术细节，生成Python代码实现。
    论文标题: {title}
    
    方法概述:
    {model_arch}
    
    关键组件:
    {components_text}
    
    算法流程:
    {algorithm}
    
    请生成完整、可运行的Python代码，包括：
    1. 必要的导入语句
    2. 主要类和函数的定义
    3. 模型架构的实现
    4. 关键算法的实现
    5. 简单的使用示例
    
    使用PyTorch框架，代码应该结构清晰，包含必要的注释。
    代码注释请使用中文编写，便于理解。
    
    论文原文参考:
    {content[:10000]}
    
    只返回代码，不需要额外的解释。
    """
    
    try:
        # 调用AI生成代码 - 使用generate_completion代替async_chat
        system_message = "你是一个专业的深度学习研究员和工程师，擅长将学术论文转化为可运行的代码实现。请提供清晰、结构良好的代码，代码注释请使用中文。"
        code = await ai.generate_completion(
            prompt, 
            temperature=0.3,  # 较低的温度以保证代码质量
            system_prompt=system_message
        )
        
        print(f"代码生成原始结果长度: {len(code)}")
        
        # 提取代码块
        code_blocks = re.findall(r'```(?:python)?(.*?)```', code, re.DOTALL)
        if code_blocks:
            # 组合所有代码块
            combined_code = "\n\n".join([block.strip() for block in code_blocks])
            print(f"成功提取 {len(code_blocks)} 个代码块，总长度: {len(combined_code)}")
        else:
            # 如果没有明确的代码块标记，尝试提取整个响应
            combined_code = code
            print("未找到代码块标记，使用原始响应作为代码")
        
        # 添加标题注释
        final_code = f"""# {title} - 代码实现
# 注意：此代码是基于论文内容自动生成的，可能需要根据具体需求进行调整

{combined_code}
"""
        
        print(f"代码生成成功，代码长度: {len(final_code)} 字符")
        return final_code
    
    except Exception as e:
        print(f"生成代码实现失败: {str(e)}")
        print(f"错误堆栈: {traceback.format_exc()}")
        # 返回默认代码框架
        return f"""# {title} - 代码框架
# 代码生成失败: {str(e)}
# 请根据论文内容自行实现

import torch
import torch.nn as nn
import torch.optim as optim

# 模型架构概述: {model_arch[:200]}...

class ModelImplementation(nn.Module):
    def __init__(self):
        super(ModelImplementation, self).__init__()
        # TODO: 实现模型架构
        pass
        
    def forward(self, x):
        # TODO: 实现前向传播
        return x

# 使用示例
def main():
    model = ModelImplementation()
    print(model)
    
if __name__ == "__main__":
    main()
"""

# 后续将逐步添加其他功能函数 