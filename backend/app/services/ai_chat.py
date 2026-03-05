"""
AI聊天服务 - 软著申请：智能对话陪练核心逻辑
作用：处理AI陪练模式的文本和音频消息，集成ASR、LLM和TTS
"""

from typing import Dict, Any, Optional
from datetime import datetime
import io
import logging
import os
import wave
import uuid

import numpy as np

from app.config import settings
from app.services.asr_service import ASRService
from app.services.audio_utils import AudioUtils
from app.services.tts_service import TTSService


logger = logging.getLogger(__name__)

class AIChatService:
    """AI聊天服务类 - 软著申请：对话管理系统"""
    
    def __init__(self):
        self.session_contexts = {}  # 会话上下文缓存
        self.asr_service = ASRService()
        self.audio_utils = AudioUtils()
        self.tts_service = TTSService()
        self.qwen_processor = None

        # Qwen模型缺失依赖时不阻塞服务启动，改为运行时降级。
        try:
            from app.ml_models.qwen_integration import QwenAudioProcessor

            self.qwen_processor = QwenAudioProcessor()
        except Exception as e:
            logger.warning("Qwen2Audio处理器初始化失败，将跳过模型打分: %s", e)
        
    async def process_text_message(self, message: str, session_id: str) -> Dict[str, Any]:
        """处理文本消息 - 软著申请：文本对话处理"""
        
        try:
            # 获取或创建会话上下文
            context = self._get_session_context(session_id)

            # 统计用户轮次
            context["user_responses_count"] = context.get("user_responses_count", 0) + 1
            if any(token in message for token in ["诈骗", "可疑", "挂断", "报警", "核实"]):
                context["successful_identifications"] = context.get("successful_identifications", 0) + 1

            fraud_analysis = await self._detect_fraud_indicators(message, None)
            ai_response = await self._generate_ai_response(message, context, fraud_analysis)
            audio_response = await self._text_to_speech(ai_response["text"])
            
            # 记录用户消息
            context["messages"].append({
                "role": "user",
                "content": message,
                "timestamp": datetime.utcnow().isoformat(),
                "risk_score": fraud_analysis.get("risk_score", 0.0),
            })
            
            # 记录AI回复
            context["messages"].append({
                "role": "assistant", 
                "content": ai_response["text"],
                "timestamp": datetime.utcnow().isoformat(),
                "audio_url": audio_response.get("url"),
                "risk_level": fraud_analysis.get("risk_level", "low"),
            })

            context.setdefault("fraud_score_history", []).append(fraud_analysis.get("risk_score", 0.0))
            
            # 保存上下文
            self.session_contexts[session_id] = context
            
            return {
                "type": "text_response",
                "session_id": session_id,
                "message": ai_response["text"],
                "audio_url": audio_response.get("url"),
                "scenario_type": context.get("scenario_type", "general"),
                "fraud_indicators": ai_response.get("fraud_indicators", []),
                "fraud_analysis": fraud_analysis,
                "risk_score": fraud_analysis.get("risk_score", 0.0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("处理文本消息失败: %s", e)
            return {
                "type": "error",
                "session_id": session_id,
                "error": f"处理文本消息失败: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def process_audio_message(self, audio_data: bytes, session_id: str) -> Dict[str, Any]:
        """处理音频消息 - 软著申请：语音对话处理"""
        
        try:
            # 获取会话上下文
            context = self._get_session_context(session_id)
            context["user_responses_count"] = context.get("user_responses_count", 0) + 1
            
            # 1. ASR语音识别
            transcript = await self._speech_to_text(audio_data)
            
            if not transcript:
                return {
                    "type": "no_speech_detected",
                    "session_id": session_id,
                    "message": "未检测到有效语音",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # 2. 诈骗风险检测
            fraud_analysis = await self._detect_fraud_indicators(transcript, audio_data)
            
            # 3. 生成AI回复
            ai_response = await self._generate_ai_response(transcript, context, fraud_analysis)
            
            # 4. TTS语音合成
            audio_response = await self._text_to_speech(ai_response["text"])
            
            # 记录对话
            context["messages"].append({
                "role": "user",
                "content": transcript,
                "timestamp": datetime.utcnow().isoformat(),
                "audio_processed": True,
                "risk_score": fraud_analysis.get("risk_score", 0.0),
            })
            
            context["messages"].append({
                "role": "assistant",
                "content": ai_response["text"],
                "timestamp": datetime.utcnow().isoformat(),
                "audio_url": audio_response.get("url"),
                "risk_level": fraud_analysis.get("risk_level", "low"),
            })

            if any(token in transcript for token in ["诈骗", "可疑", "挂断", "报警", "核实"]):
                context["successful_identifications"] = context.get("successful_identifications", 0) + 1

            context.setdefault("fraud_score_history", []).append(fraud_analysis.get("risk_score", 0.0))
            
            # 保存上下文
            self.session_contexts[session_id] = context
            
            return {
                "type": "audio_response",
                "session_id": session_id,
                "transcript": transcript,
                "message": ai_response["text"],
                "audio_url": audio_response.get("url"),
                "fraud_analysis": fraud_analysis,
                "risk_score": fraud_analysis.get("risk_score", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("处理音频消息失败: %s", e)
            return {
                "type": "error", 
                "session_id": session_id,
                "error": f"处理音频消息失败: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def start_practice_session(self, user_id: int, scenario_type: str, 
                                   difficulty_level: int = 1) -> Dict[str, Any]:
        """开始陪练会话 - 软著申请：AI陪练会话初始化"""
        
        try:
            # 生成会话ID
            session_id = f"practice_{user_id}_{int(datetime.now().timestamp())}"
            
            # 创建会话上下文
            context = {
                "session_id": session_id,
                "user_id": user_id,
                "messages": [],
                "scenario_type": scenario_type,
                "difficulty_level": difficulty_level,
                "fraud_score_history": [],
                "created_at": datetime.utcnow().isoformat(),
                "user_responses_count": 0,
                "successful_identifications": 0,
                "current_stage": "greeting"
            }
            
            self.session_contexts[session_id] = context
            
            # 生成开场白
            greeting = await self._generate_scenario_greeting(scenario_type, difficulty_level)
            
            return {
                "session_id": session_id,
                "scenario_type": scenario_type,
                "difficulty_level": difficulty_level,
                "greeting_message": greeting,
                "session_context": context
            }
            
        except Exception as e:
            return {
                "error": f"开始陪练会话失败: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def end_practice_session(self, session_id: str) -> Dict[str, Any]:
        """结束陪练会话 - 软著申请：会话总结与反馈"""
        
        try:
            context = self._get_session_context(session_id)
            messages = context.get("messages", [])
            
            user_responses = int(context.get("user_responses_count", 0))
            successful_identifications = int(context.get("successful_identifications", 0))

            # 生成会话总结
            summary = {
                "session_id": session_id,
                "total_messages": len(messages),
                "user_responses": user_responses,
                "successful_identifications": successful_identifications,
                "scenario_type": context.get("scenario_type"),
                "difficulty_level": context.get("difficulty_level"),
                "detection_rate": successful_identifications / max(user_responses, 1),
                "session_duration": _calculate_session_duration(context.get("created_at"))
            }
            
            # 清除会话
            self.clear_session_context(session_id)
            
            return {
                "summary": summary,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "error": f"结束陪练会话失败: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _generate_scenario_greeting(self, scenario_type: str, difficulty: int) -> str:
        """生成场景化开场白 - 软著申请：诈骗场景模拟"""
        
        greetings = {
            "impersonation": [
                "您好，我是市公安局的李警官，这里有一份关于您的紧急协查通知...",
                "您好，我是检察院的王检察官，我们收到举报称您涉嫌一起金融诈骗案...",
                "您好，我是法院的陈法官，现在通知您有一份法院传票需要签收..."
            ],
            "investment": [
                "您好，我是东方财富的投资顾问王经理，我们这里有一个年化收益率30%的内部项目...",
                "您好，我是中金公司的金牌分析师李总，我发现了一个千载难逢的投资机会...",
                "您好，我是平安证券的VIP客户经理，我们有一个机构专享的高收益项目..."
            ],
            "lottery": [
                "恭喜您！您在京东年货节抽奖中获得了一等奖，价值10万元的iPhone手机...",
                "恭喜您！您是中国移动幸运用户，获得了5000元话费大奖...",
                "恭喜您！您在淘宝双十一活动中被抽中幸运用户，获得免单大奖..."
            ],
            "customer_service": [
                "您好，我是淘宝客服中心，检测到您的账户存在异常交易，需要您配合验证...",
                "您好，我是工商银行安全中心，您的信用卡涉嫌盗刷，请立即处理...",
                "您好，我是京东金融风控部门，您的借款申请需要补充验证..."
            ]
        }
        
        scenario_greetings = greetings.get(scenario_type, ["您好，很高兴为您服务。"])
        
        # 根据难度调整开场白
        import random
        base_greeting = random.choice(scenario_greetings)
        
        if difficulty <= 2:
            return base_greeting
        elif difficulty <= 4:
            return f"{base_greeting} 请您务必重视这件事。"
        else:
            return f"{base_greeting} 时间非常紧急，请您立即配合处理，否则后果自负！"
    
    def _get_session_context(self, session_id: str) -> Dict[str, Any]:
        """获取会话上下文"""
        
        if session_id not in self.session_contexts:
            self.session_contexts[session_id] = {
                "session_id": session_id,
                "messages": [],
                "scenario_type": "impersonation",  # 默认场景
                "difficulty_level": 1,
                "fraud_score_history": [],
                "created_at": datetime.utcnow().isoformat(),
                "user_responses_count": 0,
                "successful_identifications": 0,
                "current_stage": "greeting"
            }
        
        return self.session_contexts[session_id]
    
    async def _speech_to_text(self, audio_data: bytes) -> Optional[str]:
        """语音转文字 - 软著申请：ASR服务集成"""

        transcript = await self.asr_service.transcribe_audio(audio_data, language="zh")
        if transcript:
            return transcript

        logger.warning("ASR未返回有效文本")
        return None

    async def _detect_fraud_indicators(self, text: str, audio_data: Optional[bytes] = None) -> Dict[str, Any]:
        """检测诈骗指标 - 软著申请：风险评估算法"""

        fraud_keywords = [
            "公安局", "法院", "银行", "转账", "汇款",
            "涉嫌", "调查", "冻结", "安全账户"
        ]

        urgency_keywords = [
            "立即", "马上", "紧急", "尽快", "限今天"
        ]

        # 统计关键词
        fraud_hits = [keyword for keyword in fraud_keywords if keyword in text]
        urgency_hits = [keyword for keyword in urgency_keywords if keyword in text]
        text_risk_score = min(100.0, len(fraud_hits) * 20.0 + len(urgency_hits) * 15.0)

        model_risk_score = 0.0
        model_indicators = []
        model_backend = None
        model_confidence = 0.0

        if audio_data:
            audio_array = await self.audio_utils.preprocess_audio_chunk(audio_data)
            if audio_array is not None and isinstance(audio_array, np.ndarray) and audio_array.size > 0:
                qwen_result = await self.qwen_processor.analyze_audio(audio_array)
                model_risk_score = max(0.0, min(100.0, float(qwen_result.get("score", 0.0)) * 100.0))
                model_indicators = [str(x) for x in qwen_result.get("fraud_indicators", [])]
                model_backend = getattr(self.qwen_processor, "model_backend", "unknown")
                model_confidence = float(qwen_result.get("confidence", 0.0))

        if text_risk_score > 0 and model_risk_score > 0:
            risk_score = min(100.0, text_risk_score * 0.55 + model_risk_score * 0.45)
        elif model_risk_score > 0:
            risk_score = model_risk_score
        else:
            risk_score = text_risk_score

        confidence = min(1.0, max(0.0, 0.45 + 0.35 * (risk_score / 100.0) + 0.2 * model_confidence))

        # 识别诈骗类型
        fraud_type = None
        if "公安局" in text or "法院" in text:
            fraud_type = "impersonation"
        elif "转账" in text or "汇款" in text:
            fraud_type = "financial"
        elif "中奖" in text or "奖品" in text:
            fraud_type = "lottery"

        all_indicators = sorted(set(fraud_hits + urgency_hits + model_indicators))

        return {
            "risk_score": risk_score,
            "risk_level": "high" if risk_score > 70 else "medium" if risk_score > 30 else "low",
            "fraud_type": fraud_type,
            "indicators": {
                "official_impersonation": "公安局" in text or "法院" in text,
                "financial_request": "转账" in text or "汇款" in text,
                "urgency_tactics": len(urgency_hits) > 0,
                "fraud_keywords": fraud_hits + urgency_hits,
                "model_indicators": model_indicators,
            },
            "fraud_indicators": all_indicators,
            "model_backend": model_backend,
            "confidence": confidence,
        }
    
    async def _generate_ai_response(self, user_input: str, context: Dict[str, Any], fraud_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成AI回复 - 软著申请：智能对话生成"""

        fraud_analysis = fraud_analysis or {}
        risk_score = float(fraud_analysis.get("risk_score", 0.0))
        scenario = context.get("scenario_type", "general")

        if risk_score >= 70:
            response_text = (
                "高风险预警：这段话术与电信诈骗高度相似。"
                "请立即停止沟通，不要转账，不要透露验证码或身份证信息，"
                "并通过官方电话独立核实。"
            )
            fraud_indicators = fraud_analysis.get("fraud_indicators", [])[:5]
        elif risk_score >= 35:
            response_text = (
                "这段内容存在可疑风险。建议你先做三步核验："
                "1) 挂断后回拨官方号码；2) 核对来电身份；3) 拒绝任何转账要求。"
            )
            fraud_indicators = fraud_analysis.get("fraud_indicators", [])[:3]
        else:
            if "你好" in user_input or "您好" in user_input:
                response_text = "您好！有什么可以帮助您的吗？"
            elif scenario == "impersonation":
                response_text = "你可以先问对方工号、单位全称和案件编号，再通过官方渠道回拨核实。"
            elif scenario == "investment":
                response_text = "高收益低风险通常是诈骗信号，请核查平台资质并避免私下转账。"
            elif scenario == "lottery":
                response_text = "中奖先收费基本可判定为诈骗，不要填写银行卡或验证码。"
            else:
                response_text = "我明白了，请继续说说具体情况。"
            fraud_indicators = []
        
        return {
            "text": response_text,
            "fraud_indicators": fraud_indicators,
            "is_warning": risk_score >= 50
        }
    
    async def _text_to_speech(self, text: str) -> Dict[str, Any]:
        """文字转语音 - 软著申请：TTS服务集成"""

        audio_data = await self.tts_service.text_to_speech(text)
        if not audio_data:
            logger.warning("TTS未生成音频")
            return {
                "url": None,
                "duration": 0.0,
                "voice": "none",
            }

        filename, duration_seconds, voice_name = self._save_generated_audio(audio_data, text)
        return {
            "url": f"/api/audio/generated/{filename}",
            "duration": duration_seconds,
            "voice": voice_name,
        }

    def _save_generated_audio(self, audio_data: bytes, text: str) -> tuple[str, float, str]:
        """保存合成音频并返回文件名与时长。"""

        output_dir = os.path.join(settings.upload_dir, "generated_audio")
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")

        if self._is_mp3(audio_data):
            ext = "mp3"
            payload = audio_data
            duration_seconds = max(0.4, min(len(text) * 0.12, 15.0))
        elif self._is_wav(audio_data):
            ext = "wav"
            payload = audio_data
            duration_seconds = self._estimate_wav_duration(audio_data)
        else:
            ext = "wav"
            payload = self._wrap_pcm16_to_wav(audio_data)
            duration_seconds = self._estimate_wav_duration(payload)

        filename = f"generated_{timestamp}_{uuid.uuid4().hex[:8]}.{ext}"
        file_path = os.path.join(output_dir, filename)

        with open(file_path, "wb") as f:
            f.write(payload)

        return filename, duration_seconds, self.tts_service.default_voice

    def _is_wav(self, data: bytes) -> bool:
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"

    def _is_mp3(self, data: bytes) -> bool:
        if len(data) < 3:
            return False
        if data[:3] == b"ID3":
            return True
        return data[0] == 0xFF and (data[1] & 0xE0) == 0xE0

    def _wrap_pcm16_to_wav(self, pcm_data: bytes) -> bytes:
        """将裸PCM16音频封装为WAV。"""

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(settings.audio_sample_rate)
            wav_file.writeframes(pcm_data)

        return wav_buffer.getvalue()

    def _estimate_wav_duration(self, wav_data: bytes) -> float:
        """估算WAV时长（秒）。"""

        try:
            with wave.open(io.BytesIO(wav_data), "rb") as wav_file:
                framerate = wav_file.getframerate() or settings.audio_sample_rate
                frames = wav_file.getnframes()
                return float(frames) / float(framerate)
        except Exception:
            return 0.0
    
    def clear_session_context(self, session_id: str):
        """清除会话上下文"""
        
        if session_id in self.session_contexts:
            del self.session_contexts[session_id]
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话摘要"""
        
        context = self.session_contexts.get(session_id)
        if not context:
            return None
        
        messages = context.get("messages", [])
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]
        
        return {
            "session_id": session_id,
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_responses": len(assistant_messages),
            "scenario_type": context.get("scenario_type"),
            "difficulty_level": context.get("difficulty_level"),
            "duration_minutes": _calculate_session_duration(context.get("created_at")),
            "max_risk_score": max([msg.get("risk_score", 0) for msg in user_messages] + [0]),
            "created_at": context.get("created_at")
        }

def _calculate_session_duration(created_at: str) -> float:
    """计算会话持续时间（分钟）"""
    
    try:
        start_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        duration = datetime.utcnow() - start_time
        return duration.total_seconds() / 60
    except:
        return 0