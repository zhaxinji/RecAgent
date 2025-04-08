import React, { useState, useEffect } from 'react';
import { 
  Typography, 
  Card, 
  Form, 
  Input, 
  Button, 
  Select, 
  Switch, 
  Divider, 
  Tabs, 
  Row, 
  Col, 
  message,
  Space,
  List,
  Modal,
  Popconfirm,
  Avatar,
  Tag
} from 'antd';
import { 
  ApiOutlined, 
  SecurityScanOutlined, 
  UserOutlined, 
  LockOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  SettingOutlined,
  GlobalOutlined,
  CloudOutlined,
  ClockCircleOutlined,
  SafetyCertificateOutlined,
  TeamOutlined
} from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;

const SettingsPage = ({ user, setUser }) => {
  const [apiForm] = Form.useForm();
  const [passwordForm] = Form.useForm();
  const [profileForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [deleteModalVisible, setDeleteModalVisible] = useState(false);
  const [deleteConfirmInput, setDeleteConfirmInput] = useState('');
  const [userProfile, setUserProfile] = useState(null);

  // 获取用户令牌辅助函数
  const getAuthToken = () => {
    try {
      return localStorage.getItem('token') || '';
    } catch (error) {
      console.error('获取认证令牌失败:', error);
      return '';
    }
  };

  // 从API获取真实用户数据
  const loadUserData = async () => {
    try {
      console.log('正在从API获取真实用户数据...');
      const token = getAuthToken();
      
      if (!token) {
        message.error('用户未登录，请先登录');
        // 可能需要重定向到登录页
        window.location.href = '/login';
        return null;
      }
      
      // 使用JWT令牌调用API
      const response = await fetch('http://localhost:8001/api/userinfo', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        credentials: 'include'
      });
      
      if (response.status === 401) {
        message.error('认证失败，请重新登录');
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        // 重定向到登录页
        window.location.href = '/login';
        return null;
      }
      
      if (!response.ok) {
        throw new Error(`获取用户数据失败: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('成功获取用户数据:', data);
      setUserProfile(data);
      
      // 使用真实用户数据填充表单
      profileForm.setFieldsValue({
        name: data.name || '',
        email: data.email || '',
        institution: data.institution || '',
        research_interests: data.research_interests || []
      });
      
      return data;
    } catch (error) {
      console.error('获取用户数据失败:', error);
      message.error(`获取用户数据失败: ${error.message}`);
      return null;
    }
  };

  // 初始化用户数据 - 同时尝试两种API路径
  const initializeUserProfile = async () => {
    try {
      console.log('尝试初始化用户资料...');
      const token = getAuthToken();
      
      if (!token) {
        message.error('用户未登录，请先登录');
        // 重定向到登录页
        window.location.href = '/login';
        return null;
      }
      
      // 使用JWT令牌初始化用户资料
      const response = await fetch('http://localhost:8001/api/init-profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        credentials: 'include',
        body: JSON.stringify({})
      });
      
      if (response.status === 401) {
        message.error('认证失败，请重新登录');
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        // 重定向到登录页
        window.location.href = '/login';
        return null;
      }
      
      if (!response.ok) {
        throw new Error(`初始化用户数据失败: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('成功初始化用户数据:', data);
      return await loadUserData();
    } catch (error) {
      console.error('初始化用户数据失败:', error);
      message.error(`初始化用户数据失败: ${error.message}`);
      return null;
    }
  };

  // 初始化表单数据
  useEffect(() => {
    const fetchData = async () => {
      let userData = await loadUserData();
      if (!userData) {
        // 如果获取数据失败，尝试初始化用户资料
        userData = await initializeUserProfile();
      }
    };
    
    fetchData();
  }, []);

  // 在组件顶部添加一个刷新函数，强制重新获取数据
  const forceRefreshUserData = async () => {
    try {
      console.log('强制刷新用户数据...');
      const userData = await loadUserData();
      
      if (userData) {
        console.log('刷新成功，用户数据:', userData);
        return true;
      }
      return false;
    } catch (error) {
      console.error('刷新用户数据失败:', error);
      return false;
    }
  };

  // 修改handleProfileUpdate函数，更好地处理和显示研究方向
  const handleProfileUpdate = async (values) => {
    setLoading(true);
    
    try {
      console.log('更新个人资料:', values);
      const token = getAuthToken();
      
      if (!token) {
        message.error('用户未登录，请先登录');
        setLoading(false);
        return;
      }
      
      // 确保research_interests是数组
      let researchInterests = values.research_interests;
      if (typeof researchInterests === 'string') {
        researchInterests = researchInterests.split(',').map(item => item.trim()).filter(Boolean);
      } else if (!Array.isArray(researchInterests)) {
        researchInterests = researchInterests ? [researchInterests] : [];
      }
      
      console.log('处理后的研究方向:', researchInterests);
      console.log('研究方向类型:', typeof researchInterests, Array.isArray(researchInterests));
      
      // 准备要发送的数据
      const requestData = {
        institution: values.institution || '',
        research_interests: researchInterests
      };
      
      console.log('发送的请求数据:', JSON.stringify(requestData));
      
      // 调用API更新用户资料，使用JWT令牌
      const response = await fetch('http://localhost:8001/api/update-research', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        credentials: 'include',
        body: JSON.stringify(requestData)
      });
      
      if (response.status === 401) {
        message.error('认证失败，请重新登录');
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setLoading(false);
        // 重定向到登录页
        window.location.href = '/login';
        return;
      }
      
      if (!response.ok) {
        throw new Error(`更新个人资料失败: ${response.status} ${response.statusText}`);
      }
      
      // 获取API返回的更新后数据
      const updatedData = await response.json();
      console.log('获取到的更新后数据:', updatedData);
      
      // 检查profile数据是否存在和格式是否正确
      if (updatedData) {
        // 直接更新UI状态，确保使用正确的字段名
        const updatedProfile = {
          ...userProfile,
          institution: updatedData.institution || values.institution || '',
          research_interests: Array.isArray(updatedData.research_interests) 
            ? updatedData.research_interests 
            : (typeof updatedData.research_interests === 'string' && updatedData.research_interests)
              ? [updatedData.research_interests]
              : researchInterests
        };
        
        console.log('更新后的用户资料:', updatedProfile);
        setUserProfile(updatedProfile);
        
        // 更新表单数据，确保表单与实际数据一致
        profileForm.setFieldsValue({
          name: updatedData.name || userProfile?.name || '',
          email: updatedData.email || userProfile?.email || '',
          institution: updatedData.institution || values.institution || '',
          research_interests: Array.isArray(updatedData.research_interests) 
            ? updatedData.research_interests 
            : (typeof updatedData.research_interests === 'string' && updatedData.research_interests)
              ? [updatedData.research_interests]
              : researchInterests
        });
        
        message.success('个人资料已更新');
        
        // 延迟1秒后强制刷新数据，确保从服务器获取最新数据
        setTimeout(() => {
          forceRefreshUserData();
        }, 1000);
      } else {
        console.warn('API返回数据无法解析或为空');
        message.warning('个人资料可能未完全更新，请刷新页面');
      }
    } catch (error) {
      message.error(`更新失败: ${error.message}`);
      console.error('更新失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 更新API设置
  const handleApiSettingsSave = async (values) => {
    setLoading(true);
    
    try {
      // 模拟API调用延迟
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // 实际项目中这里应该调用API
      console.log('更新API设置:', values);
      
      localStorage.setItem('api_settings', JSON.stringify(values));
      message.success('API设置已更新');
    } catch (error) {
      message.error('更新失败，请重试');
      console.error('更新失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 更新密码
  const handlePasswordChange = async (values) => {
    setLoading(true);
    
    try {
      console.log('更新密码:', values);
      const token = getAuthToken();
      
      if (!token) {
        message.error('用户未登录，请先登录');
        setLoading(false);
        return;
      }
      
      // 验证新密码与确认密码
      if (values.new_password !== values.confirm_password) {
        throw new Error('新密码与确认密码不一致');
      }
      
      // 调用API更新密码
      const response = await fetch('http://localhost:8001/api/update-password', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        credentials: 'include',
        body: JSON.stringify({
          current_password: values.current_password,
          new_password: values.new_password
        })
      });
      
      if (response.status === 401) {
        message.error('认证失败，请重新登录');
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setLoading(false);
        // 重定向到登录页
        window.location.href = '/login';
        return;
      }
      
      if (response.status === 400) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '当前密码不正确');
      }
      
      if (!response.ok) {
        throw new Error(`更新密码失败: ${response.status} ${response.statusText}`);
      }
      
      // 重置表单
      message.success('密码已成功更新');
      passwordForm.resetFields();
    } catch (error) {
      message.error(error.message || '更新失败，请重试');
      console.error('更新密码失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 删除账户
  const handleDeleteAccount = async () => {
    if (deleteConfirmInput !== userProfile?.email) {
      message.error('请输入正确的邮箱地址以确认删除');
      return;
    }
    
    setLoading(true);
    
    try {
      // 模拟API调用延迟
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // 实际项目中这里应该调用API
      console.log('删除账户:', user?.id);
      
      // 清除本地存储
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      
      // 更新用户状态
      setUser(null);
      
      message.success('账户已删除');
      
      // 重定向到首页
      window.location.href = '/';
    } catch (error) {
      message.error('操作失败，请重试');
      console.error('操作失败:', error);
    } finally {
      setLoading(false);
      setDeleteModalVisible(false);
      setDeleteConfirmInput('');
    }
  };

  return (
    <div className="settings-container">
      <div className="settings-header">
        <Title level={2}>
          <SettingOutlined /> 个人中心
        </Title>
        <Paragraph className="settings-subtitle">
          管理您的个人资料、研究环境和账户安全设置
        </Paragraph>
      </div>
      
      <Tabs defaultActiveKey="profile" className="settings-tabs">
        <TabPane 
          tab={
            <span>
              <UserOutlined />
              个人资料
            </span>
          } 
          key="profile"
        >
          <Row gutter={16}>
            <Col xs={24} md={8}>
              <Card className="profile-card">
                <div className="profile-header">
                  <div className="profile-info">
                    <Title level={4}>{userProfile?.name || '加载中...'}</Title>
                    <Text type="secondary">{userProfile?.email || '加载中...'}</Text>
                  </div>
                </div>
                <Divider />
                <div className="profile-details">
                  <p>
                    <TeamOutlined /> 所属机构: <Text strong>{userProfile?.institution || '未设置'}</Text>
                  </p>
                  <p>
                    <ClockCircleOutlined /> 加入时间: <Text>{userProfile?.join_date || '未知'}</Text>
                  </p>
                  <p>研究方向:</p>
                  <div className="profile-tags">
                    {userProfile?.research_interests && userProfile.research_interests.length > 0 
                      ? userProfile.research_interests.map(tag => (
                          <Tag key={tag} color="blue">{tag}</Tag>
                        ))
                      : <Text type="secondary">未设置研究方向</Text>
                    }
                  </div>
                </div>
              </Card>
            </Col>
            
            <Col xs={24} md={16}>
              <Card title="编辑个人资料">
                <Form
                  form={profileForm}
                  layout="vertical"
                  onFinish={handleProfileUpdate}
                  className="profile-form"
                >
                  <Form.Item
                    name="name"
                    label="姓名"
                  >
                    <Input prefix={<UserOutlined />} placeholder="您的姓名" disabled />
                  </Form.Item>
                  
                  <Form.Item
                    name="email"
                    label="电子邮箱"
                  >
                    <Input prefix={<UserOutlined />} placeholder="您的电子邮箱" disabled />
                  </Form.Item>
                  
                  <Form.Item
                    name="institution"
                    label="所属机构"
                  >
                    <Input placeholder="您的所属机构或大学" />
                  </Form.Item>
                  
                  <Form.Item
                    name="research_interests"
                    label="研究方向"
                  >
                    <Select
                      mode="multiple"
                      placeholder="选择您的研究方向（可多选）"
                      allowClear
                      style={{ width: "100%" }}
                    >
                      <Option value="序列推荐">序列推荐</Option>
                      <Option value="图神经网络推荐">图神经网络推荐</Option>
                      <Option value="多模态推荐">多模态推荐</Option>
                      <Option value="知识增强推荐">知识增强推荐</Option>
                      <Option value="对比学习推荐">对比学习推荐</Option>
                      <Option value="大模型推荐">大模型推荐</Option>
                      <Option value="可解释推荐">可解释推荐</Option>
                      <Option value="公平推荐">公平推荐</Option>
                      <Option value="冷启动推荐">冷启动推荐</Option>
                      <Option value="联邦推荐">联邦推荐</Option>
                      <Option value="强化学习推荐">强化学习推荐</Option>
                      <Option value="自监督推荐">自监督推荐</Option>
                    </Select>
                  </Form.Item>
                  
                  <Form.Item>
                    <Button type="primary" htmlType="submit" loading={loading}>
                      保存个人资料
                    </Button>
                  </Form.Item>
                </Form>
              </Card>
            </Col>
          </Row>
        </TabPane>
        
        <TabPane 
          tab={
            <span>
              <ApiOutlined />
              研究环境
            </span>
          } 
          key="api"
        >
          <Card className="settings-card">
            <Form
              form={apiForm}
              layout="vertical"
              onFinish={handleApiSettingsSave}
              initialValues={{
                language_model: 'deepseek',
              }}
            >
              <Row gutter={16}>
                <Col span={24}>
                  <Title level={4}>
                    <CloudOutlined /> 模型配置
                  </Title>
                  <Paragraph type="secondary">
                    配置您的大语言模型API，以获得最佳的研究助手体验
                  </Paragraph>
                  <Paragraph type="warning" style={{ color: '#ff4d4f' }}>
                    此功能暂未开放，敬请期待
                  </Paragraph>
                </Col>
                
                <Col xs={24} md={12}>
                  <Form.Item
                    name="api_key"
                    label="API密钥"
                    rules={[{ required: true, message: '请输入API密钥' }]}
                    extra="您的API密钥将被安全加密存储"
                  >
                    <Input.Password placeholder="请输入您的模型API密钥" disabled />
                  </Form.Item>
                </Col>
                
                <Col xs={24} md={12}>
                  <Form.Item
                    name="language_model"
                    label="模型提供商"
                  >
                    <Select disabled>
                      <Option value="deepseek">DeepSeek</Option>
                      <Option value="openai">OpenAI</Option>
                      <Option value="claude">Anthropic Claude</Option>
                      <Option value="local">本地模型</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
              
              <Form.Item className="form-actions">
                <Button type="primary" htmlType="submit" loading={loading} disabled>
                  保存环境设置
                </Button>
                <Button style={{ marginLeft: 8 }} disabled>
                  恢复默认设置
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>
        
        <TabPane 
          tab={
            <span>
              <SecurityScanOutlined />
              账户安全
            </span>
          } 
          key="security"
        >
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Card 
                title={
                  <span>
                    <LockOutlined /> 修改密码
                  </span>
                }
                className="settings-card"
              >
                <Form
                  form={passwordForm}
                  layout="vertical"
                  onFinish={handlePasswordChange}
                >
                  <Form.Item
                    name="current_password"
                    label="当前密码"
                    rules={[{ required: true, message: '请输入当前密码' }]}
                  >
                    <Input.Password 
                      prefix={<LockOutlined />} 
                      placeholder="请输入当前密码" 
                    />
                  </Form.Item>
                  
                  <Form.Item
                    name="new_password"
                    label="新密码"
                    rules={[
                      { required: true, message: '请输入新密码' },
                      { min: 8, message: '密码长度不能少于8个字符' }
                    ]}
                  >
                    <Input.Password 
                      prefix={<LockOutlined />} 
                      placeholder="请输入新密码" 
                    />
                  </Form.Item>
                  
                  <Form.Item
                    name="confirm_password"
                    label="确认新密码"
                    dependencies={['new_password']}
                    rules={[
                      { required: true, message: '请确认新密码' },
                      ({ getFieldValue }) => ({
                        validator(_, value) {
                          if (!value || getFieldValue('new_password') === value) {
                            return Promise.resolve();
                          }
                          return Promise.reject(new Error('两次输入的密码不一致'));
                        },
                      }),
                    ]}
                  >
                    <Input.Password 
                      prefix={<LockOutlined />} 
                      placeholder="请再次输入新密码" 
                    />
                  </Form.Item>
                  
                  <Form.Item>
                    <Button type="primary" htmlType="submit" loading={loading}>
                      更新密码
                    </Button>
                  </Form.Item>
                </Form>
              </Card>
            </Col>
          </Row>
        </TabPane>
      </Tabs>
      
      <style jsx global>{`
        .settings-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
        }
        
        .settings-header {
          margin-bottom: 24px;
          border-bottom: 1px solid #f0f0f0;
          padding-bottom: 16px;
        }
        
        .settings-subtitle {
          margin-bottom: 0;
          color: rgba(0, 0, 0, 0.45);
        }
        
        .settings-tabs {
          background: #fff;
          border-radius: 8px;
        }
        
        .settings-card {
          margin-bottom: 16px;
          border-radius: 8px;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
        }
        
        .profile-card {
          height: 100%;
        }
        
        .profile-header {
          display: flex;
          align-items: center;
          margin-bottom: 16px;
        }
        
        .profile-info {
          margin-left: 16px;
        }
        
        .profile-details p {
          margin-bottom: 8px;
        }
        
        .profile-tags {
          margin-top: 8px;
        }
        
        .avatar-uploader {
          display: flex;
          align-items: center;
          gap: 16px;
        }
        
        .danger-card {
          border-color: #ffccc7;
        }
        
        .card-title-danger {
          color: #ff4d4f;
        }
        
        .delete-warning {
          display: flex;
          margin-bottom: 16px;
          background-color: #fff2f0;
          padding: 16px;
          border-radius: 4px;
          border: 1px solid #ffccc7;
        }
        
        .warning-icon {
          font-size: 24px;
          color: #ff4d4f;
          margin-right: 16px;
        }
        
        .warning-text ul {
          margin-top: 8px;
          padding-left: 20px;
        }
        
        .danger-title {
          color: #ff4d4f;
        }
        
        .form-actions {
          margin-top: 24px;
        }
      `}</style>
    </div>
  );
};

export default SettingsPage; 