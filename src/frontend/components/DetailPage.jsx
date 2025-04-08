import React from 'react';
import PropTypes from 'prop-types';
import { 
  Card, 
  Typography, 
  Space, 
  Button, 
  Tag, 
  Divider, 
  Tabs, 
  PageHeader, 
  Avatar,
  Breadcrumb 
} from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import LoadingState from './LoadingState';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

/**
 * 详情页面组件
 * 提供详情页面的基础布局和常用功能
 */
const DetailPage = ({
  title,
  subtitle,
  description,
  avatar,
  icon,
  tags = [],
  loading = false,
  actions = [],
  extraContent,
  children,
  onBack,
  backText = '返回',
  backLink,
  footer,
  tabs = [],
  activeTabKey,
  onTabChange,
  breadcrumbs = [],
  extra,
  className = '',
  style = {}
}) => {
  const navigate = useNavigate();
  
  // 处理返回
  const handleBack = () => {
    if (onBack) {
      onBack();
    } else if (backLink) {
      navigate(backLink);
    } else {
      navigate(-1);
    }
  };

  // 渲染头部
  const renderHeader = () => {
    const headerProps = {
      onBack: handleBack,
      title: (
        <Space size={16} align="center">
          {avatar && <Avatar src={avatar} size="large" icon={icon} />}
          <div>
            <Title level={4} style={{ marginBottom: 0 }}>{title}</Title>
            {subtitle && <Text type="secondary">{subtitle}</Text>}
          </div>
        </Space>
      ),
      extra: (
        <Space>
          {actions.map((action, index) => (
            <Button
              key={index}
              type={action.primary ? 'primary' : action.type || 'default'}
              danger={action.danger}
              icon={action.icon}
              onClick={action.onClick}
              disabled={action.disabled}
            >
              {action.label}
            </Button>
          ))}
          {extra}
        </Space>
      )
    };

    // 如果有面包屑，添加到header
    if (breadcrumbs.length > 0) {
      headerProps.breadcrumb = (
        <Breadcrumb>
          {breadcrumbs.map((item, index) => (
            <Breadcrumb.Item key={index}>
              {item.link ? (
                <Link to={item.link}>{item.label}</Link>
              ) : (
                item.label
              )}
            </Breadcrumb.Item>
          ))}
        </Breadcrumb>
      );
    }

    return <PageHeader {...headerProps} />;
  };

  // 渲染标签
  const renderTags = () => {
    if (tags.length === 0) return null;
    
    return (
      <div style={{ marginBottom: 16 }}>
        <Space size={[0, 8]} wrap>
          {tags.map((tag, index) => {
            // 支持字符串或对象形式的标签
            if (typeof tag === 'string') {
              return <Tag key={index}>{tag}</Tag>;
            }
            
            return (
              <Tag
                key={index}
                color={tag.color}
                icon={tag.icon}
                closable={tag.closable}
                onClose={tag.onClose}
              >
                {tag.label}
              </Tag>
            );
          })}
        </Space>
      </div>
    );
  };

  // 渲染内容区域
  const renderContent = () => {
    // 加载状态
    if (loading) {
      return <LoadingState />;
    }
    
    // 描述内容
    const descriptionContent = description && (
      <div style={{ marginBottom: 24 }}>
        {typeof description === 'string' ? (
          <Paragraph>{description}</Paragraph>
        ) : (
          description
        )}
      </div>
    );
    
    // 附加内容
    const extraContentSection = extraContent && (
      <div style={{ marginBottom: 24 }}>
        {extraContent}
      </div>
    );

    // 标签内容
    const tagsContent = renderTags();
    
    // 显示标签页或普通内容
    const tabsOrContent = tabs.length > 0 ? (
      <Tabs activeKey={activeTabKey} onChange={onTabChange}>
        {tabs.map(tab => (
          <TabPane 
            tab={
              <span>
                {tab.icon && <span className="tab-icon">{tab.icon}</span>}
                {tab.label}
              </span>
            } 
            key={tab.key}
          >
            {tab.content}
          </TabPane>
        ))}
      </Tabs>
    ) : (
      children
    );

    return (
      <>
        {descriptionContent}
        {tagsContent}
        {extraContentSection}
        {tabsOrContent}
      </>
    );
  };

  return (
    <div 
      className={`detail-page ${className}`}
      style={{ 
        ...style 
      }}
    >
      {renderHeader()}
      
      <Card 
        bordered={false} 
        style={{ 
          marginTop: 16,
        }}
        bodyStyle={{ padding: 24 }}
      >
        {renderContent()}
      </Card>
      
      {footer && (
        <Card 
          bordered={false} 
          style={{ marginTop: 16 }}
          bodyStyle={{ padding: 16 }}
        >
          {footer}
        </Card>
      )}
    </div>
  );
};

DetailPage.propTypes = {
  /** 页面标题 */
  title: PropTypes.node.isRequired,
  /** 页面副标题 */
  subtitle: PropTypes.node,
  /** 详情描述 */
  description: PropTypes.node,
  /** 头像图片地址 */
  avatar: PropTypes.string,
  /** 图标组件 */
  icon: PropTypes.node,
  /** 标签列表 */
  tags: PropTypes.arrayOf(
    PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.shape({
        label: PropTypes.node.isRequired,
        color: PropTypes.string,
        icon: PropTypes.node,
        closable: PropTypes.bool,
        onClose: PropTypes.func
      })
    ])
  ),
  /** 加载状态 */
  loading: PropTypes.bool,
  /** 操作按钮列表 */
  actions: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.node.isRequired,
      onClick: PropTypes.func,
      icon: PropTypes.node,
      primary: PropTypes.bool,
      danger: PropTypes.bool,
      type: PropTypes.string,
      disabled: PropTypes.bool
    })
  ),
  /** 额外内容区域 */
  extraContent: PropTypes.node,
  /** 主要内容区域 */
  children: PropTypes.node,
  /** 返回按钮点击回调 */
  onBack: PropTypes.func,
  /** 返回按钮文本 */
  backText: PropTypes.string,
  /** 返回链接 */
  backLink: PropTypes.string,
  /** 底部内容 */
  footer: PropTypes.node,
  /** 标签页配置 */
  tabs: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      label: PropTypes.node.isRequired,
      icon: PropTypes.node,
      content: PropTypes.node
    })
  ),
  /** 当前激活的标签页 */
  activeTabKey: PropTypes.string,
  /** 标签页切换回调 */
  onTabChange: PropTypes.func,
  /** 面包屑配置 */
  breadcrumbs: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.node.isRequired,
      link: PropTypes.string
    })
  ),
  /** 额外的头部元素 */
  extra: PropTypes.node,
  /** 自定义类名 */
  className: PropTypes.string,
  /** 自定义样式 */
  style: PropTypes.object
};

export default DetailPage; 