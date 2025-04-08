import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { 
  Comment, 
  Avatar, 
  List, 
  Form, 
  Button, 
  Input, 
  Tooltip, 
  Typography, 
  Space,
  Popconfirm,
  Divider,
  Card
} from 'antd';
import { 
  LikeOutlined, 
  LikeFilled, 
  DislikeOutlined, 
  DislikeFilled, 
  CommentOutlined,
  DeleteOutlined,
  EditOutlined,
  MoreOutlined,
  SendOutlined
} from '@ant-design/icons';
import moment from 'moment';
import 'moment/locale/zh-cn';
import LoadingState from './LoadingState';
import EmptyState from './EmptyState';
import { themeColors } from '../theme/themeConfig';

moment.locale('zh-cn');
const { TextArea } = Input;
const { Text, Paragraph } = Typography;

/**
 * 评论编辑器组件
 */
const CommentEditor = ({
  onSubmit,
  onCancel,
  submitting = false,
  value = '',
  onChange,
  placeholder = '写下您的评论...',
  autoFocus = false,
  submitText = '提交',
  cancelText = '取消',
  showCancel = false,
  rows = 4
}) => {
  return (
    <div style={{ marginBottom: 20 }}>
      <Form.Item>
        <TextArea 
          rows={rows} 
          value={value} 
          onChange={onChange} 
          placeholder={placeholder}
          disabled={submitting}
          autoFocus={autoFocus}
        />
      </Form.Item>
      <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
        <Space>
          {showCancel && (
            <Button 
              onClick={onCancel} 
              disabled={submitting}
            >
              {cancelText}
            </Button>
          )}
          <Button 
            type="primary" 
            onClick={onSubmit} 
            loading={submitting}
            icon={<SendOutlined />}
          >
            {submitText}
          </Button>
        </Space>
      </Form.Item>
    </div>
  );
};

/**
 * 单个评论组件
 */
const SingleComment = ({
  comment,
  currentUser,
  onLike,
  onDislike,
  onReply,
  onEdit,
  onDelete,
  children,
  highlightId,
}) => {
  const [submitting, setSubmitting] = useState(false);
  const [replyValue, setReplyValue] = useState('');
  const [showReplyEditor, setShowReplyEditor] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(comment.content);
  
  // 当前用户是否是评论作者
  const isAuthor = currentUser && currentUser.id === comment.author.id;
  
  // 处理回复逻辑
  const handleReply = async () => {
    if (!replyValue.trim()) return;
    
    setSubmitting(true);
    try {
      await onReply(comment.id, replyValue);
      setReplyValue('');
      setShowReplyEditor(false);
    } catch (error) {
      console.error('Reply failed:', error);
    } finally {
      setSubmitting(false);
    }
  };

  // 处理编辑逻辑
  const handleEdit = async () => {
    if (!editValue.trim()) return;
    
    setSubmitting(true);
    try {
      await onEdit(comment.id, editValue);
      setIsEditing(false);
    } catch (error) {
      console.error('Edit failed:', error);
    } finally {
      setSubmitting(false);
    }
  };

  // 渲染操作按钮
  const actions = [
    <Tooltip key="like" title="赞同">
      <Space onClick={() => onLike && onLike(comment.id)} style={{ cursor: 'pointer' }}>
        {comment.liked ? <LikeFilled style={{ color: themeColors.primary.main }} /> : <LikeOutlined />}
        <Text style={{ color: comment.liked ? themeColors.primary.main : 'inherit' }}>
          {comment.likes > 0 && comment.likes}
        </Text>
      </Space>
    </Tooltip>,
    <Tooltip key="dislike" title="不赞同">
      <Space onClick={() => onDislike && onDislike(comment.id)} style={{ cursor: 'pointer' }}>
        {comment.disliked ? <DislikeFilled style={{ color: themeColors.error.main }} /> : <DislikeOutlined />}
        <Text style={{ color: comment.disliked ? themeColors.error.main : 'inherit' }}>
          {comment.dislikes > 0 && comment.dislikes}
        </Text>
      </Space>
    </Tooltip>,
    <span key="reply" onClick={() => setShowReplyEditor(!showReplyEditor)} style={{ cursor: 'pointer' }}>
      <Space>
        <CommentOutlined />
        <Text>回复</Text>
      </Space>
    </span>
  ];
  
  // 如果是作者，添加编辑和删除操作
  if (isAuthor) {
    actions.push(
      <span key="edit" onClick={() => setIsEditing(true)} style={{ cursor: 'pointer' }}>
        <Space>
          <EditOutlined />
          <Text>编辑</Text>
        </Space>
      </span>,
      <Popconfirm
        key="delete"
        title="确定要删除这条评论吗？"
        onConfirm={() => onDelete && onDelete(comment.id)}
        okText="确定"
        cancelText="取消"
      >
        <span style={{ cursor: 'pointer' }}>
          <Space>
            <DeleteOutlined />
            <Text>删除</Text>
          </Space>
        </span>
      </Popconfirm>
    );
  }

  // 计算评论时间
  const formattedTime = moment(comment.createdAt).fromNow();
  
  // 渲染评论内容
  const renderContent = () => {
    if (isEditing) {
      return (
        <CommentEditor
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onSubmit={handleEdit}
          onCancel={() => {
            setIsEditing(false);
            setEditValue(comment.content);
          }}
          submitting={submitting}
          showCancel={true}
          autoFocus={true}
          rows={3}
          submitText="保存"
        />
      );
    }
    
    return (
      <div style={{ 
        padding: '8px 0',
        backgroundColor: highlightId === comment.id ? themeColors.background.paper : 'transparent',
        transition: 'background-color 0.3s ease',
        borderRadius: 4
      }}>
        <Paragraph>{comment.content}</Paragraph>
        {comment.edited && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            (已编辑)
          </Text>
        )}
      </div>
    );
  };

  // 渲染回复编辑器
  const renderReplyEditor = () => {
    if (!showReplyEditor) return null;
    
    return (
      <CommentEditor
        value={replyValue}
        onChange={(e) => setReplyValue(e.target.value)}
        onSubmit={handleReply}
        onCancel={() => setShowReplyEditor(false)}
        submitting={submitting}
        showCancel={true}
        autoFocus={true}
        rows={2}
        placeholder={`回复 ${comment.author.name}...`}
      />
    );
  };

  return (
    <Comment
      actions={actions}
      author={<Text strong>{comment.author.name}</Text>}
      avatar={<Avatar src={comment.author.avatar} alt={comment.author.name}>{comment.author.name[0]}</Avatar>}
      content={renderContent()}
      datetime={
        <Tooltip title={moment(comment.createdAt).format('YYYY-MM-DD HH:mm:ss')}>
          <Text type="secondary">{formattedTime}</Text>
        </Tooltip>
      }
    >
      {renderReplyEditor()}
      {children}
    </Comment>
  );
};

