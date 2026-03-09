"""
ASR服务 - 软著申请：语音识别转录服务
作用：集成Whisper/FunASR模型，实现高精度语音转文字功能
"""

import asyncio
import logging
import numpy as np
from typing import Optional, Dict, Any, Union
from datetime import datetime

from app.config import settings
from app.services.audio_utils import AudioUtils

logger = logging.getLogger(__name__)


def _schedule_background_task(coro) -> bool:
    """在已存在事件循环时调度后台协程。"""

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
        return True
    except RuntimeError:
        try:
            coro.close()
        except Exception:
            pass
        return False

class ASRService:
    """语音识别服务类 - 软著申请：ASR核心引擎"""
    
    def __init__(self):
        """初始化ASR服务"""
        self.asr_processor = None
        self.audio_utils = AudioUtils()
        self._init_lock = asyncio.Lock()
        self._init_error: Optional[str] = None
        self.strict_no_fallback = bool(getattr(settings, "strict_no_fallback", True))
        
        # ASR配置
        self.asr_backend = str(getattr(settings, "asr_backend", "funasr") or "funasr").strip().lower()
        self.asr_language = str(getattr(settings, "asr_language", "auto") or "auto").strip().lower()
        self.model_size = settings.whisper_model_size
        self.funasr_model_name = str(getattr(settings, "funasr_model_name", "iic/SenseVoiceSmall"))
        self.sample_rate = settings.audio_sample_rate
        self.use_cuda = settings.use_cuda
        
        # 初始化模型（若当前无事件循环，则在首次调用时懒加载）
        self._init_started = _schedule_background_task(self._init_models())
        if not self._init_started:
            logger.info("ASRService将在首次转录时初始化%s模型", self.asr_backend)

    def _resolve_device(self) -> str:
        """解析ASR后端使用的设备字符串。"""

        device = "cpu"
        try:
            import torch

            if self.use_cuda and torch.cuda.is_available():
                if self.asr_backend == "funasr":
                    device = "cuda:0"
                else:
                    device = "cuda"
        except Exception as e:
            if self.strict_no_fallback:
                raise RuntimeError(f"torch不可用，严格模式禁止降级: {e}") from e
            logger.warning("torch不可用，ASR将使用CPU或降级方案")
        return device
    
    async def _init_models(self):
        """异步初始化ASR模型"""
        async with self._init_lock:
            if self.asr_processor is not None:
                return

            try:
                device = self._resolve_device()

                if self.asr_backend == "funasr":
                    logger.info("正在初始化FunASR模型 (%s)...", self.funasr_model_name)
                    from app.ml_models.funasr_integration import FunASRProcessor

                    self.asr_processor = FunASRProcessor(
                        model_name=self.funasr_model_name,
                        device=device,
                        vad_model=getattr(settings, "funasr_vad_model", None),
                        punc_model=getattr(settings, "funasr_punc_model", None),
                        spk_model=getattr(settings, "funasr_spk_model", None),
                    )
                elif self.asr_backend == "whisper":
                    logger.info("正在初始化Whisper模型 (size: %s)...", self.model_size)
                    from app.ml_models.whisper_integration import WhisperProcessor

                    self.asr_processor = WhisperProcessor(
                        model_size=self.model_size,
                        device=device,
                    )
                else:
                    raise RuntimeError(f"不支持的ASR后端: {self.asr_backend}")

                self._init_error = None
                logger.info("ASR模型初始化完成: backend=%s", self.asr_backend)
            except Exception as e:
                logger.error("ASR模型初始化失败 (%s): %s", self.asr_backend, e)
                self._init_error = str(e)
                if self.strict_no_fallback:
                    self.asr_processor = None
                else:
                    self.asr_processor = MockASRProcessor()

    async def _ensure_initialized(self):
        """确保模型已初始化。"""

        if self.asr_processor is None:
            await self._init_models()

        if self.asr_processor is None:
            raise RuntimeError(f"ASR处理器不可用: {self._init_error or '初始化失败'}")

        backend = getattr(self.asr_processor, "model_backend", None)
        if self.strict_no_fallback and backend == "mock":
            raise RuntimeError("ASR当前为Mock后端，严格模式禁止降级")

    async def warmup_model(self):
        """预热ASR模型，避免并发初始化导致不稳定状态。"""

        await self._ensure_initialized()

        if self.asr_processor is None:
            raise RuntimeError("ASR处理器不可用")

        init_method = getattr(self.asr_processor, "_async_init", None)
        if callable(init_method):
            await init_method()

        backend = getattr(self.asr_processor, "model_backend", None)
        init_error = getattr(self.asr_processor, "_init_error", None)

        if self.strict_no_fallback and backend != "real":
            raise RuntimeError(f"ASR不可用: {init_error or backend or '模型未就绪'}")
    
    async def transcribe_audio(self, audio_data: Union[bytes, np.ndarray], language: str = "zh") -> Optional[str]:
        """
        转录音频 - 软著申请：语音识别核心功能
        
        Args:
            audio_data: 音频二进制数据或浮点音频数组
            language: 语言代码 (zh/en/ja等)
            
        Returns:
            str: 转录文本
        """
        
        try:
            await self._ensure_initialized()

            if isinstance(audio_data, np.ndarray):
                audio_array = np.asarray(audio_data, dtype=np.float32).reshape(-1)
            else:
                if not audio_data or len(audio_data) < 100:
                    logger.warning("音频数据为空或过短")
                    return None

                # 音频预处理
                audio_array = await self.audio_utils.preprocess_audio_chunk(
                    audio_data,
                    prefer_container_decode=True,
                )
                if audio_array is None:
                    logger.warning("音频预处理失败")
                    return None

            if audio_array is None or len(audio_array) == 0:
                logger.warning("音频数据为空")
                return None
            
            # 检查音频长度
            duration = len(audio_array) / self.sample_rate
            if duration < 0.3:  # 少于0.3秒视为无效
                logger.warning(f"音频时长过短: {duration:.2f}秒")
                return None
            
            resolved_language = language if language is not None else self.asr_language

            if self.asr_processor:
                transcript = await self.asr_processor.transcribe(audio_array, resolved_language)
                return transcript.strip() if transcript else None
            else:
                logger.error("ASR处理器未初始化")
                return None
            
        except Exception as e:
            logger.error(f"音频转录失败: {e}")
            if self.strict_no_fallback:
                raise
            return None
    
    async def transcribe_with_timestamp(self, audio_data: Union[bytes, np.ndarray], 
                                      language: str = "zh") -> Dict[str, Any]:
        """
        带时间戳的音频转录 - 软著申请：详细语音分析功能
        
        Args:
            audio_data: 音频二进制数据
            language: 语言代码
            
        Returns:
            Dict: 包含转录文本和时间戳的详细信息
        """
        
        try:
            transcript = await self.transcribe_audio(audio_data, language)
            
            # 计算音频时长
            if isinstance(audio_data, np.ndarray):
                audio_array = np.asarray(audio_data, dtype=np.float32).reshape(-1)
            else:
                audio_array = await self.audio_utils.preprocess_audio_chunk(
                    audio_data,
                    prefer_container_decode=True,
                )
            duration = len(audio_array) / self.sample_rate if audio_array is not None else 0
            
            return {
                "text": transcript or "",
                "language": language,
                "duration_seconds": duration,
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": 0.85 if transcript else 0.0,
                "word_timestamps": []  # 可以后续实现词级时间戳
            }
            
        except Exception as e:
            logger.error(f"带时间戳转录失败: {e}")
            if self.strict_no_fallback:
                raise
            return {
                "text": "",
                "language": language,
                "duration_seconds": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def transcribe_streaming(self, audio_chunks: list, 
                                  language: str = "zh") -> str:
        """
        流式转录 - 软著申请：实时语音转录功能
        
        Args:
            audio_chunks: 音频块列表
            language: 语言代码
            
        Returns:
            str: 完整转录文本
        """
        
        try:
            await self._ensure_initialized()

            if not audio_chunks:
                return ""
            
            # 合并音频块
            all_audio = np.concatenate(audio_chunks)
            
            # 转录合并后的音频
            if not self.asr_processor:
                return ""

            resolved_language = language if language is not None else self.asr_language
            transcript = await self.asr_processor.transcribe(all_audio, resolved_language)
            return transcript.strip() if transcript else ""
            
        except Exception as e:
            logger.error(f"流式转录失败: {e}")
            if self.strict_no_fallback:
                raise
            return ""
    
    async def detect_language(self, audio_data: bytes) -> str:
        """
        检测音频语言 - 软著申请：多语言支持功能
        
        Args:
            audio_data: 音频数据
            
        Returns:
            str: 检测到的语言代码
        """
        
        try:
            await self._ensure_initialized()

            if not self.asr_processor:
                if self.strict_no_fallback:
                    raise RuntimeError("ASR处理器未初始化")
                return "zh"  # 默认中文
            
            audio_array = await self.audio_utils.preprocess_audio_chunk(
                audio_data,
                prefer_container_decode=True,
            )
            if audio_array is None:
                return "zh"
            
            # 调用语言检测
            language = await self.asr_processor.detect_language(audio_array)
            return language if language else "zh"
            
        except Exception as e:
            logger.error(f"语言检测失败: {e}")
            if self.strict_no_fallback:
                raise
            return "zh"
    
    def is_speech_present(self, audio_data: bytes) -> bool:
        """
        检测是否有语音 - 软著申请：语音活动检测
        
        Args:
            audio_data: 音频数据
            
        Returns:
            bool: 是否包含语音
        """
        
        try:
            # 简单的能量检测
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            energy = np.mean(audio_array.astype(float) ** 2)
            
            # 能量阈值
            threshold = 1000.0  # 可根据实际情况调整
            
            return energy > threshold
            
        except Exception as e:
            logger.error(f"语音检测失败: {e}")
            return False


class MockASRProcessor:
    """Mock ASR处理器 - 用于模型加载失败时的降级方案"""
    
    def __init__(self, model_size: str = "base", device: str = "cpu"):
        self.model_size = model_size
        self.device = device
        self.model_backend = "mock"
        self._init_error = "mock backend"
        
        # Mock转录文本库
        self.mock_transcripts = [
            "你好，请问有什么可以帮助您的吗？",
            "我是公安局的，请问您最近有没有接到可疑的电话？",
            "这里有一份关于您的紧急通知，请立即处理",
            "恭喜您中奖了，请提供您的银行账户信息",
            "您的账户存在异常，请配合我们进行验证",
            "这是一个诈骗电话，请您立即挂断"
        ]
    
    async def transcribe(self, audio_array: np.ndarray, language: str = "zh") -> str:
        """Mock音频转录"""
        import random
        
        # 模拟处理时间
        await asyncio.sleep(0.1)
        
        # 根据音频长度选择不同的Mock结果
        duration = len(audio_array) / 16000.0  # 假设16kHz采样率
        
        if duration < 1.0:
            return "你好"
        elif duration < 3.0:
            return random.choice(self.mock_transcripts[:3])
        else:
            return random.choice(self.mock_transcripts)
    
    async def detect_language(self, audio_array: np.ndarray) -> str:
        """Mock语言检测"""
        await asyncio.sleep(0.05)
        return "zh"  # 默认返回中文


MockWhisperProcessor = MockASRProcessor


shared_asr_service = ASRService()


# 语音活动检测 (VAD) 辅助类
class VoiceActivityDetector:
    """语音活动检测器 - 软著申请：VAD语音检测算法"""
    
    def __init__(self, sample_rate: int = 16000, frame_duration: float = 0.03):
        self.sample_rate = sample_rate
        self.frame_size = int(sample_rate * frame_duration)
        self.threshold = 0.01  # 能量阈值
        
    def detect_activity(self, audio_data: bytes) -> tuple:
        """
        检测语音活动 - 软著申请：VAD算法实现
        
        Returns:
            tuple: (is_speech, confidence)
        """
        
        try:
            # 转换为numpy数组
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(float)
            audio_array = audio_array / 32768.0  # 归一化到[-1, 1]
            
            # 分帧处理
            if len(audio_array) < self.frame_size:
                return False, 0.0
            
            # 计算每帧的能量
            frames = []
            for i in range(0, len(audio_array) - self.frame_size + 1, self.frame_size):
                frame = audio_array[i:i + self.frame_size]
                energy = np.mean(frame ** 2)
                frames.append(energy)
            
            if not frames:
                return False, 0.0
            
            # 计算平均能量和方差
            avg_energy = np.mean(frames)
            energy_var = np.var(frames)
            
            # 判断是否为语音
            is_speech = avg_energy > self.threshold
            confidence = min(avg_energy / self.threshold, 1.0) if self.threshold > 0 else 0.0
            
            return is_speech, confidence
            
        except Exception as e:
            logger.error(f"VAD检测失败: {e}")
            return False, 0.0