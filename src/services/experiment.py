from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
import uuid
import json
import os
import subprocess
import tempfile
import asyncio
from datetime import datetime
import logging
from pathlib import Path

from src.models.experiment import Experiment, ExperimentStatus, ExperimentResult
from src.models.paper import Paper
from src.core.config import settings
from src.services import ai_assistant

logger = logging.getLogger(__name__)

# 支持的编程语言和框架
SUPPORTED_LANGUAGES = ["python", "r", "julia"]
SUPPORTED_FRAMEWORKS = {
    "python": ["pytorch", "tensorflow", "sklearn", "pandas"],
    "r": ["tidyverse", "caret", "mlr"],
    "julia": ["flux", "sciml"]
}

def get_experiment_by_id(db: Session, experiment_id: str, user_id: Optional[str] = None) -> Optional[Experiment]:
    """通过ID获取实验"""
    query = db.query(Experiment).filter(Experiment.id == experiment_id)
    if user_id:
        query = query.filter(Experiment.owner_id == user_id)
    return query.first()

def get_experiments(
    db: Session, 
    user_id: str, 
    paper_id: Optional[str] = None,
    status: Optional[ExperimentStatus] = None,
    skip: int = 0, 
    limit: int = 100,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> List[Experiment]:
    """获取用户的实验列表"""
    query = db.query(Experiment).filter(Experiment.owner_id == user_id)
    
    if paper_id:
        query = query.filter(Experiment.paper_id == paper_id)
    
    if status:
        query = query.filter(Experiment.status == status)
    
    # 排序
    if sort_order.lower() == "desc":
        query = query.order_by(desc(getattr(Experiment, sort_by)))
    else:
        query = query.order_by(asc(getattr(Experiment, sort_by)))
    
    return query.offset(skip).limit(limit).all()

def create_experiment(
    db: Session, 
    user_id: str,
    name: str,
    description: str,
    code: str,
    paper_id: Optional[str] = None,
    status: ExperimentStatus = ExperimentStatus.DRAFT,
    metadata: Optional[Dict[str, Any]] = None
) -> Experiment:
    """创建新实验"""
    experiment = Experiment(
        id=str(uuid.uuid4()),
        owner_id=user_id,
        paper_id=paper_id,
        title=name,
        description=description,
        code=code,
        status=status,
        parameters=metadata or {}
    )
    
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return experiment

def update_experiment(
    db: Session, 
    experiment_id: str, 
    user_id: str, 
    update_data: Dict[str, Any]
) -> Optional[Experiment]:
    """更新实验信息"""
    experiment = get_experiment_by_id(db, experiment_id, user_id)
    if not experiment:
        return None
    
    # 更新字段
    for key, value in update_data.items():
        if hasattr(experiment, key):
            setattr(experiment, key, value)
    
    db.commit()
    db.refresh(experiment)
    return experiment

def delete_experiment(db: Session, experiment_id: str, user_id: str) -> bool:
    """删除实验"""
    experiment = get_experiment_by_id(db, experiment_id, user_id)
    if not experiment:
        return False
    
    db.delete(experiment)
    db.commit()
    return True

async def run_experiment(db: Session, experiment_id: str, user_id: str) -> Dict[str, Any]:
    """运行实验并返回结果"""
    experiment = get_experiment_by_id(db, experiment_id, user_id)
    if not experiment:
        raise ValueError("实验未找到或无权访问")
    
    # 更新实验状态为运行中
    update_experiment(
        db=db,
        experiment_id=experiment_id,
        user_id=user_id,
        update_data={"status": ExperimentStatus.RUNNING}
    )
    
    try:
        # 创建临时文件保存代码
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False) as f:
            f.write(experiment.code)
            temp_file = f.name
        
        # 准备执行命令
        cmd = ["python", temp_file]
        
        # 执行代码
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # 获取输出
        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""
        
        # 创建实验结果
        result = ExperimentResult(
            id=str(uuid.uuid4()),
            experiment_id=experiment.id,
            stdout=stdout_text,
            stderr=stderr_text,
            output=stdout_text,  # 同时设置output字段
            status="success" if process.returncode == 0 else "error",
            error=stderr_text if process.returncode != 0 else None,
            exit_code=process.returncode,
            execution_time=None,  # 可以添加实际执行时间
            created_at=datetime.now()
        )
        
        db.add(result)
        
        # 更新实验状态
        if process.returncode == 0:
            status = ExperimentStatus.COMPLETED
        else:
            status = ExperimentStatus.FAILED
        
        experiment = update_experiment(
            db=db,
            experiment_id=experiment_id,
            user_id=user_id,
            update_data={
                "status": status,
                "last_run_at": datetime.now()
            }
        )
        
        db.commit()
        
        # 删除临时文件
        os.unlink(temp_file)
        
        return {
            "experiment_id": experiment.id,
            "status": status.value,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "output": result.output,
            "exit_code": result.exit_code
        }
        
    except Exception as e:
        # 更新实验状态为失败
        update_experiment(
            db=db,
            experiment_id=experiment_id,
            user_id=user_id,
            update_data={
                "status": ExperimentStatus.FAILED,
                "last_run_at": datetime.now()
            }
        )
        
        db.commit()
        
        # 尝试删除临时文件
        try:
            if 'temp_file' in locals():
                os.unlink(temp_file)
        except:
            pass
        
        raise Exception(f"运行实验失败: {str(e)}")

