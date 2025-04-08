import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  Form, 
  Input, 
  Button, 
  Typography, 
  Card, 
  message,
  Result
} from 'antd';
import { MailOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { authAPI } from '../services/api';

const { Title, Text, Paragraph } = Typography;

const ForgotPasswordPage = () => {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const [emailSent, setEmailSent] = useState(false);

  const onFinish = async (values) => {
    setLoading(true);
    try {
      // 调用忘记密码API
      await authAPI.requestPasswordReset(values.email);
      
      setEmailSent(true);
      message.success('重置链接已发送到您的邮箱');
    } catch (error) {
      console.error('请求错误:', error);
      
      // 显示友好的错误消息
      const errorMsg = error.response?.data?.detail || '请求失败，请稍后再试';
      message.error(errorMsg);
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
          {!emailSent ? (
            <>
              <Title level={2} className="auth-title">找回密码</Title>
              <Paragraph className="auth-subtitle">
                请输入您的注册邮箱，我们将向您发送重置密码的链接
              </Paragraph>
              
              <Form
                form={form}
                name="forgot_password_form"
                onFinish={onFinish}
                size="large"
                className="auth-form"
              >
                <Form.Item
                  name="email"
                  rules={[
                    { required: true, message: '请输入您的邮箱' },
                    { type: 'email', message: '请输入有效的邮箱地址' }
                  ]}
                >
                  <Input 
                    prefix={<MailOutlined className="auth-input-icon" />} 
                    placeholder="您的邮箱" 
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
                    发送重置链接
                  </Button>
                </Form.Item>
              </Form>
            </>
          ) : (
            <Result
              status="success"
              title="重置链接已发送"
              subTitle={
                <div>
                  <p>我们已向您的邮箱发送了密码重置链接</p>
                  <p>请查收邮件并点击链接进行密码重置</p>
                </div>
              }
            />
          )}
          
          <div className="auth-alt-action">
            <Link to="/login" className="auth-link">
              <ArrowLeftOutlined /> 返回登录
            </Link>
          </div>
        </Card>
      </div>
      
      <style jsx global>{`
        .auth-container {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 100vh;
          background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
          padding: 20px;
        }
        
        .auth-card-wrapper {
          width: 100%;
          max-width: 420px;
        }
        
        .auth-card {
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
          border-radius: 12px;
        }
        
        .auth-title {
          text-align: center;
          margin-bottom: 8px;
        }
        
        .auth-subtitle {
          text-align: center;
          margin-bottom: 24px;
          color: rgba(0, 0, 0, 0.45);
        }
        
        .auth-form {
          margin-bottom: 24px;
        }
        
        .auth-input-icon {
          color: rgba(0, 0, 0, 0.25);
        }
        
        .auth-options {
          display: flex;
          justify-content: space-between;
          margin-bottom: 24px;
        }
        
        .auth-button-container {
          margin-top: 24px;
          margin-bottom: 0;
        }
        
        .auth-button {
          height: 45px;
          font-size: 16px;
          background: linear-gradient(to right, #4481eb, #04befe);
          border: none;
        }
        
        .auth-alt-action {
          text-align: center;
          margin-top: 16px;
        }
        
        .auth-link {
          font-size: 14px;
          color: #1890ff;
        }
        
        .auth-divider {
          margin: 24px 0;
        }
        
        .auth-guest {
          margin-bottom: 24px;
        }
        
        .auth-guest-button {
          height: 45px;
          font-size: 16px;
        }
        
        .auth-footer {
          text-align: center;
        }
      `}</style>
    </div>
  );
};

export default ForgotPasswordPage; 