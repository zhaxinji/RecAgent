import React from 'react';
import PropTypes from 'prop-types';
import { Card, Statistic, Typography, Space, Tooltip } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { themeColors } from '../theme/themeConfig';

const { Text } = Typography;

/**
 * 统计数据卡片组件
 * 用于显示关键指标的数据卡片，支持图标、标题、数值、趋势和脚注
 */
const StatsCard = ({
  title,
  value,
  precision = 0,
  prefix,
  suffix,
  loading = false,
  icon,
  iconBackground,
  iconColor = '#fff',
  footer,
  tooltip,
  trend,
  trendUp = true,
  onClick,
  className = '',
  style = {}
}) => {
  // 趋势颜色
  const trendColor = trendUp
    ? themeColors.functional.success.main
    : themeColors.functional.error.main;

  // 图标背景色
  const bgColor = iconBackground || themeColors.primary.main;

  return (
    <Card
      hoverable={!!onClick}
      onClick={onClick}
      className={`stats-card ${className}`}
      style={{
        borderRadius: 8,
        overflow: 'hidden',
        cursor: onClick ? 'pointer' : 'default',
        ...style
      }}
      bodyStyle={{ padding: 20 }}
      loading={loading}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 8 }}>
        <Space align="center" size={4}>
          <Text 
            style={{ 
              fontSize: 15, 
              fontWeight: 500, 
              color: 'rgba(0, 0, 0, 0.85)' 
            }}
          >
            {title}
          </Text>
          
          {tooltip && (
            <Tooltip title={tooltip} placement="top">
              <QuestionCircleOutlined 
                style={{ 
                  color: 'rgba(0, 0, 0, 0.45)',
                  fontSize: 14 
                }} 
              />
            </Tooltip>
          )}
        </Space>

        {icon && (
          <div style={{
            backgroundColor: bgColor,
            width: 32,
            height: 32,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: iconColor,
            fontSize: 16
          }}>
            {icon}
          </div>
        )}
      </div>

      <Statistic 
        value={value} 
        precision={precision}
        prefix={prefix}
        suffix={suffix}
        valueStyle={{ 
          fontSize: 28, 
          fontWeight: 600, 
          lineHeight: 1.2,
          color: 'rgba(0, 0, 0, 0.85)' 
        }} 
      />

      {trend && (
        <div style={{ marginTop: 8 }}>
          <Text
            style={{
              color: trendColor,
              fontSize: 14,
            }}
          >
            {trend}
          </Text>
        </div>
      )}

      {footer && (
        <div style={{ 
          marginTop: trend ? 4 : 16, 
          color: 'rgba(0, 0, 0, 0.45)', 
          fontSize: 13 
        }}>
          {footer}
        </div>
      )}
    </Card>
  );
};

StatsCard.propTypes = {
  /** 卡片标题 */
  title: PropTypes.node.isRequired,
  /** 统计数值 */
  value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  /** 数值精度(小数位数) */
  precision: PropTypes.number,
  /** 前缀 */
  prefix: PropTypes.node,
  /** 后缀 */
  suffix: PropTypes.node,
  /** 加载状态 */
  loading: PropTypes.bool,
  /** 图标 */
  icon: PropTypes.node,
  /** 图标背景色 */
  iconBackground: PropTypes.string,
  /** 图标颜色 */
  iconColor: PropTypes.string,
  /** 底部文本 */
  footer: PropTypes.node,
  /** 提示信息 */
  tooltip: PropTypes.node,
  /** 趋势文本 */
  trend: PropTypes.node,
  /** 趋势是否向上(绿色) */
  trendUp: PropTypes.bool,
  /** 点击事件 */
  onClick: PropTypes.func,
  /** 自定义类名 */
  className: PropTypes.string,
  /** 自定义样式 */
  style: PropTypes.object
};

export default StatsCard; 