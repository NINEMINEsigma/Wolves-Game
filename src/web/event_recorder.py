import json
import time
import logging
from typing import List, Dict, Optional
from pathlib import Path

from Convention.Convention.Runtime.Architecture import Architecture

__logger__ = logging.getLogger(__name__)

class EventRecorder:
    def __init__(self, log_file: str = "game_events.json"):
        Architecture.RegisterGeneric(
            self,
            lambda: __logger__.info(f"事件录制器初始化，日志文件: {log_file}"),
        )
        self.log_file = Path(log_file)
        self.events: List[Dict] = []
        self.sequence_id = 0
        self.game_start_time = None
        
        # 确保日志目录存在
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        __logger__.info(f"事件录制器初始化，日志文件: {self.log_file}")
        
    def start_game(self):
        """开始记录游戏事件"""
        self.game_start_time = time.time()
        self.sequence_id = 0
        self.events.clear()
        
        # 记录游戏开始事件
        self.record_event("game_start", {
            "timestamp": self.game_start_time,
            "message": "游戏开始"
        })
        
        __logger__.info("开始记录游戏事件")
        
    def end_game(self):
        """结束游戏记录"""
        if self.game_start_time:
            game_duration = time.time() - self.game_start_time
            self.record_event("game_end", {
                "duration": game_duration,
                "total_events": len(self.events),
                "message": "游戏结束"
            })
            
            # 保存事件到文件
            self.save_events()
            __logger__.info(f"游戏结束，共记录 {len(self.events)} 个事件，持续时间: {game_duration:.2f}秒")
            
    def record_event(self, event_type: str, data: dict, timestamp: Optional[float] = None) -> int:
        """记录游戏事件"""
        if timestamp is None:
            timestamp = time.time()
            
        self.sequence_id += 1
        
        event = {
            "sequence_id": self.sequence_id,
            "timestamp": timestamp,
            "event_type": event_type,
            "data": data
        }
        
        self.events.append(event)
        
        __logger__.debug(f"记录事件: {event_type} (序列号: {self.sequence_id})")
        return self.sequence_id
        
    def get_events(self, start_time: Optional[float] = None, 
                   end_time: Optional[float] = None,
                   event_types: Optional[List[str]] = None) -> List[Dict]:
        """获取指定时间范围和类型的事件"""
        filtered_events = self.events
        
        # 按时间过滤
        if start_time is not None:
            filtered_events = [e for e in filtered_events if e["timestamp"] >= start_time]
            
        if end_time is not None:
            filtered_events = [e for e in filtered_events if e["timestamp"] <= end_time]
            
        # 按事件类型过滤
        if event_types is not None:
            filtered_events = [e for e in filtered_events if e["event_type"] in event_types]
            
        return filtered_events
        
    def get_events_by_sequence(self, start_sequence: int, end_sequence: Optional[int] = None) -> List[Dict]:
        """按序列号获取事件"""
        if end_sequence is None:
            end_sequence = self.sequence_id
            
        return [e for e in self.events 
                if start_sequence <= e["sequence_id"] <= end_sequence]
                
    def get_latest_events(self, count: int) -> List[Dict]:
        """获取最新的事件"""
        return self.events[-count:] if self.events else []
        
    def get_game_summary(self) -> Dict:
        """获取游戏摘要信息"""
        if not self.events:
            return {}
            
        event_types = {}
        for event in self.events:
            event_type = event["event_type"]
            event_types[event_type] = event_types.get(event_type, 0) + 1
            
        return {
            "total_events": len(self.events),
            "event_types": event_types,
            "start_time": self.game_start_time,
            "end_time": self.events[-1]["timestamp"] if self.events else None,
            "duration": (self.events[-1]["timestamp"] - self.game_start_time) 
                       if self.events and self.game_start_time else 0
        }
        
    def save_events(self, filename: Optional[str] = None):
        """保存事件到文件"""
        if filename is None:
            filename = self.log_file
            
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    "game_summary": self.get_game_summary(),
                    "events": self.events
                }, f, ensure_ascii=False, indent=2)
                
            __logger__.info(f"事件已保存到: {filename}")
            
        except Exception as e:
            __logger__.error(f"保存事件失败: {e}")
            
    def load_events(self, filename: str) -> bool:
        """从文件加载事件"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.events = data.get("events", [])
            if self.events:
                self.sequence_id = max(e["sequence_id"] for e in self.events)
                self.game_start_time = self.events[0]["timestamp"]
                
            __logger__.info(f"从文件加载了 {len(self.events)} 个事件: {filename}")
            return True
            
        except Exception as e:
            __logger__.error(f"加载事件失败: {e}")
            return False
            
    def clear_events(self):
        """清空所有事件"""
        self.events.clear()
        self.sequence_id = 0
        self.game_start_time = None
        __logger__.info("已清空所有事件")
        
    def get_event_statistics(self) -> Dict:
        """获取事件统计信息"""
        if not self.events:
            return {}
            
        stats = {
            "total_events": len(self.events),
            "event_type_counts": {},
            "time_range": {
                "start": self.events[0]["timestamp"],
                "end": self.events[-1]["timestamp"],
                "duration": self.events[-1]["timestamp"] - self.events[0]["timestamp"]
            }
        }
        
        # 统计事件类型
        for event in self.events:
            event_type = event["event_type"]
            stats["event_type_counts"][event_type] = stats["event_type_counts"].get(event_type, 0) + 1
            
        return stats 