import React, { useState, useEffect, useRef } from 'react';
import { 
  Table, 
  Button, 
  Input, 
  Tag, 
  Space, 
  Typography, 
  Menu, 
  Layout, 
  Dropdown, 
  Modal, 
  Form,
  Select,
  Tooltip,
  TreeSelect,
  Popconfirm,
  Tabs,
  Badge,
  Card,
  message,
  Alert,
  Checkbox,
  Divider,
  Upload,
  DatePicker
} from 'antd';
import { 
  SearchOutlined, 
  FileTextOutlined, 
  DeleteOutlined, 
  EditOutlined, 
  FolderOutlined, 
  FolderAddOutlined,
  StarOutlined,
  StarFilled,
  DownloadOutlined,
  ExportOutlined,
  ImportOutlined,
  PlusOutlined,
  FileAddOutlined,
  EllipsisOutlined,
  UploadOutlined,
  DownOutlined
} from '@ant-design/icons';
import axios from 'axios';
import { API_BASE_URL } from '../../config';
import moment from 'moment';

const { Title, Text } = Typography;
const { Sider, Content } = Layout;
const { Option } = Select;
const { TextArea } = Input;
const { SHOW_PARENT } = TreeSelect;

// 文件夹结构数据
const FOLDER_TREE = [
  {
    title: '全部论文',
    value: 'all',
    key: 'all',
    selectable: false,
    children: [
      {
        title: '序列推荐',
        value: '序列推荐',
        key: 'sequential',
        children: [
          {
            title: '自注意力模型',
            value: '自注意力模型',
            key: 'sequential-attention',
          },
          {
            title: '对比学习方法',
            value: '对比学习方法',
            key: 'sequential-contrastive',
          },
        ]
      },
      {
        title: '对比学习',
        value: '对比学习',
        key: 'contrastive',
        children: [
          {
            title: '无监督对比',
            value: '无监督对比',
            key: 'contrastive-unsupervised',
          },
          {
            title: '有监督对比',
            value: '有监督对比',
            key: 'contrastive-supervised',
          },
        ]
      },
      {
        title: '图神经网络',
        value: '图神经网络',
        key: 'graph',
      },
      {
        title: '多模态推荐',
        value: '多模态推荐',
        key: 'multimodal',
      },
      {
        title: '未分类',
        value: '未分类',
        key: 'uncategorized',
      },
    ],
  },
  {
    title: '智能集合',
    value: 'smart',
    key: 'smart',
    selectable: false,
    children: [
      {
        title: '近期添加',
        value: 'recent',
        key: 'recent',
      },
      {
        title: '待阅读',
        value: 'to-read',
        key: 'to-read',
      },
      {
        title: '收藏论文',
        value: 'starred',
        key: 'starred',
      },
    ],
  },
];

// 标签管理数据
const TAGS = [
  { name: '重要', color: 'red', count: 12 },
  { name: '待读', color: 'orange', count: 23 },
  { name: '已读', color: 'green', count: 45 },
  { name: '参考', color: 'cyan', count: 18 },
  { name: '待实现', color: 'blue', count: 7 },
  { name: '方法借鉴', color: 'purple', count: 15 },
];

// 添加API调试辅助函数
const apiDebug = {
  request: (method, url, data = null, headers = {}) => {
    console.log(`[API请求] ${method.toUpperCase()} ${url}`);
    if (data) console.log('请求数据:', data);
    if (headers) console.log('请求头:', headers);
  },
  response: (status, data, url) => {
    console.log(`[API响应] ${status} ${url}`);
    console.log('响应数据:', data);
  },
  error: (error, url) => {
    console.error(`[API错误] ${url}`);
    if (error.response) {
      console.error(`状态码: ${error.response.status}`);
      console.error('响应数据:', error.response.data);
    } else if (error.request) {
      console.error('请求已发送但未收到响应');
    } else {
      console.error('错误消息:', error.message);
    }
    console.error('完整错误:', error);
  }
};

// 添加API包装函数，统一处理请求
const api = {
  getAuthHeaders: () => {
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('未找到认证令牌');
    }
    return {
      'Authorization': `Bearer ${token}`
    };
  },
  
  // 检查token是否过期
  checkTokenExpired: (error) => {
    if (error.response && error.response.status === 401) {
      message.error('登录已过期，请重新登录');
      // 可以在这里添加重定向到登录页的逻辑
      localStorage.removeItem('token');
      setTimeout(() => {
        window.location.href = '/login';
      }, 1500);
      return true;
    }
    return false;
  },
  
  // GET请求
  async get(url, params = {}, retries = 1) {
    try {
      apiDebug.request('get', url, params);
      const headers = this.getAuthHeaders();
      
      const response = await axios.get(`${API_BASE_URL}${url}`, {
        params,
        headers
      });
      
      apiDebug.response(response.status, response.data, url);
      return response.data;
    } catch (error) {
      apiDebug.error(error, url);
      
      // 检查令牌是否过期
      if (this.checkTokenExpired(error)) {
        return null;
      }
      
      // 重试逻辑
      if (retries > 0 && (!error.response || error.response.status >= 500)) {
        console.log(`[API重试] 将在1秒后重试 ${url}，剩余重试次数: ${retries-1}`);
        await new Promise(r => setTimeout(r, 1000));
        return this.get(url, params, retries - 1);
      }
      
      throw error;
    }
  },
  
  // POST请求
  async post(url, data = {}, config = {}, retries = 1) {
    try {
      apiDebug.request('post', url, data);
      const headers = this.getAuthHeaders();
      
      const finalConfig = {
        ...config,
        headers: {
          ...headers,
          ...(config.headers || {})
        }
      };
      
      const response = await axios.post(`${API_BASE_URL}${url}`, data, finalConfig);
      
      apiDebug.response(response.status, response.data, url);
      return response.data;
    } catch (error) {
      apiDebug.error(error, url);
      
      // 检查令牌是否过期
      if (this.checkTokenExpired(error)) {
        return null;
      }
      
      // 重试逻辑
      if (retries > 0 && (!error.response || error.response.status >= 500)) {
        console.log(`[API重试] 将在1秒后重试 ${url}，剩余重试次数: ${retries-1}`);
        await new Promise(r => setTimeout(r, 1000));
        return this.post(url, data, config, retries - 1);
      }
      
      throw error;
    }
  },
  
  // DELETE请求
  async delete(url, config = {}, retries = 1) {
    try {
      apiDebug.request('delete', url);
      const headers = this.getAuthHeaders();
      
      const finalConfig = {
        ...config,
        headers: {
          ...headers,
          ...(config.headers || {})
        }
      };
      
      const response = await axios.delete(`${API_BASE_URL}${url}`, finalConfig);
      
      apiDebug.response(response.status, response.data, url);
      return response.data;
    } catch (error) {
      apiDebug.error(error, url);
      
      // 检查令牌是否过期
      if (this.checkTokenExpired(error)) {
        return null;
      }
      
      // 重试逻辑
      if (retries > 0 && (!error.response || error.response.status >= 500)) {
        console.log(`[API重试] 将在1秒后重试 ${url}，剩余重试次数: ${retries-1}`);
        await new Promise(r => setTimeout(r, 1000));
        return this.delete(url, config, retries - 1);
      }
      
      throw error;
    }
  },
  
  // 添加PATCH请求
  async patch(url, data = {}, config = {}, retries = 1) {
    try {
      apiDebug.request('patch', url, data);
      const headers = this.getAuthHeaders();
      
      const finalConfig = {
        ...config,
        headers: {
          ...headers,
          ...(config.headers || {})
        }
      };
      
      const response = await axios.patch(`${API_BASE_URL}${url}`, data, finalConfig);
      
      apiDebug.response(response.status, response.data, url);
      return response.data;
    } catch (error) {
      apiDebug.error(error, url);
      
      // 检查令牌是否过期
      if (this.checkTokenExpired(error)) {
        return null;
      }
      
      // 重试逻辑
      if (retries > 0 && (!error.response || error.response.status >= 500)) {
        console.log(`[API重试] 将在1秒后重试 ${url}，剩余重试次数: ${retries-1}`);
        await new Promise(r => setTimeout(r, 1000));
        return this.patch(url, data, config, retries - 1);
      }
      
      throw error;
    }
  }
};

