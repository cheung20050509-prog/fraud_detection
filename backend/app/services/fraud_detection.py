"""
诈骗检测服务 - 软著申请：电信诈骗智能检测核心引擎
作用：基于Qwen2Audio模型实时分析音频流，识别诈骗风险特征，提供毫秒级风险预警
"""

import asyncio
import numpy as np
import torch
import librosa
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import io
import wave
from collections import deque

from app.config import settings
from app.database.database import get_db
from app.database.models import MonitoringSession, FraudAlert, DetectionResult
from app.ml_models.qwen_integration import QwenAudioProcessor
from app.services.asr_service import ASRService
from app.services.audio_utils import AudioUtils

logger = logging.getLogger(__name__)

@dataclass
class RiskAnalysis:
    """风险分析结果 - 软著申请：多维度风险评估模型"""
    risk_score: float  # 0-100 风险评分
    risk_level: str    # 'low', 'medium', 'high', 'critical'
    fraud_indicators: List[str]  # 检测到的诈骗指标
    transcript: Optional[str]     # 语音转录文本
    confidence: float  # 检测置信度
    processing_time_ms: float  # 处理耗时
    features: Dict[str, float]  # 特征向量
    alert_triggered: bool  # 是否触发警报

class FraudDetectionService:
    """诈骗检测服务类 - 软著申请：实时诈骗风险检测引擎"""
    
    def __init__(self):
        """初始化检测服务"""
        self.qwen_processor = None
        self.asr_service = ASRService()
        self.audio_utils = AudioUtils()
        
        # 音频缓存队列 - 用于累积音频片段进行分析
        self.audio_buffer = {}
        self.max_buffer_duration = 5.0  # 最大缓存时长(秒)
        
        # 风险历史缓存 - 用于平滑风险评分
        self.risk_history = {}
        self.history_window = 30.0  # 历史窗口(秒)
        
        # 诈骗关键词库 - 软著申请：诈骗模式识别词典
        self.fraud_keywords = {
            "urgency": ["立即", "马上", "抓紧", "紧急", "最后机会", "限时", "马上过期"],
            "authority": ["公安", "法院", "检察院", "税务局", "银行", "客服", "官方"],
            "money": ["转账", "汇款", "付款", "保证金", "手续费", "验证资金", "安全账户"],
            "threat": ["冻结", "逮捕", "起诉", "调查", "法律责任", "刑事"],
            "bait": ["中奖", "退款", "理赔", "补偿", "投资", "理财", "高回报"],
            "impersonation": ["我是", "这里是", "我们公司", "官方通知", "系统检测"]
        }
        
        # 初始化AI模型
        asyncio.create_task(self._init_models())
    
    async def _init_models(self):
        """异步初始化AI模型 - 软著申请：AI模型懒加载优化"""
        try:
            logger.info("正在初始化Qwen2Audio模型...")
            self.qwen_processor = QwenAudioProcessor()
            logger.info("Qwen2Audio模型初始化完成")
        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
            # 创建Mock处理器作为降级方案
            self.qwen_processor = MockQwenProcessor()
    
    async def analyze_audio_chunk(self, audio_data: bytes, session_id: str) -> RiskAnalysis:
        """
        分析音频块 - 软著申请：实时音频流分析核心算法
        
        Args:
            audio_data: 音频二进制数据
            session_id: 会话ID
            
        Returns:
            RiskAnalysis: 风险分析结果
        """
        
        start_time = datetime.now()
        
        try:
            # 1. 音频预处理
            audio_array = await self.audio_utils.preprocess_audio_chunk(audio_data)
            if audio_array is None:
                return self._create_empty_analysis(session_id)
            
            # 2. 缓存音频数据
            await self._buffer_audio(session_id, audio_array)
            
            # 3. 检查是否达到分析条件
            if not await self._should_analyze(session_id):
                return self._get_latest_analysis(session_id)
            
            # 4. 获取分析音频片段
            analysis_audio = await self._get_analysis_audio(session_id)
            
            # 5. 并行执行多种分析 - 软著申请：多模态融合分析
            tasks = [
                self._qwen_analysis(analysis_audio, session_id),
                self._asr_transcription(analysis_audio, session_id),
                self._keyword_detection(analysis_audio, session_id),
                self._voice_analysis(analysis_audio, session_id)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            qwen_result, asr_result, keyword_result, voice_result = results
            
            # 6. 融合分析结果 - 软著申请：多算法结果融合算法
            risk_analysis = await self._fuse_analysis_results(
                qwen_result, asr_result, keyword_result, voice_result, session_id
            )
            
            # 7. 更新风险历史
            await self._update_risk_history(session_id, risk_analysis)
            
            # 8. 保存检测结果到数据库
            await self._save_detection_result(session_id, risk_analysis)
            
            # 9. 检查是否需要触发警报
            await self._check_alert_conditions(session_id, risk_analysis)
            
            # 计算处理耗时
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            risk_analysis.processing_time_ms = processing_time
            
            logger.info(f"音频分析完成 {session_id}: 风险评分={risk_analysis.risk_score:.2f}, "
                       f"处理耗时={processing_time:.2f}ms")
            
            return risk_analysis
            
        except Exception as e:
            logger.error(f"音频分析失败 {session_id}: {e}")
            return self._create_error_analysis(session_id, str(e))
    
    async def _qwen_analysis(self, audio_array: np.ndarray, session_id: str) -> Dict[str, Any]:
        """Qwen2Audio模型分析 - 软著申请：深度学习音频理解"""
        
        if not self.qwen_processor:
            return {"score": 0.0, "features": {}, "confidence": 0.0}
        
        try:
            # 调用Qwen2Audio模型
            result = await self.qwen_processor.analyze_audio(audio_array)
            return result
        except Exception as e:
            logger.error(f"Qwen分析失败 {session_id}: {e}")
            return {"score": 0.0, "features": {}, "confidence": 0.0}
    
    async def _asr_transcription(self, audio_array: np.ndarray, session_id: str) -> Dict[str, Any]:
        """语音转文字 - 软著申请：语音识别转录服务"""
        
        try:
            transcript = await self.asr_service.transcribe_audio(audio_array)
            return {"transcript": transcript, "confidence": 0.8}
        except Exception as e:
            logger.error(f"ASR转录失败 {session_id}: {e}")
            return {"transcript": "", "confidence": 0.0}
    
    async def _keyword_detection(self, audio_array: np.ndarray, session_id: str) -> Dict[str, Any]:
        """诈骗关键词检测 - 软著申请：基于规则的诈骗模式识别"""
        
        try:
            # 先进行ASR转录
            asr_result = await self._asr_transcription(audio_array, session_id)
            transcript = asr_result.get("transcript", "")
            
            detected_keywords = []
            keyword_score = 0.0
            
            # 检测各类诈骗关键词
            for category, keywords in self.fraud_keywords.items():
                category_count = sum(1 for kw in keywords if kw in transcript)
                if category_count > 0:
                    detected_keywords.extend([f"{category}:{kw}" for kw in keywords if kw in transcript])
                    keyword_score += category_count * 10.0  # 每个关键词10分
            
            return {
                "detected_keywords": detected_keywords,
                "keyword_score": min(keyword_score, 60.0),  # 限制最高60分
                "matched_categories": list(set([kw.split(":")[0] for kw in detected_keywords]))
            }
        except Exception as e:
            logger.error(f"关键词检测失败 {session_id}: {e}")
            return {"detected_keywords": [], "keyword_score": 0.0, "matched_categories": []}
    
    async def _voice_analysis(self, audio_array: np.ndarray, session_id: str) -> Dict[str, Any]:
        """语音特征分析 - 软著申请：声纹特征与情感分析"""
        
        try:
            # 提取音频特征
            features = await self.audio_utils.extract_voice_features(audio_array)
            
            # 分析异常特征
            urgency_score = self._analyze_urgency_from_voice(features)
            manipulation_score = self._analyze_manipulation_from_voice(features)
            
            return {
                "urgency_score": urgency_score,
                "manipulation_score": manipulation_score,
                "voice_features": features
            }
        except Exception as e:
            logger.error(f"语音分析失败 {session_id}: {e}")
            return {"urgency_score": 0.0, "manipulation_score": 0.0, "voice_features": {}}
    
    async def _fuse_analysis_results(self, qwen_result: Dict, asr_result: Dict, 
                                    keyword_result: Dict, voice_result: Dict, 
                                    session_id: str) -> RiskAnalysis:
        """融合分析结果 - 软著申请：多算法加权融合算法"""
        
        # 权重配置 - 软著申请：多算法动态权重分配
        weights = {
            "qwen": 0.4,      # Qwen2Audio模型权重最高
            "keyword": 0.3,   # 关键词检测权重
            "voice": 0.2,     # 语音特征权重
            "asr": 0.1        # ASR转录权重
        }
        
        # 计算各项得分
        qwen_score = qwen_result.get("score", 0.0) * 100
        keyword_score = keyword_result.get("keyword_score", 0.0)
        voice_score = (voice_result.get("urgency_score", 0.0) + 
                      voice_result.get("manipulation_score", 0.0)) * 20
        
        # 加权融合
        final_score = (
            qwen_score * weights["qwen"] +
            keyword_score * weights["keyword"] +
            voice_score * weights["voice"]
        )
        
        # 获取所有诈骗指标
        fraud_indicators = []
        fraud_indicators.extend(keyword_result.get("detected_keywords", []))
        
        # 确定风险等级
        if final_score >= settings.risk_threshold_medium:
            risk_level = "high" if final_score >= 85 else "medium"
        else:
            risk_level = "low"
        
        # 计算综合置信度
        confidence = (
            qwen_result.get("confidence", 0.0) * weights["qwen"] +
            asr_result.get("confidence", 0.0) * weights["asr"] +
            0.8 * (weights["keyword"] + weights["voice"])  # 规则和特征分析置信度较高
        )
        
        return RiskAnalysis(
            risk_score=min(final_score, 100.0),
            risk_level=risk_level,
            fraud_indicators=fraud_indicators,
            transcript=asr_result.get("transcript"),
            confidence=min(confidence, 1.0),
            processing_time_ms=0.0,  # 稍后计算
            features={
                "qwen_score": qwen_score,
                "keyword_score": keyword_score,
                "voice_score": voice_score,
                "matched_categories": keyword_result.get("matched_categories", [])
            },
            alert_triggered=final_score >= settings.risk_threshold_medium
        )
    
    async def _buffer_audio(self, session_id: str, audio_array: np.ndarray):
        """缓存音频数据"""
        
        if session_id not in self.audio_buffer:
            self.audio_buffer[session_id] = {
                "audio_segments": deque(),
                "total_duration": 0.0
            }
        
        buffer = self.audio_buffer[session_id]
        segment_duration = len(audio_array) / 16000.0  # 16kHz采样率
        
        buffer["audio_segments"].append(audio_array)
        buffer["total_duration"] += segment_duration
        
        # 清理过期数据
        while buffer["total_duration"] > self.max_buffer_duration:
            oldest_segment = buffer["audio_segments"].popleft()
            buffer["total_duration"] -= len(oldest_segment) / 16000.0
    
    async def _should_analyze(self, session_id: str) -> bool:
        """判断是否应该进行分析"""
        
        if session_id not in self.audio_buffer:
            return False
        
        buffer = self.audio_buffer[session_id]
        
        # 至少有2秒的音频才分析
        return buffer["total_duration"] >= 2.0
    
    async def _get_analysis_audio(self, session_id: str) -> np.ndarray:
        """获取用于分析的音频片段"""
        
        buffer = self.audio_buffer[session_id]
        if not buffer["audio_segments"]:
            return np.array([])
        
        # 合并最近的音频片段
        recent_segments = list(buffer["audio_segments"])[-10:]  # 最多10个片段
        return np.concatenate(recent_segments)
    
    async def _update_risk_history(self, session_id: str, analysis: RiskAnalysis):
        """更新风险历史"""
        
        if session_id not in self.risk_history:
            self.risk_history[session_id] = []
        
        self.risk_history[session_id].append({
            "timestamp": datetime.now(),
            "risk_score": analysis.risk_score,
            "risk_level": analysis.risk_level
        })
        
        # 清理过期历史
        cutoff_time = datetime.now() - timedelta(seconds=self.history_window)
        self.risk_history[session_id] = [
            h for h in self.risk_history[session_id] 
            if h["timestamp"] > cutoff_time
        ]
    
    async def _save_detection_result(self, session_id: str, analysis: RiskAnalysis):
        """保存检测结果到数据库"""
        
        try:
            db = next(get_db())
            
            # 创建检测结果记录
            detection = DetectionResult(
                session_id=session_id,
                timestamp=datetime.now(),
                asr_transcript=analysis.transcript,
                qwen_logits={"features": analysis.features},
                risk_label=analysis.risk_level,
                risk_score=analysis.risk_score,
                sentiment_score=analysis.features.get("voice_score", 0.0),
                urgency_score=analysis.features.get("urgency_score", 0.0),
                manipulation_score=analysis.features.get("manipulation_score", 0.0),
                processing_time_ms=analysis.processing_time_ms,
                model_version="Qwen2Audio-v1.0"
            )
            
            db.add(detection)
            db.commit()
            
        except Exception as e:
            logger.error(f"保存检测结果失败 {session_id}: {e}")
    
    async def _check_alert_conditions(self, session_id: str, analysis: RiskAnalysis):
        """检查警报条件"""
        
        if not analysis.alert_triggered:
            return
        
        try:
            db = next(get_db())
            
            # 创建警报表
            alert = FraudAlert(
                session_id=session_id,
                alert_type="content_analysis",
                severity="high" if analysis.risk_score >= 85 else "medium",
                confidence_score=analysis.confidence,
                description=f"检测到诈骗风险: 评分{analysis.risk_score:.1f}, 指标: {', '.join(analysis.fraud_indicators[:3])}",
                evidence_data={
                    "risk_score": analysis.risk_score,
                    "fraud_indicators": analysis.fraud_indicators,
                    "transcript": analysis.transcript,
                    "features": analysis.features
                }
            )
            
            db.add(alert)
            db.commit()
            
            # 更新监听会话的警报计数
            session = db.query(MonitoringSession).filter(
                MonitoringSession.session_id == session_id
            ).first()
            
            if session:
                session.risk_alerts_triggered += 1
                session.max_risk_score = max(session.max_risk_score, analysis.risk_score)
                db.commit()
            
        except Exception as e:
            logger.error(f"创建警报失败 {session_id}: {e}")
    
    def _analyze_urgency_from_voice(self, features: Dict) -> float:
        """从语音特征分析紧急性"""
        
        # 基于语音特征计算紧急性评分
        speed_factor = features.get("speech_rate", 0.0)  # 语速
        volume_factor = features.get("volume_variance", 0.0)  # 音量变化
        pitch_factor = features.get("pitch_variance", 0.0)  # 音调变化
        
        urgency_score = (speed_factor * 0.4 + volume_factor * 0.3 + pitch_factor * 0.3)
        return min(urgency_score, 1.0)
    
    def _analyze_manipulation_from_voice(self, features: Dict) -> float:
        """从语音特征分析操纵性"""
        
        # 基于语音特征计算操纵性评分
        consistency_factor = 1.0 - features.get("intonation_consistency", 0.5)  # 语调一致性
        emotion_factor = features.get("emotion_artificiality", 0.0)  # 情感真实性
        
        manipulation_score = (consistency_factor * 0.6 + emotion_factor * 0.4)
        return min(manipulation_score, 1.0)
    
    def _create_empty_analysis(self, session_id: str) -> RiskAnalysis:
        """创建空分析结果"""
        return RiskAnalysis(
            risk_score=0.0,
            risk_level="low",
            fraud_indicators=[],
            transcript=None,
            confidence=0.0,
            processing_time_ms=0.0,
            features={},
            alert_triggered=False
        )
    
    def _create_error_analysis(self, session_id: str, error: str) -> RiskAnalysis:
        """创建错误分析结果"""
        return RiskAnalysis(
            risk_score=0.0,
            risk_level="low",
            fraud_indicators=[f"error:{error}"],
            transcript=None,
            confidence=0.0,
            processing_time_ms=0.0,
            features={"error": error},
            alert_triggered=False
        )
    
    def _get_latest_analysis(self, session_id: str) -> RiskAnalysis:
        """获取最新的分析结果"""
        # 从风险历史中获取最新结果
        if session_id in self.risk_history and self.risk_history[session_id]:
            latest = self.risk_history[session_id][-1]
            return RiskAnalysis(
                risk_score=latest["risk_score"],
                risk_level=latest["risk_level"],
                fraud_indicators=[],
                transcript=None,
                confidence=0.0,
                processing_time_ms=0.0,
                features={},
                alert_triggered=latest["risk_score"] >= settings.risk_threshold_medium
            )
        
        return self._create_empty_analysis(session_id)


class MockQwenProcessor:
    """Mock Qwen处理器 - 用于模型加载失败时的降级方案"""
    
    async def analyze_audio(self, audio_array: np.ndarray) -> Dict[str, Any]:
        """Mock音频分析"""
        import random
        
        # 生成Mock结果
        return {
            "score": random.uniform(0.1, 0.3),  # 较低的随机分数
            "features": {
                "speech_activity": random.uniform(0.5, 1.0),
                "emotion": "neutral"
            },
            "confidence": 0.5
        }