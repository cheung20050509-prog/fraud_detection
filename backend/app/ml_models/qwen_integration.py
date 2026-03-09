"""
Qwen2Audio集成模块 - 软著申请：Qwen2Audio模型接口
作用：提供Qwen2Audio模型的加载、推理和管理功能
"""

import asyncio
import importlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

try:
    torch = importlib.import_module("torch")
except Exception:  # pragma: no cover
    torch = None

try:
    transformers_module = importlib.import_module("transformers")
    AutoModelForCausalLM = getattr(transformers_module, "AutoModelForCausalLM")
    AutoProcessor = getattr(transformers_module, "AutoProcessor")
except Exception:  # pragma: no cover
    AutoModelForCausalLM = None
    AutoProcessor = None

from app.config import settings

logger = logging.getLogger(__name__)


def _strict_no_fallback() -> bool:
    """返回当前是否启用严格模式。"""

    return bool(getattr(settings, "strict_no_fallback", True))


def _schedule_background_task(coro) -> bool:
    """在已有事件循环中调度后台协程。"""

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


class QwenAudioProcessor:
    """Qwen2Audio处理器 - 软著申请：音频理解核心引擎"""

    def __init__(self, model_path: str = None):
        """初始化Qwen2Audio处理器"""

        self.model_path = model_path or settings.qwen_model_path
        self.model = None
        self.processor = None
        self.device = "cpu"
        if settings.use_cuda and torch is not None and torch.cuda.is_available():
            self.device = "cuda"

        # 模型配置
        self.max_audio_length = 30.0  # 最大音频长度（秒）
        self.sample_rate = settings.audio_sample_rate

        self.model_backend = "uninitialized"
        self._init_error: Optional[str] = None
        self._init_attempts = 0
        self._max_init_attempts = 2

        # 使用懒加载，避免与Whisper并发初始化触发meta张量竞争。
        self._initialized = False
        self._init_lock = asyncio.Lock()

    def _resolve_model_dir(self) -> Path:
        """解析模型目录，兼容工作目录差异。"""

        configured = Path(self.model_path)
        if configured.is_absolute():
            return configured

        backend_root = Path(__file__).resolve().parents[2]
        candidate = backend_root / configured
        if candidate.exists():
            return candidate

        return configured

    async def _async_init(self):
        """异步初始化模型"""

        async with self._init_lock:
            if self._initialized and self.model is not None and self.processor is not None:
                return

            if self.model is None and self._init_attempts >= self._max_init_attempts:
                return

            self._init_attempts += 1

            try:
                model_dir = self._resolve_model_dir()
                logger.info(
                    "正在加载Qwen2Audio模型: %s (attempt %s/%s)",
                    model_dir,
                    self._init_attempts,
                    self._max_init_attempts,
                )

                if AutoProcessor is None or AutoModelForCausalLM is None:
                    raise ImportError("transformers未正确安装，无法加载真实模型")

                if not (model_dir / "config.json").exists():
                    raise FileNotFoundError(f"模型配置不存在: {model_dir / 'config.json'}")

                await asyncio.to_thread(self._load_real_model_sync, model_dir)

                self.model_backend = "real"
                self._init_error = None
                self._initialized = True
                logger.info("Qwen2Audio真实模型加载完成")

            except Exception as e:
                self.model = None
                self.processor = None
                self.model_backend = "unavailable"
                self._init_error = str(e)
                self._initialized = True

                if _strict_no_fallback():
                    logger.error("Qwen2Audio真实模型加载失败（严格模式，不允许降级）: %s", e)
                else:
                    logger.error("Qwen2Audio真实模型加载失败，回退到Mock: %s", e)
                    self.model = MockQwenModel()
                    self.processor = MockQwenProcessor()
                    self.model_backend = "mock"

    def _load_real_model_sync(self, model_dir: Path):
        """同步加载真实模型，在线程池中执行。"""

        processor = AutoProcessor.from_pretrained(
            str(model_dir),
            trust_remote_code=True,
        )

        model_kwargs: Dict[str, Any] = {
            "trust_remote_code": True,
        }

        if self.device == "cuda":
            model_kwargs["torch_dtype"] = torch.float16
            try:
                model_kwargs["device_map"] = "auto"
                model = AutoModelForCausalLM.from_pretrained(str(model_dir), **model_kwargs)
            except Exception:
                model_kwargs.pop("device_map", None)
                model = AutoModelForCausalLM.from_pretrained(str(model_dir), **model_kwargs)
                model.to(self.device)
        else:
            model_kwargs["torch_dtype"] = torch.float32
            model = AutoModelForCausalLM.from_pretrained(str(model_dir), **model_kwargs)
            model.to(self.device)

        model.eval()

        self.processor = processor
        self.model = model

    async def analyze_audio(
        self,
        audio_array: np.ndarray,
        return_features: bool = True,
    ) -> Dict[str, Any]:
        """
        分析音频 - 软著申请：Qwen2Audio核心推理功能

        Args:
            audio_array: 音频数组
            return_features: 是否返回详细特征

        Returns:
            Dict: 分析结果
        """

        try:
            should_retry_init = (
                (self.model is None or self.processor is None)
                and self._init_attempts < self._max_init_attempts
            )
            if not self._initialized or should_retry_init:
                await self._async_init()

            if self.model is None or self.processor is None:
                message = self._init_error or "模型未初始化"
                if _strict_no_fallback():
                    raise RuntimeError(f"Qwen2Audio不可用: {message}")
                return self._get_mock_result()

            # 检查音频长度
            duration = len(audio_array) / self.sample_rate
            if duration > self.max_audio_length:
                # 截取前N秒
                max_samples = int(self.max_audio_length * self.sample_rate)
                audio_array = audio_array[:max_samples]

            # 调用模型推理
            if self.model_backend == "real":
                result = await asyncio.to_thread(self._predict_real_sync, audio_array)
            elif hasattr(self.model, "predict"):
                result = await self.model.predict(audio_array)
            else:
                result = self._predict_mock(audio_array)

            normalized = self._normalize_result(result, audio_array)
            if not return_features:
                normalized.pop("features", None)
            return normalized

        except Exception as e:
            logger.error("Qwen2Audio分析失败: %s", e)
            if _strict_no_fallback():
                raise
            return self._get_mock_result()

    async def generate_text(
        self,
        messages: List[Dict[str, Any]],
        max_new_tokens: int = 128,
        temperature: float = 0.8,
        top_p: float = 0.9,
        repetition_penalty: float = 1.05,
    ) -> str:
        """基于当前Qwen模型进行纯文本对话生成。"""

        try:
            should_retry_init = (
                (self.model is None or self.processor is None)
                and self._init_attempts < self._max_init_attempts
            )
            if not self._initialized or should_retry_init:
                await self._async_init()

            if self.model is None or self.processor is None:
                message = self._init_error or "模型未初始化"
                if _strict_no_fallback():
                    raise RuntimeError(f"Qwen2Audio不可用: {message}")
                return ""

            if self.model_backend != "real":
                message = self._init_error or f"当前后端为{self.model_backend}"
                if _strict_no_fallback():
                    raise RuntimeError(f"Qwen2Audio文本生成不可用: {message}")
                return ""

            output_text = await asyncio.to_thread(
                self._generate_text_real_sync,
                messages,
                max_new_tokens,
                temperature,
                top_p,
                repetition_penalty,
            )
            return self._sanitize_generated_text(output_text)

        except Exception as e:
            logger.error("Qwen2Audio文本生成失败: %s", e)
            if _strict_no_fallback():
                raise
            return ""

    def _normalize_chat_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """统一聊天消息结构，兼容processor.apply_chat_template。"""

        normalized_messages: List[Dict[str, Any]] = []
        for message in messages:
            role = str(message.get("role", "user"))
            content = message.get("content", "")

            if isinstance(content, str):
                normalized_content = [{"type": "text", "text": content}]
            elif isinstance(content, list):
                normalized_content = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        normalized_content.append({"type": "text", "text": str(item.get("text", ""))})
                    elif isinstance(item, str):
                        normalized_content.append({"type": "text", "text": item})
                if not normalized_content:
                    normalized_content = [{"type": "text", "text": ""}]
            else:
                normalized_content = [{"type": "text", "text": str(content)}]

            normalized_messages.append({
                "role": role,
                "content": normalized_content,
            })

        return normalized_messages

    def _generate_text_real_sync(
        self,
        messages: List[Dict[str, Any]],
        max_new_tokens: int,
        temperature: float,
        top_p: float,
        repetition_penalty: float,
    ) -> str:
        """同步执行文本对话生成。"""

        if self.model is None or self.processor is None:
            raise RuntimeError("Qwen2Audio模型或处理器未就绪")

        tokenizer = getattr(self.processor, "tokenizer", None)
        if tokenizer is None:
            raise RuntimeError("Qwen2Audio tokenizer不可用")

        normalized_messages = self._normalize_chat_messages(messages)
        if hasattr(self.processor, "apply_chat_template"):
            prompt = self.processor.apply_chat_template(
                normalized_messages,
                add_generation_prompt=True,
                tokenize=False,
            )
        elif hasattr(tokenizer, "apply_chat_template"):
            prompt = tokenizer.apply_chat_template(
                normalized_messages,
                add_generation_prompt=True,
                tokenize=False,
            )
        else:
            prompt_lines = []
            for message in normalized_messages:
                text_parts = [item.get("text", "") for item in message.get("content", []) if isinstance(item, dict)]
                prompt_lines.append(f"{message.get('role', 'user')}: {' '.join(text_parts).strip()}")
            prompt = "\n".join(prompt_lines) + "\nassistant:"

        inputs = self.processor(
            text=prompt,
            audio=None,
            return_tensors="pt",
        )

        target_param = next(self.model.parameters())
        target_device = target_param.device
        target_dtype = target_param.dtype
        for key, value in list(inputs.items()):
            if isinstance(value, torch.Tensor):
                if value.is_floating_point():
                    inputs[key] = value.to(device=target_device, dtype=target_dtype)
                else:
                    inputs[key] = value.to(device=target_device)

        generate_kwargs: Dict[str, Any] = {
            "max_new_tokens": max_new_tokens,
            "do_sample": temperature > 0.0,
            "temperature": max(0.01, float(temperature)),
            "top_p": float(top_p),
            "repetition_penalty": float(repetition_penalty),
        }

        pad_token_id = tokenizer.pad_token_id or tokenizer.eos_token_id
        if pad_token_id is not None:
            generate_kwargs["pad_token_id"] = pad_token_id

        if not generate_kwargs["do_sample"]:
            generate_kwargs.pop("temperature", None)
            generate_kwargs.pop("top_p", None)

        with torch.inference_mode():
            output_ids = self.model.generate(**inputs, **generate_kwargs)

        input_len = inputs["input_ids"].shape[1] if "input_ids" in inputs else 0
        generated_ids = output_ids[:, input_len:] if output_ids.shape[1] > input_len else output_ids
        output_text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return output_text

    def _sanitize_generated_text(self, output_text: str) -> str:
        """清理模型生成文本，移除多余前缀和包裹引号。"""

        text = str(output_text or "").replace("\r", "").strip()
        for prefix in (
            "assistant:",
            "Assistant:",
            "回复：",
            "答：",
            "下一轮回复：",
            "下一轮话术：",
        ):
            if text.startswith(prefix):
                text = text[len(prefix):].strip()

        if "\n\n" in text:
            text = text.split("\n\n", 1)[0].strip()

        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return text.strip(" \t\n\"'“”‘’")

    def _predict_real_sync(self, audio_array: np.ndarray) -> Dict[str, Any]:
        """真实模型同步推理。"""

        if self.model is None or self.processor is None:
            raise RuntimeError("Qwen2Audio模型或处理器未就绪")

        wave = np.asarray(audio_array, dtype=np.float32).reshape(-1)
        if wave.size == 0:
            if _strict_no_fallback():
                raise ValueError("输入音频为空")
            return self._get_mock_result()

        # 归一化输入振幅，防止异常峰值影响推理。
        peak = float(np.max(np.abs(wave))) if wave.size > 0 else 0.0
        if peak > 1.0:
            wave = wave / peak

        prompt = (
            "<|audio_bos|><|AUDIO|><|audio_eos|>"
            "请分析这段语音是否包含电信诈骗风险。"
            "仅输出JSON，格式为: "
            '{"score":0到1之间小数,"confidence":0到1之间小数,'
            '"fraud_indicators":["关键词"],"summary":"一句话结论"}'
        )

        inputs = self.processor(
            text=[prompt],
            audio=[wave],
            return_tensors="pt",
        )

        target_param = next(self.model.parameters())
        target_device = target_param.device
        target_dtype = target_param.dtype
        for key, value in list(inputs.items()):
            if isinstance(value, torch.Tensor):
                if value.is_floating_point():
                    inputs[key] = value.to(device=target_device, dtype=target_dtype)
                else:
                    inputs[key] = value.to(device=target_device)

        generate_kwargs: Dict[str, Any] = {
            "max_new_tokens": 160,
            "do_sample": False,
        }

        tokenizer = getattr(self.processor, "tokenizer", None)
        if tokenizer is not None:
            pad_token_id = tokenizer.pad_token_id or tokenizer.eos_token_id
            if pad_token_id is not None:
                generate_kwargs["pad_token_id"] = pad_token_id

        with torch.inference_mode():
            output_ids = self.model.generate(**inputs, **generate_kwargs)

        input_len = inputs["input_ids"].shape[1] if "input_ids" in inputs else 0
        generated_ids = output_ids[:, input_len:] if output_ids.shape[1] > input_len else output_ids

        if tokenizer is not None:
            output_text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
        else:
            output_text = ""

        return self._parse_real_output(output_text, wave)

    def _parse_real_output(self, output_text: str, audio_array: np.ndarray) -> Dict[str, Any]:
        """解析真实模型输出，优先解析JSON。"""

        parsed: Dict[str, Any] = {}
        match = re.search(r"\{[\s\S]*\}", output_text)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                parsed = {}

        score = parsed.get("score", parsed.get("risk_score"))
        confidence = parsed.get("confidence", 0.65)
        indicators = parsed.get("fraud_indicators", [])

        if not isinstance(indicators, list):
            indicators = [str(indicators)]

        if score is None:
            score, indicators = self._score_from_text(output_text)

        try:
            score_value = float(score)
        except Exception:
            score_value = 0.1

        try:
            confidence_value = float(confidence)
        except Exception:
            confidence_value = 0.6

        score_value = float(max(0.0, min(1.0, score_value)))
        confidence_value = float(max(0.0, min(1.0, confidence_value)))

        audio_energy = float(np.mean(audio_array ** 2)) if audio_array.size else 0.0

        return {
            "score": score_value,
            "confidence": confidence_value,
            "fraud_indicators": [str(x) for x in indicators],
            "features": {
                "voice_energy": audio_energy,
                "speech_activity": float(min(audio_energy * 100, 1.0)),
                "stress_level": float(score_value),
                "urgency_indicators": float(len(indicators)),
            },
            "model_output": output_text,
        }

    def _score_from_text(self, output_text: str):
        """当模型未输出JSON时，按关键词估算风险分。"""

        if not output_text:
            return 0.1, []

        rules = {
            "money_transfer": ["转账", "汇款", "打款", "付款"],
            "authority_impersonation": ["公安", "法院", "检察院", "客服"],
            "threat": ["冻结", "逮捕", "起诉", "刑事"],
            "urgency": ["立刻", "马上", "紧急", "现在"],
            "account_safety": ["安全账户", "验证码", "验证资金"],
        }

        hit = []
        for label, words in rules.items():
            if any(word in output_text for word in words):
                hit.append(label)

        score = min(0.15 + 0.15 * len(hit), 0.95)
        return score, hit

    def _normalize_result(self, result: Dict[str, Any], audio_array: np.ndarray) -> Dict[str, Any]:
        """统一返回字段，兼容上游风控融合逻辑。"""

        if not isinstance(result, dict):
            result = {}

        if "score" not in result and "risk_score" in result:
            result["score"] = result.get("risk_score")

        score = result.get("score", 0.0)
        confidence = result.get("confidence", 0.6)

        try:
            score = float(score)
        except Exception:
            score = 0.0

        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.6

        result["score"] = float(max(0.0, min(1.0, score)))
        result["confidence"] = float(max(0.0, min(1.0, confidence)))
        result.setdefault("fraud_indicators", [])

        if not isinstance(result["fraud_indicators"], list):
            result["fraud_indicators"] = [str(result["fraud_indicators"])]

        if "features" not in result or not isinstance(result["features"], dict):
            audio_energy = float(np.mean(audio_array ** 2)) if audio_array.size else 0.0
            result["features"] = {
                "voice_energy": audio_energy,
                "speech_activity": float(min(audio_energy * 100, 1.0)),
                "stress_level": float(result["score"]),
                "urgency_indicators": float(len(result["fraud_indicators"])),
            }

        return result

    def _predict_mock(self, audio_array: np.ndarray) -> Dict[str, Any]:
        """Mock预测结果"""

        import random

        # 基于音频特征生成Mock结果
        audio_energy = np.mean(audio_array ** 2)
        energy_score = min(audio_energy * 1000, 50)  # 基于能量的风险评分

        # 随机因素
        random_factor = random.uniform(0.1, 0.4)
        final_score = energy_score + random_factor * 50

        # 检测诈骗指标
        fraud_indicators = []
        if final_score > 30:
            fraud_indicators.append("voice_stress")
        if final_score > 50:
            fraud_indicators.append("urgency_detected")
        if final_score > 70:
            fraud_indicators.append("manipulation_pattern")

        return {
            "score": final_score / 100.0,  # 转换为0-1范围
            "features": {
                "voice_energy": audio_energy,
                "speech_activity": min(audio_energy * 100, 1.0),
                "stress_level": min(final_score / 100, 1.0),
                "urgency_indicators": len(fraud_indicators),
            },
            "confidence": 0.75 + random.uniform(-0.1, 0.1),
            "fraud_indicators": fraud_indicators,
        }

    def _get_mock_result(self) -> Dict[str, Any]:
        """获取Mock结果"""

        return {
            "score": 0.1,
            "features": {
                "voice_energy": 0.01,
                "speech_activity": 0.2,
                "stress_level": 0.1,
                "urgency_indicators": 0,
            },
            "confidence": 0.5,
            "fraud_indicators": [],
            "error": "模型未初始化",
        }

    async def batch_analyze(self, audio_list: list) -> list:
        """
        批量分析音频 - 软著申请：高效批量处理

        Args:
            audio_list: 音频数组列表

        Returns:
            list: 分析结果列表
        """

        if not audio_list:
            return []

        try:
            # 并发分析
            tasks = []
            for audio_array in audio_list:
                task = self.analyze_audio(audio_array)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理异常
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error("批量分析第%s项失败: %s", i + 1, result)
                    if _strict_no_fallback():
                        raise RuntimeError(f"批量分析第{i + 1}项失败: {result}") from result
                    processed_results.append(self._get_mock_result())
                else:
                    processed_results.append(result)

            return processed_results

        except Exception as e:
            logger.error("批量分析失败: %s", e)
            if _strict_no_fallback():
                raise
            return [self._get_mock_result()] * len(audio_list)

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息 - 软著申请：模型状态监控"""

        return {
            "model_name": "Qwen2Audio",
            "model_path": str(self._resolve_model_dir()),
            "device": self.device,
            "backend": self.model_backend,
            "initialized": self._initialized,
            "init_error": self._init_error,
            "init_attempts": self._init_attempts,
            "max_init_attempts": self._max_init_attempts,
            "max_audio_length": self.max_audio_length,
            "sample_rate": self.sample_rate,
            "timestamp": datetime.utcnow().isoformat(),
        }


class MockQwenModel:
    """Mock Qwen模型"""

    def __init__(self):
        self.loaded = True

    async def predict(self, audio_array: np.ndarray) -> Dict[str, Any]:
        """Mock预测"""
        import random

        await asyncio.sleep(0.1)  # 模拟推理时间

        # 基于音频特征生成结果
        energy = np.mean(audio_array ** 2)
        stress_score = min(energy * 500 + random.uniform(0.1, 0.3), 1.0)

        return {
            "score": stress_score,
            "risk_score": stress_score,
            "confidence": random.uniform(0.7, 0.95),
            "features": {
                "stress": stress_score,
                "urgency": random.uniform(0.0, 0.5),
                "manipulation": random.uniform(0.0, 0.3),
            },
            "fraud_indicators": ["mock_analysis"],
        }


class MockQwenProcessor:
    """Mock Qwen预处理器"""

    def __init__(self):
        self.initialized = True

    def preprocess(self, audio_array: np.ndarray) -> Dict[str, Any]:
        """Mock预处理"""
        return {
            "input_features": audio_array,
            "attention_mask": np.ones(len(audio_array)),
            "sample_rate": 16000,
        }


# Qwen2Audio模型管理器
class QwenModelManager:
    """Qwen2Audio模型管理器 - 软著申请：模型生命周期管理"""

    def __init__(self):
        self.processors = {}  # {processor_id: QwenAudioProcessor}
        self.default_processor = None
        logger.info("QwenModelManager采用懒加载策略")

    async def _init_default_processor(self):
        """初始化默认处理器"""
        try:
            self.default_processor = QwenAudioProcessor()
            self.processors["default"] = self.default_processor
            logger.info("默认Qwen2Audio处理器初始化完成")
        except Exception as e:
            logger.error("默认处理器初始化失败: %s", e)

    async def create_processor(
        self,
        processor_id: str,
        model_path: str = None,
    ) -> QwenAudioProcessor:
        """创建新的处理器实例"""

        if processor_id in self.processors:
            logger.warning("处理器 %s 已存在", processor_id)
            return self.processors[processor_id]

        try:
            processor = QwenAudioProcessor(model_path)
            self.processors[processor_id] = processor
            logger.info("创建Qwen2Audio处理器: %s", processor_id)
            return processor
        except Exception as e:
            logger.error("创建处理器失败 %s: %s", processor_id, e)
            raise

    def get_processor(self, processor_id: str = "default") -> QwenAudioProcessor:
        """获取处理器实例"""

        if processor_id in self.processors:
            return self.processors[processor_id]

        if self.default_processor is None:
            self.default_processor = QwenAudioProcessor()
            self.processors["default"] = self.default_processor

        return self.default_processor

    def list_processors(self) -> Dict[str, Dict[str, Any]]:
        """列出所有处理器"""

        info = {}
        for pid, processor in self.processors.items():
            info[pid] = processor.get_model_info()

        return info

    def remove_processor(self, processor_id: str):
        """移除处理器实例"""

        if processor_id in self.processors:
            del self.processors[processor_id]
            logger.info("移除处理器: %s", processor_id)
        else:
            logger.warning("处理器不存在: %s", processor_id)


# 全局模型管理器实例
model_manager = QwenModelManager()
