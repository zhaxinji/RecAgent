import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  Form, 
  Input, 
  Button, 
  Checkbox, 
  Typography, 
  Card,
  message,
  Divider,
  Space
} from 'antd';
import { 
  UserOutlined, 
  LockOutlined,
  MailOutlined,
  LoginOutlined
} from '@ant-design/icons';
import { authAPI } from '../services/api';

const { Title, Text } = Typography;

const LoginPage = ({ setUser }) => {
  const [loading, setLoading] = useState(false);
  const [loginMethod, setLoginMethod] = useState('auto'); // 'auto', 'username', 'email'
  const [form] = Form.useForm(); // 获取表单实例
  const navigate = useNavigate();

  // 处理表单提交
  const handleSubmit = async (e) => {
    e.preventDefault(); // 阻止默认的表单提交行为
    
    try {
      // 获取表单值
      const values = await form.validateFields();
      setLoading(true);
      
      const inputValue = values.username;
      const isEmail = authAPI.isEmail(inputValue);
      let response;
      
      // 尝试登录
      if (isEmail) {
        // 使用邮箱登录接口
        response = await authAPI.loginWithEmail(inputValue, values.password);
      } else {
        // 使用标准登录接口
        response = await authAPI.login(inputValue, values.password);
      }
      
      // 获取令牌和用户数据
      const { access_token, user } = response.data;
      
      // 存储令牌到本地存储
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(user));
      
      // 更新应用中的用户状态
      setUser(user);
      
      // 导航到首页
      navigate('/');
    } catch (error) {
      console.error('登录错误:', error);
      
      // 解析并显示友好的错误消息
      let errorMsg = '登录失败，请检查您的凭据';
      
      if (error.response) {
        const status = error.response.status;
        const serverError = error.response.data?.detail;
        
        if (status === 401) {
          errorMsg = serverError || '用户名或密码不正确，请重试';
        } else if (status === 400) {
          errorMsg = serverError || '请求格式错误，请检查输入';
        } else if (status === 404) {
          errorMsg = '登录服务暂时不可用，请稍后再试';
        } else if (status >= 500) {
          errorMsg = '服务器错误，请联系管理员或稍后再试';
        }
      } else if (error.request) {
        // 请求发送但没收到响应
        errorMsg = '无法连接到服务器，请检查您的网络连接';
      } else if (error.errorFields) {
        // 表单验证错误
        errorMsg = '请检查输入内容是否正确';
      }
      
      // 显示错误消息，设置更长的显示时间
      message.error(errorMsg, 2); // 显示10秒，确保用户能看到
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card-wrapper">
        <Card 
          bordered={false} 
          className="auth-card"
        >
          <Title level={2} className="auth-title">用户登录</Title>
          
          <Form
            form={form}
            name="login_form"
            initialValues={{ remember: true }}
            size="large"
            className="auth-form"
            // 重要：不要使用onFinish，它会与我们的自定义处理冲突
          >
            <Form.Item
              name="username"
              rules={[
                { 
                  required: true, 
                  message: '请输入用户名或邮箱' 
                },
                {
                  validator: (_, value) => {
                    if (!value) return Promise.resolve();
                    
                    // 邮箱格式验证
                    if (value.includes('@')) {
                      const isValidEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
                      if (!isValidEmail) {
                        return Promise.reject('邮箱格式不正确');
                      }
                    }
                    return Promise.resolve();
                  }
                }
              ]}
            >
              <Input 
                prefix={<UserOutlined className="auth-input-icon" />} 
                placeholder="用户名或邮箱" 
                className="auth-input"
                autoComplete="username"
                onChange={(e) => {
                  const value = e.target.value;
                  if (value.includes('@')) {
                    setLoginMethod('email');
                  } else if (value.length > 0) {
                    setLoginMethod('username');
                  } else {
                    setLoginMethod('auto');
                  }
                }}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码长度不能少于6个字符' }
              ]}
            >
              <Input.Password 
                prefix={<LockOutlined className="auth-input-icon" />} 
                placeholder="密码" 
                className="auth-input"
                autoComplete="current-password"
              />
            </Form.Item>

            <div className="auth-options">
              <Form.Item name="remember" valuePropName="checked" noStyle>
                <Checkbox>记住我</Checkbox>
              </Form.Item>
              <Link to="/forgot-password" className="auth-link">忘记密码？</Link>
            </div>

            <Form.Item className="auth-button-container">
              <Button 
                type="primary" 
                block 
                loading={loading}
                className="auth-button"
                icon={<LoginOutlined />}
                onClick={handleSubmit}
                htmlType="button" // 改为button类型，避免触发表单提交
              >
                {loading ? '登录中...' : '登录'}
              </Button>
            </Form.Item>
            
            <div className="auth-tips">
              <Text type="secondary">
                {loginMethod === 'email' ? 
                  '正在使用邮箱登录，请确保邮箱格式正确' : 
                  loginMethod === 'username' ? 
                  '正在使用用户名登录' : 
                  '支持用户名或邮箱登录'}
              </Text>
            </div>
            
            <div className="auth-alt-action">
              <Link to="/register" className="auth-link">
                还没有账号？立即注册
              </Link>
            </div>
          </Form>
          
          <Divider plain className="auth-divider">
            <Text type="secondary" style={{ fontSize: '12px' }}>或</Text>
          </Divider>
          
          <div className="auth-guest">
            <Button 
              block 
              onClick={() => navigate('/')}
              className="auth-guest-button"
            >
              以访客身份浏览
            </Button>
          </div>
          
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

export default LoginPage; 