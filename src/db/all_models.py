"""
导入所有模型类，确保它们都注册到SQLAlchemy的Base元数据中
这个文件被create_tables.py脚本使用，以确保创建所有表结构
"""

# 导入基类
from src.db.base_class import Base

# 用户相关模型
from src.models.user import User, APIKey

# 论文相关模型
from src.models.paper import Paper, Tag, Note, Category, Annotation, Folder

# 实验相关模型
from src.models.experiment import Experiment, ExperimentRun, ExperimentStatus

# 写作项目相关模型
from src.models.writing import WritingProject, WritingSection, WritingReference, ProjectStatus

# 助手相关模型
from src.models.assistant import AssistantSession, AssistantMessage

# AI设置相关模型
from src.models.ai_settings import AISettings

# 确保所有模型已导入到Base.metadata中
all_tables = list(Base.metadata.tables.keys())
print(f"已加载的表: {all_tables}") 