def get_experiment_results(db: Session, experiment_id: str, user_id: str) -> List[ExperimentResult]:
    """获取实验的所有运行结果"""
    experiment = get_experiment_by_id(db, experiment_id, user_id)
    if not experiment:
        return []
    
    return db.query(ExperimentResult).filter(
        ExperimentResult.experiment_id == experiment_id
    ).order_by(desc(ExperimentResult.created_at)).all()

def get_latest_experiment_result(db: Session, experiment_id: str, user_id: str) -> Optional[ExperimentResult]:
    """获取实验的最新运行结果"""
    experiment = get_experiment_by_id(db, experiment_id, user_id)
    if not experiment:
        return None
    
    return db.query(ExperimentResult).filter(
        ExperimentResult.experiment_id == experiment_id
    ).order_by(desc(ExperimentResult.created_at)).first()

def create_experiment_result(
    db: Session,
    experiment_id: str,
    user_id: str,
    output: str,
    status: str,
    metrics: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
) -> ExperimentResult:
    """
    创建实验结果
    """
    experiment = get_experiment_by_id(db, experiment_id, user_id)
    if not experiment:
        raise ValueError(f"实验 {experiment_id} 不存在")
    
    result = ExperimentResult(
        id=str(uuid.uuid4()),
        experiment_id=experiment_id,
        output=output,
        status=status,
        metrics=metrics or {},
        error=error
    )
    
    db.add(result)
    
    # 更新实验状态
    if status == "success":
        experiment.status = ExperimentStatus.COMPLETED
    elif status == "error":
        experiment.status = ExperimentStatus.FAILED
    else:
        experiment.status = ExperimentStatus.DRAFT
    
    experiment.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(result)
    
    return result

async def analyze_experiment_code(
    code: str,
    language: str,
    framework: str = ""
) -> Dict[str, Any]:
    """
    分析实验代码的有效性和潜在问题
    """
    try:
        # 对于Python，使用ast模块进行简单语法检查
        if language == "python":
            import ast
            try:
                ast.parse(code)
                return {
                    "has_errors": False,
                    "message": "代码语法检查通过"
                }
            except SyntaxError as e:
                return {
                    "has_errors": True,
                    "message": f"Python语法错误: {str(e)}"
                }
        
        # 其他语言暂不支持详细语法检查
        return {
            "has_errors": False,
            "message": f"无法对{language}代码进行详细语法检查"
        }
    except Exception as e:
        return {
            "has_errors": True,
            "message": f"代码分析失败: {str(e)}"
        }

async def execute_code(
    file_path: str,
    language: str
) -> Dict[str, Any]:
    """
    执行代码文件
    """
    commands = {
        "python": ["python", file_path],
        "r": ["Rscript", file_path],
        "julia": ["julia", file_path]
    }
    
    if language not in commands:
        raise ValueError(f"不支持的编程语言: {language}")
    
    command = commands[language]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            "returncode": process.returncode,
            "stdout": stdout.decode('utf-8', errors='replace'),
            "stderr": stderr.decode('utf-8', errors='replace')
        }
    except Exception as e:
        logger.error(f"执行代码失败: {str(e)}")
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(e)
        }

