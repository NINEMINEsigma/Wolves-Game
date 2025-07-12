from Convention.Convention.Runtime.Architecture                 import Architecture
from Convention.Convention.Runtime.GlobalConfig                 import ProjectConfig

import                                                             logging                                                

from typing                                             import *
from llama_index.core.agent                             import ReActAgent
from llama_index.core.tools                             import BaseTool
from llama_index.core.llms                              import ChatMessage,ChatResponse,MessageRole
from llama_index.core.settings                          import Settings
from llama_index.llms.ollama                            import Ollama

from .game_engine                                       import (
    DaySystem, UISystem, GameController, Player, NightSystem
)

__logger__ = logging.getLogger(__name__)

def SetupLLMSettings() -> None:
    config = ProjectConfig()
    print(config.FindItem("Translate",{}).get("llm_settings_setup","llm settings setup"))
    __logger__.log(
        logging.INFO,
        config.FindItem("Translate",{}).get("llm_settings_registered","llm settings registered")
    )
    config = ProjectConfig()
    ollama_url = config.FindItem("ollama_url", None)
    model = config.FindItem("model")
    Settings.llm = Ollama(
        model=model,
        base_url=ollama_url
    )

SetupLLMSettings()

#region 公共记忆

class PublicMemory:
    def __init__(self) -> None:
        config = ProjectConfig()
        print(config.FindItem("Translate",{}).get("public_memory_registered","public memory registered"))
        self.memory:List[Tuple[str,str,str]] = []
        Architecture.RegisterGeneric(
            self, 
            lambda: __logger__.log(
                logging.INFO,
                config.FindItem("Translate",{}).get("public_memory_registered","public memory registered")
            ), GameController)

    def read_memory(self, allow_stats:List[str]) -> str:
        config = ProjectConfig()
        format_string = config.FindItem("Translate",{}).get("memory_format","- player {playerId} said {stats}: \n{content}")
        all_memory = list([format_string.format(playerId=playerId,stats=stats,content=content) 
            for playerId,stats,content in self.memory if stats in allow_stats])
        max_memory_count = config.FindItem("max_memory_count")
        read_memory = all_memory[-max_memory_count:] if len(all_memory)>max_memory_count else all_memory
        return "---\n".join(read_memory)

    def add_memory(self,playerId:str,stats:str,message:str):
        self.memory.append((playerId,stats,message))

__PublicMemory = PublicMemory()

#endregion

#region 角色功能

