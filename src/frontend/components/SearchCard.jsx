import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Input, Button, Card, Form, Row, Col, Collapse, Typography, Space, Divider } from 'antd';
import { SearchOutlined, ClearOutlined, FilterOutlined } from '@ant-design/icons';

const { Search } = Input;
const { Text } = Typography;
const { Panel } = Collapse;

/**
 * 搜索卡片组件
 * 提供美观的搜索界面，支持基础搜索和高级过滤
 */
const SearchCard = ({
  placeholder = '搜索...',
  onSearch,
  loading = false,
  advancedFilters,
  showFilterByDefault = false,
  extraActions,
  className = '',
  style = {}
}) => {
  const [form] = Form.useForm();
  const [showFilters, setShowFilters] = useState(showFilterByDefault);

  // 处理搜索
  const handleSearch = (value) => {
    const filters = form.getFieldsValue();
    if (onSearch) {
      onSearch(value, filters);
    }
  };

  // 清空筛选条件
  const handleClear = () => {
    form.resetFields();
    const value = form.getFieldValue('searchTerm');
    if (onSearch) {
      onSearch(value, {});
    }
  };

  // 提交表单
  const handleSubmit = () => {
    const values = form.getFieldsValue();
    const searchTerm = values.searchTerm || '';
    if (onSearch) {
      onSearch(searchTerm, values);
    }
  };

  return (
    <Card
      className={`search-card ${className}`}
      style={{
        borderRadius: 8,
        marginBottom: 24,
        ...style
      }}
      bodyStyle={{ padding: '16px 24px' }}
    >
      <Form form={form} onFinish={handleSubmit}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Form.Item name="searchTerm" style={{ marginBottom: 0 }}>
              <Search
                placeholder={placeholder}
                allowClear
                enterButton={
                  <Button 
                    type="primary" 
                    icon={<SearchOutlined />}
                    loading={loading}
                  >
                    搜索
                  </Button>
                }
                size="large"
                onSearch={handleSearch}
                loading={loading}
              />
            </Form.Item>
          </Col>

          <Col flex="none">
            <Space>
              {advancedFilters && (
                <Button
                  type={showFilters ? 'primary' : 'default'}
                  icon={<FilterOutlined />}
                  onClick={() => setShowFilters(!showFilters)}
                  ghost={showFilters}
                >
                  筛选
                </Button>
              )}
              {extraActions && extraActions}
            </Space>
          </Col>
        </Row>

        {advancedFilters && showFilters && (
          <>
            <Divider style={{ margin: '16px 0' }} />
            
            <div className="search-filters">
              <Row gutter={[16, 16]}>
                {advancedFilters.map((filter, index) => (
                  <Col xs={24} sm={12} md={8} lg={6} key={filter.name || index}>
                    <Form.Item
                      label={filter.label}
                      name={filter.name}
                      style={{ marginBottom: 8 }}
                    >
                      {filter.component}
                    </Form.Item>
                  </Col>
                ))}
              </Row>

              <Row justify="end" style={{ marginTop: 16 }}>
                <Space>
                  <Button onClick={handleClear} icon={<ClearOutlined />}>
                    清空
                  </Button>
                  <Button type="primary" onClick={handleSubmit} loading={loading}>
                    应用筛选
                  </Button>
                </Space>
              </Row>
            </div>
          </>
        )}
      </Form>
    </Card>
  );
};

SearchCard.propTypes = {
  /** 搜索框占位符 */
  placeholder: PropTypes.string,
  /** 搜索回调函数 (searchTerm, filters) => void */
  onSearch: PropTypes.func,
  /** 加载状态 */
  loading: PropTypes.bool,
  /** 高级过滤器配置 */
  advancedFilters: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      label: PropTypes.node.isRequired,
      component: PropTypes.node.isRequired
    })
  ),
  /** 默认显示筛选器 */
  showFilterByDefault: PropTypes.bool,
  /** 额外操作按钮 */
  extraActions: PropTypes.node,
  /** 自定义类名 */
  className: PropTypes.string,
  /** 自定义样式 */
  style: PropTypes.object
};

export default SearchCard; 