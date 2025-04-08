# 贡献指南

感谢您对RecAgent项目的关注！我们欢迎各种形式的贡献，无论是功能改进、bug修复、文档完善，还是使用反馈。本指南将帮助您了解如何参与项目开发。

## 开发环境设置

1. 克隆仓库
```bash
git clone https://github.com/yourusername/agent_rec.git
cd agent_rec
```

2. 创建并激活虚拟环境
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/MacOS
source venv/bin/activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖
```

4. 设置环境变量
复制`.env.example`文件为`.env`并根据需要修改配置。

5. 准备数据库
```bash
alembic upgrade head
```

## 开发工作流

### 创建分支

所有开发工作都应在独立的分支上进行：

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

分支命名规范：
- `feature/` - 新功能
- `fix/` - 错误修复
- `docs/` - 文档更新
- `refactor/` - 代码重构
- `test/` - 测试相关

### 代码风格

我们使用以下工具确保代码质量：

- `black` - 代码格式化
- `isort` - 导入顺序
- `flake8` - 代码风格检查
- `mypy` - 类型检查

在提交代码前，请运行：

```bash
# 格式化代码
black .
isort .

# 检查代码质量
flake8
mypy
```

### 提交规范

提交信息应遵循以下格式：

```
<类型>(<范围>): <简短描述>

<可选的详细描述>

<可选的注释>
```

类型包括：
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档变更
- `style`: 代码风格变更（不影响代码功能）
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具变更

示例：
```
feat(auth): 添加新的OAuth登录方式

实现了GitHub OAuth2登录功能，包括：
- OAuth回调处理
- 用户信息获取
- 账号关联逻辑

Closes #123
```

### 测试

添加新功能或修复bug时，请确保包含相应的测试：

```bash
# 运行测试
pytest

# 带覆盖率报告
pytest --cov=agent_rec
```

## 提交Pull Request

1. 推送您的分支到GitHub
```bash
git push origin your-branch-name
```

2. 在GitHub上创建Pull Request，详细描述您的更改
3. 等待代码审核
4. 根据审核意见修改代码（如需要）
5. 合并PR

## 问题报告

如果您发现bug或有功能建议，请通过GitHub Issues提交：

1. 查看现有issues，确保没有重复
2. 使用issue模板填写详细信息
3. 提供可复现的步骤或详细描述

## 文档贡献

文档改进是非常重要的贡献：

- 修复拼写或语法错误
- 改进现有文档的清晰度
- 添加缺失的文档
- 提供示例和教程

## 行为准则

请保持尊重和专业，尊重所有项目参与者。我们致力于创建一个开放、包容的社区。

## 许可

通过贡献代码，您同意您的贡献将在项目的[MIT许可证](LICENSE)下发布。

## 项目结构

```
agent_rec/
├── docker/                 # Docker 配置文件
├── scripts/                # 部署和维护脚本
├── src/                    # 源代码
│   ├── api/                # 后端 API 服务
│   │   ├── database/       # 数据库模型和连接
│   │   ├── models/         # Pydantic 模型
│   │   ├── routers/        # API 路由
│   │   ├── services/       # 业务逻辑服务
│   │   ├── utils/          # 工具函数
│   │   └── main.py         # 应用入口
│   └── frontend/           # 前端 React 应用
│       ├── components/     # React 组件
│       ├── hooks/          # 自定义 React hooks
│       ├── pages/          # 页面组件
│       ├── services/       # API 客户端
│       └── main.jsx        # 前端入口
├── data/                   # 数据存储（向量数据库等）
├── uploads/                # 用户上传文件存储
├── .env.example            # 环境变量示例
├── docker-compose.yml      # Docker Compose 配置
└── README.md               # 项目说明
```

## 代码风格

- **Python 代码**：遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 规范
- **JavaScript/React 代码**：遵循 [Airbnb JavaScript 风格指南](https://github.com/airbnb/javascript)
- 使用 4 个空格缩进
- 使用有意义的变量名和函数名
- 添加适当的注释解释复杂逻辑

## 分支策略

- `main`：稳定分支，只接受经过审核的合并请求
- `dev`：开发分支，新功能首先合并到这里
- 功能分支：从 `dev` 分支创建，命名为 `feature/[功能名称]`
- 修复分支：从 `main` 或 `dev` 分支创建，命名为 `fix/[问题描述]`

## 联系我们

如果您有任何问题或需要帮助，请通过以下方式联系我们：

- 创建 GitHub Issue
- 发送邮件至 [your-email@example.com](mailto:your-email@example.com)

感谢您的贡献！ 