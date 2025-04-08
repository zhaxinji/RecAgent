import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { 
  Form, 
  Input, 
  Button, 
  Select, 
  Card, 
  Divider, 
  Space, 
  Checkbox, 
  Row, 
  Col,
  InputNumber,
  Alert,
  Spin
} from 'antd';
import { 
  DatabaseOutlined, 
  ThunderboltOutlined, 
  BarChartOutlined,
  SettingOutlined,
  SaveOutlined,
  CloseOutlined
} from '@ant-design/icons';
import { experimentsAPI } from '../../services/api';

const { Option, OptGroup } = Select;
const { TextArea } = Input;

const ExperimentForm = ({ onSubmit, onCancel }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [datasets, setDatasets] = useState([]);
  const [algorithms, setAlgorithms] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [advancedMode, setAdvancedMode] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [selectedAlgorithms, setSelectedAlgorithms] = useState([]);

  // 获取所有必要的数据
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [datasetsRes, algorithmsRes, metricsRes] = await Promise.all([
          experimentsAPI.getDatasets(),
          experimentsAPI.getAlgorithms(),
          experimentsAPI.getMetrics()
        ]);
        
        setDatasets(datasetsRes.data);
        setAlgorithms(algorithmsRes.data);
        setMetrics(metricsRes.data);
      } catch (error) {
        console.error('获取实验数据失败:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);

  // 处理表单提交
  const handleFinish = async (values) => {
    setSubmitting(true);
    try {
      const formData = {
        ...values,
        k_values: values.k_values || [5, 10, 20],
      };
      
      await onSubmit(formData);
    } finally {
      setSubmitting(false);
    }
  };

  // 按类型对算法进行分组
  const algorithmsByType = algorithms.reduce((groups, algo) => {
    const groupName = algo.type;
    if (!groups[groupName]) {
      groups[groupName] = [];
    }
    groups[groupName].push(algo);
    return groups;
  }, {});

  return (
    <Spin spinning={loading}>
      <Card title="创建新实验">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleFinish}
          initialValues={{
            k_values: [5, 10, 20],
          }}
        >
          <Alert
            message="创建实验"
            description="实验用于比较不同推荐算法在特定数据集上的性能表现，您可以选择数据集、多个算法和评估指标进行对比。"
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
          />
          
          {/* 基本信息 */}
          <Form.Item 
            label="实验名称" 
            name="name"
            rules={[{ required: true, message: '请输入实验名称' }]}
          >
            <Input placeholder="为您的实验起一个描述性的名称" />
          </Form.Item>
          
          <Form.Item 
            label="实验描述" 
            name="description"
          >
            <TextArea 
              placeholder="描述这个实验的目的和预期结果" 
              rows={3} 
            />
          </Form.Item>
          
          <Divider orientation="left">
            <Space>
              <DatabaseOutlined />
              <span>数据集</span>
            </Space>
          </Divider>
          
          {/* 数据集选择 */}
          <Form.Item 
            label="选择数据集" 
            name="dataset_id"
            rules={[{ required: true, message: '请选择数据集' }]}
          >
            <Select 
              placeholder="选择实验数据集"
              onChange={value => {
                const dataset = datasets.find(d => d.id === value);
                setSelectedDataset(dataset);
              }}
            >
              {datasets.map(dataset => (
                <Option key={dataset.id} value={dataset.id}>
                  {dataset.name} ({dataset.interactions} 交互, {dataset.users} 用户)
                </Option>
              ))}
            </Select>
          </Form.Item>
          
          {selectedDataset && (
            <Alert
              message={`已选择: ${selectedDataset.name}`}
              description={selectedDataset.description}
              type="success"
              showIcon
              style={{ marginBottom: 24 }}
            />
          )}
          
          <Divider orientation="left">
            <Space>
              <ThunderboltOutlined />
              <span>算法</span>
            </Space>
          </Divider>
          
          {/* 算法选择 */}
          <Form.Item 
            label="选择算法" 
            name="algorithm_ids"
            rules={[{ required: true, message: '请至少选择1个算法' }]}
          >
            <Select 
              mode="multiple" 
              placeholder="选择要比较的算法"
              onChange={values => {
                const selected = algorithms.filter(a => values.includes(a.id));
                setSelectedAlgorithms(selected);
              }}
            >
              {Object.entries(algorithmsByType).map(([type, algos]) => (
                <OptGroup key={type} label={type}>
                  {algos.map(algo => (
                    <Option key={algo.id} value={algo.id}>
                      {algo.name} (复杂度: {algo.complexity})
                    </Option>
                  ))}
                </OptGroup>
              ))}
            </Select>
          </Form.Item>
          
          {selectedAlgorithms.length > 0 && (
            <Alert
              message={`已选择 ${selectedAlgorithms.length} 个算法`}
              description={`将对比 ${selectedAlgorithms.map(a => a.name).join('、')} 的性能`}
              type="success"
              showIcon
              style={{ marginBottom: 24 }}
            />
          )}
          
          <Divider orientation="left">
            <Space>
              <BarChartOutlined />
              <span>评估指标</span>
            </Space>
          </Divider>
          
          {/* 评估指标选择 */}
          <Form.Item 
            label="选择评估指标" 
            name="metrics"
            rules={[{ required: true, message: '请至少选择1个评估指标' }]}
          >
            <Select 
              mode="multiple" 
              placeholder="选择评估指标"
            >
              {metrics.map(metric => (
                <Option key={metric.id} value={metric.id}>
                  {metric.name} ({metric.description})
                </Option>
              ))}
            </Select>
          </Form.Item>
          
          {/* 高级设置 */}
          <Divider>
            <Checkbox 
              checked={advancedMode} 
              onChange={(e) => setAdvancedMode(e.target.checked)}
            >
              <Space>
                <SettingOutlined />
                <span>高级设置</span>
              </Space>
            </Checkbox>
          </Divider>
          
          {advancedMode && (
            <Row gutter={16}>
              <Col span={24}>
                <Form.Item 
                  label="K值设置" 
                  name="k_values"
                  help="指定计算TopK指标的K值，如Recall@K, Precision@K, NDCG@K等"
                >
                  <Select mode="tags" tokenSeparators={[',']} placeholder="输入K值，用逗号分隔">
                    <Option value={5}>5</Option>
                    <Option value={10}>10</Option>
                    <Option value={20}>20</Option>
                    <Option value={50}>50</Option>
                    <Option value={100}>100</Option>
                  </Select>
                </Form.Item>
              </Col>
              
              {/* 更多高级设置可以根据需要添加 */}
            </Row>
          )}
          
          {/* 表单操作按钮 */}
          <Form.Item>
            <Space>
              <Button 
                type="primary" 
                htmlType="submit" 
                icon={<SaveOutlined />}
                loading={submitting}
              >
                创建实验
              </Button>
              <Button 
                onClick={onCancel} 
                icon={<CloseOutlined />}
              >
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </Spin>
  );
};

ExperimentForm.propTypes = {
  onSubmit: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired
};

export default ExperimentForm; 