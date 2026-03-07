"""
实时监护会话服务
作用：统一监护会话的创建、校验和结束逻辑，避免WebSocket连接ID与数据库业务会话ID分裂。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.database.database import db_manager
from app.database.models import MonitoringSession, User


class MonitoringSessionService:
    """统一管理监护会话生命周期。"""

    def _resolve_user(self, db, user_id: Optional[int]) -> User:
        if user_id is not None:
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise ValueError("用户不存在")
            return user

        demo_user = db.query(User).filter(User.username == "demo_user").first()
        if demo_user:
            return demo_user

        demo_user = User(
            username="demo_user",
            email="demo_user@local.invalid",
            password_hash="disabled-login",
            is_active=True,
        )
        db.add(demo_user)
        db.flush()
        return demo_user

    def create_session(
        self,
        user_id: Optional[int] = None,
        sensitivity_level: str = "medium",
        alert_types: Optional[List[str]] = None,
        auto_record: bool = True,
    ) -> Dict[str, Any]:
        with db_manager.get_session() as db:
            user = self._resolve_user(db, user_id)
            session = MonitoringSession(
                user_id=user.user_id,
                status="active",
                session_data={
                    "sensitivity_level": sensitivity_level,
                    "alert_types": alert_types or ["voice_biometrics", "behavioral", "content"],
                    "auto_record": auto_record,
                    "created_via": "api",
                    "connected_at": None,
                },
            )
            db.add(session)
            db.commit()
            db.refresh(session)

            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "status": session.status,
                "created_at": session.start_time,
                "session_data": session.session_data or {},
            }

    def ensure_session(self, session_id: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        with db_manager.get_session() as db:
            session = db.query(MonitoringSession).filter(MonitoringSession.session_id == session_id).first()
            if not session:
                raise ValueError("监听会话不存在")

            if user_id is not None and session.user_id != user_id:
                raise ValueError("监听会话与用户不匹配")

            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "status": session.status,
                "created_at": session.start_time,
                "session_data": session.session_data or {},
            }

    def mark_connected(self, session_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        with db_manager.get_session() as db:
            session = db.query(MonitoringSession).filter(MonitoringSession.session_id == session_id).first()
            if not session:
                return

            session.status = "active"
            session.end_time = None
            session_data = dict(session.session_data or {})
            session_data["connected_at"] = datetime.utcnow().isoformat()
            if metadata:
                session_data.update(metadata)
            session.session_data = session_data
            db.commit()

    def complete_session(self, session_id: str, status: str = "completed") -> None:
        with db_manager.get_session() as db:
            session = db.query(MonitoringSession).filter(MonitoringSession.session_id == session_id).first()
            if not session:
                return

            session.status = status
            session.end_time = datetime.utcnow()
            session_data = dict(session.session_data or {})
            session_data["closed_at"] = session.end_time.isoformat()
            session_data["closed_status"] = status
            session.session_data = session_data
            db.commit()


monitoring_session_service = MonitoringSessionService()