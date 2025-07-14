import asyncio
import json
import logging
from typing import Dict, List, Optional
from Convention.Convention.Runtime.Architecture import Architecture
from src.engine.game_engine import UISystem
import time

__logger__ = logging.getLogger(__name__)

class WebUISystem(UISystem):
    def __init__(self, websocket_server, event_recorder):
        super().__init__()
        self.websocket_server = websocket_server
        self.event_recorder = event_recorder
        self.current_phase = ""
        self.current_round = 0
        self.alive_players = []
        self.dead_players = []
        import asyncio
        self.loop = asyncio.get_event_loop()
        __logger__.info(f"WebUISystem.__init__: event_queue id={id(self.websocket_server.event_queue) if hasattr(self.websocket_server, 'event_queue') else 'N/A'}, event_loop id={id(asyncio.get_event_loop())}")
        
    def _send_event(self, event_type: str, data: dict):
        """通过事件队列发送事件"""
        __logger__.info(f"WebUISystem._send_event called: {event_type}, data: {data}, event_queue id={id(self.websocket_server.event_queue) if hasattr(self.websocket_server, 'event_queue') else 'N/A'}, event_loop id={id(asyncio.get_event_loop())}")
        if hasattr(self.websocket_server, 'event_queue') and self.websocket_server.event_queue:
            try:
                event = {
                    "type": "ui_event",
                    "event_type": event_type,
                    "data": data,
                    "timestamp": time.time()
                }
                self.loop.call_soon_threadsafe(
                    self.websocket_server.event_queue.put_nowait, event
                )
            except Exception as e:
                __logger__.error(f"发送事件失败: {e}")
        
    def title(self, title: str) -> None:
        """广播游戏标题更新"""
        __logger__.info(f"WebUISystem.title called: {title}")
        self.current_round = self._extract_round_number(title)
        event_data = {
            "title": title,
            "round": self.current_round
        }
        
        # 记录事件
        self.event_recorder.record_event("title", event_data)
        
        # 通过队列发送事件
        self._send_event("title", event_data)
        
        # 同时调用父类方法保持控制台输出
        super().title(title)
        
    def phase(self, phase: str) -> None:
        """广播游戏阶段更新"""
        __logger__.info(f"WebUISystem.phase called: {phase}")
        self.current_phase = phase
        event_data = {
            "phase": phase,
            "phase_emoji": self._get_phase_emoji(phase)
        }
        
        # 记录事件
        self.event_recorder.record_event("phase", event_data)
        
        # 通过队列发送事件
        self._send_event("phase", event_data)
        
        # 同时调用父类方法保持控制台输出
        super().phase(phase)
        
    def public_speech(self, playerId: str, role: str, message: str) -> None:
        """广播公开发言"""
        event_data = {
            "playerId": playerId,
            "role": role,
            "message": message,
            "speech_type": "public",
            "timestamp": time.time()
        }
        
        # 记录事件
        self.event_recorder.record_event("public_speech", event_data)
        
        # 通过队列发送事件
        self._send_event("public_speech", event_data)
        
        # 同时调用父类方法保持控制台输出
        super().public_speech(playerId, role, message)
        
    def private_speech(self, playerId: str, role: str, message: str) -> None:
        """广播私密发言（仅相关角色可见）"""
        event_data = {
            "playerId": playerId,
            "role": role,
            "message": message,
            "speech_type": "private",
            "timestamp": time.time(),
            "visible_to": self._get_private_speech_visibility(role)
        }
        
        # 记录事件
        self.event_recorder.record_event("private_speech", event_data)
        
        # 通过队列发送事件
        self._send_event("private_speech", event_data)
        
        # 同时调用父类方法保持控制台输出
        super().private_speech(playerId, role, message)
        
    def system_message(self, message: str) -> None:
        """广播系统消息"""
        event_data = {
            "message": message,
            "message_type": "system",
            "timestamp": time.time()
        }
        
        # 记录事件
        self.event_recorder.record_event("system_message", event_data)
        
        # 通过队列发送事件
        self._send_event("system_message", event_data)
        
        # 同时调用父类方法保持控制台输出
        super().system_message(message)
        
    def update_player_status(self, players: Dict[str, Dict]) -> None:
        """更新玩家状态"""
        __logger__.info(f"WebUISystem.update_player_status called: {players}")
        alive_players = []
        dead_players = []
        
        for player_id, player_data in players.items():
            player_info = {
                "playerId": player_id,
                "role": player_data.get("role", ""),
                "is_alive": player_data.get("is_alive", True),
                "cause_of_death": player_data.get("cause_of_death", None)
            }
            
            if player_info["is_alive"]:
                alive_players.append(player_info)
            else:
                dead_players.append(player_info)
                
        self.alive_players = alive_players
        self.dead_players = dead_players
        
        event_data = {
            "alive_players": alive_players,
            "dead_players": dead_players,
            "total_alive": len(alive_players),
            "total_dead": len(dead_players)
        }
        
        # 记录事件
        self.event_recorder.record_event("player_status_update", event_data)
        
        # 通过队列发送事件
        self._send_event("player_status_update", event_data)
        
    def game_victory(self, victory_condition: str) -> None:
        """游戏胜利条件达成"""
        event_data = {
            "victory_condition": victory_condition,
            "winner": self._extract_winner(victory_condition),
            "timestamp": time.time()
        }
        
        # 记录事件
        self.event_recorder.record_event("game_victory", event_data)
        
        # 通过队列发送事件
        self._send_event("game_victory", event_data)
        
        # 同时调用父类方法保持控制台输出
        super().system_message(victory_condition)
        
    def vote_result(self, vote_data: Dict[str, int], result: str) -> None:
        """投票结果"""
        event_data = {
            "vote_data": vote_data,
            "result": result,
            "timestamp": time.time()
        }
        
        # 记录事件
        self.event_recorder.record_event("vote_result", event_data)
        
        # 通过队列发送事件
        self._send_event("vote_result", event_data)
        
    def night_action(self, action_type: str, player_id: str, target_id: str, result: str) -> None:
        """夜晚行动结果"""
        event_data = {
            "action_type": action_type,
            "player_id": player_id,
            "target_id": target_id,
            "result": result,
            "timestamp": time.time()
        }
        
        # 记录事件
        self.event_recorder.record_event("night_action", event_data)
        
        # 通过队列发送事件
        self._send_event("night_action", event_data)
        
    def _extract_round_number(self, title: str) -> int:
        """从标题中提取轮次号"""
        try:
            # 假设标题格式为 "轮次 {round}"
            import re
            match = re.search(r'轮次\s*(\d+)', title)
            if match:
                return int(match.group(1))
        except:
            pass
        return 0
        
    def _get_phase_emoji(self, phase: str) -> str:
        """获取阶段的emoji图标"""
        phase_emojis = {
            "💬 发言": "💬",
            "🗳️ 投票": "🗳️",
            "🛡️ 辩护": "🛡️",
            "🌙 夜晚阶段": "🌙",
            "🐺 狼人发言": "🐺",
            "🐺 狼人投票": "🐺",
            "🔮 预言家行动": "🔮",
            "🧙‍♀️ 女巫行动": "🧙‍♀️",
            "🌙 夜晚结果": "🌙"
        }
        return phase_emojis.get(phase, "📋")
        
    def _get_private_speech_visibility(self, role: str) -> list:
        """获取私密发言的可见角色列表"""
        if "狼人" in role:
            return ["🐺 狼人"]
        elif "预言家" in role:
            return ["🔮 预言家"]
        elif "女巫" in role:
            return ["🧙‍♀️ 女巫"]
        else:
            return []
            
    def _extract_winner(self, victory_condition: str) -> str:
        """从胜利条件中提取获胜者"""
        if "狼人" in victory_condition:
            return "狼人"
        elif "村民" in victory_condition:
            return "村民"
        else:
            return "平局"
            
    async def get_game_state(self) -> Dict:
        """获取当前游戏状态"""
        return {
            "current_round": self.current_round,
            "current_phase": self.current_phase,
            "alive_players": self.alive_players,
            "dead_players": self.dead_players,
            "total_alive": len(self.alive_players),
            "total_dead": len(self.dead_players)
        }
        
    async def send_game_state_to_observer(self, observer_id: str):
        """向特定观察者发送游戏状态"""
        game_state = await self.get_game_state()
        await self.websocket_server._send_to_observer(observer_id, {
            "type": "game_state",
            "data": game_state
        }) 