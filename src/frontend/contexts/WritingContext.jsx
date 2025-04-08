import React, { createContext, useContext, useState, useEffect } from 'react';
import { message } from 'antd';
import { writingApi } from '../services/api';

// 创建写作上下文
const WritingContext = createContext();

// 写作上下文提供者组件
export const WritingProvider = ({ children }) => {
  // 状态管理
  const [documents, setDocuments] = useState([]); // 文档列表
  const [currentDocument, setCurrentDocument] = useState(null); // 当前文档
  const [documentContent, setDocumentContent] = useState(null); // 文档内容
  const [templates, setTemplates] = useState([]); // 模板列表
  const [loading, setLoading] = useState({
    documents: false,
    document: false,
    saveDocument: false,
    createDocument: false
  });

  // 初始化默认模板
  useEffect(() => {
    setTemplates([
      {
        id: 'standard-research',
        name: '标准研究论文',
        description: '包含完整章节的研究论文模板',
        sections: ['摘要', '引言', '相关工作', '方法', '实验', '结论']
      },
      {
        id: 'short-paper',
        name: '短篇研究论文',
        description: '适合会议短文的简化模板',
        sections: ['摘要', '引言', '方法', '实验', '结论']
      },
      {
        id: 'survey-paper',
        name: '综述论文',
        description: '文献综述和调研论文模板',
        sections: ['摘要', '引言', '研究方法', '文献分析', '研究趋势', '讨论', '结论']
      }
    ]);
  }, []);

  // 获取用户文档列表
  const fetchDocuments = async () => {
    setLoading(prev => ({ ...prev, documents: true }));
    try {
      console.log('开始获取文档列表');
      const data = await writingApi.getProjects();
      
      // 检查返回的数据是否有效
      if (!data || !data.items) {
        console.error('获取到的文档列表数据无效:', data);
        setDocuments([]);
        return [];
      }
      
      // 处理并验证每个文档项
      const validDocuments = (data.items || []).map(doc => {
        // 确保必要字段存在
        if (!doc || typeof doc !== 'object') return null;
        
        // 创建安全的文档对象
        return {
          id: doc.id || `invalid-${Date.now()}`,
          title: doc.title || '未命名文档',
          description: doc.description || '',
          updatedAt: doc.updatedAt || Date.now(),
          sections: Array.isArray(doc.sections) ? doc.sections : [],
          collaborators: Array.isArray(doc.collaborators) ? doc.collaborators : [],
          metadata: (doc.metadata && typeof doc.metadata === 'object') ? doc.metadata : {}
        };
      }).filter(doc => doc !== null && doc.id);
      
      console.log(`获取到 ${validDocuments.length} 个有效文档`);
      setDocuments(validDocuments);
      return validDocuments;
    } catch (error) {
      console.error('获取文档列表失败:', error);
      
      // 提供详细的错误信息
      let errorMessage = '获取文档列表失败';
      
      if (error.response) {
        const { status, data } = error.response;
        console.error(`获取文档列表时服务器错误 ${status}:`, data);
        
        if (data && data.detail) {
          errorMessage += `: ${data.detail}`;
        }
        
        // 特别处理ResponseValidationError
        if (data && data.detail && data.detail.includes('ResponseValidationError')) {
          errorMessage = '文档列表数据验证失败，可能是返回格式不正确';
          
          // 尝试从错误响应中提取部分有效数据
          if (data.items && Array.isArray(data.items)) {
            const validItems = data.items
              .filter(item => item && item.id)
              .map(item => ({
                ...item,
                metadata: item.metadata || {}
              }));
              
            if (validItems.length > 0) {
              console.log('从错误响应中提取了部分有效数据:', validItems.length);
              setDocuments(validItems);
              message.warning('文档列表加载不完整，部分功能可能受限');
              return validItems;
            }
          }
        }
      }
      
      message.error(errorMessage);
      
      // 设置为空数组而不是null或undefined，确保UI不会崩溃
      setDocuments([]);
      return [];
    } finally {
      setLoading(prev => ({ ...prev, documents: false }));
    }
  };

  // 获取文档内容
  const fetchDocumentContent = async (documentId) => {
    setLoading(prev => ({ ...prev, document: true }));
    try {
      console.log(`正在获取文档内容，ID: ${documentId}`);
      
      if (!documentId) {
        throw new Error('无效的文档ID');
      }
      
      // 获取文档信息
      const document = await writingApi.getProject(documentId);
      console.log('获取到文档数据:', document);
      
      // 验证获取到的文档数据
      if (!document || !document.id) {
        throw new Error('获取到的文档数据无效');
      }
      
      // 确保metadata字段是对象
      if (!document.metadata || typeof document.metadata !== 'object') {
        document.metadata = {};
      }
      
      // 获取章节信息
      const sections = await writingApi.getSections(documentId);
      console.log('获取到章节数据:', sections);
      
      // 确保sections是数组
      const validSections = Array.isArray(sections) ? sections : [];
      
      // 先设置文档结构数据
      setCurrentDocument({
        ...document,
        sections: validSections
      });
      
      // 分开处理文档内容设置，防止数据不完整导致后续错误
      if (validSections.length > 0 && validSections[0].content) {
        setDocumentContent(validSections[0].content);
      } else {
        setDocumentContent('');
        console.warn('文档没有章节内容，设置为空字符串');
      }
      
      return document;
    } catch (error) {
      console.error('获取文档内容失败:', error);
      
      // 提供详细的错误信息
      let errorMessage = '获取文档内容失败';
      
      if (error.response) {
        const { status, data } = error.response;
        console.error(`获取文档时服务器错误 ${status}:`, data);
        
        if (data && data.detail) {
          errorMessage += `: ${data.detail}`;
        }
        
        // 特别处理ResponseValidationError
        if (data && data.detail && data.detail.includes('ResponseValidationError')) {
          errorMessage = '文档数据验证失败，可能是metadata字段不是有效的字典';
          
          // 尝试从错误响应中提取部分有效数据
          if (data.project) {
            const project = data.project;
            // 确保metadata是有效的对象
            project.metadata = project.metadata || {};
            // 设置文档，使界面不会完全白屏
            setCurrentDocument({
              ...project,
              sections: []
            });
            setDocumentContent('');
            message.warning('文档加载不完整，部分功能可能受限');
            return project;
          }
        }
      } else if (error.request) {
        errorMessage = '服务器无响应，请检查网络连接';
      } else {
        errorMessage = `请求失败: ${error.message}`;
      }
      
      message.error(errorMessage);
      
      // 重置状态，防止部分加载导致的UI问题
      setCurrentDocument(null);
      setDocumentContent(null);
      return null;
    } finally {
      setLoading(prev => ({ ...prev, document: false }));
    }
  };

  // 创建新文档
  const createDocument = async (template) => {
    setLoading(prev => ({ ...prev, createDocument: true }));
    try {
      // 准备项目数据
      const projectData = {
        title: `新${template.name} ${new Date().toLocaleDateString()}`,
        description: `使用${template.name}模板创建的文档`,
        template: template.id,
        metadata: {} // 确保metadata字段存在且为空对象
      };
      
      // 创建项目
      const newProject = await writingApi.createProject(projectData);
      
      if (!newProject || !newProject.id) {
        console.error('创建项目失败: 返回的项目数据无效', newProject);
        message.error('创建文档失败: 返回的项目数据无效');
        return { success: false, error: '返回的项目数据无效' };
      }
      
      // 尝试创建章节
      try {
        // 为每个模板部分创建章节
        for (let i = 0; i < template.sections.length; i++) {
          const sectionData = {
            title: template.sections[i],
            content: `# ${template.sections[i]}\n\n这里是${template.sections[i]}的内容。`,
            order: i
          };
          
          await writingApi.createSection(newProject.id, sectionData);
        }
      } catch (sectionError) {
        // 章节创建失败，但项目已创建
        console.error('创建章节失败，但项目已创建:', sectionError);
        message.warning('文档创建部分成功，但章节创建失败，请刷新后重试');
      }
      
      try {
        // 刷新文档列表
        await fetchDocuments();
      } catch (fetchError) {
        console.error('刷新文档列表失败:', fetchError);
      }
      
      try {
        // 设置当前文档
        await fetchDocumentContent(newProject.id);
      } catch (contentError) {
        console.error('获取文档内容失败:', contentError);
        // 尝试简单设置currentDocument
        setCurrentDocument(newProject);
      }
      
      message.success('文档创建成功');
      return { success: true, project: newProject };
    } catch (error) {
      console.error('创建文档失败:', error);
      
      // 尝试提供更具体的错误信息
      let errorMessage = '创建文档失败';
      if (error.response) {
        if (error.response.status === 500 && error.response.data && error.response.data.detail) {
          errorMessage += `: ${error.response.data.detail}`;
          
          // 处理特定类型的错误
          if (error.response.data.detail.includes('ResponseValidationError') || 
              error.response.data.detail.includes('metadata')) {
            errorMessage = '创建文档失败: 服务器验证错误，请联系管理员';
          }
        }
      }
      
      message.error(errorMessage);
      
      // 返回错误对象而不是抛出异常
      return { success: false, error: errorMessage, originalError: error };
    } finally {
      setLoading(prev => ({ ...prev, createDocument: false }));
    }
  };

  // 保存文档
  const saveDocument = async () => {
    if (!currentDocument) {
      message.error('没有选中的文档');
      return;
    }
    
    setLoading(prev => ({ ...prev, saveDocument: true }));
    try {
      // 假设当前正在编辑的是第一个章节
      if (currentDocument.sections && currentDocument.sections.length > 0) {
        const sectionToUpdate = currentDocument.sections[0];
        
        await writingApi.updateSection(sectionToUpdate.id, {
          content: documentContent
        });
        
        message.success('文档保存成功');
      } else {
        message.warning('文档没有章节可保存');
      }
    } catch (error) {
      console.error('保存文档失败:', error);
      message.error('保存文档失败');
    } finally {
      setLoading(prev => ({ ...prev, saveDocument: false }));
    }
  };

  // 更新文档内容
  const updateDocumentContent = (newContent) => {
    setDocumentContent(newContent);
  };

  // 生成内容
  const generateContent = async (params) => {
    try {
      // 确保参数名称与API期望的一致
      const apiParams = {
        section: params.section,
        style: params.style,
        topic: params.topic,
        researchProblem: params.researchProblem || params.research_problem,
        methodFeature: params.methodFeature || params.method_feature,
        modelingTarget: params.modelingTarget || params.modeling_target,
        improvement: params.improvement,
        keyComponent: params.keyComponent || params.key_component,
        impact: params.impact,
        additionalContext: params.additionalContext || params.additional_context
      };
      
      return await writingApi.generateContent(apiParams);
    } catch (error) {
      console.error('生成内容失败:', error);
      message.error('生成内容失败');
      throw error;
    }
  };

  // 删除文档
  const deleteDocument = async (documentId) => {
    try {
      await writingApi.deleteProject(documentId);
      await fetchDocuments();
      
      // 如果删除的是当前文档，清除当前文档
      if (currentDocument && currentDocument.id === documentId) {
        setCurrentDocument(null);
        setDocumentContent(null);
      }
      
      message.success('文档删除成功');
      return true;
    } catch (error) {
      console.error('删除文档失败:', error);
      message.error('删除文档失败');
      return false;
    }
  };

  // 导出上下文值
  const value = {
    documents,
    currentDocument,
    documentContent,
    templates,
    loading,
    setDocumentContent: updateDocumentContent,
    fetchDocuments,
    fetchDocumentContent,
    createDocument,
    saveDocument,
    generateContent,
    deleteDocument
  };

  return (
    <WritingContext.Provider value={value}>
      {children}
    </WritingContext.Provider>
  );
};

// 自定义Hook，简化上下文访问
export const useWriting = () => {
  const context = useContext(WritingContext);
  if (!context) {
    throw new Error('useWriting必须在WritingProvider内部使用');
  }
  return context;
};

export default WritingContext; 