import React from 'react';
import PropTypes from 'prop-types';
import { 
  Card, 
  Descriptions, 
  Button, 
  Divider, 
  Tag, 
  Space, 
  Badge,
  Typography,
  Alert
} from 'antd';
import { 
  PlayCircleOutlined, 
  ExperimentOutlined, 
  DatabaseOutlined,
  BarChartOutlined,
  ClockCircleOutlined,
  TeamOutlined,
  AppstoreOutlined,
  TagsOutlined
} from '@ant-design/icons';
import moment from 'moment';
import LoadingState from '../LoadingState';

const { Title, Paragraph } = Typography;

// 状态徽章渲染
const renderStatusBadge = (status) => {
  const statusConfig = {
    created: { status: 'default', text: '已创建' },
    running: { status: 'processing', text: '运行中' },
    completed: { status: 'success', text: '已完成' },
    failed: { status: 'error', text: '失败' }
  };

  const config = statusConfig[status] || statusConfig.created;
  
  return (
    <Badge status={config.status} text={config.text} />
  );
};

const ExperimentDetail = ({ experiment, loading, onRunExperiment }) => {
  if (loading) {
    return <LoadingState />;
  }

  if (!experiment) {
    return (
      <Alert
        message="实验不存在"
        description="无法找到请求的实验，请确认实验ID是否正确。"
        type="error"
        showIcon
      />
    );
  }

  return (
    <Card
      title={
        <Space>
          <ExperimentOutlined />
          <span>实验详情</span>
          {renderStatusBadge(experiment.status)}
        </Space>
      }
      extra={
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={onRunExperiment}
          loading={experiment.status === 'running'}
          disabled={experiment.status === 'running'}
        >
          {experiment.status === 'completed' ? '重新运行' : '运行实验'}
        </Button>
      }
    >
      <Typography>
        <Title level={3}>{experiment.name}</Title>
        {experiment.description && (
          <Paragraph>{experiment.description}</Paragraph>
        )}
      </Typography>

      <Divider orientation="left">基本信息</Divider>
      
      <Descriptions bordered column={{ xxl: 4, xl: 3, lg: 3, md: 2, sm: 1, xs: 1 }}>
        <Descriptions.Item label="ID">{experiment.id}</Descriptions.Item>
        <Descriptions.Item label="创建时间">{moment(experiment.created_at).format('YYYY-MM-DD HH:mm:ss')}</Descriptions.Item>
        <Descriptions.Item label="更新时间">{moment(experiment.updated_at).format('YYYY-MM-DD HH:mm:ss')}</Descriptions.Item>
        <Descriptions.Item label="状态">{renderStatusBadge(experiment.status)}</Descriptions.Item>
      </Descriptions>
      
      <Divider orientation="left">
        <Space>
          <DatabaseOutlined />
          <span>数据集</span>
        </Space>
      </Divider>
      
      <Card>
        <Descriptions bordered column={{ xxl: 3, xl: 3, lg: 2, md: 2, sm: 1, xs: 1 }}>
          <Descriptions.Item label="数据集名称">{experiment.dataset.name}</Descriptions.Item>
          <Descriptions.Item label="类型">{experiment.dataset.type}</Descriptions.Item>
          <Descriptions.Item label="大小">{experiment.dataset.size}</Descriptions.Item>
          <Descriptions.Item label="物品类型">{experiment.dataset.items}</Descriptions.Item>
          <Descriptions.Item label="交互数量">{experiment.dataset.interactions}</Descriptions.Item>
          <Descriptions.Item label="用户数量">{experiment.dataset.users}</Descriptions.Item>
          <Descriptions.Item label="描述" span={3}>{experiment.dataset.description}</Descriptions.Item>
        </Descriptions>
      </Card>
      
      <Divider orientation="left">
        <Space>
          <AppstoreOutlined />
          <span>算法</span>
        </Space>
      </Divider>
      
      <Card>
        <Space wrap>
          {experiment.algorithms.map(algorithm => (
            <Tag key={algorithm.id} color="blue">
              {algorithm.name} ({algorithm.type})
            </Tag>
          ))}
        </Space>
        
        <Divider />
        
        {experiment.algorithms.map(algorithm => (
          <Card 
            key={algorithm.id} 
            title={algorithm.name} 
            style={{ marginBottom: 16 }}
            type="inner"
          >
            <Descriptions column={{ xxl: 3, xl: 3, lg: 2, md: 2, sm: 1, xs: 1 }}>
              <Descriptions.Item label="类型">{algorithm.type}</Descriptions.Item>
              <Descriptions.Item label="复杂度">{algorithm.complexity}</Descriptions.Item>
              <Descriptions.Item label="描述">{algorithm.description}</Descriptions.Item>
            </Descriptions>
          </Card>
        ))}
      </Card>
      
      <Divider orientation="left">
        <Space>
          <BarChartOutlined />
          <span>评估指标</span>
        </Space>
      </Divider>
      
      <Card>
        <Space wrap>
          {experiment.metrics.map(metric => (
            <Tag key={metric} color="green">
              {metric.toUpperCase()}
            </Tag>
          ))}
        </Space>
      </Card>
      
      <Divider orientation="left">
        <Space>
          <TagsOutlined />
          <span>K值设置</span>
        </Space>
      </Divider>
      
      <Card>
        <Space wrap>
          {experiment.k_values.map(k => (
            <Tag key={k} color="orange">
              K = {k}
            </Tag>
          ))}
        </Space>
      </Card>
    </Card>
  );
};

ExperimentDetail.propTypes = {
  experiment: PropTypes.shape({
    id: PropTypes.string,
    name: PropTypes.string,
    description: PropTypes.string,
    status: PropTypes.string,
    created_at: PropTypes.string,
    updated_at: PropTypes.string,
    algorithms: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.string,
      name: PropTypes.string,
      type: PropTypes.string,
      complexity: PropTypes.string,
      description: PropTypes.string
    })),
    metrics: PropTypes.arrayOf(PropTypes.string),
    k_values: PropTypes.arrayOf(PropTypes.number),
    dataset: PropTypes.shape({
      id: PropTypes.string,
      name: PropTypes.string,
      type: PropTypes.string,
      size: PropTypes.string,
      items: PropTypes.string,
      interactions: PropTypes.string,
      users: PropTypes.string,
      description: PropTypes.string
    })
  }),
  loading: PropTypes.bool,
  onRunExperiment: PropTypes.func.isRequired
};

ExperimentDetail.defaultProps = {
  loading: false
};

export default ExperimentDetail; 