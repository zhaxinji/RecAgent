import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Table, Card, Button, Space, Tag, Modal, message, Tooltip } from 'antd';
import { 
  PlayCircleOutlined, 
  EyeOutlined, 
  DeleteOutlined, 
  PlusOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import moment from 'moment';
import { experimentsAPI } from '../../services/api';
import EmptyState from '../EmptyState';
import LoadingState from '../LoadingState';

const ExperimentList = ({ onCreateClick }) => {
  const [experiments, setExperiments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [runningExperiment, setRunningExperiment] = useState(null);
  const navigate = useNavigate();

  // 获取实验列表
  const fetchExperiments = async () => {
    setLoading(true);
    try {
      const response = await experimentsAPI.getExperiments();
      if (response && response.data) {
        // 兼容两种数据格式
        const experimentData = response.data.items || response.data;
        setExperiments(Array.isArray(experimentData) ? experimentData : []);
      }
    } catch (error) {
      console.error('获取实验列表失败:', error);
      message.error('获取实验列表失败, 请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExperiments();
  }, []);

  // 运行实验
  const handleRunExperiment = async (id) => {
    setRunningExperiment(id);
    try {
      await experimentsAPI.runExperiment(id);
      message.success('实验运行成功');
      fetchExperiments();
    } catch (error) {
      console.error('运行实验失败:', error);
      message.error('运行实验失败');
    } finally {
      setRunningExperiment(null);
    }
  };

  // 查看实验详情
  const handleViewExperiment = (id) => {
    navigate(`/experiments/${id}`);
  };

  // 删除实验确认
  const confirmDelete = (id) => {
    Modal.confirm({
      title: '确认删除',
      content: '您确定要删除这个实验吗？此操作不可恢复。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => {
        // 实际项目中应调用删除API
        message.success('删除成功');
        setExperiments(experiments.filter(exp => exp.id !== id));
      }
    });
  };

  // 状态标签渲染
  const renderStatusTag = (status) => {
    const statusConfig = {
      created: { color: 'blue', icon: <ClockCircleOutlined />, text: '已创建' },
      running: { color: 'processing', icon: <SyncOutlined spin />, text: '运行中' },
      completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
      failed: { color: 'error', icon: <CloseCircleOutlined />, text: '失败' }
    };

    const config = statusConfig[status] || statusConfig.created;
    
    return (
      <Tag color={config.color} icon={config.icon}>
        {config.text}
      </Tag>
    );
  };

  // 表格列定义
  const columns = [
    {
      title: '实验名称',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Link to={`/experiments/${record.id}`}>{text}</Link>
      ),
    },
    {
      title: '数据集',
      dataIndex: ['dataset', 'name'],
      key: 'dataset',
    },
    {
      title: '算法',
      dataIndex: 'algorithms',
      key: 'algorithms',
      render: (algorithms) => (
        <span>
          {algorithms.map(algo => (
            <Tag key={algo.id}>{algo.name}</Tag>
          ))}
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: renderStatusTag,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => moment(date).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          {record.status !== 'running' && (
            <Tooltip title="运行实验">
              <Button
                type="link"
                icon={<PlayCircleOutlined />}
                onClick={() => handleRunExperiment(record.id)}
                loading={runningExperiment === record.id}
                disabled={record.status === 'running'}
              />
            </Tooltip>
          )}
          <Tooltip title="查看详情">
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => handleViewExperiment(record.id)}
            />
          </Tooltip>
          <Tooltip title="删除实验">
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              onClick={() => confirmDelete(record.id)}
              disabled={record.status === 'running'}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // 当没有实验时显示的空状态
  const emptyContent = (
    <EmptyState
      title="暂无实验"
      description="创建您的第一个推荐算法实验，比较不同算法的性能"
      buttonText="创建实验"
      buttonIcon={<PlusOutlined />}
      onButtonClick={onCreateClick}
    />
  );

  return (
    <Card 
      title="我的实验" 
      extra={
        <Button 
          type="primary" 
          icon={<PlusOutlined />} 
          onClick={onCreateClick}
        >
          创建实验
        </Button>
      }
    >
      {loading ? (
        <LoadingState rows={5} />
      ) : experiments.length > 0 ? (
        <Table 
          dataSource={experiments} 
          columns={columns} 
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      ) : (
        emptyContent
      )}
    </Card>
  );
};

ExperimentList.propTypes = {
  onCreateClick: PropTypes.func.isRequired
};

export default ExperimentList; 