class AgentToolSkills:
    @staticmethod
    def speech(message:str) -> None:
        '''
        夜晚过后的发言环节,玩家可以发言,所有玩家都可以听到

        参数:
            message: 玩家发言内容
        '''
        config = ProjectConfig()
        game:GameController = Architecture.Get((GameController))
        current_player:Player = game.current_player
        memory:PublicMemory = Architecture.Get((PublicMemory))
        memory.add_memory(current_player.playerId,config.FindItem("Translate",{}).get("speech","speech"),message)
        ui:UISystem = Architecture.Get((UISystem))
        ui.public_speech(current_player.playerId,current_player.playerRole,message)

    @staticmethod
    def vote(targetId:str) -> None:
        '''
        发言后的投票环节,若存在唯一的得票最多的角色将被放逐(死亡)

        参数:
            targetId: 被投票的玩家ID
        '''
        config = ProjectConfig()
        translate = config.FindItem("Translate",{})
        game:GameController = Architecture.Get((GameController))
        current_player:Player = game.current_player
        voteSystem:DaySystem = Architecture.Get((DaySystem))
        voteSystem.vote(targetId)
        memory:PublicMemory = Architecture.Get((PublicMemory))
        memory.add_memory(current_player.playerId,translate.get("vote","vote"),translate.get("vote_target",f"vote target:{targetId}"))
        ui:UISystem = Architecture.Get((UISystem))
        ui.public_speech(current_player.playerId,current_player.playerRole,translate.get("vote_target",f"vote target:{targetId}"))

    @staticmethod
    def justify(message:str) -> None:
        '''
        出现平票后平票玩家的辩护发言环节,玩家可以辩护,所有玩家都可以听到

        参数:
            message: 玩家辩护内容
        '''
        config = ProjectConfig()
        game:GameController = Architecture.Get((GameController))
        current_player:Player = game.current_player
        memory:PublicMemory = Architecture.Get((PublicMemory))
        memory.add_memory(current_player.playerId,config.FindItem("Translate",{}).get("justify","justify"),message)
        ui:UISystem = Architecture.Get((UISystem))
        ui.public_speech(current_player.playerId,current_player.playerRole,message)

    @staticmethod
    def testament(message:str) -> None:
        '''
        被放逐的玩家的遗言环节,玩家可以留下遗言,所有玩家都可以听到

        参数:
            message: 玩家遗言内容
        '''
        config = ProjectConfig()
        game:GameController = Architecture.Get((GameController))
        current_player:Player = game.current_player
        memory:PublicMemory = Architecture.Get((PublicMemory))
        memory.add_memory(current_player.playerId,config.FindItem("Translate",{}).get("testament","testament"),message)
        ui:UISystem = Architecture.Get((UISystem))
        ui.public_speech(current_player.playerId,current_player.playerRole,message)

    # 夜晚行动技能
    @staticmethod
    def werewolf_kill(targetId: str) -> None:
        '''
        狼人夜晚击杀技能,狼人可以选择一个目标进行击杀

        参数:
            targetId: 被击杀的玩家ID
        '''
        config = ProjectConfig()
        game: GameController = Architecture.Get((GameController))
        current_player: Player = game.current_player
        
        # 验证当前玩家是狼人
        if not current_player.is_werewolf:
            return
            
        # 验证目标玩家存在且存活
        if targetId not in game.players or not game.players[targetId].is_alive:
            return
            
        # 设置狼人击杀目标
        night_system = Architecture.Get((NightSystem))
        night_system.set_night_kill_target(targetId)
        
        # 记录到记忆
        memory: PublicMemory = Architecture.Get((PublicMemory))
        memory.add_memory(current_player.playerId, "werewolf_kill", f"target: {targetId}")
        
        # 私密消息
        ui: UISystem = Architecture.Get((UISystem))
        ui.private_speech(current_player.playerId, current_player.playerRole, 
                         config.FindItem("Translate",{}).get("werewolf_kill_target", f"werewolf kill target: {targetId}"))

    @staticmethod
    def seer_investigate(targetId: str) -> None:
        '''
        预言家夜晚查验技能,预言家可以查验一个玩家的身份

        参数:
            targetId: 被查验的玩家ID
        '''
        config = ProjectConfig()
        game: GameController = Architecture.Get((GameController))
        current_player: Player = game.current_player
        
        # 验证当前玩家是预言家
        if current_player.playerRole != config.FindItem("Translate",{}).get("seer", "seer"):
            return
            
        # 验证目标玩家存在且存活
        if targetId not in game.players or not game.players[targetId].is_alive:
            return
            
        target_player = game.players[targetId]
        result = "werewolf" if target_player.is_werewolf else "villager"
        
        # 设置查验结果
        night_system = Architecture.Get((NightSystem))
        night_system.set_seer_result(f"{targetId}: {result}")
        
        # 记录到记忆
        memory: PublicMemory = Architecture.Get((PublicMemory))
        memory.add_memory(current_player.playerId, "seer_investigate", f"target: {targetId}, result: {result}")
        
        # 私密消息
        ui: UISystem = Architecture.Get((UISystem))
        ui.private_speech(current_player.playerId, current_player.playerRole,
                         config.FindItem("Translate",{}).get("seer_result", f"investigation result: {targetId} is {result}"))

    @staticmethod
    def witch_save(targetId: str) -> None:
        '''
        女巫夜晚救人技能,女巫可以使用解药救活被狼人击杀的玩家

        参数:
            targetId: 被救的玩家ID
        '''
        config = ProjectConfig()
        game: GameController = Architecture.Get((GameController))
        current_player: Player = game.current_player
        
        # 验证当前玩家是女巫
        if current_player.playerRole != config.FindItem("Translate",{}).get("witch", "witch"):
            return
            
        # 验证目标玩家存在且已死亡
        if targetId not in game.players or game.players[targetId].is_alive:
            return
            
        # 检查解药是否已使用
        night_system = Architecture.Get((NightSystem))
        if night_system.is_witch_save_used():
            return
            
        # 使用解药
        night_system.set_witch_save_used(True)
        game.players[targetId].is_alive = True
        game.players[targetId].cause_of_death = None
        
        # 记录到记忆
        memory: PublicMemory = Architecture.Get((PublicMemory))
        memory.add_memory(current_player.playerId, "witch_save", f"target: {targetId}")
        
        # 私密消息
        ui: UISystem = Architecture.Get((UISystem))
        ui.private_speech(current_player.playerId, current_player.playerRole,
                         config.FindItem("Translate",{}).get("witch_save_target", f"witch save target: {targetId}"))

    @staticmethod
    def witch_poison(targetId: str) -> None:
        '''
        女巫夜晚毒人技能,女巫可以使用毒药毒死一个玩家

        参数:
            targetId: 被毒的玩家ID
        '''
        config = ProjectConfig()
        game: GameController = Architecture.Get((GameController))
        current_player: Player = game.current_player
        
        # 验证当前玩家是女巫
        if current_player.playerRole != config.FindItem("Translate",{}).get("witch", "witch"):
            return
            
        # 验证目标玩家存在且存活
        if targetId not in game.players or not game.players[targetId].is_alive:
            return
            
        # 检查毒药是否已使用
        night_system = Architecture.Get((NightSystem))
        if night_system.is_witch_poison_used():
            return
            
        # 使用毒药
        night_system.set_witch_poison_used(True)
        game.players[targetId].kill(config.FindItem("Translate",{}).get("witch_poison", "witch poison"))
        
        # 记录到记忆
        memory: PublicMemory = Architecture.Get((PublicMemory))
        memory.add_memory(current_player.playerId, "witch_poison", f"target: {targetId}")
        
        # 私密消息
        ui: UISystem = Architecture.Get((UISystem))
        ui.private_speech(current_player.playerId, current_player.playerRole,
                         config.FindItem("Translate",{}).get("witch_poison_target", f"witch poison target: {targetId}"))

    @staticmethod
    def get_alive_players() -> str:
        '''
        获取所有存活玩家的列表,用于夜晚行动时选择目标

        返回:
            存活玩家ID列表的字符串表示
        '''
        game: GameController = Architecture.Get((GameController))
        alive_players = [player.playerId for player in game.players.values() if player.is_alive]
        return ", ".join(alive_players)

    @staticmethod
    def get_dead_players() -> str:
        '''
        获取所有死亡玩家的列表,用于女巫救人时选择目标

        返回:
            死亡玩家ID列表的字符串表示
        '''
        game: GameController = Architecture.Get((GameController))
        dead_players = [player.playerId for player in game.players.values() if not player.is_alive]
        return ", ".join(dead_players)

    @staticmethod
    def get_night_kill_target() -> str:
        '''
        获取今晚狼人的击杀目标,用于女巫判断是否救人

        返回:
            狼人击杀目标的ID,如果没有则为空字符串
        '''
        night_system = Architecture.Get((NightSystem))
        target = night_system.get_night_kill_target()
        return target if target else ""

