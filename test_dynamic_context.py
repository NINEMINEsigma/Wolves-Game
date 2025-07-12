#!/usr/bin/env python3
"""
测试动态上下文管理器的功能
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.engine.player_engine import DynamicContextManager
from src.engine.game_engine import Player

class MockPlayer(Player):
    """模拟玩家类用于测试"""
    def __init__(self, player_id: str, player_role: str):
        super().__init__(player_id, player_role)
    
    def speech(self) -> None:
        pass
    
    def vote(self) -> None:
        pass
    
    def justify(self) -> None:
        pass
    
    def testament(self) -> None:
        pass
    
    def night_private_speech(self) -> None:
        pass
    
    def night_action(self) -> None:
        pass

def test_dynamic_context_manager():
    """测试动态上下文管理器"""
    print("=== 测试动态上下文管理器 ===")
    
    # 创建动态上下文管理器
    context_manager = DynamicContextManager()
    
    # 测试不同角色和阶段
    test_cases = [
        ("狼人", "night", "player1"),
        ("村民", "day", "player2"),
        ("预言家", "seer_action", "player3"),
        ("女巫", "witch_action", "player4"),
    ]
    
    for role, phase, player_id in test_cases:
        print(f"\n--- 测试角色: {role}, 阶段: {phase}, 玩家: {player_id} ---")
        
        # 创建模拟玩家
        player = MockPlayer(player_id, role)
        
        # 生成动态提示词
        dynamic_prompt = context_manager.build_dynamic_prompt(player, phase)
        
        print("生成的动态提示词:")
        print(dynamic_prompt)
        print("-" * 50)
    
    print("\n=== 测试完成 ===")

def test_config_validation():
    """测试配置验证功能"""
    print("\n=== 测试配置验证 ===")
    
    # 测试空配置的情况
    original_config = DynamicContextManager.__init__
    
    def mock_init(self):
        self.config = type('MockConfig', (), {
            'FindItem': lambda self, key, default=None: default or {}
        })()
        self.translate = {}
        self.dynamic_context = {}
        self.role_prompt = {}
        self.game_prompt = {}
        self._validate_config()
    
    # 临时替换初始化方法
    DynamicContextManager.__init__ = mock_init
    
    try:
        context_manager = DynamicContextManager()
        print("配置验证测试通过：空配置时提供了默认值")
        
        # 测试身份强化
        identity = context_manager.generate_identity_reinforcement("狼人", "test_player")
        print(f"身份强化测试: {identity}")
        
    finally:
        # 恢复原始方法
        DynamicContextManager.__init__ = original_config
    
    print("=== 配置验证测试完成 ===")

if __name__ == "__main__":
    test_dynamic_context_manager()
    test_config_validation() 