import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Tag, Input, Tooltip, Button, Typography, Space } from 'antd';
import { PlusOutlined, SearchOutlined, CloseOutlined } from '@ant-design/icons';
import { themeColors } from '../theme/themeConfig';

const { Text } = Typography;

/**
 * 标签过滤器组件
 * 美观且功能强大的标签筛选组件，支持添加、删除、搜索标签
 */
const TagsFilter = ({
  title,
  tags = [],
  selectedTags = [],
  onChange,
  editable = false,
  onAdd,
  onRemove,
  colorMapping = {},
  showSearch = false,
  maxTagsShow = 20,
  className = '',
  style = {}
}) => {
  const [inputVisible, setInputVisible] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [searchValue, setSearchValue] = useState('');
  const [showAll, setShowAll] = useState(false);
  
  // 输入框引用
  const inputRef = React.useRef(null);

  // 输入框显示时自动聚焦
  useEffect(() => {
    if (inputVisible) {
      inputRef.current?.focus();
    }
  }, [inputVisible]);

  // 显示输入框
  const showInput = () => {
    setInputVisible(true);
  };

  // 处理输入变化
  const handleInputChange = (e) => {
    setInputValue(e.target.value);
  };

  // 处理输入确认
  const handleInputConfirm = () => {
    if (inputValue && onAdd) {
      onAdd(inputValue.trim());
    }
    setInputVisible(false);
    setInputValue('');
  };

  // 处理输入框按键事件
  const handleInputKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleInputConfirm();
    }
  };

  // 处理标签点击
  const handleTagClick = (tag) => {
    const newSelectedTags = [...selectedTags];
    const tagIndex = newSelectedTags.indexOf(tag);
    
    if (tagIndex !== -1) {
      newSelectedTags.splice(tagIndex, 1);
    } else {
      newSelectedTags.push(tag);
    }
    
    if (onChange) {
      onChange(newSelectedTags);
    }
  };

  // 处理标签删除
  const handleTagRemove = (e, tag) => {
    e.stopPropagation();
    if (onRemove) {
      onRemove(tag);
    }
  };

  // 过滤标签
  const filteredTags = tags.filter(tag => {
    if (!searchValue) return true;
    return tag.toLowerCase().includes(searchValue.toLowerCase());
  });

  // 显示标签
  const visibleTags = showAll ? filteredTags : filteredTags.slice(0, maxTagsShow);
  const hasMoreTags = filteredTags.length > maxTagsShow;

  // 获取标签颜色
  const getTagColor = (tag) => {
    // 如果有指定颜色映射，则使用映射
    if (colorMapping[tag]) {
      return colorMapping[tag];
    }
    
    // 如果已选中，则使用主色
    if (selectedTags.includes(tag)) {
      return themeColors.primary.main;
    }
    
    // 默认颜色
    return 'default';
  };

  return (
    <div 
      className={`tags-filter ${className}`}
      style={{
        marginBottom: 16,
        ...style
      }}
    >
      {title && (
        <div 
          className="tags-filter-header" 
          style={{ 
            marginBottom: 8,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center' 
          }}
        >
          <Text strong>{title}</Text>
          
          {showSearch && (
            <Input
              size="small"
              placeholder="搜索标签"
              prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
              style={{ width: 120 }}
              value={searchValue}
              onChange={e => setSearchValue(e.target.value)}
              allowClear
            />
          )}
        </div>
      )}
      
      <div className="tags-filter-content">
        {visibleTags.map(tag => (
          <Tag
            key={tag}
            color={getTagColor(tag)}
            style={{ 
              marginBottom: 8, 
              cursor: 'pointer',
              userSelect: 'none'
            }}
            onClick={() => handleTagClick(tag)}
            closable={editable}
            onClose={(e) => handleTagRemove(e, tag)}
          >
            {tag}
          </Tag>
        ))}
        
        {editable && (
          <>
            {inputVisible ? (
              <Input
                ref={inputRef}
                type="text"
                size="small"
                value={inputValue}
                onChange={handleInputChange}
                onBlur={handleInputConfirm}
                onPressEnter={handleInputConfirm}
                onKeyDown={handleInputKeyDown}
                style={{ width: 78 }}
              />
            ) : (
              <Tag 
                onClick={showInput}
                style={{ 
                  borderStyle: 'dashed',
                  marginBottom: 8,
                  cursor: 'pointer'
                }}
              >
                <PlusOutlined /> 新标签
              </Tag>
            )}
          </>
        )}
        
        {hasMoreTags && !showAll && (
          <Button
            type="link"
            size="small"
            onClick={() => setShowAll(true)}
            style={{ padding: '0 4px', height: 'auto' }}
          >
            查看全部 ({filteredTags.length})
          </Button>
        )}
        
        {showAll && hasMoreTags && (
          <Button
            type="link"
            size="small"
            onClick={() => setShowAll(false)}
            style={{ padding: '0 4px', height: 'auto' }}
          >
            收起
          </Button>
        )}
      </div>
      
      {selectedTags.length > 0 && (
        <div 
          className="tags-filter-selected" 
          style={{ 
            marginTop: 8,
            display: 'flex',
            alignItems: 'center'
          }}
        >
          <Text type="secondary" style={{ marginRight: 8, fontSize: 13 }}>
            已选: {selectedTags.length}
          </Text>
          
          <Button
            type="link"
            size="small"
            onClick={() => onChange([])}
            icon={<CloseOutlined />}
            style={{ padding: '0 4px', height: 'auto', fontSize: 13 }}
          >
            清除
          </Button>
        </div>
      )}
    </div>
  );
};

TagsFilter.propTypes = {
  /** 标题 */
  title: PropTypes.node,
  /** 所有标签数组 */
  tags: PropTypes.array,
  /** 已选标签数组 */
  selectedTags: PropTypes.array,
  /** 选择变化时的回调 */
  onChange: PropTypes.func,
  /** 是否可编辑（增删标签） */
  editable: PropTypes.bool,
  /** 添加标签的回调 */
  onAdd: PropTypes.func,
  /** 删除标签的回调 */
  onRemove: PropTypes.func,
  /** 标签颜色映射 */
  colorMapping: PropTypes.object,
  /** 是否显示搜索框 */
  showSearch: PropTypes.bool,
  /** 默认最多显示多少个标签 */
  maxTagsShow: PropTypes.number,
  /** 自定义类名 */
  className: PropTypes.string,
  /** 自定义样式 */
  style: PropTypes.object
};

export default TagsFilter; 