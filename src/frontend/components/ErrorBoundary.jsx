import React from 'react';
import { Button, Result } from 'antd';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('组件渲染错误:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (typeof this.props.onReset === 'function') {
      this.props.onReset();
    }
  }

  handleReload = () => {
    window.location.reload();
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary-container">
          <Result
            status="error"
            title="组件渲染错误"
            subTitle={this.state.error ? this.state.error.toString() : '发生了未知错误'}
            extra={[
              <Button key="reset" type="primary" onClick={this.handleReset}>
                尝试恢复
              </Button>,
              <Button key="reload" onClick={this.handleReload}>
                刷新页面
              </Button>
            ]}
          />
          <div style={{ marginTop: 20, textAlign: 'left', padding: '0 24px' }}>
            <details style={{ whiteSpace: 'pre-wrap' }}>
              <summary>查看详细错误信息</summary>
              {this.state.errorInfo && this.state.errorInfo.componentStack}
            </details>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary; 