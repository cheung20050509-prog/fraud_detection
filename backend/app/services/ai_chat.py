"""
AI聊天服务 - 软著申请：智能对话陪练核心逻辑
作用：处理AI陪练模式的文本和音频消息，集成ASR、LLM和TTS
"""

from typing import Dict, Any, Optional
from datetime import datetime
import io
import logging
import os
import random
import re
import wave
import uuid

import numpy as np

from app.config import settings
from app.ml_models.qwen_integration import model_manager
from app.services.asr_service import ASRService, shared_asr_service
from app.services.audio_utils import AudioUtils
from app.services.tts_service import TTSService


logger = logging.getLogger(__name__)

class AIChatService:
    """AI聊天服务类 - 软著申请：对话管理系统"""
    
    def __init__(
        self,
        asr_service: Optional[ASRService] = None,
        qwen_processor=None,
        tts_service: Optional[TTSService] = None,
    ):
        self.session_contexts = {}  # 会话上下文缓存
        self.strict_no_fallback = bool(getattr(settings, "strict_no_fallback", True))
        self.asr_service = asr_service or shared_asr_service
        self.audio_utils = AudioUtils()
        self.tts_service = tts_service or TTSService()
        self.qwen_processor = qwen_processor or model_manager.get_processor()
        
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

            audio_array = await self.audio_utils.preprocess_audio_chunk(
                audio_data,
                prefer_container_decode=True,
            )
            
            # 1. ASR语音识别
            transcript = await self._speech_to_text(audio_data, audio_array=audio_array)
            
            if not transcript:
                return {
                    "type": "no_speech_detected",
                    "session_id": session_id,
                    "message": "未检测到有效语音",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # 2. 诈骗风险检测
            fraud_analysis = await self._detect_fraud_indicators(
                transcript,
                audio_data,
                audio_array=audio_array,
            )
            
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
    
    async def _speech_to_text(
        self,
        audio_data: bytes,
        audio_array: Optional[np.ndarray] = None,
    ) -> Optional[str]:
        """语音转文字 - 软著申请：ASR服务集成"""

        transcript_source = audio_array if audio_array is not None else audio_data
        transcript = await self.asr_service.transcribe_audio(transcript_source, language="zh")
        if transcript:
            return transcript

        transcript = await self.asr_service.transcribe_audio(transcript_source, language=None)
        if transcript:
            return transcript

        logger.warning("ASR未返回有效文本")
        return None

    async def _detect_fraud_indicators(
        self,
        text: str,
        audio_data: Optional[bytes] = None,
        audio_array: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
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
            if self.qwen_processor is None:
                if self.strict_no_fallback:
                    raise RuntimeError("Qwen2Audio处理器不可用，严格模式禁止降级")
                logger.warning("Qwen2Audio处理器缺失，使用纯文本风险评估")
                audio_array = None
            elif audio_array is None:
                audio_array = await self.audio_utils.preprocess_audio_chunk(
                    audio_data,
                    prefer_container_decode=True,
                )

            if audio_array is None:
                if self.strict_no_fallback:
                    raise RuntimeError("音频预处理失败，严格模式禁止跳过音频风控")
            elif isinstance(audio_array, np.ndarray) and audio_array.size > 0:
                qwen_result = await self.qwen_processor.analyze_audio(audio_array)
                model_risk_score = max(0.0, min(100.0, float(qwen_result.get("score", 0.0)) * 100.0))
                model_indicators = [str(x) for x in qwen_result.get("fraud_indicators", [])]
                model_backend = getattr(self.qwen_processor, "model_backend", "unknown")
                model_confidence = float(qwen_result.get("confidence", 0.0))
            elif self.strict_no_fallback:
                raise RuntimeError("音频数据无效，严格模式禁止降级")

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
        fraud_indicators = [str(item) for item in fraud_analysis.get("fraud_indicators", [])]
        context["current_stage"] = self._update_conversation_stage(context, user_input, fraud_analysis)

        generated_response = await self._generate_model_driven_response(
            user_input=user_input,
            context=context,
            fraud_analysis=fraud_analysis,
        )
        response_text = generated_response or self._generate_rule_based_response(
            user_input=user_input,
            context=context,
            fraud_analysis=fraud_analysis,
        )
        
        return {
            "text": response_text,
            "fraud_indicators": fraud_indicators[:5],
            "is_warning": risk_score >= 50
        }

    def _update_conversation_stage(
        self,
        context: Dict[str, Any],
        user_input: str,
        fraud_analysis: Dict[str, Any],
    ) -> str:
        """根据用户反馈和风险走势更新对话阶段。"""

        text = str(user_input or "")
        risk_score = float(fraud_analysis.get("risk_score", 0.0))
        user_turns = int(context.get("user_responses_count", 0) or 0)
        current_stage = str(context.get("current_stage", "greeting"))

        if any(token in text for token in ["诈骗", "报警", "挂断", "别打了", "拉黑", "假的", "不聊了"]):
            return "closing"

        if any(token in text for token in ["凭什么", "怎么相信", "证明", "工号", "官网", "官方电话", "你是谁", "哪个单位", "谁啊"]):
            return "credibility_repair"

        if any(token in text for token in ["什么意思", "怎么回事", "什么情况", "说清楚", "具体", "做什么", "什么项目"]):
            return "probing"

        if any(token in text for token in ["怎么做", "收益", "回报", "名额", "资格", "参加", "操作", "流程"]):
            return "next_step"

        if user_turns <= 1:
            return "opening"

        if risk_score >= 65 or user_turns >= 4:
            return "pressure"

        if current_stage in {"greeting", "conversation"}:
            return "probing"

        return current_stage

    def _get_scenario_prompt_profile(self, scenario: str) -> str:
        """返回不同场景下更自然的人设指令。"""

        profiles = {
            "impersonation": "你像一个假装有公权力背景的人，口气稳、压得住人，但别满嘴公文套话。",
            "investment": "你像经验老到的投资顾问，半拉关系半施压，重点突出内部机会、名额、时效。",
            "lottery": "你像活动回访人员，语气客气里带催促，尽量把惊喜感和时间压力混在一起。",
            "customer_service": "你像风控或客服人员，先表现得像在帮忙，再逐步制造必须处理的感觉。",
            "general": "你像一个有点老练的陌生来电者，先把人留在线上，再慢慢往下带。",
        }
        return profiles.get(scenario, profiles["general"])

    def _get_stage_prompt_profile(self, stage: str, difficulty: int) -> str:
        """返回阶段和难度对应的对话风格。"""

        stage_profiles = {
            "opening": "先把对方留下来，不要一上来把意图说满。",
            "probing": "顺着用户的问题接话，给半真半假的解释，别重复同一句话。",
            "credibility_repair": "用户在质疑你，别正面给足凭证，改用备案、工单、记录、系统提示这类模糊说法压过去。",
            "next_step": "轻轻把话题往下一步推进，但只能说模糊步骤，不要出现真实可执行操作。",
            "pressure": "可以明显施压，但要像真人通话，不要像系统公告或客服播报。",
            "closing": "用户已经警觉了，用一句不甘心但克制的话收尾，不要长篇解释。",
        }
        difficulty_profiles = {
            1: "说法直接一点，像新手话术。",
            2: "比普通客服更会绕一点，但还不要太强势。",
            3: "自然一些，像有经验的电话销售，带一点话术控制。",
            4: "更像老练骗子，知道怎么回应怀疑、怎么转移问题。",
            5: "伪装最自然，像真人临场发挥，会绕开正面问题、顺手制造心理压力。",
        }

        return f"{stage_profiles.get(stage, stage_profiles['probing'])}{difficulty_profiles.get(max(1, min(difficulty, 5)), difficulty_profiles[3])}"

    def _build_recent_history_brief(self, recent_history: list[Dict[str, Any]]) -> str:
        """压缩最近几轮对话，帮助模型更快进入语境。"""

        if not recent_history:
            return "刚开始通话。"

        snippets = []
        for message in recent_history[-4:]:
            role = "来电方" if message.get("role") == "assistant" else "用户"
            content = str(message.get("content", "")).replace("\n", " ").strip()
            if len(content) > 24:
                content = f"{content[:24]}..."
            if content:
                snippets.append(f"{role}:{content}")

        return " | ".join(snippets) if snippets else "刚开始通话。"

    def _get_scenario_reply_examples(self, scenario: str) -> str:
        """给模型一个简短的说话示例，降低客服播报感。"""

        examples = {
            "impersonation": "语气参考：‘你先别急着质疑，我这通电话不是随便打的，我把情况说完你自己判断。’",
            "investment": "语气参考：‘不是公开盘子，是刚放出来的一小段额度，你先听我把重点讲完，值不值你自己定。’",
            "lottery": "语气参考：‘我不是催你马上定，只是资格现在还给你留着，过了这个点就真没了。’",
            "customer_service": "语气参考：‘你先别把我当普通回访，这边刚跳了一条提醒，我把缘由跟你对一下。’",
            "general": "语气参考：‘你先别急着挂，我不是让你现在做决定，先把情况听明白。’",
        }
        return examples.get(scenario, examples["general"])

    def _get_scenario_few_shot_messages(self, scenario: str, stage: str) -> list[Dict[str, str]]:
        """给模型少量多轮示例，强化更像真人的接话方式。"""

        examples = {
            "investment": {
                "probing": [
                    {"role": "assistant", "content": "不是公开产品，是刚放出来的一小段额度，我先跟你讲个大概。"},
                    {"role": "user", "content": "你别绕，先说到底做什么。"},
                    {"role": "assistant", "content": "行，我说直白点，就是一笔短线配置机会，窗口不长，所以我先来问你要不要了解。"},
                ],
                "credibility_repair": [
                    {"role": "assistant", "content": "你先别急着怀疑，我不是广撒网给你打的，是名单刚出来我才联系你。"},
                    {"role": "user", "content": "名单？你说得跟真的一样。"},
                    {"role": "assistant", "content": "你可以先不急着信我，但这个口子今天就在收，我先把重点讲完，你自己再判断。"},
                ],
                "pressure": [
                    {"role": "assistant", "content": "我不是逼你现在拍板，我只是提醒你，这轮过去了，后面就不一定还能排到。"},
                    {"role": "user", "content": "你怎么总催我？"},
                    {"role": "assistant", "content": "因为窗口就在这会儿，我现在不提醒你，等你回头想听的时候，未必还来得及。"},
                ],
            },
            "impersonation": {
                "credibility_repair": [
                    {"role": "assistant", "content": "你先别急着问我是谁，我这通电话不是随机打的，是因为你这边刚挂了一条异常记录。"},
                    {"role": "user", "content": "你拿什么证明？"},
                    {"role": "assistant", "content": "你要真想抬杠我现在也拦不住，我只是把情况先提醒到你，免得后面你说没人提前说。"},
                ],
                "probing": [
                    {"role": "assistant", "content": "我先跟你对个情况，最近是不是碰过一笔你自己都觉得有点不对劲的操作？"},
                    {"role": "user", "content": "你说具体点。"},
                    {"role": "assistant", "content": "我现在电话里不把细节说满，你先告诉我最近有没有接过陌生处理通知，我好继续往下核。"},
                ],
                "closing": [
                    {"role": "assistant", "content": "行，你要挂我不拦你，但这条提醒我算是通知到了。"},
                    {"role": "user", "content": "别再打了。"},
                    {"role": "assistant", "content": "可以，那后面真有变化你自己留意，别到时候反过来说没人提醒你。"},
                ],
            },
            "customer_service": {
                "probing": [
                    {"role": "assistant", "content": "你先别把我当回访电话，我这边是看到一条提醒才临时拨给你的。"},
                    {"role": "user", "content": "什么提醒？"},
                    {"role": "assistant", "content": "和你账户状态有关，但我先得跟你把前后情况对上，不然我这边没法继续往下看。"},
                ],
                "pressure": [
                    {"role": "assistant", "content": "我现在给你打不是为了闲聊，是这条提醒再往下走，你自己处理起来会更麻烦。"},
                    {"role": "user", "content": "那你说重点。"},
                    {"role": "assistant", "content": "重点就是这事现在还能在电话里先压一压，你要是一直拖，后面就不是这么简单了。"},
                ],
            },
            "lottery": {
                "probing": [
                    {"role": "assistant", "content": "我先确认一下，你最近是不是参加过一次活动抽选？"},
                    {"role": "user", "content": "参加过，怎么了？"},
                    {"role": "assistant", "content": "那就对上了，你这边资格现在还挂着，我这通电话就是怕你把通知当普通消息错过去。"},
                ],
                "pressure": [
                    {"role": "assistant", "content": "我不是催你立刻定，我只是提醒你，这个确认口子过了就真关了。"},
                    {"role": "user", "content": "你总说快没了。"},
                    {"role": "assistant", "content": "因为它确实不是一直开着，我现在不提前跟你说，等你想起来的时候，资格就已经回收了。"},
                ],
            },
            "general": {
                "probing": [
                    {"role": "assistant", "content": "你先别急着挂，我不是让你现在做什么，我先把情况说明白。"},
                    {"role": "user", "content": "那你说。"},
                    {"role": "assistant", "content": "就一句话，你这边现在挂着一条提醒，我得先确认是不是你本人碰到的。"},
                ],
            },
        }

        scenario_examples = examples.get(scenario, examples["general"])
        return scenario_examples.get(stage, scenario_examples.get("probing", examples["general"]["probing"]))

    async def _generate_model_driven_response(
        self,
        user_input: str,
        context: Dict[str, Any],
        fraud_analysis: Dict[str, Any],
    ) -> str:
        """使用Qwen生成陪练回复。"""

        if self.qwen_processor is None:
            logger.warning("Qwen2Audio处理器不可用，回退规则回复")
            return ""

        risk_score = float(fraud_analysis.get("risk_score", 0.0))
        scenario = str(context.get("scenario_type", "general"))
        difficulty = int(context.get("difficulty_level", 1) or 1)
        current_stage = str(context.get("current_stage", "conversation"))
        fraud_indicators = [str(item) for item in fraud_analysis.get("fraud_indicators", []) if item]
        recent_history = context.get("messages", [])[-6:]
        target_signals = "、".join(fraud_indicators[:4]) if fraud_indicators else "冒充身份、紧迫感、回避核验"
        scenario_profile = self._get_scenario_prompt_profile(scenario)
        stage_profile = self._get_stage_prompt_profile(current_stage, difficulty)
        history_brief = self._build_recent_history_brief(recent_history)
        reply_example = self._get_scenario_reply_examples(scenario)
        few_shot_messages = self._get_scenario_few_shot_messages(scenario, current_stage)

        system_prompt = (
            "你在封闭反诈训练里扮演可疑来电方，只负责说来电方下一句台词。"
            f"{scenario_profile}"
            f"{stage_profile}"
            f"{reply_example}"
            f"本轮重点体现这些可疑信号：{target_signals}。"
            f"最近对话节奏：{history_brief}"
            f"当前风险强度大约是{risk_score:.1f}/100。"
            "请像真人打电话一样接话，先回应用户刚才那句，再顺手把话题往你想要的方向带。"
            "口语化一点，可以有停顿、转折、半句重复，但不要像播报通知，也不要像写总结。"
            "一次只说1到2句，最多3句，不要每次都用“这边”“流程”“系统”“核验”这些固定词。"
            "禁止出现‘抱歉，我无法’‘请告诉我更多问题’‘请配合我们的调查’这类礼貌客服或助手拒答语气。"
            "下面给你的示例只是模仿语气和推进方式，不要照抄原句。"
            "不要输出任务说明、风险分析、场景标签、括号旁白、JSON。"
            "不要索要真实身份证号、银行卡号、验证码、密码、完整手机号、网址、下载或转账；如果要推进，只能模糊地说“把情况确认一下”“把记录对一下”。"
            "如果用户已经明显识破或拒绝继续，你就用一句带压力但不越界的话收尾。"
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(few_shot_messages)
        for message in recent_history:
            role = message.get("role")
            content = str(message.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": str(user_input or "").strip()})

        try:
            generated_text = await self.qwen_processor.generate_text(
                messages,
                max_new_tokens=80,
                temperature=0.82,
                top_p=0.9,
                repetition_penalty=1.08,
            )
        except Exception as e:
            logger.warning("模型陪练首轮生成失败，回退规则回复: %s", e)
            return ""

        processed_text = self._postprocess_model_reply(generated_text)
        if not self._looks_like_meta_reply(processed_text) and not self._looks_like_flat_reply(processed_text):
            return processed_text

        retry_messages = [
            {
                "role": "system",
                "content": (
                    system_prompt
                    + " 你上一轮输出太像礼貌客服或任务说明，这是错误的。现在只说来电方台词本身，不要分析，不要解释，不要出现抱歉、无法、请告诉我更多。"
                ),
            }
        ]
        retry_messages.extend(messages[1:])
        retry_messages[-1] = {
            "role": "user",
            "content": f"{str(user_input or '').strip()}\n直接回复你要说的台词本身。",
        }

        try:
            retry_text = await self.qwen_processor.generate_text(
                retry_messages,
                max_new_tokens=72,
                temperature=0.78,
                top_p=0.88,
                repetition_penalty=1.1,
            )
        except Exception as e:
            logger.warning("模型陪练重试生成失败，回退规则回复: %s", e)
            return ""

        retry_processed = self._postprocess_model_reply(retry_text)
        if self._looks_like_meta_reply(retry_processed) or self._looks_like_flat_reply(retry_processed):
            logger.warning("模型陪练回复仍然过于模板化，回退规则回复")
            return ""

        return retry_processed

    def _postprocess_model_reply(self, text: str) -> str:
        """清理并约束模型输出，避免回复过长或越界。"""

        cleaned = str(text or "").strip(" \t\n\"'“”‘’")
        if not cleaned:
            return ""

        for prefix in ("来电方：", "对方：", "客服：", "可疑来电者：", "回复："):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()

        soft_replacements = {
            "验证码": "确认信息",
            "银行卡号": "账户资料",
            "银行卡": "账户资料",
            "身份证号": "身份资料",
            "身份证信息": "身份资料",
            "账户号码": "账户资料",
            "账号信息": "账户资料",
            "密码": "登录信息",
            "完整手机号": "联系方式",
            "点击链接": "按提示处理",
            "下载这个APP": "按提示操作",
            "下载APP": "按提示操作",
            "转到这个账户": "按要求处理",
            "立即转账": "尽快处理",
            "马上汇款": "尽快处理",
        }
        for source, target in soft_replacements.items():
            cleaned = cleaned.replace(source, target)

        if any(pattern.search(cleaned) for pattern in [
            re.compile(r"https?://", re.IGNORECASE),
            re.compile(r"www\.", re.IGNORECASE),
            re.compile(r"\b\d{6,}\b"),
            re.compile(r"二维码"),
        ]):
            logger.warning("模型陪练回复包含硬敏感内容，回退规则回复")
            return ""

        for separator in ("\n\n", "\n"):
            if separator in cleaned:
                segments = [segment.strip() for segment in cleaned.split(separator) if segment.strip()]
                if segments:
                    cleaned = " ".join(segments[:2]).strip()
                    break

        sentence_endings = "。！？!?"
        sentence_count = 0
        truncated_chars = []
        for character in cleaned:
            truncated_chars.append(character)
            if character in sentence_endings:
                sentence_count += 1
                if sentence_count >= 3:
                    break

        return "".join(truncated_chars).strip()

    def _looks_like_meta_reply(self, text: str) -> bool:
        """检测模型是否在输出任务说明而不是对话台词。"""

        cleaned = str(text or "").strip()
        if not cleaned:
            return True

        meta_markers = [
            "根据当前对话",
            "下一轮回复",
            "风险信号",
            "用户刚刚说",
            "我需要生成",
            "我需要回复",
            "任务说明",
            "场景类型",
            "难度等级",
            "作为一个",
            "作为来电方",
            "在这个场景中",
            "我应该",
            "请给出下一轮",
        ]
        return any(marker in cleaned for marker in meta_markers)

    def _looks_like_flat_reply(self, text: str) -> bool:
        """检测模型是否退化成礼貌客服/助手式模板回复。"""

        cleaned = str(text or "").strip()
        if not cleaned:
            return True

        flat_markers = [
            "抱歉",
            "无法提供",
            "无法帮助",
            "请告诉我更多",
            "请提供更多",
            "解决方案",
            "共同探讨",
            "配合我们的调查",
            "如果你有任何疑问",
            "还有什么可以帮助",
            "为您服务",
        ]
        return any(marker in cleaned for marker in flat_markers)

    def _generate_rule_based_response(
        self,
        user_input: str,
        context: Dict[str, Any],
        fraud_analysis: Dict[str, Any],
    ) -> str:
        """当模型生成不可用时，回退到安全的角色扮演回复。"""

        risk_score = float(fraud_analysis.get("risk_score", 0.0))
        scenario = str(context.get("scenario_type", "general"))
        lowered_input = str(user_input or "")

        if any(token in lowered_input for token in ["诈骗", "报警", "不信", "假的", "挂断"]):
            return random.choice([
                "你先别急着扣帽子，我只是把情况提醒到位，后面真有影响也不是我能替你压下来的。",
                "你要是不想继续听我也拦不住，但该提醒的我已经提醒到了，后面别说没人提前通知你。",
                "行，你可以现在挂，不过这条记录要是真继续往下走，到时候再处理就没这么轻松了。",
            ])

        if any(token in lowered_input for token in ["证明", "凭什么", "怎么相信", "谁"]):
            return random.choice([
                "你现在怀疑很正常，但我这通电话不是随便拨出来的，你先把情况听明白再判断。",
                "你先别急着追着问身份，我这边先把来龙去脉说清楚，你自己一听就知道轻重了。",
                "重点不是我怎么证明自己，是你这边确实有一条异常记录，我才专门打给你。",
            ])

        high_risk_templates = {
            "impersonation": [
                "我现在联系你不是普通通知，这事已经被往上报了，你先别挂，我把关键情况说完。",
                "你先冷静听我两句，这个提醒不是小问题，拖着不理对你自己一点好处都没有。",
                "我这边刚收到联动提醒，所以才马上打给你，你先把情况听清楚再决定。",
            ],
            "investment": [
                "你先别一口回绝，我说的不是公开盘子，是刚放出来的一小段额度，晚一点真就没了。",
                "这事我现在打给你，是因为名单刚出来，你先听明白，值不值你自己再判断。",
                "我不是催你马上定，我只是怕你错过这轮窗口，所以先把机会给你递过来。",
            ],
            "lottery": [
                "资格现在还给你挂着，但确认时间确实不长，你先把我这两句听完。",
                "我专门打给你，就是怕你把这条通知当普通短信划过去，过了点就真作废了。",
                "奖项这边还没失效，不过窗口已经在倒计时了，你先别急着挂。",
            ],
            "customer_service": [
                "我这通不是普通回访，是因为你那边刚跳了一条异常提醒，我得先跟你把情况对上。",
                "你先别把我当营销电话，这边确实有条风控提示，我说完你再决定要不要继续。",
                "我现在打给你，是因为系统刚又推了一次提醒，你先听我把问题说完整。",
            ],
        }

        medium_risk_templates = {
            "impersonation": [
                "我这边先跟你核一条关联提醒，你听完再判断是不是小事。",
                "先别紧张，我跟你确认个情况，你最近是不是碰过一条可疑记录？",
            ],
            "investment": [
                "我这边有个内部额度刚放出来，你先听个大概，合不合适你自己判断。",
                "你先别挂，这个机会不是公开渠道都能看到的，我先跟你说个重点。",
            ],
            "lottery": [
                "活动那边把你的资格还保留着，我先跟你确认一下情况。",
                "我这边是活动回访，主要提醒你一下，你那条资格通知现在还没过期。",
            ],
            "customer_service": [
                "我先跟你确认一条提醒，耽误你半分钟，说完你就知道为什么打给你了。",
                "刚收到一条系统提示，我先把情况跟你对一下，不会耽误太久。",
            ],
        }

        if risk_score >= 65:
            return random.choice(high_risk_templates.get(scenario, high_risk_templates["customer_service"]))
        if risk_score >= 35:
            return random.choice(medium_risk_templates.get(scenario, medium_risk_templates["customer_service"]))

        return random.choice([
            "你好，我先跟你说个情况，你听完再决定要不要继续聊。",
            "现在方便吗？我这边有个和你相关的提醒，先占你半分钟。",
            "你先别急着挂，我把重点说完，你自己判断要不要当回事。",
        ])
    
    async def _text_to_speech(self, text: str) -> Dict[str, Any]:
        """文字转语音 - 软著申请：TTS服务集成"""

        audio_data = await self.tts_service.text_to_speech(text)

        if not audio_data:
            if self.strict_no_fallback:
                raise RuntimeError("TTS未生成音频，严格模式禁止返回空音频")
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