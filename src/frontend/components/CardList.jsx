import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { 
  Card, 
  List, 
  Typography, 
  Space, 
  Pagination, 
  Empty, 
  Radio, 
  Dropdown,
  Button, 
  Menu 
} from 'antd';
import { 
  AppstoreOutlined, 
  BarsOutlined, 
  SortAscendingOutlined, 
  FilterOutlined,
  EllipsisOutlined
} from '@ant-design/icons';
import LoadingState from './LoadingState';
import EmptyState from './EmptyState';

const { Title, Text } = Typography;

/**
 * 卡片列表组件
 * 支持网格和列表两种视图模式，以及排序、筛选等功能
 */
const CardList = ({
  title,
  description,
  items = [],
  renderItem,
  renderCard,
  renderListItem,
  loading = false,
  pagination = null,
  viewMode = 'grid',
  onViewModeChange,
  sortOptions = [],
  onSortChange,
  filterOptions = [],
  onFilterChange,
  moreActions = [],
  emptyText = '暂无数据',
  emptyDescription = '没有找到匹配的数据',
  emptyButtonText,
  onEmptyButtonClick,
  grid = { gutter: 16, xs: 1, sm: 2, md: 2, lg: 3, xl: 4, xxl: 4 },
  className = '',
  style = {},
}) => {
  const [currentViewMode, setCurrentViewMode] = useState(viewMode);
  
  // 处理视图模式变更
  const handleViewModeChange = (e) => {
    const newMode = e.target.value;
    setCurrentViewMode(newMode);
    if (onViewModeChange) {
      onViewModeChange(newMode);
    }
  };

  // 处理排序变更
  const handleSortChange = ({ key }) => {
    if (onSortChange) {
      onSortChange(key);
    }
  };

  // 处理筛选变更
  const handleFilterChange = ({ key }) => {
    if (onFilterChange) {
      onFilterChange(key);
    }
  };

  // 处理更多操作
  const handleMoreAction = ({ key }) => {
    const action = moreActions.find(action => action.key === key);
    if (action && action.onClick) {
      action.onClick();
    }
  };

  // 渲染工具栏
  const renderToolbar = () => {
    return (
      <div 
        className="card-list-toolbar"
        style={{ 
          display: 'flex', 
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16 
        }}
      >
        <div className="card-list-info">
          {title && <Title level={4} style={{ marginBottom: 0 }}>{title}</Title>}
          {description && <Text type="secondary">{description}</Text>}
        </div>
        
        <Space>
          {sortOptions.length > 0 && (
            <Dropdown 
              overlay={
                <Menu onClick={handleSortChange}>
                  {sortOptions.map(option => (
                    <Menu.Item key={option.key}>{option.label}</Menu.Item>
                  ))}
                </Menu>
              } 
              trigger={['click']}
            >
              <Button icon={<SortAscendingOutlined />}>
                排序
              </Button>
            </Dropdown>
          )}
          
          {filterOptions.length > 0 && (
            <Dropdown 
              overlay={
                <Menu onClick={handleFilterChange}>
                  {filterOptions.map(option => (
                    <Menu.Item key={option.key}>{option.label}</Menu.Item>
                  ))}
                </Menu>
              } 
              trigger={['click']}
            >
              <Button icon={<FilterOutlined />}>
                筛选
              </Button>
            </Dropdown>
          )}
          
          {onViewModeChange && (
            <Radio.Group 
              value={currentViewMode}
              onChange={handleViewModeChange}
              optionType="button"
              buttonStyle="solid"
            >
              <Radio.Button value="grid">
                <AppstoreOutlined />
              </Radio.Button>
              <Radio.Button value="list">
                <BarsOutlined />
              </Radio.Button>
            </Radio.Group>
          )}
          
          {moreActions.length > 0 && (
            <Dropdown 
              overlay={
                <Menu onClick={handleMoreAction}>
                  {moreActions.map(action => (
                    <Menu.Item key={action.key} disabled={action.disabled}>
                      {action.icon && React.cloneElement(action.icon, { style: { marginRight: 8 } })}
                      {action.label}
                    </Menu.Item>
                  ))}
                </Menu>
              } 
              trigger={['click']}
            >
              <Button icon={<EllipsisOutlined />} />
            </Dropdown>
          )}
        </Space>
      </div>
    );
  };

  // 渲染列表内容
  const renderContent = () => {
    if (loading) {
      return (
        <LoadingState 
          type={currentViewMode === 'grid' ? 'skeleton' : 'list'}
          rows={4}
        />
      );
    }

    if (items.length === 0) {
      return (
        <EmptyState
          title={emptyText}
          description={emptyDescription}
          buttonText={emptyButtonText}
          onButtonClick={onEmptyButtonClick}
          style={{ padding: '40px 0' }}
        />
      );
    }

    const listProps = {
      dataSource: items,
      pagination: pagination === false ? false : {
        size: 'small',
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: total => `共 ${total} 条`,
        ...(typeof pagination === 'object' ? pagination : {})
      },
      renderItem: (item, index) => {
        // 使用custom渲染函数
        if (renderItem) {
          return renderItem(item, index);
        }
        
        // 根据视图模式选择渲染函数
        if (currentViewMode === 'grid' && renderCard) {
          return (
            <List.Item>
              {renderCard(item, index)}
            </List.Item>
          );
        }
        
        if (currentViewMode === 'list' && renderListItem) {
          return renderListItem(item, index);
        }
        
        // 默认渲染
        return (
          <List.Item>
            <Card title={item.title || `Item ${index + 1}`}>
              {item.content || '内容未定义'}
            </Card>
          </List.Item>
        );
      }
    };

    // 网格模式特有属性
    if (currentViewMode === 'grid') {
      listProps.grid = grid;
    }

    return <List {...listProps} />;
  };

  return (
    <div 
      className={`card-list ${className}`}
      style={{ 
        ...style 
      }}
    >
      {renderToolbar()}
      {renderContent()}
    </div>
  );
};

