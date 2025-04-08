import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Typography, Tabs, Spin } from 'antd';
import LiteratureSearch from '../components/literature/LiteratureSearch';
import PaperAnalyzer from '../components/literature/PaperAnalyzer';
import LiteratureManagement from '../components/literature/LiteratureManagement';
import { useLiterature } from '../contexts/LiteratureContext';

const { Title } = Typography;

const LiteraturePage = ({ user }) => {
  // 添加状态来控制当前标签页
  const [activeTab, setActiveTab] = useState('search');
  
  // 使用LiteratureContext
  const { 
    loading, 
    papers, 
    fetchPapers, 
    fetchTags
  } = useLiterature();

  // 首次加载时获取数据
  useEffect(() => {
    if (user) {
      console.log('LiteraturePage: 尝试获取数据', { activeTab });
      fetchPapers();
      fetchTags();
    }
  }, [user, activeTab]);

  // 处理标签切换
  const handleTabChange = (key) => {
    console.log('LiteraturePage: 切换标签到', key);
    setActiveTab(key);
  };

  const items = [
    {
      key: 'search',
      label: '文献检索',
      children: <LiteratureSearch />
    },
    {
      key: 'analyze',
      label: '论文分析',
      children: <PaperAnalyzer />
    },
    {
      key: 'manage',
      label: '文献管理',
      children: <LiteratureManagement key="literature-management-tab" />
    }
  ];

  // 如果正在加载，显示加载状态
  if (loading.papers && papers.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '50px 0' }}>
        <Spin size="large" tip="正在加载文献数据..." />
      </div>
    );
  }

  return (
    <div>
      <Row gutter={[24, 24]}>
        <Col xs={24}>
          <Card className="card" style={{ minHeight: 'calc(100vh - 200px)' }}>
            <div className="literature-header">
              <Title level={2}>文献中心</Title>
            </div>
            <Tabs activeKey={activeTab} onChange={handleTabChange} items={items} destroyInactiveTabPane={false} />
          </Card>
        </Col>
      </Row>

      <style jsx>{`
        .literature-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }
        
        .literature-stats {
          display: flex;
          gap: 16px;
        }
        
        .stat-item {
          background-color: #f5f5f5;
          padding: 8px 12px;
          border-radius: 4px;
        }
      `}</style>
    </div>
  );
};

export default LiteraturePage; 