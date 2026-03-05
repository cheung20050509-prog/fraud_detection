"""
音频工具类 - 软著申请：音频处理核心工具
作用：提供音频格式转换、预处理、特征提取等基础功能
"""

import asyncio
import logging
import numpy as np
import wave
import io
from typing import Optional, Dict, Any, Tuple
import librosa
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)

class AudioUtils:
    """音频工具类 - 软著申请：音频处理核心模块"""
    
    def __init__(self):
        """初始化音频工具"""
        self.sample_rate = settings.audio_sample_rate
        self.channels = settings.audio_channels
        self.chunk_size = settings.audio_chunk_size
        
        # 音频处理参数
        self.vad_threshold = settings.vad_threshold
        self.max_duration = settings.max_speech_duration
    
    async def preprocess_audio_chunk(self, audio_data: bytes) -> Optional[np.ndarray]:
        """
        音频块预处理 - 软著申请：音频流预处理
        
        Args:
            audio_data: 原始音频数据
            
        Returns:
            np.ndarray: 处理后的音频数组
        """
        
        try:
            if not audio_data or len(audio_data) < 100:
                return None
            
            # 尝试不同的音频格式
            audio_array = None
            
            # 1. 尝试WAV格式
            if audio_data.startswith(b'RIFF'):
                audio_array = self._read_wav_from_bytes(audio_data)
            
            # 2. 尝试PCM格式（16位）
            elif len(audio_data) % 2 == 0:
                try:
                    # 假设是16位PCM
                    audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
                    audio_array = audio_array / 32768.0  # 归一化到[-1, 1]
                except:
                    pass
            
            # 3. 尝试8位PCM
            else:
                try:
                    audio_array = np.frombuffer(audio_data, dtype=np.uint8).astype(np.float32)
                    audio_array = (audio_array - 128) / 128.0  # 归一化到[-1, 1]
                except:
                    pass
            
            if audio_array is None:
                logger.warning("无法解析音频格式")
                return None
            
            # 重采样到目标采样率
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)  # 转换为单声道
            
            # 重采样（如果需要）
            if len(audio_array) / self.sample_rate > self.max_duration:
                audio_array = audio_array[:int(self.max_duration * self.sample_rate)]
            
            return audio_array
            
        except Exception as e:
            logger.error(f"音频预处理失败: {e}")
            return None
    
    def _read_wav_from_bytes(self, wav_data: bytes) -> Optional[np.ndarray]:
        """从字节数据读取WAV文件"""
        
        try:
            with wave.open(io.BytesIO(wav_data), 'rb') as wav_file:
                frames = wav_file.readframes(-1)
                audio_array = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
                audio_array = audio_array / 32768.0
                
                # 转换为单声道
                if wav_file.getnchannels() > 1:
                    audio_array = audio_array.reshape(-1, wav_file.getnchannels())
                    audio_array = np.mean(audio_array, axis=1)
                
                return audio_array
                
        except Exception as e:
            logger.error(f"读取WAV数据失败: {e}")
            return None
    
    async def extract_voice_features(self, audio_array: np.ndarray) -> Dict[str, float]:
        """
        提取语音特征 - 软著申请：声纹特征分析
        
        Args:
            audio_array: 音频数组
            
        Returns:
            Dict[str, float]: 语音特征字典
        """
        
        try:
            if len(audio_array) < 1024:
                return {}
            
            features = {}
            
            # 1. 基础统计特征
            features["rms_energy"] = np.sqrt(np.mean(audio_array ** 2))
            features["zero_crossing_rate"] = np.mean(np.diff(np.sign(audio_array)) != 0)
            
            # 2. 频域特征
            fft = np.fft.fft(audio_array)
            magnitude = np.abs(fft)
            freqs = np.fft.fftfreq(len(audio_array), 1/self.sample_rate)
            
            # 频谱质心
            features["spectral_centroid"] = np.sum(freqs[:len(freqs)//2] * magnitude[:len(magnitude)//2]) / np.sum(magnitude[:len(magnitude)//2] + 1e-10)
            
            # 频谱带宽
            features["spectral_bandwidth"] = np.sqrt(np.sum(((freqs[:len(freqs)//2] - features["spectral_centroid"]) ** 2) * magnitude[:len(magnitude)//2]) / (np.sum(magnitude[:len(magnitude)//2]) + 1e-10))
            
            # 3. MFCC特征
            try:
                mfccs = librosa.feature.mfcc(y=audio_array, sr=self.sample_rate, n_mfcc=13)
                features["mfcc_mean"] = np.mean(mfccs)
                features["mfcc_std"] = np.std(mfccs)
            except:
                features["mfcc_mean"] = 0.0
                features["mfcc_std"] = 0.0
            
            # 4. 音高特征
            try:
                pitches, magnitudes = librosa.piptrack(y=audio_array, sr=self.sample_rate)
                pitch_values = []
                
                for i in range(pitches.shape[1]):
                    index = magnitudes[:, i].argmax()
                    pitch = pitches[index, i]
                    if pitch > 0:
                        pitch_values.append(pitch)
                
                if pitch_values:
                    features["pitch_mean"] = np.mean(pitch_values)
                    features["pitch_std"] = np.std(pitch_values)
                    features["pitch_range"] = np.max(pitch_values) - np.min(pitch_values)
                else:
                    features["pitch_mean"] = 0.0
                    features["pitch_std"] = 0.0
                    features["pitch_range"] = 0.0
                    
            except:
                features["pitch_mean"] = 0.0
                features["pitch_std"] = 0.0
                features["pitch_range"] = 0.0
            
            # 5. 语速和节奏特征
            features["speech_rate"] = len(audio_array) / self.sample_rate  # 简化的语速估计
            features["volume_variance"] = np.var(audio_array ** 2)  # 音量变化
            
            # 6. 情感和操纵性特征（简化版）
            features["intonation_consistency"] = 1.0 / (1.0 + features["pitch_std"])  # 语调一致性
            features["emotion_artificiality"] = min(features["zero_crossing_rate"] * 10, 1.0)  # 情感真实性
            
            return features
            
        except Exception as e:
            logger.error(f"语音特征提取失败: {e}")
            return {}
    
    async def detect_speech_activity(self, audio_array: np.ndarray, 
                                   frame_duration: float = 0.03) -> Tuple[bool, float]:
        """
        语音活动检测 - 软著申请：VAD算法
        
        Args:
            audio_array: 音频数组
            frame_duration: 帧时长（秒）
            
        Returns:
            Tuple[bool, float]: (是否包含语音, 置信度)
        """
        
        try:
            if len(audio_array) < self.sample_rate * 0.1:  # 少于0.1秒
                return False, 0.0
            
            # 分帧处理
            frame_size = int(self.sample_rate * frame_duration)
            frames = []
            
            for i in range(0, len(audio_array) - frame_size + 1, frame_size):
                frame = audio_array[i:i + frame_size]
                frames.append(frame)
            
            if not frames:
                return False, 0.0
            
            # 计算每帧的能量
            frame_energies = []
            for frame in frames:
                energy = np.mean(frame ** 2)
                frame_energies.append(energy)
            
            # 能量阈值检测
            avg_energy = np.mean(frame_energies)
            energy_std = np.std(frame_energies)
            
            # 动态阈值
            threshold = avg_energy + 2 * energy_std
            
            # 统计超过阈值的帧数
            speech_frames = sum(1 for e in frame_energies if e > threshold)
            speech_ratio = speech_frames / len(frame_energies)
            
            is_speech = speech_ratio > 0.3
            confidence = min(speech_ratio * 2, 1.0)
            
            return is_speech, confidence
            
        except Exception as e:
            logger.error(f"语音活动检测失败: {e}")
            return False, 0.0
    
    async def apply_noise_reduction(self, audio_array: np.ndarray) -> np.ndarray:
        """
        降噪处理 - 软著申请：音频降噪算法
        
        Args:
            audio_array: 原始音频数组
            
        Returns:
            np.ndarray: 降噪后的音频数组
        """
        
        try:
            # 简单的谱减法降噪
            fft = np.fft.fft(audio_array)
            magnitude = np.abs(fft)
            phase = np.angle(fft)
            
            # 估计噪声水平（使用前10%作为噪声估计）
            noise_frames = int(len(magnitude) * 0.1)
            noise_level = np.mean(magnitude[:noise_frames])
            
            # 谱减法
            gain = np.maximum(1.0 - noise_level / (magnitude + 1e-10), 0.3)
            enhanced_magnitude = magnitude * gain
            
            # 重构音频
            enhanced_fft = enhanced_magnitude * np.exp(1j * phase)
            enhanced_audio = np.fft.ifft(enhanced_fft).real
            
            return enhanced_audio.astype(np.float32)
            
        except Exception as e:
            logger.error(f"降噪处理失败: {e}")
            return audio_array
    
    async def apply_audio_enhancement(self, audio_array: np.ndarray) -> np.ndarray:
        """
        音频增强 - 软著申请：音质提升算法
        
        Args:
            audio_array: 原始音频数组
            
        Returns:
            np.ndarray: 增强后的音频数组
        """
        
        try:
            # 1. 降噪
            denoised = await self.apply_noise_reduction(audio_array)
            
            # 2. 自动增益控制
            rms = np.sqrt(np.mean(denoised ** 2))
            if rms > 0:
                target_rms = 0.1
                gain = target_rms / rms
                gain = np.clip(gain, 0.5, 2.0)  # 限制增益范围
                enhanced = denoised * gain
            else:
                enhanced = denoised
            
            # 3. 高频增强（简单的高通滤波）
            try:
                from scipy import signal
                sos = signal.butter(2, 3000, 'high', fs=self.sample_rate, output='sos')
                high_freq = signal.sosfilt(sos, enhanced)
                enhanced = enhanced * 0.8 + high_freq * 0.2
            except ImportError:
                # scipy不可用时跳过高频增强
                pass
            
            # 4. 限幅
            enhanced = np.clip(enhanced, -0.95, 0.95)
            
            return enhanced
            
        except Exception as e:
            logger.error(f"音频增强失败: {e}")
            return audio_array
    
    async def segment_audio(self, audio_array: np.ndarray, 
                           max_segment_duration: float = 10.0) -> list:
        """
        音频分段 - 软著申请：智能音频分段
        
        Args:
            audio_array: 音频数组
            max_segment_duration: 最大段时长（秒）
            
        Returns:
            list: 音频段列表
        """
        
        try:
            segment_samples = int(max_segment_duration * self.sample_rate)
            segments = []
            
            for i in range(0, len(audio_array), segment_samples):
                end_idx = min(i + segment_samples, len(audio_array))
                segment = audio_array[i:end_idx]
                segments.append(segment)
            
            return segments
            
        except Exception as e:
            logger.error(f"音频分段失败: {e}")
            return [audio_array]
    
    async def calculate_audio_similarity(self, audio1: np.ndarray, 
                                       audio2: np.ndarray) -> float:
        """
        计算音频相似度 - 软著申请：音频相似性分析
        
        Args:
            audio1: 音频1
            audio2: 音频2
            
        Returns:
            float: 相似度（0-1）
        """
        
        try:
            # 确保长度相同
            min_length = min(len(audio1), len(audio2))
            audio1 = audio1[:min_length]
            audio2 = audio2[:min_length]
            
            # 计算相关系数
            correlation = np.corrcoef(audio1, audio2)[0, 1]
            similarity = (correlation + 1) / 2  # 转换到0-1范围
            
            return max(0.0, similarity)
            
        except Exception as e:
            logger.error(f"音频相似度计算失败: {e}")
            return 0.0
    
    def create_silence(self, duration: float) -> bytes:
        """
        创建静音音频 - 软著申请：静音生成
        
        Args:
            duration: 静音时长（秒）
            
        Returns:
            bytes: 静音音频数据
        """
        
        try:
            samples = int(duration * self.sample_rate)
            silence = np.zeros(samples, dtype=np.int16)
            return silence.tobytes()
        except Exception as e:
            logger.error(f"创建静音失败: {e}")
            return b""
    
    async def mix_audio_streams(self, audio_streams: list, 
                              weights: list = None) -> np.ndarray:
        """
        混合多个音频流 - 软著申请：音频混音
        
        Args:
            audio_streams: 音频流列表
            weights: 权重列表
            
        Returns:
            np.ndarray: 混合后的音频
        """
        
        try:
            if not audio_streams:
                return np.array([])
            
            if weights is None:
                weights = [1.0] * len(audio_streams)
            
            # 确保权重数量匹配
            if len(weights) != len(audio_streams):
                weights = [1.0] * len(audio_streams)
            
            # 找到最长长度
            max_length = max(len(stream) for stream in audio_streams)
            
            # 混合音频
            mixed = np.zeros(max_length)
            
            for stream, weight in zip(audio_streams, weights):
                if len(stream) < max_length:
                    padded = np.pad(stream, (0, max_length - len(stream)), 'constant')
                else:
                    padded = stream[:max_length]
                
                mixed += padded * weight
            
            # 归一化
            max_val = np.max(np.abs(mixed))
            if max_val > 0:
                mixed = mixed / max_val * 0.95
            
            return mixed
            
        except Exception as e:
            logger.error(f"音频混合失败: {e}")
            return audio_streams[0] if audio_streams else np.array([])
    
    def audio_to_wav_bytes(self, audio_array: np.ndarray) -> bytes:
        """
        将音频数组转换为WAV字节数据 - 软著申请：音频格式转换
        
        Args:
            audio_array: 音频数组
            
        Returns:
            bytes: WAV格式字节数据
        """
        
        try:
            # 转换为16位整数
            audio_int16 = (audio_array * 32767).astype(np.int16)
            
            # 创建WAV文件
            with io.BytesIO() as wav_buffer:
                with wave.open(wav_buffer, 'wb') as wav_file:
                    wav_file.setnchannels(self.channels)
                    wav_file.setsampwidth(2)  # 16位
                    wav_file.setframerate(self.sample_rate)
                    wav_file.writeframes(audio_int16.tobytes())
                
                return wav_buffer.getvalue()
                
        except Exception as e:
            logger.error(f"WAV转换失败: {e}")
            return b""