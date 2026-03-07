"""
WebSocket连接管理器 - 软著申请：实时通信核心组件
作用：管理WebSocket连接，支持实时音频流传输和多客户端并发
"""

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from typing import Dict, List, Optional, Any
import json
import asyncio
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict, is_dataclass
import logging
from collections import defaultdict

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

logger = logging.getLogger(__name__)


def _to_json_safe(value: Any) -> Any:
    """将消息体转换为可被 json.dumps 序列化的基础类型。"""

    if is_dataclass(value):
        return _to_json_safe(asdict(value))

    if isinstance(value, dict):
        return {str(key): _to_json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(item) for item in value]

    if isinstance(value, datetime):
        return value.isoformat()

    if np is not None and isinstance(value, np.generic):
        return value.item()

    item_getter = getattr(value, "item", None)
    if callable(item_getter):
        try:
            return _to_json_safe(item_getter())
        except Exception:
            pass

    return value

@dataclass
class ConnectionInfo:
    """连接信息类 - 软著申请：连接元数据管理"""
    websocket: WebSocket
    session_id: str
    user_id: Optional[str] = None
    mode: str = "unknown"  # "practice", "monitoring", "analysis"
    connected_at: datetime = None
    last_activity: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.connected_at is None:
            self.connected_at = datetime.utcnow()
        if self.last_activity is None:
            self.last_activity = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}

