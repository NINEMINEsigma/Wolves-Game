from Convention.Convention.Runtime.Config                       import *
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
        base_url=ollama_url,
        **config.FindItem("agent_config",{}),
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

        【强制工具使用】在投票前，你必须先使用get_alive_players工具获取当前存活玩家列表！

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

        if current_player.skill_stats.get("skill_used",True):
            return config.FindItem("Translate",{}).get("skill_already_used","skill already used")

        if targetId == current_player.playerId:
            return config.FindItem("Translate",{}).get("vote_self_not_allowed","vote self is not allowed")

        voteSystem.vote(targetId)
        memory.add_memory(
            current_player.playerId,
            translate.get("vote_target",f"vote target:{targetId}").format(targetId=targetId))
        ui:UISystem = Architecture.Get((UISystem))
        ui.public_speech(
            current_player.playerId,
            current_player.playerRole,
            translate.get("vote_target",f"vote target:{targetId}").format(targetId=targetId))
            
        current_player.skill_stats.update(skill_used=True)

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

        【强制工具使用】在投票前，你必须先使用get_alive_players工具获取当前存活玩家列表！

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
            return config.FindItem("Translate",{}).get("not_vote_phase","not vote phase")
            
        if current_player.skill_stats.get("skill_used",True):
            return config.FindItem("Translate",{}).get("skill_already_used","skill already used")

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

        current_player.skill_stats.update(skill_used=True)

        return config.FindItem("Translate",{}).get("werewolf_vote_success","werewolf vote success")

    @staticmethod
    def seer_investigate(targetId: str) -> None:
        '''
        预言家夜晚查验技能,预言家可以查验一个玩家的身份

        【强制工具使用】在查验前，你必须先使用get_alive_players工具获取当前存活玩家列表！

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

        if current_player.skill_stats.get("skill_used",True):
            return config.FindItem("Translate",{}).get("skill_already_used","skill already used")

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

        current_player.skill_stats.update(skill_used=True)

    @staticmethod
    def witch_save() -> str:
        '''
        女巫夜晚救人技能,女巫可以使用解药救活被狼人击杀的玩家

        【强制工具使用】在救人前，你必须先使用get_night_kill_target工具获取今晚狼人的击杀目标！

        你可以通过get_who_are_you工具获取你自己的targetId

        你可以通过get_player_role工具获取你自己的身份

        你可以通过get_dead_players工具获取所有死亡玩家的列表，请不要尝试解救早已死亡玩家，这会视为无效

        请使用get_alive_players工具获取所有存活玩家的列表，请参考活着的玩家情况来选择是否解救

        你可以通过get_night_kill_target工具获取今晚狼人的击杀目标，请参考击杀目标情况来选择是否解救

        参数：
            无参数

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
        
        if current_player.skill_stats.get("skill_used",True):
            return config.FindItem("Translate",{}).get("skill_already_used","skill already used")

        current_player.skill_stats.update(skill_used=True)

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

        【强制工具使用】在毒人前，你必须先使用get_alive_players工具获取当前存活玩家列表！

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
        
        if current_player.skill_stats.get("skill_used",True):
            return config.FindItem("Translate",{}).get("skill_already_used","skill already used")

        current_player.skill_stats.update(skill_used=True)

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
        获取今晚狼人的击杀目标,用于女巫判断是否救人（当女巫失去解药后将不再能够获取击杀目标）

        返回:
            狼人击杀目标的ID,如果没有则为空
        '''
        night_system:NightSystem = Architecture.Get((NightSystem))
        game: GameController = Architecture.Get((GameController))
        current_player: Player = game.current_player
        if current_player.skill_stats.get("witch_save",False):
            return None
        return night_system.werewolf_kill_target

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

    @staticmethod
    def who_is_werewolf() -> List[str]:
        '''
        获取所有狼人的列表
        '''
        game: GameController = Architecture.Get((GameController))
        return [player.playerId for player in game.players.values() if player.is_werewolf]

#endregion

#region 玩家智能体

class PlayerAgent(Player):
    def get_chat_history(self) -> List[ChatMessage]:
        memory:PublicMemory = Architecture.Get((PublicMemory))
        config = ProjectConfig()
        format_prompt_translate = config.FindItem("Translate",{}).get("prompt",{})
        
        # 获取当前游戏阶段
        game:GameController = Architecture.Get((GameController))
        current_phase = game.current_phase if game else "unknown"
        
        # 创建动态上下文管理器
        context_manager = DynamicContextManager()
        
        # 构建动态提示词
        dynamic_prompt = context_manager.build_dynamic_prompt(self, current_phase)
        
        # 获取基础游戏规则
        game_prompt = config.FindItem("game_prompt", {})
        basic_rules = game_prompt.get("basic_rules", "")
        phase_rules = game_prompt.get("phase_rules", {})
        current_phase_rule = phase_rules.get(current_phase, "")
        
        # 获取角色配置
        role_prompt = config.FindItem("role_prompt", {})
        role_config = role_prompt.get(self.playerRole, {})
        role_introduction = role_config.get("role_introduction", "") if isinstance(role_config, dict) else str(role_config)
        
        # 构建完整的系统提示词
        system_prompt = f"""# 游戏规则
{basic_rules}

# 当前阶段规则
{current_phase_rule}

# 动态上下文
{dynamic_prompt}

# 角色介绍
{role_introduction}

# 工具使用要求
{game_prompt.get("tool_usage_requirements", "")}

# 当前仍存活的玩家
{AgentToolSkills.get_alive_players()}

# 当前已死亡的玩家
{AgentToolSkills.get_dead_players()}

{
f'''
# 当前狼人选择杀害的对象
{AgentToolSkills.get_night_kill_target()}
''' if self.playerRole == config.FindItem("Translate",{}).get("witch","witch") else ""
}
"""
        
        history_memory = memory.read_memory(config.FindItem("allow_memory_stats")[self.playerRole])

        result:List[ChatMessage] = [
            ChatMessage.from_str(
                system_prompt,
                MessageRole.SYSTEM
                ),
            ChatMessage.from_str(
                f"# {format_prompt_translate.get("known_speech_history","known speech history")}\n\n{
                    history_memory
                    }",
                MessageRole.SYSTEM
                )
        ]

        if config.FindItem("history_verbose",False):
            print(f'''
{"-"*10}** get_chat_history **{"-"*10}
{history_memory}
{"-"*10}** get_chat_history **{"-"*10}
''')

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
        config = ProjectConfig()
        agent_config = config.FindItem("react_config", {})
        max_iterations = agent_config.get("max_iterations", 10)  # 增加最大迭代次数
        
        self.agent:     ReActAgent  = ReActAgent.from_tools(
            tools, 
            verbose=config.FindItem("agent_verbose",False),
            max_iterations=max_iterations,  # 设置最大迭代次数
            )

    def play_chat(self, message:str) -> ChatResponse:
        try:
            result:ChatResponse = self.agent.chat(f"{message}",self.get_chat_history())
            return result
        except ValueError as e:
            if "Reached max iterations" in str(e):
                # 当达到最大迭代次数时，提供备用响应
                config = ProjectConfig()
                translate = config.FindItem("Translate",{})
                fallback_message = translate.get('fallback_speech', '我暂时无法详细分析，但我相信我的阵营会取得胜利。')
                
                # 创建一个简单的 ChatResponse 对象
                from llama_index.core.llms import ChatMessage
                fallback_response = ChatMessage(
                    role="assistant",
                    content=fallback_message
                )
                return ChatResponse(message=fallback_response)
            else:
                raise e

    def play_action(self, message:str, tool_choice:str) -> ChatResponse:
        self.skill_stats.update(skill_used=False)
        for _ in range(1):
            if(self.skill_stats.get("skill_used",False)):
                break
            result:ChatResponse = self.agent.chat(f"{message}",self.get_chat_history(),tool_choice=tool_choice)
        if(not self.skill_stats.get("skill_used",False)):
            ui:UISystem = Architecture.Get((UISystem))
            ui.private_speech(self.playerId,self.playerRole,f"没有执行行动")
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
        message =str(self.play_chat(
             f"{translate.get('testament_prompt', 'Please leave your testament.')}"
             ))

        memory:PublicMemory = Architecture.Get((PublicMemory))
        memory.add_memory(
            self.playerId,
            message)
        ui:UISystem = Architecture.Get((UISystem))
        ui.public_speech(
            self.playerId,
            self.playerRole,
            message)

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
        FunctionTool.from_defaults(
            fn=AgentToolSkills.vote,
        ),
        FunctionTool.from_defaults(
            fn=AgentToolSkills.get_alive_players,
            name="get_alive_players",
            description="获取所有存活玩家的列表。这是最重要的工具，在每次行动前都必须先调用此工具！"
        ),
        FunctionTool.from_defaults(
            fn=AgentToolSkills.get_dead_players,
            name="get_dead_players",
            description="获取所有死亡玩家的列表，用于了解游戏状态"
        ),
        FunctionTool.from_defaults(
            fn=AgentToolSkills.playerId_of_myself,
            name="get_who_are_you",
            description="获取玩家自己的ID名称，用于确认自己的身份"
        ),
        FunctionTool.from_defaults(
            fn=AgentToolSkills.playerRole_of_myself,
            name="get_player_role",
            description="获取玩家自己扮演的身份，用于确认自己的角色和阵营"
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
                ),
            FunctionTool.from_defaults(
                fn=AgentToolSkills.who_is_werewolf,
                ),
        ]
        return base_tools + werewolf_tools  # type: ignore
        
    elif player_role == translate.get("seer", "seer"):
        # 预言家专用工具
        seer_tools = [
            FunctionTool.from_defaults(
                fn=AgentToolSkills.seer_investigate,)
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
                fn=AgentToolSkills.get_night_kill_target,)
        ]
        return base_tools + witch_tools  # type: ignore
        
    else:
        # 村民只有基础工具
        return base_tools  # type: ignore

#endregion

#region 动态上下文管理

class DynamicContextManager:
    """动态上下文管理器，负责生成智能体玩家的动态提示词"""
    
    def __init__(self):
        self.config = ProjectConfig()
        self.translate = self.config.FindItem("Translate", {})
        self.dynamic_context = self.config.FindItem("dynamic_context", {})
        self.role_prompt = self.config.FindItem("role_prompt", {})
        self.game_prompt = self.config.FindItem("game_prompt", {})
        
        # 验证配置完整性
        self._validate_config()
    
    def _validate_config(self):
        """验证配置完整性，提供默认值作为备用"""
        # 验证dynamic_context配置
        if not self.dynamic_context:
            self.dynamic_context = {
                "identity_reinforcement": "身份强化提醒：你是{role}，属于{team}阵营。你的名字是{playerId}。",
                "state_awareness": "状态感知提醒：当前游戏阶段是{phase}。",
                "strategy_guidance": "策略指导：{strategy}",
                "tool_enforcement": "工具强制使用：在{action}前，你必须先使用{required_tools}工具。",
                "victory_conditions": "胜利条件：{victory_condition}",
                "phase_specific_prompts": {
                    "night": "夜晚阶段：这是你发挥特殊能力的关键时刻。",
                    "day": "白天阶段：通过发言和投票帮助你的阵营获得胜利。",
                    "vote": "投票阶段：请使用vote工具进行投票。",
                    "speech": "发言阶段：通过发言表达你的分析和判断。"
                }
            }
        
        # 验证role_prompt配置
        if not self.role_prompt:
            self.role_prompt = {
                "狼人": {
                    "identity_statement": "你是狼人阵营的一员，你的名字是{playerId}。",
                    "role_introduction": "夜晚阶段，你可以与其他狼人讨论并选择一个目标进行击杀。",
                    "strategy_guide": {"night": "夜晚策略：选择对狼人阵营威胁最大的目标进行击杀。", "day": "白天策略：伪装成普通村民。"},
                    "victory_path": "获胜路径：通过夜晚击杀和白天伪装，逐步消灭所有村民阵营玩家。",
                    "key_actions": "关键行动：夜晚击杀、白天伪装发言、投票时避免投给同阵营成员。",
                    "tool_priorities": "必需工具：get_alive_players、werewolf_vote、vote"
                }
            }
        
        # 验证game_prompt配置
        if not self.game_prompt:
            self.game_prompt = {
                "basic_rules": "这是一个狼人杀游戏。",
                "phase_rules": {"night": "夜晚阶段：狼人阵营可以击杀一名玩家。", "day": "白天阶段：所有玩家依次发言，然后进行投票。"},
                "victory_conditions": {"werewolf": "狼人阵营胜利条件：消灭所有村民阵营玩家", "villager": "村民阵营胜利条件：消灭所有狼人阵营玩家"},
                "tool_usage_requirements": "重要提醒：在每次行动前，你必须使用get_alive_players工具获取当前存活玩家列表。"
            }
    
    def generate_identity_reinforcement(self, player_role: str, player_id: str) -> str:
        """生成身份强化提示词"""
        try:
            role_config = self.role_prompt.get(player_role, {})
            identity_statement = role_config.get("identity_statement", "")
            
            # 确定阵营
            team = "狼人" if player_role == self.translate.get("werewolf", "werewolf") else "村民"
            
            # 格式化身份声明
            formatted_identity = identity_statement.format(playerId=player_id) if identity_statement else f"你是{player_role}，你的名字是{player_id}。"
            
            # 添加身份强化提醒
            identity_template = self.dynamic_context.get("identity_reinforcement", "")
            identity_reminder = identity_template.format(
                role=player_role,
                team=team,
                playerId=player_id
            ) if identity_template else f"身份强化提醒：你是{player_role}，属于{team}阵营。你的名字是{player_id}。"
            
            return f"{identity_reminder}\n{formatted_identity}"
        except Exception as e:
            # 错误处理：返回基础身份信息
            return f"你是{player_role}，你的名字是{player_id}。"
    
    def generate_state_awareness(self, game_phase: str) -> str:
        """生成状态感知提示词"""
        try:
            state_template = self.dynamic_context.get("state_awareness", "")
            state_reminder = state_template.format(phase=game_phase) if state_template else f"当前游戏阶段是{game_phase}。"
            
            # 添加阶段特定提示
            phase_prompts = self.dynamic_context.get("phase_specific_prompts", {})
            phase_specific = phase_prompts.get(game_phase, "")
            
            return f"{state_reminder}\n{phase_specific}"
        except Exception as e:
            # 错误处理：返回基础状态信息
            return f"当前游戏阶段是{game_phase}。"
    
    def generate_strategy_guidance(self, player_role: str, game_phase: str) -> str:
        """生成策略指导提示词"""
        try:
            role_config = self.role_prompt.get(player_role, {})
            strategy_guide = role_config.get("strategy_guide", {})
            
            # 获取当前阶段的策略
            current_strategy = strategy_guide.get(game_phase, "")
            
            # 获取胜利路径和关键行动
            victory_path = role_config.get("victory_path", "")
            key_actions = role_config.get("key_actions", "")
            
            strategy_template = self.dynamic_context.get("strategy_guidance", "")
            strategy_reminder = strategy_template.format(strategy=current_strategy) if strategy_template and current_strategy else ""
            
            return f"{strategy_reminder}\n获胜路径：{victory_path}\n关键行动：{key_actions}"
        except Exception as e:
            # 错误处理：返回基础策略信息
            return f"请根据你的角色{player_role}在当前阶段{game_phase}进行相应的行动。"
    
    def generate_tool_enforcement(self, required_tools: list) -> str:
        """生成工具强制使用提示词"""
        try:
            if not required_tools:
                return ""
            
            tools_str = "、".join(required_tools)
            tool_template = self.dynamic_context.get("tool_enforcement", "")
            tool_reminder = tool_template.format(
                action="当前行动",
                required_tools=tools_str
            ) if tool_template else f"工具强制使用：在当前行动前，你必须先使用{tools_str}工具获取必要信息。"
            
            return tool_reminder or ""
        except Exception as e:
            # 错误处理：返回基础工具提醒
            return f"请使用{', '.join(required_tools)}工具获取必要信息。" if required_tools else ""
    
    def get_required_tools_for_phase(self, player_role: str, game_phase: str) -> list:
        """根据角色和阶段获取必需的工具"""
        try:
            role_config = self.role_prompt.get(player_role, {})
            tool_priorities = role_config.get("tool_priorities", "")
            
            # 基础必需工具
            base_tools = ["get_alive_players", "get_player_role"]
            
            # 根据阶段添加特定工具
            if game_phase == "vote":
                base_tools.append("vote")
            elif game_phase == "werewolf_vote":
                base_tools.append("werewolf_vote")
            elif game_phase == "seer_action":
                base_tools.append("seer_investigate")
            elif game_phase == "witch_action":
                base_tools.extend(["witch_save", "witch_poison", "get_night_kill_target"])
            
            return base_tools
        except Exception as e:
            # 错误处理：返回基础工具列表
            return ["get_alive_players", "get_player_role"]
    
    def build_dynamic_prompt(self, player: 'Player', game_phase: str) -> str:
        """构建完整的动态提示词"""
        try:
            player_role = player.playerRole
            player_id = player.playerId
            
            # 生成各个部分的提示词
            identity_part = self.generate_identity_reinforcement(player_role, player_id)
            state_part = self.generate_state_awareness(game_phase)
            strategy_part = self.generate_strategy_guidance(player_role, game_phase)
            
            # 获取必需工具
            required_tools = self.get_required_tools_for_phase(player_role, game_phase)
            tool_part = self.generate_tool_enforcement(required_tools)
            
            # 获取胜利条件
            team = "狼人" if player_role == self.translate.get("werewolf", "werewolf") else "村民"
            victory_conditions = self.game_prompt.get("victory_conditions", {})
            victory_condition = victory_conditions.get("werewolf" if team == "狼人" else "villager", "")
            
            victory_template = self.dynamic_context.get("victory_conditions", "")
            victory_part = victory_template.format(victory_condition=victory_condition) if victory_template and victory_condition else f"胜利条件：{victory_condition}"
            
            # 组合所有部分
            dynamic_prompt = f"""
# 身份强化
{identity_part}

# 状态感知
{state_part}

# 策略指导
{strategy_part}

# 胜利条件
{victory_part}

# 工具使用要求
{tool_part}

# 重要提醒
{self.game_prompt.get("tool_usage_requirements", "")}
"""
            
            return dynamic_prompt.strip()
        except Exception as e:
            # 错误处理：返回基础提示词
            return f"""
# 基础信息
你是{player.playerRole}，你的名字是{player.playerId}。
当前游戏阶段是{game_phase}。
请使用get_alive_players工具获取存活玩家列表。
"""

#endregion

