from fnmatch import translate
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

    def add_memory(self,playerId:str,message:str):
        game:GameController = Architecture.Get((GameController))
        self.memory.append((playerId,game.current_phase,message))

__PublicMemory = PublicMemory()

#endregion

#region 角色功能

class AgentToolSkills:
    @staticmethod
    def speech(message:str) -> None:
        '''
        夜晚过后的发言环节,玩家可以发言,所有玩家都可以听到

        你可以通过过往的记忆来推断其他玩家的身份

        参数:
            message: 玩家发言内容
        '''
        game:GameController = Architecture.Get((GameController))
        memory:PublicMemory = Architecture.Get((PublicMemory))
        
        current_player:Player = game.current_player
        memory.add_memory(
            current_player.playerId,
            message)
        ui:UISystem = Architecture.Get((UISystem))
        ui.public_speech(
            current_player.playerId,
            current_player.playerRole,
            message)

    @staticmethod
    def vote(targetId:str) -> str:
        '''
        发言后的投票环节,若存在唯一的得票最多的角色将被放逐(死亡)

        你可以通过get_who_are_you工具获取你自己的targetId，请尽量不要投给自己，这很危险

        你可以通过get_player_role工具获取你自己的身份，请不要投给自己阵营的成员，这会降低你的胜率

        你可以通过get_dead_players工具获取所有死亡玩家的列表，请不要投给死亡玩家，这会被算做无效票

        请使用get_alive_players工具获取所有存活玩家的列表，请投给存活玩家

        参数:
            targetId: 被投票的玩家ID

        返回:
            任务状态
        '''
        config = ProjectConfig()
        game:GameController = Architecture.Get((GameController))
        voteSystem:DaySystem = Architecture.Get((DaySystem))
        memory:PublicMemory = Architecture.Get((PublicMemory))

        if game.current_phase != config.FindItem("Translate",{}).get("vote","vote"):
            return config.FindItem("Translate",{}).get("not_vote_phase","not vote phase")

        translate = config.FindItem("Translate",{})
        current_player:Player = game.current_player
        voteSystem.vote(targetId)
        memory.add_memory(
            current_player.playerId,
            translate.get("vote_target",f"vote target:{targetId}").format(targetId=targetId))
        ui:UISystem = Architecture.Get((UISystem))
        ui.public_speech(
            current_player.playerId,
            current_player.playerRole,
            translate.get("vote_target",f"vote target:{targetId}").format(targetId=targetId))

        return config.FindItem("Translate",{}).get("vote_success","vote success")

    @staticmethod
    def justify(message:str) -> None:
        '''
        出现平票后平票玩家的辩护发言环节,玩家可以辩护,所有玩家都可以听到

        参数:
            message: 玩家辩护内容
        '''
        game:GameController = Architecture.Get((GameController))
        memory:PublicMemory = Architecture.Get((PublicMemory))

        current_player:Player = game.current_player
        memory.add_memory(
            current_player.playerId,
            message)
        ui:UISystem = Architecture.Get((UISystem))
        ui.public_speech(
            current_player.playerId,
            current_player.playerRole,
            message)

    @staticmethod
    def testament(message:str) -> None:
        '''
        被放逐的玩家的遗言环节,玩家可以留下遗言,所有玩家都可以听到

        参数:
            message: 玩家遗言内容
        '''
        game:GameController = Architecture.Get((GameController))
        memory:PublicMemory = Architecture.Get((PublicMemory))

        current_player:Player = game.current_player
        memory.add_memory(
            current_player.playerId,
            message)
        ui:UISystem = Architecture.Get((UISystem))
        ui.public_speech(
            current_player.playerId,
            current_player.playerRole,
            message)

    @staticmethod
    def werewolf_private_speech(message:str) -> None:
        '''
        狼人夜晚的群体讨论，所有狼人都可以听到，但是其他玩家看不到

        参数:
            message: 狼人发言内容
        '''
        game:GameController = Architecture.Get((GameController))
        ui:UISystem = Architecture.Get((UISystem))
        memory: PublicMemory = Architecture.Get((PublicMemory))

        current_player:Player = game.current_player
        memory.add_memory(
            current_player.playerId,
            message
            )
        ui.private_speech(
            current_player.playerId,
            current_player.playerRole,
            message)

    @staticmethod
    def werewolf_vote(targetId: str) -> str:
        '''
        狼人夜晚投票技能,狼人可以选择一个目标进行投票,最终会选择一个得票最多的目标击杀

        你可以通过get_who_are_you工具获取你自己的targetId，请尽量不要投给自己，这很危险

        你可以通过get_player_role工具获取你自己的身份，请不要投给自己阵营的成员，这会降低你的胜率

        你可以通过get_dead_players工具获取所有死亡玩家的列表，请不要投给死亡玩家，这会被算做无效票

        请使用get_alive_players工具获取所有存活玩家的列表，请投给存活玩家

        参数:
            targetId: 被投票的玩家ID

        返回:
            任务状态
        '''
        config = ProjectConfig()
        game: GameController = Architecture.Get((GameController))
        night_system:NightSystem = Architecture.Get((NightSystem))
        ui:UISystem = Architecture.Get((UISystem))

        if game.current_phase != config.FindItem("Translate",{}).get("werewolf_vote","werewolf vote"):
            return config.FindItem("Translate",{}).get("not_vote_phase","not vote phase")
            
        current_player: Player = game.current_player
        if targetId not in game.players or not game.players[targetId].is_alive:
            return
            
        night_system.werewolf_vote(targetId)
        
        memory: PublicMemory = Architecture.Get((PublicMemory))
        memory.add_memory(
            current_player.playerId,
            f"target: {targetId}"
            )
        ui.private_speech(
            current_player.playerId,
            current_player.playerRole,
            str(targetId)
            )

        return config.FindItem("Translate",{}).get("werewolf_vote_success","werewolf vote success")

    @staticmethod
    def seer_investigate(targetId: str) -> None:
        '''
        预言家夜晚查验技能,预言家可以查验一个玩家的身份

        你可以通过get_who_are_you工具获取你自己的targetId，请尽量不要查验自己，这毫无意义

        你可以通过get_dead_players工具获取所有死亡玩家的列表，请不要查验死亡玩家，这将会导致查验无效

        请使用get_alive_players工具获取所有存活玩家的列表，请查验存活玩家

        参数:
            targetId: 被查验的玩家ID
        '''
        config = ProjectConfig()
        game: GameController = Architecture.Get((GameController))
        ui: UISystem = Architecture.Get((UISystem))
        memory: PublicMemory = Architecture.Get((PublicMemory))

        current_player: Player = game.current_player
        translate = config.FindItem("Translate",{})
            
        if targetId not in game.players or not game.players[targetId].is_alive:
            return

        message = translate.get("seer_result","investigation result: {targetId} {result}"
                ).format(
                    targetId=targetId,
                    result=translate.get("is_werewolf","is werewolf") 
                    if game.players[targetId].is_werewolf 
                    else translate.get("not_werewolf","not werewolf"))
        memory.add_memory(
            current_player.playerId,
            message
            )
        ui.private_speech(
            current_player.playerId,
            current_player.playerRole,
            message)

    @staticmethod
    def witch_save() -> str:
        '''
        女巫夜晚救人技能,女巫可以使用解药救活被狼人击杀的玩家

        你可以通过get_who_are_you工具获取你自己的targetId

        你可以通过get_player_role工具获取你自己的身份

        你可以通过get_dead_players工具获取所有死亡玩家的列表，请不要尝试解救早已死亡玩家，这会视为无效

        请使用get_alive_players工具获取所有存活玩家的列表，请参考活着的玩家情况来选择是否解救

        你可以通过get_night_kill_target工具获取今晚狼人的击杀目标，请参考击杀目标情况来选择是否解救

        返回:
            任务状态
        '''
        config = ProjectConfig()
        game: GameController = Architecture.Get((GameController))
        ui: UISystem = Architecture.Get((UISystem))
        memory: PublicMemory = Architecture.Get((PublicMemory))
        night_system: NightSystem = Architecture.Get((NightSystem))

        current_player: Player = game.current_player
        translate = config.FindItem("Translate",{})

        if current_player.skill_stats.get("witch_save",False):
            return config.FindItem("Translate",{}).get("witch_save_already","witch save already")

        if night_system.werewolf_kill_target:
            night_system.werewolf_kill_target = None
            message = translate.get("witch_save_target","witch save target: {targetId}"
                    ).format(targetId=night_system.werewolf_kill_target)
            memory.add_memory(
                current_player.playerId,
                message
                )
            ui.private_speech(
                current_player.playerId,
                current_player.playerRole,
                message
                )
            current_player.skill_stats["witch_save"] = False
            return config.FindItem("Translate",{}).get("witch_save_success","witch save success")
        else:
            return config.FindItem("Translate",{}).get("witch_save_not_target","witch save not target")

    @staticmethod
    def witch_poison(targetId: str) -> str:
        '''
        女巫夜晚毒人技能,女巫可以使用毒药毒死一个玩家

        你可以通过get_who_are_you工具获取你自己的targetId，请尽量不要毒害自己，这很危险

        你可以通过get_player_role工具获取你自己的身份，请不要毒害自己阵营的成员，这会降低你的胜率

        你可以通过get_dead_players工具获取所有死亡玩家的列表，请不要毒害死亡玩家，这会被视为无效

        请使用get_alive_players工具获取所有存活玩家的列表，请参考活着的玩家情况来选择是否毒害

        参数:
            targetId: 被毒的玩家ID

        返回:
            任务状态
        '''
        config = ProjectConfig()
        game: GameController = Architecture.Get((GameController))
        ui: UISystem = Architecture.Get((UISystem))
        memory: PublicMemory = Architecture.Get((PublicMemory))

        current_player: Player = game.current_player
        translate = config.FindItem("Translate",{})

        if current_player.skill_stats.get("witch_poison",False):
            return config.FindItem("Translate",{}).get("witch_poison_already","witch poison already")

        if targetId not in game.players or not game.players[targetId].is_alive:
            return config.FindItem("Translate",{}).get("witch_poison_not_target","witch poison not target")

        game.players[targetId].kill(translate.get("witch_kill","witch kill"))
        message = translate.get("witch_poison_target","witch poison target: {targetId}"
                ).format(targetId=targetId)
        memory.add_memory(
            current_player.playerId,
            message
            )
        ui.private_speech(
            current_player.playerId,
            current_player.playerRole,
            message
            )
        current_player.skill_stats["witch_poison"] = False
        return config.FindItem("Translate",{}).get("witch_poison_success","witch poison success")

    @staticmethod
    def get_alive_players() -> List[str]:
        '''
        获取所有存活玩家的列表,用于夜晚行动时选择目标

        返回:
            存活玩家ID列表
        '''
        game: GameController = Architecture.Get((GameController))
        alive_players = [player.playerId for player in game.players.values() if player.is_alive]
        return alive_players

    @staticmethod
    def get_dead_players() -> List[str]:
        '''
        获取所有死亡玩家的列表,用于女巫救人时选择目标

        返回:
            死亡玩家ID列表
        '''
        game: GameController = Architecture.Get((GameController))
        dead_players = [player.playerId for player in game.players.values() if not player.is_alive]
        return dead_players

    @staticmethod
    def get_night_kill_target() -> Optional[str]:
        '''
        获取今晚狼人的击杀目标,用于女巫判断是否救人

        返回:
            狼人击杀目标的ID,如果没有则为空字符串
        '''
        night_system:NightSystem = Architecture.Get((NightSystem))
        return night_system.werewolf_kill_target or ""

    @staticmethod
    def playerId_of_myself() -> str:
        '''
        获取玩家自己的id名称
        '''
        game: GameController = Architecture.Get((GameController))
        current_player: Player = game.current_player
        return current_player.playerId

    @staticmethod
    def playerRole_of_myself() -> str:
        '''
        获取玩家自己扮演的身份
        '''
        game: GameController = Architecture.Get((GameController))
        current_player: Player = game.current_player
        return current_player.playerRole

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
                f"# {format_prompt_translate.get("your_name","your name")}\n\n{self.playerId}",
                MessageRole.SYSTEM
                ),
            ChatMessage.from_str(
                f"# {format_prompt_translate.get("known_speech_history","known speech history")}\n\n{
                    memory.read_memory(config.FindItem("allow_memory_stats")[self.playerRole])
                    }",
                MessageRole.USER
                )
        ]
        return result

    def __init__(
        self, 
        tools:      List[BaseTool], 
        playerId:   str,
        playerRole: str,
        skill_stats:Dict[str,bool]={}
        ) -> None:
        super().__init__(
            playerId,
            playerRole,
            skill_stats=skill_stats
        )
        self.agent:     ReActAgent  = ReActAgent.from_tools(tools, verbose=True)

    def play_chat(self, message:str) -> ChatResponse:
        result:ChatResponse = self.agent.chat(f"{message}",self.get_chat_history())
        return result

    def play_action(self, message:str, tool_choice:str) -> ChatResponse:
        result:ChatResponse = self.agent.chat(f"{message}",self.get_chat_history(),tool_choice=tool_choice)
        return result

    @override
    def speech(self) -> None:
        """发言方法"""
        config = ProjectConfig()
        translate = config.FindItem("Translate",{})
        message = f"{translate.get('speech_prompt', 'Please make your speech.')}"
        AgentToolSkills.speech(str(self.play_chat(message)))

    @override
    def vote(self) -> None:
        """投票方法"""
        config = ProjectConfig()
        translate = config.FindItem("Translate",{})
        message = f"{translate.get('vote_prompt', 'Please vote for a player to eliminate.')} Available targets: {AgentToolSkills.get_alive_players()}"
        self.play_action(message,"vote")

    @override
    def justify(self) -> None:
        """辩护方法"""
        config = ProjectConfig()
        translate = config.FindItem("Translate",{})
        message = f"{translate.get('justify_prompt', 'Please justify your position.')}"
        AgentToolSkills.justify(str(self.play_chat(message)))

    @override
    def testament(self) -> None:
        """遗言方法"""
        config = ProjectConfig()
        translate = config.FindItem("Translate",{})
        message = f"{translate.get('testament_prompt', 'Please leave your testament.')}"
        AgentToolSkills.testament(str(self.play_chat(message)))

    @classmethod
    def create(cls,playerId:str,playerRole:str) -> "PlayerAgent":
        config = ProjectConfig()
        translate = config.FindItem("Translate",{})
        if playerRole == translate.get("werewolf","werewolf"):
            return WerewolfAgent(playerId)
        elif playerRole == translate.get("seer","seer"):
            return SeerAgent(playerId)
        elif playerRole == translate.get("witch","witch"):
            return WitchAgent(playerId)
        else:
            return VillagerAgent(playerId)

