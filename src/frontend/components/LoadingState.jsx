import React from 'react';
import PropTypes from 'prop-types';
import { Spin, Typography, Card, Skeleton } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';

const { Title, Paragraph } = Typography;

/**
 * 美观的加载状态组件
 * 提供多种加载样式，适应不同的场景需求
 */
const LoadingState = ({
  title,
  description,
  size = 'default', // 'small', 'default', 'large'
  type = 'spin', // 'spin', 'skeleton', 'card'
  height,
  loading = true,
  icon, // 自定义图标
  children,
  delay = 0, // 延迟显示加载状态
  bordered = true, // Card模式下是否有边框
  active = true, // Skeleton模式下是否有动画
  rows = 3, // Skeleton模式下的段落行数
  className = '',
  style = {}
}) => {
  // 渲染骨架屏
  const renderSkeleton = () => (
    <div 
      className={`loading-skeleton ${className}`}
      style={{ 
        padding: type === 'card' ? 0 : 24,
        height,
        ...style 
      }}
    >
      <Skeleton 
        active={active} 
        title={{ width: '40%' }}
        paragraph={{ rows, width: ['60%', '90%', '80%'] }}
      />
    </div>
  );

  // 渲染加载中
  const renderSpin = () => {
    // 设置图标大小
    let iconSize = 24;
    if (size === 'small') iconSize = 16;
    if (size === 'large') iconSize = 32;

    // 自定义图标或默认图标
    const loadingIcon = icon || <LoadingOutlined style={{ fontSize: iconSize }} spin />;

    return (
      <div 
        className={`loading-spin ${className}`}
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 24,
          height,
          ...style
        }}
      >
        <Spin indicator={loadingIcon} size={size} style={{ marginBottom: 16 }} />
        
        {title && (
          <Title 
            level={5} 
            style={{ 
              marginTop: 8, 
              marginBottom: description ? 4 : 0,
              fontSize: size === 'small' ? 14 : size === 'large' ? 18 : 16
            }}
          >
            {title}
          </Title>
        )}
        
        {description && (
          <Paragraph 
            type="secondary"
            style={{ 
              marginBottom: 0,
              textAlign: 'center',
              maxWidth: 300,
              fontSize: size === 'small' ? 12 : 14
            }}
          >
            {description}
          </Paragraph>
        )}
      </div>
    );
  };

  // 渲染卡片形式
  const renderCard = () => (
    <Card
      loading={true}
      className={`loading-card ${className}`}
      style={{
        height,
        borderRadius: 8,
        ...style
      }}
      bordered={bordered}
    >
      {renderSkeleton()}
    </Card>
  );

  // 根据加载状态决定是否显示子组件
  if (!loading) {
    return children || null;
  }

  // 根据类型选择不同的加载样式
  if (type === 'skeleton') {
    return renderSkeleton();
  } else if (type === 'card') {
    return renderCard();
  } else {
    return renderSpin();
  }
};

LoadingState.propTypes = {
  /** 加载标题 */
  title: PropTypes.node,
  /** 加载描述 */
  description: PropTypes.node,
  /** 加载大小 */
  size: PropTypes.oneOf(['small', 'default', 'large']),
  /** 加载类型 */
  type: PropTypes.oneOf(['spin', 'skeleton', 'card']),
  /** 加载区域高度 */
  height: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  /** 是否加载中 */
  loading: PropTypes.bool,
  /** 自定义加载图标 */
  icon: PropTypes.node,
  /** 非加载状态时显示的内容 */
  children: PropTypes.node,
  /** 延迟显示加载状态的时间(毫秒) */
  delay: PropTypes.number,
  /** Card模式下是否有边框 */
  bordered: PropTypes.bool,
  /** Skeleton模式下是否有动画 */
  active: PropTypes.bool,
  /** Skeleton模式下的段落行数 */
  rows: PropTypes.number,
  /** 自定义类名 */
  className: PropTypes.string,
  /** 自定义样式 */
  style: PropTypes.object
};

export default LoadingState; 