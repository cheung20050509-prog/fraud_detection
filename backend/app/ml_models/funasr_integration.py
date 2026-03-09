"""
FunASR集成模块 - 软著申请：FunASR/SenseVoice语音识别接口
作用：提供FunASR模型的加载、推理和语言识别能力
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

LANGUAGE_TOKEN_PATTERN = re.compile(r"<\|([^|>]+)\|>")
KNOWN_LANGUAGE_TOKENS = {"zh", "en", "yue", "ja", "ko", "nospeech"}


def _strict_no_fallback() -> bool:
    return bool(getattr(settings, "strict_no_fallback", True))


class FunASRProcessor:
    """FunASR处理器，默认加载SenseVoiceSmall。"""

    def __init__(
        self,
        model_name: str = "iic/SenseVoiceSmall",
        device: str = "cpu",
        vad_model: Optional[str] = "fsmn-vad",
        punc_model: Optional[str] = None,
        spk_model: Optional[str] = None,
    ):
        self.model_name = model_name
        self.device = device
        self.vad_model = vad_model
        self.punc_model = punc_model
        self.spk_model = spk_model
        self.model = None
        self.sample_rate = 16000
        self.model_backend = "uninitialized"
        self._init_error: Optional[str] = None
        self._init_lock = asyncio.Lock()
        self._initialized = False
        self._postprocess = None
        self.batch_size_s = max(0, int(getattr(settings, "funasr_batch_size_s", 0)))
        self.merge_vad = bool(getattr(settings, "funasr_merge_vad", True))
        self.merge_length_s = int(getattr(settings, "funasr_merge_length_s", 15))
        self.vad_kwargs = {
            "max_single_segment_time": int(
                getattr(settings, "funasr_vad_max_single_segment_ms", 30000)
            )
        }
        self.use_itn = bool(getattr(settings, "funasr_use_itn", True))

    async def _async_init(self):
        async with self._init_lock:
            if self._initialized and self.model is not None:
                return

            try:
                logger.info("正在加载FunASR模型 (%s, device=%s)...", self.model_name, self.device)

                from funasr import AutoModel

                model_kwargs: Dict[str, Any] = {
                    "model": self.model_name,
                    "device": self.device,
                    "disable_update": True,
                }
                if self.vad_model:
                    model_kwargs["vad_model"] = self.vad_model
                    model_kwargs["vad_kwargs"] = dict(self.vad_kwargs)
                if self.punc_model:
                    model_kwargs["punc_model"] = self.punc_model
                if self.spk_model:
                    model_kwargs["spk_model"] = self.spk_model

                self.model = await asyncio.to_thread(AutoModel, **model_kwargs)
                self._postprocess = None
                self.model_backend = "real"
                self._init_error = None
                self._initialized = True
                logger.info("FunASR模型加载完成: %s", self.model_name)
            except Exception as e:
                self.model = None
                self.model_backend = "unavailable"
                self._init_error = str(e)
                self._initialized = True
                logger.error("FunASR模型加载失败: %s", e)
                if _strict_no_fallback():
                    raise RuntimeError(f"FunASR初始化失败: {e}") from e

    def _normalize_language(self, language: Optional[str]) -> str:
        value = str(language or getattr(settings, "asr_language", "auto")).strip().lower()
        if value in {"", "none", "null", "auto-detect"}:
            return "auto"
        if value in {"zh-cn", "zh-hans", "cmn"}:
            return "zh"
        return value

    def _postprocess_text(self, raw_text: str) -> str:
        if not raw_text:
            return ""

        cleaned_text = LANGUAGE_TOKEN_PATTERN.sub(" ", str(raw_text))
        cleaned_text = " ".join(cleaned_text.split()).strip()
        if callable(self._postprocess):
            try:
                return str(self._postprocess(cleaned_text)).strip()
            except Exception as e:
                logger.warning("FunASR文本后处理失败，回退原始文本: %s", e)
        return cleaned_text

    def _extract_language(self, raw_text: str, fallback_language: str) -> str:
        for token in LANGUAGE_TOKEN_PATTERN.findall(raw_text or ""):
            token = str(token).strip().lower()
            if token in KNOWN_LANGUAGE_TOKENS:
                return token
        return fallback_language or "zh"

    def _parse_generation_result(
        self,
        result: Any,
        fallback_language: str,
    ) -> Tuple[str, str, List[Dict[str, Any]]]:
        payloads: List[Dict[str, Any]] = []
        if isinstance(result, list):
            payloads = [item for item in result if isinstance(item, dict)]
        elif isinstance(result, dict):
            payloads = [result]

        texts: List[str] = []
        detected_language = fallback_language or "zh"
        for payload in payloads:
            raw_text = str(payload.get("text", "")).strip()
            if raw_text:
                detected_language = self._extract_language(raw_text, detected_language)
                processed = self._postprocess_text(raw_text)
                if processed:
                    texts.append(processed)

        separator = " "
        return separator.join(texts).strip(), detected_language, payloads

    async def transcribe(
        self,
        audio_array: np.ndarray,
        language: Optional[str] = None,
        task: str = "transcribe",
    ) -> Optional[str]:
        del task

        await self._async_init()
        if self.model is None:
            message = self._init_error or "FunASR模型未初始化"
            if _strict_no_fallback():
                raise RuntimeError(message)
            return None

        audio_input = np.asarray(audio_array, dtype=np.float32).reshape(-1)
        if audio_input.size == 0:
            if _strict_no_fallback():
                raise ValueError("音频数据为空")
            return None

        resolved_language = self._normalize_language(language)
        generate_kwargs: Dict[str, Any] = {
            "input": audio_input,
            "cache": {},
            "language": resolved_language,
            "use_itn": self.use_itn,
            "merge_vad": self.merge_vad,
            "merge_length_s": self.merge_length_s,
        }
        if self.batch_size_s > 0:
            generate_kwargs["batch_size_s"] = self.batch_size_s

        result = await asyncio.to_thread(self.model.generate, **generate_kwargs)
        transcript, _, _ = self._parse_generation_result(result, resolved_language)
        return transcript or None

    async def detect_language(self, audio_array: np.ndarray) -> str:
        await self._async_init()
        if self.model is None:
            message = self._init_error or "FunASR模型未初始化"
            if _strict_no_fallback():
                raise RuntimeError(message)
            return "zh"

        audio_input = np.asarray(audio_array, dtype=np.float32).reshape(-1)
        result = await asyncio.to_thread(
            self.model.generate,
            input=audio_input,
            cache={},
            language="auto",
            use_itn=False,
            merge_vad=self.merge_vad,
            merge_length_s=self.merge_length_s,
        )
        _, detected_language, _ = self._parse_generation_result(result, "zh")
        return detected_language or "zh"