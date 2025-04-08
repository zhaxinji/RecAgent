from enum import Enum
from typing import Optional, List, Dict, Any, Union
import logging
import asyncio
import json
import os
import httpx
import uuid
import urllib.parse
import random
import time
import re

# 导入settings对象
from src.core.config import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIProvider(str, Enum):
    """AI提供商枚举"""
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    CLAUDE = "claude"

class AIAssistant:
    """AI助手类，负责与AI API进行交互"""
    
    def __init__(self):
        """初始化AI助手"""
        # 从settings获取设置
        self.provider = settings.DEFAULT_AI_PROVIDER
        self.api_key = settings.LLM_API_KEY
        self.model = settings.DEFAULT_LLM_MODEL
        self.api_base = settings.DEEPSEEK_API_BASE  # 使用默认的DeepSeek API基础URL
        self.max_tokens = settings.AI_PROVIDERS.get(self.provider, {}).get("max_tokens", 4000)
        
        # 调试输出配置信息
        logger.info(f"AI助手初始化 - 提供商: {self.provider}, 模型: {self.model}, API基础URL: {self.api_base}")
        
        # 最终检查API密钥
        if not self.api_key:
            logger.error("未设置API密钥，请在配置文件中设置LLM_API_KEY。服务将降级使用模拟数据。")
        else:
            # 只打印前几个字符作为确认
            masked_key = self.api_key[:4] + "****" + self.api_key[-4:] if len(self.api_key) > 8 else "****"
            logger.info(f"API密钥设置成功: {masked_key}")
            
        # 设置固定的模型参数
        self.default_temperature = 0.7  # 控制创造性
        self.default_top_p = 0.9  # 控制输出多样性
        self.force_mock = os.environ.get("FORCE_MOCK_DATA", "").lower() in ["true", "1", "yes", "y"]
        
        if self.force_mock:
            logger.warning("强制使用模拟数据模式已启用")
    
    def _truncate_prompt(self, prompt, ratio=None, max_length=None):
        """截断过长的提示词"""
        if not prompt:
            return ""
        
        # 默认处理
        if not ratio and not max_length:
            ratio = 0.8
            
        if isinstance(prompt, str):
            if max_length and len(prompt) > max_length:
                return prompt[:int(max_length * 0.9)] + "...[内容已截断]..." + prompt[-int(max_length * 0.1):]
            return prompt
        
        return prompt
    
    def _fix_json(self, json_str: str) -> str:
        """尝试修复无效的JSON字符串"""
        try:
            # 首先尝试直接解析
            parsed = json.loads(json_str)
            # 确保返回的JSON有必要字段
            if "content" not in parsed:
                parsed["content"] = json_str
            if "suggestions" not in parsed or not isinstance(parsed["suggestions"], list):
                parsed["suggestions"] = ["考虑增加专业术语", "添加相关研究引用", "调整段落结构"]
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            logger.warning("收到的响应不是有效JSON，尝试修复")
            
            try:
                # 查找最外层的花括号
                start_idx = json_str.find('{')
                end_idx = json_str.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    extracted = json_str[start_idx:end_idx]
                    # 尝试解析提取出的JSON
                    parsed = json.loads(extracted)
                    # 确保有必需字段
                    if "content" not in parsed:
                        parsed["content"] = extracted
                    if "suggestions" not in parsed or not isinstance(parsed["suggestions"], list):
                        parsed["suggestions"] = ["考虑增加专业术语", "添加相关研究引用", "调整段落结构"]
                    logger.info("成功修复JSON")
                    return json.dumps(parsed, ensure_ascii=False)
                else:
                    # 如果找不到有效的JSON结构，直接构造一个
                    result = {
                        "content": json_str,
                        "suggestions": ["请尝试重新生成内容，当前响应格式不正确"]
                    }
                    return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logger.error(f"修复JSON失败: {e}")
                # 构造一个基本的有效JSON作为后备
                result = {
                    "content": json_str,
                    "suggestions": ["请尝试重新生成内容，当前响应格式不正确"]
                }
                return json.dumps(result, ensure_ascii=False)
    
    def _extract_content_and_suggestions(self, response: str) -> Dict[str, Any]:
        """从API响应中提取内容和建议"""
        try:
            # 首先尝试解析为JSON
            try:
                json_data = json.loads(response)
                # 如果是JSON，尝试标准化提取内容
                return self._standardize_result(json_data, "")
            except json.JSONDecodeError:
                # 不是JSON，可能是直接的Markdown内容
                pass
            
            # 尝试从Markdown中提取内容和建议
            content_parts = response.split("## 改进建议")
            
            if len(content_parts) == 2:
                # 有标准的改进建议部分
                main_content = content_parts[0].strip()
                suggestions_text = content_parts[1].strip()
                
                # 提取建议列表
                suggestions = []
                for line in suggestions_text.split("\n"):
                    clean_line = line.strip()
                    if clean_line and (clean_line.startswith("- ") or clean_line.startswith("* ") or 
                                      (len(clean_line) >= 2 and clean_line[0].isdigit() and clean_line[1] == '.')):
                        # 移除列表标记
                        if clean_line.startswith("- "):
                            suggestion = clean_line[2:].strip()
                        elif clean_line.startswith("* "):
                            suggestion = clean_line[2:].strip()
                        else:
                            # 数字列表
                            parts = clean_line.split(".", 1)
                            if len(parts) > 1:
                                suggestion = parts[1].strip()
                            else:
                                suggestion = clean_line
                        
                        if suggestion:
                            suggestions.append(suggestion)
            else:
                # 没有标准建议部分，把所有内容当作主体
                main_content = response.strip()
                suggestions = ["考虑更精确地表述研究贡献", "添加更多专业术语", "可增加相关研究引用"]
            
            # 确保有建议
            if not suggestions:
                suggestions = ["考虑更精确地表述研究贡献", "添加更多专业术语", "可增加相关研究引用"]
                
            return {
                "content": main_content,
                "suggestions": suggestions
            }
        
        except Exception as e:
            logger.error(f"提取内容和建议失败: {e}")
            return {
                "content": response,
                "suggestions": ["考虑添加更多相关研究引用", "增加图表说明关键概念", "精简冗长描述"]
            }
    
    async def generate_paper_section(
        self, 
        section_type: str, 
        writing_style: str,
        topic: Optional[str] = None,
        research_problem: Optional[str] = None,
        method_feature: Optional[str] = None,
        modeling_target: Optional[str] = None,
        improvement: Optional[str] = None,
        key_component: Optional[str] = None,
        impact: Optional[str] = None,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成论文特定部分的内容"""
        logger.info(f"生成论文{section_type}部分，风格：{writing_style}")
        
        # 如果没有API密钥或强制使用模拟数据，直接返回模拟内容
        if self.force_mock or not self.api_key:
            logger.warning("使用模拟数据（没有API密钥或已启用强制模拟模式）")
            content = self._generate_mock_content(section_type, topic, research_problem, method_feature, key_component)
            suggestions = self._generate_mock_suggestions(section_type)
            return {
                "content": content,
                "suggestions": suggestions
            }
        
        # 构建写作风格指南
        style_guide = self._get_writing_style_guide(writing_style)
        
        # 构建部分写作指南
        section_guide = self._get_section_writing_guide(section_type)
        
        # 清理和规范化输入参数 - 只处理核心参数：研究主题和额外背景信息
        safe_topic = topic or "推荐系统"
        safe_additional_context = additional_context or ""
        
        # 前端已经删除了其他字段，只使用研究主题和额外背景信息
        combined_context = ""
        if safe_additional_context:
            combined_context = f"额外背景信息：\n{safe_additional_context}"
        
        logging.info(f"核心参数: topic={safe_topic}, 背景信息长度={len(combined_context)}")
        
        # 构建提示语
        system_prompt = f"""你是一位专精于【{safe_topic}】领域的资深推荐系统研究专家，具有多年顶级会议和期刊论文发表经验。

【核心要求（按优先级排序）】：
1. 必须严格围绕研究主题【{safe_topic}】展开所有内容，这是最高优先级要求
2. 每个段落必须与【{safe_topic}】直接相关，不相关内容一律不生成
3. 必须100%使用中文输出，包括所有标题、段落和术语解释
4. 禁止使用任何英文标题（如Abstract、Introduction等）
5. 所有标题必须使用中文（如"摘要"、"引言"等）

【内容生成规则】：
1. 内容必须直接针对【{safe_topic}】进行深入、专业的学术探讨
2. 严格按照SIGIR、RecSys、WWW、KDD等顶会的中文论文标准撰写
3. 引用的文献必须与【{safe_topic}】密切相关，引用格式为[作者,年份]
4. 术语首次出现时使用"中文术语(English Term)"格式，之后仅使用中文
5. 方法、模型和算法必须适用于【{safe_topic}】的特定场景
6. 在内容结尾用"## 改进建议"标题列出2-3条针对【{safe_topic}】研究的具体建议

为确保内容质量：
- 开始写作前，请先确认每个段落如何直接与【{safe_topic}】相关
- 避免生成通用的推荐系统知识，除非它直接应用于【{safe_topic}】
- 确保所有例子、数据和分析都围绕【{safe_topic}】展开
- 不要偏离主题，所有内容必须始终紧密围绕【{safe_topic}】

禁止使用英文标题或段落！所有输出必须是专业的学术中文！"""

        # 根据部分类型调整提示词
        if section_type == "abstract":
            section_specific_guide = """
- 摘要应简明扼要地呈现研究问题、方法创新点、关键技术、实验结果和主要结论
- 明确指出研究的理论贡献和实践意义
- 注重定量结果的精确描述，如具体的提升百分比
- 字数控制在400-500字之间，确保包含所有关键信息"""
        elif section_type == "introduction":
            section_specific_guide = """
- 引言部分应清晰阐述研究背景和问题的重要性
- 明确指出现有方法的局限性，形成研究空白和机会
- 准确描述你的研究贡献，包括理论创新、技术突破和实验验证
- 在段落末尾概述论文结构
- 引用应包括推荐系统领域的经典文献和最新进展"""
        elif section_type == "related_work":
            section_specific_guide = """
- 相关工作部分应系统全面地梳理领域内的重要研究
- 按照清晰的分类框架组织文献（如基于不同技术路线、应用场景或问题定义）
- 引用必须包括作者、年份、会议/期刊名称等准确信息
- 每类相关工作应先描述其核心思想，然后分析其优缺点
- 最后明确指出你的工作与这些相关工作的区别和优势"""
        elif section_type in ["method", "methodology"]:
            section_specific_guide = """
- 方法部分应从问题定义开始，包括数学符号和形式化定义
- 系统地阐述你提出的方法，包括整体框架、关键组件和算法细节
- 提供必要的理论推导和证明
- 使用图表清晰展示方法架构
- 解释方法的设计动机以及如何解决现有方法的缺陷
- 详细讨论算法的时间和空间复杂度"""
        elif section_type in ["experiment", "results"]:
            section_specific_guide = """
- 实验部分应详细描述数据集、评估指标、对比基线和实验设置
- 数据集必须是真实的公开数据集，包括确切的规模、特征和来源
- 对比基线应包括经典方法和最新的先进方法
- 实验结果应使用表格呈现，包括均值和标准差
- 进行充分的消融实验和参数敏感性分析
- 提供实验代码和数据的可访问链接"""
        elif section_type == "discussion":
            section_specific_guide = """
- 讨论部分应深入分析实验结果背后的原因
- 探讨方法的优势和局限性
- 提出未来可能的改进方向
- 分析方法在不同场景下的适用性
- 讨论研究对理论和实践的更广泛影响"""
        elif section_type == "conclusion":
            section_specific_guide = """
- 结论部分应简明扼要地总结研究的主要贡献
- 强调研究的理论和实践意义
- 讨论研究的局限性
- 提出未来研究方向
- 不应引入任何新的内容"""
        else:
            section_specific_guide = "按照国际顶会顶刊的标准格式撰写内容，确保准确性和专业性"

        # 补充更详细的写作风格指南
        detailed_style_guide = self._get_writing_style_guide(writing_style)
        if writing_style == "academic":
            detailed_style_guide += """
- 使用正式的学术语言，避免口语化表达
- 遵循"提出问题-分析问题-解决问题"的逻辑结构
- 使用被动语态和第三人称表达
- 准确引用相关文献，支持论点
- 定义使用的术语和概念，确保清晰准确"""

        prompt = f"""请以资深推荐系统研究专家的身份，为我撰写一篇高质量的论文{section_type}部分。

## 写作风格要求
{detailed_style_guide}

## 内容要求
{self._get_section_writing_guide(section_type)}
{section_specific_guide}

## 研究信息
研究主题：{safe_topic}
研究问题：{research_problem}
方法特点：{method_feature}
建模目标：{modeling_target}
性能提升：{improvement}
关键组件：{key_component}
研究影响：{impact}
额外上下文：{safe_additional_context}

## 要求
1. 必须使用中文撰写
2. 必须符合推荐系统领域顶级会议和期刊的学术标准
3. 所有引用的文献必须真实存在，引用格式应为[作者,年份]或(作者,年份)
4. 内容须深入、专业、严谨，展现资深研究者的学术洞见
5. 如提及具体算法或模型，需确保其表述准确，与学术界公认的定义一致
6. 如包含实验结果，数据必须真实合理
7. 中英文术语混用时，首次出现的专业术语应提供英文原文，如"协同过滤(Collaborative Filtering)"

请直接以Markdown格式生成内容，并在内容最后列出2-3条改进建议，用"## 改进建议"作为标题。
"""
        
        try:
            # 开始计时
            start_time = time.time()
            logger.info(f"开始调用AI API，提示词长度: {len(prompt)}字符")
            
            # 实际调用大模型API
            response = await self._call_deepseek_api(
                prompt=prompt, 
                max_tokens=self.max_tokens, 
                temperature=self.default_temperature,
                system_prompt=system_prompt
            )
            
            # 计算和记录用时
            elapsed_time = time.time() - start_time
            logger.info(f"AI API调用完成，用时: {elapsed_time:.2f}秒，响应长度: {len(response)}字符")
            
            # 尝试解析返回的JSON
            try:
                # 先检查响应是否为JSON格式
                if response.strip().startswith("{") and response.strip().endswith("}"):
                    # 尝试解析JSON
                    result = json.loads(response)
                    
                    # 标准化结果格式
                    result = self._standardize_result(result, section_type)
                else:
                    # 不是JSON，可能是直接的Markdown内容
                    result = self._extract_content_and_suggestions(response)
                
                logger.info(f"成功解析AI响应，内容长度: {len(result.get('content', ''))}")
                return result
            except json.JSONDecodeError as e:
                logger.info(f"响应不是JSON格式，尝试作为Markdown处理: {e}")
                result = self._extract_content_and_suggestions(response)
                return result
                
        except Exception as e:
            error_detail = str(e)
            logger.error(f"调用AI API失败: {error_detail}")
            
            # 记录更详细的错误信息用于调试
            import traceback
            tb = traceback.format_exc()
            logger.error(f"错误详情:\n{tb}")
            
            # 出错时返回模拟数据作为降级策略
            content = self._generate_mock_content(section_type, topic, research_problem, method_feature, key_component)
            suggestions = self._generate_mock_suggestions(section_type)
            
            return {
                "content": content,
                "suggestions": suggestions
            }
    
    async def _call_deepseek_api(self, prompt, max_tokens, temperature, stream=False, system_prompt=None):
        """
        调用DeepSeek API获取响应
        
        Args:
            prompt: 提示词文本
            max_tokens: 生成的最大token数
            temperature: 采样温度
            stream: 是否使用流式传输
            system_prompt: 系统提示，用于定义AI助手的行为
        
        Returns:
            API响应内容
        """
        # 记录请求信息
        request_id = str(uuid.uuid4())[:8]
        logger.info(f"[{request_id}] DeepSeek API 请求: 提示词长度={len(prompt)}, max_tokens={max_tokens}, temp={temperature}")
        start_time = time.time()
        
        # 预先截断过长的提示词，避免超时
        if len(prompt) > 8000:
            logger.info(f"[{request_id}] 提示词过长({len(prompt)}字符)，执行智能截断")
            front_len = int(8000 * 0.65)
            back_len = 8000 - front_len - 50
            prompt = prompt[:front_len] + "\n\n...[内容已省略]...\n\n" + prompt[-back_len:]
            logger.info(f"[{request_id}] 截断后长度: {len(prompt)}字符")
        
        # 检查API密钥是否有效
        api_key = self.api_key
        if not api_key or len(api_key.strip()) < 8:
            raise ValueError("无效的API密钥")
        
        # 使用settings中配置的API基础URL
        if self.provider == AIProvider.DEEPSEEK:
            api_url = f"{settings.DEEPSEEK_API_BASE}/chat/completions"
        elif self.provider == AIProvider.OPENAI:
            api_url = f"{settings.OPENAI_API_BASE}/chat/completions"
        elif self.provider == AIProvider.CLAUDE:
            api_url = f"{settings.CLAUDE_API_BASE}/messages"
        else:
            # 默认使用DeepSeek
            api_url = f"{settings.DEEPSEEK_API_BASE}/chat/completions"
            
        model = self.model
        logger.info(f"[{request_id}] 将请求发送到: {api_url}, 使用模型: {model}")
        
        # 构建请求数据
        messages = []
        
        # 添加系统提示（如果有）
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        # 添加用户提示
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
            "stream": stream
        }
        
        # 输出请求信息（排除实际提示词内容）
        debug_data = data.copy()
        for msg in debug_data.get("messages", []):
            if "content" in msg and len(msg["content"]) > 100:
                msg["content"] = msg["content"][:50] + "..." + msg["content"][-50:] 
        logger.debug(f"[{request_id}] 请求数据: {debug_data}")
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 重试逻辑
        max_retries = 3
        base_timeout = 120.0  # 增加到120秒
        
        for attempt in range(max_retries):
            current_timeout = base_timeout * (1 + attempt * 0.5)
            
            try:
                logger.info(f"[{request_id}] 尝试API请求 ({attempt+1}/{max_retries}), 超时设置: {current_timeout}秒")
                
                timeout_settings = httpx.Timeout(
                    connect=30.0,
                    read=current_timeout,
                    write=30.0,
                    pool=30.0
                )
                
                async with httpx.AsyncClient(timeout=timeout_settings) as client:
                    response = await client.post(
                        url=api_url,
                        json=data,
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if "choices" in result and len(result["choices"]) > 0:
                            message = result["choices"][0]["message"]
                            if "content" in message:
                                content = message["content"]
                                elapsed_time = time.time() - start_time
                                logger.info(f"[{request_id}] API请求成功，用时: {elapsed_time:.2f}秒，响应长度: {len(content)}")
                                
                                # 确保返回的内容不为空
                                if not content.strip():
                                    logger.warning(f"[{request_id}] API返回了空内容，使用备用响应")
                                    return json.dumps({
                                        "content": "API返回了空内容，请重试。",
                                        "suggestions": ["尝试使用不同的提示词", "检查API连接状态", "调整生成参数"]
                                    }, ensure_ascii=False)
                                
                                return content
                        
                        logger.error(f"[{request_id}] API响应格式异常: {result}")
                        # 构造一个基本的有效JSON作为后备
                        return json.dumps({
                            "content": f"API响应格式异常，请重试。收到的响应: {str(result)[:200]}...",
                            "suggestions": ["请检查API配置", "尝试使用不同的提示词", "联系技术支持"]
                        }, ensure_ascii=False)
                    else:
                        error_msg = f"API请求失败: 状态码 {response.status_code}, 响应: {response.text}"
                        logger.error(f"[{request_id}] {error_msg}")
                        
                        if response.status_code == 401:
                            raise ValueError("API密钥无效或未授权，请检查您的API密钥设置")
                        elif response.status_code == 429:
                            retry_after = int(response.headers.get('retry-after', 5)) + random.randint(1, 5)
                            logger.info(f"[{request_id}] 请求过多 (429)，等待 {retry_after} 秒后重试")
                            await asyncio.sleep(retry_after)
                        elif 500 <= response.status_code < 600:
                            wait_time = 2 ** attempt + random.random() * 2
                            logger.info(f"[{request_id}] 服务器错误 ({response.status_code})，等待 {wait_time:.1f} 秒后重试")
                            await asyncio.sleep(wait_time)
                        else:
                            raise Exception(error_msg)
            
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt + random.random() * 5
                    logger.warning(f"[{request_id}] 请求异常: {str(e)}, 等待 {wait_time:.1f} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    raise Exception(f"API请求在 {max_retries} 次尝试后仍然失败: {str(e)}")
        
        # 如果所有重试都失败了
        raise Exception(f"所有 {max_retries} 次API请求尝试均失败")
    
    def _get_writing_style_guide(self, style: str) -> str:
        """获取写作风格指南"""
        style_guides = {
            "academic": """严谨正式的学术风格，适用于顶级会议和期刊论文：
- 使用规范的学术用语和术语，专业词汇精确使用
- 采用被动语态和第三人称表达，避免使用"我们"以外的第一人称
- 句式应正式、精确、简洁，避免口语化、随意性表达
- 论证需基于实证研究和理论分析，而非个人观点
- 每个论点都应有充分的证据和引用支持
- 使用学术界公认的引用格式，如IEEE或ACM格式
- 重视逻辑性和连贯性，使用恰当的连接词和过渡词
- 确保数据准确无误，避免夸大或模糊的描述
- 图表应清晰、规范，并有详细说明""",

            "technical": """以技术细节为重点的写作风格，适合方法和实验部分：
- 详细描述算法原理、模型架构和实现细节
- 使用数学符号和公式进行精确表达，并提供必要的推导过程
- 提供伪代码或算法框架，清晰展示算法流程
- 使用专业术语和技术词汇，确保术语一致性
- 描述应具体而非抽象，提供充分的细节
- 强调方法的创新点和技术优势
- 客观分析技术的局限性和适用条件
- 对复杂概念提供图示说明
- 讨论实现细节、复杂度分析和优化策略""",

            "explanatory": """易于理解的解释性风格，适合引言和相关工作部分：
- 清晰定义研究问题和关键概念
- 提供必要的背景知识和上下文
- 使用类比和比喻辅助解释复杂概念
- 从一般到具体，逐步深入解释
- 适当使用示例说明抽象概念
- 避免过度技术性语言，但不失专业性
- 注重表达的连贯性和可读性
- 逻辑推理清晰，步骤分明
- 预见读者可能的疑问并提前解答""",

            "concise": """简洁明了的写作风格，适合摘要和结论部分：
- 直接阐述核心观点，避免冗余表达
- 每句话具有高信息密度，无废话和填充语
- 优先使用简单直接的句式，避免复杂从句
- 精选词汇，使用准确的术语
- 只包含必要的细节，省略次要信息
- 段落结构紧凑，每段聚焦一个主题
- 使用强有力的动词，避免过多修饰语
- 保持逻辑清晰，避免跳跃式论述
- 总结要点，避免重复""",

            "detailed": """详尽的描述风格，适合实验和结果部分：
- 提供全面的背景和细节信息
- 深入分析数据和现象
- 考虑多个角度和因素
- 详细说明实验设置和条件
- 全面报告实验结果，包括正面和负面发现
- 提供详细的数据分析和统计测试
- 讨论结果的意义和影响
- 探讨各种可能的解释和假设
- 考虑边缘情况和特殊条件
- 提供充分的证据支持结论"""
        }
        
        return style_guides.get(style, style_guides["academic"])
    
    def _get_section_writing_guide(self, section_type: str) -> str:
        """根据论文部分类型获取写作指南"""
        # 映射部分类型到标准类型
        section_mappings = {
            "method": "methodology",
            "results": "experiment",
            "discussion": "conclusion"
        }
        
        # 标准化section_type
        standard_section_type = section_mappings.get(section_type, section_type)
        
        section_guides = {
            "abstract": """
【摘要指南】
- 控制在400-500字以内
- 清晰介绍研究背景、问题和解决方案
- 突出核心创新点和关键研究贡献
- 概述主要实验结果和性能提升
- 不包含引用或缩写
- 避免使用未在摘要中定义的专业术语
- 用一两句话点明研究的理论或实际意义
""",
            "introduction": """
【引言指南】
- 介绍推荐系统研究领域的背景与重要性
- 阐述当前挑战和存在的问题（如冷启动、数据稀疏性、偏好漂移等）
- 简述现有方法的局限性
- 明确提出本文的研究问题、动机和目标
- 概述所提方法的核心思想和创新点
- 总结本文的主要贡献（3-4点）
- 简要描述论文结构
- 确保与推荐系统相关的专业术语正确使用
- 适当引用领域内最新、最相关的文献
""",
            "related_work": """
【相关工作指南】
- 系统性地组织和分类相关研究
- 重点关注推荐系统领域的相关工作，尤其是与本文方法相关的技术和方法
- 按照研究方向或技术类别进行分类讨论
- 重点分析现有方法的优缺点
- 对比分析不同方法在解决目标问题上的效果
- 明确指出本文方法与现有研究的区别和创新点
- 使用准确的引用格式，引用高质量、近期的文献
- 引用应包括最近2-3年内推荐系统顶级会议和期刊的工作（如RecSys, WWW, SIGIR, KDD, TKDE等）
""",
            "methodology": """
【方法论指南】
- 明确定义问题和使用的符号表示
- 详细介绍系统架构和各个组件的功能
- 提供算法的数学公式和详细推导
- 解释模型设计的理论基础和动机
- 阐述模型如何解决引言中提出的挑战
- 详细描述关键创新点及其理论依据
- 提供算法伪代码或流程图以增强可理解性
- 分析算法的时间和空间复杂度
- 讨论算法的局限性和适用场景
- 确保所有变量和符号有明确定义和一致性
""",
            "experiment": """
【实验指南】
- 详细描述实验设置：
  * 数据集选择及其特性（规模、稀疏度、领域等）
  * 数据预处理方法
  * 评估指标（如准确率、召回率、NDCG、覆盖率等）
  * 参数设置和优化方法
  * 实验环境（硬件、软件配置）
- 选择合适的基线方法进行比较（至少5-6种）
- 提供全面的实验结果：
  * 主实验：与基线方法的性能对比
  * 消融实验：验证各组件的有效性
  * 参数敏感性分析：分析关键参数对性能的影响
  * 冷启动/数据稀疏性等特殊情况下的性能
- 使用表格和图表清晰展示结果
- 提供详细的实验结果分析和讨论：
  * 解释性能优势的原因
  * 分析在不同场景下的表现
  * 讨论模型的训练效率和推理时间
  * 分析模型的可解释性和透明度
- 进行案例研究，展示模型在实际场景中的应用效果
- 确保实验的可重复性，提供必要的实现细节
""",
            "conclusion": """
【结论指南】
- 总结研究的主要发现和贡献
- 重申所提方法的核心创新点
- 分析研究的理论和实际意义
- 讨论研究的局限性
- 提出未来可能的研究方向和改进空间
- 避免简单重复论文其他部分的内容
- 确保结论与引言中提出的问题和目标相呼应
- 避免引入新的概念或讨论未在正文中提及的内容
- 用简洁有力的语言总结研究成果
"""
        }
        
        # 获取对应的写作指南，如果没有则返回空字符串
        return section_guides.get(standard_section_type, "")
    
    def _generate_mock_content(self, section_type: str, topic: Optional[str], research_problem: Optional[str], method_feature: Optional[str], key_component: Optional[str] = None) -> str:
        """生成模拟的论文部分内容（仅用于API调用失败时的降级策略）"""
        # 映射部分类型到标准类型
        section_mappings = {
            "method": "methodology",
            "results": "experiment",
            "discussion": "conclusion"
        }
        
        # 标准化section_type
        standard_section_type = section_mappings.get(section_type, section_type)
        
        # 返回简单的占位符内容
        return f"""
## {standard_section_type.title()} (临时内容)

由于生成内容失败，这是系统提供的临时占位内容。
请重新尝试生成此部分内容。
"""
    
    def _generate_mock_suggestions(self, section_type: str) -> List[str]:
        """生成模拟的改进建议（仅用于API调用失败时的降级策略）"""
        # 简单的通用建议列表
        return [
            "建议重新生成内容以获取更专业的建议",
            "请尝试使用更具体的研究主题和方法描述"
        ]
    
    def _format_suggestions(self, suggestions: List[str]) -> List[str]:
        """格式化建议，确保它们是中文格式，并移除不必要的前缀"""
        formatted = []
        for suggestion in suggestions:
            # 去除引号和多余空格
            clean_sugg = suggestion.strip().strip('"\'')
            
            # 检测语言并进行相应处理
            if any('\u4e00' <= char <= '\u9fff' for char in clean_sugg):
                # 已经是中文
                formatted.append(clean_sugg)
            else:
                # 英文建议，可以考虑翻译（这里简单处理）
                # 优化：可以集成翻译API或离线翻译工具
                if clean_sugg.startswith("Ensure") or clean_sugg.startswith("Make sure"):
                    clean_sugg = f"确保{clean_sugg[7:]}"
                elif clean_sugg.startswith("Consider"):
                    clean_sugg = f"考虑{clean_sugg[9:]}"
                elif clean_sugg.startswith("Add"):
                    clean_sugg = f"添加{clean_sugg[4:]}"
                formatted.append(clean_sugg)
        
        return formatted or ["考虑添加更多相关研究引用", "可以增加图表或表格说明", "建议精简冗长的描述，突出核心观点"]
    
    def _standardize_result(self, result, section_type: str = None) -> Dict[str, Any]:
        """标准化结果格式，确保返回符合预期的内容"""
        standard_result = {}
        
        # 如果是字符串，说明是纯文本内容，直接返回
        if isinstance(result, str):
            return {"content": result, "suggestions": []}
        
        try:
            # 处理字典类型响应
            if isinstance(result, dict):
                # 直接尝试提取内容和建议
                if "content" in result and isinstance(result["content"], str):
                    standard_result["content"] = result["content"]
                elif "text" in result and isinstance(result["text"], str):
                    standard_result["content"] = result["text"]
                else:
                    # 尝试解析完整的JSON响应
                    for key, value in result.items():
                        if isinstance(value, str) and len(value) > 100:
                            standard_result["content"] = value
                            break
                
                # 提取建议
                if "suggestions" in result and isinstance(result["suggestions"], list):
                    standard_result["suggestions"] = self._format_suggestions(result["suggestions"])
                elif "improvement_suggestions" in result and isinstance(result["improvement_suggestions"], list):
                    standard_result["suggestions"] = self._format_suggestions(result["improvement_suggestions"])
            
            # 如果没有找到内容，尝试提取任何有意义的文本
            if "content" not in standard_result or not standard_result["content"]:
                # 如果响应是字符串，可能是直接返回的Markdown
                if isinstance(result, str) and len(result) > 10:
                    content, suggestions = self._extract_content_and_suggestions(result)
                    standard_result["content"] = content
                    standard_result["suggestions"] = suggestions
                else:
                    # 尝试将整个响应转为字符串
                    try:
                        response_str = json.dumps(result, ensure_ascii=False)
                        if len(response_str) > 10:
                            content, suggestions = self._extract_content_and_suggestions(response_str)
                            standard_result["content"] = content
                            standard_result["suggestions"] = suggestions
                    except Exception as e:
                        logging.warning(f"无法将响应转换为字符串: {str(e)}")
            
            # 确保有建议
            if "suggestions" not in standard_result or not standard_result["suggestions"]:
                standard_result["suggestions"] = self._generate_mock_suggestions(section_type) if section_type else []
                
            # 如果找不到内容，返回模拟内容
            if "content" not in standard_result or not standard_result["content"]:
                if section_type:
                    standard_result["content"] = self._generate_mock_content(
                        section_type=section_type,
                        topic=None,
                        research_problem=None,
                        method_feature=None
                    )
                else:
                    standard_result["content"] = "无法解析AI响应，请重试。"
            
            return standard_result
        except Exception as e:
            logging.error(f"标准化结果时出错: {str(e)}")
            if section_type:
                standard_result["content"] = self._generate_mock_content(
                    section_type=section_type,
                    topic=None,
                    research_problem=None,
                    method_feature=None
                )
            standard_result["suggestions"] = self._generate_mock_suggestions(section_type) if section_type else []
        
        return standard_result

    async def _generate_paper_section(self, section_type: str, topic: Optional[str], research_problem: Optional[str], method_feature: Optional[str], key_component: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """生成论文指定部分内容"""
        try:
            # 部分类型映射，统一section命名
            section_mappings = {
                "method": "methodology",
                "results": "experiment",
                "discussion": "conclusion"
            }
            
            # 标准化section_type
            standard_section_type = section_mappings.get(section_type, section_type)
            
            # 预先准备中文标题映射（用于后处理）
            section_chinese_titles = {
                "abstract": "摘要",
                "introduction": "引言",
                "related_work": "相关工作",
                "methodology": "方法论",
                "experiment": "实验",
                "conclusion": "结论"
            }
            
            chinese_section_title = section_chinese_titles.get(standard_section_type, "内容")
            
            logging.info(f"生成论文部分: {standard_section_type}")
            
            # 清理和规范化输入参数 - 只处理核心参数：研究主题和额外背景信息
            safe_topic = topic or "推荐系统"
            safe_additional_context = kwargs.get("additional_context") or ""
            
            # 前端已经删除了其他字段，只使用研究主题和额外背景信息
            combined_context = ""
            if safe_additional_context:
                combined_context = f"额外背景信息：\n{safe_additional_context}"
            
            logging.info(f"核心参数: topic={safe_topic}, 背景信息长度={len(combined_context)}")
            
            # 构建写作指南，组合系统提示、部分特定指南和样式指南
            section_guide = self._get_section_writing_guide(standard_section_type)
            system_prompt = self._get_system_prompt()
            
            # 确保首个中文标题正确设置
            first_header = f"## {chinese_section_title}"
            
            # 更强调研究主题的重要性，确保内容围绕主题生成
            user_prompt = f"""【最高优先级：内容必须完全关于【{safe_topic}】】【必须使用中文回答】【禁止使用英文标题】

请用中文为一篇严格关于【{safe_topic}】的学术论文撰写{chinese_section_title}部分内容。整篇内容必须直接讨论【{safe_topic}】，不得偏离此主题。

<CURRENT_CURSOR_POSITION>
首行标题必须是：{first_header}

【核心研究主题】：{safe_topic}（这是最高优先级，所有内容必须紧密围绕此主题）
【论文部分】：{chinese_section_title}

{combined_context}

研究主题【{safe_topic}】是最关键的要求，所有段落都必须与此主题直接相关。每个段落开始前，请确认它是否与【{safe_topic}】直接相关。如果不相关，请不要生成该内容。

请按照以下指南进行撰写:
{section_guide}

严格要求（必须遵守）：
1. 内容必须严格围绕【{safe_topic}】这一核心研究主题展开，这是最高优先级要求
2. 必须完全使用中文撰写所有内容，包括标题和正文
3. 禁止使用任何英文标题（如Abstract、Introduction等）
4. 必须深入探讨【{safe_topic}】的相关概念、方法、技术或实验
5. 确保学术严谨性和专业性，符合推荐系统顶会/顶刊标准
6. 如有引用，请使用中文引用格式，如[王等，2023]

最终输出必须完全符合研究主题【{safe_topic}】，并且是纯中文。不要使用英文标题，不要使用英文段落。
"""
            
            # 调用AI助手生成内容前，确保system_prompt不被覆盖
            forced_system_prompt = f"""你是一位专业的中文学术写作专家，必须用中文输出所有内容。

{system_prompt}

最重要的要求（按优先级排序）：
1. 所有内容必须严格围绕研究主题【{safe_topic}】展开，每个段落都必须与该主题直接相关
2. 不要生成与研究主题【{safe_topic}】无关的内容，即使是学术性的通用内容
3. 输出的第一行必须是：{first_header}
4. 严禁使用英文标题（如"Abstract"、"Introduction"等）
5. 所有标题和子标题必须使用中文
6. 所有正文内容必须是中文

关于主题相关性的具体要求：
- 每写一个段落前，先确认它与研究主题的直接关系
- 所有讨论的概念和方法必须直接应用于研究主题
- 引用的文献必须与研究主题密切相关
- 实验和结果必须针对研究主题的应用场景
- 不要包含通用的推荐系统知识，除非直接应用于研究主题
- 始终保持研究主题作为内容生成的核心锚点
"""
            
            # 调用AI助手生成内容（降低温度以提高主题相关性）
            ai_response = await self.assistant.call_ai_api(
                user_prompt=user_prompt,
                system_prompt=forced_system_prompt,
                temperature=0.3  # 更低的温度以确保紧密围绕主题生成内容
            )
            
            # 在调用API后立即检查并替换标题（无论英文检测结果如何）
            if isinstance(ai_response, str):
                # 预处理：确保首行是正确的中文标题
                if not ai_response.strip().startswith(first_header):
                    logging.warning(f"首行不是预期的中文标题，添加标题: {first_header}")
                    ai_response = f"{first_header}\n\n{ai_response}"
                
                # 替换常见英文标题 - 总是执行此步骤
                eng_to_cn_titles = {
                    "# Abstract": "## 摘要",
                    "## Abstract": "## 摘要",
                    "# Introduction": "## 引言",
                    "## Introduction": "## 引言",
                    "# Related Work": "## 相关工作",
                    "## Related Work": "## 相关工作",
                    "# Methodology": "## 方法论",
                    "## Methodology": "## 方法论",
                    "# Method": "## 方法论",
                    "## Method": "## 方法论",
                    "# Experiment": "## 实验",
                    "## Experiment": "## 实验",
                    "# Results": "## 实验结果",
                    "## Results": "## 实验结果",
                    "# Conclusion": "## 结论",
                    "## Conclusion": "## 结论",
                    "# Key Contributions": "## 主要贡献",
                    "## Key Contributions": "## 主要贡献",
                    "# Improvement Suggestions": "## 改进建议",
                    "## Improvement Suggestions": "## 改进建议",
                    "# References": "## 参考文献",
                    "## References": "## 参考文献"
                }
                
                # 应用替换
                for eng, cn in eng_to_cn_titles.items():
                    ai_response = ai_response.replace(eng, cn)
                
                # 检查是否存在大量英文内容
                english_char_count = sum(1 for c in ai_response if 'a' <= c.lower() <= 'z')
                total_char_count = len(ai_response)
                chinese_char_count = sum(1 for c in ai_response if '\u4e00' <= c <= '\u9fff')
                
                # 记录字符统计情况
                logging.info(f"内容字符统计: 总字符={total_char_count}, 英文字符={english_char_count}, 中文字符={chinese_char_count}")
                logging.info(f"中英文比例: 英文={english_char_count/total_char_count:.2f}, 中文={chinese_char_count/total_char_count:.2f}")
                
                # 降低检测阈值，更容易触发中文重写 - 如果英文字符比例超过15%，或中文字符比例低于30%
                if english_char_count / total_char_count > 0.15 or chinese_char_count / total_char_count < 0.3:
                    logging.warning(f"检测到可能的英文输出，尝试重新生成中文内容")
                    
                    # 添加更强烈的中文要求并强调研究主题的核心地位
                    force_chinese_prompt = f"""我需要你用纯中文重写以下内容，特别注意：

1. 内容必须严格围绕研究主题【{safe_topic}】，这是最核心的要求
2. 确保所有内容与【{safe_topic}】直接相关，不要生成无关内容
3. 必须完全使用中文，包括所有标题、小标题和正文
4. 第一行必须是"{first_header}"，不要使用"Abstract"或其他英文标题
5. 所有标题必须是中文，如"方法"、"实验结果"等，禁止使用英文标题
6. 术语可以保留英文，但需要在括号中注明，如"协同过滤(Collaborative Filtering)"
7. 深入探讨【{safe_topic}】的相关概念、方法和技术

原内容：
{ai_response}

请完全用中文重写，并确保内容严格围绕【{safe_topic}】这一研究主题：
"""
                    
                    # 尝试重新生成中文内容
                    ai_response = await self.assistant.call_ai_api(
                        user_prompt=force_chinese_prompt,
                        system_prompt="你是一位专业的中文学术译者。你的任务是将学术内容完全转换为地道的中文，确保所有标题和正文都使用中文。禁止使用任何英文标题。",
                        temperature=0.3
                    )
                    
                    # 再次检查首行标题
                    if not ai_response.strip().startswith(first_header):
                        logging.warning(f"重写后首行仍不是预期的中文标题，强制添加标题")
                        ai_response = f"{first_header}\n\n{ai_response}"
                
                # 最终检查 - 如果内容仍然以英文为主，使用紧急备选内容
                english_char_count = sum(1 for c in ai_response if 'a' <= c.lower() <= 'z')
                chinese_char_count = sum(1 for c in ai_response if '\u4e00' <= c <= '\u9fff')
                
                if english_char_count > chinese_char_count or chinese_char_count < 200:
                    logging.error("最终内容仍以英文为主或中文内容太少，启用紧急处理！")
                    
                    # 构建一个简单的中文模板，至少确保有一些中文内容
                    fallback_content = f"""## {chinese_section_title}

关于{safe_topic}的研究表明，这是推荐系统领域的重要研究方向。当前研究中存在的一些问题包括数据稀疏性、冷启动和用户兴趣漂移等挑战需要进一步探索。

{combined_context}

## 改进建议

1. 建议重新生成此部分内容，确保使用中文输出
2. 提供更多关于{safe_topic}的具体细节和最新研究进展
3. 添加更多实验结果和分析，证明方法的有效性

【注意：本内容是因原始生成内容不符合中文要求而自动生成的后备内容，请重新提交请求】
"""
                    
                    # 再次尝试通过API获取中文内容
                    try:
                        emergency_prompt = f"""这是紧急请求！我需要你用纯中文编写一个严格关于【{safe_topic}】的论文{chinese_section_title}部分。

{combined_context}

【绝对核心要求】：
1. 每一段内容都必须与【{safe_topic}】直接相关，这是最高优先级
2. 不要生成与【{safe_topic}】无关的内容，即使是通用的学术内容
3. 完全使用中文，包括所有标题和正文
4. 第一行必须是"{first_header}"
5. 内容学术性强，符合推荐系统研究领域标准
6. 文末添加"## 改进建议"部分，列出2-3点建议

禁止任何英文标题出现！必须确保内容100%围绕【{safe_topic}】展开！"""

                        emergency_response = await self.assistant.call_ai_api(
                            user_prompt=emergency_prompt,
                            system_prompt="你是中文学术写作专家。你只能用中文输出内容。禁止使用英文标题。第一行必须是提供的中文标题。",
                            temperature=0.4
                        )
                        
                        # 检查紧急响应是否为中文
                        chinese_count_emergency = sum(1 for c in emergency_response if '\u4e00' <= c <= '\u9fff')
                        if chinese_count_emergency > 100:  # 有足够的中文字符
                            ai_response = emergency_response
                            
                            # 最后检查标题
                            if not ai_response.strip().startswith(first_header):
                                ai_response = f"{first_header}\n\n{ai_response}"
                        else:
                            ai_response = fallback_content
                    except Exception as e:
                        logging.error(f"紧急处理失败: {e}")
                        ai_response = fallback_content
            
            # 标准化AI返回的结果
            content = self._standardize_result(ai_response, standard_section_type)
            
            # 添加成功标志
            content["success"] = True
            
            # 最后的内容合规性检查
            if "content" in content and isinstance(content["content"], str):
                # 检查内容是否以英文标题开头
                first_line = content["content"].strip().split('\n')[0] if content["content"].strip() else ""
                english_title_pattern = re.compile(r'^#+\s+(Abstract|Introduction|Related Work|Method|Methodology|Experiment|Results|Conclusion)', re.IGNORECASE)
                
                if english_title_pattern.match(first_line):
                    logging.warning(f"最终内容仍包含英文标题，进行最后替换: {first_line}")
                    # 使用正则表达式替换英文标题
                    content["content"] = re.sub(
                        r'^#+\s+(Abstract)\b',
                        f"## {section_chinese_titles['abstract']}",
                        content["content"], 
                        flags=re.IGNORECASE
                    )
                    content["content"] = re.sub(
                        r'^#+\s+(Introduction)\b',
                        f"## {section_chinese_titles['introduction']}",
                        content["content"], 
                        flags=re.IGNORECASE
                    )
                    content["content"] = re.sub(
                        r'^#+\s+(Related Work)\b',
                        f"## {section_chinese_titles['related_work']}",
                        content["content"], 
                        flags=re.IGNORECASE
                    )
                    content["content"] = re.sub(
                        r'^#+\s+(Method|Methodology)\b',
                        f"## {section_chinese_titles['methodology']}",
                        content["content"], 
                        flags=re.IGNORECASE
                    )
                    content["content"] = re.sub(
                        r'^#+\s+(Experiment|Results)\b',
                        f"## {section_chinese_titles['experiment']}",
                        content["content"], 
                        flags=re.IGNORECASE
                    )
                    content["content"] = re.sub(
                        r'^#+\s+(Conclusion)\b',
                        f"## {section_chinese_titles['conclusion']}",
                        content["content"], 
                        flags=re.IGNORECASE
                    )
            
            return content
        except Exception as e:
            logging.error(f"生成论文部分时发生错误: {e}", exc_info=True)
            
            # 生成模拟内容作为降级策略
            mock_content = self._generate_mock_content(
                standard_section_type, topic, research_problem, method_feature, key_component
            )
            mock_suggestions = self._generate_mock_suggestions(standard_section_type)
            
            return {
                "content": mock_content,
                "suggestions": mock_suggestions,
                "success": False
            }

    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        return """你是一位资深的中国推荐系统研究专家，在顶级会议和期刊上发表过多篇中文论文，特别专注于用户提供的研究主题领域。

== 最高优先级指令（按重要性排序）==
1. 内容必须100%围绕用户提供的研究主题，每段内容都必须与该主题直接相关
2. 不生成任何与研究主题无关的内容，即使是学术性的通用内容
3. 必须完全使用中文输出所有内容
4. 禁止使用任何英文标题（如Abstract、Introduction等）
5. 所有标题必须是中文（如"摘要"、"引言"等）

关于主题相关性的具体要求：
- 每写一个段落前，先确认它与研究主题的直接关系
- 所有讨论的概念和方法必须直接应用于研究主题
- 引用的文献必须与研究主题密切相关
- 实验和结果必须针对研究主题的应用场景
- 不要包含通用的推荐系统知识，除非直接应用于研究主题
- 始终保持研究主题作为内容生成的核心锚点
"""

# 创建全局实例
ai_assistant_fixed = AIAssistant()

def get_assistant():
    """返回全局AI助手实例"""
    return ai_assistant_fixed 