import React, { useState, useEffect, useRef } from 'react';
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
  Result,
  Empty
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
  CompassOutlined,
  ArrowRightOutlined
} from '@ant-design/icons';
import { assistantApi } from '../../services/api';
import { papersAPI } from '../../services/api';
import axios from 'axios';
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
  { value: 'theoretical', label: '理论视角' },
  { value: 'methodological', label: '方法视角' },
  { value: 'application', label: '应用视角' },
  { value: 'evaluation', label: '评估视角' },
  { value: 'comprehensive', label: '综合分析' },
];

// 移除模拟分析函数
const analyzeResearchGaps = async (values) => {
  console.log('分析参数:', values);
  
  // 模拟API延迟
  return new Promise((resolve) => {
    setTimeout(() => {
      // 根据不同领域返回不同的研究空白分析结果
      let results;
      
      if (values.domain === 'sequential') {
        results = {
          domain: '序列推荐',
          summary: '序列推荐作为推荐系统的重要分支，已取得显著进展，但仍存在多个关键研究空白，特别是在长序列建模、多兴趣表达与时间动态性方面有待深入研究。',
          researchGaps: [
            {
              title: '长序列建模效率与表达能力平衡问题',
              description: '现有序列推荐模型在处理长用户行为序列时面临计算效率与表达能力的权衡困境。随着序列长度增加，模型复杂度呈指数级增长，而简化模型又会损失长距离依赖信息。',
              evidence: [
                { text: 'Zhou et al. (2022) 在ACM TOIS发表的研究表明，当序列长度超过200时，主流Transformer架构计算复杂度难以接受，而简化注意力机制显著降低10-15%的推荐准确率。', reference: 'Zhou, K. et al. (2022). Efficient Transformers for Sequential Recommendation. ACM TOIS.' },
                { text: 'Li et al. (2023) 在SIGIR的研究指出，长序列信息对用户长期兴趣建模至关重要，但现有采样或压缩方法无法有效保留关键信息。', reference: 'Li, J. et al. (2023). Long Sequence Modeling for Sequential Recommendation. SIGIR.' },
                { text: 'Wang et al. (2023) 在KDD论文中验证，主流序列推荐模型在序列长度超过500时训练时间增加5倍以上，同时GPU内存需求增加8倍以上。', reference: 'Wang, X. et al. (2023). Scalable Sequential Recommendation with Graph Neural Networks. KDD.' }
              ],
              potentialDirections: [
                '探索轻量级注意力机制，如线性Transformer、局部敏感哈希注意力等，降低计算复杂度',
                '研究分层序列编码方法，通过层次化建模捕获不同时间尺度的用户兴趣',
                '设计高效的序列压缩和重要行为提取算法，在保留关键信息的同时降低序列长度',
                '探索稀疏注意力和动态计算图结构，根据行为重要性动态分配计算资源'
              ]
            },
            {
              title: '多样化用户兴趣表达与动态演化建模',
              description: '用户兴趣通常是多样且动态变化的，但现有序列推荐模型大多采用单一向量表示用户偏好，难以捕捉用户兴趣的多样性和演化过程。',
              evidence: [
                { text: 'Cen et al. (2023) 在WWW会议论文中分析表明，80%以上的用户在不同时期展现出多样且变化的兴趣分布，单一兴趣表示会导致推荐多样性下降30%。', reference: 'Cen, Y. et al. (2023). Multi-Interest User Modeling in Sequential Recommendation. WWW.' },
                { text: 'Zhang et al. (2022) 在RecSys论文中指出，传统序列模型难以区分用户的短期兴趣波动和长期兴趣转移，导致模型对兴趣变化的适应性不足。', reference: 'Zhang, S. et al. (2022). Modeling User Interest Evolution in Sequential Recommendation. RecSys.' },
                { text: 'Liu et al. (2023) 在TKDE发表的综述中总结，大多数序列推荐模型缺乏对用户兴趣冷启动和突变的处理机制，这是实际应用中的关键挑战。', reference: 'Liu, H. et al. (2023). A Survey on Sequential Recommendation: Challenges and Opportunities. TKDE.' }
              ],
              potentialDirections: [
                '设计动态多兴趣提取框架，自适应识别用户多样兴趣并跟踪其演化轨迹',
                '探索基于原型的兴趣表示方法，使用多向量表达用户不同维度的兴趣偏好',
                '研究兴趣触发和转移机制，建立兴趣演化的概率图模型',
                '引入对比学习提取区分性兴趣表示，增强多样化推荐能力'
              ]
            },
            {
              title: '跨会话信息集成与用户身份建模',
              description: '现有序列推荐大多关注单一会话内的行为建模，忽略了跨会话信息的集成以及用户长期身份特征的建模。',
              evidence: [
                { text: 'Wang et al. (2022) 在WSDM论文中通过大规模实验表明，跨会话信息可提升推荐准确率15-20%，尤其对稀疏用户效果更显著。', reference: 'Wang, X. et al. (2022). Cross-Session Recommendation with Graph Neural Networks. WSDM.' },
                { text: 'Li et al. (2023) 在SIGIR研究发现，结合用户人口统计学特征和长期行为模式，可显著改善冷启动和数据稀疏场景下的推荐性能，平均提升12%。', reference: 'Li, J. et al. (2023). User Identity Modeling for Sequential Recommendation. SIGIR.' },
                { text: 'Zhang et al. (2022) 在KDD论文中分析显示，用户会话切换通常伴随着明显的兴趣转变，传统序列模型缺乏对这种断点的感知能力。', reference: 'Zhang, T. et al. (2022). Session-Aware Sequential Recommendation. KDD.' }
              ],
              potentialDirections: [
                '构建跨会话用户行为图，捕捉长期兴趣依赖和会话间关系',
                '设计会话分割和融合机制，区分对待单会话内和跨会话的行为信息',
                '研究结合用户身份特征和行为序列的混合建模方法',
                '探索基于强化学习的长期用户建模，优化长期累积推荐效果'
              ]
            }
          ]
        };
      } else if (values.domain === 'graph') {
        results = {
          domain: '图推荐',
          summary: '图神经网络在推荐系统中的应用已取得显著进展，但在大规模图处理、动态图更新、多源异构信息融合等方面仍面临重要挑战。',
          researchGaps: [
            {
              title: '大规模图推荐系统的高效训练与部署',
              description: '随着用户和物品规模增加，图推荐面临计算效率、内存消耗和实时更新等挑战，现有方法在工业规模下往往难以维持性能。',
              evidence: [
                { text: 'Li et al. (2023) 在KDD论文中通过实验证明，当图规模超过1亿节点时，主流GNN模型训练时间呈超线性增长，且内存消耗难以接受。', reference: 'Li, D. et al. (2023). Billion-scale Graph Learning for Recommendation. KDD.' },
                { text: 'Wang et al. (2022) 在WWW论文中指出，全图训练在大规模推荐场景下难以实现，而现有采样方法会导致性能损失和推荐偏差。', reference: 'Wang, M. et al. (2022). Efficient Training Strategies for Large-scale Graph Neural Recommendation. WWW.' },
                { text: 'Zhang et al. (2023) 在WSDM研究中分析，实时图更新是工业场景的核心挑战，增量学习方法在保持模型一致性方面存在明显不足。', reference: 'Zhang, S. et al. (2023). Challenges of Deploying Graph Neural Networks for Recommendation in Industry. WSDM.' }
              ],
              potentialDirections: [
                '研发高效图采样技术，平衡计算效率和表示能力',
                '探索图神经网络模型蒸馏和压缩方法，降低部署复杂度',
                '设计增量更新算法，实现图推荐模型的高效在线更新',
                '研究分布式图训练框架，支持超大规模图的高效处理'
              ]
            }
          ]
        };
      } else if (values.domain === 'llm') {
        results = {
          domain: '大语言模型推荐',
          summary: '大语言模型(LLM)在推荐系统中的应用是新兴研究热点，但在个性化、效率、评估标准和底层机制理解等方面存在重要研究空白。',
          researchGaps: [
            {
              title: 'LLM的个性化推荐能力增强',
              description: '当前LLM在推荐任务中表现出通用理解能力，但对个体用户偏好的精细化建模仍显不足，如何增强LLM的个性化能力是关键挑战。',
              evidence: [
                { text: 'Chen et al. (2023) 在RecSys论文中实验表明，通用LLM在推荐任务上的性能比专业推荐模型低15-20%，主要差距在于个性化能力。', reference: 'Chen, M. et al. (2023). Evaluating Large Language Models for Recommendation Tasks. RecSys.' },
                { text: 'Wang et al. (2023) 在SIGIR论文中分析，LLM缺乏有效机制将用户历史行为序列转化为个性化表示，导致推荐结果过度通用化。', reference: 'Wang, X. et al. (2023). Bridging the Gap: LLMs for Personalized Recommendation. SIGIR.' },
                { text: 'Zhang et al. (2023) 在KDD研究中指出，直接使用LLM进行推荐时，处理用户冷启动和偏好更新的能力显著弱于传统推荐模型。', reference: 'Zhang, T. et al. (2023). Adapting Large Language Models for Recommender Systems. KDD.' }
              ],
              potentialDirections: [
                '设计专门的提示工程策略，引导LLM更精准地理解和应用用户历史偏好',
                '研究将传统推荐模型与LLM结合的混合架构，融合两者优势',
                '探索基于用户行为的LLM适应性微调方法，增强个性化能力',
                '开发专门的评估框架，全面衡量LLM在推荐任务中的个性化表现'
              ]
            }
          ]
        };
      } else {
        results = {
          domain: values.domain || '未指定领域',
          summary: '对该领域的系统分析表明存在若干关键研究空白和机会。',
          researchGaps: [
            {
              title: '该领域的研究问题示例',
              description: '这是一个模拟生成的研究问题描述。在实际API连接后，将生成更具体、更相关的内容。',
              evidence: [
                { text: '这是支持该研究问题的证据示例。', reference: '示例参考文献 (2023)' }
              ],
              potentialDirections: [
                '这是解决该研究问题的潜在方向示例。'
              ]
            }
          ]
        };
      }
      
      resolve(results);
    }, 2000); // 模拟2秒延迟
  });
};

