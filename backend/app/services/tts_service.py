"""
TTS服务 - 软著申请：文本语音合成服务
作用：集成EdgeTTS/CosyVoice引擎，实现自然流畅的语音合成功能
"""

import asyncio
import logging
import io
import tempfile
import subprocess
import wave
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import os

from app.config import settings
from app.services.audio_utils import AudioUtils

logger = logging.getLogger(__name__)

class TTSService:
    """文本语音合成服务类 - 软著申请：TTS核心引擎"""
    
    def __init__(self):
        """初始化TTS服务"""
        self.audio_utils = AudioUtils()
        
        # TTS配置
        self.default_voice = "zh-CN-XiaoxiaoNeural"
        self.output_format = "wav"
        self.sample_rate = settings.audio_sample_rate
        
        # 支持的语音库
        self.available_voices = {
            "female": ["zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural"],
            "male": ["zh-CN-YunyangNeural", "zh-CN-YunxiNeural"],
            "child": ["zh-CN-XiaochenNeural", "zh-CN-XiaohanNeural"]
        }
        
        # 临时文件目录
        self.temp_dir = "./temp_audio"
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
    
    async def text_to_speech(self, text: str, voice: str = None, 
                           speed: float = 1.0, volume: float = 1.0) -> Optional[bytes]:
        """
        文本转语音 - 软著申请：TTS核心功能
        
        Args:
            text: 输入文本
            voice: 语音风格
            speed: 语速 (0.5-2.0)
            volume: 音量 (0.5-1.5)
            
        Returns:
            bytes: 音频数据
        """
        
        try:
            if not text or not text.strip():
                logger.warning("输入文本为空")
                return None
            
            # 使用默认语音
            if not voice:
                voice = self.default_voice
            
            # 调用EdgeTTS
            audio_data = await self._edge_tts_synthesize(text, voice, speed, volume)
            
            if audio_data:
                logger.info(f"TTS合成成功: {len(text)}字符, 语音: {voice}")
                return audio_data
            else:
                # 降级到Mock
                return await self._mock_tts_synthesize(text, voice)
            
        except Exception as e:
            logger.error(f"TTS合成失败: {e}")
            return await self._mock_tts_synthesize(text, voice)
    
    async def _edge_tts_synthesize(self, text: str, voice: str, 
                                 speed: float, volume: float) -> Optional[bytes]:
        """EdgeTTS合成 - 软著申请：Microsoft Edge TTS集成"""
        
        try:
            import edge_tts
            
            # 创建TTS通信
            communicate = edge_tts.Communicate(text, voice=voice)
            
            # 设置语音参数
            communicate.props["rate"] = f"{speed:+.0f}%"
            communicate.props["volume"] = f"{volume:+.0f}%"
            
            # 生成音频
            audio_data = b""
            
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            return audio_data if audio_data else None
            
        except ImportError:
            logger.warning("edge_tts库未安装，使用Mock TTS")
            return None
        except Exception as e:
            logger.error(f"EdgeTTS合成失败: {e}")
            return None
    
    async def _mock_tts_synthesize(self, text: str, voice: str) -> bytes:
        """Mock TTS合成 - 软著申请：降级合成方案"""
        
        # 生成简单的音频数据（正弦波）
        duration = len(text) * 0.1  # 每个字符0.1秒
        sample_rate = self.sample_rate
        samples = int(duration * sample_rate)
        
        # 生成音频信号
        import numpy as np
        t = np.linspace(0, duration, samples, False)
        
        # 基础频率（模拟声音）
        frequency = 440 if "Neural" in voice else 300
        audio_signal = np.sin(2 * np.pi * frequency * t)
        
        # 添加包络（模拟说话节奏）
        envelope = np.exp(-3 * t / duration)
        audio_signal *= envelope
        
        # 转换为16位PCM并封装为标准WAV，避免下游解析歧义
        pcm_data = (audio_signal * 32767).astype(np.int16).tobytes()

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm_data)

        return wav_buffer.getvalue()
    
    async def synthesize_with_timestamp(self, text: str, voice: str = None) -> Dict[str, Any]:
        """
        带时间戳的语音合成 - 软著申请：详细合成信息
        
        Args:
            text: 输入文本
            voice: 语音风格
            
        Returns:
            Dict: 包含音频数据和详细信息的字典
        """
        
        try:
            start_time = datetime.now()
            
            # 合成音频
            audio_data = await self.text_to_speech(text, voice)
            
            end_time = datetime.now()
            synthesis_time = (end_time - start_time).total_seconds()
            
            if not audio_data:
                return {
                    "success": False,
                    "error": "语音合成失败",
                    "timestamp": end_time.isoformat()
                }
            
            # 计算音频时长
            duration_seconds = len(audio_data) / (self.sample_rate * 2)  # 16位音频
            
            return {
                "success": True,
                "audio_data": audio_data,
                "text": text,
                "voice": voice or self.default_voice,
                "duration_seconds": duration_seconds,
                "synthesis_time_seconds": synthesis_time,
                "file_size_bytes": len(audio_data),
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"带时间戳TTS合成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def batch_synthesize(self, texts: list, voice: str = None) -> list:
        """
        批量语音合成 - 软著申请：高效批量处理
        
        Args:
            texts: 文本列表
            voice: 语音风格
            
        Returns:
            list: 音频数据列表
        """
        
        if not texts:
            return []
        
        try:
            # 并发合成
            tasks = []
            for text in texts:
                task = self.text_to_speech(text, voice)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            audio_list = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"批量合成第{i+1}项失败: {result}")
                    audio_list.append(None)
                else:
                    audio_list.append(result)
            
            return audio_list
            
        except Exception as e:
            logger.error(f"批量合成失败: {e}")
            return [None] * len(texts)
    
    async def get_available_voices(self) -> Dict[str, list]:
        """获取可用语音列表 - 软著申请：语音库管理"""
        
        try:
            # 尝试获取EdgeTTS的语音列表
            import edge_tts
            
            voices = await edge_tts.list_voices()
            
            # 按性别分类
            voice_dict = {"female": [], "male": [], "child": [], "other": []}
            
            for voice_info in voices:
                name = voice_info.get("Name", "")
                gender = voice_info.get("Gender", "").lower()
                locale = voice_info.get("Locale", "")
                
                if "zh-CN" in locale:  # 只返回中文语音
                    if gender in voice_dict:
                        voice_dict[gender].append({
                            "name": name,
                            "locale": locale,
                            "description": voice_info.get("Description", "")
                        })
                    else:
                        voice_dict["other"].append({
                            "name": name,
                            "locale": locale,
                            "description": voice_info.get("Description", "")
                        })
            
            return voice_dict
            
        except ImportError:
            logger.warning("edge_tts库未安装，返回Mock语音列表")
            return self.available_voices
        except Exception as e:
            logger.error(f"获取语音列表失败: {e}")
            return self.available_voices
    
    async def save_audio_to_file(self, audio_data: bytes, filename: str = None) -> str:
        """
        保存音频到文件 - 软著申请：音频文件管理
        
        Args:
            audio_data: 音频数据
            filename: 文件名（可选）
            
        Returns:
            str: 文件路径
        """
        
        try:
            if not filename:
                filename = f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.wav"
            
            filepath = os.path.join(self.temp_dir, filename)
            
            # 写入WAV文件
            with wave.open(filepath, 'wb') as wav_file:
                wav_file.setnchannels(1)  # 单声道
                wav_file.setsampwidth(2)  # 16位
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_data)
            
            logger.info(f"音频文件保存成功: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存音频文件失败: {e}")
            raise
    
    async def convert_audio_format(self, audio_data: bytes, 
                                 input_format: str = "wav",
                                 output_format: str = "mp3") -> Optional[bytes]:
        """
        转换音频格式 - 软著申请：音频格式转换
        
        Args:
            audio_data: 输入音频数据
            input_format: 输入格式
            output_format: 输出格式
            
        Returns:
            bytes: 转换后的音频数据
        """
        
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix=f".{input_format}", delete=False) as temp_input:
                temp_input.write(audio_data)
                temp_input_path = temp_input.name
            
            with tempfile.NamedTemporaryFile(suffix=f".{output_format}", delete=False) as temp_output:
                temp_output_path = temp_output.name
            
            # 使用ffmpeg进行格式转换
            try:
                cmd = [
                    "ffmpeg", "-y",  # 覆盖输出文件
                    "-i", temp_input_path,
                    "-acodec", "mp3" if output_format == "mp3" else "pcm_s16le",
                    "-ar", str(self.sample_rate),
                    "-ac", "1",  # 单声道
                    temp_output_path
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"ffmpeg转换失败: {stderr.decode()}")
                    return None
                
                # 读取转换后的文件
                with open(temp_output_path, 'rb') as f:
                    converted_data = f.read()
                
                return converted_data
                
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_input_path)
                    os.unlink(temp_output_path)
                except:
                    pass
            
        except Exception as e:
            logger.error(f"音频格式转换失败: {e}")
            return None
    
    def estimate_duration(self, text: str, speed: float = 1.0) -> float:
        """
        估算语音时长 - 软著申请：语音时长预测
        
        Args:
            text: 输入文本
            speed: 语速
            
        Returns:
            float: 预估时长（秒）
        """
        
        # 中文平均语速：每分钟约200-300字
        chars_per_second = 4.0 * speed  # 基础语速
        
        # 考虑标点符号的停顿
        pause_chars = ["，", "。", "！", "？", "；", "："]
        pause_count = sum(1 for char in text if char in pause_chars)
        pause_time = pause_count * 0.3  # 每个标点停顿0.3秒
        
        # 计算总时长
        reading_time = len(text) / chars_per_second
        total_time = reading_time + pause_time
        
        return max(total_time, 1.0)  # 最少1秒


