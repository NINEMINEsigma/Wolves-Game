import asyncio
import time
import logging
from typing import Dict, List, Optional, Callable
from .event_recorder import EventRecorder
from .websocket_server import WebSocketServer
from Convention.Convention.Runtime.Architecture import Architecture

__logger__ = logging.getLogger(__name__)

class ReplaySession:
    def __init__(self, observer_id: str, event_recorder: EventRecorder, websocket_server: WebSocketServer):
        self.observer_id = observer_id
        self.event_recorder = event_recorder
        self.websocket_server = websocket_server
        self.is_playing = False
        self.current_sequence = 0
        self.playback_speed = 1.0
        self.start_time = None
        self.task = None
        
    async def start_replay(self, start_sequence: int = 0, speed: float = 1.0):
        """开始回放"""
        self.current_sequence = start_sequence
        self.playback_speed = speed
        self.is_playing = True
        self.start_time = time.time()
        
        # 发送回放开始事件
        await self.websocket_server._send_to_observer(self.observer_id, {
            "type": "replay_started",
            "start_sequence": start_sequence,
            "speed": speed,
            "total_events": len(self.event_recorder.events)
        })
        
        # 启动回放任务
        self.task = asyncio.create_task(self._replay_loop())
        __logger__.info(f"开始回放，观察者: {self.observer_id}, 起始序列: {start_sequence}")
        
    async def pause_replay(self):
        """暂停回放"""
        self.is_playing = False
        if self.task:
            self.task.cancel()
            self.task = None
            
        await self.websocket_server._send_to_observer(self.observer_id, {
            "type": "replay_paused",
            "current_sequence": self.current_sequence
        })
        
        __logger__.info(f"暂停回放，观察者: {self.observer_id}")
        
    async def resume_replay(self):
        """恢复回放"""
        if not self.is_playing:
            self.is_playing = True
            self.start_time = time.time()
            self.task = asyncio.create_task(self._replay_loop())
            
            await self.websocket_server._send_to_observer(self.observer_id, {
                "type": "replay_resumed",
                "current_sequence": self.current_sequence
            })
            
            __logger__.info(f"恢复回放，观察者: {self.observer_id}")
            
    async def set_playback_speed(self, speed: float):
        """设置播放速度"""
        self.playback_speed = speed
        if self.is_playing:
            self.start_time = time.time()
            
        await self.websocket_server._send_to_observer(self.observer_id, {
            "type": "replay_speed_changed",
            "speed": speed
        })
        
        __logger__.info(f"设置播放速度: {speed}x, 观察者: {self.observer_id}")
        
    async def jump_to_sequence(self, sequence: int):
        """跳转到指定序列号"""
        if 0 <= sequence <= len(self.event_recorder.events):
            self.current_sequence = sequence
            self.start_time = time.time()
            
            # 发送跳转事件
            await self.websocket_server._send_to_observer(self.observer_id, {
                "type": "replay_jumped",
                "sequence": sequence
            })
            
            __logger__.info(f"跳转到序列: {sequence}, 观察者: {self.observer_id}")
            
    async def _replay_loop(self):
        """回放循环"""
        try:
            events = self.event_recorder.events
            if not events:
                await self.websocket_server._send_to_observer(self.observer_id, {
                    "type": "replay_error",
                    "message": "没有可回放的事件"
                })
                return
                
            # 从当前序列开始回放
            for i in range(self.current_sequence, len(events)):
                if not self.is_playing:
                    break
                    
                event = events[i]
                self.current_sequence = i
                
                # 发送事件到观察者
                await self.websocket_server._send_to_observer(self.observer_id, {
                    "type": "replay_event",
                    "event": event
                })
                
                # 计算延迟时间
                if i < len(events) - 1:
                    next_event = events[i + 1]
                    original_delay = next_event["timestamp"] - event["timestamp"]
                    replay_delay = original_delay / self.playback_speed
                    
                    # 最小延迟确保UI响应
                    replay_delay = max(replay_delay, 0.1)
                    await asyncio.sleep(replay_delay)
                    
            # 回放完成
            self.is_playing = False
            await self.websocket_server._send_to_observer(self.observer_id, {
                "type": "replay_completed",
                "total_events": len(events)
            })
            
            __logger__.info(f"回放完成，观察者: {self.observer_id}")
            
        except asyncio.CancelledError:
            __logger__.info(f"回放被取消，观察者: {self.observer_id}")
        except Exception as e:
            __logger__.error(f"回放过程中发生错误: {e}")
            await self.websocket_server._send_to_observer(self.observer_id, {
                "type": "replay_error",
                "message": f"回放错误: {str(e)}"
            })

