from typing import Dict, Any, List, Optional, Union
import httpx
import re
import json
from datetime import datetime, timedelta
import asyncio
from lxml import etree
import xmltodict
from urllib.parse import quote_plus
import time
import traceback
import os
import pickle
from functools import lru_cache

from src.schemas.paper import SearchSourceEnum, ExternalSearchResult, ExternalSearchResponse
from src.core.config import settings

# 添加常量配置，便于统一管理和调整
TIMEOUT_DEFAULT = 30.0  # 默认超时时间（秒）
RETRY_ATTEMPTS = 3      # 默认重试次数
RETRY_DELAY_BASE = 2    # 基础重试延迟（秒）
CACHE_EXPIRY = 3600     # 缓存过期时间（秒）
MAX_CONCURRENT_REQUESTS = 3  # 最大并发请求数

class PaperSearchService:
    """论文检索服务，提供对多个学术数据库的检索功能"""
    
    def __init__(self):
        # 添加代理配置，解决网络连接问题
        proxy = settings.PROXY_URL if hasattr(settings, 'PROXY_URL') else None
        
        # 创建默认客户端，提高超时时间并启用重试
        self.client = httpx.AsyncClient(
            timeout=TIMEOUT_DEFAULT, 
            follow_redirects=True,
            proxy=proxy
        )
        
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        self.headers = {"User-Agent": self.user_agent}
        
        # 创建缓存目录
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 初始化健康状态跟踪
        self.source_health = {
            source: {"status": True, "last_check": datetime.now(), "failures": 0} 
            for source in SearchSourceEnum
        }
        
        # 限制并发请求的信号量
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    def __del__(self):
        """析构函数，确保客户端正确关闭"""
        if hasattr(self, 'client') and self.client:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.client.aclose())
                else:
                    loop.run_until_complete(self.client.aclose())
            except Exception:
                pass
    
    def _get_cache_key(self, query: str, source: SearchSourceEnum, **params):
        """生成缓存键"""
        # 将所有参数合并为一个字典
        all_params = {
            "query": query,
            "source": source.value,
            **params
        }
        # 将字典转换为排序后的字符串
        param_str = json.dumps(all_params, sort_keys=True)
        # 使用简单的哈希函数生成缓存键
        import hashlib
        return hashlib.md5(param_str.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str):
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{cache_key}.pkl")
    
    async def _get_from_cache(self, cache_key: str):
        """从缓存中获取数据"""
        cache_path = self._get_cache_path(cache_key)
        if os.path.exists(cache_path):
            try:
                # 检查文件是否过期
                modified_time = os.path.getmtime(cache_path)
                if time.time() - modified_time > CACHE_EXPIRY:
                    print(f"缓存已过期: {cache_key}")
                    return None
                
                # 读取缓存文件
                with open(cache_path, 'rb') as f:
                    cached_data = pickle.load(f)
                print(f"使用缓存数据: {cache_key}")
                return cached_data
            except Exception as e:
                print(f"读取缓存错误: {e}")
        return None
    
    async def _save_to_cache(self, cache_key: str, data):
        """保存数据到缓存"""
        if not data:  # 不缓存空结果
            return
        
        cache_path = self._get_cache_path(cache_key)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            print(f"数据已缓存: {cache_key}")
        except Exception as e:
            print(f"缓存数据错误: {e}")
    
    async def _safe_request(self, method: str, url: str, **kwargs):
        """安全的HTTP请求封装，添加重试逻辑和错误处理"""
        # 提取源信息，用于健康检查
        source = kwargs.pop('source', None)
        
        # 如果源已经标记为不健康，直接返回None
        if source and not self.source_health[source]['status']:
            last_failure = self.source_health[source]['last_check']
            # 如果失败时间超过5分钟，重试
            if datetime.now() - last_failure > timedelta(minutes=5):
                print(f"源 {source.value} 之前失败，尝试恢复...")
                self.source_health[source]['status'] = True
            else:
                print(f"源 {source.value} 不健康，跳过请求")
                return None
                
        max_retries = kwargs.pop('max_retries', RETRY_ATTEMPTS)
        retry_delay = kwargs.pop('retry_delay', RETRY_DELAY_BASE)
        
        # 确保超时设置
        if 'timeout' not in kwargs:
            kwargs['timeout'] = TIMEOUT_DEFAULT
        
        # 添加标准头信息
        headers = kwargs.pop('headers', {})
        kwargs['headers'] = {**self.headers, **headers}
        
        # 设置最大重定向次数
        kwargs['follow_redirects'] = True
        
        for attempt in range(max_retries):
            try:
                # 使用信号量限制并发请求
                async with self.semaphore:
                    if method.lower() == 'get':
                        response = await self.client.get(url, **kwargs)
                    elif method.lower() == 'post':
                        response = await self.client.post(url, **kwargs)
                    else:
                        raise ValueError(f"不支持的HTTP方法: {method}")
                    
                    # 检查HTTP状态码
                    response.raise_for_status()
                    
                    # 成功请求，更新源健康状态
                    if source:
                        self.source_health[source] = {
                            "status": True,
                            "last_check": datetime.now(),
                            "failures": 0
                        }
                    
                    return response
            except httpx.TimeoutException:
                print(f"请求超时 ({attempt+1}/{max_retries}): {url}")
            except httpx.HTTPStatusError as e:
                print(f"HTTP错误 {e.response.status_code} ({attempt+1}/{max_retries}): {url}")
                # 对于某些状态码不重试
                if e.response.status_code in [401, 403, 404]:
                    break
            except Exception as e:
                print(f"请求错误 ({attempt+1}/{max_retries}): {url} - {str(e)}")
            
            # 记录源故障
            if source:
                self.source_health[source]['failures'] += 1
                self.source_health[source]['last_check'] = datetime.now()
                # 如果连续失败超过阈值，标记源为不健康
                if self.source_health[source]['failures'] >= 3:
                    self.source_health[source]['status'] = False
                    print(f"源 {source.value} 标记为不健康")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                # 使用指数退避策略
                wait_time = retry_delay * (2 ** attempt)
                print(f"等待 {wait_time} 秒后重试...")
                await asyncio.sleep(wait_time)
        
        return None
    
    async def search_papers(
        self,
        query: str,
        sources: List[SearchSourceEnum] = [SearchSourceEnum.ARXIV, SearchSourceEnum.SEMANTICSCHOLAR, 
                                          SearchSourceEnum.CORE, SearchSourceEnum.OPENALEX],
        limit: int = 10,
        offset: int = 0,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        full_text: bool = False,
        domain: Optional[str] = None,
        venues: Optional[List[str]] = None
    ) -> ExternalSearchResponse:
        """从多个学术数据库搜索论文"""
        print(f"开始搜索，关键词: '{query}', 来源: {sources}, 限制: {limit}, 偏移: {offset}")
        print(f"搜索条件：年份范围: {year_from}-{year_to}, 全文搜索: {full_text}, 领域: {domain}, 会议/期刊: {venues}")
        
        all_results = []
        search_tasks = []
        
        # 确保sources是有效的枚举值
        valid_sources = []
        for source in sources:
            if isinstance(source, str):
                try:
                    valid_source = SearchSourceEnum(source)
                    valid_sources.append(valid_source)
                except ValueError:
                    print(f"忽略无效的搜索源: {source}")
            else:
                valid_sources.append(source)
        
        # 检查是否有有效的搜索源，如果没有则使用默认值
        if not valid_sources:
            print("未指定有效的搜索源，使用默认值")
            valid_sources = [SearchSourceEnum.ARXIV, SearchSourceEnum.SEMANTICSCHOLAR]
        
        # 过滤掉不支持的搜索源
        supported_sources = [
            SearchSourceEnum.ARXIV,
            SearchSourceEnum.SEMANTICSCHOLAR,
            SearchSourceEnum.CORE, 
            SearchSourceEnum.OPENALEX,
            SearchSourceEnum.LOCAL
        ]
        
        valid_sources = [source for source in valid_sources if source in supported_sources]
        
        if not valid_sources:
            print("没有指定支持的搜索源，使用默认配置")
            valid_sources = [SearchSourceEnum.ARXIV]
        
        sources = valid_sources
        print(f"最终使用的搜索源: {sources}")
        
        # 净化搜索查询
        clean_query = query.strip()
        
        # 如果查询为空但有领域，使用领域作为查询
        if not clean_query and domain:
            clean_query = domain
            print(f"查询为空，使用领域 '{domain}' 作为查询")
        
        # 如果查询和领域都为空，使用默认查询
        if not clean_query and not domain:
            clean_query = "recommendation system"
            print(f"查询和领域都为空，使用默认查询 '{clean_query}'")
        
        # 对于每个源，首先尝试从缓存获取结果
        for source in sources:
            # 生成缓存键
            cache_key = self._get_cache_key(
                clean_query, 
                source,
                limit=limit,
                offset=offset,
                year_from=year_from,
                year_to=year_to,
                full_text=full_text,
                domain=domain,
                venues=venues
            )
            
            # 尝试从缓存获取结果
            cached_results = await self._get_from_cache(cache_key)
            if cached_results:
                print(f"使用 {source.value} 的缓存结果")
                all_results.extend(cached_results)
                continue
            
            # 如果缓存未命中，创建搜索任务
            if source == SearchSourceEnum.ARXIV:
                print(f"添加arXiv搜索任务")
                search_tasks.append((source, self.search_arxiv(clean_query, limit, offset, year_from, year_to, domain), cache_key))
            elif source == SearchSourceEnum.SEMANTICSCHOLAR:
                print(f"添加Semantic Scholar搜索任务")
                search_tasks.append((source, self.search_semantic_scholar_crawler(clean_query, limit, offset, year_from, year_to), cache_key))
            elif source == SearchSourceEnum.CORE:
                print(f"添加CORE搜索任务")
                search_tasks.append((source, self.search_core_crawler(clean_query, limit, offset, year_from, year_to), cache_key))
            elif source == SearchSourceEnum.OPENALEX:
                print(f"添加OpenAlex搜索任务")
                search_tasks.append((source, self.search_openalex_crawler(clean_query, limit, offset, year_from, year_to), cache_key))
            elif source == SearchSourceEnum.LOCAL:
                # 本地搜索在另一个服务中实现
                print(f"跳过LOCAL搜索源(未实现)")
        
        # 如果所有结果都从缓存获取，且至少有一个结果，直接返回
        if all_results and not search_tasks:
            print(f"所有结果都从缓存获取，共 {len(all_results)} 条")
            # 排序并限制结果
            all_results.sort(
                key=lambda x: x.publication_date if x.publication_date else datetime.min,
                reverse=True
            )
            total_count = len(all_results)
            limited_results = all_results[offset:offset+limit] if offset < len(all_results) else []
            
            return ExternalSearchResponse(
                results=limited_results,
                total=total_count,
                query=query
            )
        
        # 异步执行所有未缓存的搜索任务
        try:
            # 增加任务处理的容错性
            results = await asyncio.gather(*[task for _, task, _ in search_tasks], return_exceptions=True)
            
            # 处理结果并缓存
            for i, ((source, _, cache_key), result) in enumerate(zip(search_tasks, results)):
                if isinstance(result, Exception):
                    print(f"搜索任务 {source.value} 发生错误: {result}")
                    traceback.print_exception(type(result), result, result.__traceback__)
                    continue
                
                if isinstance(result, list):
                    print(f"搜索任务 {source.value} 成功, 返回 {len(result)} 条结果")
                    all_results.extend(result)
                    
                    # 缓存结果
                    if result:
                        await self._save_to_cache(cache_key, result)
                else:
                    print(f"搜索任务 {source.value} 返回了意外的类型: {type(result)}")
            
            # 如果没有结果，尝试放宽条件
            if not all_results and SearchSourceEnum.ARXIV in sources:
                print("没有找到结果，尝试放宽条件重新搜索ArXiv")
                try:
                    # 使用更宽松的搜索条件
                    relaxed_query = clean_query.split()[0] if clean_query and ' ' in clean_query else clean_query
                    print(f"放宽条件的搜索查询: '{relaxed_query}'")
                    
                    relaxed_results = await self.search_arxiv(relaxed_query, limit, offset, None, None, None)
                    
                    if relaxed_results:
                        print(f"放宽条件搜索找到 {len(relaxed_results)} 条结果")
                        all_results.extend(relaxed_results)
                        
                        # 缓存放宽条件的结果
                        fallback_cache_key = self._get_cache_key(
                            relaxed_query, 
                            SearchSourceEnum.ARXIV,
                            limit=limit,
                            offset=offset
                        )
                        await self._save_to_cache(fallback_cache_key, relaxed_results)
                except Exception as e:
                    print(f"放宽条件搜索错误: {e}")
            
            # 默认按发布时间从新到旧排序
            if all_results:
                all_results.sort(
                    key=lambda x: x.publication_date if x.publication_date else datetime.min,
                    reverse=True
                )
            
            # 限制结果数量
            total_count = len(all_results)
            limited_results = all_results[offset:offset+limit] if offset < len(all_results) else []
            
            return ExternalSearchResponse(
                results=limited_results,
                total=total_count,
                query=query
            )
        except Exception as e:
            print(f"搜索执行错误: {e}")
            traceback.print_exc()
            
            # 即使有错误，也返回已经获取到的结果
            if all_results:
                print(f"尽管有错误，仍然返回已获取的 {len(all_results)} 条结果")
                # 排序并限制结果
                all_results.sort(
                    key=lambda x: x.publication_date if x.publication_date else datetime.min,
                    reverse=True
                )
                total_count = len(all_results)
                limited_results = all_results[offset:offset+limit] if offset < len(all_results) else []
                
                return ExternalSearchResponse(
                    results=limited_results,
                    total=total_count,
                    query=query
                )
            
            return ExternalSearchResponse(
                results=[],
                total=0,
                query=query
            )
    
    async def search_arxiv(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        domain: Optional[str] = None
    ) -> List[ExternalSearchResult]:
        """搜索arXiv论文数据库"""
        # 构建arXiv API查询
        search_query = query.strip()
        
        # 如果查询为空，返回空结果
        if not search_query:
            print("arXiv搜索：查询为空，返回空结果")
            return []
        
        print(f"arXiv搜索：开始处理查询 '{search_query}'")
        
        # 检查是否包含推荐系统相关关键词
        recommendation_keywords = ["recommendation", "recommender", "recommend", "推荐"]
        has_recommendation_terms = any(keyword in search_query.lower() for keyword in recommendation_keywords)
        
        # 检查是否为研究方向关键词
        research_directions = ["sequential", "graph", "multi_modal", "knowledge", "contrastive", 
                             "llm", "explainable", "fairness", "cold_start", "federated", 
                             "reinforcement", "self_supervised", "序列", "图神经网络", "多模态", 
                             "知识增强", "对比学习", "大模型", "可解释", "公平", "冷启动", "联邦", "强化学习", "自监督"]
        
        is_research_direction = any(direction in search_query.lower() for direction in research_directions)
        
        # 根据查询类型和长度采用不同的策略
        word_count = len(search_query.split())
        
        # 对所有查询都添加推荐系统相关术语，除非已经包含
        if not has_recommendation_terms:
            recommender_terms = "(recommender OR recommendation OR \"recommender system\")"
            
            # 对于研究方向关键词，始终添加推荐系统术语
            if is_research_direction:
                search_query = f"{search_query} AND {recommender_terms}"
                print(f"arXiv搜索：检测到研究方向关键词，添加推荐系统术语：'{search_query}'")
            # 对于简单查询也添加推荐系统术语
            elif word_count <= 3:
                search_query = f"{search_query} AND {recommender_terms}"
                print(f"arXiv搜索：简单查询，添加推荐系统术语：'{search_query}'")
            # 对于长查询，如果指定了领域，则添加领域和推荐系统术语
            elif domain:
                search_query = f"{search_query} AND {domain} AND {recommender_terms}"
                print(f"arXiv搜索：复杂查询，添加领域和推荐系统术语：'{search_query}'")
            # 对于其他复杂查询，也添加推荐系统术语，但权重低一些
            else:
                search_query = f"{search_query} AND {recommender_terms}"
                print(f"arXiv搜索：复杂查询，添加推荐系统术语：'{search_query}'")
        # 如果已包含推荐系统术语但有领域参数，添加领域
        elif domain:
            search_query = f"{search_query} AND {domain}"
            print(f"arXiv搜索：查询已包含推荐系统术语，添加领域：'{search_query}'")
            
        # 添加年份过滤
        date_filter = []  # 在条件外初始化date_filter变量
        if year_from or year_to:
            if year_from:
                date_filter.append(f"submittedDate:[{year_from} TO *]")
            if year_to:
                date_filter.append(f"submittedDate:[* TO {year_to}]")
        
        if date_filter:  # 判断date_filter是否有内容
            search_query = f"{search_query} AND ({' AND '.join(date_filter)})"
            print(f"arXiv搜索：添加年份限制后的查询: '{search_query}'")
        
        # 替换为URL编码
        encoded_query = quote_plus(search_query)
        
        # 构建API URL - 增加最大结果数，以便获得更多候选结果
        max_results = min(limit * 2, 50)  # 搜索数量翻倍，但不超过50
        url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_query}&start={offset}&max_results={max_results}&sortBy=relevance"
        print(f"arXiv搜索最终URL: {url}")
        
        # 使用安全请求方法
        response = await self._safe_request(
            'get', 
            url, 
            source=SearchSourceEnum.ARXIV,
            max_retries=RETRY_ATTEMPTS,
            retry_delay=RETRY_DELAY_BASE
        )
        
        if not response:
            print("arXiv搜索请求失败，返回空结果")
            return []
        
        try:
            # 保存原始响应以便调试
            raw_response = response.text
            print(f"arXiv搜索响应状态码: {response.status_code}")
            print(f"arXiv搜索响应内容长度: {len(raw_response)} 字节")
            
            # 解析XML响应
            try:
                feed = xmltodict.parse(raw_response)
            except Exception as e:
                print(f"arXiv搜索：XML解析错误: {e}")
                return []
            
            if "feed" not in feed:
                print("arXiv搜索：响应中没有feed元素")
                print(f"arXiv搜索响应的前100个字符: {raw_response[:100]}")
                return []
            
            if "entry" not in feed["feed"]:
                print("arXiv搜索：feed中没有entry元素")
                # 检查响应中是否有错误信息
                if "error" in feed["feed"]:
                    print(f"arXiv搜索错误: {feed['feed']['error']}")
                print(f"arXiv搜索feed内容: {feed['feed'].keys()}")
                return []
            
            entries = feed["feed"]["entry"]
            if not isinstance(entries, list):
                entries = [entries]
            
            print(f"arXiv搜索：找到 {len(entries)} 条原始结果")
            results = []
            
            for entry in entries:
                # 提取作者
                if "author" in entry:
                    if isinstance(entry["author"], list):
                        authors = [{"name": author.get("name", "")} for author in entry["author"]]
                    else:
                        authors = [{"name": entry["author"].get("name", "")}]
                else:
                    authors = []
                
                # 提取发布日期
                published = None
                if "published" in entry:
                    try:
                        published = datetime.strptime(entry["published"], "%Y-%m-%dT%H:%M:%SZ")
                    except (ValueError, TypeError):
                        pass
                
                # 提取PDF链接
                pdf_url = None
                if "link" in entry:
                    links = entry["link"] if isinstance(entry["link"], list) else [entry["link"]]
                    for link in links:
                        if isinstance(link, dict) and link.get("@title") == "pdf":
                            pdf_url = link.get("@href")
                            break
                
                # 创建结果对象
                result = ExternalSearchResult(
                    title=entry.get("title", "").replace("\n", " ").strip(),
                    authors=authors,
                    abstract=entry.get("summary", "").replace("\n", " ").strip() if "summary" in entry else None,
                    publication_date=published,
                    venue="arXiv",
                    url=entry.get("id"),
                    pdf_url=pdf_url,
                    arxiv_id=entry.get("id", "").split("/")[-1] if "id" in entry else None,
                    source=SearchSourceEnum.ARXIV
                )
                
                results.append(result)
            
            # 如果找到结果，则返回
            if results:
                print(f"arXiv搜索成功找到 {len(results)} 条结果")
                return results
            
            print("未找到结果，尝试放宽搜索条件")
            
            # 简化查询
            words = search_query.split()
            if len(words) > 1:
                # 搜索词太长，只保留前2个词
                search_query = " ".join(words[:2])
                encoded_query = quote_plus(search_query)
                url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_query}&start={offset}&max_results={max_results}&sortBy=relevance"
                print(f"简化后的查询: {search_query}")
                print(f"新的arXiv搜索URL: {url}")
                
                # 使用安全请求方法
                response = await self._safe_request(
                    'get', 
                    url, 
                    source=SearchSourceEnum.ARXIV,
                    max_retries=1  # 简化查询只尝试一次
                )
                
                if not response:
                    return []
                
                try:
                    feed = xmltodict.parse(response.text)
                    if "feed" in feed and "entry" in feed["feed"]:
                        entries = feed["feed"]["entry"]
                        if not isinstance(entries, list):
                            entries = [entries]
                        
                        print(f"简化查询找到 {len(entries)} 条结果")
                        results = []
                        
                        for entry in entries:
                            # 提取作者
                            if "author" in entry:
                                if isinstance(entry["author"], list):
                                    authors = [{"name": author.get("name", "")} for author in entry["author"]]
                                else:
                                    authors = [{"name": entry["author"].get("name", "")}]
                            else:
                                authors = []
                            
                            # 提取发布日期
                            published = None
                            if "published" in entry:
                                try:
                                    published = datetime.strptime(entry["published"], "%Y-%m-%dT%H:%M:%SZ")
                                except (ValueError, TypeError):
                                    pass
                            
                            # 提取PDF链接
                            pdf_url = None
                            if "link" in entry:
                                links = entry["link"] if isinstance(entry["link"], list) else [entry["link"]]
                                for link in links:
                                    if isinstance(link, dict) and link.get("@title") == "pdf":
                                        pdf_url = link.get("@href")
                                        break
                            
                            # 创建结果对象
                            result = ExternalSearchResult(
                                title=entry.get("title", "").replace("\n", " ").strip(),
                                authors=authors,
                                abstract=entry.get("summary", "").replace("\n", " ").strip() if "summary" in entry else None,
                                publication_date=published,
                                venue="arXiv",
                                url=entry.get("id"),
                                pdf_url=pdf_url,
                                arxiv_id=entry.get("id", "").split("/")[-1] if "id" in entry else None,
                                source=SearchSourceEnum.ARXIV
                            )
                            
                            results.append(result)
                        
                        if results:
                            print(f"简化查询成功找到 {len(results)} 条结果")
                            return results
                except Exception as e:
                    print(f"简化查询处理错误: {e}")
            
            return []
        except Exception as e:
            print(f"arXiv搜索处理错误: {e}")
            traceback.print_exc()
            return []
    
    async def search_semantic_scholar_crawler(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> List[ExternalSearchResult]:
        """使用网页爬虫搜索Semantic Scholar论文数据库"""
        # Semantic Scholar提供API，但需要API密钥，这里我们使用其公开API
        # 构建API查询参数
        params = {
            "query": query,
            "limit": limit,
            "offset": offset,
            "fields": "title,abstract,year,venue,authors,url,externalIds"
        }
        
        # 添加年份过滤
        if year_from or year_to:
            year_filter = {}
            if year_from:
                year_filter["min"] = year_from
            if year_to:
                year_filter["max"] = year_to
            
            if year_filter:
                params["year"] = json.dumps(year_filter)
        
        # 使用公开API，无需API密钥
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        
        print(f"Semantic Scholar API请求URL: {url}")
        # 添加用户代理和Accept头
        headers = {
            "Accept": "application/json"
        }
        
        # 使用安全请求方法
        response = await self._safe_request(
            'get', 
            url, 
            params=params, 
            headers=headers,
            source=SearchSourceEnum.SEMANTICSCHOLAR
        )
        
        if not response:
            print("Semantic Scholar API请求失败，回退到网页爬虫")
            return await self._search_semantic_scholar_web_fallback(query, limit, offset, year_from, year_to)
        
        try:
            data = response.json()
            
            if "data" not in data:
                print("Semantic Scholar: 响应中没有data字段")
                return await self._search_semantic_scholar_web_fallback(query, limit, offset, year_from, year_to)
            
            papers = data["data"]
            results = []
            
            for paper in papers:
                # 提取作者
                authors = []
                if "authors" in paper:
                    authors = [{"name": author.get("name", "")} for author in paper["authors"]]
                
                # 提取年份并转换为日期对象
                year = None
                if "year" in paper and paper["year"]:
                    try:
                        year = datetime(int(paper["year"]), 1, 1)
                    except (ValueError, TypeError):
                        pass
                
                # 提取外部ID
                external_ids = paper.get("externalIds", {})
                
                # 创建结果对象
                result = ExternalSearchResult(
                    title=paper.get("title", ""),
                    authors=authors,
                    abstract=paper.get("abstract", ""),
                    publication_date=year,
                    venue=paper.get("venue"),
                    url=paper.get("url"),
                    pdf_url=None,  # API不直接提供PDF链接
                    doi=external_ids.get("DOI"),
                    arxiv_id=external_ids.get("ARXIV"),
                    source=SearchSourceEnum.SEMANTICSCHOLAR
                )
                
                results.append(result)
            
            print(f"Semantic Scholar API: 找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            print(f"Semantic Scholar API错误: {e}")
            traceback.print_exc()
            
            # 如果API失败，回退到使用网页爬虫
            print("尝试使用网页爬虫作为备选方案...")
            return await self._search_semantic_scholar_web_fallback(query, limit, offset, year_from, year_to)
    
    async def _search_semantic_scholar_web_fallback(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> List[ExternalSearchResult]:
        """使用网页爬虫作为备选方案搜索Semantic Scholar"""
        # 构建爬虫URL
        encoded_query = quote_plus(query)
        
        # 确保搜索与推荐系统相关
        if "recommend" not in encoded_query.lower() and "推荐" not in encoded_query.lower():
            encoded_query = f"{encoded_query}+recommendation+system"
        
        # 构建年份过滤器
        year_filter = ""
        if year_from or year_to:
            if year_from and year_to:
                year_filter = f"&year={year_from}-{year_to}"
            elif year_from:
                year_filter = f"&year={year_from}-"
            elif year_to:
                year_filter = f"&year=-{year_to}"
        
        # 计算页码 (Semantic Scholar 使用基于1的分页)
        page = offset // limit + 1
        
        # 构建URL
        url = f"https://www.semanticscholar.org/search?q={encoded_query}{year_filter}&page={page}"
        
        print(f"Semantic Scholar网页爬虫请求URL: {url}")
        
        # 使用安全请求方法
        response = await self._safe_request(
            'get', 
            url, 
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            },
            source=SearchSourceEnum.SEMANTICSCHOLAR
        )
        
        if not response:
            print("Semantic Scholar网页爬虫请求失败")
            return []
        
        try:
            # 解析HTML响应
            html = etree.HTML(response.text)
            
            # 尝试不同的选择器，应对网站结构变化
            selectors = [
                '//div[contains(@class, "serp-papers")]//article',  # 最新结构
                '//div[contains(@class, "cl-paper-row")]',  # 备选结构
                '//div[contains(@class, "search-result")]',  # 备选结构
                '//div[contains(@class, "result-page")]//article'  # 备选结构
            ]
            
            paper_elements = []
            for selector in selectors:
                paper_elements = html.xpath(selector)
                if paper_elements:
                    print(f"找到匹配的选择器: {selector}")
                    break
            
            if not paper_elements:
                print("Semantic Scholar网页爬虫：未找到论文元素")
                return []
            
            results = []
            
            for element in paper_elements:
                try:
                    # 尝试不同的标题选择器
                    title = ""
                    for title_selector in ['.//a[contains(@data-selenium-selector, "title-link")]/text()', 
                                          './/a[contains(@class, "paper-title")]/text()',
                                          './/h2//text()']:
                        title_elems = element.xpath(title_selector)
                        if title_elems:
                            title = " ".join([t.strip() for t in title_elems if t.strip()])
                            break
                    
                    if not title:
                        continue
                    
                    # 尝试不同的URL选择器
                    url = None
                    for url_selector in ['.//a[contains(@data-selenium-selector, "title-link")]/@href',
                                        './/a[contains(@class, "paper-title")]/@href',
                                        './/h2/a/@href']:
                        url_elems = element.xpath(url_selector)
                        if url_elems:
                            url_path = url_elems[0]
                            url = f"https://www.semanticscholar.org{url_path}" if url_path.startswith('/') else url_path
                            break
                    
                    # 尝试提取作者信息
                    authors = []
                    for authors_selector in ['.//span[contains(@class, "author-list")]//span/text()',
                                            './/span[contains(@class, "author-list")]//a/text()',
                                            './/a[contains(@data-selenium-selector, "author-link")]/text()']:
                        author_elems = element.xpath(authors_selector)
                        if author_elems:
                            authors = [{"name": author.strip()} for author in author_elems if author.strip()]
                            break
                    
                    # 尝试提取摘要
                    abstract = ""
                    for abstract_selector in ['.//span[contains(@data-selenium-selector, "description-truncated")]/text()',
                                            './/div[contains(@class, "abstract")]/text()',
                                            './/p[contains(@class, "abstract")]/text()']:
                        abstract_elems = element.xpath(abstract_selector)
                        if abstract_elems:
                            abstract = " ".join([a.strip() for a in abstract_elems if a.strip()])
                            break
                    
                    # 尝试提取年份
                    year = None
                    for year_selector in ['.//span[contains(@class, "year")]/text()',
                                        './/span[contains(@data-selenium-selector, "venue-metadata")]/text()']:
                        year_elems = element.xpath(year_selector)
                        if year_elems:
                            year_text = " ".join([y.strip() for y in year_elems if y.strip()])
                            year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
                            if year_match:
                                try:
                                    year = datetime(int(year_match.group(0)), 1, 1)
                                except ValueError:
                                    pass
                                break
                    
                    # 尝试提取会议/期刊
                    venue = None
                    for venue_selector in ['.//span[contains(@class, "venue")]/text()',
                                        './/span[contains(@data-selenium-selector, "venue-name")]/text()']:
                        venue_elems = element.xpath(venue_selector)
                        if venue_elems:
                            venue = " ".join([v.strip() for v in venue_elems if v.strip()])
                            break
                    
                    # 创建结果对象
                    result = ExternalSearchResult(
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        publication_date=year,
                        venue=venue,
                        url=url,
                        pdf_url=None,  # 网页爬虫不提供PDF链接
                        source=SearchSourceEnum.SEMANTICSCHOLAR
                    )
                    
                    results.append(result)
                except Exception as e:
                    print(f"处理论文元素时出错: {e}")
                    continue
            
            print(f"Semantic Scholar网页爬虫: 找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            print(f"Semantic Scholar网页爬虫错误: {e}")
            traceback.print_exc()
            return []
    
    async def search_core_crawler(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> List[ExternalSearchResult]:
        """搜索CORE论文数据库"""
        # 构建CORE API查询
        api_endpoint = "https://api.core.ac.uk/v3/search/works"
        
        # 确保搜索与推荐系统相关
        if "recommend" not in query.lower() and "推荐" not in query.lower():
            query = f"{query} recommendation system"
        
        payload = {
            "q": query,
            "offset": offset,
            "limit": min(limit, 50),  # CORE API限制每页返回的结果数
            "entity": "works"
        }
        
        # 添加年份过滤
        if year_from or year_to:
            filters = []
            if year_from:
                filters.append({"year": {"gte": year_from}})
            if year_to:
                filters.append({"year": {"lte": year_to}})
            
            if filters:
                payload["filters"] = filters
        
        try:
            print(f"CORE API请求URL: {api_endpoint}，请求体: {json.dumps(payload)}")
            response = await self.client.post(
                api_endpoint, 
                json=payload,
                headers={**self.headers, "Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            
            if "results" not in data:
                print("CORE API：响应中没有results字段")
                return []
            
            results = []
            
            for paper in data["results"]:
                # 提取作者
                authors = []
                if "authors" in paper and paper["authors"]:
                    for author in paper["authors"]:
                        if isinstance(author, str):
                            authors.append({"name": author})
                        elif isinstance(author, dict) and "name" in author:
                            authors.append({"name": author["name"]})
                
                # 提取年份并转换为日期对象
                year = None
                if "year" in paper and paper["year"]:
                    try:
                        year = datetime(int(paper["year"]), 1, 1)
                    except (ValueError, TypeError):
                        pass
                
                # 提取PDF链接
                pdf_url = None
                if "downloadUrl" in paper:
                    pdf_url = paper["downloadUrl"]
                
                # 创建结果对象
                result = ExternalSearchResult(
                    title=paper.get("title", ""),
                    authors=authors,
                    abstract=paper.get("abstract", ""),
                    publication_date=year,
                    venue=paper.get("publisher", ""),
                    url=paper.get("sourceFulltextUrls", [None])[0] if "sourceFulltextUrls" in paper and paper["sourceFulltextUrls"] else None,
                    pdf_url=pdf_url,
                    doi=paper.get("doi"),
                    source=SearchSourceEnum.CORE
                )
                
                results.append(result)
            
            print(f"CORE API：找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            import traceback
            print(f"CORE API错误: {e}")
            print(traceback.format_exc())
            
            # 如果API调用失败，尝试使用网页爬虫
            print("尝试使用CORE网页爬虫作为备选方案...")
            return await self._search_core_web_fallback(query, limit, offset, year_from, year_to)
     
    async def _search_core_web_fallback(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> List[ExternalSearchResult]:
        """使用网页爬虫作为备选方案搜索CORE论文数据库"""
        # 构建CORE网页搜索URL
        encoded_query = quote_plus(query)
        
        # 确保搜索与推荐系统相关
        if "recommend" not in encoded_query.lower() and "推荐" not in encoded_query.lower():
            encoded_query = f"{encoded_query}+recommendation+system"
        
        # CORE网页搜索
        page = offset // limit + 1
        url = f"https://core.ac.uk/search?q={encoded_query}&page={page}"
        
        try:
            print(f"CORE网页爬虫请求URL: {url}")
            response = await self.client.get(url, headers=self.headers)
            response.raise_for_status()
            
            # 解析HTML响应
            html = etree.HTML(response.text)
            
            # 尝试不同的选择器以适应网站结构变化
            selectors = [
                '//article[contains(@class, "search-result")]',     # 最新网站结构
                '//div[contains(@class, "search-result-item")]',    # 备选结构
                '//div[contains(@class, "result-item")]'            # 备选结构
            ]
            
            result_elements = []
            for selector in selectors:
                result_elements = html.xpath(selector)
                if result_elements:
                    print(f"找到匹配的选择器: {selector}")
                    break
            
            if not result_elements:
                print("CORE网页爬虫：未找到结果元素")
                # 保存页面的一部分以便调试
                print(f"HTML前100个字符: {response.text[:100]}...")
                return []
            
            results = []
            
            for element in result_elements:
                # 尝试提取标题 - 适应不同的HTML结构
                title = ""
                for title_selector in ['.//h3/a/text()', './/h2/a/text()', './/div[contains(@class, "title")]/a/text()']:
                    title_elems = element.xpath(title_selector)
                    if title_elems:
                        title = " ".join([t.strip() for t in title_elems if t.strip()])
                        break
                
                if not title:
                    continue
                
                # 尝试提取URL
                url = None
                for url_selector in ['.//h3/a/@href', './/h2/a/@href', './/div[contains(@class, "title")]/a/@href']:
                    url_elems = element.xpath(url_selector)
                    if url_elems:
                        url_path = url_elems[0]
                        url = f"https://core.ac.uk{url_path}" if url_path.startswith('/') else url_path
                        break
                
                # 尝试提取作者信息
                authors = []
                for authors_selector in ['.//span[contains(@class, "authors")]/text()', 
                                        './/div[contains(@class, "authors")]/text()']:
                    authors_elems = element.xpath(authors_selector)
                    if authors_elems:
                        authors_text = " ".join([a.strip() for a in authors_elems if a.strip()])
                        # 分割作者名称
                        author_names = re.split(r',\s*|\s+and\s+', authors_text)
                        authors = [{"name": name.strip()} for name in author_names if name.strip()]
                        break
                
                # 尝试提取摘要
                abstract = ""
                for abstract_selector in ['.//div[contains(@class, "abstract")]/text()', 
                                         './/p[contains(@class, "abstract")]/text()']:
                    abstract_elems = element.xpath(abstract_selector)
                    if abstract_elems:
                        abstract = " ".join([a.strip() for a in abstract_elems if a.strip()])
                        break
                
                # 尝试提取元数据（年份、会议等）
                year = None
                venue = None
                for metadata_selector in ['.//div[contains(@class, "metadata")]//text()',
                                         './/div[contains(@class, "meta")]//text()']:
                    metadata_elems = element.xpath(metadata_selector)
                    if metadata_elems:
                        metadata_text = " ".join([m.strip() for m in metadata_elems if m.strip()])
                        
                        # 尝试提取年份
                        year_match = re.search(r'(\d{4})', metadata_text)
                        if year_match:
                            try:
                                year_value = int(year_match.group(1))
                                # 过滤年份
                                if (not year_from or year_value >= year_from) and (not year_to or year_value <= year_to):
                                    year = datetime(year_value, 1, 1)
                                else:
                                    print(f"年份 {year_value} 不在范围 {year_from}-{year_to} 内，跳过")
                                    continue
                            except (ValueError, TypeError):
                                pass
                        
                        # 尝试提取会议/期刊
                        venue_match = re.search(r'Published in:\s+([^|]+)', metadata_text)
                        if venue_match:
                            venue = venue_match.group(1).strip()
                        
                        break
                
                # 尝试提取PDF链接
                pdf_url = None
                for pdf_selector in ['.//a[contains(@class, "pdf")]/@href',
                                    './/a[contains(text(), "PDF")]/@href']:
                    pdf_elems = element.xpath(pdf_selector)
                    if pdf_elems:
                        pdf_url = pdf_elems[0]
                        break
                
                # 创建结果对象
                result = ExternalSearchResult(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    publication_date=year,
                    venue=venue,
                    url=url,
                    pdf_url=pdf_url,
                    source=SearchSourceEnum.CORE
                )
                
                results.append(result)
                
                # 如果已达到指定限制，则停止
                if len(results) >= limit:
                    break
            
            print(f"CORE网页爬虫：找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            import traceback
            print(f"CORE网页爬虫错误: {e}")
            print(traceback.format_exc())
            return []

    async def search_openalex_crawler(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> List[ExternalSearchResult]:
        """使用OpenAlex API搜索论文数据库"""
        # OpenAlex提供免费API，无需API密钥
        encoded_query = quote_plus(query)
        
        # 确保搜索与推荐系统相关
        if "recommend" not in encoded_query.lower() and "推荐" not in encoded_query.lower():
            encoded_query = f"{encoded_query} recommendation"
        
        # 构建过滤器
        filters = []
        if year_from:
            filters.append(f"publication_year:>={year_from}")
        if year_to:
            filters.append(f"publication_year:<={year_to}")
        
        filter_param = ""
        if filters:
            filter_param = f"&filter={','.join(filters)}"
        
        # 构建URL - 使用OpenAlex的works端点
        page = offset // limit + 1
        url = f"https://api.openalex.org/works?search={encoded_query}{filter_param}&page={page}&per-page={limit}"
        
        # 添加polite pool参数
        if hasattr(self, 'email') and self.email:
            url = f"{url}&mailto={self.email}"
        
        try:
            print(f"OpenAlex API请求URL: {url}")
            response = await self.client.get(
                url, 
                headers={**self.headers, "Accept": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            
            if "results" not in data:
                print("OpenAlex API：响应中没有results字段")
                return []
            
            results = []
            
            for paper in data["results"]:
                # 提取作者
                authors = []
                if "authorships" in paper:
                    for authorship in paper["authorships"]:
                        if "author" in authorship and "display_name" in authorship["author"]:
                            authors.append({"name": authorship["author"]["display_name"]})
                
                # 提取发布日期
                pub_date = None
                if "publication_date" in paper:
                    try:
                        pub_date = datetime.fromisoformat(paper["publication_date"])
                    except (ValueError, TypeError):
                        pass
                
                # 提取DOI
                doi = None
                if "doi" in paper:
                    doi = paper["doi"]
                
                # 提取摘要
                abstract = ""
                if "abstract_inverted_index" in paper:
                    # OpenAlex存储摘要为倒排索引格式，需要重构
                    try:
                        inverted_index = paper["abstract_inverted_index"]
                        if inverted_index:
                            # 重构摘要文本
                            max_position = max([position for positions in inverted_index.values() for position in positions])
                            words = [""] * (max_position + 1)
                            for word, positions in inverted_index.items():
                                for position in positions:
                                    words[position] = word
                            abstract = " ".join(words)
                    except Exception as e:
                        print(f"重构摘要时出错: {e}")
                
                # 创建结果对象
                result = ExternalSearchResult(
                    title=paper.get("title", ""),
                    authors=authors,
                    abstract=abstract,
                    publication_date=pub_date,
                    venue=paper.get("host_venue", {}).get("display_name", ""),
                    url=paper.get("primary_location", {}).get("landing_page_url", ""),
                    pdf_url=paper.get("primary_location", {}).get("pdf_url", ""),
                    doi=doi,
                    source=SearchSourceEnum.OPENALEX
                )
                
                results.append(result)
            
            print(f"OpenAlex API：找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            import traceback
            print(f"OpenAlex API错误: {e}")
            print(traceback.format_exc())
            return []

paper_search_service = PaperSearchService() 