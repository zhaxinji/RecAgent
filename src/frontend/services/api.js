import axios from 'axios';

// 创建axios实例
const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api';
console.log('API基础URL:', baseURL);

const api = axios.create({
  baseURL: baseURL,
  timeout: 600000,  // 增加到600秒（10分钟）
  headers: {
    'Content-Type': 'application/json',
  }
});

// 请求拦截器 - 添加认证令牌
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 处理常见错误
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const { response } = error;
    
    console.log('API错误:', error);
    console.log('错误状态:', response?.status);
    console.log('错误细节:', response?.data);
    
    // 只有非登录页面的未认证错误才重定向
    if (response && response.status === 401) {
      const currentPath = window.location.pathname;
      
      // 如果不是在登录相关页面，才跳转到登录页
      if (!currentPath.includes('/login') && 
          !currentPath.includes('/register') && 
          !currentPath.includes('/reset-password')) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }
    }
    
    // 确保错误被正确传递给后续的catch
    return Promise.reject(error);
  }
);

// 生成唯一会话ID的辅助函数
function generateSessionId() {
  return 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 15);
}

// 确保每次请求前都刷新认证令牌
const ensureAuth = () => {
  const token = localStorage.getItem('token');
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    return true;
  }
  return false;
};

// 认证相关API
export const authAPI = {
  /**
   * 标准OAuth2登录方式（用户名/邮箱通用）
   * @param {string} usernameOrEmail 用户名或邮箱
   * @param {string} password 密码
   */
  login: async (usernameOrEmail, password) => {
    console.log('尝试登录:', usernameOrEmail);
    
    // 使用URLSearchParams（OAuth2标准格式）
    const params = new URLSearchParams();
    params.append('username', usernameOrEmail); 
    params.append('password', password);
    
    console.log('登录表单数据:', params.toString());
    
    try {
      const response = await api.post('/auth/login', params, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      console.log('登录响应:', response.data);
      return response;
    } catch (error) {
      console.error('登录请求出错:', error.message);
      // 确保错误被传递给调用者
      throw error;
    }
  },
  
  /**
   * 专门的邮箱登录方式
   * @param {string} email 邮箱
   * @param {string} password 密码
   */
  loginWithEmail: async (email, password) => {
    console.log('尝试使用邮箱登录:', email);
    
    try {
      const response = await api.post('/auth/login/email', {
        email,
        password
      });
      console.log('邮箱登录响应:', response.data);
      return response;
    } catch (error) {
      console.error('邮箱登录请求出错:', error.message);
      // 确保错误被传递给调用者
      throw error;
    }
  },
  
  /**
   * 检测输入是否为邮箱格式
   * @param {string} input 输入值
   * @returns {boolean} 是否为邮箱
   */
  isEmail: (input) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(input);
  },
  
  /**
   * 用户注册
   * @param {Object} userData 用户数据
   * @param {string} userData.email 邮箱
   * @param {string} userData.password 密码
   * @param {string} userData.name 用户名
   */
  register: (userData) => {
    return api.post('/auth/register', userData);
  },
  
  /**
   * 获取当前用户信息
   */
  getCurrentUser: () => {
    return api.get('/auth/me');
  },
  
  /**
   * 退出登录
   */
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    return Promise.resolve();
  },
  
  /**
   * 请求密码重置
   * @param {string} email 用户邮箱
   */
  requestPasswordReset: (email) => {
    return api.post('/auth/forgot-password', { email });
  },
  
  /**
   * 重置密码
   * @param {string} token 重置密码令牌
   * @param {string} newPassword 新密码
   */
  resetPassword: (token, newPassword) => {
    return api.post('/auth/reset-password', { 
      token,
      new_password: newPassword 
    });
  },
  
  /**
   * 验证邮箱
   * @param {string} token 邮箱验证令牌
   */
  verifyEmail: (token) => {
    return api.post('/auth/verify-email', { token });
  },
  
  /**
   * 重新发送验证邮件
   * @param {string} email 用户邮箱
   */
  resendVerification: (email) => {
    return api.post('/auth/resend-verification', { email });
  }
};

