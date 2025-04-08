/**
 * API拦截器 - 确保前端使用真实API数据
 * 添加到HTML的<head>部分加载
 */

// 页面加载完成后执行
window.addEventListener('load', function() {
  console.log('API拦截器已加载，确保使用真实数据');
  
  // 重写axios的get方法，确保个人资料页面使用API数据
  const originalGet = axios.get;
  axios.get = function(url, config) {
    // 拦截个人资料请求
    if (url === '/api/users/me/profile') {
      console.log('拦截个人资料请求，改为使用新API端点');
      return originalGet.call(this, '/api/userinfo', config);
    }
    
    // 其他请求正常处理
    return originalGet.call(this, url, config);
  };
  
  // 检测页面类型
  if (window.location.pathname.includes('/profile') || 
      window.location.pathname === '/' || 
      window.location.pathname === '') {
    console.log('检测到个人资料页面，准备替换模拟数据');
    
    // 禁用本地存储的模拟数据
    const originalGetItem = localStorage.getItem;
    localStorage.getItem = function(key) {
      if (key === 'userProfile') {
        console.log('阻止从本地存储加载用户资料数据');
        return null;
      }
      return originalGetItem.call(this, key);
    };
    
    // 强制使用API数据
    setTimeout(async function() {
      try {
        // 先初始化用户资料
        await fetch('/api/init-profile', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        
        // 获取真实数据
        const response = await fetch('/api/userinfo', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        
        if (response.ok) {
          const userData = await response.json();
          console.log('获取到真实API数据:', userData);
          
          // 通知用户
          const notification = document.createElement('div');
          notification.style.position = 'fixed';
          notification.style.top = '10px';
          notification.style.right = '10px';
          notification.style.padding = '10px';
          notification.style.background = '#4caf50';
          notification.style.color = 'white';
          notification.style.zIndex = '9999';
          notification.style.borderRadius = '4px';
          notification.textContent = '已加载真实API数据';
          
          document.body.appendChild(notification);
          
          // 2秒后移除通知
          setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transition = 'opacity 0.5s';
            setTimeout(() => document.body.removeChild(notification), 500);
          }, 2000);
          
          // 刷新页面以显示真实数据
          // 前因为可能导致循环刷新，先不自动刷新
          // location.reload();
        }
      } catch (error) {
        console.error('API数据加载失败:', error);
      }
    }, 1000);
  }
}); 