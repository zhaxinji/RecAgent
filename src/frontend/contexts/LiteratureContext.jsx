import React, { createContext, useContext, useState, useEffect } from 'react';
import { message } from 'antd';
import { papersAPI } from '../services/api';

// 创建文献管理上下文
const LiteratureContext = createContext();

// 文献管理上下文提供者
export const LiteratureProvider = ({ children }) => {
  // 状态管理
  const [papers, setPapers] = useState([]);
  const [currentPaper, setCurrentPaper] = useState(null);
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState({
    papers: false,
    paperDetails: false,
    upload: false,
    tags: false,
    notes: false,
    search: false,
  });
  const [searchResults, setSearchResults] = useState([]);
  const [filters, setFilters] = useState({
    tags: [],
    dateRange: null,
    searchText: '',
    sortBy: 'date',
    sortOrder: 'desc',
  });
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });

  // 获取论文列表
  const fetchPapers = async (params = {}) => {
    setLoading(prev => ({ ...prev, papers: true }));
    try {
      const mergedParams = {
        ...filters,
        page: pagination.current,
        per_page: pagination.pageSize,
        ...params,
      };
      
      const response = await papersAPI.getPapers(mergedParams);
      console.log('API返回论文数据:', response.data);
      
      if (response.data && response.data.papers) {
        setPapers(response.data.papers);
        setPagination(prev => ({
          ...prev,
          total: response.data.total || 0,
        }));
      } else {
        setPapers(response.data.items || []);
        setPagination(prev => ({
          ...prev,
          total: response.data.total || 0,
        }));
      }
      return response.data;
    } catch (error) {
      message.error('获取论文列表失败: ' + (error.response?.data?.detail || error.message));
      console.error('获取论文列表错误:', error);
    } finally {
      setLoading(prev => ({ ...prev, papers: false }));
    }
  };

  // 获取单篇论文详情
  const fetchPaperDetails = async (id) => {
    if (!id) return;
    
    setLoading(prev => ({ ...prev, paperDetails: true }));
    try {
      const response = await papersAPI.getPaper(id);
      setCurrentPaper(response.data);
      return response.data;
    } catch (error) {
      message.error('获取论文详情失败');
      console.error(error);
    } finally {
      setLoading(prev => ({ ...prev, paperDetails: false }));
    }
  };

  // 上传论文
  const uploadPaper = async (formData) => {
    setLoading(prev => ({ ...prev, upload: true }));
    try {
      const response = await papersAPI.uploadPaper(formData);
      setPapers(prev => [response.data, ...prev]);
      message.success('论文上传成功');
      return response.data;
    } catch (error) {
      message.error('论文上传失败');
      console.error(error);
      throw error;
    } finally {
      setLoading(prev => ({ ...prev, upload: false }));
    }
  };

  // 添加笔记
  const addNote = async (paperId, noteData) => {
    setLoading(prev => ({ ...prev, notes: true }));
    try {
      const response = await papersAPI.addNote(paperId, noteData);
      
      // 更新当前论文的笔记
      if (currentPaper && currentPaper.id === paperId) {
        setCurrentPaper(prev => ({
          ...prev,
          notes: [...(prev.notes || []), response.data],
        }));
      }
      
      message.success('笔记添加成功');
      return response.data;
    } catch (error) {
      message.error('添加笔记失败');
      console.error(error);
      throw error;
    } finally {
      setLoading(prev => ({ ...prev, notes: false }));
    }
  };

  // 获取标签列表
  const fetchTags = async () => {
    setLoading(prev => ({ ...prev, tags: true }));
    try {
      const response = await papersAPI.getTags();
      setTags(response.data);
      return response.data;
    } catch (error) {
      console.error('获取标签列表失败', error);
    } finally {
      setLoading(prev => ({ ...prev, tags: false }));
    }
  };

  // 搜索论文
  const searchPapers = async (searchText) => {
    setLoading(prev => ({ ...prev, search: true }));
    try {
      const params = {
        search: searchText,
        page: 1,
        page_size: 20,
      };
      
      const response = await papersAPI.getPapers(params);
      setSearchResults(response.data.items);
      return response.data.items;
    } catch (error) {
      message.error('搜索论文失败');
      console.error(error);
    } finally {
      setLoading(prev => ({ ...prev, search: false }));
    }
  };

  // 更新过滤条件
  const updateFilters = (newFilters) => {
    setFilters(prev => ({
      ...prev,
      ...newFilters,
    }));
    // 重置分页到第一页
    setPagination(prev => ({
      ...prev,
      current: 1,
    }));
  };

  // 处理分页变化
  const handlePaginationChange = (page, pageSize) => {
    setPagination(prev => ({
      ...prev,
      current: page,
      pageSize: pageSize || prev.pageSize,
    }));
  };

  // 在组件挂载时加载初始数据
  useEffect(() => {
    fetchTags();
    fetchPapers();
  }, []);

  // 过滤条件变化时重新加载数据
  useEffect(() => {
    fetchPapers();
  }, [filters, pagination.current, pagination.pageSize]);

  // 导出上下文值
  const contextValue = {
    papers,
    currentPaper,
    setCurrentPaper,
    tags,
    loading,
    searchResults,
    filters,
    pagination,
    fetchPapers,
    fetchPaperDetails,
    uploadPaper,
    addNote,
    fetchTags,
    searchPapers,
    updateFilters,
    handlePaginationChange,
  };

  return (
    <LiteratureContext.Provider value={contextValue}>
      {children}
    </LiteratureContext.Provider>
  );
};

// 自定义钩子，方便使用上下文
export const useLiterature = () => {
  const context = useContext(LiteratureContext);
  if (!context) {
    throw new Error('useLiterature必须在LiteratureProvider内部使用');
  }
  return context;
};

export default LiteratureContext; 