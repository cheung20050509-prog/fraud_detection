"""
诈骗检测服务 - 软著申请：电信诈骗智能检测核心引擎
作用：基于Qwen2Audio模型实时分析音频流，识别诈骗风险特征，提供毫秒级风险预警
"""

import asyncio
import numpy as np
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from app.config import settings
from app.database.database import get_db
from app.database.models import MonitoringSession, FraudAlert, DetectionResult
from app.ml_models.qwen_integration import QwenAudioProcessor, model_manager
from app.services.asr_service import ASRService, shared_asr_service
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
    
    def __init__(
        self,
        asr_service: Optional[ASRService] = None,
        qwen_processor: Optional[QwenAudioProcessor] = None,
    ):
        """初始化检测服务"""
        self.qwen_processor = qwen_processor or model_manager.get_processor()
        self.strict_no_fallback = bool(getattr(settings, "strict_no_fallback", True))
        self._initialized = False
        self._init_error: Optional[str] = None
        self._init_lock = asyncio.Lock()

        self.asr_service = asr_service or shared_asr_service
        self.audio_utils = AudioUtils()
        
        # 音频缓存队列 - 用于累积音频片段进行分析
        self.audio_buffer = {}
        self.max_buffer_duration = 5.0  # 最大缓存时长(秒)
        
        # 风险历史缓存 - 用于平滑风险评分
        self.risk_history = {}
        self.history_window = 30.0  # 历史窗口(秒)

        # 转录历史缓存 - 用于滚动文本窗口和关键词稳态检测
        self.transcript_history = {}
        self.transcript_window = 15.0  # 最近15秒转录窗口
        
        # 诈骗关键词库 - 软著申请：诈骗模式识别词典
        self.fraud_keywords = {
            "urgency": ["立即", "马上", "抓紧", "紧急", "最后机会", "限时", "马上过期"],
            "authority": ["公安", "法院", "检察院", "税务局", "银行", "客服", "官方"],
            "money": ["转账", "汇款", "付款", "保证金", "手续费", "验证资金", "安全账户"],
            "threat": ["冻结", "逮捕", "起诉", "调查", "法律责任", "刑事"],
            "bait": ["中奖", "退款", "理赔", "补偿", "投资", "理财", "高回报"],
            "impersonation": ["我是", "这里是", "我们公司", "官方通知", "系统检测"]
        }
    
    async def _init_models(self):
        """异步初始化AI模型 - 软著申请：AI模型懒加载优化"""
        async with self._init_lock:
            if self._initialized:
                return

            try:
                if self.qwen_processor is None:
                    self.qwen_processor = model_manager.get_processor()
                if self.qwen_processor is None:
                    raise RuntimeError("Qwen2Audio处理器不可用")

                self._init_error = getattr(self.qwen_processor, "_init_error", None)
                self._initialized = True
            except Exception as e:
                self.qwen_processor = None
                self._init_error = str(e)
                self._initialized = True
                logger.error("模型初始化失败: %s", e)
                if self.strict_no_fallback:
                    raise RuntimeError(f"Qwen2Audio初始化失败: {e}") from e

    async def _ensure_runtime_models_ready(self):
        """顺序预热模型，避免Whisper/Qwen并发初始化触发meta张量问题。"""

        if self.qwen_processor is None:
            message = self._init_error or "Qwen2Audio处理器未初始化"
            if self.strict_no_fallback:
                raise RuntimeError(message)
        else:
            qwen_needs_init = (
                not bool(getattr(self.qwen_processor, "_initialized", False))
                or getattr(self.qwen_processor, "model", None) is None
                or getattr(self.qwen_processor, "processor", None) is None
            )
            if qwen_needs_init:
                await self.qwen_processor._async_init()

            if self.strict_no_fallback:
                qwen_backend = getattr(self.qwen_processor, "model_backend", "unknown")
                qwen_error = getattr(self.qwen_processor, "_init_error", None)
                if qwen_backend != "real":
                    raise RuntimeError(f"Qwen2Audio不可用: {qwen_error or qwen_backend}")

        await self.asr_service.warmup_model()
    
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
            await self._init_models()

            # 1. 音频预处理
            audio_array = await self.audio_utils.preprocess_audio_chunk(
                audio_data,
                prefer_container_decode=True,
            )
            if audio_array is None or len(audio_array) == 0:
                if self.strict_no_fallback:
                    raise RuntimeError("音频预处理失败或结果为空")
                return self._create_empty_analysis(session_id)
            
            # 2. 缓存音频数据
            await self._buffer_audio(session_id, audio_array)
            
            # 3. 检查是否达到分析条件
            if not await self._should_analyze(session_id):
                return self._get_latest_analysis(session_id)
            
            # 4. 获取分析音频片段
            analysis_audio = await self._get_analysis_audio(session_id)

            # 5. 预热模型（串行）并执行分析，避免并发初始化竞态。
            await self._ensure_runtime_models_ready()

            asr_result = await self._asr_transcription(analysis_audio, session_id)
            transcript_text = asr_result.get("transcript") if isinstance(asr_result, dict) else ""
            await self._update_transcript_history(session_id, transcript_text)
            rolling_transcript = await self._get_rolling_transcript(session_id)
            
            # 并行执行其余分析 - 软著申请：多模态融合分析
            tasks = [
                self._qwen_analysis(analysis_audio, session_id),
                self._keyword_detection(analysis_audio, session_id, transcript=rolling_transcript),
                self._voice_analysis(analysis_audio, session_id)
            ]

            qwen_result, keyword_result, voice_result = await asyncio.gather(*tasks)
            
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
            logger.error("音频分析失败 %s: %s", session_id, e, exc_info=True)
            if self.strict_no_fallback:
                raise RuntimeError(f"音频分析失败: {e}") from e
            return self._create_error_analysis(session_id, str(e))
    
    async def _qwen_analysis(self, audio_array: np.ndarray, session_id: str) -> Dict[str, Any]:
        """Qwen2Audio模型分析 - 软著申请：深度学习音频理解"""
        
        if not self.qwen_processor:
            message = self._init_error or "Qwen2Audio处理器未初始化"
            if self.strict_no_fallback:
                raise RuntimeError(message)
            return {"score": 0.0, "features": {}, "confidence": 0.0}
        
        try:
            # 调用Qwen2Audio模型
            result = await self.qwen_processor.analyze_audio(audio_array)
            if not isinstance(result, dict):
                raise RuntimeError("Qwen2Audio返回结果格式无效")
            return result
        except Exception as e:
            logger.error(f"Qwen分析失败 {session_id}: {e}")
            if self.strict_no_fallback:
                raise RuntimeError(f"Qwen分析失败: {e}") from e
            return {"score": 0.0, "features": {}, "confidence": 0.0}
    
    async def _asr_transcription(self, audio_array: np.ndarray, session_id: str) -> Dict[str, Any]:
        """语音转文字 - 软著申请：语音识别转录服务"""
        
        try:
            transcript = await self.asr_service.transcribe_audio(audio_array, language="zh")
            if transcript:
                return {"transcript": transcript, "confidence": 0.8, "language": "zh"}

            transcript = await self.asr_service.transcribe_audio(audio_array, language=None)
            if transcript:
                return {"transcript": transcript, "confidence": 0.7, "language": "auto"}

            duration = float(len(audio_array) / max(1, settings.audio_sample_rate))
            logger.info("监护ASR未识别到清晰文本 %s: audio_duration=%.2fs", session_id, duration)
            return {"transcript": "", "confidence": 0.0, "language": None}
        except Exception as e:
            logger.error(f"ASR转录失败 {session_id}: {e}")
            if self.strict_no_fallback:
                raise RuntimeError(f"ASR转录失败: {e}") from e
            return {"transcript": "", "confidence": 0.0}
    
    async def _keyword_detection(
        self,
        audio_array: np.ndarray,
        session_id: str,
        transcript: Optional[str] = None,
    ) -> Dict[str, Any]:
        """诈骗关键词检测 - 软著申请：基于规则的诈骗模式识别"""
        
        try:
            if transcript is None:
                # 回退路径：单独执行关键词检测时，内部完成ASR。
                asr_result = await self._asr_transcription(audio_array, session_id)
                transcript = asr_result.get("transcript", "")

            transcript = transcript or ""
            
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
            if self.strict_no_fallback:
                raise RuntimeError(f"关键词检测失败: {e}") from e
            return {"detected_keywords": [], "keyword_score": 0.0, "matched_categories": []}
    
    async def _voice_analysis(self, audio_array: np.ndarray, session_id: str) -> Dict[str, Any]:
        """语音特征分析 - 软著申请：声纹特征与情感分析"""
        
        try:
            # 提取音频特征
            features = await self.audio_utils.extract_voice_features(audio_array)
            if self.strict_no_fallback and not features:
                raise RuntimeError("语音特征为空，严格模式禁止继续融合")
            
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
            if self.strict_no_fallback:
                raise RuntimeError(f"语音特征提取失败: {e}") from e
            return {"urgency_score": 0.0, "manipulation_score": 0.0, "voice_features": {}}

    def _normalize_percentage_score(self, score: Any) -> float:
        """将不同量纲的分数统一归一到0-100。"""

        try:
            numeric_score = float(score)
        except (TypeError, ValueError):
            return 0.0

        if numeric_score <= 1.0:
            numeric_score *= 100.0

        return max(0.0, min(100.0, numeric_score))

    def _normalize_keyword_score(self, keyword_score: Any) -> float:
        """关键词检测原始分值范围为0-60，这里映射到0-100。"""

        try:
            raw_keyword_score = float(keyword_score)
        except (TypeError, ValueError):
            return 0.0

        raw_keyword_score = max(0.0, min(60.0, raw_keyword_score))
        return (raw_keyword_score / 60.0) * 100.0

    def _normalize_voice_score(self, urgency_score: Any, manipulation_score: Any) -> float:
        """语音风险由紧急性和操纵性共同构成，统一映射到0-100。"""

        normalized_urgency = self._normalize_percentage_score(urgency_score)
        normalized_manipulation = self._normalize_percentage_score(manipulation_score)
        return (normalized_urgency * 0.5) + (normalized_manipulation * 0.5)
    
    async def _fuse_analysis_results(self, qwen_result: Dict, asr_result: Dict, 
                                    keyword_result: Dict, voice_result: Dict, 
                                    session_id: str) -> RiskAnalysis:
        """融合分析结果 - 软著申请：多算法加权融合算法"""

        if self.strict_no_fallback:
            input_map = {
                "qwen_result": qwen_result,
                "asr_result": asr_result,
                "keyword_result": keyword_result,
                "voice_result": voice_result,
            }
            invalid_inputs = [name for name, payload in input_map.items() if not isinstance(payload, dict)]
            if invalid_inputs:
                raise RuntimeError(f"融合输入结果格式非法: {', '.join(invalid_inputs)}")
        
        # 风险分与置信度分别融合，避免将ASR识别置信度错误算进诈骗风险。
        risk_weights = {
            "qwen": 0.45,
            "keyword": 0.35,
            "voice": 0.20,
        }
        confidence_weights = {
            "qwen": 0.4,
            "asr": 0.1,
            "keyword": 0.25,
            "voice": 0.25,
        }
        
        # 计算各项得分，并统一到0-100后再融合。
        qwen_score = self._normalize_percentage_score(qwen_result.get("score", 0.0))
        raw_keyword_score = keyword_result.get("keyword_score", 0.0)
        keyword_score = self._normalize_keyword_score(raw_keyword_score)
        urgency_score = voice_result.get("urgency_score", 0.0)
        manipulation_score = voice_result.get("manipulation_score", 0.0)
        normalized_urgency_score = self._normalize_percentage_score(urgency_score)
        normalized_manipulation_score = self._normalize_percentage_score(manipulation_score)
        voice_score = self._normalize_voice_score(urgency_score, manipulation_score)
        
        # 加权融合
        final_score = (
            qwen_score * risk_weights["qwen"] +
            keyword_score * risk_weights["keyword"] +
            voice_score * risk_weights["voice"]
        )
        
        # 获取所有诈骗指标
        fraud_indicators = []
        fraud_indicators.extend([str(item) for item in qwen_result.get("fraud_indicators", []) if item])
        fraud_indicators.extend(keyword_result.get("detected_keywords", []))
        fraud_indicators = list(dict.fromkeys(fraud_indicators))
        
        # 确定风险等级
        if final_score >= settings.risk_threshold_medium:
            risk_level = "high" if final_score >= 85 else "medium"
        else:
            risk_level = "low"
        
        # 计算综合置信度
        confidence = (
            qwen_result.get("confidence", 0.0) * confidence_weights["qwen"] +
            asr_result.get("confidence", 0.0) * confidence_weights["asr"] +
            0.8 * (confidence_weights["keyword"] + confidence_weights["voice"])
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
                "urgency_score": normalized_urgency_score,
                "manipulation_score": normalized_manipulation_score,
                "raw_keyword_score": raw_keyword_score,
                "raw_urgency_score": urgency_score,
                "raw_manipulation_score": manipulation_score,
                "matched_categories": keyword_result.get("matched_categories", [])
            },
            alert_triggered=final_score >= settings.risk_threshold_medium
        )
    
    async def _buffer_audio(self, session_id: str, audio_array: np.ndarray):
        """缓存音频数据"""

        sample_rate = max(1, int(getattr(settings, "audio_sample_rate", 16000)))
        
        if session_id not in self.audio_buffer:
            self.audio_buffer[session_id] = {
                "audio_segments": deque(),
                "total_duration": 0.0
            }
        
        buffer = self.audio_buffer[session_id]
        segment_duration = len(audio_array) / float(sample_rate)

        # 如果单个片段已经超过窗口上限，保留最新的窗口长度，而不是整段入队后又被完全清空。
        if segment_duration >= self.max_buffer_duration:
            max_samples = int(self.max_buffer_duration * sample_rate)
            trimmed_audio = np.asarray(audio_array[-max_samples:], dtype=np.float32)
            buffer["audio_segments"] = deque([trimmed_audio])
            buffer["total_duration"] = len(trimmed_audio) / float(sample_rate)
            return
        
        buffer["audio_segments"].append(audio_array)
        buffer["total_duration"] += segment_duration
        
        # 清理过期数据
        while buffer["total_duration"] > self.max_buffer_duration:
            oldest_segment = buffer["audio_segments"].popleft()
            buffer["total_duration"] -= len(oldest_segment) / float(sample_rate)

    def _normalize_transcript_text(self, transcript: Optional[str]) -> str:
        """规范化转录文本，避免空白差异干扰片段合并。"""

        return " ".join(str(transcript or "").split())

    def _merge_transcript_text(self, base_text: str, new_text: str) -> str:
        """按最大重叠后缀/前缀合并转录片段，减少滚动窗口中的重复文字。"""

        normalized_base = self._normalize_transcript_text(base_text)
        normalized_new = self._normalize_transcript_text(new_text)

        if not normalized_base:
            return normalized_new
        if not normalized_new:
            return normalized_base
        if normalized_base.endswith(normalized_new) or normalized_new in normalized_base:
            return normalized_base

        max_overlap = min(len(normalized_base), len(normalized_new))
        for overlap in range(max_overlap, 1, -1):
            if normalized_base[-overlap:] == normalized_new[:overlap]:
                return normalized_base + normalized_new[overlap:]

        needs_space = (
            normalized_base[-1].isascii()
            and normalized_base[-1].isalnum()
            and normalized_new[0].isascii()
            and normalized_new[0].isalnum()
        )
        separator = " " if needs_space else ""
        return normalized_base + separator + normalized_new

    async def _update_transcript_history(self, session_id: str, transcript: Optional[str]):
        """更新最近转录窗口，为关键词检测提供连续上下文。"""

        if session_id not in self.transcript_history:
            self.transcript_history[session_id] = deque()

        history = self.transcript_history[session_id]
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=self.transcript_window)

        normalized_transcript = self._normalize_transcript_text(transcript)
        if normalized_transcript:
            history.append({
                "timestamp": now,
                "text": normalized_transcript,
            })

        while history and history[0]["timestamp"] <= cutoff_time:
            history.popleft()

    async def _get_rolling_transcript(self, session_id: str) -> str:
        """返回最近窗口内的连续转录文本。"""

        history = self.transcript_history.get(session_id)
        if not history:
            return ""

        cutoff_time = datetime.now() - timedelta(seconds=self.transcript_window)
        while history and history[0]["timestamp"] <= cutoff_time:
            history.popleft()

        merged_text = ""
        for entry in history:
            merged_text = self._merge_transcript_text(merged_text, entry.get("text", ""))
        return merged_text
    
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

        db_gen = get_db()
        db = next(db_gen)
        try:
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

            monitoring_session = db.query(MonitoringSession).filter(
                MonitoringSession.session_id == session_id
            ).first()
            if monitoring_session:
                monitoring_session.max_risk_score = max(
                    monitoring_session.max_risk_score or 0.0,
                    analysis.risk_score,
                )
                session_data = dict(monitoring_session.session_data or {})
                session_data["last_analysis_at"] = datetime.utcnow().isoformat()
                session_data["last_risk_level"] = analysis.risk_level
                rolling_transcript = await self._get_rolling_transcript(session_id)
                if rolling_transcript:
                    session_data["last_transcript"] = rolling_transcript[:200]
                monitoring_session.session_data = session_data

            db.commit()

        except Exception as e:
            db.rollback()
            logger.error(f"保存检测结果失败 {session_id}: {e}")
            if self.strict_no_fallback:
                raise RuntimeError(f"保存检测结果失败: {e}") from e
        finally:
            db_gen.close()
    
    async def _check_alert_conditions(self, session_id: str, analysis: RiskAnalysis):
        """检查警报条件"""
        
        if not analysis.alert_triggered:
            return

        db_gen = get_db()
        db = next(db_gen)
        try:
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
            db.rollback()
            logger.error(f"创建警报失败 {session_id}: {e}")
            if self.strict_no_fallback:
                raise RuntimeError(f"创建警报失败: {e}") from e
        finally:
            db_gen.close()
    
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