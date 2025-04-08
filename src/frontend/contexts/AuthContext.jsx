import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';
import { message } from 'antd';

// 创建认证上下文
const AuthContext = createContext();

/**
 * 认证上下文提供者组件
 * @param {Object} props - 组件属性
 * @returns {JSX.Element} 上下文提供者
 */
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token') || null);

  // 检查用户是否已登录
  useEffect(() => {
    const checkAuthStatus = async () => {
      if (token) {
        setLoading(true);
        try {
          // 配置请求头
          axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          
          // 获取当前用户信息
          const response = await axios.get('/api/auth/me');
          
          if (response && response.data) {
            setUser(response.data);
            setIsLoggedIn(true);
          } else {
            // 如果响应不正确，清除令牌
            handleLogout(false);
          }
        } catch (error) {
          console.error('验证用户会话失败', error);
          
          // 后端API可能尚未实现，使用模拟数据
          if (process.env.NODE_ENV === 'development') {
            const mockUser = {
              id: 'mock-id',
              name: '测试用户',
              email: 'test@example.com',
              is_active: true,
              email_verified: true
            };
            setUser(mockUser);
            setIsLoggedIn(true);
            message.warning('使用模拟用户数据 (开发模式)');
          } else {
            // 生产环境下清除令牌
            handleLogout(false);
          }
        } finally {
          setLoading(false);
        }
      } else {
        setIsLoggedIn(false);
        setUser(null);
        setLoading(false);
      }
    };

    checkAuthStatus();
  }, [token]);

  // 登录函数
  const login = async (email, password) => {
    try {
      setLoading(true);
      
      // 发送登录请求
      const response = await axios.post('/api/auth/login', {
        email,
        password
      });
      
      // 确保响应包含令牌和用户信息
      if (response && response.data && response.data.access_token) {
        // 保存令牌到本地存储
        localStorage.setItem('token', response.data.access_token);
        setToken(response.data.access_token);
        
        // 设置默认请求头
        axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.access_token}`;
        
        // 更新用户信息和登录状态
        if (response.data.user) {
          setUser(response.data.user);
        }
        setIsLoggedIn(true);
        
        message.success('登录成功');
        return true;
      } else {
        throw new Error('无效的响应格式');
      }
    } catch (error) {
      console.error('登录失败', error);
      
      // 后端API可能尚未实现，使用模拟数据
      if (process.env.NODE_ENV === 'development') {
        // 创建一个模拟令牌
        const mockToken = 'mock-jwt-token-for-development';
        localStorage.setItem('token', mockToken);
        setToken(mockToken);
        
        // 设置模拟用户
        const mockUser = {
          id: 'mock-id',
          name: '测试用户',
          email: email || 'test@example.com',
          is_active: true,
          email_verified: true
        };
        setUser(mockUser);
        setIsLoggedIn(true);
        
        message.warning('使用模拟登录 (开发模式)');
        return true;
      } else {
        // 在生产环境显示错误
        const errorMsg = 
          error.response && error.response.data && error.response.data.detail
            ? error.response.data.detail
            : '登录失败，请检查您的凭据';
        message.error(errorMsg);
        return false;
      }
    } finally {
      setLoading(false);
    }
  };

  // 注册函数
  const register = async (name, email, password) => {
    try {
      setLoading(true);
      
      // 发送注册请求
      const response = await axios.post('/api/auth/register', {
        name,
        email,
        password
      });
      
      if (response && response.data) {
        message.success('注册成功，请登录');
        return true;
      } else {
        throw new Error('无效的响应格式');
      }
    } catch (error) {
      console.error('注册失败', error);
      
      // 处理错误响应
      if (error.response && error.response.data) {
        if (error.response.data.detail) {
          message.error(error.response.data.detail);
        } else {
          message.error('注册失败，请稍后重试');
        }
      } else {
        message.error('无法连接到服务器');
      }
      
      // 后端API可能尚未实现，使用模拟数据
      if (process.env.NODE_ENV === 'development') {
        message.warning('使用模拟注册 (开发模式)');
        return true;
      }
      
      return false;
    } finally {
      setLoading(false);
    }
  };

  // 登出函数
  const handleLogout = (showMessage = true) => {
    // 清除存储的令牌
    localStorage.removeItem('token');
    setToken(null);
    
    // 重置认证状态
    setIsLoggedIn(false);
    setUser(null);
    
    // 清除请求头
    delete axios.defaults.headers.common['Authorization'];
    
    if (showMessage) {
      message.success('已退出登录');
    }
  };

  // 刷新用户信息
  const refreshUser = async () => {
    if (!token) return;
    
    try {
      const response = await axios.get('/api/auth/me');
      
      if (response && response.data) {
        setUser(response.data);
        return response.data;
      }
    } catch (error) {
      console.error('刷新用户数据失败', error);
      // 在开发模式中，我们不因为刷新失败而登出用户
      if (process.env.NODE_ENV !== 'development') {
        handleLogout(false);
      }
    }
  };

  // 上下文值
  const contextValue = {
    user,
    isLoggedIn,
    loading,
    login,
    register,
    logout: handleLogout,
    refreshUser
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

/**
 * 使用认证上下文的钩子
 * @returns {Object} 认证上下文
 */
export const useAuth = () => {
  const context = useContext(AuthContext);
  
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  
  return context;
};

export default AuthContext; 