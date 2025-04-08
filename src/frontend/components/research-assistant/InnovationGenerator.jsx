import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Form, 
  Input, 
  Button, 
  Select, 
  Typography, 
  Divider, 
  Space, 
  Tag, 
  Spin,
  List,
  Collapse,
  Steps,
  Badge,
  Alert,
  Modal,
  Tabs,
  Radio,
  message
} from 'antd';
import { 
  BulbOutlined, 
  SearchOutlined, 
  ExperimentOutlined, 
  FileTextOutlined,
  RiseOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  BookOutlined,
  ApiOutlined,
  RocketOutlined,
  NodeIndexOutlined,
  CodeOutlined,
  StarOutlined,
  WarningOutlined
} from '@ant-design/icons';
import { assistantApi } from '../../services/api';
import ReactMarkdown from 'react-markdown';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { Panel } = Collapse;
const { Step } = Steps;
const { TabPane } = Tabs;

// 创新类型常量
const INNOVATION_TYPES = [
  { value: 'theoretical', label: '理论创新', description: '推荐算法的基础理论框架和模型创新' },
  { value: 'methodological', label: '方法创新', description: '技术实现、算法设计和模型架构创新' },
  { value: 'application', label: '应用创新', description: '新场景、新领域的推荐应用创新' },
];

// 研究主题领域列表
const RESEARCH_DOMAINS = [
  { value: 'sequential', label: '序列推荐', description: '基于用户历史行为序列的推荐技术' },
  { value: 'graph', label: '图神经网络推荐', description: '基于GNN的推荐系统方法' },
  { value: 'multi_modal', label: '多模态推荐', description: '结合图文音视频等多模态信息的推荐' },
  { value: 'knowledge', label: '知识增强推荐', description: '融合知识图谱的推荐技术' },
  { value: 'contrastive', label: '对比学习推荐', description: '应用对比学习的推荐方法' },
  { value: 'llm', label: '大模型推荐', description: '基于大语言模型的推荐系统' },
  { value: 'explainable', label: '可解释推荐', description: '可解释性推荐算法研究' },
  { value: 'fairness', label: '公平推荐', description: '推荐系统公平性研究' }
];

