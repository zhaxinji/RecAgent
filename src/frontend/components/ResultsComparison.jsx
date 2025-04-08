import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { 
  Card, 
  Table, 
  Typography, 
  Tooltip, 
  Badge, 
  Space, 
  Radio, 
  Divider, 
  Tabs,
  Empty,
  Button,
  Tag,
  Progress
} from 'antd';
import {
  LineChartOutlined,
  BarChartOutlined,
  TableOutlined,
  TrophyOutlined,
  InfoCircleOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined
} from '@ant-design/icons';
import LoadingState from './LoadingState';
import { themeColors } from '../theme/themeConfig';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

/**
 * 结果比较组件
 * 用于比较不同算法、模型或方法的性能结果
 */
const ResultsComparison = ({
  title,
  description,
  results = [],
  metrics = [],
  algorithms = [],
  loading = false,
  showBest = true,
  showDifference = true,
  bestHigher = true,
  decimalPlaces = 4,
  viewMode = 'table',
  onViewModeChange,
  className = '',
  style = {}
}) => {
  const [currentViewMode, setCurrentViewMode] = useState(viewMode);
  const [bestIndices, setBestIndices] = useState({});
  
  // 计算每个指标的最佳值
  useEffect(() => {
    if (!results.length || !metrics.length) return;
    
    const newBestIndices = {};
    
    metrics.forEach(metric => {
      const metricValues = algorithms.map((algo, index) => {
        const resultEntry = results.find(r => r.algorithm === algo.id);
        return resultEntry ? resultEntry.metrics[metric.id] : null;
      }).filter(value => value !== null && value !== undefined);
      
      if (metricValues.length === 0) return;
      
      // 找到最佳值（最大或最小）
      const bestValue = bestHigher 
        ? Math.max(...metricValues) 
        : Math.min(...metricValues);
        
      newBestIndices[metric.id] = bestValue;
    });
    
    setBestIndices(newBestIndices);
  }, [results, metrics, algorithms, bestHigher]);

  // 处理视图模式改变
  const handleViewModeChange = (e) => {
    const mode = e.target.value;
    setCurrentViewMode(mode);
    if (onViewModeChange) {
      onViewModeChange(mode);
    }
  };

  // 格式化数字
  const formatNumber = (value) => {
    if (value === null || value === undefined) return '-';
    return Number(value).toFixed(decimalPlaces);
  };

  // 获取差异标记
  const getDifferenceIndicator = (currentValue, bestValue) => {
    if (currentValue === null || currentValue === undefined || bestValue === null || bestValue === undefined) {
      return null;
    }
    
    const diff = currentValue - bestValue;
    if (Math.abs(diff) < 0.0001) return null;
    
    const percentage = Math.abs((diff / bestValue) * 100).toFixed(1);
    
    // 正向指标（越高越好）
    if (bestHigher) {
      if (diff > 0) {
        return (
          <Text type="success" style={{ fontSize: 12 }}>
            <ArrowUpOutlined /> {percentage}%
          </Text>
        );
      } else {
        return (
          <Text type="danger" style={{ fontSize: 12 }}>
            <ArrowDownOutlined /> {percentage}%
          </Text>
        );
      }
    } 
    // 反向指标（越低越好）
    else {
      if (diff < 0) {
        return (
          <Text type="success" style={{ fontSize: 12 }}>
            <ArrowDownOutlined /> {percentage}%
          </Text>
        );
      } else {
        return (
          <Text type="danger" style={{ fontSize: 12 }}>
            <ArrowUpOutlined /> {percentage}%
          </Text>
        );
      }
    }
  };

  // 获取进度条
  const getProgressBar = (currentValue, bestValue, metric) => {
    if (currentValue === null || currentValue === undefined) return null;
    
    // 计算百分比
    let percent;
    if (bestHigher) {
      const minValue = metric.minValue || 0;
      const range = (metric.maxValue || 1) - minValue;
      percent = ((currentValue - minValue) / range) * 100;
    } else {
      const maxValue = metric.maxValue || 1;
      const minValue = metric.minValue || 0;
      const range = maxValue - minValue;
      percent = ((maxValue - currentValue) / range) * 100;
    }
    
    percent = Math.min(100, Math.max(0, percent));
    
    // 确定状态颜色
    let status;
    let strokeColor;
    
    if (Math.abs(currentValue - bestValue) < 0.0001) {
      status = 'success';
      strokeColor = themeColors.success.main;
    } else if (percent >= 80) {
      status = 'normal';
      strokeColor = themeColors.primary.main;
    } else if (percent >= 60) {
      status = 'normal';
      strokeColor = themeColors.warning.main;
    } else {
      status = 'exception';
      strokeColor = themeColors.error.main;
    }
    
    return (
      <Tooltip title={`${formatNumber(currentValue)} / 最佳: ${formatNumber(bestValue)}`}>
        <Progress 
          percent={percent.toFixed(0)} 
          size="small"
          showInfo={false}
          status={status}
          strokeColor={strokeColor}
          trailColor={themeColors.background.paper}
          style={{ marginTop: 2, marginBottom: 0 }}
        />
      </Tooltip>
    );
  };

  // 渲染表格视图
  const renderTableView = () => {
    const columns = [
      {
        title: '算法/模型',
        dataIndex: 'algorithm',
        key: 'algorithm',
        fixed: 'left',
        width: 160,
        render: (_, record) => {
          const algo = algorithms.find(a => a.id === record.algorithm);
          if (!algo) return record.algorithm;
          
          return (
            <Space>
              {algo.icon && <span>{algo.icon}</span>}
              <Text strong>{algo.name}</Text>
            </Space>
          );
        }
      },
      ...metrics.map(metric => ({
        title: (
          <Tooltip title={metric.description || metric.name}>
            <Space size={4}>
              <span>{metric.name}</span>
              <InfoCircleOutlined style={{ fontSize: 12, color: '#8c8c8c' }} />
              {metric.higherIsBetter !== undefined ? (
                <Tag size="small" color={metric.higherIsBetter ? "success" : "error"} style={{ margin: 0, fontSize: 10 }}>
                  {metric.higherIsBetter ? "越高越好" : "越低越好"}
                </Tag>
              ) : null}
            </Space>
          </Tooltip>
        ),
        dataIndex: ['metrics', metric.id],
        key: metric.id,
        width: 120,
        align: 'center',
        render: (value, record) => {
          const bestValue = bestIndices[metric.id];
          const isBest = Math.abs(value - bestValue) < 0.0001;
          
          return (
            <div>
              <div style={{ marginBottom: 4 }}>
                {showBest && isBest ? (
                  <Badge
                    count={<TrophyOutlined style={{ color: themeColors.warning.main }} />}
                    style={{ backgroundColor: 'transparent' }}
                  >
                    <Text strong style={{ color: themeColors.success.main }}>
                      {formatNumber(value)}
                    </Text>
                  </Badge>
                ) : (
                  <Text>{formatNumber(value)}</Text>
                )}
              </div>
              
              {showDifference && !isBest && (
                <div>{getDifferenceIndicator(value, bestValue)}</div>
              )}
              
              {getProgressBar(value, bestValue, metric)}
            </div>
          );
        }
      }))
    ];

    return (
      <Table
        dataSource={results}
        columns={columns}
        rowKey="algorithm"
        pagination={false}
        size="middle"
        bordered
        scroll={{ x: 'max-content' }}
      />
    );
  };

  // 渲染切换视图的工具栏
  const renderViewToggle = () => {
    if (!onViewModeChange) return null;
    
    return (
      <div style={{ marginBottom: 16, textAlign: 'right' }}>
        <Radio.Group 
          value={currentViewMode} 
          onChange={handleViewModeChange}
          optionType="button"
          buttonStyle="solid"
          size="small"
        >
          <Radio.Button value="table">
            <TableOutlined />
            <span style={{ marginLeft: 4 }}>表格</span>
          </Radio.Button>
          <Radio.Button value="bar">
            <BarChartOutlined />
            <span style={{ marginLeft: 4 }}>柱状图</span>
          </Radio.Button>
          <Radio.Button value="line">
            <LineChartOutlined />
            <span style={{ marginLeft: 4 }}>折线图</span>
          </Radio.Button>
        </Radio.Group>
      </div>
    );
  };

  // 渲染不同的视图
  const renderContent = () => {
    if (loading) {
      return <LoadingState rows={5} />;
    }
    
    if (!results.length || !metrics.length) {
      return (
        <Empty 
          description="暂无比较数据" 
          image={Empty.PRESENTED_IMAGE_SIMPLE} 
        />
      );
    }
    
    // 目前只实现了表格视图，将来可以添加图表视图
    switch(currentViewMode) {
      case 'table':
        return renderTableView();
      case 'bar':
      case 'line':
        return (
          <div style={{ padding: '20px 0', textAlign: 'center' }}>
            <Text type="secondary">图表视图正在开发中...</Text>
          </div>
        );
      default:
        return renderTableView();
    }
  };

  return (
    <div 
      className={`results-comparison ${className}`}
      style={{ 
        ...style 
      }}
    >
      <Card
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              {title && <Title level={4} style={{ marginBottom: 0 }}>{title}</Title>}
              {description && <Text type="secondary">{description}</Text>}
            </div>
          </div>
        }
        bordered={false}
        extra={renderViewToggle()}
      >
        {renderContent()}
      </Card>
    </div>
  );
};

