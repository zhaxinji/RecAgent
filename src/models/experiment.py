from sqlalchemy import Boolean, Column, String, Integer, DateTime, ForeignKey, Text, JSON, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from src.db.base import Base

class ExperimentStatus(enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RUNNING = "running"

class Experiment(Base):
    """实验模型"""
    __tablename__ = "experiments"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(ExperimentStatus), default=ExperimentStatus.DRAFT)
    code = Column(Text, nullable=True)  # 实验代码
    result = Column(JSON, nullable=True)  # 实验结果
    parameters = Column(JSON, nullable=True)  # 实验参数
    error_message = Column(Text, nullable=True)  # 错误信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)  # 最后运行时间
    
    # 外键
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    paper_id = Column(String, ForeignKey("papers.id", ondelete="SET NULL"), nullable=True)
    
    # 关系
    owner = relationship("User", back_populates="experiments")
    paper = relationship("Paper", back_populates="experiments")
    runs = relationship("ExperimentRun", back_populates="experiment")
    
class ExperimentRun(Base):
    """实验运行记录模型"""
    __tablename__ = "experiment_runs"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    parameters = Column(JSON, nullable=True)  # 运行时使用的参数
    metrics = Column(JSON, nullable=True)  # 运行结果指标
    logs = Column(Text, nullable=True)  # 运行日志
    duration = Column(Float, nullable=True)  # 运行时长，单位秒
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(ExperimentStatus), default=ExperimentStatus.IN_PROGRESS)
    
    # 外键
    experiment_id = Column(String, ForeignKey("experiments.id", ondelete="CASCADE"))
    
    # 关系
    experiment = relationship("Experiment", back_populates="runs")

class ExperimentResult(Base):
    """实验结果模型"""
    __tablename__ = "experiment_results"
    __table_args__ = {'extend_existing': True}
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    experiment_id = Column(String, ForeignKey("experiments.id", ondelete="CASCADE"))
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    output = Column(Text, nullable=True)  # 一般输出内容
    status = Column(String, nullable=True)  # 状态字符串
    error = Column(Text, nullable=True)  # 错误信息
    exit_code = Column(Integer, nullable=True)
    execution_time = Column(Float, nullable=True)
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    experiment = relationship("Experiment", backref="results") 