// 模拟创新点生成函数
const generateInnovations = async (values) => {
  console.log('生成创新点参数:', values);
  
  // 模拟API延迟
  return new Promise((resolve) => {
    setTimeout(() => {
      // 根据不同领域和创新类型返回不同的创新点
      let results;
      
      if (values.domain === 'sequential' && values.innovationType === 'methodological') {
        results = {
          domain: '序列推荐',
          innovationType: '方法创新',
          summary: '序列推荐系统在方法层面存在多个创新机会，特别是在模型架构设计、序列表示学习和跨域应用等方面有突破空间。',
          innovations: [
            {
              title: '分层时间感知Transformer架构',
              description: '设计一种新型分层Transformer架构，专门针对不同时间尺度的用户行为建模，包括会话内短期行为、跨会话中期兴趣和长期稳定偏好。',
              theoreticalBasis: '现有序列推荐模型大多采用统一的时间建模方式，无法同时兼顾不同时间尺度的用户行为模式。研究表明用户兴趣存在明显的多尺度时间特性，如会话内高度相关性、跨会话主题连续性以及长期稳定偏好。',
              technicalImplementation: [
                '设计三层嵌套Transformer结构：短期行为编码器、中期兴趣聚合器和长期偏好提取器',
                '引入自适应时间衰减机制，为不同时间窗口的行为分配动态权重',
                '设计层间注意力融合模块，实现不同时间尺度信息的有效集成',
                '添加对比学习辅助任务，增强不同时间尺度表示的区分度'
              ],
              potentialValue: '该架构可以显著提升序列推荐在复杂时间模式场景下的表现，特别适用于包含明显周期性和多尺度兴趣变化的应用场景，如电子商务和内容平台。预计在长序列准确率上可提升8-12%，同时提高模型对用户兴趣变化的适应性。',
              relatedWork: [
                '分层Transformer (Li et al., 2022)',
                '多尺度时间建模 (Wang et al., 2023)',
                '时间感知注意力机制 (Zhang et al., 2022)'
              ]
            },
            {
              title: '自适应多粒度序列压缩框架',
              description: '提出一种自适应多粒度序列压缩框架，能够根据序列内部结构特征自动确定最优压缩策略，平衡信息保留和计算效率。',
              theoreticalBasis: '长序列建模面临计算复杂度与表达能力的权衡问题。现有的序列压缩方法如均匀采样或基于重要性的采样往往采用固定策略，无法适应不同用户行为序列的独特模式和结构特征。',
              technicalImplementation: [
                '设计序列结构特征提取模块，分析序列的稀疏性、周期性和多样性',
                '开发多策略压缩池，包括兴趣块合并、关键点保留和均匀采样等策略',
                '实现基于强化学习的压缩策略选择器，根据序列特征自动选择最优压缩组合',
                '设计重建损失函数，确保压缩后的序列保留原始序列的关键信息'
              ],
              potentialValue: '该框架可以在保持推荐精度的同时，显著降低长序列处理的计算成本，使序列推荐更适用于资源受限环境和实时推荐场景。测试表明，计算复杂度可降低60%以上，同时保持98%的推荐准确率。',
              relatedWork: [
                '序列压缩技术 (Chen et al., 2023)',
                '自适应采样策略 (Liu et al., 2022)',
                '信息瓶颈压缩 (Yang et al., 2023)'
              ]
            },
            {
              title: '对比互增强的多序列跨域推荐框架',
              description: '构建一种创新的多序列跨域推荐框架，通过对比学习实现不同领域用户行为序列的表示对齐和互增强，解决跨领域冷启动和数据稀疏问题。',
              theoreticalBasis: '用户在不同领域的行为序列往往存在内在关联，但当前跨域推荐模型多关注静态用户表示的迁移，忽略了序列动态模式的跨域共享潜力。对比学习提供了连接不同表示空间的有效机制。',
              technicalImplementation: [
                '设计双流序列编码器，分别处理源域和目标域的用户行为序列',
                '构建序列级和项目级双重对比学习目标，促进不同领域表示空间对齐',
                '引入领域特定和领域共享的表示分离机制，平衡通用性和特异性',
                '设计跨域序列模式迁移模块，实现行为模式的显式迁移'
              ],
              potentialValue: '该框架特别适用于多业务场景，可有效缓解目标域数据稀疏和冷启动问题，提升跨域推荐性能。实验表明，在目标域数据稀疏场景下可提升20%以上的推荐准确率，显著优于传统跨域推荐方法。',
              relatedWork: [
                '跨域序列推荐 (Zhang et al., 2023)',
                '对比表示对齐 (Wang et al., 2022)',
                '双流神经网络 (Li et al., 2023)'
              ]
            }
          ],
          references: [
            'Li, H. et al. (2022). Hierarchical Transformer for Sequential Recommendation. WWW 2022.',
            'Wang, X. et al. (2023). Multi-scale Temporal Modeling for Sequential Recommendation. SIGIR 2023.',
            'Zhang, Y. et al. (2022). Time-aware Attention Networks for Sequential Recommendation. KDD 2022.',
            'Chen, M. et al. (2023). Efficient Sequence Compression for Recommendation. WSDM 2023.',
            'Liu, Z. et al. (2022). Adaptive Sampling Strategies for Long Sequential Recommendation. RecSys 2022.',
            'Yang, L. et al. (2023). Information Bottleneck Compression for Sequential Recommendation. CIKM 2023.',
            'Zhang, Y. et al. (2023). Cross-domain Sequential Recommendation via Contrastive Learning. SIGIR 2023.',
            'Wang, X. et al. (2022). Contrastive Representation Alignment for Cross-domain Recommendation. WWW 2022.',
            'Li, J. et al. (2023). Dual-stream Neural Networks for Cross-domain Sequential Recommendation. KDD 2023.'
          ]
        };
      } else if (values.domain === 'contrastive' && values.innovationType === 'theoretical') {
        results = {
          domain: '对比学习推荐',
          innovationType: '理论创新',
          summary: '对比学习推荐系统在理论基础方面存在多个创新方向，特别是在表示学习理论、负样本理论和自适应对比机制等方面有深入探索空间。',
          innovations: [
            {
              title: '推荐系统专用信息对比理论框架',
              description: '构建推荐系统专用的信息对比理论框架，解释对比学习在稀疏、高维和不平衡推荐数据上的工作机制，并提供理论保证和指导。',
              theoreticalBasis: '现有对比学习理论主要来自计算机视觉和自然语言处理领域，未能充分考虑推荐数据的特殊性。推荐系统面临的用户-项目交互数据高度稀疏、长尾分布明显、多重隐式反馈并存等特性，需要专门的理论框架。',
              technicalImplementation: [
                '建立考虑推荐数据稀疏性的互信息下界',
                '推导包含流行度偏差修正的对比目标函数',
                '构建多粒度互信息最大化理论',
                '设计适应推荐场景的对比温度参数理论解析方法'
              ],
              potentialValue: '该理论框架将为对比学习在推荐系统中的应用提供坚实基础，指导对比损失设计、负样本选择和训练策略优化，预计可提升对比学习推荐模型10-15%的性能，并提高模型解释性和可靠性。',
              relatedWork: [
                '信息对比学习理论 (Liu et al., 2022)',
                '推荐系统表示学习理论 (Chen et al., 2023)',
                '互信息最大化原则 (Wang et al., 2023)'
              ]
            },
            {
              title: '自适应难度负样本谱系理论',
              description: '提出负样本难度谱系理论，从信息论和学习动力学角度阐述不同类型负样本对模型学习的影响机制，并设计自适应负样本选择策略。',
              theoreticalBasis: '负样本选择是对比学习的核心挑战，但缺乏系统的理论指导。现有研究表明，不同难度的负样本对模型学习的贡献存在显著差异，但其工作机制和最优选择策略尚不明确。',
              technicalImplementation: [
                '构建负样本难度量化理论，基于语义相似性和用户交互模式',
                '建立负样本-学习进展动态关系模型，解释不同阶段最优负样本分布',
                '推导课程学习视角下的负样本调度理论',
                '设计自适应负样本采样策略的理论基础'
              ],
              potentialValue: '该理论将革新对比学习推荐中的负样本选择方法，提供从随机采样到困难样本挖掘的统一理论框架。实验验证表明，基于该理论指导的负样本策略可提升模型收敛速度30%，并改善最终性能7-12%。',
              relatedWork: [
                '困难负样本挖掘 (Zhang et al., 2022)',
                '课程学习理论 (Li et al., 2023)',
                '动态负样本采样 (Yang et al., 2022)'
              ]
            },
            {
              title: '多粒度交互对比表示理论',
              description: '发展多粒度用户-项目交互对比表示理论，从微观交互到宏观偏好模式的统一建模框架，弥合逐点推荐与序列推荐的理论鸿沟。',
              theoreticalBasis: '推荐系统中的用户-项目交互存在多个粒度层次，从单次点击到完整会话再到长期行为模式。现有对比学习方法多针对单一粒度优化，缺乏跨粒度的统一理论框架。',
              technicalImplementation: [
                '建立从微观交互到宏观偏好的多层次表示理论',
                '构建跨粒度对比学习目标及其理论保证',
                '设计粒度间知识蒸馏的理论机制',
                '推导多粒度表示的互补性度量与优化方法'
              ],
              potentialValue: '该理论将打破传统推荐模型在不同交互粒度上的隔阂，提供从单次交互到长期偏好的统一建模视角。实验表明，基于该理论的多粒度对比学习可同时提升即时推荐和序列推荐性能，平均提升8.5%。',
              relatedWork: [
                '多粒度推荐表示 (Wang et al., 2022)',
                '层次化对比学习 (Zhang et al., 2023)',
                '交互粒度理论 (Chen et al., 2022)'
              ]
            }
          ],
          references: [
            'Liu, Z. et al. (2022). Toward Theoretical Understanding of Contrastive Learning in Recommendation. SIGIR 2022.',
            'Chen, M. et al. (2023). A Theoretical Framework for Representation Learning in Recommender Systems. NeurIPS 2023.',
            'Wang, X. et al. (2023). Mutual Information Maximization in Recommendation: A Theoretical Perspective. KDD 2023.',
            'Zhang, Y. et al. (2022). Hard Negative Mining in Contrastive Recommendation: Theory and Practice. WWW 2022.',
            'Li, J. et al. (2023). Curriculum Learning for Contrastive Recommendation. SIGIR 2023.',
            'Yang, L. et al. (2022). Dynamic Negative Sampling for Contrastive Learning. WSDM 2022.',
            'Wang, X. et al. (2022). Multi-granularity Representations for Recommendation. NeurIPS 2022.',
            'Zhang, Y. et al. (2023). Hierarchical Contrastive Learning for Recommendation. SIGIR 2023.',
            'Chen, M. et al. (2022). Interaction Granularity Theory for Recommender Systems. KDD 2022.'
          ]
        };
      } else if (values.domain === 'llm' && values.innovationType === 'application') {
        results = {
          domain: '大模型推荐',
          innovationType: '应用创新',
          summary: '大语言模型在推荐系统中的应用创新空间广阔，特别是在个性化内容生成、跨模态推荐理解和交互式推荐对话等方面有巨大潜力。',
          innovations: [
            {
              title: '个性化内容摘要与重写推荐系统',
              description: '开发基于大语言模型的个性化内容摘要与重写推荐系统，根据用户兴趣和阅读偏好动态调整内容呈现方式，提升信息获取效率和用户体验。',
              theoreticalBasis: '传统推荐系统关注"推荐什么内容"，而忽视了"如何呈现内容"的重要性。研究表明，内容呈现方式对用户接受度和转化率有显著影响。大语言模型的文本生成和改写能力为个性化内容呈现提供了技术可能。',
              technicalImplementation: [
                '构建用户阅读偏好画像模块，包括风格偏好、长度偏好和专业度偏好',
                '开发多维度内容特征提取器，分析文章结构、关键信息和语言风格',
                '设计个性化提示工程系统，生成针对特定用户的内容改写指令',
                '实现基于大语言模型的内容摘要、重点突出和风格适配功能'
              ],
              potentialValue: '该系统能显著提升用户内容消费效率和满意度，特别适用于信息密集型平台如新闻、学术和专业内容服务。实验表明，个性化内容呈现可提高用户阅读完成率35%，内容互动率22%，同时减少信息获取时间40%。',
              relatedWork: [
                '个性化摘要生成 (Wang et al., 2023)',
                '内容自适应呈现 (Li et al., 2022)',
                '大语言模型内容改写 (Chen et al., 2023)'
              ]
            },
            {
              title: '多轮对话式意图挖掘推荐助手',
              description: '构建创新的对话式推荐助手，通过多轮自然语言交互深入挖掘用户隐式需求和偏好，弥合用户表达与系统理解之间的语义鸿沟。',
              theoreticalBasis: '传统推荐系统难以处理复杂、模糊或多维度的用户需求，用户也常难以准确表达自己的真实偏好。多轮对话提供了渐进式澄清和需求精化的机制，而大语言模型的理解和生成能力使自然对话式推荐成为可能。',
              technicalImplementation: [
                '设计基于不确定性的主动提问策略，识别并消除用户需求的模糊点',
                '开发对话式偏好抽取模型，从自然语言交互中提取结构化偏好',
                '构建对话历史感知的推荐引擎，支持偏好动态调整和需求精化',
                '实现多样化推荐理由生成，提供个性化解释和建议'
              ],
              potentialValue: '该系统将革新用户与推荐系统的交互方式，特别适用于复杂决策场景如旅游规划、教育资源推荐和高价值产品选择。数据显示，对话式推荐可提高用户决策满意度42%，减少决策时间35%，并显著降低用户放弃率。',
              relatedWork: [
                '对话推荐系统 (Zhang et al., 2022)',
                '意图挖掘技术 (Yang et al., 2023)',
                '大语言模型辅助决策 (Liu et al., 2023)'
              ]
            },
            {
              title: '跨模态内容理解与创意推荐平台',
              description: '打造基于大语言模型的跨模态内容理解与创意推荐平台，能够分析图像、视频和文本的深层语义，发现创意关联，支持创作者灵感激发和素材推荐。',
              theoreticalBasis: '创意工作者常需要跨媒体类型寻找灵感和素材，传统推荐系统难以理解不同模态内容间的深层创意联系。多模态大语言模型展现了理解和关联不同媒体类型的潜力，为创意推荐提供了新可能。',
              technicalImplementation: [
                '集成多模态内容编码器，统一表示图像、视频和文本内容',
                '设计创意关联发现引擎，识别不同媒体间的灵感连接',
                '开发风格迁移推荐模块，支持跨媒体类型的创意迁移',
                '实现基于用户创作历史的个性化创意推荐流'
              ],
              potentialValue: '该平台将彻底改变创意工作者的工作流程，提供前所未有的跨媒体灵感发现体验。应用场景包括设计、营销内容创作、短视频制作等创意领域。测试显示，使用该平台可提升创意生产效率28%，增加创意多样性35%，并促进跨媒体创新。',
              relatedWork: [
                '多模态创意推荐 (Chen et al., 2022)',
                '跨媒体灵感挖掘 (Wang et al., 2023)',
                '大语言模型辅助创作 (Li et al., 2023)'
              ]
            }
          ],
          references: [
            'Wang, X. et al. (2023). Personalized Content Summarization with Large Language Models. ACL 2023.',
            'Li, J. et al. (2022). Content Adaptive Presentation for Information Recommendation. SIGIR 2022.',
            'Chen, M. et al. (2023). Large Language Models for Content Rewriting in Recommendation. KDD 2023.',
            'Zhang, Y. et al. (2022). Towards Conversational Recommendation: Models and Evaluation. WWW 2022.',
            'Yang, L. et al. (2023). Intent Mining in Conversational Recommender Systems. SIGIR 2023.',
            'Liu, Z. et al. (2023). Large Language Models for Decision Support in Recommendation. RecSys 2023.',
            'Chen, M. et al. (2022). Cross-modal Creative Recommendation. MM 2022.',
            'Wang, X. et al. (2023). Multimodal Inspiration Mining for Content Creators. SIGIR 2023.',
            'Li, J. et al. (2023). Large Language Models as Creative Assistants. CHI 2023.'
          ]
        };
      } else {
        // 默认创新点（通用）
        results = {
          domain: RESEARCH_DOMAINS.find(d => d.value === values.domain)?.label || '推荐系统',
          innovationType: INNOVATION_TYPES.find(t => t.value === values.innovationType)?.label || '创新方向',
          summary: `${RESEARCH_DOMAINS.find(d => d.value === values.domain)?.label || '推荐系统'}领域的${INNOVATION_TYPES.find(t => t.value === values.innovationType)?.label || '创新'}具有广阔前景，以下提供几个潜在创新点供参考。`,
          innovations: [
            {
              title: '自适应推荐架构',
              description: '设计一种能够根据用户特性和场景需求动态调整推荐策略和模型结构的自适应推荐架构。',
              theoreticalBasis: '现有推荐模型通常采用固定结构，难以适应不同用户群体和场景的差异化需求。研究表明，针对不同用户和场景定制化的推荐策略可显著提升性能。',
              technicalImplementation: [
                '设计模块化推荐组件库，支持灵活组合',
                '开发用户-场景特征分析器，识别关键模式',
                '构建策略选择器，动态组装最优推荐流程',
                '实现在线学习机制，持续优化策略选择'
              ],
              potentialValue: '该创新可大幅提升推荐系统的灵活性和适应性，特别适用于用户群体多样、使用场景复杂的大型平台。预计可提升推荐相关性15-20%，同时提高系统对冷启动和长尾问题的处理能力。',
              relatedWork: [
                '动态神经网络 (Liu et al., 2022)',
                '元学习推荐 (Wang et al., 2023)',
                '自适应特征选择 (Zhang et al., 2022)'
              ]
            },
            {
              title: '多目标平衡优化框架',
              description: '提出推荐系统多目标平衡优化框架，解决准确性、多样性、新颖性和公平性等多维目标的权衡问题。',
              theoreticalBasis: '推荐系统面临多个潜在冲突的优化目标，传统方法多采用简单加权或分阶段优化，难以找到真正的平衡点。帕累托最优理论和多智能体博弈为解决此类问题提供了新思路。',
              technicalImplementation: [
                '构建多目标表示学习框架，统一不同指标的优化空间',
                '设计基于帕累托前沿的动态权重调整机制',
                '开发多智能体协同优化算法，协调不同目标',
                '实现个性化目标平衡策略，适应不同用户偏好'
              ],
              potentialValue: '该框架将帮助推荐系统摆脱单一指标优化的局限，实现更全面的用户体验提升。应用该框架后，推荐系统可在保持准确率的同时，提升多样性18%，新颖性12%，同时改善不同群体间的公平性。',
              relatedWork: [
                '多目标推荐优化 (Chen et al., 2023)',
                '帕累托前沿学习 (Li et al., 2022)',
                '公平多样推荐 (Yang et al., 2023)'
              ]
            },
            {
              title: '知识增强解释框架',
              description: '开发知识图谱增强的推荐解释框架，提供个性化、多样化和交互式的推荐理由，提升系统透明度和用户信任。',
              theoreticalBasis: '推荐解释是构建可信AI系统的关键环节，但现有解释方法多局限于简单关联或模板生成，缺乏深度知识支持和个性化定制。知识图谱提供了丰富的领域知识，可用于生成更有说服力的解释。',
              technicalImplementation: [
                '构建多源知识融合图谱，整合领域知识和用户历史',
                '设计个性化路径挖掘算法，发现用户-项目间的知识连接',
                '开发多样化解释生成器，支持不同类型和粒度的解释',
                '实现交互式解释优化机制，根据用户反馈调整解释策略'
              ],
              potentialValue: '该框架将显著提升推荐系统的透明度和可信度，特别适用于需要高度用户信任的领域如医疗、教育和金融推荐。研究表明，有效的解释可提高用户采纳率25%，满意度20%，并增强长期使用意愿。',
              relatedWork: [
                '知识图谱推荐 (Wang et al., 2022)',
                '可解释AI技术 (Zhang et al., 2023)',
                '交互式解释生成 (Liu et al., 2022)'
              ]
            }
          ],
          references: [
            'Liu, Z. et al. (2022). Dynamic Neural Networks for Recommendation. SIGIR 2022.',
            'Wang, X. et al. (2023). Meta-learning for Recommendation Systems. KDD 2023.',
            'Zhang, Y. et al. (2022). Adaptive Feature Selection in Recommendation. WWW 2022.',
            'Chen, M. et al. (2023). Multi-objective Optimization for Recommendation. WSDM 2023.',
            'Li, J. et al. (2022). Pareto Front Learning in Multi-objective Recommendation. NeurIPS 2022.',
            'Yang, L. et al. (2023). Balancing Fairness and Diversity in Recommendation. SIGIR 2023.',
            'Wang, X. et al. (2022). Knowledge Graph Enhanced Recommendation. WWW 2022.',
            'Zhang, Y. et al. (2023). Explainable AI for Recommendation Systems. KDD 2023.',
            'Liu, Z. et al. (2022). Interactive Explanation Generation for Recommendation. CIKM 2022.'
          ]
        };
      }
      
      resolve(results);
    }, 3000);
  });
};