class ConnectionManager:
    """WebSocket连接管理器 - 软著申请：实时通信连接池管理"""
    
    def __init__(self):
        # 活跃连接字典 {session_id: ConnectionInfo}
        self.active_connections: Dict[str, ConnectionInfo] = {}
        
        # 用户连接映射 {user_id: [session_id1, session_id2, ...]}
        self.user_connections: Dict[str, List[str]] = defaultdict(list)
        
        # 模式连接映射 {mode: [session_id1, session_id2, ...]}
        self.mode_connections: Dict[str, List[str]] = defaultdict(list)
        
        # 连接统计
        self.connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "practice_sessions": 0,
            "monitoring_sessions": 0,
            "analysis_sessions": 0
        }
        
        # 消息队列 - 用于广播消息
        self.broadcast_queue = asyncio.Queue()
        
    # ✅ 新增：专门用于启动后台任务的异步方法
    async def start_background_tasks(self):
        """启动后台任务 - 软著申请：后台协程生命周期管理"""
        # 启动清理任务
        asyncio.create_task(self._cleanup_inactive_connections())
        
        # 启动广播任务
        asyncio.create_task(self._broadcast_loop())
        
        logger.info("WebSocket 后台清理和广播任务已启动")
    
    async def connect(
        self,
        websocket: WebSocket,
        mode: str = "unknown",
        user_id: str = None,
        session_id: str | None = None,
    ) -> str:
        """建立新连接 - 软著申请：WebSocket连接建立和认证"""
        
        try:
            await websocket.accept()
            
            # 生成唯一会话ID
            session_id = session_id or str(uuid.uuid4())

            if session_id in self.active_connections:
                raise RuntimeError(f"连接已存在: {session_id}")
            
            # 创建连接信息
            connection_info = ConnectionInfo(
                websocket=websocket,
                session_id=session_id,
                user_id=user_id,
                mode=mode,
                metadata={}
            )
            
            # 保存连接
            self.active_connections[session_id] = connection_info
            
            # 更新索引映射
            if user_id:
                self.user_connections[user_id].append(session_id)
            self.mode_connections[mode].append(session_id)
            
            # 更新统计
            self._update_stats()
            
            logger.info(f"新连接建立: {session_id}, 模式: {mode}, 用户: {user_id}")
            
            # 发送连接确认消息
            await self.send_message(session_id, {
                "type": "connection_established",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "mode": mode
            })
            
            return session_id
            
        except Exception as e:
            logger.error(f"连接建立失败: {e}")
            await websocket.close(code=1011, reason="连接建立失败")
            raise
    
    async def disconnect(self, session_id: str):
        """断开连接 - 软著申请：优雅断开和资源清理"""
        
        connection_info = self.active_connections.get(session_id)
        if not connection_info:
            return
        
        try:
            # 关闭WebSocket连接
            if connection_info.websocket.application_state != WebSocketState.DISCONNECTED:
                await connection_info.websocket.close()
        except Exception as e:
            logger.warning(f"关闭WebSocket连接时出错: {e}")
        
        # 从活跃连接中移除
        del self.active_connections[session_id]
        
        # 更新索引映射
        if connection_info.user_id:
            self.user_connections[connection_info.user_id].remove(session_id)
            if not self.user_connections[connection_info.user_id]:
                del self.user_connections[connection_info.user_id]
        
        self.mode_connections[connection_info.mode].remove(session_id)
        if not self.mode_connections[connection_info.mode]:
            del self.mode_connections[connection_info.mode]
        
        # 更新统计
        self._update_stats()
        
        logger.info(f"连接断开: {session_id}")

    def has_connection(self, session_id: str) -> bool:
        """检查连接是否仍然活跃。"""

        return session_id in self.active_connections
    
    async def send_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """发送消息到指定连接 - 软著申请：点对点消息传输"""
        
        connection_info = self.active_connections.get(session_id)
        if not connection_info:
            logger.warning(f"连接不存在: {session_id}")
            return False
        
        try:
            payload = _to_json_safe(message)
            await connection_info.websocket.send_text(json.dumps(payload, ensure_ascii=False))
            
            # 更新最后活动时间
            connection_info.last_activity = datetime.utcnow()
            return True
            
        except Exception as e:
            logger.error(f"发送消息失败 {session_id}: {e}")
            await self.disconnect(session_id)
            return False
    
    async def send_binary(self, session_id: str, data: bytes):
        """发送二进制数据到指定连接 - 软著申请：音频流二进制传输"""
        
        connection_info = self.active_connections.get(session_id)
        if not connection_info:
            return
        
        try:
            await connection_info.websocket.send_bytes(data)
            connection_info.last_activity = datetime.utcnow()
        except Exception as e:
            logger.error(f"发送二进制数据失败 {session_id}: {e}")
            await self.disconnect(session_id)
    
    async def broadcast_to_mode(self, mode: str, message: Dict[str, Any]):
        """向指定模式的所有连接广播消息 - 软著申请：组播功能"""
        
        session_ids = self.mode_connections.get(mode, [])
        if not session_ids:
            return
        
        await self.broadcast_queue.put({
            "type": "mode_broadcast",
            "mode": mode,
            "session_ids": session_ids.copy(),
            "message": message
        })
    
    async def broadcast_to_user(self, user_id: str, message: Dict[str, Any]):
        """向指定用户的所有连接广播消息"""
        
        session_ids = self.user_connections.get(user_id, [])
        if not session_ids:
            return
        
        await self.broadcast_queue.put({
            "type": "user_broadcast",
            "user_id": user_id,
            "session_ids": session_ids.copy(),
            "message": message
        })
    
    async def get_connection_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取连接信息"""
        
        connection_info = self.active_connections.get(session_id)
        if not connection_info:
            return None
        
        return {
            "session_id": connection_info.session_id,
            "user_id": connection_info.user_id,
            "mode": connection_info.mode,
            "connected_at": connection_info.connected_at.isoformat(),
            "last_activity": connection_info.last_activity.isoformat(),
            "metadata": connection_info.metadata
        }
    
    async def update_connection_metadata(self, session_id: str, metadata: Dict[str, Any]):
        """更新连接元数据"""
        
        connection_info = self.active_connections.get(session_id)
        if connection_info:
            connection_info.metadata.update(metadata)
            connection_info.last_activity = datetime.utcnow()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        
        return {
            **self.connection_stats,
            "detailed_modes": {mode: len(connections) for mode, connections in self.mode_connections.items()},
            "detailed_users": {user_id: len(connections) for user_id, connections in self.user_connections.items()}
        }
    
    async def _broadcast_loop(self):
        """广播消息循环"""
        
        while True:
            try:
                # 等待广播消息
                broadcast_item = await self.broadcast_queue.get()
                
                session_ids = broadcast_item["session_ids"]
                message = broadcast_item["message"]
                
                # 并发发送消息
                tasks = []
                for session_id in session_ids:
                    task = asyncio.create_task(
                        self.send_message(session_id, message)
                    )
                    tasks.append(task)
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
    
    async def _cleanup_inactive_connections(self):
        """清理非活跃连接"""
        
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                current_time = datetime.utcnow()
                inactive_sessions = []
                
                for session_id, connection_info in self.active_connections.items():
                    # 检查连接是否超过5分钟没有活动
                    if (current_time - connection_info.last_activity).seconds > 300:
                        inactive_sessions.append(session_id)
                
                # 断开非活跃连接
                for session_id in inactive_sessions:
                    logger.info(f"清理非活跃连接: {session_id}")
                    await self.disconnect(session_id)
                
            except Exception as e:
                logger.error(f"清理非活跃连接失败: {e}")
    
    def _update_stats(self):
        """更新统计信息"""
        
        self.connection_stats.update({
            "total_connections": len(self.active_connections),
            "active_connections": len(self.active_connections),
            "practice_sessions": len(self.mode_connections.get("practice", [])),
            "monitoring_sessions": len(self.mode_connections.get("monitoring", [])),
            "analysis_sessions": len(self.mode_connections.get("analysis", []))
        })

# 全局连接管理器实例
connection_manager = ConnectionManager()

# WebSocket异常处理
class WebSocketError(Exception):
    """WebSocket异常类"""
    pass

class ConnectionNotFoundError(WebSocketError):
    """连接未找到异常"""
    pass

class InvalidModeError(WebSocketError):
    """无效模式异常"""
    pass