import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Form, 
  Input, 
  Button, 
  Select, 
  Typography, 
  Divider, 
  Space, 
  Tag, 
  Spin,
  List,
  Collapse,
  Steps,
  Tabs,
  message,
  Upload,
  Modal,
  Drawer,
  Alert,
  Empty,
  Radio,
  Tooltip,
  Row,
  Col
} from 'antd';
import { 
  EditOutlined, 
  FileTextOutlined, 
  PlusOutlined, 
  SaveOutlined,
  CopyOutlined,
  BookOutlined,
  InboxOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  HighlightOutlined,
  HistoryOutlined,
  FormatPainterOutlined,
  BulbOutlined
} from '@ant-design/icons';
import { writingApi } from '../../services/api';
import { useWriting } from '../../contexts/WritingContext';
import ReactMarkdown from 'react-markdown';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { Panel } = Collapse;
const { Step } = Steps;
const { TabPane } = Tabs;
const { Dragger } = Upload;

// 从API获取论文部分类型
const fetchPaperSections = async () => {
  try {
    const sections = await writingApi.getPaperSections();
    console.log('成功获取论文部分列表:', sections);
    if (!Array.isArray(sections) || sections.length === 0) {
      console.warn('获取到的论文部分列表为空');
      return [];
    }
    return sections;
  } catch (error) {
    console.error('获取论文部分失败:', error);
    message.error('无法获取论文部分列表，请检查网络连接后刷新页面');
    return [];
  }
};

// 从API获取写作风格
const fetchWritingStyles = async () => {
  try {
    const styles = await writingApi.getWritingStyles();
    console.log('成功获取写作风格列表:', styles);
    if (!Array.isArray(styles) || styles.length === 0) {
      console.warn('获取到的写作风格列表为空');
      return [];
    }
    return styles;
  } catch (error) {
    console.error('获取写作风格失败:', error);
    message.error('无法获取写作风格列表，请检查网络连接后刷新页面');
    return [];
  }
};

// 生成写作内容
const generateWriting = async (values) => {
  console.log('生成写作内容参数:', values);
  
  try {
    // 确保参数命名与后端API期望的一致
    const apiParams = {
      section_type: values.section_type,
      writing_style: values.writing_style,
      topic: values.topic,
      research_problem: values.research_problem,
      method_feature: values.method_feature,
      modeling_target: values.modeling_target,
      improvement: values.improvement,
      key_component: values.key_component,
      impact: values.impact,
      additional_context: values.additional_context
    };
    
    console.log('发送到API的参数:', apiParams);
    return await writingApi.generateContent(apiParams);
  } catch (error) {
    console.error('生成内容API调用失败:', error);
    throw error;
  }
};