class WerewolfAgent(PlayerAgent):
    def __init__(self,playerId:str) -> None:
        config = ProjectConfig()
        playerRole = config.FindItem("Translate",{}).get("werewolf","werewolf")
        super().__init__(
            create_player_tools(playerRole),
            playerId,
            playerRole,
            )
    
    @override
    def night_private_speech(self) -> None:
        """狼人夜晚讨论"""
        config = ProjectConfig()
        message = config.FindItem("Translate",{}).get('werewolf_night_speech_prompt','werewolf,please discuss how to choose a target to kill')
        AgentToolSkills.werewolf_private_speech(str(self.play_chat(message)))

    @override
    def night_action(self) -> None:
        """狼人夜晚投票击杀玩家"""
        config = ProjectConfig()
        self.play_action(
            f"{config.FindItem("Translate",{}
                ).get('werewolf_night_prompt','werewolf,please vote a player to kill')}",
            "werewolf_vote"
            )

class SeerAgent(PlayerAgent):
    def __init__(self,playerId:str) -> None:
        config = ProjectConfig()
        playerRole = config.FindItem("Translate",{}).get("seer","seer")
        super().__init__(
            create_player_tools(playerRole),
            playerId,
            playerRole,
            )
    
    @override
    def night_private_speech(self) -> None:
        """晚上不发言"""
        pass

    @override
    def night_action(self) -> None:
        """预言家在夜晚查验玩家身份"""
        config = ProjectConfig()
        self.play_action(
            f"{config.FindItem("Translate",{}
                ).get('seer_night_prompt','seer,please choose a player to investigate')}",
            "seer_investigate"
            )

