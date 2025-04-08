/**
 * 前端应用配置文件
 */

// API基础URL
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';
export const API_BASE_URL = `${API_URL}/api`;

// 分页默认值
export const DEFAULT_PAGE_SIZE = 10;
export const DEFAULT_PAGE = 1;

// 主题键
export const THEME_KEY = 'agent_rec_theme';

// 存储键
export const STORAGE_KEYS = {
  TOKEN: 'token',
  USER: 'user',
  RECENT_PAPERS: 'recent_papers',
  SEARCH_HISTORY: 'search_history',
};

// 文件上传配置
export const UPLOAD_CONFIG = {
  ACCEPTED_FILE_TYPES: '.pdf',
  MAX_FILE_SIZE: 20 * 1024 * 1024, // 20MB
};

// 论文相关常量
export const PAPER_CONSTANTS = {
  MAX_TITLE_LENGTH: 200,
  MAX_ABSTRACT_PREVIEW: 300,
  MAX_TAGS: 10,
};

// 助手相关常量
export const ASSISTANT_CONSTANTS = {
  MAX_QUESTION_LENGTH: 1000,
  MAX_CONTEXT_LENGTH: 5000,
};

// 路由路径
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  PAPERS: '/literature',
  PAPER_DETAIL: '/literature/:paperId',
  PAPER_UPLOAD: '/literature/upload',
  ASSISTANT: '/assistant',
  EXPERIMENT: '/experiment',
  WRITING: '/writing',
  PROFILE: '/profile',
  SETTINGS: '/settings',
  NOT_FOUND: '*',
};

// 错误消息
export const ERROR_MESSAGES = {
  DEFAULT: '操作失败，请稍后重试',
  NETWORK: '网络错误，请检查网络连接',
  UNAUTHORIZED: '未授权访问，请先登录',
  FORBIDDEN: '无权访问此资源',
  NOT_FOUND: '请求的资源不存在',
  SERVER: '服务器错误，请联系管理员',
  VALIDATION: '输入数据验证失败',
};

// 日期格式
export const DATE_FORMAT = 'YYYY-MM-DD';

export default {
  API_URL,
  API_BASE_URL,
  DEFAULT_PAGE_SIZE,
  DEFAULT_PAGE,
  THEME_KEY,
  STORAGE_KEYS,
  UPLOAD_CONFIG,
  PAPER_CONSTANTS,
  ASSISTANT_CONSTANTS,
  ROUTES,
  ERROR_MESSAGES,
  DATE_FORMAT,
}; 