#endregion

#region 玩家智能体

class PlayerAgent(Player):
    def get_chat_history(self) -> List[ChatMessage]:
        memory:PublicMemory = Architecture.Get((PublicMemory))
        config = ProjectConfig()
        format_prompt_translate = config.FindItem("Translate",{}).get("prompt",{})
        result:List[ChatMessage] = [
            ChatMessage.from_str(
                f"# {format_prompt_translate.get("game_rule","game rule")}\n\n{config.FindItem("game_prompt")}"+
                f"# {format_prompt_translate.get("your_role","your role")}\n\n{self.playerRole}"+
                f"# {format_prompt_translate.get("your_role_introduction","your role introduction")}\n\n{config.FindItem("role_prompt")[self.playerRole]}"+
                f"# {format_prompt_translate.get("your_name","your name")}\n\n{self.playerId}"+
                f"# {format_prompt_translate.get("known_speech_history","known speech history")}\n\n{
                    memory.read_memory(config.FindItem("allow_memory_stats")[self.playerRole])
                    }",
                MessageRole.SYSTEM
                ),
        ]
        return result

    def __init__(
        self, 
        tools:      List[BaseTool], 
        playerId:   str,
        playerRole: str
        ) -> None:
        super().__init__(playerId, playerRole)
        self.agent:     ReActAgent  = ReActAgent.from_tools(tools)

    def set_current_player(self) -> None:
        game:GameController = Architecture.Get((GameController))
        game.current_player = self

    def play_chat(self, message:str) -> ChatResponse:
        result:ChatResponse = self.agent.chat(f"{message}",self.get_chat_history())
        return result

    def play_action(self, message:str, tool_choice:str) -> ChatResponse:
        result:ChatResponse = self.agent.chat(f"{message}",self.get_chat_history(),tool_choice=tool_choice)
        return result

    def speech(self) -> None:
        """发言方法"""
        config = ProjectConfig()
        translate = config.FindItem("Translate",{})
        message = f"{translate.get('speech_prompt', 'Please make your speech.')}"
        self.play_chat(message)

    def vote(self) -> None:
        """投票方法"""
        config = ProjectConfig()
        translate = config.FindItem("Translate",{})
        message = f"{translate.get('vote_prompt', 'Please vote for a player to eliminate.')} Available targets: {AgentToolSkills.get_alive_players()}"
        self.play_chat(message)

    def justify(self) -> None:
        """辩护方法"""
        config = ProjectConfig()
        translate = config.FindItem("Translate",{})
        message = f"{translate.get('justify_prompt', 'Please justify your position.')}"
        self.play_chat(message)

    def night_action(self, action_type: str) -> None:
        """夜晚行动方法"""
        config = ProjectConfig()
        translate = config.FindItem("Translate",{})
        
        # 根据角色和行动类型发送相应的提示
        if action_type == "werewolf_kill" and self.is_werewolf:
            message = f"{translate.get('werewolf_night_prompt', 'Werewolves, please discuss and choose a target to kill.')} Available targets: {AgentToolSkills.get_alive_players()}"
            self.play_chat(message)
            
        elif action_type == "seer_investigate" and self.playerRole == translate.get("seer", "seer"):
            message = f"{translate.get('seer_night_prompt', 'Seer, please choose a player to investigate.')} Available targets: {AgentToolSkills.get_alive_players()}"
            self.play_chat(message)
            
        elif action_type == "witch_action" and self.playerRole == translate.get("witch", "witch"):
            night_kill_target = AgentToolSkills.get_night_kill_target()
            if night_kill_target:
                message = f"{translate.get('witch_save_prompt', 'Witch, someone was killed tonight. Do you want to save them?')} Killed player: {night_kill_target}"
                self.play_chat(message)
            else:
                message = f"{translate.get('witch_poison_prompt', 'Witch, do you want to use poison?')} Available targets: {AgentToolSkills.get_alive_players()}"
                self.play_chat(message)

