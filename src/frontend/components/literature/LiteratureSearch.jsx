import React, { useState, useEffect, useCallback } from 'react';
import { 
  Input, 
  Button, 
  Select, 
  Card, 
  List, 
  Tag, 
  Typography, 
  Drawer, 
  Space, 
  Divider, 
  Spin, 
  Alert,
  Empty,
  Tooltip,
  Checkbox,
  Radio,
  DatePicker,
  message,
  Row,
  Col,
  Progress,
  Collapse,
  Badge,
  notification
} from 'antd';
import { 
  SearchOutlined, 
  FilterOutlined, 
  DownloadOutlined, 
  FileTextOutlined, 
  StarOutlined,
  StarFilled,
  SortAscendingOutlined,
  DatabaseOutlined,
  ClockCircleOutlined,
  BookOutlined,
  LinkOutlined,
  ImportOutlined
} from '@ant-design/icons';
import { API_BASE_URL } from '../../config';
import moment from 'moment';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;
const { Option } = Select;
const { RangePicker } = DatePicker;
const { Panel } = Collapse;

// 推荐系统相关的免费论文数据库源
const DATA_SOURCES = [
  { value: 'arxiv', label: 'arXiv', description: '计算机科学预印本平台' },
  { value: 'semanticscholar', label: 'Semantic Scholar', description: '语义学术搜索引擎' },
  { value: 'core', label: 'CORE', description: '全球开放获取研究论文集合' },
  { value: 'citeseerx', label: 'CiteSeerX', description: '计算机与信息科学开放库' },
  { value: 'openalex', label: 'OpenAlex', description: '开放获取学术图谱' },
  { value: 'local', label: '本地文献库', description: '已上传至系统的论文' },
];

// 推荐系统领域的主要研究方向
const RESEARCH_DOMAINS = [
  { value: 'sequential', label: '序列推荐', description: '基于用户历史行为序列的推荐技术' },
  { value: 'graph', label: '图神经网络推荐', description: '基于GNN的推荐系统方法' },
  { value: 'multi_modal', label: '多模态推荐', description: '结合图文音视频等多模态信息的推荐' },
  { value: 'knowledge', label: '知识增强推荐', description: '融合知识图谱的推荐技术' },
  { value: 'contrastive', label: '对比学习推荐', description: '应用对比学习的推荐方法' },
  { value: 'llm', label: '大模型推荐', description: '基于大语言模型的推荐系统' },
  { value: 'explainable', label: '可解释推荐', description: '可解释性推荐算法研究' },
  { value: 'fairness', label: '公平推荐', description: '推荐系统公平性研究' },
  { value: 'cold_start', label: '冷启动推荐', description: '解决冷启动问题的推荐技术' },
  { value: 'federated', label: '联邦推荐', description: '联邦学习推荐系统' },
  { value: 'reinforcement', label: '强化学习推荐', description: '基于强化学习的推荐技术' },
  { value: 'self_supervised', label: '自监督推荐', description: '自监督学习在推荐中的应用' },
];

// 会议与期刊列表
const CONFERENCES_JOURNALS = [
  { value: 'sigir', label: 'SIGIR', description: '信息检索领域顶级会议' },
  { value: 'www', label: 'WWW', description: '万维网技术顶级会议' },
  { value: 'kdd', label: 'KDD', description: '数据挖掘顶级会议' },
  { value: 'recsys', label: 'RecSys', description: '推荐系统专业会议' },
  { value: 'cikm', label: 'CIKM', description: '信息与知识管理会议' },
  { value: 'wsdm', label: 'WSDM', description: '网络搜索与数据挖掘会议' },
  { value: 'icdm', label: 'ICDM', description: '数据挖掘国际会议' },
  { value: 'ijcai', label: 'IJCAI', description: '人工智能顶级会议' },
  { value: 'aaai', label: 'AAAI', description: '人工智能顶级会议' },
  { value: 'neurips', label: 'NeurIPS', description: '神经信息处理系统会议' },
  { value: 'icml', label: 'ICML', description: '机器学习国际会议' },
  { value: 'iclr', label: 'ICLR', description: '表示学习国际会议' },
  { value: 'tkde', label: 'TKDE', description: '知识与数据工程汇刊' },
  { value: 'tois', label: 'TOIS', description: '信息系统汇刊' },
  { value: 'tist', label: 'TIST', description: '智能科学与技术汇刊' },
];

