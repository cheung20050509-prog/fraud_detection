"""
案例分析模式路由 - 软著申请：文件上传和离线分析API
作用：提供音频文件上传、分析和案例创建的RESTful接口
"""

import asyncio
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
import logging

from app.database.database import get_db
from app.database.models import AudioEvidence, DetectionResult, FraudCase, User
from app.ml_models.qwen_integration import model_manager
from app.services.asr_service import shared_asr_service
from app.services.audio_utils import AudioUtils
from app.config import settings
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

ANALYSIS_TASKS: Dict[str, Dict[str, Any]] = {}
ANALYSIS_TASK_LOCK = asyncio.Lock()

FRAUD_KEYWORDS: Dict[str, List[str]] = {
    "authority": ["公安", "法院", "检察院", "客服", "官方", "监管"],
    "urgency": ["立即", "马上", "紧急", "立刻", "最后机会", "现在就"],
    "money": ["转账", "汇款", "打款", "验证码", "安全账户", "手续费", "保证金"],
    "threat": ["冻结", "逮捕", "起诉", "刑事", "法律责任"],
    "bait": ["中奖", "退款", "补偿", "高收益", "高回报", "投资"],
}


def _iso_now() -> str:
    return datetime.utcnow().isoformat()


def _risk_level(score: float) -> str:
    if score >= settings.risk_threshold_medium:
        return "high"
    if score >= settings.risk_threshold_low:
        return "medium"
    return "low"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _detect_keywords(text: str) -> Dict[str, Any]:
    cleaned = (text or "").strip()
    hits: List[str] = []
    category_hits: List[str] = []

    for category, words in FRAUD_KEYWORDS.items():
        matched = [w for w in words if w in cleaned]
        if matched:
            category_hits.append(category)
            hits.extend([f"{category}:{word}" for word in matched])

    keyword_score = min(len(hits) * 9.0, 65.0)
    return {
        "detected_keywords": hits,
        "matched_categories": sorted(set(category_hits)),
        "keyword_score": keyword_score,
    }


def _build_suggestions(risk_score: float, detected_keywords: List[str]) -> List[str]:
    base = [
        "遇到要求转账、提供验证码或个人敏感信息时，先挂断并通过官方渠道核实。",
        "对“限时处理”“立即操作”等施压话术保持警惕，避免在压力下做决定。",
        "不要向陌生账户转账，尤其是所谓“安全账户”或“监管账户”。",
    ]
    if risk_score >= 80:
        base.insert(0, "检测到高风险诈骗特征，建议立即中止沟通并保留证据报警。")
    elif risk_score >= 60:
        base.insert(0, "检测到中高风险信号，建议暂停操作并联系官方客服二次确认。")

    if any("authority:" in item for item in detected_keywords):
        base.append("涉及公检法/客服身份声明时，请独立回拨官方号码核验身份。")

    return base[:5]


def _build_fraud_type_breakdown(keyword_result: Dict[str, Any], risk_score: float) -> List[Dict[str, Any]]:
    category_names = {
        "authority": "身份冒充",
        "urgency": "紧急施压",
        "money": "资金诱导",
        "threat": "威胁恐吓",
        "bait": "利益诱导",
    }
    categories = keyword_result.get("matched_categories", [])

    if not categories and risk_score < 30:
        return [{"type": "normal", "name": "未见明显诈骗类型", "confidence": int(max(5, 100 - risk_score))}]

    breakdown: List[Dict[str, Any]] = []
    for category in categories:
        confidence = int(min(95, 45 + risk_score * 0.5))
        breakdown.append(
            {
                "type": category,
                "name": category_names.get(category, category),
                "confidence": confidence,
            }
        )
    return breakdown


async def _set_task(analysis_id: str, updates: Dict[str, Any]) -> None:
    async with ANALYSIS_TASK_LOCK:
        task = ANALYSIS_TASKS.get(analysis_id, {}).copy()
        task.update(updates)
        ANALYSIS_TASKS[analysis_id] = task


