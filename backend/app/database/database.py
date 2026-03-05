"""
数据库连接和会话管理 - 软著申请：数据库连接池和事务管理
作用：提供数据库连接、会话管理和初始化功能，支持高并发访问
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os
from typing import Generator

from app.database.models import Base
from app.config import settings

# 数据库引擎配置 - 软著申请：高性能数据库连接池
def create_database_engine():
    """创建数据库引擎"""
    
    if settings.database_url.startswith("sqlite"):
        # SQLite配置 - 适用于开发和轻量级部署
        engine = create_engine(
            settings.database_url,
            connect_args={
                "check_same_thread": False,  # SQLite特有配置，允许多线程
                "timeout": 20,  # 连接超时时间
            },
            poolclass=StaticPool,  # SQLite使用静态连接池
            echo=settings.database_echo,  # 开发环境下打印SQL语句
            pool_pre_ping=True,  # 连接前检查连接有效性
        )
    else:
        # PostgreSQL/MySQL配置 - 适用于生产环境
        engine = create_engine(
            settings.database_url,
            pool_size=20,  # 连接池大小
            max_overflow=30,  # 最大溢出连接数
            pool_pre_ping=True,  # 连接前检查连接有效性
            pool_recycle=3600,  # 连接回收时间（秒）
            echo=settings.database_echo,
        )
    
    return engine

# 创建数据库引擎
engine = create_database_engine()

# 创建会话工厂 - 软著申请：会话管理模式
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # 防止对象在提交后过期
)

# 元数据
metadata = MetaData()

def init_database():
    """初始化数据库 - 软著申请：数据库初始化和迁移"""
    
    # 确保上传目录存在
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(os.path.join(settings.upload_dir, "audio"), exist_ok=True)
    os.makedirs(os.path.join(settings.upload_dir, "models"), exist_ok=True)
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 初始化系统配置
    _init_system_config()

def _init_system_config():
    """初始化系统配置"""
    from app.database.models import SystemConfig
    
    db = SessionLocal()
    try:
        # 检查是否已有配置
        existing_configs = db.query(SystemConfig).count()
        if existing_configs > 0:
            return
        
        # 默认系统配置
        default_configs = [
            {
                "config_key": "risk_threshold_low",
                "config_value": str(settings.risk_threshold_low),
                "description": "低风险阈值"
            },
            {
                "config_key": "risk_threshold_medium", 
                "config_value": str(settings.risk_threshold_medium),
                "description": "中风险阈值"
            },
            {
                "config_key": "vad_threshold",
                "config_value": str(settings.vad_threshold),
                "description": "语音活动检测阈值"
            },
            {
                "config_key": "max_concurrent_sessions",
                "config_value": "100",
                "description": "最大并发会话数"
            },
            {
                "config_key": "audio_retention_days",
                "config_value": "30",
                "description": "音频文件保留天数"
            },
            {
                "config_key": "auto_alert_enabled",
                "config_value": "true",
                "description": "自动警报功能开关"
            }
        ]
        
        for config in default_configs:
            db_config = SystemConfig(**config)
            db.add(db_config)
        
        db.commit()
        print("系统配置初始化完成")
        
    except Exception as e:
        db.rollback()
        print(f"系统配置初始化失败: {e}")
        raise
    finally:
        db.close()

def get_db() -> Generator[Session, None, None]:
    """获取数据库会话 - 软著申请：依赖注入模式"""
    
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

class DatabaseManager:
    """数据库管理器 - 软著申请：数据库高级管理功能"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    def get_session(self) -> Session:
        """获取新的数据库会话"""
        return self.SessionLocal()
    
    def health_check(self) -> dict:
        """数据库健康检查"""
        try:
            with self.get_session() as db:
                from sqlalchemy import text
                db.execute(text("SELECT 1"))
            return {"status": "healthy", "message": "数据库连接正常"}
        except Exception as e:
            return {"status": "unhealthy", "message": str(e)}
    
    def get_stats(self) -> dict:
        """获取数据库统计信息"""
        try:
            from app.database.models import User, FraudCase, MonitoringSession, AiPracticeSession, FraudAlert, DetectionResult
            
            with self.get_session() as db:
                # 各表的记录数统计
                stats = {
                    "users": db.query(User).count(),
                    "fraud_cases": db.query(FraudCase).count(),
                    "monitoring_sessions": db.query(MonitoringSession).count(),
                    "ai_practice_sessions": db.query(AiPracticeSession).count(),
                    "fraud_alerts": db.query(FraudAlert).count(),
                    "detection_results": db.query(DetectionResult).count(),
                }
                return stats
        except Exception as e:
            return {"error": str(e)}
    
    def cleanup_old_data(self, days: int = 30):
        """清理旧数据 - 软著申请：数据生命周期管理"""
        from datetime import datetime, timedelta
        from app.database.models import MonitoringSession, DetectionResult
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with self.get_session() as db:
            try:
                # 删除旧的检测结果
                old_results = db.query(DetectionResult).filter(
                    DetectionResult.timestamp < cutoff_date
                ).delete()
                
                # 删除旧的监听会话
                old_sessions = db.query(MonitoringSession).filter(
                    MonitoringSession.start_time < cutoff_date,
                    MonitoringSession.status != 'active'
                ).delete()
                
                db.commit()
                return {
                    "deleted_results": old_results,
                    "deleted_sessions": old_sessions
                }
            except Exception as e:
                db.rollback()
                return {"error": str(e)}

# 创建全局数据库管理器实例
db_manager = DatabaseManager()