const ResearchGapFinder = () => {
  // 状态管理
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [researchGapResult, setResearchGapResult] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedPapers, setSelectedPapers] = useState([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedGap, setSelectedGap] = useState(null);
  const [researchDomains, setResearchDomains] = useState(RESEARCH_DOMAINS);
  const [analysisPerspectives, setAnalysisPerspectives] = useState(ANALYSIS_PERSPECTIVES);
  const [paperSelectVisible, setPaperSelectVisible] = useState(false);
  const [papers, setPapers] = useState([]);
  const [loadingPapers, setLoadingPapers] = useState(false);
  const [downloadModalVisible, setDownloadModalVisible] = useState(false);
  const [error, setError] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  
  // 检查用户是否已登录
  useEffect(() => {
    const token = localStorage.getItem('token');
    const user = localStorage.getItem('user');
    if (token && user) {
      setIsAuthenticated(true);
    } else {
      setIsAuthenticated(false);
      message.warning('请先登录以使用研究问题识别功能的全部特性');
    }
  }, []);
  
  // 获取研究领域列表和可用论文
  useEffect(() => {
    const fetchDomains = async () => {
      try {
        const domains = await assistantApi.getResearchDomains();
        if (domains && Array.isArray(domains)) {
          setResearchDomains(domains);
        }
      } catch (error) {
        console.error('获取研究领域列表失败:', error);
        // 使用默认领域列表
      }
    };

    const fetchPerspectives = async () => {
      try {
        const perspectives = await assistantApi.getAnalysisPerspectives();
        if (perspectives && Array.isArray(perspectives)) {
          setAnalysisPerspectives(perspectives);
        }
      } catch (error) {
        console.error('获取分析角度列表失败:', error);
        // 使用默认角度列表
      }
    };

    // 获取用户的论文列表
    const fetchPapers = async () => {
      try {
        setLoadingPapers(true);
        
        // 直接使用papersAPI，这应该是最可靠的方式
        const response = await papersAPI.getPapers({ limit: 100 });
        console.log('论文API响应:', response);
        
        if (response && response.data) {
          // 根据API返回的不同数据结构进行处理
          if (Array.isArray(response.data)) {
            console.log('获取到论文数据(数组格式):', response.data);
            setPapers(response.data);
          } else if (response.data.items && Array.isArray(response.data.items)) {
            console.log('获取到论文数据(items格式):', response.data.items);
            setPapers(response.data.items);
          } else if (response.data.papers && Array.isArray(response.data.papers)) {
            console.log('获取到论文数据(papers格式):', response.data.papers);
            setPapers(response.data.papers);
          } else {
            console.warn('API返回了数据，但格式不符合预期:', response.data);
            message.warning('论文数据格式不正确，请联系管理员');
          }
        } else {
          console.warn('API返回空数据');
          // 如果没有数据，设置为空数组
          setPapers([]);
        }
      } catch (error) {
        console.error('获取论文列表失败:', error);
        message.error('无法加载论文数据，请稍后重试');
        // 确保我们至少有一个空数组
        setPapers([]);
      } finally {
        setLoadingPapers(false);
      }
    };

    fetchDomains();
    fetchPerspectives();
    fetchPapers();
  }, []);
  
  // 显示论文选择模态框
  const showPaperSelectModal = () => {
    // 如果当前没有论文数据，尝试重新获取
    if (papers.length === 0 && !loadingPapers) {
      setLoadingPapers(true);
      papersAPI.getPapers({ limit: 100 })
        .then(response => {
          if (response && response.data) {
            if (Array.isArray(response.data)) {
              setPapers(response.data);
            } else if (response.data.items && Array.isArray(response.data.items)) {
              setPapers(response.data.items);
            } else if (response.data.papers && Array.isArray(response.data.papers)) {
              setPapers(response.data.papers);
            }
          }
        })
        .catch(error => {
          console.error('打开模态框时获取论文失败:', error);
        })
        .finally(() => {
          setLoadingPapers(false);
          setPaperSelectVisible(true);
        });
    } else {
      setPaperSelectVisible(true);
    }
  };
  
  // 确认选择的论文
  const handlePaperSelect = () => {
    const selectedPaperIds = selectedPapers.map(paper => paper.id);
    form.setFieldsValue({ paper_ids: selectedPaperIds });
    setPaperSelectVisible(false);
  };
  
  // 表单提交处理
  const handleSubmit = async () => {
    try {
      // 验证用户是否已登录
      if (!isAuthenticated) {
        message.error('请先登录再进行研究问题分析');
        // 可以在这里添加跳转到登录页的逻辑
        // window.location.href = '/login';
        return;
      }
      
      const values = form.getFieldsValue();
      
      // 验证必填字段
      if (!values.domain || values.domain === 'undefined') {
        message.error('请选择研究领域');
        return;
      }
      
      setLoading(true);
      setError(null);
      
      console.log('提交的表单数据:', values);
      
      // 如果没有选择论文，确保传递空数组而不是undefined
      const paperIds = selectedPapers.map(paper => paper.id) || [];
      
      try {
        // 调用API
        const results = await assistantApi.analyzeResearchGaps(
          values.domain,
          values.perspective || 'comprehensive', // 默认使用综合分析
          paperIds,
          values.additionalContext
        );
        
        console.log('研究问题分析结果:', results);
        
        if (results.success === false) {
          throw new Error(results.message || '分析过程中发生错误');
        }
        
        setResearchGapResult(results);
        setCurrentStep(2); // 进入查看结果步骤
      } catch (apiError) {
        console.error('API调用失败:', apiError);
        
        // 判断是否是认证错误
        if (apiError.response && apiError.response.status === 401) {
          message.error('用户未认证或会话已过期，请重新登录');
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          setIsAuthenticated(false);
          // 可以在这里添加跳转到登录页的逻辑
          // window.location.href = '/login';
          return;
        }
        
        // 显示错误信息
        setError(apiError.message || '连接服务器失败，请稍后重试');
        message.error('分析过程中发生错误: ' + (apiError.message || '服务器连接失败'));
      }
    } catch (error) {
      console.error('研究问题分析出错:', error);
      setError(error.message || '无法获取分析概要，请稍后重试');
      message.error('分析过程中发生错误: ' + (error.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  };
  
  // 显示研究空白详情
  const openGapDetails = (gap) => {
    setSelectedGap(gap);
    setModalVisible(true);
  };
  
  // 重置分析
  const handleReset = () => {
    form.resetFields();
    setResearchGapResult(null);
    setCurrentStep(0);
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
      title: '摘要',
      dataIndex: 'abstract',
      key: 'abstract',
      render: (text) => text ? (
        <span style={{ 
          display: 'inline-block', 
          maxWidth: '400px', 
          overflow: 'hidden', 
          textOverflow: 'ellipsis', 
          whiteSpace: 'nowrap' 
        }}>
          {text}
        </span>
      ) : <span style={{ color: '#999' }}>无摘要</span>,
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
    <div className="research-gap-finder">
      <Card bordered={false}>
        {!isAuthenticated && (
          <Alert
            message="认证提示"
            description="您当前未登录或会话已过期。请登录后使用完整的研究问题分析功能。未登录状态下将使用本地模拟数据。"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
            action={
              <Button size="small" type="primary" href="/login">
                立即登录
              </Button>
            }
          />
        )}
        
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
                {researchDomains.map(domain => (
                  <Option key={domain.value} value={domain.value}>
                    {domain.label} - {domain.description}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            
            <Form.Item
              name="perspective"
              label="分析视角"
              rules={[{ required: true, message: '请选择分析视角' }]}
            >
              <Select placeholder="选择研究问题分析视角">
                {analysisPerspectives.map(perspective => (
                  <Option key={perspective.value} value={perspective.value}>
                    {perspective.label} - {perspective.description}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            
            <Form.Item
              name="paper_ids"
              label="相关论文（可选）"
              extra="选择相关论文可以提高分析的针对性和准确性"
            >
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ flex: 1, marginRight: 16 }}>
                  {selectedPapers.length > 0 ? (
                    <Alert 
                      message={`已选择 ${selectedPapers.length} 篇论文`} 
                      type="info" 
                      showIcon 
                    />
                  ) : (
                    <Alert 
                      message="未选择任何论文" 
                      type="info" 
                      showIcon 
                    />
                  )}
                </div>
                <Button 
                  type="primary" 
                  onClick={showPaperSelectModal}
                  icon={<PlusOutlined />}
                >
                  选择论文
                </Button>
              </div>
            </Form.Item>
            
            <Form.Item
              name="additionalContext"
              label="补充背景信息（可选）"
              extra="提供更具体的研究兴趣、问题定义或相关工作描述"
            >
              <TextArea 
                placeholder="例如：我对如何优化推荐系统中的长序列建模特别感兴趣..." 
                rows={5} 
                showCount
                maxLength={3000}
              />
            </Form.Item>
            
            <Form.Item>
              <Button 
                type="primary" 
                htmlType="submit" 
                icon={<SearchOutlined />}
                loading={loading}
                block
              >
                开始研究问题识别分析
              </Button>
            </Form.Item>
          </Form>
        )}
        
        {currentStep === 1 && (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <Spin size="large" />
            <div style={{ marginTop: 24 }}>
              <Title level={4}>正在深入分析研究问题...</Title>
              <Paragraph>
                系统正在分析当前研究领域的主要问题和机会，包括：主要存在的问题、文献支持、分析过程和潜在解决方向...
              </Paragraph>
            </div>
          </div>
        )}
        
        {currentStep === 2 && researchGapResult && (
          <div className="analysis-results">
            <div className="results-header">
              <Alert
                type="success"
                message={`${researchGapResult.domain}领域研究问题分析`}
                description={researchGapResult.summary}
                showIcon
                icon={<BookOutlined />}
                style={{ marginBottom: 24 }}
              />
              
              <Space style={{ marginBottom: 16 }}>
                <Button 
                  onClick={() => setCurrentStep(0)} 
                  icon={<SyncOutlined />}
                >
                  重新分析
                </Button>
              </Space>
            </div>
            
            {researchGapResult.researchGaps && researchGapResult.researchGaps.length > 0 ? (
              <List
                itemLayout="vertical"
                dataSource={researchGapResult.researchGaps || []}
                renderItem={(gap) => (
                  <List.Item
                    key={gap.title}
                    actions={[
                      <span key="evidence">
                        <FileTextOutlined /> 证据: {Array.isArray(gap.evidence) ? gap.evidence.length : 0}
                      </span>,
                      <span key="directions">
                        <CompassOutlined /> 潜在方向: {Array.isArray(gap.potentialDirections) ? gap.potentialDirections.length : 0}
                      </span>,
                      <Button key="view" type="link" onClick={(e) => {
                        e.stopPropagation();
                        openGapDetails(gap);
                      }}>
                        查看详情
                      </Button>
                    ]}
                  >
                    <List.Item.Meta
                      title={gap.title}
                      description={
                        <ReactMarkdown>{gap.description}</ReactMarkdown>
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
        {papers.length === 0 && !loadingPapers ? (
          <Empty 
            description={
              <span>
                没有找到任何论文。请先在<a href="/literature">文献管理</a>中添加论文。
              </span>
            }
          />
        ) : (
          <Table
            rowKey="id"
            dataSource={papers}
            columns={paperColumns}
            rowSelection={rowSelection}
            loading={loadingPapers}
            pagination={{ pageSize: 5 }}
            size="small"
          />
        )}
      </Modal>
      
      {/* 研究问题详情模态框 */}
      <Modal
        title={selectedGap ? selectedGap.title : "研究问题详情"}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {selectedGap && (
          <>
            <Paragraph>
              <Text strong>描述: </Text>
              <ReactMarkdown>{selectedGap.description}</ReactMarkdown>
            </Paragraph>
            
            {Array.isArray(selectedGap.evidence) && selectedGap.evidence.length > 0 && (
              <>
                <Divider orientation="left">支持证据</Divider>
                <List
                  dataSource={selectedGap.evidence}
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
            
            {Array.isArray(selectedGap.potentialDirections) && selectedGap.potentialDirections.length > 0 && (
              <>
                <Divider orientation="left">潜在研究方向</Divider>
                <List
                  dataSource={Array.isArray(selectedGap.potentialDirections) ? selectedGap.potentialDirections : []}
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
        .research-gap-finder {
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
      `}</style>
    </div>
  );
};

export default ResearchGapFinder; 