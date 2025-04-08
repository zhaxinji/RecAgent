#!/bin/bash

# 设置颜色变量
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_green() {
  echo -e "${GREEN}$1${NC}"
}

print_yellow() {
  echo -e "${YELLOW}$1${NC}"
}

print_red() {
  echo -e "${RED}$1${NC}"
}

print_green "=== 开始安装 AgentRec 系统 ==="

# 检查操作系统
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  print_yellow "检测到 Linux 系统"
elif [[ "$OSTYPE" == "darwin"* ]]; then
  print_yellow "检测到 macOS 系统"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  print_red "警告: 在 Windows 上运行需要 WSL 或 Docker 环境"
  print_yellow "推荐使用 Docker Compose 安装，或在 WSL 中继续执行此脚本"
  read -p "是否继续? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# 检查必要的工具
print_yellow "检查必要的工具..."
command -v python3 >/dev/null 2>&1 || { print_red "未找到 Python3，请先安装"; exit 1; }
command -v pip3 >/dev/null 2>&1 || { print_red "未找到 pip3，请先安装"; exit 1; }
command -v npm >/dev/null 2>&1 || { print_red "未找到 npm，请先安装 Node.js"; exit 1; }
command -v docker >/dev/null 2>&1 || { print_yellow "未找到 Docker，如果需要容器化部署请先安装"; }
command -v docker-compose >/dev/null 2>&1 || { print_yellow "未找到 Docker Compose，如果需要容器化部署请先安装"; }

# 创建环境变量文件
print_yellow "创建环境变量文件..."
if [ ! -f .env ]; then
  cp .env.example .env
  print_green "创建了 .env 文件，请根据需要修改其中的配置"
else
  print_yellow ".env 文件已存在，跳过"
fi

# 设置选择安装模式
print_yellow "请选择安装模式:"
echo "1) 开发模式 - 本地安装依赖"
echo "2) Docker 模式 - 使用 Docker Compose 部署"
read -p "请选择 [1-2]: " install_mode

if [ "$install_mode" = "1" ]; then
  # 开发模式安装
  print_yellow "开始开发模式安装..."
  
  # 安装后端依赖
  print_yellow "安装后端依赖..."
  cd src/api && pip3 install -r requirements.txt
  if [ $? -ne 0 ]; then
    print_red "安装后端依赖失败，请检查错误"
    exit 1
  fi
  cd ../..
  
  # 安装前端依赖
  print_yellow "安装前端依赖..."
  cd src/frontend && npm install
  if [ $? -ne 0 ]; then
    print_red "安装前端依赖失败，请检查错误"
    exit 1
  fi
  cd ../..
  
  # 创建必要的目录
  print_yellow "创建必要的目录..."
  mkdir -p uploads data/vector_db logs
  
  print_green "开发模式安装完成！"
  print_yellow "启动后端: cd src/api && uvicorn main:app --reload"
  print_yellow "启动前端: cd src/frontend && npm run dev"
  
elif [ "$install_mode" = "2" ]; then
  # Docker模式安装
  print_yellow "开始 Docker 模式安装..."
  
  # 检查 Docker 和 Docker Compose
  command -v docker >/dev/null 2>&1 || { print_red "未找到 Docker，请先安装"; exit 1; }
  command -v docker-compose >/dev/null 2>&1 || { print_red "未找到 Docker Compose，请先安装"; exit 1; }
  
  # 启动 Docker Compose
  print_yellow "启动 Docker Compose..."
  docker-compose up -d
  
  if [ $? -ne 0 ]; then
    print_red "Docker Compose 启动失败，请检查错误"
    exit 1
  fi
  
  print_green "Docker 模式安装完成！"
  print_yellow "应用已在后台启动"
  print_yellow "- 前端: http://localhost:3000"
  print_yellow "- API: http://localhost:8001/docs"
  
else
  print_red "无效的选择"
  exit 1
fi

print_green "=== AgentRec 系统安装完成 ==="
print_yellow "请确保已在 .env 文件中配置了正确的 OpenAI API 密钥和其他必要设置"
print_yellow "享受使用 AgentRec 进行研究和论文管理的便利！" 