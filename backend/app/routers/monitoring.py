"""
实时监护模式路由 - 软著申请：实时通话监护API
作用：提供环境音监听和实时风险检测的RESTful接口
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime

from app.database.database import get_db
from app.database.models import MonitoringSession, FraudAlert, User
from app.services.monitoring_session_service import monitoring_session_service
from pydantic import BaseModel

router = APIRouter()

# Pydantic模型
class MonitoringSessionCreate(BaseModel):
    """创建监听会话请求模型"""
    user_id: int | None = None
    sensitivity_level: str = "medium"
    alert_types: List[str] = ["voice_biometrics", "behavioral", "content"]
    auto_record: bool = True

class MonitoringSessionResponse(BaseModel):
    """监听会话响应模型"""
    session_id: str
    status: str
    created_at: datetime
    sensitivity_level: str
    auto_record: bool

@router.post("/session", response_model=MonitoringSessionResponse)
async def create_monitoring_session(
    session_data: MonitoringSessionCreate,
    db: Session = Depends(get_db)
):
    """创建新的监听会话"""
    
    try:
        session_payload = monitoring_session_service.create_session(
            user_id=session_data.user_id,
            sensitivity_level=session_data.sensitivity_level,
            alert_types=session_data.alert_types,
            auto_record=session_data.auto_record,
        )

        return MonitoringSessionResponse(
            session_id=session_payload["session_id"],
            status=session_payload["status"],
            created_at=session_payload["created_at"],
            sensitivity_level=session_data.sensitivity_level,
            auto_record=session_data.auto_record
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建监听会话失败: {e}")

@router.get("/session/{session_id}/risk")
async def get_session_risk(
    session_id: str,
    db: Session = Depends(get_db)
):
    """获取会话的实时风险评估"""
    
    try:
        session = db.query(MonitoringSession).filter(
            MonitoringSession.session_id == session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="监听会话不存在")
        
        # 获取最近的警报
        recent_alerts = db.query(FraudAlert).filter(
            FraudAlert.session_id == session_id,
            FraudAlert.detection_timestamp >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).order_by(FraudAlert.detection_timestamp.desc()).limit(10).all()
        
        return {
            "session_id": session_id,
            "status": session.status,
            "max_risk_score": session.max_risk_score,
            "risk_alerts_triggered": session.risk_alerts_triggered,
            "recent_alerts": [
                {
                    "alert_id": alert.alert_id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "confidence_score": alert.confidence_score,
                    "description": alert.description,
                    "timestamp": alert.detection_timestamp
                }
                for alert in recent_alerts
            ],
            "risk_level": _calculate_risk_level(session.max_risk_score)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取风险评估失败: {e}")

@router.post("/session/{session_id}/alert")
async def trigger_manual_alert(
    session_id: str,
    alert_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """手动触发警报"""
    
    try:
        session = db.query(MonitoringSession).filter(
            MonitoringSession.session_id == session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="监听会话不存在")
        
        # 创建手动警报
        alert = FraudAlert(
            session_id=session_id,
            alert_type="manual",
            severity=alert_data.get("severity", "medium"),
            confidence_score=1.0,  # 手动警报置信度为100%
            description=alert_data.get("description", "用户手动触发的警报"),
            evidence_data=alert_data.get("evidence_data", {}),
            is_acknowledged=False
        )
        
        db.add(alert)
        
        # 更新会话统计
        session.risk_alerts_triggered += 1
        
        db.commit()
        
        return {
            "message": "手动警报已触发",
            "alert_id": alert.alert_id,
            "timestamp": alert.detection_timestamp
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"触发警报失败: {e}")

@router.get("/sessions/{user_id}")
async def get_user_monitoring_sessions(
    user_id: int,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取用户的监听会话列表"""
    
    try:
        sessions = db.query(MonitoringSession).filter(
            MonitoringSession.user_id == user_id
        ).order_by(MonitoringSession.start_time.desc()).limit(limit).all()
        
        return {
            "sessions": [
                {
                    "session_id": session.session_id,
                    "status": session.status,
                    "start_time": session.start_time,
                    "end_time": session.end_time,
                    "risk_alerts_triggered": session.risk_alerts_triggered,
                    "max_risk_score": session.max_risk_score,
                    "duration_minutes": _calculate_session_duration(session)
                }
                for session in sessions
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取监听会话列表失败: {e}")

@router.get("/session/{session_id}/alerts")
async def get_session_alerts(
    session_id: str,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取会话的警报列表"""
    
    try:
        session = db.query(MonitoringSession).filter(
            MonitoringSession.session_id == session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="监听会话不存在")
        
        alerts = db.query(FraudAlert).filter(
            FraudAlert.session_id == session_id
        ).order_by(FraudAlert.detection_timestamp.desc()).limit(limit).all()
        
        return {
            "session_id": session_id,
            "total_alerts": len(alerts),
            "alerts": [
                {
                    "alert_id": alert.alert_id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "confidence_score": alert.confidence_score,
                    "description": alert.description,
                    "evidence_data": alert.evidence_data,
                    "is_acknowledged": alert.is_acknowledged,
                    "timestamp": alert.detection_timestamp
                }
                for alert in alerts
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取警报列表失败: {e}")

def _calculate_risk_level(risk_score: float) -> str:
    """根据风险评分计算风险等级"""
    from app.config import settings
    
    if risk_score >= settings.risk_threshold_medium:
        return "high"
    elif risk_score >= settings.risk_threshold_low:
        return "medium"
    else:
        return "low"

def _calculate_session_duration(session: MonitoringSession) -> float:
    """计算会话持续时间（分钟）"""
    if session.end_time:
        duration = session.end_time - session.start_time
        return duration.total_seconds() / 60
    else:
        # 会话仍在进行中
        duration = datetime.utcnow() - session.start_time
        return duration.total_seconds() / 60