const LiteratureManagement = () => {
  // 状态管理
  const [papers, setPapers] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [currentFolder, setCurrentFolder] = useState('all');
  const [modalVisible, setModalVisible] = useState(false);
  const [currentPaper, setCurrentPaper] = useState(null);
  const [folderModalVisible, setFolderModalVisible] = useState(false);
  const [currentTab, setCurrentTab] = useState('all');
  const [exportModalVisible, setExportModalVisible] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [collapsed, setCollapsed] = useState(false);
  const [useMockData, setUseMockData] = useState(false);  // 默认不使用演示模式
  
  // 表单引用
  const [form] = Form.useForm();
  const [folderForm] = Form.useForm();
  const [exportForm] = Form.useForm();
  
  // 在组件内添加右键菜单状态
  const contextMenuRef = useRef(null);
  const [contextMenuVisible, setContextMenuVisible] = useState(false);
  const [contextMenuPosition, setContextMenuPosition] = useState({ x: 0, y: 0 });
  const [rightClickedPaper, setRightClickedPaper] = useState(null);
  
  // 生成模拟数据函数
  const generateMockData = () => {
    console.log('正在生成模拟数据...');
    const mockPapers = Array(15).fill().map((_, index) => ({
      id: `mock-paper-${index}`,
      title: `序列推荐中的自监督学习研究 ${index + 1}`,
      authors: ['张三', '李四', '王五'],
      venue: index % 3 === 0 ? 'SIGIR 2023' : (index % 3 === 1 ? 'RecSys 2022' : 'KDD 2021'),
      year: 2021 + (index % 3),
      keywords: ['推荐系统', '序列推荐', '自监督学习', '对比学习'],
      isStarred: index % 5 === 0,
      tags: index % 4 === 0 ? ['重要', '待读'] : (index % 4 === 1 ? ['已读', '参考'] : (index % 4 === 2 ? ['待实现'] : ['方法借鉴'])),
      notes: index % 3 === 0 ? '这篇论文提出了一种新的序列推荐方法，值得深入阅读' : '',
      addedDate: new Date(2023, 5 + (index % 6), 10 + (index % 15)).toISOString(),
      folder: index % 5 === 0 ? '序列推荐' : (index % 5 === 1 ? '对比学习' : (index % 5 === 2 ? '图神经网络' : (index % 5 === 3 ? '多模态推荐' : '未分类'))),
      lastOpened: index % 7 === 0 ? new Date(2023, 10, 10 + (index % 15)).toISOString() : null,
    }));
    
    console.log('已生成模拟数据:', mockPapers.length, '条');
    return mockPapers;
  };
  
  // 切换数据源
  const toggleDataSource = () => {
    const nextMode = !useMockData;
    setUseMockData(nextMode);
    
    if (nextMode) {
      // 切换到模拟数据
      const mockData = generateMockData();
      setPapers(mockData);
      setTotal(mockData.length);
      setErrorMessage(null);
      message.success('已切换到演示模式');
    } else {
      // 切换到API数据
      message.loading('正在加载真实数据...', 1.5);
      // 使用延迟确保状态已更新
      setTimeout(() => {
      loadPapers();
      }, 100);
    }
  };
  
  // 初始加载数据
  useEffect(() => {
    console.log('LiteratureManagement组件已挂载');
    // 尝试加载真实数据，如果失败才使用模拟数据
    loadPapers();
  }, []);
  
  // 加载论文数据
  const loadPapers = async () => {
    console.log('开始加载论文数据...');
    setLoading(true);
    setErrorMessage(null); // 重置错误消息
    
    try {
      // 构建API参数
      const params = {
        page: 1,
        per_page: 100, // 增大每页数量，确保获取所有论文
        sort_by: 'updated_at',
        sort_order: 'desc'
      };
      
      if (searchText) {
        params.query = searchText;
      }
      
      if (currentFolder === 'starred') {
        params.favorite = true;
      } else if (currentFolder !== 'all' && !currentFolder.startsWith('smart')) {
        // 处理文件夹过滤
        params.folder = currentFolder;
      }
      
      // 使用API封装
      const response = await api.get('/papers', params);
      
      // 检查API调用是否成功
      if (!response) {
        // api.checkTokenExpired 已处理令牌过期的情况
        return;
      }
      
      // 简化数据处理逻辑
      let papersList = [];
      let papersCount = 0;
      
      if (response.papers) {
        papersList = response.papers;
        papersCount = response.total || papersList.length;
      } else if (Array.isArray(response)) {
        papersList = response;
        papersCount = papersList.length;
      }
      
      console.log(`发现 ${papersList.length} 篇论文`);
      
      // 仅当明确选择使用模拟数据且真实数据为空时才使用模拟数据
      if (papersList.length === 0 && useMockData) {
        const mockData = generateMockData();
        setPapers(mockData);
        setTotal(mockData.length);
        console.log('使用模拟数据', mockData.length, '条');
      } else {
        // 在设置论文数据前，统一字段名
        papersList = papersList.map(paper => ({
          ...paper,
          // 确保所有论文对象都有一致的字段
          isStarred: paper.is_favorite !== undefined ? paper.is_favorite : paper.isStarred,
          venue: paper.venue || paper.journal || paper.conference || '',
          year: paper.year || (paper.publication_date ? new Date(paper.publication_date).getFullYear() : ''),
          addedDate: paper.created_at || paper.addedDate || new Date().toISOString(),
          // 统一标签格式
          tags: paper.tags ? (Array.isArray(paper.tags) 
            ? paper.tags.map(tag => typeof tag === 'string' ? tag : tag.name)
            : [paper.tags]) 
            : []
        }));
      setPapers(papersList);
      setTotal(papersCount);
        console.log('已加载真实API数据', papersList.length, '条');
        setUseMockData(false); // 确保禁用模拟数据模式
      }
      
    } catch (error) {
      console.error('加载论文数据失败:', error);
      
      let errorMsg = '加载数据失败';
      
      if (error.response) {
        console.log('服务器错误:', error.response.status, error.response.data);
        if (error.response.status === 401) {
          errorMsg = '登录已过期，请重新登录';
        } else {
          errorMsg = `服务器错误 (${error.response.status}): ${error.response.data?.detail || '未知错误'}`;
        }
      } else {
        console.log('网络错误:', error.message);
        errorMsg = `无法连接到服务器: ${error.message}`;
      }
      
      setErrorMessage(errorMsg);
      message.error(errorMsg);
      
      // 仅当用户明确选择使用模拟数据时才加载模拟数据
      if (useMockData) {
        const mockData = generateMockData();
        setPapers(mockData);
        setTotal(mockData.length);
        console.log('加载失败，使用模拟数据', mockData.length, '条');
      } else {
      setPapers([]);
      setTotal(0);
      }
    } finally {
      setLoading(false);
    }
  };
  
  // 搜索处理
  const handleSearch = (value) => {
    setSearchText(value);
    // 这里应该调用后端API进行过滤
  };
  
  // 行选择处理
  const onSelectChange = (selectedKeys) => {
    setSelectedRowKeys(selectedKeys);
  };
  
  // 选择器配置
  const rowSelection = {
    selectedRowKeys,
    onChange: onSelectChange,
  };
  
  // 编辑论文处理
  const handleEditPaper = (paper) => {
    setCurrentPaper(paper);
    
    console.log('准备编辑论文:', paper);
    
    // 根据是否是模拟数据，设置不同的表单初始值
    if (useMockData) {
    form.setFieldsValue({
      title: paper.title,
        authors: Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors,
      venue: paper.venue,
      year: paper.year,
      keywords: paper.keywords,
      tags: paper.tags,
      notes: paper.notes,
      folder: paper.folder
    });
    } else {
      // 统一处理作者数据格式
      let authorsString = '';
      if (Array.isArray(paper.authors)) {
        authorsString = paper.authors.map(a => {
          if (typeof a === 'string') return a;
          return a.name || '';
        }).join(', ');
      } else if (typeof paper.authors === 'string') {
        authorsString = paper.authors;
      }
      
      // 统一处理标签数据格式
      let tagsArray = [];
      if (Array.isArray(paper.tags)) {
        tagsArray = paper.tags.map(t => {
          if (typeof t === 'string') return t;
          return t.name || '';
        }).filter(t => t);
      } else if (typeof paper.tags === 'string' && paper.tags) {
        tagsArray = [paper.tags];
      }
      
      // 统一处理日期格式
      let pubDate = paper.publication_date;
      if (paper.year && !pubDate) {
        pubDate = `${paper.year}-01-01`;
      }
      
      form.setFieldsValue({
        title: paper.title || '',
        abstract: paper.abstract || '',
        authors: authorsString,
        journal: paper.journal || paper.venue || '',
        conference: paper.conference || '',
        publication_date: pubDate ? moment(pubDate) : null,
        tags: tagsArray,
        notes: paper.notes || ''
      });
    }
    
    setModalVisible(true);
  };
  
  // 提交编辑表单
  const handleSubmitEdit = async () => {
    try {
      const values = await form.validateFields();
      
      // 如果使用模拟数据，使用原来的逻辑
      if (useMockData) {
      // 处理表单值
      const updatedPaper = {
        ...currentPaper,
        title: values.title,
        authors: values.authors.split(',').map(a => a.trim()),
        venue: values.venue,
        year: values.year,
        keywords: values.keywords,
        tags: values.tags,
        notes: values.notes,
        folder: values.folder
      };
      
      // 更新列表中的论文
      setPapers(prevPapers => 
        prevPapers.map(paper => 
          paper.id === updatedPaper.id ? updatedPaper : paper
        )
      );
      
      setModalVisible(false);
      message.success('论文信息已更新');
        return;
      }
      
      // 显示加载消息
      const hide = message.loading('正在更新论文信息...', 0);
      
      try {
        // 准备更新数据 - 确保符合PaperUpdate模型
        const updateData = {
          title: values.title
        };
        
        // 只有当有值时才添加其他字段，避免发送undefined或null
        if (values.abstract) updateData.abstract = values.abstract;
        
        // 确保authors是对象数组而不是字符串
        if (values.authors) {
          // 完全重写authors处理逻辑，确保类型正确
          let authorsArray = [];
          
          if (typeof values.authors === 'string') {
            // 字符串情况：分割并创建对象数组
            authorsArray = values.authors
              .split(',')
              .map(name => name.trim())
              .filter(name => name)
              .map(name => ({ name }));
          } else if (Array.isArray(values.authors)) {
            // 数组情况：确保每个元素都是对象
            authorsArray = values.authors.map(author => {
              if (typeof author === 'string') {
                return { name: author };
              } else if (typeof author === 'object' && author !== null) {
                // 如果已经是对象且有name属性，则使用它
                if (author.name) {
                  return author;
                } else {
                  // 如果是对象但没有name属性，尝试转换
                  const authorStr = String(author);
                  return { name: authorStr };
                }
              }
              return { name: String(author) }; // 兜底转换
            });
          }
          
          // 只有在数组非空时才添加到更新数据中
          if (authorsArray.length > 0) {
            updateData.authors = authorsArray;
          }
        }
        
        // 处理日期字段
        if (values.publication_date) {
          if (values.publication_date._isAMomentObject) {
            updateData.publication_date = values.publication_date.format('YYYY-MM-DD');
          } else if (values.publication_date instanceof Date) {
            updateData.publication_date = values.publication_date.toISOString().split('T')[0];
          } else if (typeof values.publication_date === 'string') {
            updateData.publication_date = values.publication_date;
          }
        }
        
        // 处理标签字段 - 确保是数组
        if (values.tags) {
          // 确保tags总是一个数组
          if (typeof values.tags === 'string') {
            // 如果是逗号分隔的字符串，转换为数组
            updateData.tags = values.tags.split(',').map(tag => tag.trim()).filter(tag => tag);
          } else if (Array.isArray(values.tags)) {
            // 如果已经是数组，使用现有数组
            updateData.tags = values.tags;
          } else {
            // 其他情况，使用空数组
            updateData.tags = [];
          }
        } else {
          // 如果tags不存在，使用空数组
          updateData.tags = [];
        }
        
        // 处理其他可选字段
        if (values.journal) updateData.journal = values.journal;
        if (values.conference) updateData.conference = values.conference;
        if (values.notes !== undefined) updateData.notes = values.notes || ''; // 确保notes是字符串而不是null或undefined
        
        console.log('正在更新论文，请求数据:', JSON.stringify(updateData, null, 2));
        console.log('论文ID:', currentPaper.id);
        
        // 使用PATCH方法而不是POST
        const response = await api.patch(`/papers/${currentPaper.id}`, updateData, { 
          headers: { 'Content-Type': 'application/json' }
        });
        
        hide();
        
        if (!response) {
          // Token过期已经在api处理了
          return;
        }
        
        console.log('更新论文成功:', response);
        message.success('论文信息已更新');
        setModalVisible(false);
        
        // 刷新论文列表
        setTimeout(() => {
          loadPapers();
        }, 500);
      } catch (error) {
        hide();
        console.error('API更新论文失败:', error);
        
        let errorMessage = '更新论文信息失败';
        if (error.response) {
          console.error('服务器返回错误:', error.response.status, error.response.data);
          console.error('请求数据:', JSON.stringify(error.config?.data, null, 2));
          if (error.response.status === 401) {
            errorMessage = '登录已过期，请重新登录';
          } else if (error.response.data?.detail) {
            errorMessage += ': ' + error.response.data.detail;
          }
        } else if (error.message) {
          errorMessage += ': ' + error.message;
        }
        
        message.error(errorMessage);
      }
    } catch (error) {
      console.error('表单验证失败:', error);
      message.error('请检查表单填写是否正确');
    }
  };
  
  // 删除论文处理
  const handleDeletePapers = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要删除的论文');
      return;
    }
    
    // 如果使用模拟数据，使用原来的逻辑
    if (useMockData) {
    // 删除选中的论文
    setPapers(prevPapers => prevPapers.filter(paper => !selectedRowKeys.includes(paper.id)));
    setSelectedRowKeys([]);
    message.success('选中的论文已删除');
      return;
    }
    
    try {
      // 显示正在删除的消息
      const hide = message.loading(`正在删除 ${selectedRowKeys.length} 篇论文...`, 0);
      
      // 用于记录成功和失败的论文ID
      const failedPaperIds = [];
      const successPaperIds = [];
      
      // 逐个删除选中的论文
      for (const paperId of selectedRowKeys) {
        try {
          // 使用API封装进行删除请求
          await api.delete(`/papers/${paperId}`);
          console.log(`成功删除论文: ${paperId}`);
          successPaperIds.push(paperId);
        } catch (error) {
          console.error(`删除论文 ${paperId} 失败:`, error);
          
          // 检查是否是401错误(令牌过期)
          if (error.response && error.response.status === 401) {
            hide();
            // 令牌过期已在api.delete中处理
            return;
          }
          
          failedPaperIds.push(paperId);
        }
      }
      
      // 关闭加载提示
      hide();
      
      // 清空选中状态
      setSelectedRowKeys([]);
      
      // 本地先移除已删除的论文，提高响应速度
      setPapers(prevPapers => prevPapers.filter(paper => !successPaperIds.includes(paper.id)));
      
      // 然后再刷新论文列表获取最新数据
      loadPapers();
      
      // 根据结果显示消息
      if (failedPaperIds.length === 0) {
        message.success(`成功删除 ${successPaperIds.length} 篇论文`);
      } else if (failedPaperIds.length < selectedRowKeys.length) {
        message.warning(`部分论文删除失败，已删除 ${successPaperIds.length} 篇论文，${failedPaperIds.length} 篇论文删除失败`);
      } else {
        message.error('所有论文删除失败，请稍后重试');
      }
    } catch (error) {
      console.error('删除论文失败:', error);
      
      let errorMessage = '删除论文失败';
      if (error.response) {
        if (error.response.status === 401) {
          errorMessage = '登录已过期，请重新登录';
        } else if (error.response.data?.detail) {
          errorMessage += ': ' + error.response.data.detail;
        }
      } else if (error.message) {
        errorMessage += ': ' + error.message;
      }
      
      message.error(errorMessage);
    }
  };
  
  // 收藏/取消收藏论文
  const handleToggleStarPaper = async (paperId) => {
    // 如果使用的是模拟数据，则只更新本地数据
    if (useMockData) {
    setPapers(prevPapers => 
      prevPapers.map(paper => 
        paper.id === paperId 
          ? { ...paper, isStarred: !paper.isStarred } 
          : paper
      )
    );
      message.success('收藏状态已更新');
      return;
    }

    try {
      // 获取当前论文
      const paper = papers.find(p => p.id === paperId);
      if (!paper) {
        console.error('未找到要操作的论文:', paperId);
        return;
      }

      // 确定当前收藏状态 - 处理两种可能的字段名
      const isFavorite = paper.is_favorite !== undefined ? paper.is_favorite : paper.isStarred;
      
      // 显示加载提示
      const hide = message.loading('正在更新收藏状态...', 0);

      // 先在UI上更新收藏状态以提高响应速度
      setPapers(prevPapers => 
        prevPapers.map(p => 
          p.id === paperId 
            ? { ...p, is_favorite: !isFavorite, isStarred: !isFavorite } 
            : p
        )
      );

      try {
        // 使用API模块发送请求，确保请求体格式正确
        const response = await api.post(`/papers/${paperId}/favorite`, {
          is_favorite: !isFavorite
        });
        
        hide();
        
        if (!response) {
          // Token过期已在api处理
          return;
        }
        
        console.log('论文收藏状态已更新:', response);
        message.success(isFavorite ? '已取消收藏' : '已添加到收藏');
        
        // 刷新数据
        setTimeout(() => {
          loadPapers();
        }, 500);
      } catch (error) {
        hide();
        console.error('更新收藏状态失败:', error);
        
        // 恢复原来的收藏状态
        setPapers(prevPapers => 
          prevPapers.map(p => 
            p.id === paperId 
              ? { ...p, is_favorite: isFavorite, isStarred: isFavorite } 
              : p
          )
        );
        
        let errorMessage = '更新收藏状态失败';
        if (error.response) {
          console.error('服务器返回错误:', error.response.status, error.response.data);
          if (error.response.data?.detail) {
            errorMessage += ': ' + error.response.data.detail;
          }
        } else if (error.message) {
          errorMessage += ': ' + error.message;
        }
        
        message.error(errorMessage);
      }
    } catch (error) {
      console.error('收藏操作失败:', error);
      message.error('操作失败，请重试');
    }
  };
  
  // 创建新文件夹
  const handleCreateFolder = () => {
    folderForm.validateFields().then(values => {
      message.success(`已创建新文件夹: ${values.folderName}`);
      setFolderModalVisible(false);
    });
  };
  
  // 批量移动到文件夹
  const handleMoveToFolder = (folder) => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要移动的论文');
      return;
    }
    
    setPapers(prevPapers => 
      prevPapers.map(paper => 
        selectedRowKeys.includes(paper.id) 
          ? { ...paper, folder } 
          : paper
      )
    );
    
    message.success(`已将 ${selectedRowKeys.length} 篇论文移动到 "${folder}"`);
    setSelectedRowKeys([]);
  };
  
  // 批量添加标签
  const handleAddTag = async (tag) => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要添加标签的论文');
      return;
    }
    
    // 如果使用模拟数据，仅更新本地数据
    if (useMockData) {
    setPapers(prevPapers => 
      prevPapers.map(paper => 
        selectedRowKeys.includes(paper.id) 
            ? { ...paper, tags: [...new Set([...(paper.tags || []), tag])] } 
          : paper
      )
    );
    
    message.success(`已为 ${selectedRowKeys.length} 篇论文添加标签 "${tag}"`);
      return;
    }
    
    // 使用真实API添加标签
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录后再操作');
        return;
      }
      
      message.loading(`正在为 ${selectedRowKeys.length} 篇论文添加标签...`, 0.5);
      
      // 逐个处理选中的论文
      for (const paperId of selectedRowKeys) {
        // 找到当前论文
        const paper = papers.find(p => p.id === paperId);
        if (!paper) continue;
        
        // 准备更新数据
        const updateData = {
          operations: [{
            tag: tag,
            operation: "add"
          }]
        };
        
        // 发送请求更新标签
        await axios.patch(
          `${API_BASE_URL}/papers/${paperId}/tags`,
          updateData,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          }
        );
      }
      
      // 成功添加标签后刷新列表
      loadPapers();
      
      message.success(`已为 ${selectedRowKeys.length} 篇论文添加标签 "${tag}"`);
    } catch (error) {
      console.error('添加标签失败:', error);
      message.error('添加标签失败: ' + (error.response?.data?.detail || error.message));
    }
  };
  
  // 添加批量删除标签功能
  const handleRemoveTag = async (tag) => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要移除标签的论文');
      return;
    }
    
    // 如果使用模拟数据，仅更新本地数据
    if (useMockData) {
      setPapers(prevPapers => 
        prevPapers.map(paper => 
          selectedRowKeys.includes(paper.id) 
            ? { ...paper, tags: (paper.tags || []).filter(t => t !== tag) } 
            : paper
        )
      );
      
      message.success(`已为 ${selectedRowKeys.length} 篇论文移除标签 "${tag}"`);
      return;
    }
    
    // 使用真实API移除标签
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录后再操作');
        return;
      }
      
      message.loading(`正在为 ${selectedRowKeys.length} 篇论文移除标签...`, 0.5);
      
      // 逐个处理选中的论文
      for (const paperId of selectedRowKeys) {
        // 找到当前论文
        const paper = papers.find(p => p.id === paperId);
        if (!paper) continue;
        
        // 准备更新数据
        const updateData = {
          operations: [{
            tag: tag,
            operation: "remove"
          }]
        };
        
        // 发送请求更新标签
        await axios.patch(
          `${API_BASE_URL}/papers/${paperId}/tags`,
          updateData,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          }
        );
      }
      
      // 成功移除标签后刷新列表
      loadPapers();
      
      message.success(`已为 ${selectedRowKeys.length} 篇论文移除标签 "${tag}"`);
    } catch (error) {
      console.error('移除标签失败:', error);
      message.error('移除标签失败: ' + (error.response?.data?.detail || error.message));
    }
  };
  
  // 导出选中论文
  const handleExport = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要导出的论文');
      return;
    }
    
    setExportModalVisible(true);
  };
  
  // 确认导出
  const handleConfirmExport = () => {
    exportForm.validateFields().then(values => {
      message.success(`已将 ${selectedRowKeys.length} 篇论文导出为 ${values.format} 格式`);
      setExportModalVisible(false);
    });
  };
  
  // 添加新论文功能
  const handleAddPaper = async () => {
    try {
      const values = await form.validateFields();
      
      // 如果使用模拟数据，使用简单的本地添加
      if (useMockData) {
        const newPaper = {
          id: `mock-paper-${Date.now()}`,
          title: values.title,
          authors: typeof values.authors === 'string' ? values.authors.split(',').map(a => a.trim()) : values.authors,
          venue: values.venue || '',
          year: values.year || new Date().getFullYear(),
          keywords: values.keywords || [],
          tags: values.tags || [],
          notes: values.notes || '',
          folder: values.folder || '未分类',
          addedDate: new Date().toISOString(),
          isStarred: false
        };
        
        setPapers(prevPapers => [newPaper, ...prevPapers]);
        setModalVisible(false);
        message.success('论文已添加');
        return;
      }
      
      // 显示加载消息
      const hide = message.loading('正在添加论文...', 0);
      
      try {
        // 准备请求数据 - 简化为最基本必须字段
        const paperData = {
          title: values.title,
          source: "manual" // 手动添加
        };
        
        // 有值时才添加可选字段
        if (values.abstract) paperData.abstract = values.abstract;
        if (values.authors) {
          if (typeof values.authors === 'string') {
            paperData.authors = values.authors.split(',').map(a => ({name: a.trim()}));
          } else if (Array.isArray(values.authors)) {
            paperData.authors = values.authors;
          }
        }
        
        // 其他可选字段
        if (values.publication_date) {
          try {
            if (values.publication_date._isAMomentObject) {
              paperData.publication_date = values.publication_date.format('YYYY-MM-DD');
            } else {
              paperData.publication_date = new Date(values.publication_date).toISOString().split('T')[0];
            }
          } catch (e) {
            console.error('日期解析错误:', e);
          }
        }
        
        if (values.journal) paperData.journal = values.journal;
        if (values.conference) paperData.conference = values.conference;
        if (values.tags && values.tags.length > 0) paperData.tags = values.tags;
        if (values.notes) paperData.notes = values.notes;
        
        console.log('正在添加论文，请求数据:', paperData);
        
        // 使用API封装进行请求
        const response = await api.post('/papers', paperData);
        
        hide();
        
        if (!response) {
          // Token过期已经在api处理了
          return;
        }
        
        console.log('添加论文成功:', response);
        message.success('论文已成功添加');
        setModalVisible(false);
        
        // 延迟加载以确保后端处理完成
        setTimeout(() => {
          loadPapers();
        }, 500);
      } catch (error) {
        hide();
        let errorMessage = '添加论文失败';
        
        if (error.response) {
          if (error.response.data?.detail) {
            errorMessage += ': ' + error.response.data.detail;
          }
        } else if (error.message) {
          errorMessage += ': ' + error.message;
        }
        
        console.error('添加论文失败:', errorMessage);
        message.error(errorMessage);
      }
    } catch (error) {
      console.error('表单验证失败:', error);
      message.error('请检查表单填写是否正确');
    }
  };
  
  // 修改文件上传功能
  const handleUploadPaper = async (file) => {
    try {
      // 检查文件类型
      if (file.type !== 'application/pdf') {
        message.error('只支持上传PDF文件');
        return false;
      }
      
      // 检查文件大小 (限制为50MB)
      if (file.size > 50 * 1024 * 1024) {
        message.error('文件大小不能超过50MB');
        return false;
      }
      
      // 如果使用模拟数据，直接返回，不支持上传
      if (useMockData) {
        message.warning('演示模式不支持文件上传，请切换到API数据模式');
        return false;
      }
      
      // 显示上传进度消息
      const hideLoading = message.loading('正在上传论文，请稍候...', 0);
      
      try {
        // 使用FormData处理文件上传
        const formData = new FormData();
        formData.append('file', file);
        formData.append('extract_content', 'true');
        
        // 文件名可能包含论文标题信息，尝试提取
        const filename = file.name.replace('.pdf', '');
        if (filename && filename.length > 5) {
          formData.append('title', filename);
        }
        
        // 使用API封装，但特殊处理FormData
        const token = localStorage.getItem('token');
        if (!token) {
          hideLoading();
          message.error('未找到认证令牌，请先登录');
          return false;
        }
        
        apiDebug.request('post', '/papers/upload', { filename, size: file.size });
        
        const response = await axios.post(
          `${API_BASE_URL}/papers/upload`,
          formData,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'multipart/form-data'
            },
            // 添加上传进度处理
            onUploadProgress: (progressEvent) => {
              const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
              console.log(`上传进度: ${percentCompleted}%`);
            }
          }
        );
        
        apiDebug.response(response.status, response.data, '/papers/upload');
        
        hideLoading(); // 关闭加载提示
        console.log('上传论文成功:', response.data);
        message.success('论文上传成功，正在提取内容');
        
        // 刷新论文列表
        setTimeout(() => {
          loadPapers();
        }, 1000); // 延迟一秒刷新，等待后端处理
        
        return false; // 阻止默认上传行为
      } catch (error) {
        hideLoading();
        
        // 检查令牌是否过期
        if (api.checkTokenExpired(error)) {
          return false;
        }
        
        let errorMessage = '上传论文失败';
        if (error.response?.status === 413) {
          errorMessage = '文件太大，服务器拒绝处理';
        } else if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail;
        } else if (error.message) {
          errorMessage += ': ' + error.message;
        }
        
        console.error('API上传失败:', error, errorMessage);
        message.error(errorMessage);
        return false;
      }
    } catch (error) {
      console.error('上传论文失败:', error);
      
      let errorMessage = '上传论文失败';
      if (error.message) {
        errorMessage += ': ' + error.message;
      }
      
      message.error(errorMessage);
      return false;
    }
  };
  
  // 添加查看论文详情的处理函数
  const handleViewPaper = (paper) => {
    // 如果是真实数据，使用paper.file_path查看PDF
    if (!useMockData && paper.file_path) {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录后再查看论文');
        return;
      }
      
      // 构造文件下载URL
      const fileUrl = `${API_BASE_URL}/papers/${paper.id}/file`;
      
      // 在新窗口打开文件链接
      window.open(fileUrl, '_blank');
      return;
    }
    
    // 显示论文信息
    Modal.info({
      title: paper.title,
      width: 700,
      content: (
        <div>
          <p><strong>作者:</strong> {Array.isArray(paper.authors) 
            ? paper.authors.map(a => typeof a === 'string' ? a : a.name).join(', ')
            : paper.authors}</p>
          {paper.abstract && <p><strong>摘要:</strong> {paper.abstract}</p>}
          {paper.notes && <p><strong>笔记:</strong> {paper.notes}</p>}
        </div>
      ),
      okText: '关闭'
    });
  };
  
  // 处理右键点击事件
  const handleContextMenu = (e, paper) => {
    e.preventDefault();
    setContextMenuPosition({ x: e.clientX, y: e.clientY });
    setContextMenuVisible(true);
    setRightClickedPaper(paper);
  };

  // 处理右键菜单关闭
  const handleContextMenuClose = () => {
    setContextMenuVisible(false);
    setRightClickedPaper(null);
  };

  // 右键菜单项列表
  const contextMenuItems = [
    {
      key: 'view',
      label: '查看详情',
      icon: <FileTextOutlined />,
      onClick: () => {
        if (rightClickedPaper) {
          handleViewPaper(rightClickedPaper);
        }
        handleContextMenuClose();
      }
    },
    {
      key: 'star',
      label: rightClickedPaper?.is_favorite || rightClickedPaper?.isStarred ? '取消收藏' : '收藏',
      icon: (rightClickedPaper?.is_favorite || rightClickedPaper?.isStarred) ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />,
      onClick: () => {
        if (rightClickedPaper) {
          handleToggleStarPaper(rightClickedPaper.id);
        }
        handleContextMenuClose();
      }
    },
    {
      key: 'edit',
      label: '编辑信息',
      icon: <EditOutlined />,
      onClick: () => {
        if (rightClickedPaper) {
          handleEditPaper(rightClickedPaper);
        }
        handleContextMenuClose();
      }
    },
    {
      key: 'download',
      label: '下载PDF',
      icon: <DownloadOutlined />,
      onClick: () => {
        if (rightClickedPaper && rightClickedPaper.file_path) {
          // 构造文件下载URL
          const token = localStorage.getItem('token');
          if (!token) {
            message.error('请先登录后再下载论文');
            return;
          }
          
          const fileUrl = `${API_BASE_URL}/papers/${rightClickedPaper.id}/file`;
          window.open(fileUrl, '_blank');
        } else {
          message.warning('该论文没有可下载的PDF文件');
        }
        handleContextMenuClose();
      }
    },
    {
      type: 'divider',
    },
    {
      key: 'delete',
      label: '删除',
      icon: <DeleteOutlined />,
      danger: true,
      onClick: () => {
        if (rightClickedPaper) {
          Modal.confirm({
            title: '确认删除',
            content: `确定要删除论文"${rightClickedPaper.title}"吗？此操作不可恢复。`,
            okText: '删除',
            okType: 'danger',
            cancelText: '取消',
            onOk: () => {
              setSelectedRowKeys([rightClickedPaper.id]);
              handleDeletePapers();
            }
          });
        }
        handleContextMenuClose();
      }
    }
  ];

  // 修改表格组件，添加onRow属性以支持右键菜单
  const renderTable = (dataSource) => (
    <Table
      rowSelection={rowSelection}
      columns={columns}
      dataSource={dataSource}
      rowKey="id"
      pagination={{
        total: dataSource.length,
        showSizeChanger: true,
        showTotal: (total) => `共 ${total} 篇论文`,
        pageSize: 10,
        pageSizeOptions: ['10', '20', '50', '100'],
      }}
      loading={loading}
      onRow={(record) => ({
        onContextMenu: (e) => handleContextMenu(e, record),
        onClick: () => handleViewPaper(record)
      })}
      style={{ marginTop: 16 }}
      size="middle"
      bordered={false}
      rowClassName={() => 'table-row-hover'}
      className="modern-table"
    />
  );

  // 修改渲染内容，支持右键菜单
  const renderContent = () => {
    // 如果没有论文数据且不在加载中，显示欢迎页面
    if (papers.length === 0 && !loading && !errorMessage) {
      return <Welcome />;
    }
    
    if (errorMessage) {
      return (
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <Alert
            message="加载错误"
            description={errorMessage}
            type="error"
            showIcon
            action={
              <Button size="small" type="primary" onClick={loadPapers}>
                重试
              </Button>
            }
          />
          <div style={{ marginTop: 20 }}>
            <Welcome />
          </div>
        </div>
      );
    }

    const tabItems = [
      {
        key: 'all',
        label: '全部',
        children: renderTable(papers)
      },
      {
        key: 'starred',
        label: '收藏',
        children: renderTable(papers.filter(p => p.is_favorite || p.isStarred))
      },
      {
        key: 'recent',
        label: '近期添加',
        children: renderTable(
          [...papers].sort((a, b) => {
            const dateA = new Date(a.addedDate || a.created_at || 0);
            const dateB = new Date(b.addedDate || b.created_at || 0);
            return dateB - dateA;
          })
        )
      }
    ];

    return (
      <div onContextMenu={(e) => e.preventDefault()}>
        <Card>
          <Tabs activeKey={currentTab} onChange={setCurrentTab} items={tabItems} />
        </Card>
        
        {/* 右键菜单 */}
        {contextMenuVisible && (
          <div
            ref={contextMenuRef}
            style={{
              position: 'fixed',
              left: contextMenuPosition.x,
              top: contextMenuPosition.y,
              zIndex: 1000
            }}
          >
            <Dropdown
              menu={{ items: contextMenuItems }}
              trigger={['click']}
              open={contextMenuVisible}
              onOpenChange={(visible) => !visible && handleContextMenuClose()}
            >
              <div style={{ position: 'absolute', left: 0, top: 0 }}></div>
            </Dropdown>
          </div>
        )}
      </div>
    );
  };

  // 添加点击其他区域关闭右键菜单
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (contextMenuRef.current && !contextMenuRef.current.contains(event.target)) {
        setContextMenuVisible(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // 添加批量操作功能
  const renderBatchOperations = () => {
    if (selectedRowKeys.length === 0) {
      return null;
    }

    return (
      <div style={{ marginBottom: 16, padding: 8, background: '#f5f5f5', borderRadius: 4 }}>
        <Space>
          <span>已选择 {selectedRowKeys.length} 篇论文</span>
          <Dropdown
            menu={{
              items: TAGS.map(tag => ({
                key: tag.name,
                label: tag.name,
                icon: <Tag color={tag.color} style={{ marginRight: 0 }} />,
                onClick: () => handleAddTag(tag.name)
              }))
            }}
          >
            <Button size="small">
              添加标签 <DownOutlined />
            </Button>
          </Dropdown>
          <Button 
            size="small" 
            danger 
            icon={<DeleteOutlined />}
            onClick={handleDeletePapers}
          >
            批量删除
          </Button>
          <Button 
            size="small" 
            type="text" 
            onClick={() => setSelectedRowKeys([])}
          >
            取消选择
          </Button>
        </Space>
      </div>
    );
  };

  // 修改columns中的按钮处理函数
  const columns = [
    {
      title: '',
      dataIndex: 'is_favorite',
      width: 50,
      render: (is_favorite, record) => (
        <Button
          type="text"
          icon={(is_favorite || record.isStarred) ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
          onClick={(e) => {
            e.stopPropagation(); // 阻止事件冒泡
            handleToggleStarPaper(record.id);
          }}
        />
      ),
    },
    {
      title: '标题',
      dataIndex: 'title',
      ellipsis: true,
      render: (text, record) => (
        <div>
          <a onClick={(e) => {
            e.stopPropagation(); // 阻止事件冒泡到行点击
            handleViewPaper(record);
          }}>{text}</a>
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {Array.isArray(record.authors) 
                ? record.authors.map(a => typeof a === 'string' ? a : a.name).join(', ')
                : record.authors} | {record.venue || record.journal || record.conference || ''} | {
                  record.year || (record.publication_date ? new Date(record.publication_date).getFullYear() : '')
                }
            </Text>
          </div>
        </div>
      ),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      width: 250,
      render: (tags, record) => {
        // 处理不同格式的标签
        const formattedTags = (tags || []).map(tag => 
          typeof tag === 'string' ? tag : tag.name
        );
        
        return (
        <Space wrap>
            {formattedTags.map(tag => {
            const tagInfo = TAGS.find(t => t.name === tag) || { color: 'default' };
            return <Tag color={tagInfo.color} key={tag}>{tag}</Tag>;
          })}
        </Space>
        );
      }
    },
    {
      title: '文件夹',
      dataIndex: 'folder',
      width: 120,
      render: folder => (
        <Tag icon={<FolderOutlined />} color="default">
          {folder}
        </Tag>
      ),
    },
    {
      title: '添加日期',
      dataIndex: 'addedDate',
      width: 120,
      render: date => new Date(date).toLocaleDateString(),
    },
    {
      title: '操作',
      width: 120,
      render: (_, record) => (
        <Space>
          <Tooltip title="查看详情">
            <Button 
              type="text" 
              icon={<FileTextOutlined />} 
              onClick={(e) => {
                e.stopPropagation();
                handleViewPaper(record);
              }} 
            />
          </Tooltip>
          <Tooltip title="编辑信息">
            <Button 
              type="text" 
              icon={<EditOutlined />} 
              onClick={(e) => {
                e.stopPropagation();
                handleEditPaper(record);
              }} 
            />
          </Tooltip>
          <Tooltip title="删除">
            <Popconfirm
              title="确定要删除这篇论文吗？"
              onConfirm={(e) => {
                e?.stopPropagation();
                // 删除单篇论文
                setSelectedRowKeys([record.id]);
                handleDeletePapers();
              }}
              okText="是"
              cancelText="否"
            >
              <Button type="text" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ];
  
  // 创建菜单项结构
  const generateMenuItems = () => {
    const items = [];
    
    // 添加全部论文组
    const allPapersGroup = {
      type: 'group',
      label: <Text strong>全部论文</Text>,
      key: 'all-group',
      children: FOLDER_TREE[0].children.map(folder => ({
        key: folder.key,
        icon: <FolderOutlined />,
        label: folder.title,
        children: folder.children ? folder.children.map(child => ({
          key: child.key,
          label: child.title,
        })) : undefined
      }))
    };
    
    // 添加智能集合组
    const smartCollectionGroup = {
      type: 'group',
      label: <Text strong>智能集合</Text>,
      key: 'smart-group',
      children: FOLDER_TREE[1].children.map(folder => ({
        key: folder.key,
        icon: <FolderOutlined />,
        label: folder.title
      }))
    };
    
    items.push(allPapersGroup, smartCollectionGroup);
    return items;
  };
  
  // 渲染一个简单的欢迎组件
  const Welcome = () => (
    <div style={{ textAlign: 'center', padding: '50px 0' }}>
      <Title level={3}>文献管理系统</Title>
      <p>您可以在这里管理和组织您的学术论文，添加标签、分类整理和导出分享。</p>
      {/* 添加一些统计信息或提示 */}
      <Card style={{ maxWidth: 600, margin: '0 auto', marginTop: 20, borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center' }}>
          <div>
            <Title level={2}>0</Title>
            <Text>我的论文</Text>
          </div>
          <div>
            <Title level={2}>0</Title>
            <Text>已分类</Text>
          </div>
          <div>
            <Title level={2}>0</Title>
            <Text>已标记</Text>
          </div>
        </div>
        <div style={{ marginTop: 20 }}>
              <Button 
            type="primary" 
                icon={<FileAddOutlined />} 
            size="large"
            style={{ borderRadius: '6px', height: '42px' }}
            onClick={() => {
              form.resetFields(); // 清空表单
              setCurrentPaper(null); // 设置为新增模式
              setModalVisible(true); // 打开模态框
            }}
          >
            添加您的第一篇论文
              </Button>
          </div>
      </Card>
    </div>
  );
  
  // 编辑/添加论文的模态框
  const renderModal = () => (
      <Modal
      title={currentPaper ? "编辑论文信息" : "添加新论文"}
        open={modalVisible}
      onOk={currentPaper ? handleSubmitEdit : handleAddPaper}
        onCancel={() => setModalVisible(false)}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
        >
          <Form.Item
            name="title"
            label="标题"
            rules={[{ required: true, message: '请输入论文标题' }]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            name="authors"
            label="作者"
            rules={[{ required: true, message: '请输入作者姓名' }]}
            extra="多个作者请用逗号分隔"
          >
            <Input />
          </Form.Item>
        
        <Form.Item
          name="abstract"
          label="摘要"
        >
          <Input.TextArea rows={4} />
          </Form.Item>
          
          <Form.Item
            name="tags"
            label="标签"
          >
            <Select
              mode="multiple"
              style={{ width: '100%' }}
              placeholder="选择标签"
            allowClear
            tokenSeparators={[',']}
            >
              {TAGS.map(tag => (
                <Option key={tag.name} value={tag.name}>
                  <Tag color={tag.color}>{tag.name}</Tag>
                </Option>
              ))}
            </Select>
          </Form.Item>
        
        <Form.Item
          name="journal"
          label="期刊/会议"
        >
          <Input placeholder="例如: SIGIR 2023, KDD 2022" />
        </Form.Item>
        
        <Form.Item
          name="publication_date"
          label="发表日期"
        >
          <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          
          <Form.Item
            name="notes"
            label="笔记"
          >
          <Input.TextArea rows={4} placeholder="添加笔记..." />
          </Form.Item>
        </Form>
      </Modal>
  );

  return (
    <div className="literature-management">
      {console.log('渲染LiteratureManagement组件', {
        papers: papers.length,
        loading,
        errorMessage
      })}

      {/* 主要布局 */}
      <Layout style={{ minHeight: 'calc(100vh - 40px)' }}>
        <Content style={{ padding: 16, minHeight: 'calc(100vh - 40px)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
            <Title level={4}>论文管理</Title>
            
            <Space>
              <Button 
                icon={<FileAddOutlined />} 
                type="primary"
                onClick={() => {
                  // 清空表单
                  form.resetFields();
                  setCurrentPaper(null);
                  setModalVisible(true);
                }}
              >
                添加论文
              </Button>
              
              <Button onClick={toggleDataSource} type="default">
                {useMockData ? '切换到API数据' : '切换到演示模式'}
              </Button>
            </Space>
          </div>
          
          {/* 批量操作区 */}
          {renderBatchOperations()}
          
          {renderContent()}
        </Content>
      </Layout>
      
      {/* 渲染编辑/添加论文模态框 */}
      {renderModal()}
      
      {/* 添加全局CSS样式 */}
      <style jsx global>{`
        .modern-table .ant-table-thead > tr > th {
          background-color: #fafafa;
          font-weight: 600;
          color: #333;
          border-bottom: 1px solid #f0f0f0;
        }
        
        .table-row-hover:hover {
          background-color: #f5f5f5 !important;
        }
        
        .modern-table .ant-table-tbody > tr > td {
          padding: 12px 16px;
          border-bottom: 1px solid #f0f0f0;
        }
        
        .modern-table .ant-table-pagination {
          margin: 16px 0;
        }
      `}</style>
    </div>
  );
};

export default LiteratureManagement; 