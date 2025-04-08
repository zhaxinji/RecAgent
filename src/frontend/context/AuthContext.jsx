import React, { createContext, useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';  // 添加axios导入
import { authAPI } from '../services/api';

// 创建认证上下文
const AuthContext = createContext();

// 自定义Hook，提供认证上下文访问
export const useAuth = () => useContext(AuthContext);

// 认证Provider组件
export const AuthProvider = ({ children }) => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  // 初始化认证状态
  useEffect(() => {
    const checkAuthentication = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          // 尝试获取当前用户信息
          const userData = localStorage.getItem('user');
          if (userData) {
            setUser(JSON.parse(userData));
            setIsLoggedIn(true);
            
            // 刷新用户资料
            try {
              await refreshUser();
            } catch (refreshError) {
              console.error('刷新用户信息失败:', refreshError);
              // 初始化用户资料
              try {
                await axios.post('/api/init-profile', {}, {
                  headers: { 'Authorization': `Bearer ${token}` }
                });
              } catch (initError) {
                console.error('初始化用户资料失败:', initError);
              }
            }
          } else {
            // 尝试从服务器获取
            await refreshUser();
          }
        } catch (err) {
          console.error('认证检查失败:', err);
          // 无效的token，清除本地存储
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          setIsLoggedIn(false);
          setUser(null);
        }
      }
      setLoading(false);
    };

    checkAuthentication();
  }, []);

  // 刷新用户信息
  const refreshUser = async () => {
    try {
      const response = await authAPI.getCurrentUser();
      if (response.data) {
        setUser(response.data);
        localStorage.setItem('user', JSON.stringify(response.data));
        setIsLoggedIn(true);
        return response.data;
      }
    } catch (err) {
      console.error('获取当前用户信息失败:', err);
      if (err.response && err.response.status === 401) {
        // 认证失败，清除token
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setIsLoggedIn(false);
        setUser(null);
      }
      throw err;
    }
  };

  // 登录函数
  const login = async (usernameOrEmail, password) => {
    try {
      setLoading(true);
      setError(null);
      
      // 执行登录请求
      const response = await authAPI.login(usernameOrEmail, password);
      
      if (response.data) {
        localStorage.setItem('token', response.data.access_token);
        localStorage.setItem('user', JSON.stringify(response.data.user));
        
        setUser(response.data.user);
        setIsLoggedIn(true);
        
        // 新增：登录后立即初始化用户资料
        try {
          console.log('登录成功，初始化用户个人资料...');
          const initResponse = await axios.post('/api/init-profile', {}, {
            headers: { 
              'Authorization': `Bearer ${response.data.access_token}`
            }
          });
          console.log('用户资料初始化成功:', initResponse.data);
        } catch (initError) {
          console.error('初始化用户资料失败:', initError);
          // 初始化失败不影响登录流程，继续执行
        }
        
        return true;
      } else {
        setError('登录响应无效');
        return false;
      }
    } catch (err) {
      console.error('登录失败:', err);
      setError(err.response?.data?.detail || '登录失败，请检查用户名和密码');
      return false;
    } finally {
      setLoading(false);
    }
  };

  // 注册函数
  const register = async (userData) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await authAPI.register(userData);
      
      if (response.data) {
        // 注册成功后自动登录
        return await login(userData.email, userData.password);
      }
      
      return false;
    } catch (err) {
      console.error('注册失败:', err);
      setError(err.response?.data?.detail || '注册失败，请稍后重试');
      return false;
    } finally {
      setLoading(false);
    }
  };

  // 登出函数
  const logout = async () => {
    try {
      setLoading(true);
      await authAPI.logout();
    } catch (err) {
      console.error('登出请求失败:', err);
      // 即使API请求失败，也要清除本地存储
    } finally {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      setIsLoggedIn(false);
      setUser(null);
      setLoading(false);
      navigate('/login');
    }
  };

  // 忘记密码
  const forgotPassword = async (email) => {
    try {
      setLoading(true);
      setError(null);
      const response = await authAPI.requestPasswordReset(email);
      return response.data;
    } catch (err) {
      console.error('密码重置请求失败:', err);
      setError(err.response?.data?.detail || '发送重置密码请求失败');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // 重置密码
  const resetPassword = async (token, newPassword) => {
    try {
      setLoading(true);
      setError(null);
      const response = await authAPI.resetPassword(token, newPassword);
      return response.data;
    } catch (err) {
      console.error('重置密码失败:', err);
      setError(err.response?.data?.detail || '重置密码失败');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // 验证邮箱
  const verifyEmail = async (token) => {
    try {
      setLoading(true);
      setError(null);
      const response = await authAPI.verifyEmail(token);
      
      // 更新用户信息
      if (isLoggedIn) {
        await refreshUser();
      }
      
      return response.data;
    } catch (err) {
      console.error('验证邮箱失败:', err);
      setError(err.response?.data?.detail || '验证邮箱失败');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // 重新发送验证邮件
  const resendVerification = async (email) => {
    try {
      setLoading(true);
      setError(null);
      const response = await authAPI.resendVerification(email);
      return response.data;
    } catch (err) {
      console.error('重新发送验证邮件失败:', err);
      setError(err.response?.data?.detail || '重新发送验证邮件失败');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // 组装上下文值
  const value = {
    isLoggedIn,
    user,
    loading,
    error,
    login,
    logout,
    register,
    refreshUser,
    forgotPassword,
    resetPassword,
    verifyEmail,
    resendVerification
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext; 