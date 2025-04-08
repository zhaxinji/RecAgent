import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Typography, Tabs, Button, Space, Spin, Badge, Statistic } from 'antd';
import { PlusOutlined, ReloadOutlined, BarsOutlined, AppstoreOutlined } from '@ant-design/icons';
import ExperimentList from '../components/experiment/ExperimentList';
import ExperimentForm from '../components/experiment/ExperimentForm';
import ExperimentDetail from '../components/experiment/ExperimentDetail';
import ExperimentResults from '../components/experiment/ExperimentResults';
import { useExperiment } from '../contexts/ExperimentContext';

const { Title } = Typography;

const ExperimentPage = ({ user }) => {
  // 使用ExperimentContext
  const { 
    loading, 
    experiments,
    currentExperiment,
    setCurrentExperiment,
    fetchExperiments,
    fetchDatasets,
    fetchAlgorithms,
    fetchMetrics 
  } = useExperiment();
  
  // 本地状态
  const [activeTab, setActiveTab] = useState('list');
  const [viewMode, setViewMode] = useState('list'); // 'list' 或 'grid'

  // 首次加载时获取数据
  useEffect(() => {
    if (user) {
      fetchExperiments();
      fetchDatasets();
      fetchAlgorithms();
      fetchMetrics();
    }
  }, [user]);

  // 刷新实验列表
  const handleRefresh = () => {
    fetchExperiments();
  };

  // 创建新实验
  const handleCreateNew = () => {
    setCurrentExperiment(null);
    setActiveTab('create');
  };

  // 查看实验详情
  const handleViewExperiment = (experiment) => {
    setCurrentExperiment(experiment);
    setActiveTab('detail');
  };

  // 查看实验结果
  const handleViewResults = (experiment) => {
    setCurrentExperiment(experiment);
    setActiveTab('results');
  };

  // 获取进行中和已完成的实验数量
  const getExperimentCounts = () => {
    if (!experiments || experiments.length === 0) {
      return { running: 0, completed: 0, total: 0 };
    }
    
    const running = experiments.filter(exp => exp.status === 'running').length;
    const completed = experiments.filter(exp => exp.status === 'completed').length;
    
    return {
      running,
      completed,
      total: experiments.length
    };
  };

  const counts = getExperimentCounts();

  // 渲染实验统计信息
  const renderStatistics = () => {
    return (
      <div className="experiment-statistics">
        <Statistic title="总实验数" value={counts.total} />
        <Statistic 
          title="进行中" 
          value={counts.running} 
          valueStyle={{ color: '#1890ff' }}
          prefix={<Badge status="processing" />}
        />
        <Statistic 
          title="已完成" 
          value={counts.completed} 
          valueStyle={{ color: '#52c41a' }}
          prefix={<Badge status="success" />}
        />
      </div>
    );
  };

  // 如果正在加载，显示加载状态
  if (loading.experiments && loading.datasets && loading.algorithms && !activeTab) {
    return (
      <div style={{ textAlign: 'center', padding: '50px 0' }}>
        <Spin size="large" tip="正在加载实验数据..." />
      </div>
    );
  }

  // 渲染页面内容
  const renderContent = () => {
    switch (activeTab) {
      case 'list':
        return (
          <ExperimentList 
            onViewExperiment={handleViewExperiment} 
            onViewResults={handleViewResults}
            viewMode={viewMode}
          />
        );
      case 'create':
        return (
          <ExperimentForm 
            onSuccess={() => setActiveTab('list')}
            onCancel={() => setActiveTab('list')}
          />
        );
      case 'detail':
        return (
          <ExperimentDetail 
            experiment={currentExperiment}
            onBack={() => setActiveTab('list')}
            onViewResults={() => setActiveTab('results')}
          />
        );
      case 'results':
        return (
          <ExperimentResults 
            experiment={currentExperiment}
            onBack={() => setActiveTab('detail')}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div>
      <Row gutter={[24, 24]}>
        <Col xs={24}>
          <Card className="card" style={{ minHeight: 'calc(100vh - 200px)' }}>
            <div className="experiment-header">
              <Title level={2}>实验设计工作台</Title>
              
              <Space>
                {activeTab === 'list' && (
                  <>
                    <Button.Group>
                      <Button 
                        type={viewMode === 'list' ? 'primary' : 'default'}
                        icon={<BarsOutlined />}
                        onClick={() => setViewMode('list')}
                      />
                      <Button 
                        type={viewMode === 'grid' ? 'primary' : 'default'}
                        icon={<AppstoreOutlined />}
                        onClick={() => setViewMode('grid')}
                      />
                    </Button.Group>
                    
                    <Button 
                      icon={<ReloadOutlined />} 
                      onClick={handleRefresh}
                    >
                      刷新
                    </Button>
                  </>
                )}
                
                {activeTab !== 'create' && (
                  <Button 
                    type="primary" 
                    icon={<PlusOutlined />}
                    onClick={handleCreateNew}
                  >
                    新建实验
                  </Button>
                )}
              </Space>
            </div>
            
            {activeTab === 'list' && renderStatistics()}
            
            <div className="experiment-content">
              {renderContent()}
            </div>
          </Card>
        </Col>
      </Row>

      <style jsx>{`
        .experiment-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }
        
        .experiment-statistics {
          display: flex;
          gap: 32px;
          margin-bottom: 24px;
          padding: 16px;
          background-color: #f5f5f5;
          border-radius: 8px;
        }
        
        .experiment-content {
          margin-top: 24px;
        }
      `}</style>
    </div>
  );
};

export default ExperimentPage; 