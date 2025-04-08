import React from 'react';
import { Row, Col, Card, Typography } from 'antd';
import ResearchAssistant from '../components/research-assistant/ResearchAssistant';

const { Title } = Typography;

const AssistantPage = () => {
  return (
    <div>
      <Row gutter={[24, 24]}>
        <Col xs={24}>
          <Card className="card" style={{ minHeight: 'calc(100vh - 200px)' }}>
            <Title level={2}>推荐系统研究助手</Title>
            <ResearchAssistant />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AssistantPage; 