CardList.propTypes = {
  /** 列表标题 */
  title: PropTypes.node,
  /** 列表描述 */
  description: PropTypes.node,
  /** 数据项数组 */
  items: PropTypes.array,
  /** 自定义渲染项函数(优先级最高) */
  renderItem: PropTypes.func,
  /** 网格视图下的渲染函数 */
  renderCard: PropTypes.func,
  /** 列表视图下的渲染函数 */
  renderListItem: PropTypes.func,
  /** 加载状态 */
  loading: PropTypes.bool,
  /** 分页配置, 传入false禁用分页 */
  pagination: PropTypes.oneOfType([PropTypes.object, PropTypes.bool]),
  /** 视图模式: grid | list */
  viewMode: PropTypes.oneOf(['grid', 'list']),
  /** 视图模式改变回调 */
  onViewModeChange: PropTypes.func,
  /** 排序选项 */
  sortOptions: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      label: PropTypes.node.isRequired
    })
  ),
  /** 排序变更回调 */
  onSortChange: PropTypes.func,
  /** 筛选选项 */
  filterOptions: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      label: PropTypes.node.isRequired
    })
  ),
  /** 筛选变更回调 */
  onFilterChange: PropTypes.func,
  /** 更多操作选项 */
  moreActions: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      label: PropTypes.node.isRequired,
      icon: PropTypes.node,
      disabled: PropTypes.bool,
      onClick: PropTypes.func
    })
  ),
  /** 空数据文本 */
  emptyText: PropTypes.node,
  /** 空数据描述 */
  emptyDescription: PropTypes.node,
  /** 空数据按钮文本 */
  emptyButtonText: PropTypes.node,
  /** 空数据按钮点击回调 */
  onEmptyButtonClick: PropTypes.func,
  /** 网格配置 */
  grid: PropTypes.object,
  /** 自定义类名 */
  className: PropTypes.string,
  /** 自定义样式 */
  style: PropTypes.object
};

export default CardList; 