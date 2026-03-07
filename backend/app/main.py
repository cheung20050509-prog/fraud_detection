"""
FastAPI主应用入口 - 软著申请：系统核心服务入口
作用：整合所有模块，提供RESTful API和WebSocket服务，实现电信诈骗检测系统的核心功能
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from contextlib import asynccontextmanager
import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Dict, Any

# 导入自定义模块
from app.config import Settings
from app.database.database import init_database, db_manager, get_db
from app.websocket.manager import connection_manager
from app.routers.ai_practice import router as ai_practice_router
from app.routers.monitoring import router as monitoring_router
from app.routers.analysis import router as analysis_router
from app.routers.config import router as config_router
from app.services.monitoring_session_service import monitoring_session_service

import os

# 实例化配置对象 (修复未定义的 settings 变量)
settings = Settings()

# ==========================================
# 🆕 新增：自动检查并创建日志文件夹
# ==========================================
log_dir = os.path.dirname(settings.log_file)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir)
    print(f"已自动创建日志目录: {log_dir}")
    
# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 软著申请：优雅启动和关闭"""
    
    # 启动时执行
    logger.info("=== 电信诈骗风险阻断系统启动 ===")
    
    try:
        # 初始化数据库
        logger.info("初始化数据库...")
        init_database()
        
        # 检查数据库健康状态
        db_health = db_manager.health_check()
        logger.info(f"数据库状态: {db_health}")
        
        # ==========================================
        # 核心修改：在这里启动 WebSocket 的后台管理任务
        # 此时 FastAPI 的异步事件循环已经准备就绪！
        # ==========================================
        logger.info("启动WebSocket后台任务...")
        await connection_manager.start_background_tasks()
        
        # 启动后台监控任务
        logger.info("启动系统健康监控任务...")
        asyncio.create_task(start_background_monitoring())
        
        logger.info("系统启动完成")
        
    except Exception as e:
        logger.error(f"系统启动失败: {e}")
        raise
    
    yield
    
    # 关闭时执行
    logger.info("=== 系统关闭中 ===")
    
    try:
        # 关闭所有WebSocket连接
        for session_id in list(connection_manager.active_connections.keys()):
            await connection_manager.disconnect(session_id)
        
        logger.info("系统关闭完成")
        
    except Exception as e:
        logger.error(f"系统关闭时出错: {e}")

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    description="基于Qwen2Audio的实时电信诈骗风险阻断系统",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS中间件 - 软著申请：跨域资源共享配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(ai_practice_router, prefix="/api/practice", tags=["AI陪练"])
# 兼容旧前端代理配置（会将 /api 前缀去掉）
app.include_router(ai_practice_router, prefix="/practice", tags=["AI陪练兼容"])
app.include_router(monitoring_router, prefix="/api/monitoring", tags=["实时监护"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["案例分析"])
app.include_router(config_router, prefix="/api/config", tags=["系统配置"])

# WebSocket路由
@app.websocket("/ws/audio/{mode}")
async def websocket_audio_endpoint(websocket: WebSocket, mode: str):
    """音频流WebSocket端点 - 软著申请：实时音频流传输核心接口"""
    
    session_id = None
    session_status = "completed"
    try:
        # 验证模式
        valid_modes = ["practice", "monitoring", "analysis"]
        if mode not in valid_modes:
            raise HTTPException(status_code=400, detail=f"无效模式: {mode}")

        requested_session_id = websocket.query_params.get("session_id")
        raw_user_id = websocket.query_params.get("user_id")
        requested_user_id = int(raw_user_id) if raw_user_id and raw_user_id.isdigit() else None

        if mode == "monitoring":
            if requested_session_id:
                monitoring_session = monitoring_session_service.ensure_session(
                    requested_session_id,
                    user_id=requested_user_id,
                )
            else:
                monitoring_session = monitoring_session_service.create_session(user_id=requested_user_id)

            requested_session_id = monitoring_session["session_id"]
            requested_user_id = monitoring_session["user_id"]
        
        # 建立连接
        session_id = await connection_manager.connect(
            websocket,
            mode=mode,
            user_id=str(requested_user_id) if requested_user_id is not None else None,
            session_id=requested_session_id if mode == "monitoring" else None,
        )

        if mode == "monitoring":
            monitoring_session_service.mark_connected(
                session_id,
                metadata={
                    "mode": mode,
                    "transport": "websocket",
                },
            )
        logger.info(f"WebSocket连接建立: {session_id}, 模式: {mode}")
        
        # 根据模式处理消息
        if mode == "practice":
            await handle_practice_mode(session_id, websocket)
        elif mode == "monitoring":
            session_status = await handle_monitoring_mode(session_id, websocket)
        elif mode == "analysis":
            await handle_analysis_mode(session_id, websocket)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: {session_id}")
    except ValueError as e:
        session_status = "interrupted"
        logger.error(f"WebSocket会话校验失败 {session_id}: {e}")
        await websocket.close(code=1008, reason=str(e))
    except Exception as e:
        session_status = "interrupted"
        logger.error(f"WebSocket错误 {session_id}: {e}")
    finally:
        if session_id and mode == "monitoring":
            monitoring_session_service.complete_session(session_id, status=session_status)
        if session_id:
            await connection_manager.disconnect(session_id)

async def handle_practice_mode(session_id: str, websocket: WebSocket):
    """处理AI陪练模式 - 软著申请：智能对话陪练功能"""
    
    from app.services.ai_chat import AIChatService
    
    ai_service = AIChatService()
    
    while True:
        try:
            # 接收消息
            message = await websocket.receive_text()
            data = message  # 简化处理，实际应解析JSON
            
            # 处理音频或文本消息
            if isinstance(data, str):
                # 文本消息处理
                response = await ai_service.process_text_message(data, session_id)
            else:
                # 音频消息处理
                response = await ai_service.process_audio_message(data, session_id)
            
            # 发送响应
            await connection_manager.send_message(session_id, response)
            
        except WebSocketDisconnect:
            break
        except Exception as e:
            logger.error(f"陪练模式处理错误 {session_id}: {e}")
            break

async def handle_monitoring_mode(session_id: str, websocket: WebSocket) -> str:
    """处理实时监护模式 - 软著申请：环境音监听和风险检测"""
    
    from app.services.fraud_detection import FraudDetectionService
    
    detection_service = FraudDetectionService()

    def _is_normal_socket_shutdown(exc: Exception) -> bool:
        message = str(exc)
        return (
            isinstance(exc, WebSocketDisconnect)
            or "WebSocket is not connected" in message
            or not connection_manager.has_connection(session_id)
        )

    async def _receive_monitoring_audio() -> bytes | None:
        message = await websocket.receive()
        message_type = message.get("type")

        if message_type == "websocket.disconnect":
            raise WebSocketDisconnect()

        if message_type != "websocket.receive":
            return None

        text_payload = message.get("text")
        if isinstance(text_payload, str):
            is_heartbeat = False
            try:
                parsed = json.loads(text_payload)
                is_heartbeat = isinstance(parsed, dict) and parsed.get("type") == "heartbeat"
            except json.JSONDecodeError:
                parsed = None

            if is_heartbeat:
                await connection_manager.send_message(session_id, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat(),
                })
            else:
                logger.info("忽略监护文本帧 %s: %s", session_id, text_payload[:80])
            return None

        binary_payload = message.get("bytes")
        if binary_payload is None or len(binary_payload) == 0:
            return None

        return binary_payload
    
    while True:
        try:
            # 接收音频数据
            data = await _receive_monitoring_audio()
            if data is None:
                continue
            
            # 实时风险检测
            risk_result = await detection_service.analyze_audio_chunk(data, session_id)
            risk_payload = asdict(risk_result)
            
            # 发送检测结果
            sent = await connection_manager.send_message(session_id, {
                "type": "risk_analysis",
                "data": risk_payload,
                "timestamp": datetime.utcnow().isoformat()
            })
            if not sent:
                break
            
            # 如果检测到高风险，触发警报
            if risk_payload.get("risk_score", 0) > settings.risk_threshold_medium:
                sent = await connection_manager.send_message(session_id, {
                    "type": "fraud_alert",
                    "severity": "high",
                    "message": "检测到潜在的诈骗风险！",
                    "data": risk_payload,
                    "timestamp": datetime.utcnow().isoformat()
                })
                if not sent:
                    return "completed"
            
        except WebSocketDisconnect:
            return "completed"
        except Exception as e:
            if _is_normal_socket_shutdown(e):
                logger.info(f"监护模式连接正常关闭: {session_id}")
                return "completed"

            logger.error(f"监护模式处理错误 {session_id}: {e}")
            if connection_manager.has_connection(session_id):
                await connection_manager.send_message(session_id, {
                    "type": "error",
                    "code": "monitoring_analysis_failed",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                })
            return "interrupted"

    return "completed"

