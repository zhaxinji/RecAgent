import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Form, 
  Input, 
  Button, 
  Select, 
  Typography, 
  Divider, 
  Space, 
  Tag, 
  Spin,
  List,
  Collapse,
  Steps,
  Badge,
  Alert,
  Modal,
  message,
  Table,
  Result
} from 'antd';
import { 
  SearchOutlined, 
  QuestionCircleOutlined, 
  BulbOutlined, 
  FileTextOutlined,
  RiseOutlined,
  WarningOutlined,
  ExperimentOutlined,
  SafetyCertificateOutlined,
  BookOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  PlusOutlined,
  CompassOutlined
} from '@ant-design/icons';
import { assistantApi } from '../../services/api';
import { papersAPI } from '../../services/api';
import ReactMarkdown from 'react-markdown';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { Panel } = Collapse;
const { Step } = Steps;

// 研究主题领域列表
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

// 分析角度列表
const ANALYSIS_PERSPECTIVES = [
  { value: 'theoretical', label: '理论缺口', description: '现有理论框架的局限性和扩展空间' },
  { value: 'methodological', label: '方法缺口', description: '算法和技术实现层面的问题和改进空间' },
  { value: 'application', label: '应用缺口', description: '特定场景下的适用性问题和新应用方向' },
  { value: 'evaluation', label: '评估缺口', description: '实验设计和评价指标的局限性' },
  { value: 'comprehensive', label: '综合分析', description: '全面考量各个维度的研究问题' },
];

