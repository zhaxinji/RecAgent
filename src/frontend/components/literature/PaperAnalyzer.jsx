import React, { useState, useEffect } from 'react';
import { 
  Upload, 
  Button, 
  Card, 
  Typography, 
  Steps, 
  Divider, 
  Space, 
  Spin, 
  Alert, 
  Collapse, 
  Empty,
  Tag,
  List,
  Tabs,
  Modal,
  message,
  Select,
  Table,
  Progress
} from 'antd';
import { 
  InboxOutlined, 
  FileTextOutlined, 
  BulbOutlined, 
  ExperimentOutlined, 
  NodeIndexOutlined,
  CodeOutlined,
  AreaChartOutlined,
  AlignLeftOutlined,
  CopyOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import axios from 'axios';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { docco } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import { API_BASE_URL } from '../../config';

const { Dragger } = Upload;
const { Title, Text, Paragraph } = Typography;
const { Step } = Steps;
const { Panel } = Collapse;
const { TabPane } = Tabs;

const PaperAnalyzer = () => {
  // 状态管理
  const [file, setFile] = useState(null);
  const [uploadedPaperId, setUploadedPaperId] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [paperData, setPaperData] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [selectedTab, setSelectedTab] = useState("methodology");
  const [analysisStatus, setAnalysisStatus] = useState(null);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [pollFailCount, setPollFailCount] = useState(0); // 轮询失败计数
  const [lastProgressTime, setLastProgressTime] = useState(Date.now()); // 上次进度更新时间

  // 论文状态映射
  const statusMap = {
    pending: { text: '等待分析', icon: <SyncOutlined spin />, color: 'blue' },
    processing: { text: '分析中', icon: <SyncOutlined spin />, color: 'blue' },
    completed: { text: '分析完成', icon: <CheckCircleOutlined />, color: 'green' },
    failed: { text: '分析失败', icon: <CloseCircleOutlined />, color: 'red' }
  };

  // 当已上传的论文ID变化时，启动分析
  useEffect(() => {
    if (uploadedPaperId) {
      startAnalysis(uploadedPaperId);
    }
  }, [uploadedPaperId]);

  // 定期轮询分析状态
  useEffect(() => {
    let interval;
    if (uploadedPaperId && (analysisStatus === 'pending' || analysisStatus === 'processing')) {
      // 缩短轮询间隔至2秒，使进度显示更实时
      interval = setInterval(() => {
        checkAnalysisStatus(uploadedPaperId);
        
        // 检查进度是否长时间未更新（超过60秒）
        const now = Date.now();
        if (now - lastProgressTime > 60000 && analysisProgress > 0 && analysisProgress < 100) {
          console.log(`进度已${Math.floor((now - lastProgressTime)/1000)}秒未更新，当前${analysisProgress}%`);
          
          // 如果进度卡在15-40%之间超过2分钟，尝试主动获取分析结果
          if (analysisProgress >= 15 && analysisProgress < 40 && now - lastProgressTime > 120000) {
            console.log('方法论分析可能已完成但进度未更新，尝试获取分析结果');
            fetchAnalysisResult(uploadedPaperId);
          }
        }
      }, 2000);
      
      console.log("开始轮询分析状态，间隔: 2秒");
    }

    return () => {
      if (interval) {
        clearInterval(interval);
        console.log("停止轮询分析状态");
      }
    };
  }, [uploadedPaperId, analysisStatus, lastProgressTime, analysisProgress]);

  // 上传论文处理
  const handleUpload = async (info) => {
    const { status, originFileObj } = info.file;
    
    if (status === 'done') {
      setFile(originFileObj);
      message.success(`${originFileObj.name} 上传成功`);
      
      // 获取上传后的论文ID
      const paperId = info.file.response.id;
      setUploadedPaperId(paperId);
      setCurrentStep(1);
    } else if (status === 'error') {
      setError(`${originFileObj.name} 上传失败: ${info.file.error.message}`);
      message.error(`${originFileObj.name} 上传失败`);
    }
  };

  // 开始分析论文
  const startAnalysis = async (paperId) => {
    try {
      setLoading(true);
      setError(null);
      setAnalysisStatus('processing');
      
      console.log(`开始分析论文 ID: ${paperId}`);
      
      // 创建取消令牌
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 600000); // 设置10分钟超时
      
      // 调用分析API，只提取核心内容，不分析参考文献和实验部分
      const response = await axios.post(
        `${API_BASE_URL}/papers/${paperId}/analyze`, 
        {
          sections: true,          // 分析章节结构
          methodology: true,       // 分析方法论
          experiments: false,      // 不分析实验
          code: true,              // 生成代码片段
          findings: true,          // 提取关键发现
          weaknesses: true,        // 分析弱点
          future_work: true,       // 分析未来工作方向
          references: false,       // 不分析参考文献
          extract_core_content: true // 只提取核心内容分析
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          },
          signal: controller.signal,
          timeout: 600000, // 显式设置600秒超时（10分钟）
        }
      );
      
      // 清除超时计时器
      clearTimeout(timeoutId);
      
      console.log('分析API响应:', response.data);
      
      // 分析可能需要时间，设置状态并开始轮询
      setAnalysisStatus(response.data.analysis_status || 'processing');
      checkAnalysisStatus(paperId);
      
    } catch (error) {
      console.error('分析论文失败:', error);
      
      // 区分不同类型的错误
      let errorMessage = '分析论文失败: ';
      
      if (error.name === 'AbortError' || error.code === 'ECONNABORTED') {
        // 超时错误处理
        errorMessage += '请求超时，但分析可能在后台继续。请稍后检查分析状态。';
        message.warning('请求超时，分析会在后台继续进行');
        // 继续轮询分析状态，因为后端可能仍在处理
        setAnalysisStatus('processing');
        checkAnalysisStatus(paperId);
      } else if (error.response) {
        // 服务器返回的错误
        errorMessage += error.response.data?.detail || error.response.data?.message || error.message;
      } else {
        // 其他错误
        errorMessage += error.message;
      }
      
      setError(errorMessage);
      if (error.name !== 'AbortError' && error.code !== 'ECONNABORTED') {
        setAnalysisStatus('failed');
        message.error('分析论文失败');
      }
    } finally {
      setLoading(false);
    }
  };

  // 查询分析状态
  const checkAnalysisStatus = async (paperId) => {
    try {
      // 增加超时时间到5分钟
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 300000); // 5分钟超时
      
      console.log(`检查论文(${paperId})分析状态，当前进度: ${analysisProgress}%`);
      
      const response = await axios.get(`${API_BASE_URL}/papers/${paperId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`
        },
        signal: controller.signal,
        timeout: 300000 // 5分钟超时
      });
      
      // 清除超时
      clearTimeout(timeoutId);
      
      const status = response.data.analysis_status;
      setAnalysisStatus(status);
      
      // 获取并设置分析进度，添加详细日志
      const progress = response.data.analysis_progress || 0;
      
      // 只有当进度有变化时才记录日志并更新时间戳
      if (progress !== analysisProgress) {
        console.log(`分析进度更新: ${analysisProgress}% -> ${progress}%`);
        setAnalysisProgress(progress);
        setLastProgressTime(Date.now()); // 更新进度时间戳
        setPollFailCount(0); // 重置失败计数
      }
      
      // 如果分析完成，获取分析结果
      if (status === 'completed') {
        console.log('分析已完成，获取结果');
        fetchAnalysisResult(paperId);
      } else if (status === 'failed') {
        const errorMsg = response.data.analysis_error || '分析过程中出错，请稍后重试';
        setError(errorMsg);
        message.error('分析失败: ' + errorMsg);
      } else if (status === 'processing' && progress >= 95) {
        // 当进度接近完成但状态仍为processing时，尝试获取结果
        console.log('进度接近完成(95%+)但状态仍为处理中，尝试获取结果');
        fetchAnalysisResult(paperId);
      }
    } catch (error) {
      console.error('获取分析状态失败:', error);
      
      // 增加失败计数
      const newFailCount = pollFailCount + 1;
      setPollFailCount(newFailCount);
      
      // 超时错误不显示错误消息，继续轮询
      if (error.name === 'AbortError' || error.code === 'ECONNABORTED') {
        console.log('状态检查超时，将继续轮询');
      } else {
        // 网络错误不中断轮询，只是在console记录
        console.log(`网络错误: ${error.message}，继续轮询 (失败次数: ${newFailCount})`);
        
        // 如果连续失败超过10次，显示提示但继续轮询
        if (newFailCount >= 10 && newFailCount % 5 === 0) {
          message.warning(
            '网络连接不稳定，但分析仍在后台进行。请检查网络连接，稍后将自动恢复。',
            5
          );
        }
      }
    }
  };

  // 获取分析结果
  const fetchAnalysisResult = async (paperId) => {
    try {
      setLoading(true);
      setError(null);
      
      // 添加超时控制
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 300000); // 300秒超时（5分钟）
      
      const response = await axios.get(`${API_BASE_URL}/papers/${paperId}/analysis`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`
        },
        signal: controller.signal,
        timeout: 300000 // 300秒超时（5分钟）
      });
      
      // 清除超时
      clearTimeout(timeoutId);
      
      // 检查返回的数据结构
      if (!response.data) {
        throw new Error('返回数据为空');
      }
      
      console.log('获取到分析结果：', response.data);
      
      // 处理各种分析状态
      if (response.data.status !== 'completed') {
        if (response.data.status === 'processing') {
          // 如果分析仍在进行，但有部分数据可用，也显示部分结果
          if (response.data.data && Object.keys(response.data.data).length > 0) {
            console.log('分析尚未完成，但已有部分数据可用:', response.data.data);
            // 继续处理部分数据，但标记状态为处理中
            setAnalysisStatus('processing');
            setAnalysisProgress(response.data.progress || 0);
            message.info('显示已分析完成的部分。分析仍在进行中，稍后刷新可获取更多结果。');
            // 使用部分数据，下面继续处理
          } else {
            // 没有可用数据时才抛出错误
            setAnalysisStatus('processing');
            setAnalysisProgress(response.data.progress || 0);
            throw new Error(response.data.message || '论文分析中，请稍后再试');
          }
        } else if (response.data.status === 'failed') {
          // 即使分析失败，也尝试获取部分已分析数据
          if (response.data.data && Object.keys(response.data.data).length > 0) {
            console.log('分析失败，但已有部分数据可用:', response.data.data);
            message.warning('论文部分分析失败，显示已完成的部分。');
            // 继续处理部分数据
          } else {
            setAnalysisStatus('failed');
            throw new Error(response.data.message || '论文分析失败');
          }
        } else if (response.data.status === 'not_analyzed') {
          // 特殊处理"分析数据不完整"的情况
          console.log('服务器返回分析数据不完整，尝试获取可用数据');
          if (response.data.data && Object.keys(response.data.data).length > 0) {
            console.log('找到部分可用数据，继续处理');
            message.warning('分析数据不完整，显示可用部分');
            // 继续处理可用数据
          } else {
            // 检查paper记录是否显示为completed
            if (analysisStatus === 'completed') {
              console.log('状态不一致：paper记录为completed但API返回not_analyzed');
              message.warning('分析状态不一致，将尝试重新分析');
              // 触发重新分析
              startAnalysis(paperId);
              return;
            } else {
              throw new Error('分析数据不完整，请稍后刷新或重新分析');
            }
          }
        } else if (!response.data.data || Object.keys(response.data.data).length === 0) {
          // 其他未知状态，但没有数据
          throw new Error(response.data.message || '论文尚未分析或数据不可用');
        }
      }
      
      // 使用新结构的数据（无论分析是否完全完成）
      const analysisData = response.data.data || {};
      console.log('处理分析数据:', analysisData);
      
      try {
        // 初始化一个基本的数据结构，确保每个部分都有默认值
        const processedData = {
          // 为各部分提供默认值
          sections: Array.isArray(analysisData.sections) ? analysisData.sections : [],
          methodology: analysisData.methodology && typeof analysisData.methodology === 'object' ? 
            {
              modelArchitecture: analysisData.methodology.modelArchitecture || "未能提取方法论信息或分析尚未完成",
              keyComponents: Array.isArray(analysisData.methodology.keyComponents) ? analysisData.methodology.keyComponents : [],
              algorithm: analysisData.methodology.algorithm || "未能提取算法流程或分析尚未完成",
              innovations: Array.isArray(analysisData.methodology.innovations) ? analysisData.methodology.innovations : []
            } : 
            {
              modelArchitecture: "未能提取方法论信息或分析尚未完成",
              keyComponents: [],
              algorithm: "未能提取算法流程或分析尚未完成",
              innovations: []
            },
          key_findings: Array.isArray(analysisData.key_findings) ? analysisData.key_findings : [],
          weaknesses: Array.isArray(analysisData.weaknesses) ? analysisData.weaknesses : 
                     (typeof analysisData.weaknesses === 'string' ? [{ description: analysisData.weaknesses }] : []),
          future_work: Array.isArray(analysisData.future_work) ? analysisData.future_work : 
                     (typeof analysisData.future_work === 'string' && analysisData.future_work.trim() ? 
                     [{ 
                       direction: "未来研究方向概述", 
                       description: analysisData.future_work,
                       source: "paper"
                     }] : []),
          code_implementation: analysisData.code_implementation || "// 未能生成代码实现或分析尚未完成"
        };
        
        // 更新分析结果状态
        setAnalysisResult(processedData);
        setPaperData(response.data.paper);
        setCurrentStep(2);
        console.log('分析结果处理成功:', processedData);
      } catch (processingError) {
        console.error('处理分析数据时出错:', processingError);
        // 尝试使用最基本的数据结构
        const fallbackData = {
          sections: [],
          methodology: {
            modelArchitecture: "数据处理错误，未能提取方法论信息",
            keyComponents: [],
            algorithm: "数据处理错误，未能提取算法流程",
            innovations: []
          },
          key_findings: [],
          weaknesses: [],
          future_work: [],
          code_implementation: "// 数据处理错误，未能获取代码实现"
        };
        setAnalysisResult(fallbackData);
        setPaperData(response.data.paper || {});
        setCurrentStep(2);
        message.warning('分析数据格式有误，显示基本结果');
      }
      
      // 如果分析完全完成，显示添加到文献库的提示
      if (response.data.status === 'completed') {
        // 显示一个简单的成功提示而不是对话框
        message.success('论文分析已完成');
        
        // 自动跳转到结果页
        setCurrentStep(2);
      } else if (response.data.data && Object.keys(response.data.data).length > 0) {
        // 部分完成的情况
        message.info('显示已分析完成的部分。分析仍在进行中，稍后刷新可获取更多结果。');
      }
      
    } catch (error) {
      console.error('获取分析结果失败:', error);
      
      // 区分不同类型的错误
      if (error.name === 'AbortError' || error.code === 'ECONNABORTED') {
        // 超时错误
        setError('获取分析结果超时，请稍后重试');
        message.warning('获取分析结果超时，但分析可能已完成。请刷新页面或稍后重试。');
      } else if (error.response) {
        // HTTP错误
        const status = error.response.status;
        if (status === 404) {
          setError('找不到分析结果，可能尚未完成');
        } else if (status === 400) {
          setError(error.response.data?.detail || '请求参数错误');
        } else if (status === 500) {
          setError('服务器处理分析结果时出错');
        } else {
          setError(`获取分析结果失败 (HTTP ${status}): ${error.response.data?.detail || error.message}`);
        }
      } else {
        // 其他错误
        setError(`获取分析结果失败: ${error.message}`);
      }
      
      // 如果是论文分析中的错误，保持处理中状态
      if (error.message && error.message.includes('论文分析中')) {
        setAnalysisStatus('processing');
      }
    } finally {
      setLoading(false);
    }
  };

  // 复制代码到剪贴板
  const copyCodeToClipboard = (code) => {
    navigator.clipboard.writeText(code)
      .then(() => message.success('代码已复制到剪贴板'))
      .catch(err => message.error('复制失败: ' + err.message));
  };

  // 方法论Tab的渲染函数
  const renderMethodologyTab = () => {
    if (!analysisResult || !analysisResult.methodology) {
      return <Empty description="未找到方法论分析" />;
    }
    
    const { modelArchitecture, keyComponents, algorithm, innovations } = analysisResult.methodology;
    
    return (
      <Space direction="vertical" style={{ width: '100%' }}>
        <Card 
          title={<Title level={5}>模型架构</Title>} 
          style={{ marginBottom: 16 }}
          extra={<CopyOutlined onClick={() => copyCodeToClipboard(modelArchitecture)} />}
        >
          <Paragraph>
            {modelArchitecture || "未能从论文中提取模型架构信息"}
          </Paragraph>
        </Card>
        
        <Card 
          title={<Title level={5}>关键组件</Title>} 
          style={{ marginBottom: 16 }}
        >
          {Array.isArray(keyComponents) && keyComponents.length > 0 ? (
            <List
              itemLayout="vertical"
              dataSource={keyComponents}
              renderItem={item => (
                <List.Item>
                  <List.Item.Meta
                    title={item.name || "组件"}
                    description={
                      <div>
                        <Paragraph>
                          {item.description || "未提供描述"}
                        </Paragraph>
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          ) : (
            <Empty description="未找到组件信息" />
          )}
        </Card>
        
        <Card 
          title={<Title level={5}>算法流程</Title>} 
          style={{ marginBottom: 16 }}
          extra={<CopyOutlined onClick={() => copyCodeToClipboard(algorithm)} />}
        >
          <Paragraph>
            {algorithm || "未能从论文中提取算法流程信息"}
          </Paragraph>
        </Card>
        
        <Card 
          title={<Title level={5}>创新点</Title>} 
          style={{ marginBottom: 16 }}
        >
          {Array.isArray(innovations) && innovations.length > 0 ? (
            <List
              itemLayout="vertical"
              dataSource={innovations}
              renderItem={(item, index) => (
                <List.Item>
                  <Text strong>{`创新点 ${index + 1}：`}</Text>
                  <Paragraph>
                    {typeof item === 'string' ? item : JSON.stringify(item)}
                  </Paragraph>
                </List.Item>
              )}
            />
          ) : (
            <Empty description="未找到创新点信息" />
          )}
        </Card>
      </Space>
    );
  };

  // 局限性Tab的渲染函数
  const renderWeaknessesTab = () => {
    if (!analysisResult || !analysisResult.weaknesses || !Array.isArray(analysisResult.weaknesses) || analysisResult.weaknesses.length === 0) {
      return <Empty description="未找到局限性分析" />;
    }
    
    return (
      <Space direction="vertical" style={{ width: '100%' }}>
        <List
          itemLayout="vertical"
          dataSource={analysisResult.weaknesses}
          renderItem={(weakness, index) => {
            // 确保weakness是对象类型
            if (typeof weakness !== 'object' || weakness === null) {
              weakness = { 
                type: "数据解析错误", 
                description: String(weakness),
                impact: "无法确定影响",
                improvement: "无法提供改进建议"
              };
            }
            
            // 兼容旧格式和新格式
            const weaknessType = weakness.type || weakness.weakness || "未分类的局限性";
            const description = weakness.description || "未提供描述";
            const impact = weakness.impact || weakness.influence || "未分析影响";
            const improvement = weakness.improvement || "未提供改进建议";
            
            return (
              <Card 
                title={<Text strong>{weaknessType}</Text>} 
                style={{ marginBottom: 16 }}
                extra={<CopyOutlined onClick={() => copyCodeToClipboard(description)} />}
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Paragraph>
                    <Text strong>描述：</Text> {description}
                  </Paragraph>
                  <Paragraph>
                    <Text strong>潜在影响：</Text> {impact}
                  </Paragraph>
                  <Paragraph>
                    <Text strong>改进建议：</Text> {improvement}
                  </Paragraph>
                </Space>
              </Card>
            );
          }}
        />
      </Space>
    );
  };

  // 渲染章节结构
  const renderSections = () => {
    if (!analysisResult || !analysisResult.sections || analysisResult.sections.length === 0) {
      return <Empty description="未找到章节结构" />;
    }
    
    return (
      <Collapse defaultActiveKey={['0']}>
        {analysisResult.sections.map((section, index) => (
          <Panel 
            header={
              <Space>
                <Title level={section.level + 3}>{section.title}</Title>
                {section.level === 1 && <Tag color="blue">主章节</Tag>}
                {section.level === 2 && <Tag color="cyan">子章节</Tag>}
                {section.level > 2 && <Tag color="purple">深层章节</Tag>}
              </Space>
            } 
            key={index}
          >
            <Paragraph>{section.summary}</Paragraph>
          </Panel>
        ))}
      </Collapse>
    );
  };

  // 渲染实验
  const renderExperiments = () => {
    if (!analysisResult) {
      return <Empty description="未获取到分析结果" />;
    }
    
    console.log('渲染实验数据:', analysisResult.experiments);
    
    if (!analysisResult.experiments || Object.keys(analysisResult.experiments).length === 0) {
      return <Empty description="未找到实验信息" />;
    }
    
    try {
      const { datasets = [], baselines = [], metrics = [], mainResults = "", ablationAnalysis = "" } = analysisResult.experiments;
      
      console.log('处理实验数据:',{
        datasets: datasets?.length || 0,
        baselines: baselines?.length || 0,
        metrics: metrics?.length || 0,
        hasMainResults: !!mainResults,
        hasAblation: !!ablationAnalysis
      });
      
      return (
        <div>
          <Card title="数据集" style={{ marginBottom: 16 }}>
            <Table 
              dataSource={Array.isArray(datasets) ? datasets.map((ds, idx) => ({...ds, key: idx})) : []} 
              columns={[
                { title: '数据集名称', dataIndex: 'name', key: 'name', render: (text) => text || '未指定' },
                { title: '描述', dataIndex: 'description', key: 'description', render: (text) => text || '无描述' }
              ]}
              pagination={false}
              locale={{ emptyText: '未找到数据集信息' }}
            />
          </Card>
          
          <Card title="基线方法" style={{ marginBottom: 16 }}>
            <Table 
              dataSource={Array.isArray(baselines) ? baselines.map((bl, idx) => ({...bl, key: idx})) : []} 
              columns={[
                { title: '方法名称', dataIndex: 'name', key: 'name', render: (text) => text || '未指定' },
                { title: '描述', dataIndex: 'description', key: 'description', render: (text) => text || '无描述' }
              ]}
              pagination={false}
              locale={{ emptyText: '未找到基线方法信息' }}
            />
          </Card>
          
          <Card title="评价指标" style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {Array.isArray(metrics) && metrics.length > 0 ? metrics.map((metric, idx) => (
                <Tag color="blue" key={idx}>
                  {typeof metric === 'string' ? metric : (metric.name || '未命名指标')}
                </Tag>
              )) : <Empty description="未找到评价指标" />}
            </div>
          </Card>
          
          <Card title="主要实验结果" style={{ marginBottom: 16 }}>
            <Paragraph>{mainResults || '未提供实验结果'}</Paragraph>
          </Card>
          
          <Card title="消融实验">
            <Paragraph>{ablationAnalysis || '未提供消融实验分析'}</Paragraph>
          </Card>
        </div>
      );
    } catch (error) {
      console.error('渲染实验数据出错:', error, analysisResult.experiments);
      return (
        <Alert 
          message="实验数据解析错误" 
          description={`实验数据结构不符合预期。错误详情：${error.message}`} 
          type="error" 
          showIcon
        />
      );
    }
  };

  // 渲染参考文献
  const renderReferences = () => {
    if (!analysisResult || !analysisResult.references || analysisResult.references.length === 0) {
      return <Empty description="未找到参考文献" />;
    }
    
    return (
      <List
        bordered
        dataSource={analysisResult.references}
        renderItem={(ref, index) => (
          <List.Item>
            <div>
              <Text strong>{index + 1}. </Text>
              <Text>{ref.authors} ({ref.year}). </Text>
              <Text italic>{ref.title}. </Text>
              <Text>{ref.venue}</Text>
            </div>
          </List.Item>
        )}
      />
    );
  };

  // 渲染代码实现
  const renderCodeImplementation = () => {
    if (!analysisResult || !analysisResult.code_implementation) {
      return <Empty description="未找到代码实现" />;
    }

    return (
      <div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
          <Button 
            icon={<CopyOutlined />} 
            onClick={() => copyCodeToClipboard(analysisResult.code_implementation)}
          >
            复制代码
          </Button>
        </div>
        <SyntaxHighlighter language="python" style={{}} showLineNumbers>
          {analysisResult.code_implementation}
        </SyntaxHighlighter>
      </div>
    );
  };

  // 渲染关键发现
  const renderKeyFindings = () => {
    if (!analysisResult || !analysisResult.key_findings || analysisResult.key_findings.length === 0) {
      return <Empty description="未找到关键发现" />;
    }
    
    return (
      <List
        bordered
        dataSource={analysisResult.key_findings}
        renderItem={(finding, index) => (
          <List.Item>
            <div>
              <Text strong>{index + 1}. </Text>
              <Text>{finding}</Text>
            </div>
          </List.Item>
        )}
      />
    );
  };

  // 渲染未来工作
  const renderFutureWork = () => {
    if (!analysisResult || !analysisResult.future_work) {
      return <Empty description="未找到未来工作方向" />;
    }
    
    // 检查future_work是否为数组
    if (Array.isArray(analysisResult.future_work)) {
      // 如果是数组但长度为0，显示Empty组件
      if (analysisResult.future_work.length === 0) {
        return <Empty description="未找到未来工作方向" />;
      }
      
      // 将future_work作为数组进行渲染
      return (
        <List
          bordered
          dataSource={analysisResult.future_work}
          renderItem={(item, index) => (
            <List.Item>
              <div>
                <Text strong>{index + 1}. {item.direction}</Text>
                <div style={{ marginTop: 8 }}>
                  <Text>{item.description}</Text>
                </div>
                {item.source && (
                  <div style={{ marginTop: 4 }}>
                    <Tag color={item.source === 'paper' ? 'blue' : 'orange'}>
                      {item.source === 'paper' ? '论文明确提出' : '推断内容'}
                    </Tag>
                  </div>
                )}
              </div>
            </List.Item>
          )}
        />
      );
    }
    
    // 如果不是数组而是字符串，则直接使用Paragraph组件显示
    return <Paragraph>{analysisResult.future_work}</Paragraph>;
  };

  // 渲染分析进度条
  const renderAnalysisProgress = () => {
    // 根据不同进度阶段使用不同颜色
    let progressColor = 'blue';
    let progressStatus = 'active';
    
    if (analysisProgress >= 95) {
      progressColor = 'green';
      progressStatus = 'success';
    } else if (analysisProgress >= 75) {
      progressColor = 'cyan';
    } else if (analysisProgress >= 40) {
      progressColor = 'blue';
    } else {
      progressColor = 'gold';
    }
    
    // 设置进度条步骤提示
    let progressTip = '预处理论文内容';
    if (analysisProgress >= 95) {
      progressTip = '完成分析';
    } else if (analysisProgress >= 90) {
      progressTip = '分析未来研究方向';
    } else if (analysisProgress >= 85) {
      progressTip = '分析论文局限性';
    } else if (analysisProgress >= 80) {
      progressTip = '准备分析局限性';
    } else if (analysisProgress >= 75) {
      progressTip = '提取关键发现';
    } else if (analysisProgress >= 65) {
      progressTip = '准备提取关键发现';
    } else if (analysisProgress >= 60) {
      progressTip = '生成示例代码';
    } else if (analysisProgress >= 55) {
      progressTip = '准备生成代码';
    } else if (analysisProgress >= 40) {
      progressTip = '方法论分析完成';
    } else if (analysisProgress >= 30) {
      progressTip = '分析方法论内容';
    } else if (analysisProgress >= 25) {
      progressTip = '提取方法论文本';
    } else if (analysisProgress >= 20) {
      progressTip = '准备分析方法论';
    } else if (analysisProgress >= 15) {
      progressTip = '章节结构提取完成';
    } else if (analysisProgress >= 10) {
      progressTip = '提取论文章节结构';
    } else if (analysisProgress >= 5) {
      progressTip = '准备分析论文';
    } else {
      progressTip = '初始化分析';
    }
    
    // 设置提示消息
    let statusMessage = '';
    if (analysisProgress < 40) {
      statusMessage = '正在分析论文结构和方法论，这可能需要几分钟...';
    } else if (analysisProgress < 60) {
      statusMessage = '正在生成代码示例，请耐心等待...';
    } else if (analysisProgress < 85) {
      statusMessage = '正在提取关键发现和研究价值...';
    } else {
      statusMessage = '即将完成分析...';
    }
    
    return (
      <div style={{ marginBottom: 20 }}>
        <Progress 
          percent={analysisProgress} 
          status={progressStatus} 
          strokeColor={progressColor}
          format={percent => `${percent.toFixed(0)}%`}
        />
        <p style={{ textAlign: 'center', marginTop: 8 }}>
          {analysisStatus === 'processing' ? (
            <span><SyncOutlined spin /> {progressTip}</span>
          ) : analysisStatus === 'completed' ? (
            <span><CheckCircleOutlined /> 分析完成</span>
          ) : (
            <span>{progressTip}</span>
          )}
        </p>
        {analysisStatus === 'processing' && (
          <p style={{ textAlign: 'center', color: '#888', fontSize: '12px', marginTop: 4 }}>
            {statusMessage}
          </p>
        )}
      </div>
    );
  };

  // 步骤内容
  const steps = [
    {
      title: '上传论文',
      content: (
        <div>
          <Dragger
            name="file"
            action={`${API_BASE_URL}/papers/upload`}
            headers={{
              Authorization: `Bearer ${localStorage.getItem('token')}`
            }}
            onChange={handleUpload}
            maxCount={1}
            accept=".pdf"
            showUploadList={false}
            data={{
              extract_content: true,
              analyze_content: true,  // 默认设置为true，自动分析
              source: "upload",
              title: ""
            }}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽PDF文件到此区域进行上传</p>
            <p className="ant-upload-hint">
              支持单个PDF文件，文件大小不超过30MB
            </p>
          </Dragger>
        </div>
      )
    },
    {
      title: '分析中',
      content: (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          {loading || analysisStatus === 'processing' ? (
            <Space direction="vertical" style={{ width: '80%' }}>
              <Spin size="large" tip="正在分析论文内容..." />
              {analysisStatus === 'processing' && (
                <div style={{ marginTop: 20 }}>
                  {renderAnalysisProgress()}
                </div>
              )}
            </Space>
          ) : (
            <div>
              <Title level={4}>{paperData?.title}</Title>
              <Space direction="vertical" style={{ width: '100%' }}>
                {paperData && (
                  <Card>
                    <Space>
                      <Text>分析状态:</Text>
                      {analysisStatus && (
                        <Tag 
                          icon={statusMap[analysisStatus].icon} 
                          color={statusMap[analysisStatus].color}
                        >
                          {statusMap[analysisStatus].text}
                        </Tag>
                      )}
                    </Space>
                  </Card>
                )}
                
                {error && (
                  <Alert
                    message="分析错误"
                    description={error}
                    type="error"
                    showIcon
                  />
                )}
                
                {analysisStatus !== 'processing' && (
                  <Button 
                    type="primary" 
                    onClick={() => startAnalysis(uploadedPaperId)}
                    disabled={loading}
                  >
                    开始分析
                  </Button>
                )}
              </Space>
            </div>
          )}
        </div>
      )
    },
    {
      title: '分析结果',
      content: (
        <div>
          {analysisResult ? (
            <div>
              <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <Title level={4}>{analysisResult.title}</Title>
                  {analysisResult.authors && analysisResult.authors.length > 0 && (
                    <Paragraph>
                      <Text type="secondary">
                        作者: {analysisResult.authors.map(author => author.name).join(', ')}
                      </Text>
                    </Paragraph>
                  )}
                </div>
              </div>
              
              <Tabs activeKey={selectedTab} onChange={setSelectedTab}>
                <TabPane
                  tab={<span><NodeIndexOutlined />方法论</span>}
                  key="methodology"
                >
                  {renderMethodologyTab()}
                </TabPane>
                
                <TabPane
                  tab={<span><CodeOutlined />代码实现</span>}
                  key="code"
                >
                  {renderCodeImplementation()}
                </TabPane>
                
                <TabPane
                  tab={<span><BulbOutlined />关键发现</span>}
                  key="key_findings"
                >
                  {renderKeyFindings()}
                </TabPane>
                
                <TabPane
                  tab={<span><AreaChartOutlined />局限性</span>}
                  key="weaknesses"
                >
                  {renderWeaknessesTab()}
                </TabPane>
                
                <TabPane
                  tab={<span><BulbOutlined />未来工作</span>}
                  key="future_work"
                >
                  {renderFutureWork()}
                </TabPane>
              </Tabs>
            </div>
          ) : (
            <Empty description="未获取到分析结果" />
          )}
        </div>
      )
    }
  ];
  
  return (
    <div className="paper-analyzer-container">
      <Card title="论文分析工具" style={{ width: '100%', marginBottom: 20 }}>
        <Steps current={currentStep} style={{ marginBottom: 20 }}>
          <Step title="上传论文" icon={<InboxOutlined />} />
          <Step title="分析中" icon={<BulbOutlined />} />
          <Step title="查看结果" icon={<FileTextOutlined />} />
        </Steps>
        
        {/* 显示分析进度条 */}
        {(analysisStatus === 'processing' || analysisStatus === 'pending') && uploadedPaperId && (
          renderAnalysisProgress()
        )}
      </Card>
      
      <Card style={{ minHeight: 400 }}>
        {steps[currentStep].content}
      </Card>
      
      <div style={{ marginTop: 24, textAlign: 'center' }}>
        {/* 删除"上一步"按钮，不允许返回上一步 */}
      </div>
    </div>
  );
};

export default PaperAnalyzer; 