async def _get_task(analysis_id: str) -> Optional[Dict[str, Any]]:
    async with ANALYSIS_TASK_LOCK:
        task = ANALYSIS_TASKS.get(analysis_id)
        return task.copy() if task else None


def _resolve_user(db: Session, user_id: Optional[int]) -> User:
    """解析分析关联用户；未提供用户时使用（或创建）演示用户。"""

    if user_id is not None:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
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


async def _analyze_text_file(file_path: str) -> Dict[str, Any]:
    async with aiofiles.open(file_path, "rb") as file_obj:
        raw = await file_obj.read()

    text = raw.decode("utf-8", errors="ignore").strip()
    if not text:
        raise RuntimeError("文本文件内容为空")

    keyword_result = _detect_keywords(text)
    keyword_score = _safe_float(keyword_result.get("keyword_score", 0.0))
    risk_score = min(100.0, keyword_score + (8.0 if len(text) > 80 else 0.0))

    return {
        "fraud_detection": {
            "risk_score": risk_score,
            "risk_level": _risk_level(risk_score),
            "fraud_indicators": keyword_result.get("detected_keywords", []),
            "confidence": min(0.95, 0.55 + keyword_score / 100.0),
            "fraud_types": _build_fraud_type_breakdown(keyword_result, risk_score),
        },
        "voice_analysis": {
            "speaker_count": 0,
            "voice_characteristics": {},
        },
        "transcription": {
            "text": text,
            "duration_seconds": 0.0,
            "language": "zh-CN",
            "confidence": 1.0,
        },
        "key_features": keyword_result,
        "suggestions": _build_suggestions(risk_score, keyword_result.get("detected_keywords", [])),
    }


async def _analyze_audio_file(file_path: str) -> Dict[str, Any]:
    audio_utils = AudioUtils()
    asr_service = shared_asr_service
    qwen_processor = model_manager.get_processor()

    async with aiofiles.open(file_path, "rb") as file_obj:
        audio_bytes = await file_obj.read()

    audio_array = await audio_utils.preprocess_audio_chunk(
        audio_bytes,
        prefer_container_decode=True,
    )
    if audio_array is None or len(audio_array) == 0:
        raise RuntimeError("音频预处理失败或结果为空")

    transcript = await asr_service.transcribe_audio(audio_array)
    transcript_text = (transcript or "").strip()

    qwen_result = await qwen_processor.analyze_audio(audio_array)
    qwen_score = max(0.0, min(100.0, _safe_float(qwen_result.get("score", 0.0)) * 100.0))
    qwen_confidence = max(0.0, min(1.0, _safe_float(qwen_result.get("confidence", 0.0))))

    keyword_result = _detect_keywords(transcript_text)
    keyword_score = _safe_float(keyword_result.get("keyword_score", 0.0))

    voice_features = await audio_utils.extract_voice_features(audio_array)
    voice_signal = min(
        100.0,
        (
            abs(_safe_float(voice_features.get("pitch_std", 0.0))) * 0.05
            + abs(_safe_float(voice_features.get("volume_variance", 0.0))) * 4000.0
            + abs(_safe_float(voice_features.get("zero_crossing_rate", 0.0))) * 120.0
        ),
    )

    risk_score = min(100.0, qwen_score * 0.55 + keyword_score * 0.3 + voice_signal * 0.15)
    fraud_indicators = list(
        dict.fromkeys(
            [str(item) for item in qwen_result.get("fraud_indicators", [])]
            + keyword_result.get("detected_keywords", [])
        )
    )

    duration_seconds = float(len(audio_array) / max(1, settings.audio_sample_rate))

    return {
        "fraud_detection": {
            "risk_score": risk_score,
            "risk_level": _risk_level(risk_score),
            "fraud_indicators": fraud_indicators,
            "confidence": max(qwen_confidence, 0.55),
            "fraud_types": _build_fraud_type_breakdown(keyword_result, risk_score),
        },
        "voice_analysis": {
            "speaker_count": 1,
            "voice_characteristics": {
                "stress_level": min(1.0, voice_signal / 100.0),
                "speech_rate": voice_features.get("speech_rate", 0.0),
                "volume_variance": voice_features.get("volume_variance", 0.0),
                "pitch_variance": voice_features.get("pitch_std", 0.0),
            },
        },
        "transcription": {
            "text": transcript_text,
            "duration_seconds": duration_seconds,
            "language": "zh-CN",
            "confidence": max(0.0, min(1.0, 0.8 if transcript_text else 0.0)),
        },
        "key_features": {
            **keyword_result,
            "qwen_score": qwen_score,
            "voice_signal": voice_signal,
        },
        "suggestions": _build_suggestions(risk_score, fraud_indicators),
    }