// 更新替换fetchPapers函数，提高容错性
const fetchPapers = async (params) => {
  console.log('Searching with params:', params);
  
  try {
    // 构建API请求体
    const apiParams = {
      query: params.query || "",
      sources: params.sources.map(source => source.toLowerCase()),
      limit: 100, // 修改为一次获取较大数量，避免分页问题
      offset: 0, // 始终从0开始，获取所有结果
      year_from: params.yearRange?.[0] || null,
      year_to: params.yearRange?.[1] || null,
      full_text: params.searchMode === 'full_text',
      domain: params.domains?.length > 0 ? params.domains.join(' OR ') : null,
      venues: params.venues?.length > 0 ? params.venues : null
    };
    
    console.log('Sending API request:', apiParams);
    
    // 设置超时控制
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30秒超时
    
    const response = await fetch(`${API_BASE_URL}/papers/search/external`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(apiParams),
      signal: controller.signal
    });
    
    clearTimeout(timeoutId); // 清除超时
    
    if (!response.ok) {
      let errorMessage = `搜索失败: ${response.status} ${response.statusText}`;
      try {
        const errorText = await response.text();
        console.error('Search API error:', response.status, errorText);
        errorMessage = `搜索失败: ${response.statusText} (${errorText})`;
      } catch (textError) {
        console.error('Failed to get error text:', textError);
      }
      throw new Error(errorMessage);
    }
    
    const data = await response.json();
    console.log('Search results:', data);
    
    // 格式化返回结果
    return {
      total: data.total || 0,
      items: Array.isArray(data.results) ? data.results.map(item => ({
        id: item.arxiv_id || item.doi || `paper-${Math.random().toString(36).substr(2, 9)}`,
        title: item.title || "无标题",
        authors: item.authors?.map(author => author.name) || [],
        venue: item.venue || '',
        year: item.publication_date ? new Date(item.publication_date).getFullYear() : null,
        abstract: item.abstract || "无摘要",
        keywords: item.keywords || [],
        url: item.url || '',
        pdf_url: item.pdf_url || '',
        doi: item.doi || '',
        arxiv_id: item.arxiv_id || '',
        isStarred: false,
        source: item.source || '',
      })) : []
    };
  } catch (error) {
    console.error('External paper search error:', error);
    if (error.name === 'AbortError') {
      throw new Error('搜索请求超时，请稍后再试');
    }
    throw error; // 保留原始错误，让上层组件处理
  }
};

