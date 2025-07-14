import asyncio
import json
import logging
from typing import Dict, Set, Optional
from websockets.server import serve, WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed
import time

from Convention.Convention.Runtime.Architecture import Architecture

__logger__ = logging.getLogger(__name__)

class WebSocketServer:
    def __init__(self, host: str = "localhost", port: int = 8765):
        Architecture.RegisterGeneric(
            self,
            lambda: __logger__.info(f"WebSocket服务器启动在 ws://{host}:{port}"),
        )
        self.host = host
        self.port = port
        self.observers: Dict[str, WebSocketServerProtocol] = {}
        self.observer_counter = 0
        self.server = None
        self.event_queue: Optional[asyncio.Queue] = None
        self.connection_event: Optional[asyncio.Event] = None
        
    def set_event_queue(self, event_queue: asyncio.Queue):
        """设置事件队列"""
        self.event_queue = event_queue
        
    def set_connection_event(self, connection_event: asyncio.Event):
        """设置连接事件"""
        self.connection_event = connection_event
        
    async def start(self):
        """启动WebSocket服务器（已弃用，现在通过HTTP服务器处理）"""
        __logger__.info("WebSocket服务器现在通过HTTP服务器处理连接")
        
    async def stop(self):
        """停止WebSocket服务器"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            __logger__.info("WebSocket服务器已停止")
            
    async def _handle_connection(self, websocket, path: str):
        """处理新的WebSocket连接"""
        observer_id = f"observer_{self.observer_counter}"
        self.observer_counter += 1
        
        try:
            self.observers[observer_id] = websocket
            __logger__.info(f"新观察者连接: {observer_id}")
            
            # 通知连接事件（如果有的话）
            if self.connection_event and not self.connection_event.is_set():
                self.connection_event.set()
            
            # 发送连接确认
            await websocket.send_str(json.dumps({
                "type": "connection_established",
                "observer_id": observer_id,
                "message": "连接成功"
            }))
            
            # 保持连接直到断开
            async for message in websocket:
                await self._handle_message(observer_id, message)
                
        except ConnectionClosed:
            __logger__.info(f"观察者断开连接: {observer_id}")
        except Exception as e:
            __logger__.error(f"处理连接时发生错误: {e}")
        finally:
            if observer_id in self.observers:
                del self.observers[observer_id]
                
    async def _handle_message(self, observer_id: str, message: str):
        """处理来自观察者的消息"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "ping":
                await self._send_to_observer(observer_id, {
                    "type": "pong",
                    "timestamp": time.time()
                })
            elif message_type == "request_replay":
                # 处理回放请求
                await self._handle_replay_request(observer_id, data)
            else:
                __logger__.warning(f"未知消息类型: {message_type}")
                
        except json.JSONDecodeError:
            __logger__.error(f"无效的JSON消息: {message}")
        except Exception as e:
            __logger__.error(f"处理消息时发生错误: {e}")
            
    async def _handle_replay_request(self, observer_id: str, data: dict):
        """处理回放请求"""
        # 这里将在后续实现中与回放系统集成
        await self._send_to_observer(observer_id, {
            "type": "replay_response",
            "status": "not_implemented",
            "message": "回放功能即将实现"
        })
        
    async def process_event_queue(self):
        """处理事件队列中的消息"""
        if not self.event_queue:
            __logger__.error("事件队列未设置")
            return
            
        while True:
            try:
                # 从队列中获取事件
                event = await self.event_queue.get()
                
                # 处理UI事件
                if event.get("type") == "ui_event":
                    await self.broadcast_event(event["event_type"], event["data"])
                else:
                    __logger__.warning(f"未知事件类型: {event.get('type')}")
                    
            except asyncio.CancelledError:
                __logger__.info("事件队列处理被取消")
                break
            except Exception as e:
                __logger__.error(f"处理事件队列时发生错误: {e}")
        
    async def broadcast_event(self, event_type: str, data: dict):
        """向所有观察者广播事件"""
        message = {
            "type": "game_event",
            "event_type": event_type,
            "data": data,
            "timestamp": time.time()
        }
        
        # 创建断开连接的观察者列表
        disconnected_observers = []
        
        for observer_id, websocket in self.observers.items():
            try:
                await websocket.send_str(json.dumps(message))
            except ConnectionClosed:
                disconnected_observers.append(observer_id)
            except Exception as e:
                __logger__.error(f"向观察者 {observer_id} 发送消息失败: {e}")
                disconnected_observers.append(observer_id)
                
        # 清理断开的连接
        for observer_id in disconnected_observers:
            del self.observers[observer_id]
            __logger__.info(f"清理断开的观察者连接: {observer_id}")
            
    async def _send_to_observer(self, observer_id: str, message: dict):
        """向特定观察者发送消息"""
        if observer_id in self.observers:
            try:
                await self.observers[observer_id].send_str(json.dumps(message))
            except ConnectionClosed:
                del self.observers[observer_id]
                __logger__.info(f"观察者 {observer_id} 连接已断开")
            except Exception as e:
                __logger__.error(f"向观察者 {observer_id} 发送消息失败: {e}")
                
    def get_observer_count(self) -> int:
        """获取当前观察者数量"""
        return len(self.observers)
        
    def get_observer_ids(self) -> Set[str]:
        """获取所有观察者ID"""
        return set(self.observers.keys()) 