async def handle_analysis_mode(session_id: str, websocket: WebSocket):
    """处理案例分析模式 - 软著申请：文件上传和离线分析"""
    
    while True:
        try:
            # 接收文件或分析请求
            await websocket.receive_text()

            # 严格模式下禁止返回模拟进度状态。
            raise RuntimeError("分析模式WebSocket尚未接入真实离线分析流水线")
            
        except WebSocketDisconnect:
            break
        except Exception as e:
            logger.error(f"分析模式处理错误 {session_id}: {e}")
            await connection_manager.send_message(session_id, {
                "type": "error",
                "code": "analysis_pipeline_unavailable",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            })
            break

# REST API路由
@app.get("/")
async def root():
    """根路径 - 软著申请：系统状态检查"""
    return {
        "message": "电信诈骗风险阻断系统",
        "version": settings.app_version,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """健康检查端点 - 软著申请：系统健康监控"""
    
    try:
        # 数据库健康检查
        db_health = db_manager.health_check()
        
        # WebSocket连接统计
        ws_stats = connection_manager.get_stats()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_health,
            "websocket": ws_stats,
            "version": settings.app_version
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@app.get("/api/audio/generated/{filename}")
@app.get("/audio/generated/{filename}")
async def get_generated_audio(filename: str):
    """返回模拟TTS生成的音频文件"""

    # 基础路径校验，防止路径穿越
    if "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="非法文件名")

    audio_path = os.path.join(settings.upload_dir, "generated_audio", filename)
    if not os.path.isfile(audio_path):
        raise HTTPException(status_code=404, detail="音频文件不存在")

    ext = os.path.splitext(filename)[1].lower()
    if ext == ".mp3":
        media_type = "audio/mpeg"
    else:
        media_type = "audio/wav"

    return FileResponse(audio_path, media_type=media_type, filename=filename)

@app.get("/stats")
async def get_stats():
    """获取系统统计信息 - 软著申请：系统性能监控"""
    
    try:
        db_stats = db_manager.get_stats()
        ws_stats = connection_manager.get_stats()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_stats,
            "websocket": ws_stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {e}")

async def start_background_monitoring():
    """启动后台监控任务 - 软著申请：系统后台监控"""
    
    while True:
        try:
            # 每5分钟执行一次健康检查
            await asyncio.sleep(300)
            
            # 检查系统健康状态
            health = await health_check()
            if health["status"] != "healthy":
                logger.warning(f"系统健康检查失败: {health}")
            
        except Exception as e:
            logger.error(f"后台监控任务错误: {e}")

# 错误处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "内部服务器错误",
            "message": "服务器遇到了一个错误，请稍后重试",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# 启动命令
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )