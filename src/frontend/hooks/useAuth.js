import { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';

/**
 * 用户认证钩子
 * @returns {Object} 认证工具对象
 */
const useAuth = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 从localStorage加载用户信息
  useEffect(() => {
    try {
      const storedUser = localStorage.getItem('user');
      if (storedUser) {
        setUser(JSON.parse(storedUser));
      }
    } catch (err) {
      console.error('解析用户信息失败', err);
      localStorage.removeItem('user');
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * 登录
   * @param {Object} credentials - 登录凭证
   * @returns {Promise<Object>} 用户信息
   */
  const login = useCallback(async (credentials) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.auth.login(credentials);
      const { token, user: userData } = response.data;
      
      // 保存到localStorage
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(userData));
      
      // 更新状态
      setUser(userData);
      return userData;
    } catch (err) {
      setError(err.message || '登录失败');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * 注册
   * @param {Object} userData - 用户数据
   * @returns {Promise<Object>} 注册结果
   */
  const register = useCallback(async (userData) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.auth.register(userData);
      return response.data;
    } catch (err) {
      setError(err.message || '注册失败');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * 退出登录
   * @returns {Promise<void>}
   */
  const logout = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      // 清除本地存储
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      
      // 更新状态
      setUser(null);
      
      // 如果有退出登录API，则调用
      try {
        await apiService.auth.logout();
      } catch (err) {
        // 忽略API错误，确保本地退出成功
        console.warn('API退出登录失败', err);
      }
    } catch (err) {
      setError(err.message || '退出登录失败');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * 获取用户资料
   * @returns {Promise<Object>} 用户信息
   */
  const getProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.auth.getProfile();
      const userData = response.data;
      
      // 更新localStorage和状态
      localStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);
      
      return userData;
    } catch (err) {
      setError(err.message || '获取用户资料失败');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * 更新用户资料
   * @param {Object} profileData - 资料数据
   * @returns {Promise<Object>} 更新后的用户信息
   */
  const updateProfile = useCallback(async (profileData) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.auth.updateProfile(profileData);
      const userData = response.data;
      
      // 更新localStorage和状态
      localStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);
      
      return userData;
    } catch (err) {
      setError(err.message || '更新用户资料失败');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * 检查是否已登录
   * @returns {boolean} 是否已登录
   */
  const isLoggedIn = useCallback(() => {
    return !!user && !!localStorage.getItem('token');
  }, [user]);

  /**
   * 强制更新用户信息
   * @param {Object} userData - 用户数据
   */
  const updateUserData = useCallback((userData) => {
    if (userData) {
      localStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);
    }
  }, []);

  return {
    user,
    loading,
    error,
    login,
    register,
    logout,
    getProfile,
    updateProfile,
    isLoggedIn,
    updateUserData,
  };
};

export default useAuth; 