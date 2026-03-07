"""
配置管理模块 - 软著申请：系统配置中心
作用：集中管理所有系统配置，支持动态配置更新，便于运维管理
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    """系统设置类 - 使用Pydantic进行配置验证"""
    
    # 应用基础配置
    app_name: str = "电信诈骗风险阻断系统"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 1080
    reload: bool = False
    
    # CORS配置 - 软著申请：跨域资源共享配置
    cors_origins: List[str] = [
        "http://127.0.0.1:6006",     # 本地开发前端
        "http://localhost:5173",     # Vite默认端口
        "http://127.0.0.1:6006",
        "*"  # 生产环境应限制具体域名
    ]
    
    # WebSocket配置 - 软著申请：实时通信配置
    websocket_ping_interval: int = 20
    websocket_ping_timeout: int = 10
    max_websocket_connections: int = 1000
    
    # 音频处理配置 - 软著申请：音频流处理参数
    audio_sample_rate: int = 16000  # 16kHz采样率
    audio_channels: int = 1         # 单声道
    audio_chunk_size: int = 1024   # 音频块大小
    audio_format: str = "wav"      # 音频格式
    
    # VAD (语音活动检测) 配置
    vad_threshold: float = 0.5      # 语音检测阈值
    vad_frame_duration: float = 0.03  # VAD帧时长(秒)
    max_speech_duration: float = 30.0  # 最大语音时长
    
    # FastRTC配置 - 软著申请：实时音视频通信
    fastrtc_mode: str = "send-receive"  # 发送接收模式
    fastrtc_modality: str = "audio"      # 音频模式
    use_turn_server: bool = True         # 是否使用TURN服务器
    
    # TURN服务器配置 - 软著申请：NAT穿透配置
    turn_server_url: Optional[str] = None
    turn_username: Optional[str] = None
    turn_credential: Optional[str] = None
    
    # AI模型配置 - 软著申请：人工智能模型集成
    qwen_model_path: str = "./models/qwen2-audio"
    whisper_model_size: str = "base"    # tiny/base/small/medium/large
    use_cuda: bool = True               # GPU加速
    max_concurrent_inferences: int = 10 # 并发推理限制
    strict_no_fallback: bool = True     # 拒绝降级：依赖缺失时直接报错
    
    # 风险检测配置 - 软著申请：诈骗风险评估算法
    risk_threshold_low: float = 30.0    # 低风险阈值
    risk_threshold_medium: float = 70.0  # 中风险阈值
    risk_detection_window: float = 5.0  # 检测窗口(秒)
    
    # 数据库配置 - 软著申请：数据持久化存储
    database_url: str = "sqlite:///./fraud_detection.db"
    database_echo: bool = False
    
    # 文件存储配置 - 软著申请：文件管理系统
    upload_dir: str = "./uploads"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_audio_formats: List[str] = [".mp3", ".wav", ".m4a", ".flac"]
    allowed_text_formats: List[str] = [".txt", ".json", ".csv"]
    
    # 日志配置 - 软著申请：系统日志管理
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"
    log_rotation: str = "1 day"
    log_retention: str = "30 days"
    
    # 安全配置 - 软著申请：系统安全防护
    secret_key: Optional[str] = None
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # 监控配置 - 软著申请：系统性能监控
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# 创建全局设置实例
settings = Settings()

# 运行时配置覆盖（从环境变量读取）
def override_settings():
    """运行时动态覆盖配置"""
    # 如果是生产环境，从环境变量读取关键配置
    if os.getenv("ENVIRONMENT") == "production":
        settings.debug = False
        settings.cors_origins = [os.getenv("FRONTEND_URL", "https://yourdomain.com")]
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            settings.database_url = db_url
        secret = os.getenv("SECRET_KEY")
        if secret:
            settings.secret_key = secret
        
        # TURN服务器配置
        settings.turn_server_url = os.getenv("TURN_SERVER_URL")
        settings.turn_username = os.getenv("TURN_USERNAME")
        settings.turn_credential = os.getenv("TURN_CREDENTIAL")

# 应用配置覆盖
override_settings()