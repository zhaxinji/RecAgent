import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider, message, App as AntdApp, notification } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './AppComponent'
import './styles/globalStyles.css'
import './index.css'
import { AssistantProvider } from './contexts/AssistantContext'
import { LiteratureProvider } from './contexts/LiteratureContext'
import { ExperimentProvider } from './contexts/ExperimentContext'
import { WritingProvider } from './contexts/WritingContext'
import { AuthProvider } from './contexts/AuthContext'
import axios from 'axios'

// 全局错误边界组件
class GlobalErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('全局错误捕获:', error, errorInfo)
    this.setState({ errorInfo })
    
    // 记录错误到日志服务器（可根据需要实现）
    // logErrorToService(error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h1>应用程序出现问题</h1>
          <p>我们已记录此错误，并将尽快修复。</p>
          <details>
            <summary>查看详细信息</summary>
            <p>{this.state.error && this.state.error.toString()}</p>
            <p>组件堆栈:</p>
            <pre>{this.state.errorInfo && this.state.errorInfo.componentStack}</pre>
          </details>
          <button
            onClick={() => {
              this.setState({ hasError: false })
              window.location.reload()
            }}
            style={{
              padding: '8px 16px',
              backgroundColor: '#1890ff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              marginTop: '16px'
            }}
          >
            刷新页面
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

// 配置Axios默认值
axios.defaults.baseURL = import.meta.env.VITE_API_URL || '/api'
axios.defaults.timeout = 600000  // 增加到600秒（10分钟），解决复杂大型论文分析超时问题

// 添加请求拦截器
axios.interceptors.request.use(
  (config) => {
    // 从localStorage获取令牌
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 添加响应拦截器
axios.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // 处理响应错误
    if (error.response) {
      const { status, data } = error.response
      
      // 未授权错误
      if (status === 401) {
        // 检查是否是登录页面
        if (!window.location.pathname.includes('/login')) {
          // 清除存储的令牌
          localStorage.removeItem('token')
          message.error('会话已过期，请重新登录')
          // 重定向到登录页
          window.location.href = '/login'
        }
      } 
      // 服务器错误
      else if (status >= 500) {
        notification.error({
          message: '服务器错误',
          description: '服务器处理请求时出现问题，请稍后重试'
        })
      }
      // 其他错误
      else if (data && data.detail) {
        message.error(data.detail)
      }
    } else if (error.request) {
      // 请求已发送但没有收到响应
      notification.error({
        message: '网络错误',
        description: '无法连接到服务器，请检查您的网络连接'
      })
    } else {
      // 在设置请求时发生错误
      console.error('请求错误:', error.message)
    }
    
    return Promise.reject(error)
  }
)

// 处理未捕获的Promise错误
window.addEventListener('unhandledrejection', (event) => {
  console.error('未处理的Promise错误:', event.reason)
  // 可以在这里添加额外的错误处理逻辑
})

// 处理全局错误
window.addEventListener('error', (event) => {
  console.error('全局错误:', event.error)
  // 可以在这里添加额外的错误处理逻辑
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <GlobalErrorBoundary>
      <ConfigProvider locale={zhCN}>
        <AntdApp>
          <BrowserRouter>
            <AuthProvider>
              <AssistantProvider>
                <LiteratureProvider>
                  <ExperimentProvider>
                    <WritingProvider>
                      <App />
                    </WritingProvider>
                  </ExperimentProvider>
                </LiteratureProvider>
              </AssistantProvider>
            </AuthProvider>
          </BrowserRouter>
        </AntdApp>
      </ConfigProvider>
    </GlobalErrorBoundary>
  </React.StrictMode>,
) 