def parse_metrics_from_output(output: str) -> Dict[str, Any]:
    """
    从输出中解析实验指标
    """
    metrics = {}
    
    # 尝试查找JSON格式的指标
    try:
        import re
        json_pattern = r'METRICS_JSON:(.*?)\n'
        match = re.search(json_pattern, output)
        if match:
            metrics_json = match.group(1).strip()
            metrics = json.loads(metrics_json)
            return metrics
    except:
        pass
    
    # 尝试查找键值对格式的指标
    try:
        import re
        metric_pattern = r'METRIC\s+([a-zA-Z0-9_]+):\s*([\d\.]+)'
        matches = re.findall(metric_pattern, output)
        for key, value in matches:
            try:
                metrics[key] = float(value)
            except:
                metrics[key] = value
    except:
        pass
    
    return metrics

async def generate_experiment_template(
    db: Session,
    user_id: str,
    paper_id: Optional[str] = None,
    template_type: str = "basic",
    language: str = "python",
    framework: str = "pytorch"
) -> str:
    """
    生成实验模板代码
    """
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"不支持的编程语言: {language}")
    
    if framework and framework not in SUPPORTED_FRAMEWORKS.get(language, []):
        raise ValueError(f"不支持的框架 {framework} 用于 {language}")
    
    template_code = ""
    
    if template_type == "basic":
        if language == "python":
            if framework == "pytorch":
                template_code = """
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import matplotlib.pyplot as plt

# 设置随机种子，确保结果可复现
torch.manual_seed(42)
np.random.seed(42)

# 生成模拟数据
def generate_data(n_samples=1000):
    X = np.random.randn(n_samples, 10)
    w = np.random.randn(10, 1)
    y = X.dot(w) + 0.1 * np.random.randn(n_samples, 1)
    return X, y

# 数据准备
X, y = generate_data()
X_tensor = torch.FloatTensor(X)
y_tensor = torch.FloatTensor(y)

# 划分训练集和测试集
train_size = int(0.8 * len(X))
X_train, X_test = X_tensor[:train_size], X_tensor[train_size:]
y_train, y_test = y_tensor[:train_size], y_tensor[train_size:]

# 定义模型
class LinearRegression(nn.Module):
    def __init__(self, input_dim):
        super(LinearRegression, self).__init__()
        self.linear = nn.Linear(input_dim, 1)
        
    def forward(self, x):
        return self.linear(x)

# 初始化模型
model = LinearRegression(X.shape[1])
criterion = nn.MSELoss()
optimizer = optim.SGD(model.parameters(), lr=0.01)

# 训练模型
n_epochs = 100
losses = []

for epoch in range(n_epochs):
    # 前向传播
    outputs = model(X_train)
    loss = criterion(outputs, y_train)
    losses.append(loss.item())
    
    # 反向传播和优化
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    
    if (epoch+1) % 10 == 0:
        print(f'Epoch [{epoch+1}/{n_epochs}], Loss: {loss.item():.4f}')

# 评估模型
with torch.no_grad():
    model.eval()
    y_pred = model(X_test)
    test_loss = criterion(y_pred, y_test)
    print(f'Test Loss: {test_loss.item():.4f}')

# 可视化结果
plt.figure(figsize=(10, 6))
plt.plot(range(n_epochs), losses)
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.title('Training Loss Over Time')
plt.grid(True)
plt.savefig('loss_curve.png')

# 输出指标
rmse = np.sqrt(test_loss.item())
print(f'METRIC rmse: {rmse:.6f}')

print('METRICS_JSON:{"rmse": ' + str(rmse) + ', "final_train_loss": ' + str(losses[-1]) + '}')
"""
            elif framework == "tensorflow":
                template_code = """
import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt

# 设置随机种子，确保结果可复现
tf.random.set_seed(42)
np.random.seed(42)

# 生成模拟数据
def generate_data(n_samples=1000):
    X = np.random.randn(n_samples, 10)
    w = np.random.randn(10, 1)
    y = X.dot(w) + 0.1 * np.random.randn(n_samples, 1)
    return X, y

# 数据准备
X, y = generate_data()

# 划分训练集和测试集
train_size = int(0.8 * len(X))
X_train, X_test = X[:train_size], X[train_size:]
y_train, y_test = y[:train_size], y[train_size:]

# 定义模型
model = tf.keras.Sequential([
    tf.keras.layers.Dense(1, input_shape=(10,))
])

# 编译模型
model.compile(optimizer='sgd', loss='mse')

# 训练模型
history = model.fit(
    X_train, y_train,
    epochs=100,
    verbose=1,
    validation_data=(X_test, y_test)
)

# 评估模型
test_loss = model.evaluate(X_test, y_test, verbose=0)
print(f'Test Loss: {test_loss:.4f}')

# 可视化训练过程
plt.figure(figsize=(10, 6))
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('Model Loss')
plt.ylabel('Loss')
plt.xlabel('Epoch')
plt.legend(['Train', 'Validation'], loc='upper right')
plt.grid(True)
plt.savefig('loss_curve.png')

# 输出指标
rmse = np.sqrt(test_loss)
print(f'METRIC rmse: {rmse:.6f}')

print('METRICS_JSON:{"rmse": ' + str(rmse) + ', "final_train_loss": ' + str(history.history['loss'][-1]) + '}')
"""
            elif framework == "sklearn":
                template_code = """
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt

# 设置随机种子，确保结果可复现
np.random.seed(42)

# 生成模拟数据
def generate_data(n_samples=1000):
    X = np.random.randn(n_samples, 10)
    w = np.random.randn(10, 1)
    y = X.dot(w) + 0.1 * np.random.randn(n_samples, 1)
    return X, y.ravel()

# 数据准备
X, y = generate_data()

# 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 训练模型
model = LinearRegression()
model.fit(X_train, y_train)

# 评估模型
y_pred = model.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
r2 = r2_score(y_test, y_pred)

print(f'均方误差 (MSE): {mse:.4f}')
print(f'均方根误差 (RMSE): {rmse:.4f}')
print(f'决定系数 (R^2): {r2:.4f}')

# 可视化预测结果
plt.figure(figsize=(10, 6))
plt.scatter(y_test, y_pred, alpha=0.5)
plt.plot([y.min(), y.max()], [y.min(), y.max()], 'k--', lw=2)
plt.xlabel('实际值')
plt.ylabel('预测值')
plt.title('预测值 vs 实际值')
plt.grid(True)
plt.savefig('prediction_vs_actual.png')

# 输出指标
print(f'METRIC rmse: {rmse:.6f}')
print(f'METRIC r2: {r2:.6f}')

print('METRICS_JSON:{"rmse": ' + str(rmse) + ', "r2": ' + str(r2) + '}')
"""
    
    if not template_code and paper_id:
        # 如果指定了论文，可以尝试从论文内容生成相关代码
        paper = db.query(Paper).filter(Paper.id == paper_id, Paper.owner_id == user_id).first()
        if paper and paper.content:
            template_code = await ai_assistant.generate_code_from_paper(
                paper.content,
                language,
                framework
            )
    
    if not template_code:
        template_code = f"# {language.upper()} 实验模板\n\n# 在此编写您的{language}代码\n"
        
    return template_code 

