import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  Form, 
  Input, 
  Button, 
  Typography, 
  Card,
  message,
  Select,
  Tabs,
  Divider,
  Alert,
  Space
} from 'antd';
import { 
  UserOutlined, 
  LockOutlined, 
  MailOutlined,
  TeamOutlined,
  BookOutlined,
  CheckCircleOutlined,
  UserAddOutlined
} from '@ant-design/icons';

import { authAPI } from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

const RegisterPage = () => {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [registrationSuccess, setRegistrationSuccess] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState('');

  const onFinish = async (values) => {
    setLoading(true);
    
    try {
      // 准备注册数据
      const userData = {
        name: values.username,
        email: values.email,
        password: values.password,
        profile: {
          institution: values.institution || '',
          research_interests: values.research_interests || [],
          research_level: values.research_level || ''
        }
      };
      
      // 调用注册API
      await authAPI.register(userData);
      
      // 保存注册邮箱
      setRegisteredEmail(values.email);
      
      // 显示成功信息
      setRegistrationSuccess(true);
      message.success('注册成功！请查收验证邮件');
    } catch (error) {
      // 解析错误信息
      let errorMsg = '注册失败，请重试';
      
      if (error.response) {
        const status = error.response.status;
        const serverError = error.response.data?.detail;
        
        if (status === 400) {
          errorMsg = serverError || '该邮箱或用户名已被注册';
        } else if (status === 422) {
          errorMsg = '请求数据格式有误，请检查输入';
        } else if (status >= 500) {
          errorMsg = '服务器错误，请联系管理员或稍后再试';
        }
      } else if (error.request) {
        errorMsg = '无法连接到服务器，请检查您的网络连接';
      }
      
      message.error(errorMsg);
      console.error('注册错误:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleResendVerification = async () => {
    try {
      setLoading(true);
      await authAPI.resendVerification(registeredEmail);
      message.success('验证邮件已重新发送，请查收');
    } catch (error) {
      message.error('发送验证邮件失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleGoToLogin = () => {
    navigate('/login');
  };

  // 添加Tabs的items配置
  const tabItems = [
    {
      key: "1",
      label: "基本信息",
      children: (
        <>
          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '用户名不能少于3个字符' },
              { max: 30, message: '用户名不能超过30个字符' },
              { pattern: /^[a-zA-Z0-9_\u4e00-\u9fa5]+$/, message: '用户名只能包含字母、数字、下划线和中文' }
            ]}
          >
            <Input 
              prefix={<UserOutlined className="auth-input-icon" />} 
              placeholder="用户名" 
              className="auth-input"
              autoComplete="username"
            />
          </Form.Item>

          <Form.Item
            name="email"
            label="邮箱地址"
            rules={[
              { required: true, message: '请输入邮箱地址' },
              { type: 'email', message: '请输入有效的邮箱地址' }
            ]}
          >
            <Input 
              prefix={<MailOutlined className="auth-input-icon" />} 
              placeholder="邮箱地址" 
              className="auth-input"
              autoComplete="email"
            />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 8, message: '密码长度不能少于8个字符' },
              { 
                pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$/, 
                message: '密码必须包含大小写字母和数字' 
              }
            ]}
            hasFeedback
          >
            <Input.Password 
              prefix={<LockOutlined className="auth-input-icon" />} 
              placeholder="密码" 
              className="auth-input"
              autoComplete="new-password"
            />
          </Form.Item>

          <Form.Item
            name="confirm"
            label="确认密码"
            dependencies={['password']}
            hasFeedback
            rules={[
              { required: true, message: '请确认密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password 
              prefix={<LockOutlined className="auth-input-icon" />} 
              placeholder="确认密码" 
              className="auth-input"
              autoComplete="new-password"
            />
          </Form.Item>
        </>
      )
    },
    {
      key: "2",
      label: "研究信息（选填）",
      children: (
        <>
          <Form.Item
            name="institution"
            label="所属机构"
          >
            <Input 
              prefix={<TeamOutlined className="auth-input-icon" />} 
              placeholder="例如：北京大学、清华大学、微软研究院等" 
              className="auth-input"
            />
          </Form.Item>

          <Form.Item
            name="research_interests"
            label="研究方向"
          >
            <Select
              mode="multiple"
              placeholder="选择您的研究方向（可多选）"
              allowClear
              className="auth-select"
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
          
          <Form.Item
            name="research_level"
            label="研究水平"
          >
            <Select 
              placeholder="选择您的研究水平"
              className="auth-select"
            >
              <Option value="student">学生</Option>
              <Option value="researcher">研究人员</Option>
              <Option value="professor">教授</Option>
              <Option value="industry">业界从业者</Option>
              <Option value="other">其他</Option>
            </Select>
          </Form.Item>
        </>
      )
    }
  ];

  // 注册成功确认界面
  if (registrationSuccess) {
    return (
      <div className="auth-container">
        <div className="auth-card-wrapper">
          <Card 
            bordered={false} 
            className="auth-card register-success-card"
          >
            <div className="register-success">
              <CheckCircleOutlined className="success-icon" />
              <Title level={2}>注册成功！</Title>
              <Paragraph>
                我们已向您的邮箱 <strong>{registeredEmail}</strong> 发送了一封验证邮件。
                请查收邮件并点击验证链接以激活您的账户。
              </Paragraph>
              <Alert
                type="info"
                showIcon
                message="邮件可能需要几分钟时间送达，如果未收到，请检查垃圾邮件文件夹。"
                style={{ marginBottom: 20 }}
              />
              <Space direction="vertical" style={{ width: '100%' }}>
                <Button 
                  type="primary" 
                  onClick={handleGoToLogin} 
                  block
                  className="auth-button"
                >
                  前往登录
                </Button>
                <Button 
                  onClick={handleResendVerification} 
                  loading={loading} 
                  block
                >
                  重新发送验证邮件
                </Button>
              </Space>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-card-wrapper">
        <Card 
          bordered={false} 
          className="auth-card register-card"
        >
          <Title level={2} className="auth-title">用户注册</Title>
          
          <Form
            form={form}
            name="register_form"
            initialValues={{ agreement: true }}
            onFinish={onFinish}
            size="large"
            layout="vertical"
            className="auth-form"
          >
            <Tabs 
              defaultActiveKey="1" 
              items={tabItems} 
              className="auth-tabs"
            />

            <Form.Item className="auth-button-container">
              <Button 
                type="primary" 
                htmlType="submit" 
                block 
                loading={loading}
                className="auth-button"
                icon={<UserAddOutlined />}
              >
                {loading ? '注册中...' : '注册'}
              </Button>
            </Form.Item>
            
            <div className="auth-alt-action">
              <Link to="/login" className="auth-link">
                已有账号？立即登录
              </Link>
            </div>
          </Form>
          
          <div className="auth-footer">
            <Text type="secondary" style={{ fontSize: '12px' }}>
              RecAgent &copy; {new Date().getFullYear()} 推荐系统学术研究智能体
            </Text>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default RegisterPage; 