import React, { useEffect, useState, Component } from 'react';
import { Row, Col, Card, Typography, Tabs, Button, Space, Spin, Modal, List, Divider, message } from 'antd';
import { 
  FileTextOutlined, 
  EditOutlined, 
  PlusOutlined, 
  FileAddOutlined,
  HistoryOutlined
} from '@ant-design/icons';
import { useWriting } from '../contexts/WritingContext';
import WritingAssistant from '../components/research-assistant/WritingAssistant';

const { Title, Paragraph } = Typography;
const { TabPane } = Tabs;

// 创建错误边界组件
class TabErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Tab渲染错误:', error, errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      // 显示友好的错误信息
      return (
        <div style={{ padding: '24px', textAlign: 'center' }}>
          <FileTextOutlined style={{ fontSize: 48, color: '#ff4d4f', marginBottom: 16 }} />
          <Typography.Title level={4}>加载出错了</Typography.Title>
          <Paragraph>文档列表加载过程中发生错误</Paragraph>
          <div style={{ marginTop: 16 }}>
            <Button 
              type="primary" 
              onClick={() => {
                this.setState({ hasError: false, error: null, errorInfo: null });
                // 如果有提供重试函数，则调用它
                if (this.props.onRetry) {
                  this.props.onRetry();
                }
              }}
            >
              重试加载
            </Button>
            <Button 
              style={{ marginLeft: 8 }}
              onClick={() => window.location.reload()}
            >
              刷新页面
            </Button>
          </div>
          {process.env.NODE_ENV !== 'production' && this.state.error && (
            <div style={{ marginTop: 16, textAlign: 'left', overflow: 'auto', maxHeight: 200 }}>
              <details>
                <summary style={{ cursor: 'pointer', color: '#1890ff' }}>错误详情</summary>
                <pre style={{ textAlign: 'left', color: '#ff4d4f', fontSize: 12 }}>
                  {this.state.error.toString()}
                  {this.state.errorInfo && this.state.errorInfo.componentStack}
                </pre>
              </details>
            </div>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

const WritingPage = ({ user }) => {
  // 使用WritingContext
  const { 
    documents,
    currentDocument,
    documentContent,
    loading,
    setDocumentContent,
    templates,
    fetchDocuments,
    fetchDocumentContent,
    createDocument,
    saveDocument,
    deleteDocument
  } = useWriting();
  
  // 本地状态
  const [activeTab, setActiveTab] = useState('write');
  const [isCreating, setIsCreating] = useState(false);
  // 添加历史记录状态
  const [docHistory, setDocHistory] = useState([]);

  // 首次加载时获取数据
  useEffect(() => {
    if (user) {
      fetchDocuments().catch(err => {
        console.error('获取文档列表失败:', err);
        message.error('获取文档列表失败，请刷新页面重试');
      });
    }
  }, [user]);

  // 处理新建文档
  const handleCreateDocument = async () => {
    try {
      // 直接使用标准研究论文模板，不显示选择对话框
      setIsCreating(true);
      message.loading('正在创建标准研究论文...');
      
      // 查找标准研究论文模板
      const standardTemplate = templates.find(t => t.id === 'standard-research') || templates[0];
      
      if (!standardTemplate) {
        message.error('无法创建文档：未找到有效的论文模板');
        return;
      }
      
      const result = await createDocument(standardTemplate);
      
      if (result.success) {
        message.success('文档创建成功');
        setActiveTab('write');
        
        // 添加创建文档的历史记录
        const newHistoryItem = {
          user: '当前用户',
          action: `创建了新${standardTemplate.name}文档`,
          timestamp: new Date().getTime()
        };
        setDocHistory(prev => [newHistoryItem, ...prev]);
      } else {
        message.error(result.error || '创建文档失败，请重试');
      }
    } catch (error) {
      console.error('创建文档过程中发生异常:', error);
      message.error('创建过程中发生错误，请重试或联系管理员');
    } finally {
      setIsCreating(false);
    }
  };

  // 打开文档
  const handleOpenDocument = async (docId) => {
    try {
      console.log(`尝试打开文档，ID: ${docId}`);
      
      // 先切换到写作区以显示加载状态
      setActiveTab('write');
      
      // 添加超时处理
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('获取文档超时')), 15000);
      });
      
      // 使用Promise.race实现超时控制
      const result = await Promise.race([
        fetchDocumentContent(docId),
        timeoutPromise
      ]);
      
      if (result) {
        console.log('文档加载成功');
      } else {
        // fetchDocumentContent已经显示错误消息
        console.warn('文档加载失败或返回空数据');
        
        // 尝试自动重试一次
        setTimeout(async () => {
          try {
            console.log('正在重试获取文档...');
            message.info('重新尝试获取文档...');
            await fetchDocumentContent(docId);
          } catch (retryError) {
            console.error('重试获取文档失败:', retryError);
            message.error('多次尝试后仍无法加载文档，请稍后再试');
          }
        }, 2000);
      }
    } catch (error) {
      console.error('打开文档过程中发生异常:', error);
      
      if (error.message === '获取文档超时') {
        message.error('获取文档超时，请检查网络连接后重试');
      } else {
        message.error(`打开文档失败: ${error.message || '未知错误'}`);
      }
      
      // 如果发生错误，先切换回文档列表
      setActiveTab('documents');
    }
  };

  // 保存当前文档
  const handleSaveDocument = async () => {
    try {
      await saveDocument();
      
      // 添加保存文档的历史记录
      const newHistoryItem = {
        user: '当前用户',
        action: `保存了文档 "${currentDocument?.title || '未命名文档'}"`,
        timestamp: new Date().getTime()
      };
      setDocHistory(prev => [newHistoryItem, ...prev]);
    } catch (error) {
      console.error('保存文档失败:', error);
    }
  };

  // 处理删除文档
  const handleDeleteDocument = async (docId, docTitle) => {
    try {
      // 弹出确认对话框
      const confirmed = await Modal.confirm({
        title: '确认删除',
        content: `确定要删除 "${docTitle}" 吗？此操作不可恢复。`,
        okText: '确认删除',
        okType: 'danger',
        cancelText: '取消',
        centered: true
      });
      
      if (confirmed) {
        await deleteDocument(docId);
        message.success('文档已成功删除');
        
        // 添加删除文档的历史记录
        const newHistoryItem = {
          user: '当前用户',
          action: `删除了文档 "${docTitle}"`,
          timestamp: new Date().getTime()
        };
        setDocHistory(prev => [newHistoryItem, ...prev]);
      }
    } catch (error) {
      console.error('删除文档失败:', error);
      message.error('删除文档失败，请重试');
    }
  };

  // 渲染文档列表
  const renderDocumentList = () => {
    // 如果正在加载，显示加载状态
    if (loading.documents) {
      return (
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <Spin size="large" tip="正在加载文档..." />
        </div>
      );
    }

    // 如果documents不存在或为空，显示空状态
    if (!documents || documents.length === 0) {
      return (
        <div className="empty-state">
          <FileTextOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />
          <Paragraph>暂无文档</Paragraph>
          <Button 
            type="primary" 
            icon={<PlusOutlined />}
            onClick={handleCreateDocument}
          >
            创建新文档
          </Button>
        </div>
      );
    }

    // 渲染文档列表
    return (
      <List
        itemLayout="horizontal"
        dataSource={documents}
        renderItem={doc => {
          // 数据验证：确保每一项文档都有所需属性，避免渲染错误
          if (!doc || !doc.id || !doc.title) {
            console.error('无效的文档数据:', doc);
            return null;
          }
          
          // 确保所有需要的字段都有默认值
          const safeDoc = {
            ...doc,
            title: doc.title || '未命名文档',
            updatedAt: doc.updatedAt || Date.now(),
            sections: Array.isArray(doc.sections) ? doc.sections : [],
            collaborators: Array.isArray(doc.collaborators) ? doc.collaborators : []
          };

          return (
            <List.Item
              key={safeDoc.id}
              actions={[
                <Button 
                  type="link" 
                  onClick={() => handleOpenDocument(safeDoc.id)}
                >
                  打开
                </Button>,
                <Button 
                  type="link" 
                  danger
                  onClick={() => handleDeleteDocument(safeDoc.id, safeDoc.title)}
                >
                  删除
                </Button>
              ]}
            >
              <List.Item.Meta
                avatar={<FileTextOutlined style={{ fontSize: 24 }} />}
                title={<a onClick={() => handleOpenDocument(safeDoc.id)}>{safeDoc.title}</a>}
                description={
                  <Space split={<Divider type="vertical" />}>
                    <span>
                      更新于 {new Date(safeDoc.updatedAt).toLocaleString('zh-CN')}
                    </span>
                    <span>
                      {safeDoc.sections.length}个章节
                    </span>
                    <span>
                      {safeDoc.collaborators.length}位协作者
                    </span>
                  </Space>
                }
              />
            </List.Item>
          );
        }}
      />
    );
  };

  return (
    <div>
      <Row gutter={[24, 24]}>
        <Col xs={24}>
          <Card className="card" style={{ minHeight: 'calc(100vh - 200px)' }}>
            <div className="writing-header">
              <Title level={2}>智能论文写作</Title>
              
              <Space>
                {activeTab === 'write' && currentDocument && (
                  <Button 
                    onClick={handleSaveDocument}
                    loading={loading.saveDocument}
                  >
                    保存文档
                  </Button>
                )}
                
                <Button 
                  type="primary" 
                  icon={<PlusOutlined />}
                  onClick={handleCreateDocument}
                >
                  新建文档
                </Button>
              </Space>
            </div>
            
            <Tabs activeKey={activeTab} onChange={setActiveTab}>
              <TabPane tab={<><EditOutlined /> 写作区</>} key="write">
                {loading.document ? (
                  <div className="loading-container" style={{ textAlign: 'center', padding: '40px 0' }}>
                    <Spin size="large" tip="正在加载文档内容..." />
                    <div style={{ marginTop: 20 }}>
                      <Button 
                        onClick={() => setActiveTab('documents')}
                        type="link"
                      >
                        取消并返回文档列表
                      </Button>
                    </div>
                  </div>
                ) : currentDocument ? (
                  <WritingAssistant />
                ) : (
                  <div className="empty-state">
                    <FileTextOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />
                    <Paragraph>请从文档列表中选择一篇文档或创建新文档</Paragraph>
                    <Space>
                      <Button 
                        type="primary" 
                        onClick={() => setActiveTab('documents')}
                      >
                        打开文档列表
                      </Button>
                      <Button
                        onClick={handleCreateDocument}
                      >
                        创建新文档
                      </Button>
                    </Space>
                  </div>
                )}
              </TabPane>
              
              <TabPane tab={<><FileTextOutlined /> 文档列表</>} key="documents">
                <TabErrorBoundary onRetry={fetchDocuments}>
                  {renderDocumentList()}
                </TabErrorBoundary>
              </TabPane>
              
              <TabPane tab={<><HistoryOutlined /> 历史记录</>} key="history">
                {currentDocument ? (
                  <List
                    itemLayout="horizontal"
                    dataSource={docHistory.length > 0 ? docHistory : [
                      // 模拟历史记录数据
                      {
                        user: '当前用户',
                        action: `创建了文档 "${currentDocument.title}"`,
                        timestamp: currentDocument.createdAt || Date.now() - 86400000
                      },
                      {
                        user: '当前用户',
                        action: `修改了文档 "${currentDocument.title}" 的内容`,
                        timestamp: Date.now() - 3600000
                      },
                      {
                        user: '当前用户',
                        action: `保存了文档 "${currentDocument.title}"`,
                        timestamp: Date.now() - 1800000
                      }
                    ]}
                    renderItem={historyItem => (
                      <List.Item>
                        <List.Item.Meta
                          title={historyItem.action}
                          description={
                            <Space split={<Divider type="vertical" />}>
                              <span>{historyItem.user}</span>
                              <span>
                                {new Date(historyItem.timestamp).toLocaleString('zh-CN')}
                              </span>
                            </Space>
                          }
                        />
                      </List.Item>
                    )}
                  />
                ) : (
                  <div className="empty-state">
                    <HistoryOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />
                    <Paragraph>请先选择一篇文档查看历史记录</Paragraph>
                  </div>
                )}
              </TabPane>
            </Tabs>
          </Card>
        </Col>
      </Row>
      
      <style jsx>{`
        .writing-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }
        
        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 64px 0;
          text-align: center;
        }
        
        .template-item {
          cursor: pointer;
          padding: 12px;
          border-radius: 6px;
          margin-bottom: 8px;
          border: 1px solid #f0f0f0;
        }
        
        .template-item:hover {
          background-color: #f5f5f5;
        }
        
        .template-item.selected {
          background-color: #e6f7ff;
          border-color: #91d5ff;
        }
        
        .template-sections {
          color: #888;
          font-size: 12px;
          max-width: 300px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
      `}</style>
    </div>
  );
};

export default WritingPage; 