async def generate_experiment_design(
    domain: str,
    dataset_type: str,
    metric_type: str,
    method_description: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    生成实验设计方案
    
    Args:
        domain: 研究领域
        dataset_type: 数据集类型
        metric_type: 评估指标类型
        method_description: 方法描述或特殊需求
        user_id: 用户ID
        
    Returns:
        实验设计方案
    """
    logging.info(f"为用户 {user_id} 生成实验设计方案，领域: {domain}, 数据集类型: {dataset_type}, 评估指标: {metric_type}")
    
    # 默认设计结果
    design_result = {}
    
    # 序列推荐领域
    if domain == "sequential":
        design_result = {
            "domain": "序列推荐",
            "experimentTitle": "基于多粒度时间动态的序列推荐方法实验评估",
            "overview": "本实验旨在全面评估提出的多粒度时间动态序列推荐方法在多个公开数据集上的性能，并通过与最新基线方法的对比和详细的消融实验，验证方法的有效性和各组件的贡献。",
            "datasets": [
                {
                    "name": "Amazon Electronics",
                    "type": "电子商务序列数据",
                    "size": "用户-物品交互 1,689,188条，用户数 192,403，物品数 63,001",
                    "features": "时间戳、物品类别、物品属性、评分、评论文本",
                    "source": "Amazon Review Dataset",
                    "preprocessing": "筛选至少5次交互的用户，按时间戳排序构建序列，80%训练/10%验证/10%测试"
                },
                {
                    "name": "MovieLens-1M",
                    "type": "电影评分序列数据",
                    "size": "用户-电影评分 1,000,209条，用户数 6,040，电影数 3,706",
                    "features": "时间戳、电影类别、用户人口统计学特征、评分",
                    "source": "GroupLens Research",
                    "preprocessing": "按时间戳排序构建序列，使用滑动窗口生成训练样本，最后一次交互作为测试"
                },
                {
                    "name": "Taobao User Behavior",
                    "type": "电商行为序列数据",
                    "size": "用户-物品交互 100,150,807条，用户数 987,994，物品数 4,162,024",
                    "features": "用户ID、物品ID、物品类别、行为类型、时间戳",
                    "source": "Alibaba",
                    "preprocessing": "按用户和时间戳构建行为序列，使用前80%序列训练，后20%测试"
                }
            ],
            "baselines": [
                {
                    "name": "GRU4Rec",
                    "description": "基于GRU的序列推荐模型，能够捕获用户行为的顺序信息",
                    "reference": "Hidasi et al. 2016, Session-based Recommendations with Recurrent Neural Networks"
                },
                {
                    "name": "SASRec",
                    "description": "基于自注意力机制的序列推荐模型，能够捕获长距离依赖",
                    "reference": "Kang et al. 2018, Self-Attentive Sequential Recommendation"
                },
                {
                    "name": "BERT4Rec",
                    "description": "基于双向Transformer的序列推荐模型，利用掩码机制进行预训练",
                    "reference": "Sun et al. 2019, BERT4Rec: Sequential Recommendation with Bidirectional Encoder Representations"
                },
                {
                    "name": "TiSASRec",
                    "description": "时间感知的自注意力序列推荐模型，利用时间间隔信息增强模型表达",
                    "reference": "Li et al. 2020, Time Interval Aware Self-Attention for Sequential Recommendation"
                },
                {
                    "name": "DuoRec",
                    "description": "基于对比学习的序列推荐模型，同时学习序列和物品表示",
                    "reference": "Qiu et al. 2022, Contrastive Learning for Representation Degeneration Problem in Sequential Recommendation"
                }
            ],
            "metrics": [
                {
                    "name": "HR@K",
                    "description": "评估推荐列表中包含目标物品的比例",
                    "implementation": "K值分别设为5、10、20"
                },
                {
                    "name": "NDCG@K",
                    "description": "评估推荐物品的排序质量，考虑位置因素",
                    "implementation": "K值分别设为5、10、20"
                },
                {
                    "name": "MRR",
                    "description": "平均倒数排名，评估目标物品在推荐列表中的平均位置",
                    "implementation": "计算整个测试集的MRR均值"
                }
            ],
            "experimentSetup": {
                "trainTestSplit": "根据时间顺序，使用前80%数据训练，中间10%验证，最后10%测试",
                "evaluationStrategy": "对每个用户的测试集交互，预测下一个物品，计算Top-K指标",
                "hyperparameterTuning": "使用网格搜索优化嵌入维度、学习率、注意力头数等关键参数",
                "infrastructure": "使用PyTorch框架在NVIDIA V100 GPU上训练",
                "reproductionSettings": "固定随机种子为42，报告5次运行的平均结果和标准差"
            },
            "implementationDetails": {
                "framework": "PyTorch 1.10+",
                "batchSize": 128,
                "optimizer": "Adam优化器，学习率1e-3，权重衰减1e-5",
                "epochs": "最多100轮，使用早停策略，验证集性能5轮无提升则停止",
                "embeddings": "使用维度为128的嵌入层表示用户和物品",
                "regularization": "使用Dropout(0.2)防止过拟合"
            },
            "analysisPlans": [
                "主实验：将提出的方法与所有基线在三个数据集上进行全面对比",
                "消融实验：分析移除多粒度时间建模、自注意力机制和对比学习组件的影响",
                "超参数敏感性分析：探讨嵌入维度、注意力头数和时间粒度设置的影响",
                "效率分析：比较各方法的训练时间和推理时间",
                "可视化分析：展示不同时间粒度下用户兴趣的变化模式"
            ],
            "limitations": [
                "只考虑物品ID和时间信息，未充分利用物品属性和内容特征",
                "未考虑多种行为类型的差异性和关联性",
                "训练复杂度随序列长度增加而快速增长，在超长序列场景下可能面临计算挑战",
                "离线评估可能无法完全反映在线推荐性能"
            ]
        }
    
    # 图神经网络推荐领域
    elif domain == "graph":
        design_result = {
            "domain": "图神经网络推荐",
            "experimentTitle": "基于异构图神经网络的多关系推荐系统实验研究",
            "overview": "本实验设计针对基于异构图神经网络的推荐方法，通过构建包含多种节点类型和边关系的知识图谱，利用图神经网络捕获复杂的交互模式，实现更精准的推荐。实验将在多个公开数据集上进行全面评估，与最新图推荐方法进行对比，并通过消融实验验证各组件的有效性。",
            "datasets": [
                {
                    "name": "Amazon Book",
                    "type": "电商评价数据集",
                    "size": "用户-物品交互 22,507,155条，用户数 8,026,324，物品数 2,330,066",
                    "features": "评分、评论文本、物品元数据（类别、品牌、价格等）",
                    "source": "Amazon Review Dataset",
                    "preprocessing": "抽取评分≥4的交互作为正样本，构建用户-物品二部图，80%训练/10%验证/10%测试"
                },
                {
                    "name": "Yelp2022",
                    "type": "商户评价数据集",
                    "size": "用户-商户评价 6,990,280条，用户数 2,189,457，商户数 160,585",
                    "features": "评分、评论文本、商户类别、属性、地理位置",
                    "source": "Yelp Dataset Challenge",
                    "preprocessing": "转换为隐式反馈，构建用户-商户-类别-城市异构图"
                },
                {
                    "name": "MovieLens+IMDB",
                    "type": "电影推荐数据集",
                    "size": "MovieLens-20M评分+IMDB元数据，用户数 138,493，电影数 27,278",
                    "features": "评分、标签、电影详情（导演、演员、类别、剧情、年份等）",
                    "source": "GroupLens Research + IMDB API",
                    "preprocessing": "整合IMDB元数据，构建电影-演员-导演-类别知识图谱"
                }
            ],
            "baselines": [
                {
                    "name": "NGCF",
                    "description": "神经图协同过滤，利用图神经网络对用户-项目二部图进行消息传递",
                    "reference": "Wang et al. 2019, Neural Graph Collaborative Filtering"
                },
                {
                    "name": "LightGCN",
                    "description": "轻量级图卷积网络，简化了NGCF中的特征变换和非线性激活",
                    "reference": "He et al. 2020, LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation"
                },
                {
                    "name": "KGAT",
                    "description": "知识图谱注意力网络，结合知识图谱和注意力机制的推荐模型",
                    "reference": "Wang et al. 2019, KGAT: Knowledge Graph Attention Network for Recommendation"
                },
                {
                    "name": "HAN",
                    "description": "异构图注意力网络，设计了节点级和语义级注意力",
                    "reference": "Wang et al. 2019, Heterogeneous Graph Attention Network"
                },
                {
                    "name": "RGCN",
                    "description": "关系图卷积网络，为不同类型的边设计不同的权重矩阵",
                    "reference": "Schlichtkrull et al. 2018, Modeling Relational Data with Graph Convolutional Networks"
                }
            ],
            "metrics": [
                {
                    "name": "Recall@K",
                    "description": "召回率，评估检索到的相关物品比例",
                    "implementation": "K值设为10、20、50"
                },
                {
                    "name": "NDCG@K",
                    "description": "归一化折损累积增益，评估推荐排序质量",
                    "implementation": "K值设为10、20、50"
                },
                {
                    "name": "Precision@K",
                    "description": "精确率，评估推荐物品的准确性",
                    "implementation": "K值设为10、20、50"
                },
                {
                    "name": "Coverage",
                    "description": "覆盖率，评估推荐物品的多样性",
                    "implementation": "计算所有测试用户推荐结果中出现的独特物品占比"
                }
            ],
            "experimentSetup": {
                "trainTestSplit": "随机划分80%训练/10%验证/10%测试，固定随机种子确保可复现",
                "negativeSampling": "每个正样本采样4个负样本，确保负样本未在用户历史中出现",
                "layerSettings": "设置3层图卷积，聚合范围为一阶邻居",
                "infrastructure": "使用DGL库实现图神经网络，在NVIDIA A100 GPU上训练",
                "crossValidation": "进行5折交叉验证，报告平均性能和标准差"
            },
            "implementationDetails": {
                "framework": "PyTorch Geometric / DGL",
                "embeddings": "维度为64的初始节点嵌入",
                "aggregator": "采用平均聚合器、最大池化聚合器和注意力聚合器分别进行实验",
                "optimizer": "Adam优化器，学习率0.001，权重衰减1e-5",
                "batchSize": "1024个节点的子图批次",
                "earlyStopping": "在验证集上10轮无改善则停止"
            },
            "analysisPlans": [
                "主实验：比较提出的方法与各基线在推荐准确性上的差异",
                "消融实验：验证不同关系类型、不同聚合器、注意力机制的贡献",
                "异构性分析：分析不同类型节点和边对最终性能的影响",
                "冷启动分析：评估模型对不同物品曝光度的适应能力",
                "可视化分析：可视化注意力分布和节点嵌入空间"
            ],
            "limitations": [
                "构建大规模异构图需要额外数据源，增加了数据预处理复杂度",
                "图神经网络训练成本高，模型规模受GPU内存限制",
                "难以处理动态变化的图结构",
                "异构关系的选择需要领域专家知识，不同数据集可能需要定制化设计"
            ]
        }
        
    # 对于其他领域，根据需要生成通用模板
    else:
        # 获取领域名称标签
        domain_name = domain
        for d in [
            {"value": "sequential", "label": "序列推荐"},
            {"value": "graph", "label": "图神经网络推荐"},
            {"value": "multi_modal", "label": "多模态推荐"},
            {"value": "knowledge", "label": "知识图谱推荐"},
            {"value": "contrastive", "label": "对比学习推荐"},
            {"value": "cold_start", "label": "冷启动推荐"},
            {"value": "cross_domain", "label": "跨域推荐"},
            {"value": "explainable", "label": "可解释性推荐"}
        ]:
            if d["value"] == domain:
                domain_name = d["label"]
                break
        
        # 获取指标名称
        metrics_name = metric_type
        for m in [
            {"value": "accuracy", "label": "准确率指标"},
            {"value": "diversity", "label": "多样性指标"},
            {"value": "novelty", "label": "新颖性指标"},
            {"value": "efficiency", "label": "效率指标"},
            {"value": "fairness", "label": "公平性指标"}
        ]:
            if m["value"] == metric_type:
                metrics_name = m["label"]
                break
        
        # 通用实验设计
        design_result = {
            "domain": domain_name,
            "experimentTitle": f"基于{domain_name}的推荐方法实验评估",
            "overview": f"本实验设计提供了评估{domain_name}方法的完整框架，包括数据集选择、基线方法、评估指标和实验设置，以全面验证所提出方法的有效性。",
            "datasets": [
                {
                    "name": "MovieLens-1M",
                    "type": "电影评分数据",
                    "size": "用户-电影评分 1,000,209条，用户数 6,040，电影数 3,706",
                    "features": "评分、时间戳、用户人口统计学特征、电影类别",
                    "source": "GroupLens Research",
                    "preprocessing": "保留评分4分以上为正样本，随机分割为8:1:1的训练-验证-测试集"
                },
                {
                    "name": "Amazon Review",
                    "type": "电子商务评价数据",
                    "size": "多个产品类别，数百万用户-物品交互",
                    "features": "评分、评论文本、产品类别、产品描述、品牌",
                    "source": "Amazon Review Dataset",
                    "preprocessing": "可选择具体类别子集，筛选活跃用户和物品，构建隐式或显式反馈数据集"
                },
                {
                    "name": "Yelp",
                    "type": "商户评价数据",
                    "size": "用户-商户评价 8,635,403条，用户数 2,189,457，商户数 160,585",
                    "features": "评分、评论文本、商户类别、位置、图片",
                    "source": "Yelp Dataset Challenge",
                    "preprocessing": "将评分转换为隐式反馈，使用时间信息进行训练-测试划分"
                }
            ],
            "baselines": [
                {
                    "name": "BPR-MF",
                    "description": "经典矩阵分解模型，使用贝叶斯个性化排序优化",
                    "reference": "Rendle et al. 2009, BPR: Bayesian Personalized Ranking from Implicit Feedback"
                },
                {
                    "name": "NeuMF",
                    "description": "神经协同过滤模型，结合了MF和MLP",
                    "reference": "He et al. 2017, Neural Collaborative Filtering"
                },
                {
                    "name": "LightGCN",
                    "description": "轻量级图卷积网络推荐模型",
                    "reference": "He et al. 2020, LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation"
                },
                {
                    "name": "SASRec",
                    "description": "基于自注意力的序列推荐模型",
                    "reference": "Kang et al. 2018, Self-Attentive Sequential Recommendation"
                },
                {
                    "name": "RecVAE",
                    "description": "基于变分自编码器的推荐模型",
                    "reference": "Shenbin et al. 2020, RecVAE: A New Variational Autoencoder for Top-N Recommendations with Implicit Feedback"
                }
            ],
            "metrics": [
                {
                    "name": "Recall@K",
                    "description": "衡量推荐系统检索相关物品的能力",
                    "implementation": "K值为10、20、50"
                },
                {
                    "name": "NDCG@K",
                    "description": "衡量推荐系统考虑排序质量的能力",
                    "implementation": "K值为10、20、50"
                },
                {
                    "name": "Precision@K",
                    "description": "衡量推荐列表中相关物品的比例",
                    "implementation": "K值为10、20、50"
                },
                {
                    "name": "F1@K",
                    "description": "Precision和Recall的调和平均",
                    "implementation": "K值为10、20、50"
                }
            ],
            "experimentSetup": {
                "trainTestSplit": "随机划分数据集为训练集(80%)、验证集(10%)和测试集(10%)",
                "negativeSampling": "对每个正样本随机采样4个负样本",
                "evaluationProtocol": "对每个用户，在全部物品集合上计算排序分数，推荐Top-K物品",
                "hyperparameterOptimization": "使用网格搜索优化关键超参数",
                "implementation": "使用PyTorch实现所有模型"
            },
            "implementationDetails": {
                "framework": "PyTorch 1.10+",
                "optimizer": "Adam优化器，初始学习率0.001",
                "batchSize": 256,
                "embeddingSize": 64,
                "regularization": "L2正则化系数1e-5",
                "earlyStopping": "验证集上5轮无提升则停止"
            },
            "analysisPlans": [
                "主实验：比较提出方法与基线方法在三个数据集上的性能",
                "消融实验：验证提出方法的各关键组件的有效性",
                "超参数敏感性分析：探讨关键超参数对模型性能的影响",
                "冷启动性能分析：评估在数据稀疏场景下的表现",
                "计算效率分析：比较各方法的训练和推理效率"
            ],
            "limitations": [
                "离线评估可能无法完全反映在线性能",
                "未考虑用户长期兴趣演变",
                "数据集可能存在偏差，影响评估结果",
                "计算资源限制了更大规模的模型训练"
            ]
        }
        
    # 如果有方法描述，可以基于此定制设计
    if method_description:
        design_result["methodDescription"] = method_description
        # 可以根据方法描述进一步定制设计内容
    
    return design_result 