// 论文相关API
export const papersAPI = {
  /**
   * 获取论文列表
   * @param {Object} params 查询参数
   */
  getPapers: (params = {}) => {
    return api.get('/papers', { params });
  },
  
  /**
   * 获取单篇论文详情
   * @param {string} id 论文ID
   */
  getPaper: (id) => {
    return api.get(`/papers/${id}`);
  },
  
  /**
   * 上传论文
   * @param {FormData} formData 包含论文文件和元数据的表单数据
   */
  uploadPaper: (formData) => {
    return api.post('/papers/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  
  /**
   * 添加论文笔记
   * @param {string} paperId 论文ID
   * @param {Object} noteData 笔记数据
   */
  addNote: (paperId, noteData) => {
    return api.post(`/papers/${paperId}/notes`, noteData);
  },
  
  /**
   * 获取标签列表
   */
  getTags: () => {
    return api.get('/papers/tags');
  }
};

// 研究助手相关API
export const assistantApi = {
  // 会话相关
  getSessions: async () => {
    try {
      ensureAuth();
      const response = await api.get('/assistant/sessions');
      return response.data;
    } catch (error) {
      console.error('获取会话列表失败:', error);
      throw error;
    }
  },
  
  getSession: async (sessionId) => {
    try {
      ensureAuth();
      const response = await api.get(`/assistant/sessions/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error('获取会话详情失败:', error);
      throw error;
    }
  },
  
  createSession: async (sessionData) => {
    try {
      const response = await api.post('/assistant/sessions', sessionData);
      return response.data;
    } catch (error) {
      console.error('创建会话失败:', error);
      throw error;
    }
  },
  
  updateSession: async (sessionId, sessionData) => {
    try {
      const response = await api.put(`/assistant/sessions/${sessionId}`, sessionData);
      return response.data;
    } catch (error) {
      console.error('更新会话失败:', error);
      throw error;
    }
  },
  
  deleteSession: async (sessionId, hardDelete = false) => {
    try {
      const response = await api.delete(`/assistant/sessions/${sessionId}?hard_delete=${hardDelete}`);
      return response.data;
    } catch (error) {
      console.error('删除会话失败:', error);
      throw error;
    }
  },
  
  // 获取消息列表
  getMessages: async (sessionId, skip = 0, limit = 100) => {
    try {
      const response = await api.get(`/assistant/sessions/${sessionId}/messages?skip=${skip}&limit=${limit}`);
      return response.data;
    } catch (error) {
      console.error('获取消息列表失败:', error);
      throw error;
    }
  },
  
  // 分析研究问题
  analyzeResearchGaps: async (domain, perspective, paperIds = [], additionalContext = '') => {
    console.log('开始研究问题分析...', { domain, perspective, paperIds, additionalContext });
    
    // 完整性检查
    if (!domain) {
      throw new Error('请指定研究领域');
    }
    
    // 检查用户是否已登录
    const isAuthenticated = ensureAuth();
    if (!isAuthenticated) {
      throw new Error('用户未登录，无法使用API功能');
    }
    
    // 尝试调用真实API
    try {
      // 设置更长的超时时间（20分钟）
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1200000);
      
      const response = await api.post('/assistant/research-problems/analyze', {
        domain,
        perspective: perspective || 'comprehensive',
        paper_ids: paperIds || [],
        additional_context: additionalContext || ''
      }, {
        signal: controller.signal,
        timeout: 1200000, // 20分钟
        onUploadProgress: (progressEvent) => {
          console.log(`上传进度: ${Math.round(progressEvent.loaded * 100 / progressEvent.total)}%`);
        }
      });
      
      // 清除超时计时器
      clearTimeout(timeoutId);
      
      console.log('API返回结果:', response.data);
      
      return response.data;
    } catch (error) {
      console.error('研究问题分析API调用失败:', error);
      
      // 超时错误特殊处理
      if (error.name === 'AbortError' || error.code === 'ECONNABORTED') {
        throw new Error('请求超时，服务器处理时间过长。研究问题分析需要较长时间，请稍后重试或减少输入内容');
      }
      
      // 抛出具体错误，由组件处理
      if (error.response) {
        // 服务器返回了错误
        const errorMsg = error.response.data?.detail || `服务器错误 (${error.response.status})`;
        throw new Error(errorMsg);
      } else if (error.request) {
        // 没有收到响应
        throw new Error('服务器无响应，请检查网络连接');
      } else {
        // 请求配置出错
        throw new Error(`请求配置错误: ${error.message}`);
      }
    }
  },
  
  // 创新点生成
  generateInnovationIdeas: async (researchTopic, paperIds = [], innovationType = null, additionalContext = null) => {
    try {
      console.log('请求创新点生成, 参数:', { researchTopic, paperIds, innovationType, additionalContext });
      
      // 设置更长的超时时间（10分钟）
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 600000);
      
      const response = await api.post('/assistant/innovation-ideas/generate', {
        research_topic: researchTopic,
        paper_ids: Array.isArray(paperIds) ? paperIds : [],
        innovation_type: innovationType,
        additional_context: additionalContext,
        // 添加创新要求参数
        innovation_requirements: {
          base_on_mainstream: true,  // 基于最新主流技术
          incremental_innovation: true,  // 确保技术创新是渐进式的
          academic_oriented: true  // 确保学术导向
        }
      }, {
        signal: controller.signal,
        // 增加超时选项到10分钟
        timeout: 600000,
        // 显示上传进度
        onUploadProgress: (progressEvent) => {
          console.log(`上传进度: ${Math.round(progressEvent.loaded * 100 / progressEvent.total)}%`);
        }
      });
      
      // 清除超时计时器
      clearTimeout(timeoutId);

      // 添加日志
      console.log(`创新点生成API请求完成，API响应:`, response.data);
      
      // 检查响应中是否包含错误信息
      if (response.data && response.data.error) {
        console.error('API返回错误:', response.data.error);
        return {
          error: true,
          message: response.data.error,
          details: response.data.details || '服务器处理失败',
        };
      }
      
      // 正常返回数据
      return response.data;
    } catch (error) {
      console.error('生成创新点请求失败:', error);
      
      // 超时错误特殊处理
      if (error.name === 'AbortError' || error.code === 'ECONNABORTED') {
        return {
          error: true, 
          message: '请求超时，服务器处理时间过长',
          details: '创新点生成需要较长时间，请稍后重试或减少输入内容。复杂的研究主题可能需要更多处理时间。'
        };
      } else if (error.response) {
        // 服务器返回错误状态码
        const statusCode = error.response.status;
        let message = '服务器处理失败';
        let details = error.response.data?.details || error.message;
        
        if (statusCode === 400) {
          message = '请求参数错误';
        } else if (statusCode === 401) {
          message = '未授权访问';
        } else if (statusCode === 404) {
          message = '资源不存在';
        } else if (statusCode === 500) {
          message = '服务器内部错误';
          details = error.response.data?.details || '生成创新点时服务器出现错误，请稍后重试';
        }
        
        return { error: true, message, details, statusCode };
      } else if (error.request) {
        // 请求发送但没有收到响应
        return { 
          error: true, 
          message: '服务器无响应',
          details: '请检查网络连接或服务器状态'
        };
      } else {
        // 设置请求时发生错误
        return { 
          error: true, 
          message: '请求配置错误',
          details: error.message
        };
      }
    }
  },
  
  // 实验设计生成
  generateExperiment: async (paperId, experimentData) => {
    try {
      console.log('请求生成实验代码, 参数:', { paperId, ...experimentData });
      
      // 确保framework和language有默认值
      experimentData.framework = experimentData.framework || 'pytorch';
      experimentData.language = experimentData.language || 'python';
      
      // 添加实验设计偏好
      experimentData.experiment_preferences = {
        academic_standard: true,  // 遵循学术界标准
        mainstream_approach: true, // 主流学术方法
        rigorous_evaluation: true  // 严格评估
      };
      
      // 设置更长的超时时间（10分钟）
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 600000);
      
      // 如果提供了paperId，使用带paperId的端点；否则使用新端点
      const url = paperId 
        ? `/assistant/generate-experiment/${paperId}` 
        : '/assistant/generate-experiment';
      
      // 如果提供了paperId，将其添加到请求数据中
      if (paperId) {
        experimentData.paper_id = paperId;
      }
      
      const response = await api.post(url, experimentData, {
        signal: controller.signal,
        timeout: 600000, // 10分钟
        onUploadProgress: (progressEvent) => {
          console.log(`上传进度: ${Math.round(progressEvent.loaded * 100 / progressEvent.total)}%`);
        }
      });
      
      // 清除超时计时器
      clearTimeout(timeoutId);
      
      console.log('实验代码生成响应:', response.data);
      
      return response.data;
    } catch (error) {
      console.error('生成实验代码失败:', error);
      
      // 超时错误特殊处理
      if (error.name === 'AbortError' || error.code === 'ECONNABORTED') {
        return {
          error: true,
          message: '请求超时，服务器处理时间过长',
          details: '生成实验代码需要较长时间，请稍后重试或简化实验设计。复杂的实验设计可能需要更多处理时间。'
        };
      }
      
      // 服务器返回的错误处理
      if (error.response) {
        const statusCode = error.response.status;
        let message = '服务器处理失败';
        let details = error.response.data?.detail || error.message;
        
        if (statusCode === 400) {
          message = '请求参数错误';
        } else if (statusCode === 401) {
          message = '未授权访问';
        } else if (statusCode === 404) {
          message = '论文或资源不存在';
        } else if (statusCode === 500) {
          message = '服务器内部错误';
          details = error.response.data?.detail || '生成实验代码时服务器出现错误，请稍后重试';
        }
        
        return { error: true, message, details, statusCode };
      }
      
      // 其他错误处理
      return { 
        error: true, 
        message: '请求失败',
        details: error.message || '未知错误'
      };
    }
  },
  
  // 获取研究领域列表
  getResearchDomains: async () => {
    try {
      const response = await api.get('/assistant/research-domains');
      return response.data;
    } catch (error) {
      console.error('获取研究领域列表失败:', error);
      throw error;
    }
  },
  
  // 获取分析角度列表
  getAnalysisPerspectives: async () => {
    try {
      const response = await api.get('/assistant/analysis-perspectives');
      return response.data;
    } catch (error) {
      console.error('获取分析角度列表失败:', error);
      throw error;
    }
  }
};

// 实验API
export const experimentsAPI = {
  // 获取数据集列表
  getDatasets: async () => {
    return await api.get('/experiments/datasets');
  },
  
  // 获取算法列表
  getAlgorithms: async () => {
    return await api.get('/experiments/algorithms');
  },
  
  // 获取评估指标列表
  getMetrics: async () => {
    return await api.get('/experiments/metrics');
  },
  
  // 获取实验列表
  getExperiments: async (params = {}) => {
    return await api.get('/experiments', { params });
  },
  
  // 获取单个实验详情
  getExperiment: async (id) => {
    return await api.get(`/experiments/${id}`);
  },
  
  // 创建新实验
  createExperiment: async (experimentData) => {
    return await api.post('/experiments', experimentData);
  },
  
  // 运行实验
  runExperiment: async (id) => {
    return await api.post(`/experiments/${id}/run`);
  }
};

// 写作助手相关API
export const writingApi = {
  /**
   * 获取论文部分类型列表
   * @returns {Array} 论文部分类型列表
   */
  getPaperSections: async () => {
    try {
      const response = await api.get('/writing/paper-sections');
      console.log('获取论文部分成功:', response.data);
      return response.data;
    } catch (error) {
      console.error('获取论文部分失败:', error);
      // 返回默认值
      return [
        {"value": "abstract", "label": "摘要", "description": "概括研究内容、方法和主要结果"},
        {"value": "introduction", "label": "引言", "description": "介绍研究背景、动机和贡献"},
        {"value": "related_work", "label": "相关工作", "description": "总结和评价已有相关研究"},
        {"value": "methodology", "label": "方法论", "description": "详细描述研究方法和实现细节"},
        {"value": "experiment", "label": "实验", "description": "实验设计、结果分析和讨论"},
        {"value": "conclusion", "label": "结论", "description": "总结主要发现和未来工作"}
      ];
    }
  },
  
  /**
   * 获取写作风格列表
   * @returns {Array} 写作风格列表
   */
  getWritingStyles: async () => {
    try {
      const response = await api.get('/writing/writing-styles');
      console.log('获取写作风格成功:', response.data);
      return response.data;
    } catch (error) {
      console.error('获取写作风格失败:', error);
      // 返回默认值
      return [
        {"value": "academic", "label": "学术风格", "description": "严谨、正式的学术论文风格"},
        {"value": "technical", "label": "技术报告风格", "description": "注重技术细节的报告风格"},
        {"value": "explanatory", "label": "解释性风格", "description": "通俗易懂、注重解释的风格"}
      ];
    }
  },
  
  /**
   * 生成论文内容
   * @param {Object} data 包含各种参数的生成请求数据
   * @returns {Object} 生成的内容和建议
   */
  generateContent: async (data) => {
    try {
      console.log('发送生成内容请求:', data);
      // 确保所有必要参数都存在
      const requestData = {
        section_type: data.section_type,
        writing_style: data.writing_style,
        topic: data.topic || '',
        research_problem: data.research_problem || '',
        method_feature: data.method_feature || '',
        modeling_target: data.modeling_target || '',
        improvement: data.improvement || '',
        key_component: data.key_component || '',
        impact: data.impact || '',
        additional_context: data.additional_context || ''
      };
      
      console.log('发送到API的数据:', requestData);
      
      // 发送API请求
      const response = await api.post('/writing/generate-content', requestData);
      console.log('生成内容API响应:', response.data);
      
      // 验证返回数据
      if (!response.data || !response.data.content) {
        console.error('API返回的数据缺少content字段:', response.data);
        throw new Error('服务器返回的数据格式不正确');
      }
      
      return response.data;
    } catch (error) {
      console.error('生成内容API错误:', error);
      
      // 尝试从不同位置提取错误信息
      let errorMessage = '生成内容失败';
      if (error.response) {
        if (error.response.data && error.response.data.detail) {
          errorMessage = error.response.data.detail;
        } else {
          errorMessage = `服务器错误 (${error.response.status})`;
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      throw new Error(errorMessage);
    }
  },

  /**
   * 获取项目列表
   */
  getProjects: async (params = {}) => {
    // 从缓存尝试获取之前的文档列表
    const cachedProjectsList = localStorage.getItem('projects_list_cache');
    let cachedData = null;
    
    if (cachedProjectsList) {
      try {
        cachedData = JSON.parse(cachedProjectsList);
        console.log('从缓存中找到文档列表数据:', cachedData);
      } catch (e) {
        console.warn('解析缓存的文档列表数据失败:', e);
        localStorage.removeItem('projects_list_cache');
      }
    }
  
    try {
      console.log('开始请求文档列表');
      const response = await api.get('/writing/projects', { params });
      
      // 数据验证和清理
      let validData = { items: [] };
      
      if (response.data) {
        // 如果返回的不是数组，尝试从中提取items数组
        if (Array.isArray(response.data)) {
          validData.items = response.data;
        } else if (response.data.items && Array.isArray(response.data.items)) {
          validData = response.data;
        } else {
          console.warn('API返回的项目列表格式不符合预期:', response.data);
          validData.items = [];
        }
        
        // 处理每个项目的数据
        validData.items = validData.items.map(project => {
          // 确保必要的字段都存在
          return {
            ...project,
            id: project.id || `temp-${Date.now()}`,
            title: project.title || '未命名项目',
            description: project.description || '',
            updatedAt: project.updatedAt || Date.now(),
            sections: Array.isArray(project.sections) ? project.sections : [],
            collaborators: Array.isArray(project.collaborators) ? project.collaborators : [],
            metadata: (project.metadata && typeof project.metadata === 'object') ? project.metadata : {}
          };
        });
        
        // 缓存项目列表数据到localStorage
        try {
          localStorage.setItem('projects_list_cache', JSON.stringify(validData));
        } catch (cacheError) {
          console.warn('缓存项目列表数据失败:', cacheError);
        }
      }
      
      return validData;
    } catch (error) {
      console.error('获取写作项目列表失败:', error);
      
      // 处理特定错误类型
      if (error.response && error.response.data && 
          error.response.data.detail && 
          error.response.data.detail.includes('ResponseValidationError')) {
        console.error('项目列表API响应验证错误');
        
        // 尝试从错误响应中提取部分有效数据
        if (error.response.data.items && Array.isArray(error.response.data.items)) {
          const validItems = {
            items: error.response.data.items.filter(item => item && item.id)
          };
          
          return validItems;
        }
      }
      
      // 如果发生错误且有缓存数据，返回缓存数据
      if (cachedData) {
        console.log('使用缓存的项目列表数据作为后备方案');
        return cachedData;
      }
      
      // 如果没有可用的缓存数据，返回空列表而不是抛出错误
      console.warn('返回空项目列表作为错误处理');
      return { items: [] };
    }
  },

  /**
   * 获取单个项目
   * @param {string} projectId 项目ID
   */
  getProject: async (projectId) => {
    // 从缓存中检查是否有备份
    const cachedProject = localStorage.getItem(`project_${projectId}`);
    let cachedData = null;
    
    if (cachedProject) {
      try {
        cachedData = JSON.parse(cachedProject);
        console.log('从缓存中找到项目数据:', cachedData);
      } catch (e) {
        console.warn('解析缓存的项目数据失败:', e);
        localStorage.removeItem(`project_${projectId}`);
      }
    }
    
    try {
      console.log(`尝试获取项目 ${projectId} 的数据`);
      const response = await api.get(`/writing/projects/${projectId}`);
      
      // 数据验证和清理
      if (response.data) {
        // 确保metadata是有效的对象
        if (response.data.metadata === null || response.data.metadata === undefined) {
          console.log('修复空的metadata字段');
          response.data.metadata = {};
        }
        
        // 确保sections字段至少是空数组
        if (!response.data.sections) {
          response.data.sections = [];
        }
        
        // 确保collaborators字段至少是空数组
        if (!response.data.collaborators) {
          response.data.collaborators = [];
        }
        
        // 缓存项目数据到localStorage，以便后续恢复
        try {
          localStorage.setItem(`project_${projectId}`, JSON.stringify(response.data));
        } catch (cacheError) {
          console.warn('缓存项目数据失败:', cacheError);
        }
      }
      
      return response.data;
    } catch (error) {
      console.error('获取写作项目失败:', error);
      
      // 处理特定错误类型
      if (error.response && error.response.data && 
          error.response.data.detail && 
          error.response.data.detail.includes('ResponseValidationError')) {
        console.error('API响应验证错误，可能是metadata字段不是有效的字典');
        
        // 尝试从错误响应中提取部分有效数据
        if (error.response.data.project) {
          const project = error.response.data.project;
          // 确保metadata是有效的对象
          project.metadata = project.metadata || {};
          
          // 缓存修复后的数据
          try {
            localStorage.setItem(`project_${projectId}`, JSON.stringify(project));
          } catch (cacheError) {
            console.warn('缓存修复后的项目数据失败:', cacheError);
          }
          
          return project;
        }
      }
      
      // 如果发生错误且有缓存数据，返回缓存数据
      if (cachedData) {
        console.log('使用缓存数据作为后备方案');
        return cachedData;
      }
      
      throw error;
    }
  },

  /**
   * 创建新项目
   * @param {Object} projectData 项目数据
   */
  createProject: async (projectData) => {
    try {
      // 确保projectData包含必要字段
      if (!projectData.title) {
        throw new Error('项目标题不能为空');
      }
      
      // 确保metadata字段是对象
      if (!projectData.metadata || typeof projectData.metadata !== 'object') {
        projectData.metadata = {};
      }
      
      console.log('创建项目请求数据:', projectData);
      
      const response = await api.post('/writing/projects', projectData);
      
      // 验证响应数据
      if (!response || !response.data || !response.data.id) {
        console.error('创建项目响应无效:', response);
        throw new Error('服务器返回无效数据');
      }
      
      console.log('创建项目成功，响应:', response.data);
      return response.data;
    } catch (error) {
      console.error('创建写作项目失败:', error);
      
      // 增强错误信息
      let errorMessage = '创建项目失败';
      
      // 处理服务器响应错误
      if (error.response) {
        const { status, data } = error.response;
        console.error(`服务器错误 ${status}:`, data);
        
        if (data && data.detail) {
          errorMessage += `: ${data.detail}`;
        }
        
        // 特别处理验证错误
        if (status === 422 || (data && data.detail && data.detail.includes('validation'))) {
          errorMessage = '项目数据验证失败，请检查必填字段';
        }
        
        // 特别处理ResponseValidationError
        if (data && data.detail && data.detail.includes('ResponseValidationError')) {
          errorMessage = 'API响应验证失败，可能是metadata字段不是有效的字典';
        }
      } else if (error.request) {
        // 请求发送但没有收到响应
        errorMessage = '服务器无响应，请检查网络连接';
      } else {
        // 其他错误
        errorMessage = `请求设置错误: ${error.message}`;
      }
      
      error.userMessage = errorMessage;
      throw error;
    }
  },

  /**
   * 更新项目
   * @param {string} projectId 项目ID
   * @param {Object} updateData 更新数据
   */
  updateProject: async (projectId, updateData) => {
    try {
      const response = await api.patch(`/writing/projects/${projectId}`, updateData);
      return response.data;
    } catch (error) {
      console.error('更新写作项目失败:', error);
      throw error;
    }
  },

  /**
   * 删除项目
   * @param {string} projectId 项目ID
   */
  deleteProject: async (projectId) => {
    try {
      await api.delete(`/writing/projects/${projectId}`);
      return true;
    } catch (error) {
      console.error('删除写作项目失败:', error);
      throw error;
    }
  },

  /**
   * 获取项目章节
   * @param {string} projectId 项目ID
   */
  getSections: async (projectId) => {
    try {
      const response = await api.get(`/writing/projects/${projectId}/sections`);
      
      // 确保返回数据是数组
      if (!Array.isArray(response.data)) {
        console.warn('获取章节API没有返回数组，返回空数组');
        return [];
      }
      
      return response.data;
    } catch (error) {
      console.error('获取章节列表失败:', error);
      
      // 返回空数组而不是抛出错误，确保UI不会崩溃
      console.warn('获取章节失败，返回空数组');
      return [];
    }
  },

  /**
   * 创建章节
   * @param {string} projectId 项目ID
   * @param {Object} sectionData 章节数据
   */
  createSection: async (projectId, sectionData) => {
    try {
      const response = await api.post(`/writing/projects/${projectId}/sections`, sectionData);
      return response.data;
    } catch (error) {
      console.error('创建章节失败:', error);
      throw error;
    }
  },

  /**
   * 更新章节
   * @param {string} sectionId 章节ID
   * @param {Object} updateData 更新数据
   */
  updateSection: async (sectionId, updateData) => {
    try {
      const response = await api.patch(`/writing/sections/${sectionId}`, updateData);
      return response.data;
    } catch (error) {
      console.error('更新章节失败:', error);
      throw error;
    }
  },

  /**
   * 删除章节
   * @param {string} sectionId 章节ID
   */
  deleteSection: async (sectionId) => {
    try {
      await api.delete(`/writing/sections/${sectionId}`);
      return true;
    } catch (error) {
      console.error('删除章节失败:', error);
      throw error;
    }
  },

  /**
   * 生成章节内容
   * @param {string} sectionId 章节ID
   * @param {Object} data 生成参数
   */
  generateSectionContent: async (sectionId, data) => {
    try {
      const response = await api.post(`/writing/sections/${sectionId}/generate`, data);
      return response.data;
    } catch (error) {
      console.error('生成章节内容失败:', error);
      throw error;
    }
  },

  /**
   * 改进章节内容
   * @param {string} sectionId 章节ID
   * @param {Object} data 改进参数
   */
  improveSectionContent: async (sectionId, data) => {
    try {
      const response = await api.post(`/writing/sections/${sectionId}/improve`, data);
      return response.data;
    } catch (error) {
      console.error('改进章节内容失败:', error);
      throw error;
    }
  },

  /**
   * 生成论文结构
   * @param {Object} data 结构生成参数
   */
  generateStructure: async (data) => {
    try {
      const response = await api.post('/writing/generate-structure', data);
      return response.data;
    } catch (error) {
      console.error('生成论文结构失败:', error);
      throw error;
    }
  },

  /**
   * 生成写作提示
   * @param {Object} data 提示生成参数
   */
  generatePrompt: async (data) => {
    try {
      const response = await api.post('/writing/generate-prompt', data);
      return response.data;
    } catch (error) {
      console.error('生成写作提示失败:', error);
      throw error;
    }
  },

  /**
   * 导出项目
   * @param {string} id 项目ID
   * @param {string} format 导出格式
   */
  exportProject: async (id, format = 'markdown') => {
    const response = await api.get(`/writing/projects/${id}/export`, { 
      params: { format } 
    });
    return response.data;
  }
};

// API初始化逻辑

// 确保全局设置认证头
export const setupApiAuth = () => {
  const token = localStorage.getItem('token');
  if (token) {
    console.log('设置全局认证头');
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }
};

// 用户API
export const usersAPI = {
  // 获取当前用户资料
  getUserProfile: async () => {
    setupApiAuth(); // 确保认证头设置
    try {
      console.log('调用用户资料API');
      return await api.get('/userinfo'); // 使用新的简化路径
    } catch (error) {
      console.error('获取用户资料失败:', error);
      throw error;
    }
  },
  
  // 初始化用户资料
  initializeProfile: async () => {
    setupApiAuth(); // 确保认证头设置
    try {
      console.log('调用初始化资料API');
      return await api.post('/init-profile');
    } catch (error) {
      console.error('初始化用户资料失败:', error);
      throw error;
    }
  },
  
  // 更新研究信息
  updateResearchInfo: async (institution, research_interests) => {
    setupApiAuth(); // 确保认证头设置
    try {
      console.log('调用更新研究信息API');
      return await api.put('/update-research', {
        institution,
        research_interests
      });
    } catch (error) {
      console.error('更新研究信息失败:', error);
      throw error;
    }
  }
};

export default api; 