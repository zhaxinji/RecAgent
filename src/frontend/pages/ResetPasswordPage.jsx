import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { 
  Form, 
  Input, 
  Button, 
  Typography, 
  Card, 
  message,
  Alert,
  Result
} from 'antd';
import { 
  LockOutlined, 
  ArrowLeftOutlined,
  CheckCircleOutlined
} from '@ant-design/icons';
import { authAPI } from '../services/api';

const { Title, Text, Paragraph } = Typography;

// 从URL参数中获取token
function useQuery() {
  return new URLSearchParams(useLocation().search);
}

const ResetPasswordPage = () => {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const [tokenValid, setTokenValid] = useState(true);
  const [resetSuccess, setResetSuccess] = useState(false);
  const query = useQuery();
  const token = query.get('token');
  const navigate = useNavigate();

  // 检查是否有令牌
  useEffect(() => {
    if (!token) {
      setTokenValid(false);
    }
  }, [token]);

  const onFinish = async (values) => {
    if (values.new_password !== values.confirm_password) {
      message.error('两次输入的密码不一致');
      return;
    }

    setLoading(true);
    try {
      // 调用重置密码API
      await authAPI.resetPassword(token, values.new_password);
      
      setResetSuccess(true);
      message.success('密码重置成功');
      
      // 3秒后跳转到登录页
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (error) {
      console.error('重置错误:', error);
      
      // 显示友好的错误消息
      const errorMsg = error.response?.data?.detail || '重置失败，请重试或请求新的重置链接';
      message.error(errorMsg);
      
      // 如果是令牌无效的错误，更新状态
      if (error.response?.status === 400) {
        setTokenValid(false);
      }
    } finally {
      setLoading(false);
    }
  };

  const renderContent = () => {
    if (!token) {
      return (
        <Alert
          message="链接无效"
          description="缺少密码重置令牌，请通过忘记密码页面重新申请。"
          type="error"
          showIcon
          action={
            <Button size="small" type="primary" onClick={() => navigate('/forgot-password')}>
              重新申请
            </Button>
          }
        />
      );
    }

    if (!tokenValid) {
      return (
        <Alert
          message="链接无效"
          description="您的密码重置链接已过期或无效，请重新申请重置密码。"
          type="error"
          showIcon
          action={
            <Button size="small" type="primary" onClick={() => navigate('/forgot-password')}>
              重新申请
            </Button>
          }
        />
      );
    }

    if (resetSuccess) {
      return (
        <Result
          icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
          title="密码重置成功"
          subTitle="您的密码已成功更新，3秒后将跳转到登录页面"
          extra={[
            <Button 
              type="primary" 
              key="login" 
              onClick={() => navigate('/login')}
            >
              立即登录
            </Button>
          ]}
        />
      );
    }

    return (
      <>
        <Title level={2} className="auth-title">重置密码</Title>
        <Paragraph className="auth-subtitle">
          请设置您的新密码
        </Paragraph>
        
        <Form
          form={form}
          name="reset_password_form"
          onFinish={onFinish}
          size="large"
          className="auth-form"
        >
          <Form.Item
            name="new_password"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 8, message: '密码长度不能少于8个字符' }
            ]}
          >
            <Input.Password 
              prefix={<LockOutlined className="auth-input-icon" />} 
              placeholder="新密码" 
              className="auth-input"
            />
          </Form.Item>

          <Form.Item
            name="confirm_password"
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
              prefix={<LockOutlined className="auth-input-icon" />} 
              placeholder="确认新密码" 
              className="auth-input"
            />
          </Form.Item>

          <Form.Item className="auth-button-container">
            <Button 
              type="primary" 
              htmlType="submit" 
              block 
              loading={loading}
              className="auth-button"
            >
              重置密码
            </Button>
          </Form.Item>
        </Form>
      </>
    );
  };

  return (
    <div className="auth-container">
      <div className="auth-card-wrapper">
        <Card 
          bordered={false} 
          className="auth-card"
        >
          {renderContent()}
          
          {!resetSuccess && tokenValid && (
            <div className="auth-alt-action">
              <Link to="/login" className="auth-link">
                <ArrowLeftOutlined /> 返回登录
              </Link>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default ResetPasswordPage; 