#endregion

#region 工具创建

def create_player_tools(player_role: str) -> List[BaseTool]:
    """为不同角色创建相应的工具集"""
    from llama_index.core.tools import FunctionTool
    
    # 基础工具 - 所有角色都可以使用
    base_tools = [
        FunctionTool.from_defaults(
            fn=AgentToolSkills.speech,
            name="speech",
            description="在白天发言环节进行公开发言"
        ),
        FunctionTool.from_defaults(
            fn=AgentToolSkills.vote,
            name="vote",
            description="在投票环节对某个玩家进行投票"
        ),
        FunctionTool.from_defaults(
            fn=AgentToolSkills.justify,
            name="justify",
            description="在辩护环节进行辩护发言"
        ),
        FunctionTool.from_defaults(
            fn=AgentToolSkills.testament,
            name="testament",
            description="在被放逐后留下遗言"
        ),
        FunctionTool.from_defaults(
            fn=AgentToolSkills.get_alive_players,
            name="get_alive_players",
            description="获取所有存活玩家的列表"
        )
    ]
    
    config = ProjectConfig()
    translate = config.FindItem("Translate",{})
    
    # 根据角色添加特定工具
    if player_role == translate.get("werewolf", "werewolf"):
        # 狼人专用工具
        werewolf_tools = [
            FunctionTool.from_defaults(
                fn=AgentToolSkills.werewolf_kill,
                name="werewolf_kill",
                description="夜晚击杀一个玩家"
            )
        ]
        return base_tools + werewolf_tools  # type: ignore
        
    elif player_role == translate.get("seer", "seer"):
        # 预言家专用工具
        seer_tools = [
            FunctionTool.from_defaults(
                fn=AgentToolSkills.seer_investigate,
                name="seer_investigate",
                description="夜晚查验一个玩家的身份"
            )
        ]
        return base_tools + seer_tools  # type: ignore
        
    elif player_role == translate.get("witch", "witch"):
        # 女巫专用工具
        witch_tools = [
            FunctionTool.from_defaults(
                fn=AgentToolSkills.witch_save,
                name="witch_save",
                description="使用解药救活被狼人击杀的玩家"
            ),
            FunctionTool.from_defaults(
                fn=AgentToolSkills.witch_poison,
                name="witch_poison",
                description="使用毒药毒死一个玩家"
            ),
            FunctionTool.from_defaults(
                fn=AgentToolSkills.get_dead_players,
                name="get_dead_players",
                description="获取所有死亡玩家的列表"
            ),
            FunctionTool.from_defaults(
                fn=AgentToolSkills.get_night_kill_target,
                name="get_night_kill_target",
                description="获取今晚狼人的击杀目标"
            )
        ]
        return base_tools + witch_tools  # type: ignore
        
    else:
        # 村民只有基础工具
        return base_tools  # type: ignore

#endregion