class WitchAgent(PlayerAgent):
    def __init__(self,playerId:str) -> None:
        config = ProjectConfig()
        playerRole = config.FindItem("Translate",{}).get("witch","witch")
        super().__init__(
            create_player_tools(playerRole),
            playerId,
            playerRole,
            )
    
    @override
    def night_private_speech(self) -> None:
        """晚上不发言"""
        pass
    
    @override
    def night_action(self) -> None:
        """女巫在夜晚使用药剂"""
        config = ProjectConfig()
        self.play_action(
            f"{config.FindItem("Translate",{}
                ).get('witch_night_prompt','witch,if someone is killed,you can save him or use poison')}",
            "witch_save;witch_poison"
            )

class VillagerAgent(PlayerAgent):
    def __init__(self,playerId:str) -> None:
        config = ProjectConfig()
        playerRole = config.FindItem("Translate",{}).get("villager","villager")
        super().__init__(
            create_player_tools(playerRole),
            playerId,
            playerRole,
            )
    
    @override
    def night_private_speech(self) -> None:
        """晚上不发言"""
        pass

    @override
    def night_action(self) -> None:
        """村民晚上不行动"""
        pass

#endregion

#region 工具创建

def create_player_tools(player_role: str) -> List[BaseTool]:
    """为不同角色创建相应的工具集"""
    from llama_index.core.tools import FunctionTool
    
    # 基础工具 - 所有角色都可以使用
    base_tools = [
        # FunctionTool.from_defaults(
        #     fn=AgentToolSkills.speech,
        # ),
        FunctionTool.from_defaults(
            fn=AgentToolSkills.vote,
            name="vote",
            description="在投票环节对某个玩家进行投票"
        ),
        # FunctionTool.from_defaults(
        #     fn=AgentToolSkills.justify,
        # ),
        # FunctionTool.from_defaults(
        #     fn=AgentToolSkills.testament,
        # ),
        FunctionTool.from_defaults(
            fn=AgentToolSkills.get_alive_players,
        ),
        FunctionTool.from_defaults(
            fn=AgentToolSkills.get_dead_players,
        ),
        FunctionTool.from_defaults(
            fn=AgentToolSkills.playerId_of_myself,
        ),
        FunctionTool.from_defaults(
            fn=AgentToolSkills.playerRole_of_myself,
            name="get_player_role",
            description="获取玩家自己扮演的身份"
        ),
    ]
    
    config = ProjectConfig()
    translate = config.FindItem("Translate",{})
    
    # 根据角色添加特定工具
    if player_role == translate.get("werewolf", "werewolf"):
        # 狼人专用工具
        werewolf_tools = [
            FunctionTool.from_defaults(
                fn=AgentToolSkills.werewolf_vote,
            )
        ]
        return base_tools + werewolf_tools  # type: ignore
        
    elif player_role == translate.get("seer", "seer"):
        # 预言家专用工具
        seer_tools = [
            FunctionTool.from_defaults(
                fn=AgentToolSkills.seer_investigate,
            )
        ]
        return base_tools + seer_tools  # type: ignore
        
    elif player_role == translate.get("witch", "witch"):
        # 女巫专用工具
        witch_tools = [
            FunctionTool.from_defaults(
                fn=AgentToolSkills.witch_save,
            ),
            FunctionTool.from_defaults(
                fn=AgentToolSkills.witch_poison,
            ),
            FunctionTool.from_defaults(
                fn=AgentToolSkills.get_night_kill_target,
            )
        ]
        return base_tools + witch_tools  # type: ignore
        
    else:
        # 村民只有基础工具
        return base_tools  # type: ignore

#endregion

