import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { 
  Card, 
  Table, 
  Tabs, 
  Button, 
  Row, 
  Col, 
  Statistic, 
  Select, 
  Space, 
  Tooltip,
  Empty,
  Divider
} from 'antd';
import { 
  BarChartOutlined, 
  LineChartOutlined, 
  TableOutlined, 
  DownloadOutlined,
  FilterOutlined,
  PercentageOutlined,
  AimOutlined,
  StarOutlined
} from '@ant-design/icons';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar
} from 'recharts';
import LoadingState from '../LoadingState';
import EmptyState from '../EmptyState';

const { TabPane } = Tabs;
const { Option } = Select;

// 为图表准备数据
const prepareChartData = (results, metrics, kValues) => {
  if (!results || !results.length) return [];
  
  // 为条形图准备数据
  const barData = metrics.map(metric => {
    const data = {};
    data.name = metric.id; // 使用指标名称作为条形图的名称
    
    // 为每个算法添加数据
    results.forEach(result => {
      // 我们假设每个结果都有一个metrics对象，包含各个指标的值
      const algorithmName = result.algorithm;
      if (result.metrics && result.metrics[metric.id] !== undefined) {
        data[algorithmName] = result.metrics[metric.id];
      }
    });
    
    return data;
  });
  
  // 为k值折线图准备数据
  const lineData = [];
  if (kValues && kValues.length) {
    kValues.forEach(k => {
      const kData = { name: `K=${k}` };
      
      results.forEach(result => {
        const algorithmName = result.algorithm;
        // 这里我们假设结果中有针对不同k值的指标数据
        // 实际情况可能需要根据API返回的数据结构进行调整
        if (result.metrics && result.metrics[`ndcg@${k}`] !== undefined) {
          kData[algorithmName] = result.metrics[`ndcg@${k}`];
        }
      });
      
      lineData.push(kData);
    });
  }
  
  // 为雷达图准备数据
  const radarData = results.map(result => {
    const data = { name: result.algorithm };
    
    metrics.forEach(metric => {
      if (result.metrics && result.metrics[metric.id] !== undefined) {
        data[metric.id] = result.metrics[metric.id];
      }
    });
    
    return data;
  });
  
  return { barData, lineData, radarData };
};