ResultsComparison.propTypes = {
  /** 比较标题 */
  title: PropTypes.node,
  /** 比较描述 */
  description: PropTypes.node,
  /** 结果数据 */
  results: PropTypes.arrayOf(
    PropTypes.shape({
      algorithm: PropTypes.string.isRequired,
      metrics: PropTypes.object.isRequired
    })
  ),
  /** 指标定义 */
  metrics: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      description: PropTypes.string,
      higherIsBetter: PropTypes.bool,
      minValue: PropTypes.number,
      maxValue: PropTypes.number
    })
  ),
  /** 算法定义 */
  algorithms: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      icon: PropTypes.node,
      description: PropTypes.string
    })
  ),
  /** 加载状态 */
  loading: PropTypes.bool,
  /** 是否显示最佳值标记 */
  showBest: PropTypes.bool,
  /** 是否显示差异标记 */
  showDifference: PropTypes.bool,
  /** 最佳值是越高越好还是越低越好 */
  bestHigher: PropTypes.bool,
  /** 小数位数 */
  decimalPlaces: PropTypes.number,
  /** 视图模式: table | bar | line */
  viewMode: PropTypes.oneOf(['table', 'bar', 'line']),
  /** 视图模式改变回调 */
  onViewModeChange: PropTypes.func,
  /** 自定义类名 */
  className: PropTypes.string,
  /** 自定义样式 */
  style: PropTypes.object
};

export default ResultsComparison; 