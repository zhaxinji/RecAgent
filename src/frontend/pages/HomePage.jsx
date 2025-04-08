import React from 'react';
import { Typography, Button, Row, Col, Card } from 'antd';
import { 
  RobotOutlined, 
  BookOutlined, 
  ExperimentOutlined, 
  FileTextOutlined,
  ArrowRightOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  LineChartOutlined,
  DatabaseOutlined,
  CodeOutlined,
  ApartmentOutlined
} from '@ant-design/icons';
import { Link } from 'react-router-dom';

// 导入样式
import '../styles/homepage.css';

const { Title, Paragraph, Text } = Typography;

const HomePage = () => {
  return (
    <div className="home-container">
      {/* 英雄区域 */}
      <section className="hero-section slide-up">
        <div className="hero-content-full">
          <div className="hero-badge">
            <ThunderboltOutlined /> 推荐系统领域专属智能体
          </div>
          <Title level={1} className="hero-title">
            提升学术研究效率的<br />智能协作平台
          </Title>
          <Paragraph className="hero-subtitle">
            RecAgent 融合大模型与专业知识，为推荐系统研究提供全流程支持，从文献调研、算法设计到实验分析和论文撰写，让研究更具洞察力与创新性。
          </Paragraph>
          <div className="hero-buttons">
            <Button type="primary" size="large">
            <Link to="/assistant">开始使用</Link>
            </Button>
            <Button size="large" className="btn-light">
            <Link to="/literature">探索功能</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* 主要特性区域 */}
      <section className="features-section">
        <div className="section-header">
          <div className="section-badge">
            <BulbOutlined /> 核心功能
          </div>
          <Title level={2} className="section-title">一站式推荐系统研究平台</Title>
          <Paragraph className="section-subtitle">
            覆盖研究全周期的智能辅助工具，简化流程，深化分析，提升研究质量
          </Paragraph>
        </div>

        <div className="feature-cards">
          <div className="feature-card" data-color="blue">
            <div className="feature-icon">
              <RobotOutlined />
            </div>
            <Title level={4} className="feature-title">文献智能管理</Title>
            <Paragraph className="feature-description">
              便捷的文献整理与管理系统，帮助构建个人学术资料库
            </Paragraph>
            <ul className="feature-list">
              <li><CheckCircleOutlined /> 学术数据库文献检索</li>
              <li><CheckCircleOutlined /> 本地论文深度解析</li>
              <li><CheckCircleOutlined /> 个人文献管理</li>
            </ul>
            <Link to="/literature" className="feature-link">
              了解更多 <ArrowRightOutlined />
            </Link>
          </div>

          <div className="feature-card" data-color="teal">
            <div className="feature-icon">
              <BookOutlined />
            </div>
            <Title level={4} className="feature-title">智能研究助手</Title>
            <Paragraph className="feature-description">
              专业知识问答系统，解决复杂技术问题，提供研究方法和算法指导
            </Paragraph>
            <ul className="feature-list">
              <li><CheckCircleOutlined /> 研究空白识别</li>
              <li><CheckCircleOutlined /> 创新点分析与专业概念解读</li>
              <li><CheckCircleOutlined /> 个性化实验设计</li>
            </ul>
            <Link to="/assistant" className="feature-link">
              了解更多 <ArrowRightOutlined />
            </Link>
          </div>

          <div className="feature-card" data-color="amber">
            <div className="feature-icon">
              <FileTextOutlined />
            </div>
            <Title level={4} className="feature-title">学术写作助手</Title>
            <Paragraph className="feature-description">
              提升论文质量的智能工具，辅助学术写作与格式规范
            </Paragraph>
            <ul className="feature-list">
              <li><CheckCircleOutlined /> 论文框架智能构建</li>
              <li><CheckCircleOutlined /> 不同标准学术论文撰写</li>
              <li><CheckCircleOutlined /> 个人写作论文管理</li>
            </ul>
            <Link to="/writing" className="feature-link">
              了解更多 <ArrowRightOutlined />
            </Link>
          </div>
        </div>
      </section>

      {/* 应用场景区域 */}
      <section className="scenarios-section">
        <div className="section-header">
          <div className="section-badge">
            <LineChartOutlined /> 应用场景
          </div>
          <Title level={2} className="section-title">解决研究实际痛点</Title>
          <Paragraph className="section-subtitle">
            从入门到精通，RecAgent为不同阶段的研究者提供精准支持
          </Paragraph>
        </div>

        <div className="scenarios-grid">
          <Card className="scenario-card">
            <Title level={4}>算法创新突破</Title>
            <Paragraph>
              分析方法原理和实现方式，探索改进空间，辅助构建研究模型，促进算法创新
            </Paragraph>
            <div className="scenario-tags">
              <span className="tag">模型架构</span>
              <span className="tag">性能瓶颈</span>
              <span className="tag">创新验证</span>
            </div>
          </Card>

          <Card className="scenario-card">
            <Title level={4}>高质量论文发表</Title>
            <Paragraph>
              优化论文结构与表达，规范学术格式，完善实验分析，提高研究成果的表达质量
            </Paragraph>
            <div className="scenario-tags">
              <span className="tag">论文结构</span>
              <span className="tag">表达精炼</span>
              <span className="tag">投稿指导</span>
            </div>
          </Card>

          <Card className="scenario-card">
            <Title level={4}>研究方向探索</Title>
            <Paragraph>
              帮助整理研究文献资料，便于识别研究热点，提供方向参考，辅助研究选题
            </Paragraph>
            <div className="scenario-tags">
              <span className="tag">多源检索</span>
              <span className="tag">文献整理</span>
              <span className="tag">方向评估</span>
            </div>
          </Card>

          <Card className="scenario-card">
            <Title level={4}>实验效率提升</Title>
            <Paragraph>
              简化实验设计和参数配置流程，提供结果可视化与分析，帮助优化实验过程
            </Paragraph>
            <div className="scenario-tags">
              <span className="tag">流程优化</span>
              <span className="tag">参数设置</span>
              <span className="tag">结果分析</span>
            </div>
          </Card>
        </div>
      </section>

      {/* 功能亮点区域 */}
      <section className="highlights-section">
        <div className="section-header">
          <Title level={2} className="section-title">领先技术驱动的研究体验</Title>
        </div>

        <div className="highlights-grid">
          <div className="highlight-item">
            <div className="highlight-icon"><ApartmentOutlined /></div>
            <div className="highlight-content">
              <Title level={4}>动态知识图谱</Title>
              <Paragraph>学术文献管理工具，帮助整理研究文献关系，方便查找和管理关键文献资料</Paragraph>
            </div>
          </div>
          
          <div className="highlight-item">
            <div className="highlight-icon"><RobotOutlined /></div>
            <div className="highlight-content">
              <Title level={4}>领域专家模型</Title>
              <Paragraph>针对推荐系统研究的智能问答系统，理解专业术语与概念，提供研究参考</Paragraph>
            </div>
          </div>
          
          <div className="highlight-item">
            <div className="highlight-icon"><CodeOutlined /></div>
            <div className="highlight-content">
              <Title level={4}>实验管理工具</Title>
              <Paragraph>支持实验参数配置与管理的工具，帮助设计和记录实验流程，保障实验的可复现性</Paragraph>
            </div>
          </div>
          
          <div className="highlight-item">
            <div className="highlight-icon"><DatabaseOutlined /></div>
            <div className="highlight-content">
              <Title level={4}>研究资源库</Title>
              <Paragraph>整合学术写作和研究资料的知识库，提供参考资源，辅助学术写作与研究</Paragraph>
            </div>
          </div>
        </div>
      </section>

      {/* CTA区域 */}
      <section className="cta-section">
        <div className="cta-content">
          <Title level={2} className="cta-title">开启智能研究新时代</Title>
          <Paragraph className="cta-subtitle">
            加入RecAgent，让您的推荐系统研究更高效、更创新、更有影响力
          </Paragraph>
          <Button type="primary" size="large">
            <Link to="/register">免费注册体验</Link>
          </Button>
          <div className="cta-more">
            <Text>已有账号？</Text> <Link to="/login">直接登录</Link>
          </div>
        </div>
      </section>
    </div>
  );
};

export default HomePage; 