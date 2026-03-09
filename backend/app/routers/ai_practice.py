"""
AI陪练模式路由 - 软著申请：智能对话训练API
作用：提供AI陪练会话的RESTful接口，支持诈骗场景模拟训练
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime

from app.database.database import get_db
from app.database.models import AiPracticeSession, User
from app.services.ai_chat import AIChatService
from pydantic import BaseModel

router = APIRouter()
ai_chat_service = AIChatService()


def _raise_chat_service_error(error_text: str):
    """将服务层错误映射为更合适的HTTP状态码。"""

    message = error_text or "服务处理失败"
    lowered = message.lower()
    dependency_keywords = [
        "严格模式",
        "不可用",
        "初始化失败",
        "禁止降级",
        "not available",
        "not installed",
        "dependency",
        "qwen",
        "whisper",
        "edge_tts",
        "tts",
    ]

    status_code = 503 if any(keyword in lowered for keyword in dependency_keywords) else 500
    raise HTTPException(status_code=status_code, detail=message)

# Pydantic模型
class PracticeSessionCreate(BaseModel):
    """创建陪练会话请求模型"""
    scenario_type: str
    difficulty_level: int = 1
    user_id: int

class PracticeSessionResponse(BaseModel):
    """陪练会话响应模型"""
    session_id: str
    status: str
    created_at: datetime
    scenario_type: str
    difficulty_level: int


class PracticeSessionStartRequest(BaseModel):
    """开始陪练会话请求模型"""
    scenario_type: str
    difficulty_level: int = 1
    user_id: int = 1


class PracticeSessionEndRequest(BaseModel):
    """结束陪练会话请求模型"""
    session_id: str


@router.post("/session/start")
async def start_practice_session(session_data: PracticeSessionStartRequest):
    """兼容前端的会话开始接口"""

    result = await ai_chat_service.start_practice_session(
        user_id=session_data.user_id,
        scenario_type=session_data.scenario_type,
        difficulty_level=session_data.difficulty_level,
    )

    if result.get("error"):
        _raise_chat_service_error(result["error"])

    return {
        "session_id": result.get("session_id"),
        "scenario_type": result.get("scenario_type", session_data.scenario_type),
        "difficulty_level": result.get("difficulty_level", session_data.difficulty_level),
        "greeting_message": result.get("greeting_message", "欢迎来到AI防诈陪练。"),
    }


@router.post("/session/end")
async def end_practice_session(session_data: PracticeSessionEndRequest):
    """兼容前端的会话结束接口"""

    result = await ai_chat_service.end_practice_session(session_data.session_id)
    if result.get("error"):
        _raise_chat_service_error(result["error"])

    summary = result.get("summary", {})
    total_messages = int(summary.get("total_messages", 0))
    successful_identifications = int(summary.get("successful_identifications", 0))
    detection_rate = float(summary.get("detection_rate", 0.0))
    performance_score = float(summary.get("performance_score", 0.0))

    return {
        "totalMessages": total_messages,
        "successfulIdentifications": successful_identifications,
        "detectionRate": detection_rate,
        "performanceScore": performance_score,
        "improvementSuggestions": [
            "遇到自称公检法、客服要求转账时，务必先挂断并通过官方渠道核实。",
            "对“限时处理”“立即操作”类话术保持警惕，避免在压力下做决定。",
            "不要在通话中透露身份证、银行卡、验证码等敏感信息。",
        ],
        "keyLearningPoints": [
            "识别身份冒充和紧急施压是防诈第一步。",
            "先核实、后操作，永远优先独立回拨官方电话。",
            "任何要求私下转账到“安全账户”的行为都高度可疑。",
        ],
    }


@router.post("/audio")
async def process_practice_audio(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
):
    """兼容前端的音频上传处理接口"""

    audio_data = await audio.read()
    if not audio_data:
        raise HTTPException(status_code=400, detail="音频数据为空")

    result = await ai_chat_service.process_audio_message(audio_data, session_id)
    if result.get("error"):
        _raise_chat_service_error(result["error"])

    fraud_analysis = result.get("fraud_analysis", {})
    indicators = fraud_analysis.get("indicators", {})
    fraud_keywords = indicators.get("fraud_keywords", [])

    return {
        "transcript": result.get("transcript", ""),
        "response": {
            "text": result.get("message", "我已收到你的语音内容。"),
            "audio_url": result.get("audio_url"),
            "fraud_indicators": fraud_keywords,
        },
        "risk_score": result.get("risk_score", 0),
    }

@router.post("/session", response_model=PracticeSessionResponse)
async def create_practice_session(
    session_data: PracticeSessionCreate,
    db: Session = Depends(get_db)
):
    """创建新的AI陪练会话"""
    
    try:
        # 验证用户存在
        user = db.query(User).filter(User.user_id == session_data.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 创建会话
        practice_session = AiPracticeSession(
            user_id=session_data.user_id,
            scenario_type=session_data.scenario_type,
            difficulty_level=session_data.difficulty_level,
        )
        
        db.add(practice_session)
        db.commit()
        db.refresh(practice_session)
        
        return PracticeSessionResponse(
            session_id=practice_session.session_id,
            status='active',
            created_at=practice_session.start_time,
            scenario_type=practice_session.scenario_type,
            difficulty_level=practice_session.difficulty_level
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建会话失败: {e}")

@router.get("/session/{session_id}")
async def get_practice_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """获取陪练会话信息"""
    
    try:
        session = db.query(AiPracticeSession).filter(
            AiPracticeSession.session_id == session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "scenario_type": session.scenario_type,
            "difficulty_level": session.difficulty_level,
            "status": "completed" if session.end_time else "active",
            "start_time": session.start_time,
            "end_time": session.end_time,
            "user_responses_count": session.user_responses_count,
            "successful_identifications": session.successful_identifications,
            "performance_score": session.performance_score
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话失败: {e}")

@router.get("/scenarios")
async def get_available_scenarios():
    """获取可用的训练场景"""
    
    scenarios = [
        {
            "id": "impersonation",
            "name": "身份冒充诈骗",
            "description": "模拟冒充公检法、银行等官方机构的诈骗场景",
            "difficulty_levels": [1, 2, 3, 4, 5]
        },
        {
            "id": "investment",
            "name": "投资理财诈骗",
            "description": "模拟高收益投资、虚拟货币等诈骗场景",
            "difficulty_levels": [1, 2, 3, 4, 5]
        },
        {
            "id": "lottery",
            "name": "中奖诈骗",
            "description": "模拟各种中奖、兑奖等诈骗场景",
            "difficulty_levels": [1, 2, 3]
        },
        {
            "id": "urgency_tactics",
            "name": "紧急诈骗",
            "description": "模拟利用紧急情况制造压力的诈骗场景",
            "difficulty_levels": [2, 3, 4, 5]
        }
    ]
    
    return {"scenarios": scenarios}

@router.post("/session/{session_id}/complete")
async def complete_practice_session(
    session_id: str,
    completion_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """完成陪练会话"""
    
    try:
        session = db.query(AiPracticeSession).filter(
            AiPracticeSession.session_id == session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 更新会话状态
        session.end_time = datetime.utcnow()
        session.status = 'completed'
        session.user_responses_count = completion_data.get('user_responses_count', 0)
        session.successful_identifications = completion_data.get('successful_identifications', 0)
        session.performance_score = completion_data.get('performance_score', 0.0)
        session.session_transcript = completion_data.get('transcript', '')
        session.feedback_data = completion_data.get('feedback_data', {})
        
        db.commit()
        
        return {
            "message": "会话完成",
            "session_id": session_id,
            "performance_score": session.performance_score
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"完成会话失败: {e}")

@router.get("/user/{user_id}/sessions")
async def get_user_practice_sessions(
    user_id: int,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取用户的陪练会话列表"""
    
    try:
        sessions = db.query(AiPracticeSession).filter(
            AiPracticeSession.user_id == user_id
        ).order_by(AiPracticeSession.start_time.desc()).limit(limit).all()
        
        return {
            "sessions": [
                {
                    "session_id": session.session_id,
                    "scenario_type": session.scenario_type,
                    "difficulty_level": session.difficulty_level,
                    "status": "completed" if session.end_time else "active",
                    "start_time": session.start_time,
                    "end_time": session.end_time,
                    "performance_score": session.performance_score
                }
                for session in sessions
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {e}")