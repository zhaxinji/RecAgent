import React from 'react';
import PropTypes from 'prop-types';
import { Typography, Space, Breadcrumb, Divider, Row, Col, Tag } from 'antd';
import { Link } from 'react-router-dom';

const { Title, Paragraph } = Typography;

/**
 * 页面标题组件
 * 提供统一的页面标题、描述、面包屑和操作按钮区域
 */
const PageHeader = ({ 
  title, 
  subtitle, 
  breadcrumb = [], 
  tags = [], 
  extra,
  bordered = true,
  className = '',
  style = {}
}) => {
  return (
    <div 
      className={`page-header ${className}`} 
      style={{ 
        marginBottom: 24,
        background: '#fff',
        borderRadius: 4,
        padding: '16px 24px',
        boxShadow: bordered ? '0 1px 3px rgba(0, 0, 0, 0.05)' : 'none',
        ...style 
      }}
    >
      {breadcrumb.length > 0 && (
        <Breadcrumb 
          className="mb-3"
          items={breadcrumb.map((item, index) => ({
            key: index,
            title: item.path ? <Link to={item.path}>{item.title}</Link> : item.title
          }))}
        />
      )}
      
      <Row align="middle" justify="space-between" wrap={false}>
        <Col flex="auto">
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <Title 
              level={4} 
              className="page-title mb-0" 
              style={{ 
                fontSize: 20,
                fontWeight: 600,
                marginBottom: 0,
                lineHeight: 1.4
              }}
            >
              {title}
            </Title>
            
            {tags.length > 0 && (
              <div className="page-tags">
                <Space size={4}>
                  {tags.map((tag, index) => (
                    <Tag key={index} color={tag.color || "blue"}>
                      {tag.text}
                    </Tag>
                  ))}
                </Space>
              </div>
            )}
            
            {subtitle && (
              <Paragraph 
                className="page-subtitle mb-0" 
                type="secondary"
                style={{ 
                  marginBottom: 0,
                  fontSize: 14
                }}
              >
                {subtitle}
              </Paragraph>
            )}
          </Space>
        </Col>
        
        {extra && (
          <Col flex="none">
            <div className="page-header-extra">
              {extra}
            </div>
          </Col>
        )}
      </Row>
      
      {bordered && <Divider style={{ margin: '16px 0 0 0' }} />}
    </div>
  );
};

PageHeader.propTypes = {
  /** 页面标题 */
  title: PropTypes.node.isRequired,
  /** 页面副标题/描述 */
  subtitle: PropTypes.node,
  /** 面包屑导航数据 */
  breadcrumb: PropTypes.arrayOf(PropTypes.shape({
    title: PropTypes.node,
    path: PropTypes.string
  })),
  /** 标签数据 */
  tags: PropTypes.arrayOf(PropTypes.shape({
    text: PropTypes.node,
    color: PropTypes.string
  })),
  /** 右侧额外内容，通常放置操作按钮 */
  extra: PropTypes.node,
  /** 是否显示底部边框 */
  bordered: PropTypes.bool,
  /** 自定义类名 */
  className: PropTypes.string,
  /** 自定义样式 */
  style: PropTypes.object
};

export default PageHeader; 