def _build_results_payload(task: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "analysis_id": task["analysis_id"],
        "evidence_id": task.get("evidence_id"),
        "case_id": task.get("case_id"),
        "status": task.get("status", "processing"),
        "created_at": task.get("created_at"),
        "started_at": task.get("started_at"),
        "completed_at": task.get("completed_at"),
        "processing_time_ms": task.get("processing_time_ms", 0.0),
        "file_name": task.get("file_name"),
        "file_size": task.get("file_size"),
        "error": task.get("error"),
        "results": task.get("results"),
    }

# Pydantic模型
class AnalysisRequest(BaseModel):
    """分析请求模型"""
    user_id: int
    case_name: str
    fraud_type: str
    analysis_types: List[str] = ["fraud_detection", "voice_analysis", "transcription"]

class CaseCreateRequest(BaseModel):
    """创建案例请求模型"""
    analysis_id: str
    fraud_type: str
    priority: str = "medium"
    notes: Optional[str] = None

@router.post("/upload")
async def upload_file_for_analysis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: int = None,
    case_name: str = "默认案例",
    fraud_type: str = "unknown",
    analysis_types: str = "fraud_detection,voice_analysis,transcription",
    db: Session = Depends(get_db)
):
    """上传文件进行分析 - 软著申请：文件上传和预处理"""

    try:
        # 验证文件类型
        if not _is_allowed_file(file.filename):
            raise HTTPException(status_code=400, detail="不支持的文件类型")

        # 保存文件后使用实际字节长度校验，兼容不同客户端是否上送size。
        content = await file.read()
        if len(content) > settings.max_file_size:
            raise HTTPException(status_code=400, detail="文件大小超过限制")

        # 生成唯一文件名
        file_extension = os.path.splitext(file.filename)[1].lower()
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(settings.upload_dir, "audio", unique_filename)

        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        resolved_user = _resolve_user(db, user_id)
        case_label = case_name.strip() if case_name else "默认案例"

        # 先创建案例，再挂接证据，避免case_id非空约束失败。
        fraud_case = FraudCase(
            user_id=resolved_user.user_id,
            case_name=case_label,
            fraud_type=fraud_type or "unknown",
            risk_score=0.0,
            status="pending",
            notes="由离线分析上传自动创建",
        )
        db.add(fraud_case)
        db.flush()

        # 创建证据记录
        audio_evidence = AudioEvidence(
            case_id=fraud_case.case_id,
            file_name=file.filename,
            file_path=file_path,
            file_size=len(content),
            audio_format=file_extension[1:],  # 去掉点号
            processing_status="uploaded"
        )

        db.add(audio_evidence)
        db.commit()
        db.refresh(audio_evidence)

        # 解析分析类型
        analysis_types_list = analysis_types.split(',') if isinstance(analysis_types, str) else analysis_types

        # 添加后台分析任务
        analysis_id = str(uuid.uuid4())

        await _set_task(
            analysis_id,
            {
                "analysis_id": analysis_id,
                "status": "processing",
                "created_at": _iso_now(),
                "file_name": file.filename,
                "file_size": len(content),
                "evidence_id": audio_evidence.evidence_id,
                "case_id": fraud_case.case_id,
                "error": None,
                "results": None,
            },
        )

        background_tasks.add_task(
            _analyze_file_background,
            analysis_id,
            audio_evidence.evidence_id,
            analysis_types_list,
            resolved_user.user_id,
            case_name,
            fraud_type,
            file_path,
            file_extension,
        )

        return {
            "message": "文件上传成功，正在分析中",
            "analysis_id": analysis_id,
            "evidence_id": audio_evidence.evidence_id,
            "case_id": fraud_case.case_id,
            "file_id": analysis_id,
            "file_name": file.filename,
            "file_size": len(content),
            "status": "processing"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"文件上传失败: {e}")