// 组件重命名: ResearchGapFinder -> ResearchProblemIdentifier
const ResearchProblemIdentifier = () => {
  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [loadingPapers, setLoadingPapers] = useState(false);
  const [results, setResults] = useState(null);
  const [paperSelectVisible, setPaperSelectVisible] = useState(false);
  const [papers, setPapers] = useState([]);
  const [selectedPapers, setSelectedPapers] = useState([]);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [activeGap, setActiveGap] = useState(null);
  const [downloadModalVisible, setDownloadModalVisible] = useState(false);
  
  // 加载论文数据
  useEffect(() => {
    const fetchPapers = async () => {
      setLoadingPapers(true);
      try {
        const response = await papersAPI.getPapers();
        setPapers(response);
      } catch (error) {
        console.error('获取论文列表失败:', error);
        message.error('无法加载论文列表');
      } finally {
        setLoadingPapers(false);
      }
    };
    
    fetchPapers();
  }, []);
  
  // 打开论文选择模态框
  const openPaperSelect = () => {
    setPaperSelectVisible(true);
  };
  
  // 确认选择论文
  const handlePaperSelect = () => {
    form.setFieldsValue({ paper_ids: selectedPapers.map(paper => paper.id) });
    setPaperSelectVisible(false);
  };
  
  // 提交表单进行分析
  const handleSubmit = async (values) => {
    setCurrentStep(1);
    setLoading(true);
    setResults(null);
    
    try {
      // 显示正在分析的消息
      message.info('正在进行研究问题识别，可能需要一些时间...');
      
      // 调用后端API获取研究问题识别
      const response = await assistantApi.analyzeResearchGaps(
        values.domain,
        values.perspective,
        values.paper_ids,
        values.additionalContext
      );
      
      if (response) {
        console.log('研究问题识别结果:', response);
        
        // 标准化响应数据结构
        let standardizedResults = { ...response };
        
        // 如果有research_gaps字段但没有researchGaps或researchProblems字段，重命名
        if (!standardizedResults.researchProblems && !standardizedResults.researchGaps) {
          if (response.research_gaps) {
            standardizedResults.researchProblems = response.research_gaps;
          } else if (response.research_problems) {
            standardizedResults.researchProblems = response.research_problems;
          }
        } else if (!standardizedResults.researchProblems && standardizedResults.researchGaps) {
          standardizedResults.researchProblems = standardizedResults.researchGaps;
        }
        
        // 确保有researchProblems字段
        if (!standardizedResults.researchProblems) {
          standardizedResults.researchProblems = [];
        }
        
        // 标准化每个研究问题的结构
        standardizedResults.researchProblems = standardizedResults.researchProblems.map(problem => {
          const standardizedProblem = { ...problem };
          
          // 检查并标准化evidence字段
          if (!standardizedProblem.evidence) {
            standardizedProblem.evidence = [];
          } else if (!Array.isArray(standardizedProblem.evidence)) {
            standardizedProblem.evidence = [];
          }
          
          // 检查并标准化potentialDirections字段
          if (!standardizedProblem.potentialDirections) {
            if (standardizedProblem.potential_directions) {
              standardizedProblem.potentialDirections = standardizedProblem.potential_directions;
            } else {
              standardizedProblem.potentialDirections = [];
            }
          }
          
          return standardizedProblem;
        });
        
        setResults(standardizedResults);
        setCurrentStep(2);
        message.success('研究问题识别完成！');
      } else {
        throw new Error('服务器返回了空响应');
      }
    } catch (error) {
      console.error('获取研究问题识别失败:', error);
      
      let errorMessage = '分析过程出现错误';
      
      if (error.response) {
        // 服务器返回了错误状态码
        console.error('错误状态码:', error.response.status);
        console.error('错误数据:', error.response.data);
        
        if (error.response.data && error.response.data.detail) {
          errorMessage = error.response.data.detail;
        } else if (error.response.status === 404) {
          errorMessage = 'API端点不存在，请检查服务是否正常运行';
        } else if (error.response.status === 500) {
          errorMessage = '服务器内部错误，可能是AI服务暂时不可用';
        } else if (error.response.status === 403) {
          errorMessage = '没有权限执行此操作';
        } else if (error.response.status === 401) {
          errorMessage = '未授权，请重新登录';
        }
      } else if (error.request) {
        // 请求已发送但没有收到响应
        console.error('无响应:', error.request);
        errorMessage = '服务器无响应，请检查网络连接';
      } else {
        // 请求设置时出错
        console.error('请求错误:', error.message);
        errorMessage = `请求错误: ${error.message}`;
      }
      
      // 显示错误消息
      message.error(`分析失败: ${errorMessage}`);
      
      // 返回到初始步骤
      setCurrentStep(0);
    } finally {
      setLoading(false);
    }
  };
  
  // 显示研究问题详情
  const showGapDetails = (gap) => {
    setActiveGap(gap);
    setDetailModalVisible(true);
  };
  
  // 重置分析
  const handleReset = () => {
    form.resetFields();
    setResults(null);
    setCurrentStep(0);
    setActiveGap(null);
    setSelectedPapers([]);
  };
  
  // 论文选择表格列定义
  const paperColumns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (text) => <span style={{ fontWeight: 'bold' }}>{text}</span>,
    },
    {
      title: '作者',
      dataIndex: 'authors',
      key: 'authors',
      render: (authors) => (Array.isArray(authors) ? authors.join(', ') : authors),
    },
    {
      title: '年份',
      dataIndex: 'publication_year',
      key: 'publication_year',
      width: 100,
    },
    {
      title: '发布于',
      dataIndex: 'publication',
      key: 'publication',
      width: 200,
    }
  ];
  
  // 论文选择表格的行选择配置
  const rowSelection = {
    selectedRowKeys: selectedPapers.map(paper => paper.id),
    onChange: (selectedRowKeys, selectedRows) => {
      setSelectedPapers(selectedRows);
    },
  };
  
  // 显示已选论文信息
  const renderSelectedPapers = () => {
    if (!selectedPapers || selectedPapers.length === 0) {
      return <Alert message="未选择任何论文" type="info" showIcon />;
    }
    
    return (
      <List
        size="small"
        bordered
        dataSource={selectedPapers}
        renderItem={(paper) => (
          <List.Item>
            <span>{paper.title}</span>
            <Tag color="blue">{paper.publication_year}</Tag>
          </List.Item>
        )}
      />
    );
  };
  
  return (
    <div className="research-problem-identifier">
      <Card bordered={false}>
        <Steps current={currentStep} style={{ marginBottom: 24 }}>
          <Step title="设置参数" description="指定研究领域" icon={<QuestionCircleOutlined />} />
          <Step title="分析中" description="AI深度分析" icon={<SyncOutlined spin={loading} />} />
          <Step title="查看结果" description="研究问题识别" icon={<BulbOutlined />} />
        </Steps>
        
        {currentStep === 0 && (
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            initialValues={{
              domain: 'sequential',
              perspective: 'comprehensive',
              additionalContext: '',
              paper_ids: []
            }}
          >
            <Form.Item
              name="domain"
              label="研究领域"
              rules={[{ required: true, message: '请选择研究领域' }]}
            >
              <Select placeholder="选择推荐系统研究领域">
                {RESEARCH_DOMAINS.map(domain => (
                  <Option key={domain.value} value={domain.value}>
                    {domain.label} - {domain.description}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            
            <Form.Item
              name="perspective"
              label="分析角度"
              rules={[{ required: true, message: '请选择分析角度' }]}
            >
              <Select placeholder="选择研究问题识别角度">
                {ANALYSIS_PERSPECTIVES.map(perspective => (
                  <Option key={perspective.value} value={perspective.value}>
                    {perspective.label} - {perspective.description}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            
            <Form.Item
              label="相关论文"
              name="paper_ids"
            >
              <div>
                <Button 
                  onClick={openPaperSelect} 
                  style={{ marginBottom: 16 }}
                  icon={<PlusOutlined />}
                >
                  选择论文
                </Button>
                {renderSelectedPapers()}
              </div>
            </Form.Item>
            
            <Form.Item
              name="additionalContext"
              label="补充背景信息（可选）"
              extra="您可以提供额外的领域背景信息以进行更准确的分析"
            >
              <TextArea 
                placeholder="例如：特定的研究方向、已有的发现或技术限制等..." 
                autoSize={{ minRows: 3, maxRows: 6 }}
              />
            </Form.Item>
            
            <Form.Item>
              <Button 
                type="primary" 
                htmlType="submit" 
                icon={<SearchOutlined />}
                loading={loading}
              >
                开始分析
              </Button>
            </Form.Item>
          </Form>
        )}
        
        {currentStep === 1 && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
            <div style={{ marginTop: 24 }}>
              <Title level={4}>AI正在深入分析{form.getFieldValue('domain') && RESEARCH_DOMAINS.find(d => d.value === form.getFieldValue('domain'))?.label}领域的研究问题...</Title>
              <Paragraph>
                正在识别关键研究问题、分析文献证据、评估现有方法局限性、探索潜在研究方向，请稍候...
              </Paragraph>
            </div>
          </div>
        )}
        
        {currentStep === 2 && results && (
          <div className="analysis-results">
            <div className="results-header">
              <Alert
                message={`${results.domain}领域研究问题识别`}
                description={results.summary}
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />
            </div>

            {/* 显示Markdown格式内容 */}
            {results.markdown_content ? (
              <div className="markdown-preview">
                <ReactMarkdown>{results.markdown_content}</ReactMarkdown>
              </div>
            ) : results.researchProblems && results.researchProblems.length > 0 ? (
              <List
                itemLayout="vertical"
                dataSource={results.researchProblems}
                renderItem={(problem) => (
                  <List.Item
                    key={problem.title}
                    actions={[
                      <span key="evidence">
                        <FileTextOutlined /> 证据: {Array.isArray(problem.evidence) ? problem.evidence.length : 0}
                      </span>,
                      <span key="directions">
                        <CompassOutlined /> 潜在方向: {Array.isArray(problem.potentialDirections) ? problem.potentialDirections.length : 0}
                      </span>,
                      <Button key="view" type="link" onClick={() => showGapDetails(problem)}>
                        查看详情
                      </Button>
                    ]}
                  >
                    <List.Item.Meta
                      title={problem.title}
                      description={
                        <ReactMarkdown>{problem.description}</ReactMarkdown>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Result
                status="warning"
                title="未找到研究问题"
                subTitle={
                  <div>
                    <p>可能的原因:</p>
                    <ul>
                      <li>所选领域已经充分研究</li>
                      <li>未提供足够的论文或背景信息</li>
                      <li>系统处理过程中出现问题</li>
                    </ul>
                    <p>建议尝试:</p>
                    <ul>
                      <li>选择不同的研究领域或角度</li>
                      <li>提供更多相关论文</li>
                      <li>添加更具体的背景信息</li>
                    </ul>
                  </div>
                }
              />
            )}
            
            <Divider />
            <Space>
              <Button onClick={handleReset}>重新分析</Button>
              <Button type="primary" onClick={() => setDownloadModalVisible(true)}>
                导出分析结果
              </Button>
            </Space>
          </div>
        )}
      </Card>
      
      {/* 论文选择模态框 */}
      <Modal
        title="选择相关论文"
        open={paperSelectVisible}
        onOk={handlePaperSelect}
        onCancel={() => setPaperSelectVisible(false)}
        width={800}
        okText="确认选择"
        cancelText="取消"
      >
        <Table
          rowKey="id"
          dataSource={papers}
          columns={paperColumns}
          rowSelection={rowSelection}
          loading={loadingPapers}
          pagination={{ pageSize: 5 }}
          size="small"
        />
      </Modal>
      
      {/* 研究问题详情模态框 */}
      <Modal
        title={activeGap ? activeGap.title : "研究问题详情"}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {activeGap && (
          <>
            <Paragraph>
              <Text strong>描述: </Text>
              <ReactMarkdown>{activeGap.description}</ReactMarkdown>
            </Paragraph>
            
            {Array.isArray(activeGap.evidence) && activeGap.evidence.length > 0 && (
              <>
                <Divider orientation="left">支持证据</Divider>
                <List
                  dataSource={activeGap.evidence}
                  renderItem={(item) => (
                    <List.Item>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Text type="secondary">{item.reference || item.source || '未指定来源'}</Text>
                        <ReactMarkdown>{item.content || item.text || '未提供内容'}</ReactMarkdown>
                      </Space>
                    </List.Item>
                  )}
                />
              </>
            )}
            
            {Array.isArray(activeGap.potentialDirections) && activeGap.potentialDirections.length > 0 && (
              <>
                <Divider orientation="left">潜在研究方向</Divider>
                <List
                  dataSource={Array.isArray(activeGap.potentialDirections) ? activeGap.potentialDirections : []}
                  renderItem={(item) => (
                    <List.Item>
                      {typeof item === 'string' ? (
                        <Paragraph>
                          <BulbOutlined style={{ marginRight: 8, color: '#1890ff' }} />
                          <ReactMarkdown>{item}</ReactMarkdown>
                        </Paragraph>
                      ) : (
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Paragraph>
                            <BulbOutlined style={{ marginRight: 8, color: '#1890ff' }} />
                            <Text strong>{item.direction || '未命名方向'}</Text>
                          </Paragraph>
                          {item.approach && (
                            <Paragraph style={{ marginLeft: 24 }}>
                              <ReactMarkdown>{item.approach}</ReactMarkdown>
                            </Paragraph>
                          )}
                        </Space>
                      )}
                    </List.Item>
                  )}
                />
              </>
            )}
          </>
        )}
      </Modal>
      
      <style jsx="true">{`
        .research-problem-identifier {
          max-width: 1000px;
          margin: 0 auto;
        }
        
        .analysis-results {
          padding: 16px 0;
        }
        
        .results-header {
          margin-bottom: 24px;
        }
        
        .references {
          max-height: 300px;
          overflow-y: auto;
          padding: 0 16px;
          background-color: #f9f9f9;
          border-radius: 4px;
        }
        
        .markdown-preview {
          background-color: #fff;
          padding: 16px;
          border-radius: 4px;
          box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
      `}</style>
    </div>
  );
};

export default ResearchProblemIdentifier; 