const LiteratureSearch = () => {
  // 状态管理
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [totalResults, setTotalResults] = useState(0);
  const [selectedPaper, setSelectedPaper] = useState(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [filterDrawerVisible, setFilterDrawerVisible] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [searchError, setSearchError] = useState(null);
  
  // 添加新的状态
  const [sourceStatus, setSourceStatus] = useState({
    arxiv: { status: 'unknown', message: '未知状态' },
    semanticscholar: { status: 'unknown', message: '未知状态' },
    core: { status: 'unknown', message: '未知状态' },
    openalex: { status: 'unknown', message: '未知状态' }
  });
  const [searchProgress, setSearchProgress] = useState(0);
  const [lastSuccessfulSearch, setLastSuccessfulSearch] = useState(null);
  const [searchAttempts, setSearchAttempts] = useState(0);
  
  // 过滤器状态
  const [selectedSources, setSelectedSources] = useState(['arxiv', 'semanticscholar', 'core', 'openalex']);
  const [selectedDomains, setSelectedDomains] = useState([]);
  const [selectedVenues, setSelectedVenues] = useState([]);
  const [yearRange, setYearRange] = useState([null, null]);
  const [searchMode, setSearchMode] = useState('semantic');
  
  // 存储搜索结果缓存，用于分页时不重新搜索
  const [cachedResults, setCachedResults] = useState([]);
  
  // 导入论文状态
  const [importingPaperId, setImportingPaperId] = useState(null);
  
  // 检查数据源健康状态
  const checkSourceHealth = useCallback(async () => {
    try {
      const testSearches = [
        { source: 'arxiv', query: 'recommender systems' },
        { source: 'semanticscholar', query: 'recommendation' },
        { source: 'core', query: 'collaborative filtering' },
        { source: 'openalex', query: 'recommendation algorithms' }
      ];
      
      // 逐个检查每个源
      for (const test of testSearches) {
        setSourceStatus(prev => ({
          ...prev,
          [test.source]: { status: 'checking', message: '检查中...' }
        }));
        
        try {
          const params = {
            query: test.query,
            sources: [test.source],
            limit: 3,
            offset: 0,
            searchMode: 'semantic'
          };
          
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 10000); // 10秒超时
          
          const response = await fetch(`${API_BASE_URL}/papers/search/external`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params),
            signal: controller.signal
          });
          
          clearTimeout(timeoutId);
          
          if (response.ok) {
            const data = await response.json();
            if (data.results && data.results.length > 0) {
              setSourceStatus(prev => ({
                ...prev,
                [test.source]: { status: 'healthy', message: '可用' }
              }));
            } else {
              setSourceStatus(prev => ({
                ...prev,
                [test.source]: { status: 'warning', message: '无结果' }
              }));
            }
          } else {
            setSourceStatus(prev => ({
              ...prev,
              [test.source]: { status: 'error', message: '请求失败' }
            }));
          }
        } catch (error) {
          setSourceStatus(prev => ({
            ...prev,
            [test.source]: { 
              status: 'error', 
              message: error.name === 'AbortError' ? '超时' : '错误' 
            }
          }));
        }
        
        // 间隔一段时间再检查下一个源，避免请求过于密集
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    } catch (error) {
      console.error('Health check error:', error);
    }
  }, []);
  
  // 在组件挂载后检查源的健康状态
  useEffect(() => {
    checkSourceHealth();
  }, [checkSourceHealth]);
  
  // 执行搜索，增强错误处理和重试机制
  const handleSearch = async (query = searchQuery) => {
    // 检查搜索关键词是否为空
    if (!query.trim() && selectedDomains.length === 0) {
      message.warning('请输入搜索关键词或选择研究方向');
      return;
    }
    
    setIsSearching(true);
    setSearchError(null);
    setSearchProgress(10); // 开始进度
    
    // 记录搜索尝试次数
    const currentAttempt = searchAttempts + 1;
    setSearchAttempts(currentAttempt);
    
    // 自动增加进度的效果
    const progressInterval = setInterval(() => {
      setSearchProgress(prev => {
        if (prev >= 90) return prev;
        return prev + 5;
      });
    }, 1000);
    
    try {
      // 根据源的健康状态选择搜索源
      let sourcesToUse = [...selectedSources];
      
      // 如果所有选择的源都不健康，添加arXiv作为备选
      const allSelectedUnhealthy = sourcesToUse.every(
        source => sourceStatus[source]?.status === 'error'
      );
      
      if (allSelectedUnhealthy && !sourcesToUse.includes('arxiv')) {
        notification.warning({
          message: '数据源状态警告',
          description: '所选数据源可能不可用，已自动添加arXiv作为备选源',
          duration: 5
        });
        sourcesToUse.push('arxiv');
      }
      
      const params = {
        query,
        pageSize: 100, // 请求较大数量，避免分页问题
        sources: sourcesToUse,
        domains: selectedDomains,
        venues: selectedVenues,
        yearRange,
        searchMode
      };
      
      console.log('发送搜索请求参数:', JSON.stringify(params));
      message.info('正在搜索中，请稍候...');
      
      const result = await fetchPapers(params);
      console.log('搜索结果:', JSON.stringify(result));
      
      clearInterval(progressInterval);
      setSearchProgress(100);
      
      if (result.items.length === 0) {
        // 如果没有结果，显示更详细的提示
        message.warning('未找到匹配结果，可能的原因：1. 关键词过于专业 2. 筛选条件过于严格 3. 网络连接问题');
        
        // 如果这是第一次尝试，且使用了多个源，可能是某些源出问题，尝试只用arXiv
        if (currentAttempt === 1 && sourcesToUse.length > 1 && !sourcesToUse.includes('arxiv')) {
          setTimeout(() => {
            message.info('正在尝试使用arXiv重新搜索...');
            setSelectedSources(['arxiv']);
            handleSearch(query);
          }, 1500);
          return;
        }
      } else {
        message.success(`找到 ${result.items.length} 条相关结果`);
        // 保存最后一次成功的搜索
        setLastSuccessfulSearch({
          query,
          time: new Date().toISOString(),
          resultCount: result.items.length
        });
      }
      
      // 存储所有结果到缓存
      setCachedResults(result.items);
      
      // 设置当前页为第1页
      setPage(1);
      
      // 计算当前页应显示的结果
      const currentPageResults = result.items.slice(0, pageSize);
      setSearchResults(currentPageResults);
      setTotalResults(result.items.length); // 使用实际获取到的数量
    } catch (error) {
      clearInterval(progressInterval);
      setSearchProgress(0);
      
      console.error('搜索错误:', error);
      const errorMessage = error.message || '未知错误';
      setSearchError(`搜索失败: ${errorMessage}`);
      
      // 提供更友好的错误信息
      if (errorMessage.includes('timeout') || errorMessage.includes('超时')) {
        message.error('搜索超时，数据库服务器可能繁忙，请稍后再试');
      } else if (errorMessage.includes('500')) {
        message.error('服务器内部错误，请稍后重试');
      } else if (errorMessage.includes('404')) {
        message.error('搜索服务不可用，请联系管理员');
      } else {
        message.error(`搜索失败: ${errorMessage}`);
      }
      
      // 尝试回退到使用缓存的结果
      if (cachedResults.length > 0 && currentAttempt > 1) {
        message.info('显示上次搜索的结果');
        setSearchResults(cachedResults.slice(0, pageSize));
        setTotalResults(cachedResults.length);
      } else {
        setSearchResults([]);
        setTotalResults(0);
        setCachedResults([]);
      }
      
      // 检查数据源健康状态
      checkSourceHealth();
    } finally {
      setIsSearching(false);
    }
  };
  
  // 渲染数据源状态指示器
  const renderSourceStatus = () => (
    <div className="source-status">
      <Collapse ghost>
        <Panel header={
          <Space>
            <span>数据源状态</span>
            {Object.values(sourceStatus).some(s => s.status === 'error') && 
              <Badge status="error" />
            }
            {Object.values(sourceStatus).every(s => s.status === 'healthy') && 
              <Badge status="success" />
            }
          </Space>
        } key="1">
          <div className="status-grid">
            {Object.entries(sourceStatus).map(([source, status]) => (
              <div key={source} className="status-item">
                <span>{DATA_SOURCES.find(s => s.value === source)?.label || source}</span>
                <Badge 
                  status={
                    status.status === 'healthy' ? 'success' : 
                    status.status === 'warning' ? 'warning' : 
                    status.status === 'error' ? 'error' : 'default'
                  } 
                  text={status.message} 
                />
              </div>
            ))}
            <Button 
              type="link" 
              size="small" 
              onClick={(e) => {
                e.stopPropagation();
                checkSourceHealth();
              }}
            >
              刷新状态
            </Button>
          </div>
        </Panel>
      </Collapse>
    </div>
  );
  
  // 分页变化处理 - 不再触发新的搜索，而是使用缓存结果
  const handlePageChange = (newPage, newPageSize) => {
    console.log(`分页切换到：第${newPage}页，每页${newPageSize}条`);
    
    setPage(newPage);
    
    // 如果页大小改变，重新计算
    if (newPageSize !== pageSize) {
      setPageSize(newPageSize);
    }
    
    // 从缓存中获取当前页的数据
    const startIndex = (newPage - 1) * (newPageSize || pageSize);
    const endIndex = startIndex + (newPageSize || pageSize);
    console.log(`加载索引范围：${startIndex} 到 ${endIndex}，缓存总条数：${cachedResults.length}`);
    
    const currentPageResults = cachedResults.slice(startIndex, endIndex);
    console.log(`当前页实际加载了${currentPageResults.length}条结果`);
    
    // 更新显示结果
    setSearchResults(currentPageResults);
  };
  
  // 选择论文处理
  const handleSelectPaper = (paper) => {
    setSelectedPaper(paper);
    setDrawerVisible(true);
  };
  
  // 收藏论文处理
  const handleToggleStarPaper = async (paperId) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录后再收藏论文');
        return;
      }

      // 获取当前论文
      const paper = cachedResults.find(p => p.id === paperId);
      if (!paper) {
        console.error('未找到要操作的论文:', paperId);
        return;
      }
      
      // 检查论文是否已导入系统
      if (!paper.isImported) {
        message.warning('请先添加论文到文献库，然后再收藏');
        // 自动触发添加操作
        await handleAddPaper(paper);
        return;
      }

      // 确定当前收藏状态
      const isFavorite = paper.isStarred || false;
      
      // 显示加载提示
      const hide = message.loading('正在更新收藏状态...', 0.5);

      // 先在UI上更新收藏状态以提高响应速度
      setSearchResults(prevResults => 
        prevResults.map(p => 
          p.id === paperId 
            ? { ...p, isStarred: !isFavorite } 
            : p
        )
      );
      
      // 同时更新缓存中的结果
      setCachedResults(prevResults => 
        prevResults.map(p => 
          p.id === paperId 
            ? { ...p, isStarred: !isFavorite } 
            : p
        )
      );

      try {
        // 查询系统中的论文ID (使用标题或其他唯一标识符)
        const paperResponse = await fetch(`${API_BASE_URL}/papers/search?query=${encodeURIComponent(paper.title)}`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!paperResponse.ok) {
          throw new Error('无法找到系统中的论文');
        }
        
        const paperResult = await paperResponse.json();
        console.log('查询到系统中的论文:', paperResult);
        
        if (!paperResult.items || paperResult.items.length === 0) {
          throw new Error('未在系统中找到该论文，请先添加');
        }
        
        // 使用系统中的论文ID发送收藏请求
        const systemPaperId = paperResult.items[0].id;
        
        const favoriteResponse = await fetch(`${API_BASE_URL}/papers/${systemPaperId}/favorite`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ is_favorite: !isFavorite })
        });
        
        hide();
        
        if (!favoriteResponse.ok) {
          if (favoriteResponse.status === 401) {
            message.error('登录已过期，请重新登录');
            return;
          }
          throw new Error('设置收藏状态失败: ' + favoriteResponse.statusText);
        }
        
        // 记录收藏成功
        const updatedPaper = await favoriteResponse.json();
        console.log('收藏状态已更新', updatedPaper);
        message.success(isFavorite ? '已取消收藏' : '已添加到收藏');
      } catch (error) {
        hide();
        console.error('API更新收藏状态失败:', error);
        
        // 恢复原来的收藏状态
        setSearchResults(prevResults => 
          prevResults.map(p => 
            p.id === paperId 
              ? { ...p, isStarred: isFavorite } 
              : p
          )
        );
        
        setCachedResults(prevResults => 
          prevResults.map(p => 
            p.id === paperId 
              ? { ...p, isStarred: isFavorite } 
              : p
          )
        );
        
        message.error('更新收藏状态失败: ' + error.message);
      }
    } catch (error) {
      console.error('收藏操作失败:', error);
      message.error('操作失败，请重试');
    }
  };
  
  // 修改添加论文函数，确保参数格式与后端API一致
  const handleAddPaper = async (paper) => {
    try {
      // 检查用户认证状态
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录后再添加论文');
        return;
      }
      
      setImportingPaperId(paper.id);
      const hide = message.loading('正在添加论文...', 0);
      
      try {
        // 直接使用论文基本信息创建新论文
        const paperData = {
          title: paper.title,
          authors: paper.authors.map(name => ({ name })),
          abstract: paper.abstract,
          url: paper.url || '',
          pdf_url: paper.pdf_url || '',
          doi: paper.doi || '',
          arxiv_id: paper.arxiv_id || '',
          venue: paper.venue || '',
          publication_date: paper.year ? `${paper.year}-01-01` : null,
          keywords: paper.keywords || []
        };
        
        console.log('创建论文数据:', paperData);
        
        // 使用创建论文API
        const response = await fetch(`${API_BASE_URL}/papers/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(paperData)
        });
        
        hide();
        
        if (!response.ok) {
          // 如果创建失败，尝试备用方法
          if (paper.arxiv_id) {
            return await tryImportByMetadata(paper, token);
          }
          
          let errorDetail = '';
          try {
            const errorJson = await response.json();
            errorDetail = errorJson.detail || errorJson.message || '';
          } catch (e) {
            errorDetail = await response.text();
          }
          
          if (response.status === 409) {
            message.warning('该论文已存在于您的文献库中');
            markPaperAsImported(paper.id);
            return;
          }
          
          throw new Error(`创建论文失败: ${errorDetail || response.statusText}`);
        }
        
        // 处理成功响应
        const result = await response.json();
        console.log('添加成功，返回数据:', result);
        
        message.success('论文已成功添加到您的文献库');
        markPaperAsImported(paper.id);
      } catch (error) {
        hide();
        console.error('API添加论文失败:', error);
        
        // 尝试备用方法
        if (paper.arxiv_id) {
          return await tryImportByMetadata(paper, token);
        }
        
        message.error('添加论文失败: ' + error.message);
      }
    } catch (error) {
      console.error('添加论文过程出错:', error);
      message.error('添加论文失败: ' + error.message);
    } finally {
      setImportingPaperId(null);
    }
  };
  
  // 标记论文为已导入
  const markPaperAsImported = (paperId) => {
    setSearchResults(prevResults => 
      prevResults.map(p => 
        p.id === paperId ? { ...p, isImported: true } : p
      )
    );
    
    setCachedResults(prevResults => 
      prevResults.map(p => 
        p.id === paperId ? { ...p, isImported: true } : p
      )
    );
  };
  
  // 尝试使用元数据导入（备用方法）
  const tryImportByMetadata = async (paper, token) => {
    const hide = message.loading('尝试通过元数据导入...', 0);
    
    try {
      // 尝试使用元数据导入API
      const metadataResponse = await fetch(`${API_BASE_URL}/papers/import/metadata`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          title: paper.title,
          authors: paper.authors,
          abstract: paper.abstract,
          url: paper.url || '',
          pdf_url: paper.pdf_url || '',
          doi: paper.doi || '',
          arxiv_id: paper.arxiv_id || '',
          source: paper.source || '',
          publication_date: paper.year ? `${paper.year}-01-01` : null
        })
      });
      
      hide();
      
      if (!metadataResponse.ok) {
        let errorDetail = '';
        try {
          const errorJson = await metadataResponse.json();
          errorDetail = errorJson.detail || errorJson.message || '';
        } catch (e) {
          errorDetail = await metadataResponse.text();
        }
        
        if (metadataResponse.status === 409) {
          message.warning('该论文已存在于您的文献库中');
          markPaperAsImported(paper.id);
          return;
        }
        
        throw new Error(`通过元数据导入失败: ${errorDetail}`);
      }
      
      const result = await metadataResponse.json();
      console.log('元数据导入成功，返回数据:', result);
      
      message.success('论文已成功添加到您的文献库');
      markPaperAsImported(paper.id);
    } catch (error) {
      hide();
      console.error('元数据导入失败:', error);
      message.error('添加论文失败: ' + error.message);
    }
  };
  
  return (
    <div className="literature-search-container">
      <div className="search-header">
        <Title level={3}>推荐系统文献检索</Title>
        <Paragraph type="secondary">
          搜索全球开放获取的推荐系统学术文献，支持语义理解和精准匹配
        </Paragraph>
        
        <div className="search-bar">
          <Input.Group compact>
            <Select 
              defaultValue="semantic" 
              value={searchMode}
              onChange={setSearchMode}
              style={{ width: '15%' }}
            >
              <Option value="semantic">语义搜索</Option>
              <Option value="keyword">关键词搜索</Option>
            </Select>
            <Search
              placeholder="输入研究主题、方法、作者或关键词..."
              allowClear
              enterButton={<Button type="primary" icon={<SearchOutlined />}>搜索</Button>}
              size="large"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onSearch={() => handleSearch()}
              style={{ width: '85%' }}
            />
          </Input.Group>
          
          <Space style={{ marginTop: 12 }}>
            <Button 
              icon={<FilterOutlined />} 
              onClick={() => setFilterDrawerVisible(true)}
            >
              高级筛选
            </Button>
            <Button
              type="link"
              onClick={checkSourceHealth}
            >
              检查数据源状态
            </Button>
          </Space>
        </div>
        
        {/* 数据源状态指示器 */}
        {renderSourceStatus()}
        
        {/* 常用研究方向快捷选择 */}
        <div className="quick-domains" style={{ marginTop: 16 }}>
          <Text strong style={{ marginRight: 8 }}>热门研究方向:</Text>
          <Space wrap>
            {RESEARCH_DOMAINS.slice(0, 8).map(domain => (
              <Tag 
                key={domain.value}
                color={selectedDomains.includes(domain.value) ? '#108ee9' : 'default'}
                style={{ cursor: 'pointer' }}
                onClick={() => {
                  if (selectedDomains.includes(domain.value)) {
                    setSelectedDomains(selectedDomains.filter(d => d !== domain.value));
                  } else {
                    setSelectedDomains([...selectedDomains, domain.value]);
                  }
                }}
              >
                {domain.label}
              </Tag>
            ))}
            <Tag color="processing">更多...</Tag>
          </Space>
        </div>
      </div>
      
      {/* 搜索结果 */}
      <div className="search-results" style={{ marginTop: 24 }}>
        {searchError ? (
          <Alert 
            message="搜索错误" 
            description={searchError} 
            type="error" 
            showIcon 
            action={
              <Button size="small" onClick={() => checkSourceHealth()}>
                检查数据源状态
              </Button>
            }
          />
        ) : (
          <>
            <div className="results-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <Text>
                {isSearching ? '正在搜索...' : cachedResults.length > 0 ? `共找到 ${cachedResults.length} 篇相关论文 (当前显示第 ${(page-1)*pageSize+1}-${Math.min(page*pageSize, cachedResults.length)} 篇)` : '暂无搜索结果'}
              </Text>
              
              {/* 上次成功搜索信息 */}
              {lastSuccessfulSearch && !isSearching && (
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  上次搜索: "{lastSuccessfulSearch.query}" 找到 {lastSuccessfulSearch.resultCount} 条结果
                </Text>
              )}
            </div>
            
            {isSearching ? (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Spin size="large" />
                <div style={{ marginTop: 16 }}>正在搜索相关文献，这可能需要几秒钟...</div>
                <Progress percent={searchProgress} status="active" style={{ marginTop: 16, maxWidth: '80%', margin: '16px auto' }} />
                <div className="search-sources-info" style={{ marginTop: 8, fontSize: '12px', color: '#999' }}>
                  正在搜索以下数据库: {selectedSources.map(src => 
                    DATA_SOURCES.find(s => s.value === src)?.label || src
                  ).join(', ')}
                </div>
              </div>
            ) : searchResults.length > 0 ? (
              <List
                itemLayout="vertical"
                size="large"
                pagination={{
                  onChange: handlePageChange,
                  current: page,
                  pageSize,
                  total: cachedResults.length, // 使用缓存的实际数量而不是后端返回的总数
                  showSizeChanger: true,
                  pageSizeOptions: ['5', '10', '20', '50'],
                  showTotal: (total) => `共 ${total} 条结果`
                }}
                dataSource={searchResults}
                renderItem={item => (
                  <List.Item
                    key={item.id}
                    actions={[
                      <Space>
                        {item.venue && <Tag color="blue">{item.venue}</Tag>}
                        {item.year && <Tag color="green">{item.year}</Tag>}
                      </Space>,
                      <Space>
                        <Tag icon={<DatabaseOutlined />} color={
                          sourceStatus[item.source]?.status === 'healthy' ? 'success' :
                          sourceStatus[item.source]?.status === 'warning' ? 'warning' :
                          sourceStatus[item.source]?.status === 'error' ? 'error' : 'default'
                        }>
                          {DATA_SOURCES.find(src => src.value === item.source)?.label || item.source}
                        </Tag>
                        <Button
                          type="link"
                          size="small"
                          onClick={() => handleSelectPaper(item)}
                        >
                          查看详情
                        </Button>
                        <Tooltip title={item.isImported ? '已添加到文献库' : '添加到文献库'}>
                          <Button
                            type="primary"
                            icon={<ImportOutlined />}
                            size="small"
                            style={{ padding: '0 6px', height: '22px', fontSize: '12px', lineHeight: '18px' }}
                            loading={importingPaperId === item.id}
                            disabled={item.isImported}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleAddPaper(item);
                            }}
                          >
                            {item.isImported ? '已添加' : '添加'}
                          </Button>
                        </Tooltip>
                      </Space>
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <a onClick={() => handleSelectPaper(item)}>{item.title}</a>
                        </div>
                      }
                      description={
                        <Space wrap>
                          {item.authors.map((author, index) => (
                            <Text key={index} type="secondary">
                              {author}{index < item.authors.length - 1 ? ', ' : ''}
                            </Text>
                          ))}
                        </Space>
                      }
                    />
                    <div>
                      <Paragraph ellipsis={{ rows: 3, expandable: true, symbol: '更多' }}>
                        {item.abstract}
                      </Paragraph>
                      <div>
                        <Space wrap>
                          {item.keywords.map((keyword, index) => (
                            <Tag key={index} color="default" style={{ cursor: 'pointer' }} onClick={() => setSearchQuery(keyword)}>
                              {keyword}
                            </Tag>
                          ))}
                        </Space>
                      </div>
                    </div>
                  </List.Item>
                )}
              />
            ) : (
              <Empty 
                description={searchQuery ? "未找到匹配的论文，请尝试更改搜索条件" : "请输入搜索关键词或选择研究方向"} 
                style={{ padding: 40 }}
              />
            )}
          </>
        )}
      </div>
      
      {/* 添加CSS样式 */}
      <style jsx="true">{`
        .source-status {
          margin-top: 16px;
          border-radius: 4px;
          background-color: #f9f9f9;
        }
        
        .status-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 8px;
        }
        
        .status-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 4px;
        }
        
        .search-sources-info {
          max-width: 80%;
          margin: 0 auto;
          text-align: center;
        }
      `}</style>
      
      {/* 论文详情抽屉 */}
      <Drawer
        title={selectedPaper?.title || '论文详情'}
        placement="right"
        width={720}
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
      >
        {selectedPaper && (
          <div className="paper-detail">
            <div className="paper-meta">
              <Space wrap>
                {selectedPaper.venue && <Tag color="blue">{selectedPaper.venue}</Tag>}
                {selectedPaper.year && <Tag color="green">{selectedPaper.year}</Tag>}
                <Tag icon={<DatabaseOutlined />}>
                  {DATA_SOURCES.find(src => src.value === selectedPaper.source)?.label || selectedPaper.source}
                </Tag>
              </Space>
              
              <div style={{ margin: '16px 0' }}>
                <Text strong>作者:</Text>
                <Paragraph>
                  {selectedPaper.authors.join(', ')}
                </Paragraph>
              </div>
              
              <Divider orientation="left">摘要</Divider>
              <Paragraph>
                {selectedPaper.abstract}
              </Paragraph>
              
              <Divider orientation="left">关键词</Divider>
              <div>
                <Space wrap>
                  {selectedPaper.keywords && selectedPaper.keywords.length > 0 ? (
                    selectedPaper.keywords.map((keyword, index) => (
                      <Tag key={index} color="processing">
                        {keyword}
                      </Tag>
                    ))
                  ) : (
                    <Text type="secondary">无关键词</Text>
                  )}
                </Space>
              </div>
              
              <Divider orientation="left">引用信息</Divider>
              <Paragraph copyable>{`${selectedPaper.authors.join(', ')}. (${selectedPaper.year || 'n.d.'}). ${selectedPaper.title}. ${selectedPaper.venue ? `In ${selectedPaper.venue}` : ''}`}</Paragraph>
              
              <Divider orientation="left">链接</Divider>
              <div>
                {selectedPaper.url ? (
                  <Button type="link" icon={<LinkOutlined />} href={selectedPaper.url} target="_blank">
                    原始链接
                  </Button>
                ) : (
                  <Text type="secondary">无可用链接</Text>
                )}
                
                {selectedPaper.pdf_url && (
                  <Button type="link" icon={<FileTextOutlined />} href={selectedPaper.pdf_url} target="_blank">
                    PDF链接
                  </Button>
                )}
                
                {selectedPaper.doi && (
                  <Button type="link" icon={<LinkOutlined />} href={`https://doi.org/${selectedPaper.doi}`} target="_blank">
                    DOI: {selectedPaper.doi}
                  </Button>
                )}
                
                {selectedPaper.arxiv_id && (
                  <Button type="link" icon={<LinkOutlined />} href={`https://arxiv.org/abs/${selectedPaper.arxiv_id}`} target="_blank">
                    arXiv: {selectedPaper.arxiv_id}
                  </Button>
                )}
              </div>
              
              <Divider />
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Button 
                  type="primary" 
                  icon={<ImportOutlined />}
                  disabled={selectedPaper.isImported}
                  loading={importingPaperId === selectedPaper.id}
                  onClick={() => handleAddPaper(selectedPaper)}
                >
                  {selectedPaper.isImported ? '已添加到文献库' : '添加到文献库'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </Drawer>
      
      {/* 高级筛选抽屉 */}
      <Drawer
        title="高级搜索筛选"
        placement="right"
        width={360}
        onClose={() => setFilterDrawerVisible(false)}
        open={filterDrawerVisible}
        footer={
          <div style={{ textAlign: 'right' }}>
            <Button 
              style={{ marginRight: 8 }} 
              onClick={() => {
                setSelectedSources(['arxiv', 'semanticscholar', 'core', 'openalex']);
                setSelectedDomains([]);
                setSelectedVenues([]);
                setYearRange([null, null]);
              }}
            >
              重置
            </Button>
            <Button 
              type="primary" 
              onClick={() => {
                setFilterDrawerVisible(false);
                handleSearch();
              }}
            >
              应用筛选
            </Button>
          </div>
        }
      >
        <div className="filter-section">
          <Title level={5}>数据来源</Title>
          <Checkbox.Group 
            value={selectedSources}
            onChange={setSelectedSources}
            style={{ width: '100%' }}
          >
            <Row>
              <Col span={24}>
                <Checkbox value="arxiv">arXiv</Checkbox>
              </Col>
              <Col span={24}>
                <Checkbox value="semanticscholar">Semantic Scholar</Checkbox>
              </Col>
              <Col span={24}>
                <Checkbox value="core">CORE</Checkbox>
              </Col>
              <Col span={24}>
                <Checkbox value="openalex">OpenAlex</Checkbox>
              </Col>
            </Row>
          </Checkbox.Group>
          
          <Divider />
          
          <Title level={5}>研究方向</Title>
          <Checkbox.Group 
            options={RESEARCH_DOMAINS.map(domain => ({ label: domain.label, value: domain.value }))}
            value={selectedDomains}
            onChange={setSelectedDomains}
          />
          
          <Divider />
          
          <Title level={5}>会议/期刊</Title>
          <Checkbox.Group 
            options={CONFERENCES_JOURNALS.map(venue => ({ label: venue.label, value: venue.value }))}
            value={selectedVenues}
            onChange={setSelectedVenues}
          />
          
          <Divider />
          
          <Title level={5}>发表年份</Title>
          <RangePicker 
            picker="year"
            value={[
              yearRange[0] ? moment(`${yearRange[0]}-01-01`) : null, 
              yearRange[1] ? moment(`${yearRange[1]}-12-31`) : null
            ]}
            onChange={(dates) => {
              if (dates && dates[0] && dates[1]) {
                setYearRange([dates[0].year(), dates[1].year()]);
              } else {
                setYearRange([null, null]);
              }
            }}
          />
          
          <Divider />
          
          <Title level={5}>搜索模式</Title>
          <Radio.Group 
            value={searchMode}
            onChange={(e) => setSearchMode(e.target.value)}
          >
            <Space direction="vertical">
              <Radio value="semantic">
                <Space>
                  <span>语义搜索</span>
                  <Text type="secondary">(基于文本理解)</Text>
                </Space>
              </Radio>
              <Radio value="keyword">
                <Space>
                  <span>关键词搜索</span>
                  <Text type="secondary">(精确匹配)</Text>
                </Space>
              </Radio>
            </Space>
          </Radio.Group>
        </div>
      </Drawer>
    </div>
  );
};

export default LiteratureSearch; 