/**
 * 评论列表组件
 */
const Comments = ({
  comments = [],
  currentUser,
  loading = false,
  onSubmit,
  onLike,
  onDislike,
  onReply,
  onEdit,
  onDelete,
  title = '评论',
  emptyText = '暂无评论',
  emptyDescription = '成为第一个发表评论的人吧',
  highlightId,
  className = '',
  style = {}
}) => {
  const [submitting, setSubmitting] = useState(false);
  const [commentValue, setCommentValue] = useState('');
  
  // 提交评论
  const handleSubmit = async () => {
    if (!commentValue.trim()) return;
    
    setSubmitting(true);
    try {
      await onSubmit(commentValue);
      setCommentValue('');
    } catch (error) {
      console.error('Submit comment failed:', error);
    } finally {
      setSubmitting(false);
    }
  };

  // 递归渲染评论树
  const renderCommentTree = (commentList, parentId = null) => {
    const filteredComments = commentList.filter(c => c.parentId === parentId);
    
    if (filteredComments.length === 0) return null;
    
    return filteredComments.map(comment => (
      <SingleComment
        key={comment.id}
        comment={comment}
        currentUser={currentUser}
        onLike={onLike}
        onDislike={onDislike}
        onReply={onReply}
        onEdit={onEdit}
        onDelete={onDelete}
        highlightId={highlightId}
      >
        {renderCommentTree(commentList, comment.id)}
      </SingleComment>
    ));
  };

  // 渲染评论列表内容
  const renderCommentsContent = () => {
    if (loading) {
      return <LoadingState type="list" rows={3} />;
    }
    
    if (comments.length === 0) {
      return (
        <EmptyState 
          title={emptyText}
          description={emptyDescription}
          compact={true}
          style={{ padding: '16px 0' }}
        />
      );
    }
    
    return renderCommentTree(comments);
  };

  return (
    <div 
      className={`comments-section ${className}`}
      style={{
        ...style
      }}
    >
      <Card 
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <CommentOutlined />
              <span>{title}</span>
              {comments.length > 0 && <Text type="secondary">({comments.length})</Text>}
            </Space>
          </div>
        }
        bordered={false}
      >
        {currentUser && (
          <>
            <Comment
              avatar={<Avatar src={currentUser.avatar} alt={currentUser.name}>{currentUser.name[0]}</Avatar>}
              content={
                <CommentEditor
                  value={commentValue}
                  onChange={(e) => setCommentValue(e.target.value)}
                  onSubmit={handleSubmit}
                  submitting={submitting}
                />
              }
            />
            <Divider />
          </>
        )}
        {renderCommentsContent()}
      </Card>
    </div>
  );
};

Comments.propTypes = {
  /** 评论数据 */
  comments: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      author: PropTypes.shape({
        id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
        name: PropTypes.string.isRequired,
        avatar: PropTypes.string
      }).isRequired,
      content: PropTypes.string.isRequired,
      createdAt: PropTypes.oneOfType([PropTypes.string, PropTypes.number, PropTypes.object]).isRequired,
      likes: PropTypes.number,
      dislikes: PropTypes.number,
      liked: PropTypes.bool,
      disliked: PropTypes.bool,
      edited: PropTypes.bool,
      parentId: PropTypes.oneOfType([PropTypes.string, PropTypes.number])
    })
  ),
  /** 当前用户信息 */
  currentUser: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    name: PropTypes.string.isRequired,
    avatar: PropTypes.string
  }),
  /** 加载状态 */
  loading: PropTypes.bool,
  /** 提交评论回调 */
  onSubmit: PropTypes.func.isRequired,
  /** 点赞回调 */
  onLike: PropTypes.func,
  /** 点踩回调 */
  onDislike: PropTypes.func,
  /** 回复回调 */
  onReply: PropTypes.func,
  /** 编辑回调 */
  onEdit: PropTypes.func,
  /** 删除回调 */
  onDelete: PropTypes.func,
  /** 评论标题 */
  title: PropTypes.node,
  /** 空状态文本 */
  emptyText: PropTypes.node,
  /** 空状态描述 */
  emptyDescription: PropTypes.node,
  /** 高亮评论ID */
  highlightId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  /** 自定义类名 */
  className: PropTypes.string,
  /** 自定义样式 */
  style: PropTypes.object
};

export default Comments; 