@router.get("/results/{analysis_id}")
async def get_analysis_results(
    analysis_id: str,
    db: Session = Depends(get_db)
):
    """获取分析结果"""

    try:
        task = await _get_task(analysis_id)
        if not task:
            raise HTTPException(status_code=404, detail="分析任务不存在")

        return _build_results_payload(task)

    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"获取分析结果失败: {e}")

@router.post("/results/{analysis_id}/create_case")
async def create_case_from_analysis(
    analysis_id: str,
    case_data: CaseCreateRequest,
    db: Session = Depends(get_db)
):
    """从分析结果创建诈骗案例"""

    try:
        task = await _get_task(analysis_id)
        if not task:
            raise HTTPException(status_code=404, detail="分析任务不存在")
        if task.get("status") != "completed":
            raise HTTPException(status_code=400, detail="分析尚未完成，无法创建案例")

        case_id = task.get("case_id")
        if case_id is None:
            raise HTTPException(status_code=500, detail="任务缺少关联案例ID")

        fraud_case = db.query(FraudCase).filter(FraudCase.case_id == case_id).first()
        if not fraud_case:
            raise HTTPException(status_code=404, detail="关联案例不存在")

        result_payload = task.get("results") or {}
        fraud_detection = result_payload.get("fraud_detection") or {}

        fraud_case.fraud_type = case_data.fraud_type or fraud_case.fraud_type
        fraud_case.risk_score = _safe_float(fraud_detection.get("risk_score", fraud_case.risk_score))
        fraud_case.status = "investigating" if fraud_case.risk_score >= settings.risk_threshold_low else "resolved"
        fraud_case.notes = case_data.notes or fraud_case.notes
        fraud_case.case_metadata = {
            "analysis_id": analysis_id,
            "priority": case_data.priority,
            "fraud_indicators": fraud_detection.get("fraud_indicators", []),
            "updated_at": _iso_now(),
        }

        db.commit()

        return {
            "message": "案例创建成功",
            "case_id": case_id,
            "analysis_id": analysis_id,
            "fraud_type": fraud_case.fraud_type,
            "risk_score": fraud_case.risk_score
        }

    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建案例失败: {e}")

