import React, { useState } from 'react';
import { 
  Layout,
  Tabs,
  message,
  Typography,
  Card,
  Button,
  Space
} from 'antd';
import { 
  BulbOutlined,
  QuestionCircleOutlined,
  ExperimentOutlined,
  EditOutlined,
  MessageOutlined,
  HistoryOutlined
} from '@ant-design/icons';
import ResearchGapFinder from './ResearchGapFinder';
import InnovationGenerator from './InnovationGenerator';
import ExperimentDesigner from './ExperimentDesigner';
import { useAssistant } from '../../contexts/AssistantContext';

const { Title, Paragraph } = Typography;

const ResearchAssistant = () => {
  // 使用AssistantContext
  const { 
    sessions, 
    currentSession, 
    setCurrentSession, 
    loading, 
    createSession, 
    deleteSession 
  } = useAssistant();
  
  // 本地状态管理
  const [activeTab, setActiveTab] = useState('research_gap');  // 默认选中研究问题识别
  const [showHistory, setShowHistory] = useState(false);

  // 默认选中的标签页 - "研究问题识别"
  const DEFAULT_ACTIVE_TAB = 'research_gap';

  // 创建新会话
  const handleCreateSession = async () => {
    try {
      const newSession = await createSession({
        title: `推荐系统研究 ${new Date().toLocaleString('zh-CN')}`,
        context: { description: '新的研究助手会话' },
        session_type: activeTab
      });
      
      setCurrentSession(newSession);
      message.success('已创建新会话');
    } catch (error) {
      message.error('创建会话失败');
      console.error(error);
    }
  };

  // 删除会话
  const handleDeleteSession = async (sessionId) => {
    try {
      await deleteSession(sessionId);
      message.success('会话已删除');
    } catch (error) {
      message.error('删除会话失败');
      console.error(error);
    }
  };

  // 创建标签页数据
  const tabs = [
    {
      key: 'research_gap',
      label: '研究问题识别',
      icon: <QuestionCircleOutlined />
    },
    {
      key: 'innovation',
      label: '创新点生成',
      icon: <BulbOutlined />
    },
    {
      key: 'experiment',
      label: '实验设计',
      icon: <ExperimentOutlined />
    }
  ];

  // 渲染会话历史
  const renderSessionHistory = () => {
    if (!showHistory) return null;
    
    return (
      <Card className="session-history-card">
        <Title level={4}>会话历史</Title>
        {loading.sessions ? (
          <div className="center-content">
            <Paragraph>加载会话历史...</Paragraph>
          </div>
        ) : sessions.length === 0 ? (
          <div className="center-content">
            <Paragraph>暂无会话历史</Paragraph>
            <Button type="primary" onClick={handleCreateSession}>创建新会话</Button>
          </div>
        ) : (
          <ul className="session-list">
            {sessions.map(session => (
              <li 
                key={session.id} 
                className={`session-item ${currentSession?.id === session.id ? 'selected' : ''}`}
                onClick={() => setCurrentSession(session)}
              >
                <div className="session-item-content">
                  <div className="session-item-header">
                    <strong>{session.title}</strong>
                    <small>{new Date(session.created_at).toLocaleString('zh-CN')}</small>
                  </div>
                  <p className="session-description">
                    {session.context?.description || '研究助手会话'}
                  </p>
                </div>
                <Button 
                  type="text" 
                  danger 
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteSession(session.id);
                  }}
                >
                  删除
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    );
  };

  // 切换标签
  const handleTabChange = (key) => {
    setActiveTab(key);
  };

  // 渲染当前选中的功能面板
  const renderTabContent = () => {
    switch (activeTab) {
      case 'research_gap':
        return <ResearchGapFinder />;
      case 'innovation':
        return <InnovationGenerator />;
      case 'experiment':
        return <ExperimentDesigner isDisabled={true} disabledMessage="由于考虑到自动化实验验证，暂未开发，敬请期待" />;
      default:
        return <div>未找到对应功能</div>;
    }
  };

  return (
    <Layout className="research-assistant-container">
      <div className="research-assistant-header">
        <Space>
          <Button 
            type="text" 
            icon={<HistoryOutlined />} 
            onClick={() => setShowHistory(!showHistory)}
          >
            {showHistory ? '隐藏历史' : '会话历史'}
          </Button>
          
          <Button 
            type="primary" 
            icon={<MessageOutlined />} 
            onClick={handleCreateSession}
          >
            新建会话
          </Button>
        </Space>
      </div>
      
      <div className="research-assistant-content">
        {showHistory && (
          <div className="session-history-panel">
            {renderSessionHistory()}
          </div>
        )}
        
        <div className={`main-content ${showHistory ? 'with-history' : ''}`}>
          <Tabs 
            activeKey={activeTab} 
            onChange={handleTabChange}
            className="feature-tabs"
            type="card"
            items={tabs.map(tab => ({
              key: tab.key,
              label: (
                <span>
                  {tab.icon} {tab.label}
                </span>
              )
            }))}
          />
          
          <div className="tab-content">
            {renderTabContent()}
          </div>
        </div>
      </div>
      
      <style jsx>{`
        .research-assistant-container {
          min-height: calc(100vh - 220px);
          background: transparent;
          display: flex;
          flex-direction: column;
        }
        
        .research-assistant-header {
          margin-bottom: 16px;
          display: flex;
          justify-content: flex-end;
        }
        
        .research-assistant-content {
          display: flex;
          flex: 1;
          gap: 16px;
        }
        
        .session-history-panel {
          width: 300px;
          flex-shrink: 0;
        }
        
        .main-content {
          flex: 1;
        }
        
        .main-content.with-history {
          max-width: calc(100% - 316px);
        }
        
        .main-tabs {
          width: 100%;
        }
        
        .session-history-card {
          height: 100%;
        }
        
        .center-content {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 24px 0;
        }
        
        .session-list {
          list-style-type: none;
          padding: 0;
          margin: 0;
          max-height: 500px;
          overflow-y: auto;
        }
        
        .session-item {
          padding: 12px;
          border-radius: 6px;
          margin-bottom: 8px;
          border: 1px solid #f0f0f0;
          cursor: pointer;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .session-item:hover {
          background-color: #f5f5f5;
        }
        
        .session-item.selected {
          background-color: #e6f7ff;
          border-color: #91d5ff;
        }
        
        .session-item-content {
          flex: 1;
        }
        
        .session-item-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 4px;
        }
        
        .session-description {
          color: #666;
          font-size: 12px;
          margin: 0;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
      `}</style>
    </Layout>
  );
};

export default ResearchAssistant; 