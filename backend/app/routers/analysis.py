"""
案例分析模式路由 - 软著申请：文件上传和离线分析API
作用：提供音频文件上传、分析和案例创建的RESTful接口
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import uuid
import aiofiles

from app.database.database import get_db
from app.database.models import FraudCase, AudioEvidence, DetectionResult, User
from app.config import settings
from pydantic import BaseModel

router = APIRouter()

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
        
        # 验证文件大小
        if file.size > settings.max_file_size:
            raise HTTPException(status_code=400, detail="文件大小超过限制")
        
        # 生成唯一文件名
        file_extension = os.path.splitext(file.filename)[1].lower()
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(settings.upload_dir, "audio", unique_filename)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # 创建音频证据记录
        audio_evidence = AudioEvidence(
            file_name=file.filename,
            file_path=file_path,
            file_size=content.__len__(),
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
        background_tasks.add_task(
            _analyze_file_background,
            analysis_id,
            audio_evidence.evidence_id,
            analysis_types_list,
            user_id,
            case_name,
            fraud_type
        )
        
        return {
            "message": "文件上传成功，正在分析中",
            "analysis_id": analysis_id,
            "evidence_id": audio_evidence.evidence_id,
            "file_name": file.filename,
            "file_size": content.__len__(),
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
        # 简化实现，实际应用中需要分析结果表
        # 这里返回模拟结果
        return {
            "analysis_id": analysis_id,
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "results": {
                "fraud_detection": {
                    "risk_score": 75.5,
                    "risk_level": "high",
                    "fraud_indicators": [
                        "紧迫性语言",
                        "身份冒充",
                        "财务要求"
                    ],
                    "confidence": 0.85
                },
                "voice_analysis": {
                    "speaker_count": 2,
                    "voice_characteristics": {
                        "stress_level": 0.7,
                        "emotional_state": "anxious",
                        "speech_rate": "fast"
                    }
                },
                "transcription": {
                    "text": "这里应该是ASR转录的文本内容...",
                    "duration_seconds": 120.5,
                    "language": "zh-CN",
                    "confidence": 0.92
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分析结果失败: {e}")

@router.post("/results/{analysis_id}/create_case")
async def create_case_from_analysis(
    analysis_id: str,
    case_data: CaseCreateRequest,
    db: Session = Depends(get_db)
):
    """从分析结果创建诈骗案例"""
    
    try:
        # 创建诈骗案例
        fraud_case = FraudCase(
            user_id=case_data.user_id if hasattr(case_data, 'user_id') else 1,  # 默认用户ID
            case_name=f"案例_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            fraud_type=case_data.fraud_type,
            risk_score=75.5,  # 应从分析结果获取
            status="pending",
            notes=case_data.notes
        )
        
        db.add(fraud_case)
        db.commit()
        db.refresh(fraud_case)
        
        return {
            "message": "案例创建成功",
            "case_id": fraud_case.case_id,
            "analysis_id": analysis_id,
            "fraud_type": case_data.fraud_type,
            "risk_score": fraud_case.risk_score
        }
        
    except Exception as e:
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
    
    try:
        if not file_urls:
            raise HTTPException(status_code=400, detail="请提供文件URL列表")
        
        batch_id = str(uuid.uuid4())
        analysis_tasks = []
        
        for i, file_url in enumerate(file_urls):
            task_id = f"{batch_id}_{i}"
            analysis_tasks.append({
                "task_id": task_id,
                "file_url": file_url,
                "status": "queued"
            })
            
            # 添加到后台任务队列
            background_tasks.add_task(
                _analyze_url_background,
                task_id,
                file_url,
                analysis_config or {}
            )
        
        return {
            "batch_id": batch_id,
            "message": f"已提交{len(file_urls)}个文件进行批量分析",
            "tasks": analysis_tasks
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量分析失败: {e}")

async def _analyze_file_background(
    analysis_id: str,
    evidence_id: int,
    analysis_types: List[str],
    user_id: int,
    case_name: str,
    fraud_type: str
):
    """后台分析任务 - 软著申请：异步文件处理"""
    
    try:
        # 这里应该调用实际的AI分析服务
        # 模拟分析过程
        import asyncio
        await asyncio.sleep(5)  # 模拟处理时间
        
        # 更新数据库状态
        # 实际应用中需要更新AudioEvidence和处理结果
        
    except Exception as e:
        print(f"后台分析任务失败 {analysis_id}: {e}")

async def _analyze_url_background(task_id: str, file_url: str, config: Dict[str, Any]):
    """后台URL分析任务"""
    
    try:
        # 这里应该下载文件并分析
        import asyncio
        await asyncio.sleep(3)  # 模拟处理时间
        
    except Exception as e:
        print(f"后台URL分析任务失败 {task_id}: {e}")

def _is_allowed_file(filename: str) -> bool:
    """检查文件类型是否允许"""
    if not filename:
        return False
    
    file_extension = os.path.splitext(filename)[1].lower()
    return (
        file_extension in settings.allowed_audio_formats or
        file_extension in settings.allowed_text_formats
    )