// 写作助手组件
const WritingAssistant = ({ document, content }) => {
  // 使用WritingContext获取文档数据和加载状态
  const { loading: contextLoading, currentDocument, documentContent } = useWriting();
  
  // 状态管理
  const [form] = Form.useForm();
  const [generating, setGenerating] = useState(false);
  const [writingContent, setWritingContent] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [currentSection, setCurrentSection] = useState(null);
  const [editorVisible, setEditorVisible] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [history, setHistory] = useState([]);
  const [previewMode, setPreviewMode] = useState('edit');
  const [paperSections, setPaperSections] = useState([]);
  const [writingStyles, setWritingStyles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [initError, setInitError] = useState(null);
  
  // 设置初始内容
  useEffect(() => {
    // 如果有传入的文档内容，则使用它
    if (documentContent) {
      setWritingContent(documentContent);
      setEditedContent(documentContent);
    }
  }, [documentContent]);
  
  // 检查当前文档有效性
  useEffect(() => {
    if (currentDocument) {
      console.log('WritingAssistant: 接收到当前文档数据', currentDocument);
      if (currentDocument.sections && currentDocument.sections.length > 0) {
        setCurrentSection({
          value: 'current',
          label: currentDocument.sections[0].title || '当前章节'
        });
      }
    }
  }, [currentDocument]);
  
  // 加载论文部分和写作风格
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      setInitError(null);
      
      try {
        const [sections, styles] = await Promise.all([
          fetchPaperSections(),
          fetchWritingStyles()
        ]);
        
        // 检查返回的数据是否有效
        if (Array.isArray(sections) && sections.length > 0) {
          setPaperSections(sections);
        } else {
          console.warn('获取到的论文部分数据无效或为空');
          setPaperSections([]);
          message.warning('无法获取论文部分数据，请联系管理员');
        }
        
        if (Array.isArray(styles) && styles.length > 0) {
          setWritingStyles(styles);
        } else {
          console.warn('获取到的写作风格数据无效或为空');
          setWritingStyles([]);
          message.warning('无法获取写作风格数据，请联系管理员');
        }
      } catch (error) {
        console.error('加载数据失败:', error);
        setError('加载数据失败，请刷新页面重试');
        setInitError('无法加载论文部分和写作风格数据');
        message.error('加载数据失败，请刷新页面重试');
        // 使用空数组
        setPaperSections([]);
        setWritingStyles([]);
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
  }, []);
  
  // 生成写作内容
  const handleGenerate = async (values) => {
    setGenerating(true);
    setError(null);
    
    try {
      console.log('提交生成请求:', values);
      
      // 参数验证
      if (!values.section_type) {
        throw new Error('请选择论文部分');
      }
      
      // 添加到历史记录
      const timestamp = new Date().toLocaleString();
      const historyItem = {
        id: Date.now(),
        type: values.section_type,
        timestamp,
        content: null,
        params: { ...values }
      };
      
      // 防止表单值丢失，先保存一份
      const formValues = { ...values };
      
      // 发送请求
      const result = await generateWriting(values);
      console.log('生成内容结果:', result);
      
      // 更新内容
      if (result && result.content) {
        setWritingContent(result.content);
        setEditedContent(result.content);
        
        // 同时更新建议列表
        if (result.suggestions && Array.isArray(result.suggestions)) {
          setSuggestions(result.suggestions);
        } else {
          setSuggestions([]);
        }
        
        // 更新历史记录
        historyItem.content = result.content;
        setHistory(prev => [historyItem, ...prev]);
        
        // 显示成功消息
        message.success(`${values.section_type}部分内容生成成功！`);
      } else {
        throw new Error('生成的内容为空');
      }
    } catch (error) {
      console.error('生成内容失败:', error);
      setError(`生成内容失败: ${error.message || '未知错误'}`);
      message.error(`生成内容失败: ${error.message || '未知错误'}`);
      
      // 恢复表单值
      form.setFieldsValue(values);
    } finally {
      setGenerating(false);
    }
  };
  
  // 打开编辑器
  const openEditor = () => {
    setEditedContent(writingContent);
    setEditorVisible(true);
  };
  
  // 保存编辑内容
  const saveEdits = () => {
    // 保存当前内容到历史记录
    setHistory(prev => [...prev, {
      section: currentSection?.label || '未指定部分',
      content: writingContent,
      timestamp: new Date().toLocaleString()
    }]);
    
    setWritingContent(editedContent);
    setEditorVisible(false);
    message.success('内容已更新');
  };
  
  // 应用建议
  const applySuggestion = (suggestion) => {
    message.info(`正在应用建议: ${suggestion}`);
    // 实际应用中，这里会调用API获取基于建议的内容修改
    // 这里仅做示意
    setTimeout(() => {
      setEditedContent(prev => prev + `\n\n// 应用建议: ${suggestion}\n// 这里将显示根据建议修改的内容`);
      message.success('建议已应用');
    }, 500);
  };
  
  // 复制内容到剪贴板
  const copyContent = () => {
    navigator.clipboard.writeText(writingContent)
      .then(() => message.success('内容已复制到剪贴板'))
      .catch(() => message.error('复制失败，请手动复制'));
  };
  
  // 导出为Markdown文件
  const exportMarkdown = () => {
    const blob = new Blob([writingContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentSection?.label || '论文部分'}_${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
    
    message.success('内容已导出为Markdown文件');
  };
  
  // 查看历史版本
  const viewHistory = (item) => {
    setEditedContent(item.content);
    setEditorVisible(true);
  };
  
  // 论文内容展示区域
  const renderContentPreview = () => {
    if (generating) {
      return (
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <Spin size="large" tip="正在生成内容，请稍候..." />
          <div style={{ marginTop: 20, color: '#999' }}>
            生成高质量学术内容可能需要10-30秒，请耐心等待...
          </div>
        </div>
      );
    }
    
    if (!writingContent) {
      return (
        <Empty 
          image={Empty.PRESENTED_IMAGE_SIMPLE} 
          description="请选择论文部分并填写相关信息生成内容"
        />
      );
    }
    
    return (
      <div className="writing-preview">
        {previewMode === 'edit' ? (
          <div>
            <TextArea
              value={editedContent}
              onChange={e => setEditedContent(e.target.value)}
              autoSize={{ minRows: 10, maxRows: 20 }}
              style={{ marginBottom: 16 }}
            />
            <Space>
              <Button 
                type="primary" 
                icon={<SaveOutlined />} 
                onClick={saveEdits}
              >
                保存修改
              </Button>
              <Button 
                icon={<CopyOutlined />} 
                onClick={copyContent}
              >
                复制内容
              </Button>
            </Space>
          </div>
        ) : (
          <div>
            <div className="markdown-preview" style={{ padding: '0 16px' }}>
              <ReactMarkdown>{writingContent}</ReactMarkdown>
            </div>
            <Space style={{ marginTop: 16 }}>
              <Button 
                icon={<EditOutlined />} 
                onClick={() => setPreviewMode('edit')}
              >
                切换到编辑模式
              </Button>
              <Button 
                icon={<CopyOutlined />} 
                onClick={copyContent}
              >
                复制内容
              </Button>
            </Space>
          </div>
        )}
      </div>
    );
  };
  
  // 改进建议区域
  const renderSuggestions = () => {
    if (!suggestions || suggestions.length === 0) {
      return null;
    }
    
    return (
      <div className="writing-suggestions">
        <Divider orientation="left">
          <BulbOutlined /> 改进建议
        </Divider>
        <List
          size="small"
          dataSource={suggestions}
          renderItem={suggestion => (
            <List.Item 
              actions={[
                <Button 
                  type="link" 
                  size="small"
                  onClick={() => applySuggestion(suggestion)}
                >
                  应用
                </Button>
              ]}
            >
              <List.Item.Meta
                avatar={<BulbOutlined style={{ color: '#1890ff' }} />}
                description={suggestion}
              />
            </List.Item>
          )}
        />
      </div>
    );
  };
  
  return (
    <div className="writing-assistant">
      <Row gutter={24}>
        <Col span={10}>
          <Card 
            title="写作设置" 
            bordered={true}
            loading={loading}
          >
            {initError && (
              <Alert 
                message="初始化错误" 
                description={initError}
                type="error" 
                showIcon 
                style={{ marginBottom: 16 }}
              />
            )}
            
            <Form
              form={form}
              layout="vertical"
              onFinish={handleGenerate}
              initialValues={{
                section_type: 'abstract',
                writing_style: 'academic'
              }}
            >
              <Form.Item
                name="section_type"
                label={<span style={{ color: '#ff4d4f' }}>*论文部分</span>}
                rules={[{ required: true, message: '请选择论文部分' }]}
              >
                <Select 
                  placeholder="选择要生成的论文部分"
                  options={paperSections.map(section => ({
                    value: section.value,
                    label: section.label
                  }))}
                />
              </Form.Item>
              
              <Form.Item
                name="writing_style"
                label={<span style={{ color: '#ff4d4f' }}>*写作风格</span>}
                rules={[{ required: true, message: '请选择写作风格' }]}
              >
                <Select 
                  placeholder="选择写作风格"
                  options={writingStyles.map(style => ({
                    value: style.value,
                    label: style.label
                  }))}
                >
                </Select>
              </Form.Item>
              
              <Form.Item
                name="topic"
                label="研究主题"
              >
                <Input placeholder="如: 序列推荐、多模态推荐、知识图谱..." />
              </Form.Item>
              
              <Form.Item
                name="additional_context"
                label="额外背景信息"
              >
                <TextArea 
                  placeholder="补充研究背景、方法特点、数据集等额外信息，帮助AI生成更符合您研究主题的内容..."
                  rows={6}
                />
              </Form.Item>
              
              <Form.Item>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  block
                  loading={generating}
                  icon={<HighlightOutlined />}
                >
                  生成内容
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>
        
        <Col span={14}>
          <Card 
            title="摘要内容" 
            bordered={true}
            extra={
              <Radio.Group 
                value={previewMode} 
                onChange={e => setPreviewMode(e.target.value)}
                buttonStyle="solid"
                size="small"
              >
                <Radio.Button value="edit">编辑</Radio.Button>
                <Radio.Button value="preview">预览</Radio.Button>
              </Radio.Group>
            }
          >
            {error && (
              <Alert 
                message="错误" 
                description={error}
                type="error" 
                showIcon 
                style={{ marginBottom: 16 }}
                closable
                onClose={() => setError(null)}
              />
            )}
            
            {renderContentPreview()}
            {renderSuggestions()}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default WritingAssistant; 