const ExperimentResults = ({ 
  experiment, 
  results, 
  loading, 
  onExport 
}) => {
  const [selectedMetric, setSelectedMetric] = useState(experiment?.metrics?.[0] || 'recall');
  const [selectedK, setSelectedK] = useState(experiment?.k_values?.[0] || 10);
  
  if (loading) {
    return <LoadingState />;
  }
  
  if (!experiment || !results || !results.length) {
    return (
      <EmptyState
        title="暂无实验结果"
        description="尚未运行实验或尚未产生实验结果"
        buttonText="运行实验"
        buttonIcon={<BarChartOutlined />}
      />
    );
  }
  
  // 简单处理算法名称，使其更可读
  const formatAlgorithmName = (name) => {
    return name.split('-').map(part => part.charAt(0).toUpperCase() + part.slice(1)).join(' ');
  };
  
  // 提取算法和指标数据
  const algorithms = experiment.algorithms.map(algo => algo.id);
  const metricsList = experiment.metrics.map(metricId => {
    // 这里应该根据metricId获取指标的详细信息
    // 简化处理，仅使用ID
    return { id: metricId, name: metricId.charAt(0).toUpperCase() + metricId.slice(1) };
  });
  
  // 准备图表数据
  const chartData = prepareChartData(results, metricsList, experiment.k_values);
  
  // 随机生成一些颜色
  const colors = ['#1890ff', '#13c2c2', '#52c41a', '#faad14', '#f5222d', '#722ed1'];
  
  // 表格列定义
  const columns = [
    {
      title: '算法',
      dataIndex: 'algorithm',
      key: 'algorithm',
      render: text => formatAlgorithmName(text)
    }
  ];
  
  // 为每个指标添加列
  metricsList.forEach((metric, index) => {
    columns.push({
      title: metric.name,
      dataIndex: ['metrics', metric.id],
      key: metric.id,
      render: value => (value ? value.toFixed(4) : '-'),
      sorter: (a, b) => {
        const aValue = a.metrics && a.metrics[metric.id] ? a.metrics[metric.id] : 0;
        const bValue = b.metrics && b.metrics[metric.id] ? b.metrics[metric.id] : 0;
        return aValue - bValue;
      }
    });
  });
  
  // 最佳和最差指标高亮显示
  const findBestAlgorithm = (metric) => {
    if (!results || !results.length) return null;
    
    let bestAlgorithm = null;
    let bestValue = -Infinity;
    
    results.forEach(result => {
      if (result.metrics && result.metrics[metric] !== undefined) {
        if (result.metrics[metric] > bestValue) {
          bestValue = result.metrics[metric];
          bestAlgorithm = result.algorithm;
        }
      }
    });
    
    return bestAlgorithm ? { algorithm: formatAlgorithmName(bestAlgorithm), value: bestValue } : null;
  };
  
  const bestAlgorithm = findBestAlgorithm(selectedMetric);
  
  return (
    <Card title="实验结果">
      <Tabs defaultActiveKey="charts">
        <TabPane 
          tab={
            <span>
              <BarChartOutlined />
              图表
            </span>
          } 
          key="charts"
        >
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col xs={24} sm={8} md={6}>
              <Card>
                <Statistic
                  title="对比算法数量"
                  value={algorithms.length}
                  prefix={<AimOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8} md={6}>
              <Card>
                <Statistic
                  title="评估指标数量"
                  value={metricsList.length}
                  prefix={<PercentageOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8} md={12}>
              <Card>
                <Statistic
                  title={`最佳算法 (${selectedMetric})`}
                  value={bestAlgorithm ? bestAlgorithm.algorithm : '-'}
                  suffix={bestAlgorithm ? `(${(bestAlgorithm.value * 100).toFixed(2)}%)` : ''}
                  prefix={<StarOutlined />}
                />
              </Card>
            </Col>
          </Row>
          
          <Card 
            title="实验指标对比" 
            extra={
              <Space>
                <Select 
                  value={selectedMetric} 
                  onChange={setSelectedMetric}
                  style={{ width: 120 }}
                  placeholder="选择指标"
                >
                  {metricsList.map(metric => (
                    <Option key={metric.id} value={metric.id}>{metric.name}</Option>
                  ))}
                </Select>
                <Tooltip title="导出数据">
                  <Button 
                    icon={<DownloadOutlined />} 
                    onClick={onExport}
                  />
                </Tooltip>
              </Space>
            }
          >
            <Row gutter={[16, 16]}>
              <Col xs={24} md={12}>
                <div style={{ height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={chartData.barData}
                      margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <RechartsTooltip />
                      <Legend />
                      {algorithms.map((algorithm, index) => (
                        <Bar 
                          key={algorithm} 
                          dataKey={algorithm} 
                          name={formatAlgorithmName(algorithm)} 
                          fill={colors[index % colors.length]} 
                        />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Col>
              <Col xs={24} md={12}>
                <div style={{ height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart 
                      cx="50%" 
                      cy="50%" 
                      outerRadius="80%" 
                      data={chartData.radarData}
                    >
                      <PolarGrid />
                      <PolarAngleAxis dataKey="name" />
                      <PolarRadiusAxis />
                      {metricsList.map((metric, index) => (
                        <Radar
                          key={metric.id}
                          name={metric.name}
                          dataKey={metric.id}
                          stroke={colors[index % colors.length]}
                          fill={colors[index % colors.length]}
                          fillOpacity={0.6}
                        />
                      ))}
                      <Legend />
                      <RechartsTooltip />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </Col>
            </Row>
            
            <Divider>K值敏感性分析</Divider>
            
            <Card 
              title="TopK指标对比"
              extra={
                <Select 
                  value={selectedK} 
                  onChange={setSelectedK}
                  style={{ width: 80 }}
                  placeholder="K值"
                >
                  {experiment.k_values.map(k => (
                    <Option key={k} value={k}>K={k}</Option>
                  ))}
                </Select>
              }
            >
              <div style={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={chartData.lineData}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <RechartsTooltip />
                    <Legend />
                    {algorithms.map((algorithm, index) => (
                      <Line
                        key={algorithm}
                        type="monotone"
                        dataKey={algorithm}
                        name={formatAlgorithmName(algorithm)}
                        stroke={colors[index % colors.length]}
                        activeDot={{ r: 8 }}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </Card>
        </TabPane>
        
        <TabPane 
          tab={
            <span>
              <TableOutlined />
              表格数据
            </span>
          } 
          key="table"
        >
          <Card 
            title="实验原始数据" 
            extra={
              <Button 
                icon={<DownloadOutlined />} 
                onClick={onExport}
              >
                导出CSV
              </Button>
            }
          >
            <Table 
              columns={columns} 
              dataSource={results} 
              rowKey="algorithm"
              pagination={false}
            />
          </Card>
        </TabPane>
      </Tabs>
    </Card>
  );
};

ExperimentResults.propTypes = {
  experiment: PropTypes.shape({
    id: PropTypes.string,
    name: PropTypes.string,
    description: PropTypes.string,
    algorithms: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.string,
      name: PropTypes.string
    })),
    metrics: PropTypes.arrayOf(PropTypes.string),
    k_values: PropTypes.arrayOf(PropTypes.number),
    dataset: PropTypes.object
  }),
  results: PropTypes.array,
  loading: PropTypes.bool,
  onExport: PropTypes.func
};

ExperimentResults.defaultProps = {
  loading: false,
  onExport: () => {}
};

export default ExperimentResults; 