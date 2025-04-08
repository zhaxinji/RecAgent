import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Result, Button, Spin, Card, Alert } from 'antd';
import { CheckCircleOutlined, WarningOutlined, SyncOutlined } from '@ant-design/icons';

import { authAPI } from '../services/api';

// 从URL参数中获取token
function useQuery() {
  return new URLSearchParams(useLocation().search);
}

const VerifyEmailPage = () => {
  const navigate = useNavigate();
  const query = useQuery();
  const token = query.get('token');
  
  const [loading, setLoading] = useState(true);
  const [verified, setVerified] = useState(false);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    if (!token) {
      setLoading(false);
      setError('验证令牌缺失');
      return;
    }
    
    const verifyEmail = async () => {
      try {
        await authAPI.verifyEmail(token);
        setVerified(true);
      } catch (err) {
        console.error('邮箱验证失败', err);
        setError(err.response?.data?.detail || '邮箱验证失败，请稍后重试');
      } finally {
        setLoading(false);
      }
    };
    
    verifyEmail();
  }, [token]);
  
  const handleGoToLogin = () => {
    navigate('/login');
  };
  
  const handleGoToHome = () => {
    navigate('/');
  };
  
  if (loading) {
    return (
      <div className="verify-email-container">
        <Card className="verify-email-card">
          <div className="verify-loading">
            <Spin size="large" />
            <p>验证中，请稍候...</p>
          </div>
        </Card>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="verify-email-container">
        <Result
          status="error"
          title="邮箱验证失败"
          subTitle={error}
          icon={<WarningOutlined />}
          extra={[
            <Button type="primary" key="home" onClick={handleGoToHome}>
              返回首页
            </Button>,
            <Button key="login" onClick={handleGoToLogin}>
              前往登录
            </Button>
          ]}
        />
      </div>
    );
  }
  
  return (
    <div className="verify-email-container">
      <Result
        status="success"
        title="邮箱验证成功"
        subTitle="您的邮箱已成功验证，现在可以使用RecAgent的所有功能了"
        icon={<CheckCircleOutlined />}
        extra={[
          <Button type="primary" key="login" onClick={handleGoToLogin}>
            前往登录
          </Button>,
          <Button key="home" onClick={handleGoToHome}>
            返回首页
          </Button>
        ]}
      />
    </div>
  );
};

export default VerifyEmailPage; 