@router.get("/cases/{user_id}")
async def get_user_cases(
    user_id: int,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取用户的诈骗案例列表"""
    
    try:
        cases = db.query(FraudCase).filter(
            FraudCase.user_id == user_id
        ).order_by(FraudCase.detection_timestamp.desc()).limit(limit).all()
        
        return {
            "cases": [
                {
                    "case_id": case.case_id,
                    "case_name": case.case_name,
                    "fraud_type": case.fraud_type,
                    "risk_score": case.risk_score,
                    "status": case.status,
                    "detection_timestamp": case.detection_timestamp,
                    "resolution_timestamp": case.resolution_timestamp,
                    "assigned_agent": case.assigned_agent
                }
                for case in cases
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取案例列表失败: {e}")

@router.post("/batch")
async def batch_analysis(
    background_tasks: BackgroundTasks,
    file_urls: List[str],
    user_id: int,
    analysis_config: Dict[str, Any] = None,
    db: Session = Depends(get_db)
):
    """批量分析文件"""

    raise HTTPException(status_code=501, detail="批量URL分析暂未开放，请使用单文件上传接口")

async def _analyze_file_background(
    analysis_id: str,
    evidence_id: int,
    analysis_types: List[str],
    user_id: int,
    case_name: str,
    fraud_type: str,
    file_path: str,
    file_extension: str,
):
    """后台分析任务 - 软著申请：异步文件处理"""

    started_at = time.perf_counter()
    db_gen = get_db()
    db = next(db_gen)

    try:
        await _set_task(analysis_id, {"started_at": _iso_now(), "status": "processing"})

        is_audio_file = file_extension.lower() in set(settings.allowed_audio_formats)
        if is_audio_file:
            results = await _analyze_audio_file(file_path)
        else:
            results = await _analyze_text_file(file_path)

        fraud_detection = results.get("fraud_detection", {})
        transcription = results.get("transcription", {})
        key_features = results.get("key_features", {})

        evidence = db.query(AudioEvidence).filter(AudioEvidence.evidence_id == evidence_id).first()
        if not evidence:
            raise RuntimeError(f"证据记录不存在: evidence_id={evidence_id}")

        risk_score = _safe_float(fraud_detection.get("risk_score", 0.0))
        risk_level = str(fraud_detection.get("risk_level", _risk_level(risk_score)))

        detection = DetectionResult(
            evidence_id=evidence_id,
            timestamp=datetime.utcnow(),
            asr_transcript=transcription.get("text", ""),
            qwen_logits={"analysis": key_features},
            risk_label=risk_level,
            risk_score=risk_score,
            sentiment_score=_safe_float(key_features.get("voice_signal", 0.0)),
            urgency_score=_safe_float(key_features.get("keyword_score", 0.0)),
            manipulation_score=_safe_float(key_features.get("qwen_score", 0.0)),
            processing_time_ms=(time.perf_counter() - started_at) * 1000.0,
            model_version="analysis-pipeline-v1",
        )

        db.add(detection)

        evidence.processing_status = "completed"
        evidence.transcription = transcription.get("text", "")
        evidence.fraud_indicators = fraud_detection.get("fraud_indicators", [])

        linked_case = db.query(FraudCase).filter(FraudCase.case_id == evidence.case_id).first()
        if linked_case:
            linked_case.risk_score = risk_score
            linked_case.status = "investigating" if risk_score >= settings.risk_threshold_low else "resolved"
            linked_case.fraud_type = fraud_type or linked_case.fraud_type
            linked_case.case_metadata = {
                "analysis_id": analysis_id,
                "analysis_types": analysis_types,
                "risk_level": risk_level,
                "updated_at": _iso_now(),
            }

        db.commit()

        await _set_task(
            analysis_id,
            {
                "status": "completed",
                "completed_at": _iso_now(),
                "processing_time_ms": (time.perf_counter() - started_at) * 1000.0,
                "results": results,
                "error": None,
            },
        )

        logger.info("离线分析任务完成: analysis_id=%s", analysis_id)

    except Exception as e:
        db.rollback()

        try:
            evidence = db.query(AudioEvidence).filter(AudioEvidence.evidence_id == evidence_id).first()
            if evidence:
                evidence.processing_status = "failed"
                db.commit()
        except Exception:
            db.rollback()

        await _set_task(
            analysis_id,
            {
                "status": "failed",
                "completed_at": _iso_now(),
                "processing_time_ms": (time.perf_counter() - started_at) * 1000.0,
                "error": str(e),
                "results": None,
            },
        )
        logger.error("后台分析任务失败 %s: %s", analysis_id, e)

    finally:
        db_gen.close()

async def _analyze_url_background(task_id: str, file_url: str, config: Dict[str, Any]):
    """后台URL分析任务"""

    logger.warning("URL分析任务尚未实现: task_id=%s, file_url=%s", task_id, file_url)

def _is_allowed_file(filename: str) -> bool:
    """检查文件类型是否允许"""
    if not filename:
        return False
    
    file_extension = os.path.splitext(filename)[1].lower()
    return (
        file_extension in settings.allowed_audio_formats or
        file_extension in settings.allowed_text_formats
    )