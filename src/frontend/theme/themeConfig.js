// Ant Design主题配置
// 推荐系统学术研究智能体配色方案

// 基础色彩系统
const colors = {
  // 主色系
  primary: {
    light: '#e6f7ff',    // 浅蓝色
    main: '#1890ff',     // 蓝色
    dark: '#096dd9',     // 深蓝色
  },
  // 辅助色系
  secondary: {
    light: '#f6ffed',    // 浅绿色
    main: '#52c41a',     // 绿色
    dark: '#389e0d',     // 深绿色
  },
  // 强调色系
  accent: {
    light: '#f9f0ff',    // 浅紫色
    main: '#722ed1',     // 紫色
    dark: '#531dab',     // 深紫色
  },
  // 中性色系
  neutral: {
    white: '#ffffff',
    gray1: '#fafafa',
    gray2: '#f5f5f5',
    gray3: '#f0f0f0',
    gray4: '#d9d9d9',
    gray5: '#bfbfbf',
    gray6: '#8c8c8c',
    gray7: '#595959',
    gray8: '#434343',
    gray9: '#262626',
    black: '#000000',
  },
  // 功能色系
  functional: {
    success: {
      light: '#f6ffed',
      main: '#52c41a',
      dark: '#389e0d',
    },
    warning: {
      light: '#fffbe6',
      main: '#faad14',
      dark: '#d48806',
    },
    error: {
      light: '#fff1f0',
      main: '#ff4d4f',
      dark: '#cf1322',
    },
    info: {
      light: '#e6f7ff',
      main: '#1890ff',
      dark: '#096dd9',
    },
  },
};

// 可自定义的Ant Design主题配置
const themeConfig = {
  token: {
    colorPrimary: colors.primary.main,
    colorSuccess: colors.functional.success.main,
    colorWarning: colors.functional.warning.main,
    colorError: colors.functional.error.main,
    colorInfo: colors.functional.info.main,
    
    colorBgBase: colors.neutral.white,
    colorTextBase: colors.neutral.gray9,
    
    borderRadius: 4,
    wireframe: false,
    
    // 字体相关
    fontFamily: "'Nunito Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    fontSize: 14,
    
    // 尺寸与间距
    sizeStep: 4,
    sizeUnit: 4,
    
    // 动画
    motionUnit: 0.1,
    motionBase: 0,
    
    // 阴影
    boxShadowSecondary: '0 6px 16px -8px rgba(0, 0, 0, 0.08), 0 9px 28px 0 rgba(0, 0, 0, 0.05), 0 12px 48px 16px rgba(0, 0, 0, 0.03)',
    boxShadow: '0 1px 2px -2px rgba(0, 0, 0, 0.08), 0 3px 6px 0 rgba(0, 0, 0, 0.05), 0 5px 12px 4px rgba(0, 0, 0, 0.03)'
  },
  components: {
    Button: {
      primaryShadow: 'none',
      defaultShadow: 'none',
      defaultGhostBorderColor: colors.primary.main,
    },
    Card: {
      colorBgContainer: colors.neutral.white,
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
    },
    Layout: {
      colorBgHeader: colors.neutral.white,
      colorBgBody: colors.neutral.gray1,
      colorBgTrigger: colors.neutral.white,
    },
    Menu: {
      colorItemBgSelected: colors.primary.light,
      colorItemTextHover: colors.primary.main,
      colorItemTextSelected: colors.primary.main,
      colorItemBgHover: colors.neutral.gray1,
    },
    Table: {
      colorBgContainer: colors.neutral.white,
      headerBg: colors.neutral.gray2,
    },
    Input: {
      colorBgContainer: colors.neutral.white,
      activeBorderColor: colors.primary.main,
      hoverBorderColor: colors.primary.light,
    },
    Select: {
      colorBgElevated: colors.neutral.white,
      optionSelectedBg: colors.primary.light,
    },
    Tabs: {
      colorBgContainer: 'transparent',
      inkBarColor: colors.primary.main,
      cardGutter: 0,
    },
    Modal: {
      contentBg: colors.neutral.white,
      headerBg: colors.neutral.white,
      footerBg: colors.neutral.white,
    }
  },
};

// 导出颜色系统，便于在组件中直接使用
export const themeColors = colors;

export default themeConfig; 