// 组件主体
const InnovationGenerator = () => {
  // 状态管理
  const [form] = Form.useForm();
  const [generating, setGenerating] = useState(false);
  const [results, setResults] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [activeInnovation, setActiveInnovation] = useState(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [innovationPerspectives, setInnovationPerspectives] = useState([]);
  const [innovationResults, setInnovationResults] = useState(null);
  const [error, setError] = useState(null);
  
  // 获取研究领域和创新视角列表
  useEffect(() => {
    const fetchInnovationPerspectives = async () => {
      try {
        const perspectives = await assistantApi.getInnovationPerspectives();
        if (perspectives && Array.isArray(perspectives)) {
          setInnovationPerspectives(perspectives);
        }
      } catch (error) {
        console.error('获取创新视角列表失败:', error);
        // 使用默认视角列表
      }
    };

    fetchInnovationPerspectives();
  }, []);
  
  // 提交表单进行创新点生成
  const handleSubmit = async () => {
    try {
      // 显示加载状态
      setLoading(true);
      message.loading({
        content: "正在生成创新点建议，这可能需要一些时间...",
        key: "innovationLoading",
        duration: 0,
      });
      
      // 验证必填字段
      if (!form.getFieldValue('researchTopic')) {
        message.error("研究主题不能为空");
        setLoading(false);
        message.destroy("innovationLoading");
        return;
      }
      
      console.log("提交创新点生成请求:", form.getFieldsValue());
      
      // 调用API生成创新点
      const response = await assistantApi.generateInnovationIdeas(
        form.getFieldValue('researchTopic'),
        form.getFieldValue('paper_ids') || [],
        form.getFieldValue('innovationType') || 'methodological',
        form.getFieldValue('additionalContext')
      );
      
      // 清除加载状态
      message.destroy("innovationLoading");
      setLoading(false);
      
      // 处理API返回的错误
      if (response && response.error) {
        console.error("创新点生成失败:", response.message);
        message.error({
          content: `创新点生成失败: ${response.message}${response.details ? `，${response.details}` : ''}`,
          duration: 5,
        });
        
        // 即使有错误也设置结果，以便UI可以显示一些内容
        setResults({
          summary: response.message,
          domain: form.getFieldValue('researchTopic'),
          innovations: [],
          references: []
        });
        setInnovationResults({
          summary: response.message,
          domain: form.getFieldValue('researchTopic'),
          innovations: [],
          references: []
        });
        return;
      }
      
      console.log("创新点生成结果:", response);
      
      // 成功处理
      if (response) {
        const innovationCount = response.innovations ? response.innovations.length : 0;
        message.success(`已生成${innovationCount}个创新点建议`);
        
        // 保存会话ID
        if (response.session_id) {
          const currentSessions = JSON.parse(localStorage.getItem('innovationSessions') || '[]');
          if (!currentSessions.includes(response.session_id)) {
            currentSessions.push(response.session_id);
            localStorage.setItem('innovationSessions', JSON.stringify(currentSessions));
          }
        }
        
        // 直接使用标准化数据格式
        const adaptedResponse = {
          domain: response.research_topic,
          innovationType: response.innovation_type || form.getFieldValue('innovationType') || "methodological",
          summary: response.summary || "",
          final_summary: response.final_summary || "",
          implementation_strategy: response.implementation_strategy || "",
          innovations: response.innovations || [],
          references: response.references || []
        };
        
        // 标准化字段名称
        adaptedResponse.innovations = adaptedResponse.innovations.map(innovation => {
          const standardizedInnovation = { ...innovation };
          
          // 确保关键字段使用正确的驼峰命名 
          if ('theoretical_basis' in innovation && !('theoreticalBasis' in innovation)) {
            standardizedInnovation.theoreticalBasis = innovation.theoretical_basis;
            delete standardizedInnovation.theoretical_basis;
          }
          
          if ('potential_value' in innovation && !('potentialValue' in innovation)) {
            standardizedInnovation.potentialValue = innovation.potential_value;
            delete standardizedInnovation.potential_value;
          }
          
          if ('related_work' in innovation && !('relatedWork' in innovation)) {
            standardizedInnovation.relatedWork = innovation.related_work;
            delete standardizedInnovation.related_work;
          }
          
          if ('technical_challenges' in innovation && !('technicalChallenges' in innovation)) {
            standardizedInnovation.technicalChallenges = innovation.technical_challenges;
            delete standardizedInnovation.technical_challenges;
          }
          
          if ('solution_approaches' in innovation && !('solutionApproaches' in innovation)) {
            standardizedInnovation.solutionApproaches = innovation.solution_approaches;
            delete standardizedInnovation.solution_approaches;
          }
          
          // 确保列表类型的字段始终是数组
          const listFields = ['technical_implementation', 'relatedWork', 'technicalChallenges', 'solutionApproaches'];
          listFields.forEach(field => {
            if (standardizedInnovation[field] && !Array.isArray(standardizedInnovation[field])) {
              standardizedInnovation[field] = [standardizedInnovation[field]];
            } else if (!standardizedInnovation[field]) {
              standardizedInnovation[field] = [];
            }
          });
          
          return standardizedInnovation;
        });
        
        // 设置结果状态
        setResults(adaptedResponse);
        setInnovationResults(adaptedResponse);
        setCurrentStep(2); // 切换到结果显示步骤
      } else {
        // 响应格式不符合预期
        message.warning("创新点生成结果格式不正确");
        console.error("创新点响应格式异常:", response);
        setResults({
          summary: "服务器返回的数据格式不正确",
          domain: form.getFieldValue('researchTopic'),
          innovations: [],
          references: []
        });
        setInnovationResults({
          summary: "服务器返回的数据格式不正确",
          domain: form.getFieldValue('researchTopic'),
          innovations: [],
          references: []
        });
      }
    } catch (error) {
      // 清除加载状态
      setLoading(false);
      message.destroy("innovationLoading");
      
      // 处理异常
      console.error("创新点生成过程出现异常:", error);
      message.error({
        content: `生成创新点时发生错误: ${error.message || "未知错误"}`,
        duration: 5
      });
      
      // 设置错误状态
      setResults({
        summary: `生成过程发生错误: ${error.message || "未知错误"}`,
        domain: form.getFieldValue('researchTopic'),
        innovations: [],
        references: []
      });
      setInnovationResults({
        summary: `生成过程发生错误: ${error.message || "未知错误"}`,
        domain: form.getFieldValue('researchTopic'),
        innovations: [],
        references: []
      });
    }
  };
  
  // 显示创新点详情
  const showInnovationDetails = (innovation) => {
    console.log("打开创新点详情:", JSON.stringify(innovation, null, 2));
    // 确保所有关键字段都存在并标准化
    const standardizedInnovation = { ...innovation };
    
    // 标准化字段，确保所有字段都存在
    const defaultInnovation = {
      title: "未命名创新点",
      description: "无描述",
      theoreticalBasis: "无理论基础",
      technical_implementation: [],
      potentialValue: "无潜在价值",
      relatedWork: [],
      technicalChallenges: [],
      solutionApproaches: []
    };
    
    // 合并默认值和当前创新点
    Object.keys(defaultInnovation).forEach(key => {
      if (!standardizedInnovation[key]) {
        standardizedInnovation[key] = defaultInnovation[key];
      }
    });
    
    // 确保所有列表字段都是数组
    ['technical_implementation', 'relatedWork', 'technicalChallenges', 'solutionApproaches'].forEach(field => {
      if (standardizedInnovation[field] && !Array.isArray(standardizedInnovation[field])) {
        standardizedInnovation[field] = [standardizedInnovation[field]];
      }
    });
    
    setActiveInnovation(standardizedInnovation);
    setDetailModalVisible(true);
  };
  
  // 重置生成
  const handleReset = () => {
    form.resetFields();
    setInnovationResults(null);
    setError(null);
    setActiveInnovation(null);
  };
  
  return (
    <div className="innovation-generator">
      <Card bordered={false}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            domain: 'sequential',
            innovationType: 'methodological',
            additionalContext: '',
            researchTopic: ''
          }}
        >
          <Form.Item
            name="researchTopic"
            label="研究主题"
            rules={[{ required: true, message: '请输入研究主题' }]}
          >
            <Input 
              placeholder="例如：序列推荐、跨域推荐、知识增强推荐等" 
              allowClear
            />
          </Form.Item>
          
          <Form.Item
            name="innovationType"
            label="创新类型"
            rules={[{ required: true, message: '请选择创新类型' }]}
          >
            <Radio.Group>
              {INNOVATION_TYPES.map(type => (
                <Radio.Button key={type.value} value={type.value}>
                  {type.label} - {type.description}
                </Radio.Button>
              ))}
            </Radio.Group>
          </Form.Item>
          
          <Form.Item
            name="domain"
            label="研究领域"
            rules={[{ required: true, message: '请选择研究领域' }]}
          >
            <Select placeholder="选择推荐系统研究领域">
              {RESEARCH_DOMAINS.map(domain => (
                <Option key={domain.value} value={domain.value}>
                  {domain.label} - {domain.description}
                </Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item
            name="additionalContext"
            label="额外上下文信息（可选）"
            extra="可提供您的具体研究方向、关注的问题或已有的相关工作"
          >
            <TextArea 
              placeholder="请输入您的研究重点、已有工作或特定关注点..." 
              autoSize={{ minRows: 3, maxRows: 6 }}
            />
          </Form.Item>
          
          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              icon={<BulbOutlined />}
              loading={loading}
              disabled={loading}
            >
              生成创新点建议
            </Button>
          </Form.Item>
        </Form>

        {loading && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
            <div style={{ marginTop: 24 }}>
              <Title level={4}>
                AI正在为{form.getFieldValue('domain') && RESEARCH_DOMAINS.find(d => d.value === form.getFieldValue('domain'))?.label}
                领域生成{form.getFieldValue('innovationType') && INNOVATION_TYPES.find(t => t.value === form.getFieldValue('innovationType'))?.label}...
              </Title>
              <Paragraph>
                创新点生成过程包括：分析现有研究、发现创新机会、设计技术方案、评估潜在价值，请稍候...
              </Paragraph>
            </div>
          </div>
        )}

        {error && (
          <Alert
            type="error"
            message="生成失败"
            description={error}
            showIcon
            style={{ marginTop: 16 }}
          />
        )}

        {innovationResults && !loading && (
          <div className="innovation-results">
            <div className="results-header">
              <Title level={3}>{innovationResults.domain}领域{innovationResults.innovationType}建议</Title>
              <Paragraph>{innovationResults.summary}</Paragraph>
              
              {innovationResults.implementation_strategy && (
                <div style={{ marginTop: 16, marginBottom: 16, padding: 16, background: '#f5f5f5', borderRadius: 8 }}>
                  <Title level={4}>实现策略</Title>
                  <Paragraph><ReactMarkdown>{innovationResults.implementation_strategy}</ReactMarkdown></Paragraph>
                </div>
              )}
              
              <div style={{ textAlign: 'right', marginBottom: 16 }}>
                <Button onClick={handleReset} icon={<SyncOutlined />}>
                  重新生成
                </Button>
              </div>
            </div>
            
            <Alert
              type="success"
              message="创新点生成完成"
              description={`已为您生成${innovationResults.innovations.length}个高质量创新点，包含理论基础、技术实现和潜在价值分析。点击查看详情获取完整实现思路。`}
              showIcon
              style={{ marginBottom: 24 }}
            />
            
            <List
              itemLayout="vertical"
              dataSource={innovationResults.innovations}
              renderItem={(innovation, index) => (
                <List.Item
                  key={index}
                  actions={[
                    <Button 
                      type="link" 
                      onClick={() => showInnovationDetails(innovation)}
                      icon={<FileTextOutlined />}
                    >
                      查看详情
                    </Button>
                  ]}
                >
                  <List.Item.Meta
                    avatar={
                      <Badge 
                        count={index + 1} 
                        style={{ 
                          backgroundColor: index === 0 ? '#52c41a' : (index === 1 ? '#1890ff' : '#722ed1'),
                          width: 26,
                          height: 26,
                          lineHeight: '26px',
                          borderRadius: '50%'
                        }} 
                      />
                    }
                    title={
                      <Space>
                        <Text strong>{innovation.title || "未命名创新点"}</Text>
                        <Tag color={index === 0 ? 'success' : (index === 1 ? 'processing' : 'purple')}>
                          {index === 0 ? '最佳创新点' : (index === 1 ? '高潜力创新' : '创新方向')}
                        </Tag>
                        {innovation.innovation_type && (
                          <Tag color="blue">{innovation.innovation_type}</Tag>
                        )}
                      </Space>
                    }
                    description={
                      <div>
                        <ReactMarkdown>{innovation.description || innovation.core_concept || innovation.technical_description || ""}</ReactMarkdown>
                        {innovation.key_insight && (
                          <div style={{ marginTop: 8 }}>
                            <Text type="secondary">核心洞察: </Text>
                            <Text italic>{innovation.key_insight}</Text>
                          </div>
                        )}
                      </div>
                    }
                  />
                  {innovation.differentiators && (
                    <div style={{ marginTop: 12, paddingLeft: 32 }}>
                      <Text type="secondary">与现有研究的区别: </Text>
                      <Text>{innovation.differentiators}</Text>
                    </div>
                  )}
                </List.Item>
              )}
            />
            
            {innovationResults.references && innovationResults.references.length > 0 && (
              <>
                <Divider>参考文献</Divider>
                <div className="references">
                  <List
                    size="small"
                    dataSource={innovationResults.references}
                    renderItem={(reference, index) => (
                      <List.Item>
                        <Text mark>[{index + 1}]</Text> <ReactMarkdown>{reference}</ReactMarkdown>
                      </List.Item>
                    )}
                  />
                </div>
              </>
            )}
          </div>
        )}
      </Card>
      
      {/* 创新点详情模态框 */}
      <Modal
        title={activeInnovation?.title || '创新点详情'}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="back" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {activeInnovation && (
          <div className="innovation-details">
            <Paragraph strong>
              <ReactMarkdown>{activeInnovation.description || "无描述"}</ReactMarkdown>
            </Paragraph>
            
            {activeInnovation.key_insight && (
              <div style={{ marginBottom: 16, background: '#f0f9ff', padding: 12, borderRadius: 4 }}>
                <Text strong>核心洞察: </Text>
                <Text italic>{activeInnovation.key_insight}</Text>
              </div>
            )}

            <Tabs defaultActiveKey="theoretical">
              <TabPane 
                tab={<span><BookOutlined />理论基础</span>} 
                key="theoretical"
              >
                {activeInnovation.theoreticalBasis ? (
                  <Paragraph>
                    <ReactMarkdown>{activeInnovation.theoreticalBasis}</ReactMarkdown>
                  </Paragraph>
                ) : (
                  <Alert
                    message="无理论基础信息"
                    description="当前创新点没有提供理论基础相关信息。"
                    type="info"
                    showIcon
                  />
                )}
                
                {activeInnovation.differentiators && (
                  <div style={{ marginTop: 16 }}>
                    <Title level={5}>创新点差异化优势</Title>
                    <Paragraph>
                      <ReactMarkdown>{activeInnovation.differentiators}</ReactMarkdown>
                    </Paragraph>
                  </div>
                )}
              </TabPane>
              
              <TabPane 
                tab={<span><CodeOutlined />技术实现</span>} 
                key="technical"
              >
                {Array.isArray(activeInnovation.technical_implementation) && activeInnovation.technical_implementation.length > 0 ? (
                  <List
                    itemLayout="horizontal"
                    dataSource={activeInnovation.technical_implementation}
                    renderItem={(item, index) => (
                      <List.Item>
                        <Space align="start">
                          <Badge count={index + 1} style={{ backgroundColor: '#1890ff' }} />
                          <ReactMarkdown>{item}</ReactMarkdown>
                        </Space>
                      </List.Item>
                    )}
                  />
                ) : (
                  <Alert
                    message="无技术实现信息"
                    description="当前创新点没有提供技术实现相关信息。"
                    type="info"
                    showIcon
                  />
                )}
                
                {activeInnovation.feasibilityAnalysis && (
                  <div style={{ marginTop: 16 }}>
                    <Title level={5}>可行性分析</Title>
                    <Paragraph>
                      <ReactMarkdown>{activeInnovation.feasibilityAnalysis}</ReactMarkdown>
                    </Paragraph>
                  </div>
                )}
              </TabPane>
              
              <TabPane 
                tab={<span><RiseOutlined />潜在价值</span>} 
                key="value"
              >
                {activeInnovation.potentialValue ? (
                  <Paragraph>
                    <ReactMarkdown>{activeInnovation.potentialValue}</ReactMarkdown>
                  </Paragraph>
                ) : (
                  <Alert
                    message="无潜在价值信息"
                    description="当前创新点没有提供潜在价值相关信息。"
                    type="info"
                    showIcon
                  />
                )}
              </TabPane>
              
              {(Array.isArray(activeInnovation.technicalChallenges) && activeInnovation.technicalChallenges.length > 0) && (
                <TabPane 
                  tab={<span><WarningOutlined />技术挑战</span>} 
                  key="challenges"
                >
                  <List
                    itemLayout="horizontal"
                    dataSource={activeInnovation.technicalChallenges}
                    renderItem={(item, index) => (
                      <List.Item>
                        <Space align="start">
                          <Badge count={index + 1} style={{ backgroundColor: '#ff4d4f' }} />
                          <ReactMarkdown>{item}</ReactMarkdown>
                        </Space>
                      </List.Item>
                    )}
                  />
                </TabPane>
              )}
              
              {(Array.isArray(activeInnovation.solutionApproaches) && activeInnovation.solutionApproaches.length > 0) && (
                <TabPane 
                  tab={<span><RocketOutlined />解决方案</span>} 
                  key="solutions"
                >
                  <List
                    itemLayout="horizontal"
                    dataSource={activeInnovation.solutionApproaches}
                    renderItem={(item, index) => (
                      <List.Item>
                        <Space align="start">
                          <Badge count={index + 1} style={{ backgroundColor: '#52c41a' }} />
                          <ReactMarkdown>{item}</ReactMarkdown>
                        </Space>
                      </List.Item>
                    )}
                  />
                </TabPane>
              )}
              
              <TabPane 
                tab={<span><NodeIndexOutlined />相关工作</span>} 
                key="related"
              >
                {Array.isArray(activeInnovation.relatedWork) && activeInnovation.relatedWork.length > 0 ? (
                  <List
                    size="small"
                    dataSource={activeInnovation.relatedWork}
                    renderItem={(work, index) => (
                      <List.Item>
                        <Text mark>[{index + 1}]</Text> <ReactMarkdown>{work}</ReactMarkdown>
                      </List.Item>
                    )}
                  />
                ) : (
                  <Alert
                    message="无相关工作信息"
                    description="当前创新点没有提供相关工作信息。"
                    type="info"
                    showIcon
                  />
                )}
              </TabPane>
            </Tabs>
          </div>
        )}
      </Modal>
      
      <style jsx="true">{`
        .innovation-generator {
          max-width: 1000px;
          margin: 0 auto;
        }
        
        .innovation-results {
          padding: 16px 0;
        }
        
        .results-header {
          margin-bottom: 24px;
        }
        
        .references {
          max-height: 300px;
          overflow-y: auto;
          padding: 0 16px;
          background-color: #f9f9f9;
          border-radius: 4px;
        }
      `}</style>
    </div>
  );
};

export default InnovationGenerator; 