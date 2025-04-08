import React from 'react';
import PropTypes from 'prop-types';
import { Empty, Button, Typography, Space } from 'antd';
import { PlusOutlined } from '@ant-design/icons';

const { Title, Paragraph } = Typography;

/**
 * 美观的空状态组件
 * 为空数据状态提供友好的用户体验，支持图标、标题、描述、按钮和自定义内容
 */
const EmptyState = ({
  image,
  title,
  description,
  buttonText,
  buttonIcon = <PlusOutlined />,
  onButtonClick,
  secondaryButtonText,
  onSecondaryButtonClick,
  extra,
  compact = false,
  className = '',
  style = {}
}) => {
  return (
    <div 
      className={`empty-state ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: compact ? '24px' : '48px 24px',
        textAlign: 'center',
        backgroundColor: '#ffffff',
        borderRadius: 8,
        ...style
      }}
    >
      <Empty
        image={image || Empty.PRESENTED_IMAGE_SIMPLE}
        imageStyle={{
          height: compact ? 80 : 120,
          marginBottom: compact ? 16 : 24
        }}
        description={false}
      />

      {title && (
        <Title 
          level={compact ? 5 : 4} 
          style={{ 
            marginTop: 0,
            marginBottom: 8,
            fontSize: compact ? 16 : 20 
          }}
        >
          {title}
        </Title>
      )}

      {description && (
        <Paragraph 
          type="secondary"
          style={{ 
            maxWidth: 480,
            marginBottom: buttonText ? 24 : 0,
            fontSize: compact ? 13 : 14
          }}
        >
          {description}
        </Paragraph>
      )}

      {(buttonText || secondaryButtonText) && (
        <Space size={8}>
          {buttonText && (
            <Button
              type="primary"
              icon={buttonIcon}
              onClick={onButtonClick}
              size={compact ? 'middle' : 'large'}
            >
              {buttonText}
            </Button>
          )}

          {secondaryButtonText && (
            <Button
              onClick={onSecondaryButtonClick}
              size={compact ? 'middle' : 'large'}
            >
              {secondaryButtonText}
            </Button>
          )}
        </Space>
      )}

      {extra && (
        <div 
          className="empty-state-extra"
          style={{ marginTop: buttonText ? 16 : 24 }}
        >
          {extra}
        </div>
      )}
    </div>
  );
};

EmptyState.propTypes = {
  /** 自定义图片 */
  image: PropTypes.node,
  /** 标题文本 */
  title: PropTypes.node,
  /** 描述文本 */
  description: PropTypes.node,
  /** 主按钮文本 */
  buttonText: PropTypes.string,
  /** 主按钮图标 */
  buttonIcon: PropTypes.node,
  /** 主按钮点击回调 */
  onButtonClick: PropTypes.func,
  /** 次要按钮文本 */
  secondaryButtonText: PropTypes.string,
  /** 次要按钮点击回调 */
  onSecondaryButtonClick: PropTypes.func,
  /** 额外内容 */
  extra: PropTypes.node,
  /** 紧凑模式 */
  compact: PropTypes.bool,
  /** 自定义类名 */
  className: PropTypes.string,
  /** 自定义样式 */
  style: PropTypes.object
};

export default EmptyState; 