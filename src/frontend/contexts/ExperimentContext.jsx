import React, { createContext, useContext, useState, useEffect } from 'react';
import { message } from 'antd';
import { experimentsAPI } from '../services/api';

// 创建实验管理上下文
const ExperimentContext = createContext();

// 实验管理上下文提供者
export const ExperimentProvider = ({ children }) => {
  // 状态管理
  const [experiments, setExperiments] = useState([]);
  const [currentExperiment, setCurrentExperiment] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [algorithms, setAlgorithms] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState({
    experiments: false,
    experimentDetails: false,
    datasets: false,
    algorithms: false,
    metrics: false,
    runExperiment: false,
    createExperiment: false,
  });
  const [filters, setFilters] = useState({
    dataset: null,
    algorithm: null,
    status: null,
    sortBy: 'date',
    sortOrder: 'desc',
  });

  // 获取实验列表
  const fetchExperiments = async (params = {}) => {
    setLoading(prev => ({ ...prev, experiments: true }));
    try {
      const mergedParams = {
        ...filters,
        ...params,
      };
      
      const response = await experimentsAPI.getExperiments(mergedParams);
      setExperiments(response.data);
      return response.data;
    } catch (error) {
      message.error('获取实验列表失败');
      console.error(error);
    } finally {
      setLoading(prev => ({ ...prev, experiments: false }));
    }
  };

  // 获取数据集列表
  const fetchDatasets = async () => {
    setLoading(prev => ({ ...prev, datasets: true }));
    try {
      const response = await experimentsAPI.getDatasets();
      setDatasets(response.data);
      return response.data;
    } catch (error) {
      console.error('获取数据集列表失败', error);
    } finally {
      setLoading(prev => ({ ...prev, datasets: false }));
    }
  };

  // 获取算法列表
  const fetchAlgorithms = async () => {
    setLoading(prev => ({ ...prev, algorithms: true }));
    try {
      const response = await experimentsAPI.getAlgorithms();
      setAlgorithms(response.data);
      return response.data;
    } catch (error) {
      console.error('获取算法列表失败', error);
    } finally {
      setLoading(prev => ({ ...prev, algorithms: false }));
    }
  };

  // 获取评估指标列表
  const fetchMetrics = async () => {
    setLoading(prev => ({ ...prev, metrics: true }));
    try {
      const response = await experimentsAPI.getMetrics();
      setMetrics(response.data);
      return response.data;
    } catch (error) {
      console.error('获取评估指标列表失败', error);
    } finally {
      setLoading(prev => ({ ...prev, metrics: false }));
    }
  };

  // 获取单个实验详情
  const fetchExperimentDetails = async (id) => {
    if (!id) return;
    
    setLoading(prev => ({ ...prev, experimentDetails: true }));
    try {
      const response = await experimentsAPI.getExperiment(id);
      setCurrentExperiment(response.data);
      return response.data;
    } catch (error) {
      message.error('获取实验详情失败');
      console.error(error);
    } finally {
      setLoading(prev => ({ ...prev, experimentDetails: false }));
    }
  };

  // 创建新实验
  const createExperiment = async (experimentData) => {
    setLoading(prev => ({ ...prev, createExperiment: true }));
    try {
      const response = await experimentsAPI.createExperiment(experimentData);
      setExperiments(prev => [response.data, ...prev]);
      message.success('实验创建成功');
      return response.data;
    } catch (error) {
      message.error('创建实验失败');
      console.error(error);
      throw error;
    } finally {
      setLoading(prev => ({ ...prev, createExperiment: false }));
    }
  };

  // 运行实验
  const runExperiment = async (id) => {
    setLoading(prev => ({ ...prev, runExperiment: true }));
    try {
      const response = await experimentsAPI.runExperiment(id);
      
      // 更新实验列表中的状态
      setExperiments(prev => 
        prev.map(exp => 
          exp.id === id ? { ...exp, status: 'running' } : exp
        )
      );
      
      // 如果当前实验就是正在运行的实验，也更新它的状态
      if (currentExperiment && currentExperiment.id === id) {
        setCurrentExperiment(prev => ({ ...prev, status: 'running' }));
      }
      
      message.success('实验已开始运行');
      return response.data;
    } catch (error) {
      message.error('运行实验失败');
      console.error(error);
      throw error;
    } finally {
      setLoading(prev => ({ ...prev, runExperiment: false }));
    }
  };

  // 更新过滤条件
  const updateFilters = (newFilters) => {
    setFilters(prev => ({
      ...prev,
      ...newFilters,
    }));
  };

  // 在组件挂载时加载初始数据
  useEffect(() => {
    fetchDatasets();
    fetchAlgorithms();
    fetchMetrics();
    fetchExperiments();
  }, []);

  // 过滤条件变化时重新加载数据
  useEffect(() => {
    fetchExperiments();
  }, [filters]);

  // 导出上下文值
  const contextValue = {
    experiments,
    currentExperiment,
    setCurrentExperiment,
    datasets,
    algorithms,
    metrics,
    loading,
    filters,
    fetchExperiments,
    fetchExperimentDetails,
    createExperiment,
    runExperiment,
    updateFilters,
  };

  return (
    <ExperimentContext.Provider value={contextValue}>
      {children}
    </ExperimentContext.Provider>
  );
};

// 自定义钩子，方便使用上下文
export const useExperiment = () => {
  const context = useContext(ExperimentContext);
  if (!context) {
    throw new Error('useExperiment必须在ExperimentProvider内部使用');
  }
  return context;
};

export default ExperimentContext; 