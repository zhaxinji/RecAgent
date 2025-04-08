import React, { useState, useEffect } from 'react';
import { 
  Layout, 
  Card, 
  Typography, 
  Tabs, 
  Dropdown, 
  Menu, 
  Button, 
  Space, 
  Divider,
  List,
  Avatar,
  message
} from 'antd';
import { 
  RobotOutlined, 
  MessageOutlined, 
  QuestionCircleOutlined, 
  BulbOutlined,
  ExperimentOutlined,
  FormOutlined,
  HistoryOutlined,
  DeleteOutlined,
  MoreOutlined,
  PlusOutlined
} from '@ant-design/icons';

import ResearchAssistant from './ResearchAssistant';
import ResearchGapFinder from './ResearchGapFinder';
import InnovationGenerator from './InnovationGenerator';
import ConceptExplainer from './ConceptExplainer';

import { assistantApi } from '../../services/api';

const { Content } = Layout;
const { Title, Text } = Typography;
const { TabPane } = Tabs;

const AssistantPage = () => {
  const [activeTab, setActiveTab] = useState('assistant');
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentSession, setCurrentSession] = useState(null);
  
  // 获取会话列表
  const fetchSessions = async () => {
    setLoading(true);
    try {
      const response = await assistantApi.getSessions();
      setSessions(response.items || []);
    } catch (error) {
      console.error('获取会话列表失败:', error);
      message.error('获取会话列表失败');
    } finally {
      setLoading(false);
    }
  };
  
  // 删除会话
  const handleDeleteSession = async (sessionId) => {
    try {
      await assistantApi.deleteSession(sessionId);
      message.success('会话已删除');
      // 更新会话列表
      fetchSessions();
      
      // 如果删除的是当前会话，清除当前会话
      if (currentSession && currentSession.id === sessionId) {
        setCurrentSession(null);
      }
    } catch (error) {
      console.error('删除会话失败:', error);
      message.error('删除会话失败');
    }
  };
  
  // 创建新会话
  const handleCreateSession = async () => {
    try {
      const newSession = await assistantApi.createSession({
        title: '新建会话',
        type: 'general'
      });
      
      // 更新会话列表
      fetchSessions();
      
      // 设置当前会话
      setCurrentSession(newSession);
      message.success('已创建新会话');
    } catch (error) {
      console.error('创建会话失败:', error);
      message.error('创建会话失败');
    }
  };
  
  // 选择会话
  const handleSelectSession = async (sessionId) => {
    try {
      const session = await assistantApi.getSession(sessionId);
      setCurrentSession(session);
    } catch (error) {
      console.error('获取会话详情失败:', error);
      message.error('获取会话详情失败');
    }
  };
  
  // 初始化加载会话列表
  useEffect(() => {
    fetchSessions();
  }, []);
  
  // 会话操作菜单
  const sessionMenu = (sessionId) => (
    <Menu>
      <Menu.Item 
        key="delete" 
        icon={<DeleteOutlined />}
        onClick={() => handleDeleteSession(sessionId)}
      >
        删除会话
      </Menu.Item>
    </Menu>
  );
  
  const renderSessionList = () => (
    <Card 
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>会话历史</span>
          <Button 
            type="primary" 
            icon={<PlusOutlined />} 
            size="small"
            onClick={handleCreateSession}
          >
            新建会话
          </Button>
        </div>
      }
      style={{ height: '100%' }}
    >
      <List
        loading={loading}
        dataSource={sessions}
        renderItem={item => (
          <List.Item
            key={item.id}
            actions={[
              <Dropdown overlay={sessionMenu(item.id)} trigger={['click']}>
                <Button type="text" icon={<MoreOutlined />} />
              </Dropdown>
            ]}
            style={{ 
              cursor: 'pointer',
              backgroundColor: currentSession && currentSession.id === item.id ? '#f0f8ff' : 'transparent'
            }}
            onClick={() => handleSelectSession(item.id)}
          >
            <List.Item.Meta
              avatar={<Avatar icon={<MessageOutlined />} />}
              title={item.title || '未命名会话'}
              description={
                <div>
                  <Text type="secondary">
                    {new Date(item.created_at).toLocaleDateString()} · {item.message_count || 0} 条消息
                  </Text>
                </div>
              }
            />
          </List.Item>
        )}
        locale={{
          emptyText: <div style={{ padding: '20px 0', textAlign: 'center' }}>
            <Text type="secondary">暂无会话历史</Text>
            <div style={{ marginTop: 16 }}>
              <Button type="primary" onClick={handleCreateSession}>
                创建新会话
              </Button>
            </div>
          </div>
        }}
      />
    </Card>
  );
  
  return (
    <Content className="site-layout-content">
      <div style={{ padding: '24px 0' }}>
        <Title level={2}>
          <Space>
            <RobotOutlined />
            <span>研究助手</span>
          </Space>
        </Title>
        <Divider />
        
        <Tabs 
          activeKey={activeTab} 
          onChange={setActiveTab}
          tabPosition="top"
          size="large"
          className="assistant-tabs"
        >
          <TabPane 
            tab={
              <span>
                <MessageOutlined />
                智能助手
              </span>
            } 
            key="assistant"
          >
            <div className="assistant-content">
              <div className="session-list" style={{ width: 300 }}>
                {renderSessionList()}
              </div>
              <div className="chat-container" style={{ flex: 1 }}>
                <ResearchAssistant 
                  currentSession={currentSession}
                  onSessionCreated={fetchSessions}
                  onSessionUpdated={fetchSessions}
                />
              </div>
            </div>
          </TabPane>
          
          <TabPane 
            tab={
              <span>
                <BulbOutlined />
                研究空白分析
              </span>
            } 
            key="gaps"
          >
            <ResearchGapFinder />
          </TabPane>
          
          <TabPane 
            tab={
              <span>
                <ExperimentOutlined />
                创新思路生成
              </span>
            } 
            key="innovation"
          >
            <InnovationGenerator />
          </TabPane>
          
          <TabPane 
            tab={
              <span>
                <QuestionCircleOutlined />
                概念解释
              </span>
            } 
            key="concept"
          >
            <ConceptExplainer />
          </TabPane>
        </Tabs>
      </div>
    </Content>
  );
};

export default AssistantPage; 