import React, { useState, useEffect } from 'react'
import { Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom'
import { Layout, Menu, Button, Dropdown, Avatar, Space, ConfigProvider, theme, message } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { 
  HomeOutlined, 
  UserOutlined, 
  LogoutOutlined, 
  LoginOutlined,
  RobotOutlined,
  ReadOutlined,
  EditOutlined,
  ExperimentOutlined,
  SettingOutlined,
  MenuOutlined,
  CloseOutlined
} from '@ant-design/icons';

// 页面导入
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import AssistantPage from './pages/AssistantPage';
import LiteraturePage from './pages/LiteraturePage';
import ExperimentPage from './pages/ExperimentPage';
import WritingPage from './pages/WritingPage';
import SettingsPage from './pages/SettingsPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import VerifyEmailPage from './pages/VerifyEmailPage';

// 样式
import './App.css'
import './styles/auth.css'
import './styles/assistant.css'

const { Header, Content, Footer } = Layout

// 无需导航栏的路径列表
const noNavbarPaths = ['/login', '/register', '/forgot-password', '/reset-password', '/verify-email'];

// 配置消息提示
message.config({
  top: 40, // 设置更靠近顶部的位置
  duration: 5, // 显示时间延长
  maxCount: 3, // 允许同时显示消息数量
  rtl: false // 从右到左布局，不开启
});

// 自定义错误消息样式
const errorMessageStyle = {
  marginTop: '40px',
  zIndex: 9999,
  width: '400px',
  padding: '10px 20px',
  borderRadius: '4px',
  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
};

// 重写message.error方法，应用自定义样式
const originalError = message.error;
message.error = (content, duration = 10, onClose) => {
  return originalError(content, duration, onClose);
};

function App() {
  const [currentPage, setCurrentPage] = useState('home')
  const [user, setUser] = useState(null)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const location = useLocation();
  const navigate = useNavigate();
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken()

  // 判断当前路径是否需要导航栏
  const needNavbar = !noNavbarPaths.includes(location.pathname);

  // 初始化时从localStorage加载用户信息
  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (e) {
        console.error('解析用户信息失败', e);
        localStorage.removeItem('user');
      }
    }
  }, []);

  // 根据当前路径更新当前页面
  useEffect(() => {
    const pathToKey = {
      '/': 'home',
      '/assistant': 'assistant',
      '/literature': 'literature',
      '/experiments': 'experiments',
      '/writing': 'writing',
      '/settings': 'settings',
      '/profile': 'profile'
    };
    
    const path = '/' + location.pathname.split('/')[1];
    if (pathToKey[path]) {
      setCurrentPage(pathToKey[path]);
    }
  }, [location]);

  // 处理登出
  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    navigate('/');
  };

  // 创建菜单项
  const getMenuItems = () => {
    // 基础菜单项
    const items = [
      {
        key: 'home',
        label: <Link to="/">探索</Link>,
      },
      {
        key: 'literature',
        label: <Link to="/literature">文献中心</Link>,
      },
      {
        key: 'assistant',
        label: <Link to="/assistant">研究助手</Link>,
      },
      {
        key: 'writing',
        label: <Link to="/writing">智能写作</Link>,
      }
    ];
    
    // 不在主菜单中添加个人中心
    return items;
  };

  const handleMenuClick = (e) => {
    setCurrentPage(e.key);
    setMobileMenuOpen(false);
  }

  // 移动端菜单覆盖层
  const mobileMenu = (
    <div className={`mobile-menu-overlay ${mobileMenuOpen ? 'active' : ''}`}>
      <div className="mobile-menu-header">
        <div className="logo">
          <h2 className="logo-text">RecAgent</h2>
        </div>
        <Button 
          type="text" 
          icon={<CloseOutlined />} 
          onClick={() => setMobileMenuOpen(false)}
          size="large"
        />
      </div>
      <Menu
        theme="light"
        mode="inline"
        selectedKeys={[currentPage]}
        onClick={handleMenuClick}
        items={getMenuItems()}
        className="mobile-menu-items"
      />
      <div className="mobile-menu-footer">
        {user ? (
          <div className="user-info">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button 
                block 
                type="primary"
                onClick={() => { 
                  navigate('/settings'); 
                  setMobileMenuOpen(false); 
                }}
                className="profile-button"
              >
                个人中心
              </Button>
              <Button 
                block
                type="default"
                danger
                icon={<LogoutOutlined />} 
                onClick={() => {
                  handleLogout();
                  setMobileMenuOpen(false);
                }}
              >
                退出登录
              </Button>
            </Space>
          </div>
        ) : (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Button block type="primary" onClick={() => { navigate('/login'); setMobileMenuOpen(false); }}>
              登录
            </Button>
            <Button block onClick={() => { navigate('/register'); setMobileMenuOpen(false); }}>
              注册
            </Button>
          </Space>
        )}
      </div>
    </div>
  );

  return (
    <ConfigProvider locale={zhCN}>
      <Layout className="main-layout">
        {mobileMenu}
        
        {/* 只在需要导航栏的页面显示头部 */}
        {needNavbar && (
          <Header className="site-header">
            <div className="header-container">
              <div className="header-left">
                <div className="mobile-trigger">
                  <Button 
                    type="text" 
                    icon={<MenuOutlined />} 
                    onClick={() => setMobileMenuOpen(true)}
                    size="large"
                  />
                </div>
                <div className="logo">
                  <Link to="/">
                    <h2 className="logo-text">RecAgent</h2>
                  </Link>
                </div>
              </div>
              
              <div className="desktop-menu">
                <Menu
                  mode="horizontal"
                  selectedKeys={[currentPage]}
                  onClick={handleMenuClick}
                  items={getMenuItems()}
                  className="top-menu"
                />
              </div>
              
              <div className="header-right">
                {user ? (
                  <Space>
                    <Button 
                      type="default"
                      onClick={() => navigate('/settings')}
                      className="profile-button"
                      style={{
                        background: 'white',
                        borderColor: '#f0f0f0',
                        boxShadow: 'none'
                      }}
                    >
                      个人中心
                    </Button>
                    <Button 
                      type="text" 
                      danger 
                      icon={<LogoutOutlined />} 
                      onClick={handleLogout}
                      size="small"
                    />
                  </Space>
                ) : (
                  <Space>
                    <Button className="login-button" onClick={() => navigate('/login')}>
                      登录
                    </Button>
                    <Button 
                      type="primary" 
                      onClick={() => navigate('/register')}
                      style={{
                        background: 'linear-gradient(to right, #4481eb, #04befe)',
                        borderColor: 'transparent'
                      }}
                    >
                      注册
                    </Button>
                  </Space>
                )}
              </div>
            </div>
          </Header>
        )}
        
        {/* 登录/注册页面直接渲染，不需要内容容器 */}
        {['/login', '/register', '/forgot-password', '/reset-password', '/verify-email'].includes(location.pathname) ? (
          <Routes>
            <Route path="/login" element={<LoginPage setUser={setUser} />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />
          </Routes>
        ) : (
          <Content className="site-content">
            <div
              className="content-container"
              style={{
                borderRadius: needNavbar ? borderRadiusLG : 0,
              }}
            >
              <Routes>
                <Route path="/" element={<HomePage user={user} />} />
                <Route path="/assistant" element={<AssistantPage user={user} />} />
                <Route path="/literature" element={<LiteraturePage user={user} />} />
                <Route path="/experiments" element={<ExperimentPage user={user} />} />
                <Route path="/writing" element={<WritingPage user={user} />} />
                <Route path="/settings" element={<SettingsPage user={user} />} />
              </Routes>
            </div>
          </Content>
        )}
        
        {/* 只在需要导航栏的页面显示底部 */}
        {needNavbar && (
          <Footer className="site-footer">
            RecAgent ©{new Date().getFullYear()} 推荐系统学术研究智能体
          </Footer>
        )}
      </Layout>
      <style jsx global>{`
        .logo-text {
          font-family: 'Montserrat', 'Helvetica Neue', Arial, sans-serif;
          font-weight: 700;
          background: linear-gradient(90deg, #1890ff, #722ed1);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          letter-spacing: -0.5px;
          font-size: 28px;
          margin: 0;
          text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        }
        
        .top-menu .ant-menu-item {
          font-size: 16px;
          font-weight: 500;
          padding: 0 20px;
        }
        
        .mobile-menu-items .ant-menu-item {
          font-size: 18px;
          margin: 8px 0;
        }
      `}</style>
    </ConfigProvider>
  )
}

export default App 