# 语音效果处理器
class VoiceEffectProcessor:
    """语音效果处理器 - 软著申请：语音效果增强"""
    
    def __init__(self):
        self.sample_rate = 16000
    
    async def add_background_music(self, voice_data: bytes, 
                                 music_data: bytes, 
                                 voice_volume: float = 0.8,
                                 music_volume: float = 0.2) -> bytes:
        """添加背景音乐 - 软著申请：混音功能"""
        
        try:
            import numpy as np
            
            # 转换为numpy数组
            voice_array = np.frombuffer(voice_data, dtype=np.int16).astype(np.float32)
            music_array = np.frombuffer(music_data, dtype=np.int16).astype(np.float32)
            
            # 归一化
            voice_array = voice_array / 32768.0
            music_array = music_array / 32768.0
            
            # 调整长度
            min_length = min(len(voice_array), len(music_array))
            voice_array = voice_array[:min_length]
            music_array = music_array[:min_length]
            
            # 混合音频
            mixed = voice_array * voice_volume + music_array * music_volume
            
            # 限制幅度
            mixed = np.clip(mixed, -1.0, 1.0)
            
            # 转换回16位
            mixed_data = (mixed * 32767).astype(np.int16).tobytes()
            
            return mixed_data
            
        except Exception as e:
            logger.error(f"混音失败: {e}")
            return voice_data
    
    async def apply_echo_effect(self, voice_data: bytes, 
                              delay: float = 0.3,
                              decay: float = 0.5) -> bytes:
        """添加回声效果"""
        
        try:
            import numpy as np
            
            # 转换为numpy数组
            audio_array = np.frombuffer(voice_data, dtype=np.int16).astype(np.float32)
            audio_array = audio_array / 32768.0
            
            # 计算延迟样本数
            delay_samples = int(delay * self.sample_rate)
            
            # 创建延迟信号
            delayed = np.zeros_like(audio_array)
            delayed[delay_samples:] = audio_array[:-delay_samples] * decay
            
            # 混合原信号和延迟信号
            echoed = audio_array + delayed
            
            # 限制幅度
            echoed = np.clip(echoed, -1.0, 1.0)
            
            # 转换回16位
            echoed_data = (echoed * 32767).astype(np.int16).tobytes()
            
            return echoed_data
            
        except Exception as e:
            logger.error(f"回声效果失败: {e}")
            return voice_data