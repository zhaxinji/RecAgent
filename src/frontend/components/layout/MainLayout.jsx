import React from 'react';
import { Layout } from 'antd';
import PropTypes from 'prop-types';

const { Content } = Layout;

const MainLayout = ({ children }) => {
  return (
    <Layout className="content-layout">
      <Content className="content-container">
        {children}
      </Content>
    </Layout>
  );
};

MainLayout.propTypes = {
  children: PropTypes.node.isRequired,
};

export default MainLayout; 