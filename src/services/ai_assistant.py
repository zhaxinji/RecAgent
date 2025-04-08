import json
import re
import logging
import httpx
import uuid
import os
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from enum import Enum
from . import paper as paper_service
from src.core.config import settings
import urllib.parse
import asyncio
import random
import time

class AIProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "claude"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    DEFAULT = "default"

class AIAssistant:
    """AI助手类，负责与AI API进行交互"""
    
    def __init__(self, api_key: str = None, provider: str = None):
        """
        初始化AI助手
        
        参数:
            api_key: API密钥（可选，默认从配置文件中读取）
            provider: AI提供商（可选，默认从配置文件中读取）
        """
        # 设置API提供商
        self.provider = provider or settings.DEFAULT_AI_PROVIDER
        print(f"AI助手初始化，使用提供商: {self.provider}")
        
        # 设置API密钥
        self.api_key = api_key or settings.LLM_API_KEY
        if not self.api_key:
            raise ValueError("未设置API密钥，请在配置文件中设置LLM_API_KEY或在初始化时提供")
        
        # 设置模型和API基础URL
        self.model = settings.DEFAULT_LLM_MODEL
        
        # 设置各种API的基础URL
        self.api_base = settings.DEEPSEEK_API_BASE
        
        # 添加max_tokens属性，使用默认值4000
        self.max_tokens = getattr(settings, "DEFAULT_MAX_TOKENS", 4000)
        
        print(f"AI助手初始化成功，使用提供商: {self.provider}，模型: {self.model}")
        
        # 创建httpx客户端用于API请求
        self.client = httpx.AsyncClient(base_url=self.api_base)
    
    def set_provider(self, provider: str):
        self.provider = provider
    
    def change_ai_provider(self, provider: str) -> Dict[str, str]:
        """
        切换默认的AI提供商
        
        参数:
            provider: 新的AI提供商名称
            
        返回:
            包含旧提供商和新提供商信息的字典
        """
        old_provider = self.provider
        try:
            self.set_provider(provider)
            return {
                "old_provider": old_provider,
                "new_provider": provider,
                "status": "success"
            }
        except Exception as e:
            logging.error(f"切换AI提供商失败: {str(e)}")
            return {
                "old_provider": old_provider,
                "new_provider": old_provider,
                "status": f"failed: {str(e)}"
            }
    
    async def generate_completion(self, prompt, max_tokens=None, temperature=0.7, verbose=False, system_prompt=None):
        """生成完成内容，增强版本确保更有效地控制提示词长度"""
        if not prompt:
            raise ValueError("Prompt cannot be empty")
        
        # 限制最大token数
        if max_tokens is None:
            # 根据提示词长度自适应token数
            prompt_length = len(prompt)
            max_tokens = min(8000, max(2000, int(prompt_length * 0.5)))  # 自适应调整
        
        # 提示词长度安全检查 - 大幅降低阈值以避免代理超时
        max_chars = 8000  # 8000字符上限，对于methodolgy设置更低
        if len(prompt) > max_chars:
            print(f"提示词过长({len(prompt)}字符)，截断至最大{max_chars}字符")
            # 智能截断：保留前60%和后40%
            front_part = int(max_chars * 0.6)
            back_part = max_chars - front_part - 20
            prompt = prompt[:front_part] + "\n...[内容省略]...\n" + prompt[-back_part:] if back_part > 0 else prompt[:max_chars]
        
        # 如果未指定max_tokens，则使用配置或默认值
        max_tokens = max_tokens or self.max_tokens or 2000  # 默认减少到2000
        
        # 记录请求信息
        if verbose:
            print(f"生成请求：长度={len(prompt)}字符，max_tokens={max_tokens}")
        
        # 重试策略
        max_retries = 3
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                # 调用API
                response = await self._call_deepseek_api(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system_prompt=system_prompt
                )
                return response
            except Exception as e:
                retry_count += 1
                last_error = e
                error_msg = str(e).lower()
                
                print(f"API调用失败 (尝试 {retry_count}/{max_retries}): {error_msg}")
                
                # 错误类型检测
                if retry_count < max_retries:
                    # 不同类型错误的处理策略
                    if "timeout" in error_msg:
                        # 超时错误 - 大幅减少请求内容
                        new_length = int(len(prompt) * 0.4)  # 更激进，减少60%
                        prompt = prompt[:new_length]
                        print(f"超时错误，减少提示词长度至{new_length}字符后重试")
                        max_tokens = int(max_tokens * 0.75)  # 减少生成长度
                        
                    elif "too many tokens" in error_msg or "maximum context length" in error_msg:
                        # Token过多错误
                        new_length = int(len(prompt) * 0.3)  # 更激进，减少70%
                        prompt = prompt[:new_length] 
                        print(f"Token超限，减少提示词长度至{new_length}字符后重试")
                        max_tokens = int(max_tokens * 0.6)  # 大幅减少生成长度
                        
                    else:
                        # 其他错误，减少30%内容
                        new_length = int(len(prompt) * 0.7)
                        prompt = prompt[:new_length]
                        print(f"遇到错误，减少提示词长度至{new_length}字符后重试")
                    
                    # 等待后重试
                    await asyncio.sleep(2)
                else:
                    # 最后一次尝试失败
                    print(f"达到最大重试次数，所有尝试均失败")
                    raise Exception(f"在{max_retries}次尝试后API调用仍然失败: {str(last_error)}")
                
        # 不应该执行到这里
        return "生成失败"

    def _preprocess_prompt(self, prompt):
        """
        预处理提示词，估算token数并在必要时进行截断
        
        Args:
            prompt: 原始提示词
        
        Returns:
            处理后的提示词和token信息
        """
        # 粗略估算token数（按照英文1:1.5，中文1:2的比例）
        english_char_count = sum(1 for c in prompt if ord(c) < 128)
        chinese_char_count = len(prompt) - english_char_count
        
        estimated_tokens = int(english_char_count * 0.25 + chinese_char_count * 0.5)
        token_info = {
            "estimated_tokens": estimated_tokens,
            "prompt_length": len(prompt),
            "english_chars": english_char_count,
            "chinese_chars": chinese_char_count
        }
        
        # 如果估计的token数超过阈值，进行截断
        max_allowed_tokens = 6000  # 设置一个安全阈值
        if estimated_tokens > max_allowed_tokens:
            # 计算需要保留的比例
            keep_ratio = max_allowed_tokens / estimated_tokens
            truncated_prompt = self._truncate_prompt(prompt, ratio=keep_ratio)
            print(f"提示词过长(估计{estimated_tokens}tokens)，已截断至{len(truncated_prompt)}/{len(prompt)}字符")
            return truncated_prompt, {**token_info, "truncated": True, "truncated_length": len(truncated_prompt)}
        
        return prompt, token_info

    def _truncate_prompt(self, prompt, ratio=None, max_length=None):
        """
        智能截断提示词，尽量保留重要信息
        
        Args:
            prompt: 原始提示词
            ratio: 保留的比例，0-1之间
            max_length: 最大长度限制
        
        Returns:
            截断后的提示词
        """
        if not ratio and not max_length:
            return prompt
        
        # 如果指定了比例，计算目标长度
        if ratio:
            target_length = int(len(prompt) * ratio)
        else:
            target_length = max_length
        
        # 如果目标长度大于原始长度，不需要截断
        if target_length >= len(prompt):
            return prompt
        
        # 找到提示词中的指令部分（通常在开头）和内容部分
        lines = prompt.split('\n')
        instruction_end = 0
        
        # 假设前10行是指令部分
        max_instruction_lines = min(10, len(lines) // 3)
        instruction_text = '\n'.join(lines[:max_instruction_lines])
        content_text = '\n'.join(lines[max_instruction_lines:])
        
        # 保留所有指令，截断内容部分
        content_target_length = target_length - len(instruction_text)
        if content_target_length <= 0:
            # 极端情况，指令部分已超过目标长度，则对整个文本进行简单截断
            return prompt[:target_length]
        
        # 截取内容部分的起始和结尾
        # 策略：保留开头60%和结尾40%的内容，中间部分省略
        start_portion = 0.6
        start_length = int(content_target_length * start_portion)
        end_length = content_target_length - start_length
        
        truncated_content = content_text[:start_length]
        if end_length > 0:
            truncated_content += f"\n\n... [内容已截断，保留前{start_length}字符和后{end_length}字符] ...\n\n"
            truncated_content += content_text[-end_length:]
        
        return instruction_text + '\n' + truncated_content
    
    def _fix_json(self, json_str: str) -> str:
        """尝试修复无效的JSON字符串"""
        try:
            # 移除可能的前缀和后缀文本
            start_idx = json_str.find('{')
            end_idx = json_str.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = json_str[start_idx:end_idx]
            
            # 尝试解析
            json.loads(json_str)
            return json_str
        except:
            # 如果仍然无法解析，则返回一个默认的JSON
            return json.dumps({
                "summary": "无法解析AI返回的内容为有效JSON",
                "innovations": []
            }, ensure_ascii=False)
    
    async def _call_openai_api(self, prompt, max_tokens, temperature, system_prompt=None):
        """
        调用OpenAI API生成文本

        Args:
            prompt: 用户提示词
            max_tokens: 最大生成token数
            temperature: 采样温度
            system_prompt: 系统提示，用于定义AI助手的行为

        Returns:
            API响应内容
        """
        import httpx
        import json
        import time
        
        api_key = self.api_key
        api_base = self.api_base or "https://api.openai.com/v1"
        
        # 创建header
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 构建请求数据
        messages = []
        
        # 添加系统提示（如果有）
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        # 添加用户提示
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": self.model,
            "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
        
        async with httpx.AsyncClient(timeout=120.0) as client:  # 增加超时时间到120秒
            response = await client.post(
                f"{api_base.rstrip('/')}/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                response_json = response.json()
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    return response_json["choices"][0]["message"]["content"]
                else:
                    error_msg = f"OpenAI API 返回了不包含有效内容的响应: {response.text}"
                    print(f"错误: {error_msg}")
                    return f"API 调用出错: {error_msg}"
            else:
                error_msg = f"OpenAI API 调用失败，状态码: {response.status_code}, 响应: {response.text}"
                print(f"错误: {error_msg}")
                
                # 对于常见错误进行更友好的处理
                if response.status_code == 429:
                    return "API 服务器负载过高或达到速率限制，请稍后再试。"
                elif response.status_code >= 500:
                    return "API 服务器出现错误，请稍后再试。"
                else:
                    return f"API 调用出错: {error_msg}"
        
    async def _call_deepseek_api(self, prompt, max_tokens, temperature, stream=False, system_prompt=None):
        """
        调用DeepSeek API，使用更可靠的连接策略，解决超时问题
        
        Args:
            prompt: 提示词文本
            max_tokens: 生成的最大token数
            temperature: 采样温度
            stream: 是否使用流式传输
            system_prompt: 系统提示，用于定义AI助手的行为
        
        Returns:
            API响应内容
        """
        import httpx
        import urllib.parse
        import asyncio
        import random
        import time
        
        # 记录请求信息
        request_id = str(uuid.uuid4())[:8]
        print(f"[{request_id}] DeepSeek API 请求: 提示词长度={len(prompt)}, max_tokens={max_tokens}, temp={temperature}")
        start_time = time.time()
        
        # 预先截断过长的提示词，避免超时
        if len(prompt) > 8000:  # 降低阈值以减少超时风险
            print(f"[{request_id}] 提示词过长({len(prompt)}字符)，执行智能截断")
            # 保留前60%和后30%
            front_len = int(8000 * 0.65)
            back_len = 8000 - front_len - 50
            prompt = prompt[:front_len] + "\n\n...[内容已省略]...\n\n" + prompt[-back_len:]
            print(f"[{request_id}] 截断后长度: {len(prompt)}字符")
        
        # 创建请求数据
        api_key = self.api_key
        
        # 规范化API基础URL，防止URL路径重复
        base_url = self.api_base or "https://api.deepseek.com"
        
        # 移除末尾的斜杠
        base_url = base_url.rstrip('/')
            
        # 分析URL看是否已包含v1路径
        parsed_url = urllib.parse.urlparse(base_url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        # 构建正确的完整URL
        if 'v1' in path_parts:
            # URL已包含v1，直接添加chat/completions
            api_url = f"{base_url}/chat/completions"
        else:
            # URL不包含v1，需要添加完整路径
            api_url = f"{base_url}/v1/chat/completions"
            
        model = self.model or "deepseek-chat"
        
        # 构建请求数据，更好地兼容API格式
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
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 高级重试逻辑
        max_retries = 5  # 增加最大重试次数
        base_timeout = 60.0  # 增加基础超时时间到60秒
        
        # 计算原始内容长度用于判断
        original_prompt_length = len(prompt)
        original_max_tokens = max_tokens
        
        # 退避重试策略
        for attempt in range(max_retries):
            # 计算当前尝试的超时时间（随着重试次数增加）
            current_timeout = base_timeout * (1 + attempt * 0.5)
            
            try:
                print(f"[{request_id}] 尝试API请求 ({attempt+1}/{max_retries}), 超时设置: {current_timeout}秒")
                
                # 创建客户端，设置合理的超时
                timeout_settings = httpx.Timeout(
                    connect=20.0,  # 增加连接超时
                    read=current_timeout,  # 读取超时
                    write=20.0,  # 增加写入超时
                    pool=20.0  # 增加连接池超时
                )
                
                # 默认会使用系统代理，除非显式禁用
                async with httpx.AsyncClient(timeout=timeout_settings) as client:
                    response = await client.post(
                        url=api_url,
                        json=data,
                        headers=headers
                    )
                    
                    # 处理成功响应
                    if response.status_code == 200:
                        result = response.json()
                        if "choices" in result and len(result["choices"]) > 0:
                            message = result["choices"][0]["message"]
                            if "content" in message:
                                content = message["content"]
                                elapsed_time = time.time() - start_time
                                print(f"[{request_id}] API请求成功，用时: {elapsed_time:.2f}秒，响应长度: {len(content)}")
                                return content
                        
                        print(f"[{request_id}] API响应格式异常: {result}")
                        raise ValueError("API响应格式异常")
                    else:
                        # 处理错误响应
                        error_msg = f"API请求失败: 状态码 {response.status_code}, 响应: {response.text}"
                        print(f"[{request_id}] {error_msg}")
                        
                        # 429状态码表示请求过多，需要更长的等待时间
                        if response.status_code == 429:
                            retry_after = int(response.headers.get('retry-after', 5)) + random.randint(1, 5)
                            print(f"[{request_id}] 请求过多 (429)，等待 {retry_after} 秒后重试")
                            await asyncio.sleep(retry_after)
                        elif 500 <= response.status_code < 600:
                            # 服务器错误，等待后重试
                            wait_time = 2 ** attempt + random.random() * 2  # 指数退避
                            print(f"[{request_id}] 服务器错误 ({response.status_code})，等待 {wait_time:.1f} 秒后重试")
                            await asyncio.sleep(wait_time)
                        else:
                            # 其他错误直接抛出
                            raise Exception(error_msg)
                
            except httpx.TimeoutException as e:
                # 处理超时异常
                wait_time = 2 ** attempt + random.random() * 5  # 增加等待时间
                elapsed_time = time.time() - start_time
                print(f"[{request_id}] API请求超时 (尝试 {attempt+1}/{max_retries}): {str(e)}, 已用时: {elapsed_time:.2f}秒")
                
                if attempt < max_retries - 1:
                    # 如果还有重试次数，更激进地减少提示词长度
                    reduction_factor = 0.6 ** (attempt + 1)  # 更激进的减少因子
                    
                    # 确保提示词长度不小于原始长度的20%
                    min_length = max(int(original_prompt_length * 0.2), 1000)
                    new_length = max(int(len(prompt) * reduction_factor), min_length)
                    
                    front_len = int(new_length * 0.7)  # 前面部分占更多
                    back_len = new_length - front_len - 50
                    
                    # 确保back_len不是负数
                    if back_len < 0:
                        front_len = new_length - 50
                        back_len = 0
                    
                    if front_len > 0 and back_len >= 0:
                        prompt = prompt[:front_len] + "\n\n...[内容已大幅省略以避免超时]...\n\n" + (prompt[-back_len:] if back_len > 0 else "")
                        print(f"[{request_id}] 超时重试：减少提示词长度至 {len(prompt)} 字符 (原始长度的 {len(prompt)/original_prompt_length*100:.1f}%)")
                        
                        # 同时减少生成的token数，减轻模型负担
                        max_tokens = max(int(max_tokens * 0.7), 500)  # 确保不小于500
                        print(f"[{request_id}] 超时重试：减少max_tokens至 {max_tokens} (原始值的 {max_tokens/original_max_tokens*100:.1f}%)")
                        
                        # 更新请求数据
                        data["messages"][0]["content"] = prompt
                        data["max_tokens"] = max_tokens
                    
                    print(f"[{request_id}] 等待 {wait_time:.1f} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    # 最后一次重试失败，抛出异常
                    total_time = time.time() - start_time
                    raise Exception(f"API请求在 {max_retries} 次尝试后仍然超时，总用时: {total_time:.2f}秒")
                    
            except httpx.ConnectError as e:
                # 处理连接错误
                wait_time = 3 ** attempt + random.random() * 5
                print(f"[{request_id}] API连接错误 (尝试 {attempt+1}/{max_retries}): {str(e)}")
                
                if attempt < max_retries - 1:
                    print(f"[{request_id}] 等待 {wait_time:.1f} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    total_time = time.time() - start_time
                    raise Exception(f"API连接在 {max_retries} 次尝试后仍然失败，总用时: {total_time:.2f}秒")
                    
            except Exception as e:
                # 处理其他异常
                elapsed_time = time.time() - start_time
                print(f"[{request_id}] API请求发生其他异常 (尝试 {attempt+1}/{max_retries}): {str(e)}, 已用时: {elapsed_time:.2f}秒")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt + random.random() * 3
                    print(f"[{request_id}] 等待 {wait_time:.1f} 秒后重试...")
                    await asyncio.sleep(wait_time)
                    
                    # 如果是最后几次尝试，尝试大幅减少提示词长度以提高成功率
                    if attempt >= max_retries - 3 and len(prompt) > 2000:
                        prompt = prompt[:1500] + "\n\n...[内容已大幅省略]...\n\n" + prompt[-500:]
                        print(f"[{request_id}] 最后尝试：极限减少提示词长度至 {len(prompt)} 字符")
                        max_tokens = min(max_tokens, 1000)
                        print(f"[{request_id}] 最后尝试：限制max_tokens至 {max_tokens}")
                        
                        # 更新请求数据
                        data["messages"][0]["content"] = prompt
                        data["max_tokens"] = max_tokens
            else:
                    total_time = time.time() - start_time
                    raise Exception(f"API请求在 {max_retries} 次尝试后仍然失败: {str(e)}, 总用时: {total_time:.2f}秒")
        
        # 如果所有重试都失败
        total_time = time.time() - start_time
        raise Exception(f"所有API请求尝试均失败，总用时: {total_time:.2f}秒")


# 创建全局实例
ai_assistant = AIAssistant()

def _get_assistant():
    """返回全局AI助手实例"""
    return ai_assistant 