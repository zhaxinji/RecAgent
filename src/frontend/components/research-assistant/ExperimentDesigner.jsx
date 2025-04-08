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
  Tabs,
  Table,
  Tooltip,
  Alert,
  Modal,
  Badge,
  message
} from 'antd';
import { 
  ExperimentOutlined, 
  SearchOutlined, 
  FileTextOutlined,
  DatabaseOutlined,
  BarChartOutlined,
  SyncOutlined,
  SettingOutlined,
  BulbOutlined,
  CodeOutlined,
  AppstoreOutlined,
  CheckCircleOutlined,
  QuestionCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { assistantApi, papersAPI } from '../../services/api';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { Panel } = Collapse;
const { Step } = Steps;
const { TabPane } = Tabs;

// 研究领域列表
const RESEARCH_DOMAINS = [
  { value: 'sequential', label: '序列推荐', description: '基于用户历史行为序列的推荐技术' },
  { value: 'graph', label: '图神经网络推荐', description: '基于GNN的推荐系统方法' },
  { value: 'multi_modal', label: '多模态推荐', description: '结合图文音视频等多模态信息的推荐' },
  { value: 'contrastive', label: '对比学习推荐', description: '应用对比学习的推荐方法' },
  { value: 'llm', label: '大模型推荐', description: '基于大语言模型的推荐系统' }
];

// 数据集类型
const DATASET_TYPES = [
  { value: 'explicit', label: '显式反馈', description: '包含用户明确评分的数据集' },
  { value: 'implicit', label: '隐式反馈', description: '包含用户点击、浏览等行为的数据集' },
  { value: 'sequential', label: '序列数据', description: '包含时序用户行为的数据集' },
  { value: 'kg', label: '知识图谱增强', description: '包含知识图谱信息的数据集' },
  { value: 'social', label: '社交网络增强', description: '包含社交关系的数据集' },
  { value: 'multi_modal', label: '多模态数据', description: '包含文本、图像等多模态信息的数据集' }
];

// 评估指标
const METRICS = [
  { value: 'accuracy', label: '准确率指标', metrics: ['HR@K', 'NDCG@K', 'Precision@K', 'Recall@K', 'MAP@K', 'MRR'] },
  { value: 'diversity', label: '多样性指标', metrics: ['ILD', 'Coverage', 'Entropy', 'Gini'] },
  { value: 'novelty', label: '新颖性指标', metrics: ['Novelty@K', 'Unexpectedness', 'Serendipity'] },
  { value: 'efficiency', label: '效率指标', metrics: ['Training Time', 'Inference Time', 'Memory Usage'] },
  { value: 'fairness', label: '公平性指标', metrics: ['Statistical Parity', 'Equal Opportunity', 'Disparate Impact'] }
];

// 编程框架
const FRAMEWORKS = [
  { value: 'pytorch', label: 'PyTorch', description: 'Facebook开发的深度学习框架' },
  { value: 'tensorflow', label: 'TensorFlow', description: 'Google开发的深度学习框架' },
  { value: 'jax', label: 'JAX', description: '高性能数值计算库' },
  { value: 'numpy', label: 'NumPy', description: '基础数值计算库' }
];

// 从代码和解释中提取数据集信息
const extractDatasets = (code, experimentDesign) => {
  // 如果detailed_design中有datasets数据，使用其中的信息
  if (experimentDesign && experimentDesign.detailed_design && experimentDesign.detailed_design.datasets) {
    return experimentDesign.detailed_design.datasets.map(dataset => ({
      name: dataset.name || '未命名数据集',
      type: dataset.description || '数据集描述未提供',
      size: dataset.statistics || '数据规模未提供',
      features: Array.isArray(dataset.preprocessing) ? dataset.preprocessing.join(', ') : '预处理信息未提供',
      source: dataset.source || '来源未提供',
      preprocessing: dataset.split_strategy || '分割策略未提供'
    }));
  }
  
  // 尝试从代码中提取数据集信息（兼容旧版本）
  const datasets = [];
  
  // 提取数据集名称
  const datasetRegex = /(?:dataset|data_path|load_data|Dataset).*?['"](.+?)['"]/g;
  let match;
  const datasetNames = new Set();
  
  while ((match = datasetRegex.exec(code)) !== null) {
    if (match[1] && !match[1].includes('path/to') && !datasetNames.has(match[1])) {
      datasetNames.add(match[1]);
      datasets.push({
        name: match[1],
        type: '推荐系统数据集',
        size: '数据规模待确定',
        features: '根据代码实现确定',
        source: '公开数据集',
        preprocessing: '详见代码中的数据预处理部分'
      });
    }
  }
  
  // 如果没有提取到，返回默认数据集
  if (datasets.length === 0) {
    datasets.push({
      name: 'MovieLens-1M',
      type: '电影评分数据集',
      size: '用户-电影评分 1,000,209条',
      features: '用户ID、电影ID、评分、时间戳',
      source: 'GroupLens Research',
      preprocessing: '按需进行数据分割和预处理'
    });
  }
  
  return datasets;
};

// 从代码和解释中提取基线方法
const extractBaselines = (code, explanation, experimentDesign) => {
  // 如果detailed_design中有baseline_methods数据，使用其中的信息
  if (experimentDesign && experimentDesign.detailed_design && experimentDesign.detailed_design.baseline_methods) {
    return experimentDesign.detailed_design.baseline_methods.map(baseline => ({
      name: baseline.name || '未命名方法',
      description: baseline.description || (baseline.type ? `${baseline.type}方法` : '描述未提供'),
      reference: baseline.reference_paper || '参考文献未提供',
      implementation: baseline.implementation_source || '实现来源未提供'
    }));
  }
  
  // 默认基线方法（兼容旧版本）
  return [
    {
      name: '基本MLP模型',
      description: '多层感知机模型，用于基础性能比较',
      reference: '参考生成的代码实现',
      implementation: '详见生成的代码'
    },
    {
      name: '自定义模型',
      description: '根据实验需求定制的模型结构',
      reference: '根据生成的代码和实验设计文档',
      implementation: '详见生成的代码实现部分'
    }
  ];
};

// 从代码和解释中提取评估指标
const extractMetrics = (code, explanation, experimentDesign) => {
  // 如果detailed_design中有evaluation_metrics数据，使用其中的信息
  if (experimentDesign && experimentDesign.detailed_design && experimentDesign.detailed_design.evaluation_metrics) {
    return experimentDesign.detailed_design.evaluation_metrics.map(metric => ({
      name: metric.name || '未命名指标',
      description: metric.description || '描述未提供',
      formula: metric.formula || '公式未提供',
      k: metric.name && metric.name.includes('@') ? [parseInt(metric.name.split('@')[1])] : null
    }));
  }
  
  // 兼容旧版本的提取逻辑
  const metricsRegex = /(NDCG|HR|Precision|Recall|MAP|MRR|AUC|F1)@?(\d+)?/gi;
  const metrics = [];
  const metricsSet = new Set();
  
  let match;
  while ((match = metricsRegex.exec(code)) !== null) {
    const metricName = match[1].toUpperCase();
    const k = match[2];
    const fullName = k ? `${metricName}@${k}` : metricName;
    
    if (!metricsSet.has(fullName)) {
      metricsSet.add(fullName);
      metrics.push({
        name: fullName,
        description: getMetricDescription(metricName),
        formula: getMetricFormula(metricName, k),
        k: k ? [parseInt(k)] : null
      });
    }
  }
  
  // 如果没有提取到指标，返回默认指标
  if (metrics.length === 0) {
    metrics.push({
      name: 'NDCG@10',
      description: '归一化折扣累积增益，考虑推荐项目的排序位置',
      formula: 'NDCG@K = DCG@K / IDCG@K',
      k: [10]
    });
  }
  
  return metrics;
};

// 获取指标描述
const getMetricDescription = (metricName) => {
  const descriptions = {
    'NDCG': '归一化折扣累积增益，考虑推荐项目的排序位置',
    'HR': '命中率，推荐列表中包含测试项目的比例',
    'PRECISION': '精确率，推荐正确的项目数与推荐项目总数的比值',
    'RECALL': '召回率，推荐正确的项目数与用户实际交互的项目数比值',
    'MAP': '平均精度均值，在不同召回率水平上精确率的平均值',
    'MRR': '平均倒数排名，相关项目的排名倒数的平均值',
    'AUC': '曲线下面积，评估模型区分正负样本的能力',
    'F1': 'F1值，精确率和召回率的调和平均'
  };
  
  return descriptions[metricName] || '评估模型性能的指标';
};

// 获取指标公式
const getMetricFormula = (metricName, k) => {
  const formulas = {
    'NDCG': 'NDCG@K = DCG@K / IDCG@K',
    'HR': 'HR@K = #命中 / #用户数',
    'PRECISION': 'Precision@K = #命中 / K',
    'RECALL': 'Recall@K = #命中 / #交互项目数',
    'MAP': 'MAP@K = (1/#用户数) * ∑(AP@K)',
    'MRR': 'MRR = (1/#用户数) * ∑(1/rank)',
    'AUC': 'AUC = P(正样本分数 > 负样本分数)',
    'F1': 'F1 = 2 * (Precision * Recall) / (Precision + Recall)'
  };
  
  return formulas[metricName] || '计算公式见代码实现';
};

// 从代码和解释中提取实验设置
const extractSettings = (code, explanation, experimentDesign) => {
  // 如果detailed_design中有implementation_details数据，使用其中的信息
  if (experimentDesign && experimentDesign.detailed_design) {
    const details = experimentDesign.detailed_design.implementation_details || {};
    const proposed = experimentDesign.detailed_design.proposed_method || {};
    
    return {
      splitMethod: experimentDesign.detailed_design.evaluation_protocol || '根据实验需求进行数据分割',
      negativeHandling: experimentDesign.detailed_design.data_sampling_strategy || '见代码中的负采样实现',
      trainStrategy: proposed.training_process || '详见训练循环实现',
      hyperparameters: extractHyperparametersFromDesign(experimentDesign),
      hardware: details.hardware_requirements || '根据可用资源配置',
      software: details.dependencies ? details.dependencies.join(', ') : extractSoftware(code)
    };
  }
  
  // 默认设置（兼容旧版本）
  return {
    splitMethod: '根据实验需求进行数据分割',
    negativeHandling: '见代码中的负采样实现',
    trainStrategy: '详见训练循环实现',
    hyperparameters: extractHyperparameters(code),
    hardware: '根据可用资源配置',
    software: extractSoftware(code)
  };
};

// 提取超参数
const extractHyperparameters = (code) => {
  const hyperparams = [];
  
  // 常见超参数模式
  const patterns = [
    { regex: /batch_size\s*=\s*(\d+)/i, name: '批大小' },
    { regex: /learning_rate\s*=\s*([\d\.e\-]+)/i, name: '学习率' },
    { regex: /hidden_dim\s*=\s*(\d+)/i, name: '隐藏层大小' },
    { regex: /n_layers\s*=\s*(\d+)/i, name: '层数' },
    { regex: /dropout\s*=\s*([\d\.]+)/i, name: 'dropout率' },
    { regex: /embed_dim\s*=\s*(\d+)/i, name: '嵌入维度' },
    { regex: /num_epochs\s*=\s*(\d+)/i, name: '训练轮数' }
  ];
  
  patterns.forEach(({ regex, name }) => {
    const match = regex.exec(code);
    if (match && match[1]) {
      hyperparams.push({ name, value: match[1] });
    }
  });
  
  // 如果没提取到，提供默认值
  if (hyperparams.length === 0) {
    hyperparams.push(
      { name: '批大小', value: '64' },
      { name: '学习率', value: '0.001' },
      { name: '隐藏层大小', value: '64' }
    );
  }
  
  return hyperparams;
};

// 提取软件信息
const extractSoftware = (code) => {
  if (code.includes('import torch')) {
    return 'PyTorch, Python 3.x';
  } else if (code.includes('import tensorflow')) {
    return 'TensorFlow, Python 3.x';
      } else {
    return 'Python 3.x 及相关数据科学库';
  }
};

// 从实验设计数据中提取超参数
const extractHyperparametersFromDesign = (experimentDesign) => {
  const hyperparams = [];
  
  if (experimentDesign && experimentDesign.detailed_design) {
    // 尝试从proposed_method中提取
    if (experimentDesign.detailed_design.proposed_method && experimentDesign.detailed_design.proposed_method.hyperparameters) {
      const params = experimentDesign.detailed_design.proposed_method.hyperparameters;
      Object.entries(params).forEach(([name, value]) => {
        hyperparams.push({ name, value });
      });
    }
    
    // 如果还有参数敏感性分析，也加入
    if (experimentDesign.detailed_design.parameter_sensitivity) {
      experimentDesign.detailed_design.parameter_sensitivity.forEach(param => {
        if (!hyperparams.some(h => h.name === param.parameter)) {
          hyperparams.push({ 
            name: param.parameter, 
            value: param.range || '需要调优'
          });
        }
      });
    }
  }
  
  // 如果没提取到，回退到代码分析
  if (hyperparams.length === 0) {
    return extractHyperparameters(code);
  }
  
  return hyperparams;
};

// 从代码和解释中提取消融实验设计
const extractAblations = (code, explanation, experimentDesign) => {
  // 如果detailed_design中有ablation_studies数据，使用其中的信息
  if (experimentDesign && experimentDesign.detailed_design && experimentDesign.detailed_design.ablation_studies) {
    return experimentDesign.detailed_design.ablation_studies.map(study => ({
      component: study.component || '未命名组件',
      purpose: study.purpose || '目的未提供',
      variants: [
        study.variant_description || '移除该组件',
        '完整模型对比',
        study.implementation_details || '实现细节未提供'
      ]
    }));
  }
  
  // 默认消融实验（兼容旧版本）
  return [
    {
      component: '模型核心组件',
      purpose: '验证各组件的有效性',
      variants: [
        '完整模型',
        '移除特定组件',
        '替换为基线实现'
      ]
    }
  ];
};

// 实验设计生成函数 - 使用真实API
const generateExperimentDesign = async (values) => {
  console.log('生成实验设计参数:', values);
  
  // 准备请求参数
  const experimentData = {
    experiment_name: values.experimentName,
    experiment_description: values.methodDescription,
    framework: values.framework || 'pytorch',
    language: values.language || 'python'
  };
  
  try {
    // 调用API - 如果有paperId则使用，否则不传入
    const response = await assistantApi.generateExperiment(values.paperId, experimentData);
    
    // 检查错误
    if (response.error) {
      throw new Error(response.message || '生成实验设计失败');
    }
    
    console.log("实验设计API返回数据:", response);
    
    // 处理返回结果
    const result = {
      paperId: response.paper_id,
      experimentId: response.experiment_id,
      experimentTitle: response.experiment_design?.title || values.experimentName,
      code: response.code,
      explanation: response.explanation,
      domain: values.domain ? RESEARCH_DOMAINS.find(d => d.value === values.domain)?.label : '推荐系统',
      overview: response.explanation?.split('\n')[0] || '实验设计方案',
      // 把代码整理为UI显示需要的结构
      datasets: extractDatasets(response.code, response),
      baselines: extractBaselines(response.code, response.explanation, response),
      evaluationMetrics: extractMetrics(response.code, response.explanation, response),
      experimentalSettings: extractSettings(response.code, response.explanation, response),
      ablationStudy: extractAblations(response.code, response.explanation, response),
      codeSnippet: response.code
    };
    
    return result;
  } catch (error) {
    console.error('调用API失败:', error);
    message.error(`生成实验设计失败: ${error.message}`);
    throw error;
  }
};

// 实验设计组件主体
const ExperimentDesigner = ({ isDisabled = false, disabledMessage = '' }) => {
  // 状态管理
  const [form] = Form.useForm();
  const [generating, setGenerating] = useState(false);
  const [results, setResults] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [codeVisible, setCodeVisible] = useState(false);
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // 加载论文列表
  useEffect(() => {
    const fetchPapers = async () => {
      setLoading(true);
      try {
        const response = await papersAPI.getPapers();
        setPapers(response.data.items || []);
      } catch (error) {
        console.error('获取论文列表失败:', error);
        message.error('获取论文列表失败');
      } finally {
        setLoading(false);
      }
    };
    
    fetchPapers();
  }, []);
  
  // 提交表单生成实验设计
  const handleSubmit = async (values) => {
    if (isDisabled) {
      message.warning(disabledMessage || '该功能暂未开放，敬请期待');
      return;
    }
    
    setGenerating(true);
    setCurrentStep(1);
    try {
      const designResults = await generateExperimentDesign(values);
      setResults(designResults);
      setCurrentStep(2);
    } catch (error) {
      console.error('生成失败:', error);
      message.error(`生成实验设计失败: ${error.message}`);
      setCurrentStep(0);
    } finally {
      setGenerating(false);
    }
  };
  
  // 重置设计
  const handleReset = () => {
    form.resetFields();
    setResults(null);
    setCurrentStep(0);
  };
  
  // 显示代码示例模态框
  const showCodeModal = () => {
    setCodeVisible(true);
  };
  
  // 隐藏代码示例模态框
  const handleCodeModalClose = () => {
    setCodeVisible(false);
  };
  
  return (
    <div className="experiment-designer">
      <Card bordered={false}>
        {isDisabled && (
          <Alert
            message="功能暂未开放"
            description={disabledMessage || "由于考虑到自动化实验验证，暂未开发，敬请期待"}
            type="error"
            showIcon
            style={{ marginBottom: 24 }}
          />
        )}
        
        <Steps current={currentStep} style={{ marginBottom: 24 }}>
          <Step title="设置参数" description="指定实验配置" icon={<ExperimentOutlined />} />
          <Step title="生成中" description="AI设计实验" icon={<SyncOutlined spin={generating} />} />
          <Step title="查看结果" description="实验方案展示" icon={<FileTextOutlined />} />
        </Steps>
        
        {currentStep === 0 && (
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            initialValues={{
              domain: 'sequential',
              datasetType: 'implicit',
              metricType: 'accuracy',
              language: 'python',
              framework: 'pytorch',
              methodDescription: ''
            }}
          >
            <Form.Item
              name="paperId"
              label="选择论文（可选）"
            >
              <Select 
                placeholder="选择要基于的论文（可选）"
                loading={loading}
                allowClear
                showSearch
                optionFilterProp="children"
                filterOption={(input, option) =>
                  option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
                }
              >
                {papers.map(paper => (
                  <Option key={paper.id} value={paper.id}>
                    {paper.title}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            
            <Form.Item
              name="experimentName"
              label="实验名称"
              rules={[{ required: true, message: '请输入实验名称' }]}
            >
              <Input placeholder="例如：基于注意力机制的序列推荐实验" />
            </Form.Item>
            
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
              name="datasetType"
              label="数据集类型"
              rules={[{ required: true, message: '请选择数据集类型' }]}
            >
              <Select placeholder="选择实验所需数据集类型">
                {DATASET_TYPES.map(type => (
                  <Option key={type.value} value={type.value}>
                    {type.label} - {type.description}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            
            <Form.Item
              name="metricType"
              label="评估指标类型"
              rules={[{ required: true, message: '请选择评估指标类型' }]}
            >
              <Select placeholder="选择主要关注的评估指标类型">
                {METRICS.map(metric => (
                  <Option key={metric.value} value={metric.value}>
                    {metric.label} ({metric.metrics.join(', ')})
                  </Option>
                ))}
              </Select>
            </Form.Item>
            
            <Form.Item
              name="framework"
              label="实验框架"
              initialValue="pytorch"
              rules={[{ required: false }]}
            >
              <Input disabled value="PyTorch" placeholder="默认使用PyTorch框架" suffix={<Tooltip title="默认使用PyTorch作为实验框架"><InfoCircleOutlined /></Tooltip>} />
            </Form.Item>
            
            <Form.Item
              name="language"
              label="编程语言"
              initialValue="python"
              rules={[{ required: false }]}
            >
              <Input disabled value="Python" placeholder="默认使用Python" suffix={<Tooltip title="默认使用Python作为编程语言"><InfoCircleOutlined /></Tooltip>} />
            </Form.Item>
            
            <Form.Item
              name="methodDescription"
              label="方法描述（可选）"
              extra="简要描述您的方法或特殊实验需求"
            >
              <TextArea 
                placeholder="请输入您的方法描述、创新点或特殊实验需求..." 
                autoSize={{ minRows: 3, maxRows: 6 }}
              />
            </Form.Item>
            
            <Form.Item>
              <Button type="primary" htmlType="submit" icon={<ExperimentOutlined />} disabled={isDisabled || loading}>
                生成实验设计方案
              </Button>
              {isDisabled && (
                <Text type="danger" style={{ marginLeft: 16 }}>
                  由于考虑到自动化实验验证，暂未开发，敬请期待
                </Text>
              )}
            </Form.Item>
          </Form>
        )}
        
        {currentStep === 1 && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
            <div style={{ marginTop: 24 }}>
              <Title level={4}>
                AI正在设计{form.getFieldValue('domain') && RESEARCH_DOMAINS.find(d => d.value === form.getFieldValue('domain'))?.label}
                领域的实验方案...
              </Title>
              <Paragraph>
                实验设计过程包括：筛选合适数据集、选择基线方法、确定评估指标、设计实验流程，请稍候...
              </Paragraph>
            </div>
          </div>
        )}
        
        {currentStep === 2 && results && (
          <div className="experiment-results">
            <div className="results-header">
              <Title level={3}>{results.experimentTitle}</Title>
              <Paragraph>{results.overview}</Paragraph>
              <div style={{ textAlign: 'right', marginBottom: 16 }}>
                <Button onClick={handleReset} icon={<SyncOutlined />}>
                  重新设计
                </Button>
              </div>
            </div>
            
            <Tabs defaultActiveKey="datasets">
              <TabPane 
                tab={<span><DatabaseOutlined />数据集选择</span>} 
                key="datasets"
              >
                <Alert
                  message="推荐的数据集"
                  description={`为${results.domain}实验精选了${results.datasets.length}个高质量数据集，包含多种场景和规模。`}
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                
                <List
                  itemLayout="vertical"
                  dataSource={results.datasets}
                  renderItem={(dataset, index) => (
                    <Card style={{ marginBottom: 16 }} title={dataset.name}>
                      <List.Item>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <div>
                            <Text strong>类型：</Text> {dataset.type}
                          </div>
                          <div>
                            <Text strong>规模：</Text> {dataset.size}
                          </div>
                          <div>
                            <Text strong>特征：</Text> {dataset.features}
                          </div>
                          <div>
                            <Text strong>来源：</Text> {dataset.source}
                          </div>
                          <div>
                            <Text strong>预处理：</Text> {dataset.preprocessing}
                          </div>
                        </Space>
                      </List.Item>
                    </Card>
                  )}
                />
              </TabPane>
              
              <TabPane 
                tab={<span><AppstoreOutlined />基线方法</span>} 
                key="baselines"
              >
                <Alert
                  message="推荐的基线方法"
                  description={`精选了${results.baselines.length}个适合${results.domain}的最新基线方法，包含代表性算法和实现资源。`}
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                
                <List
                  itemLayout="vertical"
                  dataSource={results.baselines}
                  renderItem={(baseline, index) => (
                    <Card 
                      style={{ marginBottom: 16 }} 
                      title={baseline.name}
                      extra={
                        <a href={baseline.implementation} target="_blank" rel="noopener noreferrer">
                          实现代码
                        </a>
                      }
                    >
                      <List.Item>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <div>
                            <Text strong>描述：</Text> {baseline.description}
                          </div>
                          <div>
                            <Text strong>参考文献：</Text> {baseline.reference}
                          </div>
                        </Space>
                      </List.Item>
                    </Card>
                  )}
                />
              </TabPane>
              
              <TabPane 
                tab={<span><BarChartOutlined />评估指标</span>} 
                key="metrics"
              >
                <Alert
                  message="推荐的评估指标"
                  description={`为全面评估${results.domain}方法的性能，精选了多种评估指标，包括主要指标和辅助指标。`}
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                
                <List
                  itemLayout="vertical"
                  dataSource={results.evaluationMetrics}
                  renderItem={(metric, index) => (
                    <Card style={{ marginBottom: 16 }} title={metric.name}>
                      <List.Item>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <div>
                            <Text strong>描述：</Text> {metric.description}
                          </div>
                          <div>
                            <Text strong>计算公式：</Text> {metric.formula}
                          </div>
                          {metric.k && (
                            <div>
                              <Text strong>推荐K值：</Text> {metric.k.join(', ')}
                            </div>
                          )}
                        </Space>
                      </List.Item>
                    </Card>
                  )}
                />
              </TabPane>
              
              {results.experimentalSettings && (
                <TabPane 
                  tab={<span><SettingOutlined />实验设置</span>} 
                  key="settings"
                >
                  <Alert
                    message="实验设置与参数配置"
                    description="详细的实验流程和参数配置，确保实验的可重复性和公平性。"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  
                  <Card title="基本设置" style={{ marginBottom: 16 }}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div>
                        <Text strong>数据分割方法：</Text> {results.experimentalSettings.splitMethod}
                      </div>
                      <div>
                        <Text strong>负样本处理：</Text> {results.experimentalSettings.negativeHandling}
                      </div>
                      <div>
                        <Text strong>训练策略：</Text> {results.experimentalSettings.trainStrategy}
                      </div>
                      <div>
                        <Text strong>硬件环境：</Text> {results.experimentalSettings.hardware}
                      </div>
                      <div>
                        <Text strong>软件环境：</Text> {results.experimentalSettings.software}
                      </div>
                    </Space>
                  </Card>
                  
                  <Card title="超参数设置" style={{ marginBottom: 16 }}>
                    <Table
                      dataSource={results.experimentalSettings.hyperparameters}
                      columns={[
                        {
                          title: '参数名称',
                          dataIndex: 'name',
                          key: 'name',
                        },
                        {
                          title: '推荐值',
                          dataIndex: 'value',
                          key: 'value',
                        }
                      ]}
                      pagination={false}
                      size="small"
                      rowKey={(record, index) => index}
                    />
                  </Card>
                </TabPane>
              )}
              
              {results.ablationStudy && (
                <TabPane 
                  tab={<span><BulbOutlined />消融实验</span>} 
                  key="ablation"
                >
                  <Alert
                    message="消融实验设计"
                    description="通过移除或替换方法的关键组件，验证各个模块的有效性和贡献。"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  
                  <List
                    itemLayout="vertical"
                    dataSource={results.ablationStudy}
                    renderItem={(study, index) => (
                      <Card 
                        style={{ marginBottom: 16 }} 
                        title={`实验${index+1}：${study.component}`}
                      >
                        <List.Item>
                          <Space direction="vertical" style={{ width: '100%' }}>
                            <div>
                              <Text strong>目的：</Text> {study.purpose}
                            </div>
                            <div>
                              <Text strong>变体：</Text>
                              <List
                                dataSource={study.variants}
                                renderItem={(variant, idx) => (
                                  <List.Item>
                                    <Badge status={idx === study.variants.length - 1 ? "success" : "default"} text={variant} />
                                  </List.Item>
                                )}
                                size="small"
                              />
                            </div>
                          </Space>
                        </List.Item>
                      </Card>
                    )}
                  />
                </TabPane>
              )}
              
              {results.codeSnippet && (
                <TabPane 
                  tab={<span><CodeOutlined />参考代码</span>} 
                  key="code"
                >
                  <Alert
                    message="核心算法参考实现"
                    description="提供方法核心部分的PyTorch实现示例，可作为实验的起点。"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  
                  <Card>
                    <div style={{ textAlign: 'right', marginBottom: 10 }}>
                      <Button type="primary" onClick={showCodeModal} icon={<CodeOutlined />}>
                        查看完整代码
                      </Button>
                    </div>
                    <div style={{ maxHeight: '300px', overflow: 'auto' }}>
                      <pre style={{ 
                        backgroundColor: '#f5f5f5', 
                        padding: 16, 
                        borderRadius: 4,
                        fontSize: '0.9em',
                        fontFamily: 'SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace',
                        lineHeight: 1.6
                      }}>
                        <code>{results.codeSnippet}</code>
                      </pre>
                    </div>
                  </Card>
                </TabPane>
              )}
            </Tabs>
          </div>
        )}
      </Card>
      
      {/* 代码示例模态框 */}
      {results && results.codeSnippet && (
        <Modal
          title="算法核心代码实现"
          open={codeVisible}
          onCancel={handleCodeModalClose}
          footer={[
            <Button key="close" type="primary" onClick={handleCodeModalClose}>
              关闭
            </Button>
          ]}
          width={800}
          bodyStyle={{ maxHeight: '80vh', overflow: 'auto' }}
        >
          <div>
            <Alert
              message="核心算法实现"
              description="以下代码展示了该实验方法的核心算法实现，包含模型定义、关键层和创新点的具体实现。代码为伪代码性质，可能需要根据实际环境进行调整。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            
            <pre style={{ 
              backgroundColor: '#f5f5f5', 
              padding: 16, 
              borderRadius: 4,
              overflowX: 'auto',
              fontSize: '0.9em',
              fontFamily: 'SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace',
              lineHeight: 1.6
            }}>
              <code>{results.codeSnippet}</code>
            </pre>
            
            <Divider>依赖库和环境要求</Divider>
            
            <div style={{ marginBottom: 16 }}>
              <Text strong>主要依赖：</Text>
              <div style={{ marginTop: 8 }}>
                {(results.meta?.dependencies || ['numpy', 'pandas', 'torch', 'scikit-learn']).map(dep => (
                  <Tag color="blue" key={dep} style={{ margin: '0 8px 8px 0' }}>{dep}</Tag>
                ))}
              </div>
            </div>
            
            <div>
              <Text strong>环境要求：</Text>
              <div style={{ marginTop: 8 }}>
                <Tag color="green">Python 3.7+</Tag>
                <Tag color="green">{results.meta?.framework || 'PyTorch'} 1.8+</Tag>
                <Tag color="green">CUDA 10.2+ (GPU加速)</Tag>
              </div>
            </div>
          </div>
        </Modal>
      )}
      
      <style jsx="true">{`
        .experiment-designer {
          max-width: 1000px;
          margin: 0 auto;
        }
        
        .experiment-results {
          padding: 16px 0;
        }
        
        .results-header {
          margin-bottom: 24px;
        }
      `}</style>
    </div>
  );
};

export default ExperimentDesigner; 