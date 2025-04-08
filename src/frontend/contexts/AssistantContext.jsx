import React, { createContext, useContext, useState, useEffect } from 'react';
import { message } from 'antd';
import { assistantApi } from '../services/api';

// 创建研究助手上下文
const AssistantContext = createContext();

// 研究助手上下文提供者
export const AssistantProvider = ({ children }) => {
  // 状态管理
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState({
    sessions: false,
    messages: false,
    researchGap: false,
    innovation: false,
    concept: false,
  });
  const [researchDomains, setResearchDomains] = useState([]);
  const [analysisPerspectives, setAnalysisPerspectives] = useState([]);
  const [researchGapResults, setResearchGapResults] = useState(null);
  const [innovationIdeas, setInnovationIdeas] = useState(null);

  // 获取会话列表
  const fetchSessions = async () => {
    setLoading(prev => ({ ...prev, sessions: true }));
    try {
      const data = await assistantApi.getSessions();
      setSessions(data);
    } catch (error) {
      message.error('获取会话列表失败');
      console.error(error);
    } finally {
      setLoading(prev => ({ ...prev, sessions: false }));
    }
  };

  // 获取指定会话的消息
  const fetchMessages = async (sessionId) => {
    if (!sessionId) return;
    
    setLoading(prev => ({ ...prev, messages: true }));
    try {
      const data = await assistantApi.getMessages(sessionId);
      setMessages(data);
    } catch (error) {
      message.error('获取消息失败');
      console.error(error);
    } finally {
      setLoading(prev => ({ ...prev, messages: false }));
    }
  };

  // 创建新会话
  const createSession = async (sessionData) => {
    setLoading(prev => ({ ...prev, sessions: true }));
    try {
      const data = await assistantApi.createSession(sessionData);
      setSessions(prev => [data, ...prev]);
      setCurrentSession(data);
      return data;
    } catch (error) {
      message.error('创建会话失败');
      console.error(error);
      throw error;
    } finally {
      setLoading(prev => ({ ...prev, sessions: false }));
    }
  };

  // 删除会话
  const deleteSession = async (sessionId) => {
    try {
      await assistantApi.deleteSession(sessionId);
      setSessions(prev => prev.filter(session => session.id !== sessionId));
      if (currentSession?.id === sessionId) {
        setCurrentSession(null);
        setMessages([]);
      }
    } catch (error) {
      message.error('删除会话失败');
      console.error(error);
    }
  };

  // 分析研究空白
  const analyzeResearchGaps = async (domain, perspective, paperIds, additionalContext) => {
    setLoading(prev => ({ ...prev, researchGap: true }));
    try {
      const data = await assistantApi.analyzeResearchGaps(
        domain,
        perspective,
        paperIds,
        additionalContext
      );
      setResearchGapResults(data);
      return data;
    } catch (error) {
      message.error('分析研究空白失败');
      console.error(error);
      throw error;
    } finally {
      setLoading(prev => ({ ...prev, researchGap: false }));
    }
  };

  // 生成创新点
  const generateInnovationIdeas = async (researchTopic, paperIds, innovationType, additionalContext) => {
    setLoading(prev => ({ ...prev, innovation: true }));
    try {
      const data = await assistantApi.generateInnovationIdeas(
        researchTopic,
        paperIds,
        innovationType,
        additionalContext
      );
      setInnovationIdeas(data);
      return data;
    } catch (error) {
      message.error('生成创新点失败');
      console.error(error);
      throw error;
    } finally {
      setLoading(prev => ({ ...prev, innovation: false }));
    }
  };

  // 获取研究领域列表
  const fetchResearchDomains = async () => {
    try {
      const data = await assistantApi.getResearchDomains();
      setResearchDomains(data);
    } catch (error) {
      console.error('获取研究领域失败', error);
    }
  };

  // 获取分析角度列表
  const fetchAnalysisPerspectives = async () => {
    try {
      const data = await assistantApi.getAnalysisPerspectives();
      setAnalysisPerspectives(data);
    } catch (error) {
      console.error('获取分析角度失败', error);
    }
  };

  // 在组件挂载时加载初始数据
  useEffect(() => {
    fetchResearchDomains();
    fetchAnalysisPerspectives();
    fetchSessions();
  }, []);

  // 切换会话时加载消息
  useEffect(() => {
    if (currentSession) {
      fetchMessages(currentSession.id);
    }
  }, [currentSession]);

  // 导出上下文值
  const contextValue = {
    sessions,
    currentSession,
    setCurrentSession,
    messages,
    loading,
    researchDomains,
    analysisPerspectives,
    researchGapResults,
    innovationIdeas,
    fetchSessions,
    fetchMessages,
    createSession,
    deleteSession,
    analyzeResearchGaps,
    generateInnovationIdeas,
  };

  return (
    <AssistantContext.Provider value={contextValue}>
      {children}
    </AssistantContext.Provider>
  );
};

// 自定义钩子，方便使用上下文
export const useAssistant = () => {
  const context = useContext(AssistantContext);
  if (!context) {
    throw new Error('useAssistant必须在AssistantProvider内部使用');
  }
  return context;
};

export default AssistantContext; 