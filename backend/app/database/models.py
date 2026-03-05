"""
数据库模型定义 - 软著申请：数据持久化层设计
作用：定义系统中所有数据表结构，支持电信诈骗检测业务的完整数据流
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, JSON, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    """用户表 - 软著申请：用户管理系统"""
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # 关联关系
    fraud_cases = relationship("FraudCase", back_populates="user")
    monitoring_sessions = relationship("MonitoringSession", back_populates="user")
    ai_practice_sessions = relationship("AiPracticeSession", back_populates="user")

class FraudCase(Base):
    """诈骗案例表 - 软著申请：诈骗案件管理核心数据结构"""
    __tablename__ = "fraud_cases"
    
    case_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    case_name = Column(String(200), nullable=False)
    fraud_type = Column(String(100), nullable=False)  # 'vishing', 'impersonation', 'wangiri', 'investment', 'lottery'
    risk_score = Column(Float, nullable=False)  # 0.00-100.00 风险评分
    status = Column(String(20), default='pending')  # 'pending', 'investigating', 'resolved'
    detection_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    resolution_timestamp = Column(DateTime)
    assigned_agent = Column(String(100))
    notes = Column(Text)
    
    # ⚠️ 核心修改点：将 metadata 改为 case_metadata 以避免 SQLAlchemy 保留字冲突
    case_metadata = Column(JSON)  # 额外的诈骗检测特征数据
    
    # 关联关系
    user = relationship("User", back_populates="fraud_cases")
    audio_evidence = relationship("AudioEvidence", back_populates="fraud_case")
    fraud_alerts = relationship("FraudAlert", back_populates="fraud_case")

class AudioEvidence(Base):
    """音频证据表 - 软著申请：多媒体证据管理系统"""
    __tablename__ = "audio_evidence"
    
    evidence_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("fraud_cases.case_id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    duration_seconds = Column(Float)
    audio_format = Column(String(20))  # 'mp3', 'wav', 'm4a', 'flac'
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    processing_status = Column(String(20), default='uploaded')  # 'uploaded', 'processing', 'completed', 'failed'
    transcription = Column(Text)  # ASR转录文本
    fraud_indicators = Column(JSON)  # 诈骗指标分析结果
    
    # 关联关系
    fraud_case = relationship("FraudCase", back_populates="audio_evidence")
    detection_results = relationship("DetectionResult", back_populates="audio_evidence")

class MonitoringSession(Base):
    """实时监听会话表 - 软著申请：实时通话监护核心功能"""
    __tablename__ = "monitoring_sessions"
    
    session_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    status = Column(String(20), default='active')  # 'active', 'completed', 'interrupted'
    risk_alerts_triggered = Column(Integer, default=0)
    max_risk_score = Column(Float, default=0.00)
    session_data = Column(JSON)  # 会话详细数据
    
    # 关联关系
    user = relationship("User", back_populates="monitoring_sessions")
    fraud_alerts = relationship("FraudAlert", back_populates="monitoring_session")
    detection_results = relationship("DetectionResult", back_populates="monitoring_session")

class AiPracticeSession(Base):
    """AI陪练会话表 - 软著申请：智能对话训练系统"""
    __tablename__ = "ai_practice_sessions"
    
    session_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    scenario_type = Column(String(100))  # 'impersonation', 'urgency_tactics', 'investment', 'lottery'
    difficulty_level = Column(Integer, default=1)  # 1-5 难度等级
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    user_responses_count = Column(Integer, default=0)
    successful_identifications = Column(Integer, default=0)
    performance_score = Column(Float)
    session_transcript = Column(Text)
    feedback_data = Column(JSON)  # 详细反馈数据
    
    # 关联关系
    user = relationship("User", back_populates="ai_practice_sessions")

class FraudAlert(Base):
    """诈骗警报表 - 软著申请：实时警报系统"""
    __tablename__ = "fraud_alerts"
    
    alert_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("monitoring_sessions.session_id"), index=True)
    case_id = Column(Integer, ForeignKey("fraud_cases.case_id"), index=True)
    alert_type = Column(String(100), nullable=False)  # 'voice_biometrics', 'behavioral', 'content_analysis'
    severity = Column(String(20), nullable=False)  # 'low', 'medium', 'high', 'critical'
    confidence_score = Column(Float, nullable=False)
    detection_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    description = Column(Text)
    evidence_data = Column(JSON)  # 警报证据数据
    is_acknowledged = Column(Boolean, default=False)
    
    # 关联关系
    monitoring_session = relationship("MonitoringSession", back_populates="fraud_alerts")
    fraud_case = relationship("FraudCase", back_populates="fraud_alerts")

class DetectionResult(Base):
    """检测结果表 - 软著申请：AI检测结果详细记录"""
    __tablename__ = "detection_results"
    
    result_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("monitoring_sessions.session_id"), index=True)
    evidence_id = Column(Integer, ForeignKey("audio_evidence.evidence_id"), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # 检测数据
    audio_chunk_id = Column(String(100))  # 音频块标识
    asr_transcript = Column(Text)  # 语音识别结果
    qwen_logits = Column(JSON)  # Qwen2Audio模型输出logits
    risk_label = Column(String(50))  # 风险标签
    risk_score = Column(Float)  # 风险评分
    
    # 模型分析详情
    sentiment_score = Column(Float)  # 情感分析分数
    urgency_score = Column(Float)  # 紧急性评分
    manipulation_score = Column(Float)  # 操纵性评分
    
    # 处理状态
    processing_time_ms = Column(Float)  # 处理耗时(毫秒)
    model_version = Column(String(50))  # 使用的模型版本
    
    # 关联关系
    monitoring_session = relationship("MonitoringSession", back_populates="detection_results")
    audio_evidence = relationship("AudioEvidence", back_populates="detection_results")

class SystemConfig(Base):
    """系统配置表 - 软著申请：动态配置管理"""
    __tablename__ = "system_config"
    
    config_key = Column(String(100), primary_key=True)
    config_value = Column(Text, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class ModelMetrics(Base):
    """模型性能指标表 - 软著申请：AI模型性能监控"""
    __tablename__ = "model_metrics"
    
    metric_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_name = Column(String(100), nullable=False, index=True)
    model_version = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # 性能指标
    total_inferences = Column(Integer, default=0)
    avg_inference_time_ms = Column(Float)
    max_inference_time_ms = Column(Float)
    min_inference_time_ms = Column(Float)
    error_count = Column(Integer, default=0)
    
    # 准确性指标
    true_positives = Column(Integer, default=0)
    false_positives = Column(Integer, default=0)
    true_negatives = Column(Integer, default=0)
    false_negatives = Column(Integer, default=0)
    
    # 计算指标
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    accuracy = Column(Float)