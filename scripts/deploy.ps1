# AgentRec 系统部署脚本 (PowerShell版本)

# 设置颜色函数
function Write-Green {
    param([string]$text)
    Write-Host $text -ForegroundColor Green
}

function Write-Yellow {
    param([string]$text)
    Write-Host $text -ForegroundColor Yellow
}

function Write-Red {
    param([string]$text)
    Write-Host $text -ForegroundColor Red
}

Write-Green "=== 开始部署 AgentRec 系统 ==="

# 检查必要的工具
Write-Yellow "检查必要的工具..."
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Red "未找到 Docker，请先安装"
    exit 1
}
if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Red "未找到 Docker Compose，请先安装"
    exit 1
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Red "未找到 Git，请先安装"
    exit 1
}

# 检查是否在项目根目录
if (-not (Test-Path "docker-compose.yml")) {
    Write-Red "错误: 当前目录下未找到 docker-compose.yml 文件"
    Write-Yellow "请确保你在项目根目录下执行此脚本"
    exit 1
}

# 检查环境变量文件
if (-not (Test-Path ".env")) {
    Write-Yellow "环境变量文件 .env 不存在，从示例文件创建..."
    Copy-Item .env.example .env
    Write-Yellow "请编辑 .env 文件，设置正确的环境变量，尤其是 OpenAI API 密钥"
    exit 1
}

# 询问是否要备份数据
$backupData = Read-Host "是否要在部署前备份数据? (y/n)"
if ($backupData -eq "y") {
    Write-Yellow "开始备份数据..."
    $backupDir = "backups\$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    New-Item -Path $backupDir -ItemType Directory -Force | Out-Null
    
    # 备份数据库
    $dbRunning = docker-compose ps | Select-String -Pattern "db"
    if ($dbRunning) {
        Write-Yellow "备份 PostgreSQL 数据库..."
        docker-compose exec -T db pg_dumpall -c -U postgres > "$backupDir\database_backup.sql"
        if ($?) {
            Write-Green "数据库备份成功: $backupDir\database_backup.sql"
        } else {
            Write-Red "数据库备份失败"
        }
    }
    
    # 备份上传的文件
    if (Test-Path "uploads") {
        Write-Yellow "备份上传的文件..."
        Copy-Item -Path "uploads" -Destination "$backupDir\uploads" -Recurse
        Write-Green "文件备份成功: $backupDir\uploads"
    }
    
    # 备份向量数据库
    if (Test-Path "data\vector_db") {
        Write-Yellow "备份向量数据库..."
        Copy-Item -Path "data\vector_db" -Destination "$backupDir\vector_db" -Recurse
        Write-Green "向量数据库备份成功: $backupDir\vector_db"
    }
    
    Write-Green "备份完成: $backupDir"
}

# 询问是否拉取最新代码
$pullCode = Read-Host "是否拉取最新代码? (y/n)"
if ($pullCode -eq "y") {
    Write-Yellow "拉取最新代码..."
    git pull
    if (-not $?) {
        Write-Red "拉取代码失败，请解决冲突后重试"
        exit 1
    }
    Write-Green "代码更新成功"
}

# 询问是否要重建容器
$rebuildContainers = Read-Host "是否重建所有容器? (y/n)"
if ($rebuildContainers -eq "y") {
    Write-Yellow "停止并移除现有容器..."
    docker-compose down
    
    Write-Yellow "构建新的容器..."
    docker-compose build
    
    Write-Yellow "启动新的容器..."
    docker-compose up -d
} else {
    Write-Yellow "仅重启现有容器..."
    docker-compose restart
}

# 检查容器状态
Write-Yellow "检查容器状态..."
docker-compose ps

# 运行数据库迁移
$runMigration = Read-Host "是否运行数据库迁移? (y/n)"
if ($runMigration -eq "y") {
    Write-Yellow "运行数据库迁移..."
    docker-compose exec api python -m src.api.database.init_db
    if ($?) {
        Write-Green "数据库迁移成功"
    } else {
        Write-Red "数据库迁移失败"
    }
}

Write-Green "=== AgentRec 系统部署完成 ==="
Write-Yellow "应用访问地址:"
Write-Yellow "- 前端: http://localhost:3000"
Write-Yellow "- API文档: http://localhost:8001/docs"
Write-Yellow "- 健康检查: http://localhost:8001/health"

# 显示日志
$viewLogs = Read-Host "是否查看日志? (y/n)"
if ($viewLogs -eq "y") {
    docker-compose logs -f
} 