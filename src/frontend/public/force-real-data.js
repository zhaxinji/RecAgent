/**
 * 强制使用真实API数据脚本
 * 在浏览器控制台执行此文件内容，可绕过前端模拟数据
 */

// 立即执行函数
(async function forceRealData() {
  console.log('开始强制使用真实API数据...');
  
  // 尝试初始化用户资料
  try {
    const initResponse = await fetch('/api/init-profile', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    
    if (initResponse.ok) {
      console.log('用户资料初始化成功！');
    } else {
      console.warn('用户资料初始化API返回错误:', await initResponse.text());
    }
  } catch (error) {
    console.error('初始化API调用失败:', error);
  }
  
  // 获取真实用户数据
  try {
    const response = await fetch('/api/userinfo', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    
    if (!response.ok) {
      throw new Error(`API请求失败: ${response.status}`);
    }
    
    const userData = await response.json();
    console.log('获取到真实API数据:', userData);
    
    // 查找React组件实例并更新状态
    // 注意：这是一个hack方法，仅用于演示
    setTimeout(() => {
      // 清除localStorage中可能的缓存数据
      localStorage.removeItem('userProfile');
      
      // 找到Profile组件的React实例
      const reactRoot = document.querySelector('div[id^="root"]');
      if (!reactRoot) {
        console.warn('找不到React根元素');
        return;
      }
      
      // 强制更新页面显示
      const forceUpdateUI = () => {
        // 1. 直接替换DOM中的值（粗暴但有效的方式）
        document.querySelectorAll('h1, h2, h3, h4, h5, p, span, div').forEach(el => {
          if (el.textContent.includes('研究机构') || 
              el.textContent.includes('中国科学院') ||
              el.textContent.includes('研究员')) {
            // 检查是否为用户名或机构名
            if (el.textContent.trim() === '张研究' || 
                el.textContent.trim() === '研究员' ||
                el.textContent.includes('中国科学院计算技术研究所')) {
              console.log('替换DOM元素:', el.textContent, '->', userData.name);
              if (userData.name) el.textContent = userData.name;
              else if (userData.institution) el.textContent = userData.institution;
            }
          }
        });
        
        // 2. 显示通知
        alert('已强制加载真实API数据，请刷新页面查看最新效果！');
      };
      
      // 延迟执行，确保React已完成渲染
      setTimeout(forceUpdateUI, 1000);
    }, 500);
    
  } catch (error) {
    console.error('获取用户API数据失败:', error);
    alert('获取API数据失败，请确保已登录并且后端服务正常运行！');
  }
})(); 