class ReplaySystem:
    def __init__(self, event_recorder: EventRecorder, websocket_server: WebSocketServer):
        Architecture.RegisterGeneric(
            self,
            lambda: __logger__.info("回放系统初始化"),
        )
        self.event_recorder = event_recorder
        self.websocket_server = websocket_server
        self.replay_sessions: Dict[str, ReplaySession] = {}
        
        __logger__.info("回放系统初始化")
        
    async def start_replay(self, observer_id: str, start_sequence: int = 0, speed: float = 1.0):
        """为观察者开始回放"""
        # 如果已有回放会话，先停止
        if observer_id in self.replay_sessions:
            await self.stop_replay(observer_id)
            
        # 创建新的回放会话
        session = ReplaySession(observer_id, self.event_recorder, self.websocket_server)
        self.replay_sessions[observer_id] = session
        
        await session.start_replay(start_sequence, speed)
        
    async def stop_replay(self, observer_id: str):
        """停止观察者的回放"""
        if observer_id in self.replay_sessions:
            session = self.replay_sessions[observer_id]
            await session.pause_replay()
            del self.replay_sessions[observer_id]
            
            await self.websocket_server._send_to_observer(observer_id, {
                "type": "replay_stopped"
            })
            
    async def pause_replay(self, observer_id: str):
        """暂停观察者的回放"""
        if observer_id in self.replay_sessions:
            await self.replay_sessions[observer_id].pause_replay()
            
    async def resume_replay(self, observer_id: str):
        """恢复观察者的回放"""
        if observer_id in self.replay_sessions:
            await self.replay_sessions[observer_id].resume_replay()
            
    async def set_playback_speed(self, observer_id: str, speed: float):
        """设置观察者的播放速度"""
        if observer_id in self.replay_sessions:
            await self.replay_sessions[observer_id].set_playback_speed(speed)
            
    async def jump_to_sequence(self, observer_id: str, sequence: int):
        """观察者跳转到指定序列"""
        if observer_id in self.replay_sessions:
            await self.replay_sessions[observer_id].jump_to_sequence(sequence)
            
    async def get_replay_status(self, observer_id: str) -> Dict:
        """获取观察者的回放状态"""
        if observer_id in self.replay_sessions:
            session = self.replay_sessions[observer_id]
            return {
                "is_playing": session.is_playing,
                "current_sequence": session.current_sequence,
                "playback_speed": session.playback_speed,
                "total_events": len(self.event_recorder.events)
            }
        else:
            return {
                "is_playing": False,
                "current_sequence": 0,
                "playback_speed": 1.0,
                "total_events": len(self.event_recorder.events)
            }
            
    def get_active_replays(self) -> List[str]:
        """获取所有活跃的回放会话"""
        return list(self.replay_sessions.keys())
        
    async def cleanup_observer(self, observer_id: str):
        """清理观察者的回放会话"""
        if observer_id in self.replay_sessions:
            await self.stop_replay(observer_id)
            
    async def get_available_replays(self) -> List[Dict]:
        """获取可用的回放列表"""
        # 这里可以扩展为从文件系统读取历史游戏记录
        return [{
            "id": "current_game",
            "name": "当前游戏",
            "total_events": len(self.event_recorder.events),
            "duration": self.event_recorder.get_game_summary().get("duration", 0)
        }] 