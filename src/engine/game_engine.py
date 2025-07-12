from typing                                             import *

from Convention.Convention.Runtime.Config            import *
from Convention.Convention.Runtime.Architecture      import Architecture
from Convention.Convention.Runtime.GlobalConfig      import ProjectConfig

from abc                                                import ABC, abstractmethod

import                                                         logging

__logger__ = logging.getLogger(__name__)

class Player(ABC):
    def __init__(self,playerId:str,playerRole:str) -> None:
        self.playerId:      str     = playerId
        self.playerRole:    str     = playerRole
        self.is_alive:      bool    = True
        self.cause_of_death:Optional[str] = None

    def kill(self, cause_of_death:str) -> None:
        self.is_alive = False
        self.cause_of_death = cause_of_death

    @property
    def is_werewolf(self) -> bool:
        config = ProjectConfig()
        return self.playerRole == config.FindItem("Translate",{}).get("werewolf","werewolf")
    
    @property
    def is_villager(self) -> bool:
        config = ProjectConfig()
        return self.playerRole == config.FindItem("Translate",{}).get("villager","villager")

    @abstractmethod
    def speech(self) -> None:
        pass
    
    @abstractmethod
    def vote(self) -> None:
        pass
    
    @abstractmethod
    def justify(self) -> None:
        pass
    
    @abstractmethod
    def night_action(self, action_type: str) -> None:
        pass

#region 游戏主控

class GameController:
    def __init__(self) -> None:
        config = ProjectConfig()
        print(config.FindItem("Translate",{}).get("game_controller_registered","game controller registered"))
        Architecture.RegisterGeneric(
            self,
            lambda: __logger__.log(
                logging.INFO,
                config.FindItem("Translate",{}).get("game_controller_registered","game controller registered")
            ))
        self.players:           Dict[str,Player]    = {}
        self.current_player:    Player              = None
        self.current_phase:     str                 = "night"
        self.round:             int                 = 0
        self.victory_conditions:Optional[str]       = None
        
    def start_game(self) -> None:
        self.round = 1
        self.current_phase = "night"
        self.current_player = None

        while True:
            self.start_night()
            if self.check_victory_conditions() is not None:
                break
            self.start_day()
            if self.check_victory_conditions() is not None:
                break
            self.round += 1
        
        ui:UISystem = Architecture.Get(UISystem)
        ui.system_message(self.victory_conditions)
    
    def add_player(self, player:Player) -> None:
        self.players[player.playerId] = player

    def start_day(self) -> None:
        Architecture.Get(DaySystem).start()

    def start_night(self) -> None:
        Architecture.Get(NightSystem).start()

    def check_victory_conditions(self) -> Optional[str]:
        if self.victory_conditions is not None:
            return self.victory_conditions
        config = ProjectConfig()
        translate = config.FindItem("Translate",{})
        has_villager_alive = False
        has_werewolf_alive = False
        for player in self.players.values():
            if player.is_villager:
                has_villager_alive = True
            if player.is_werewolf:
                has_werewolf_alive = True
        if not has_villager_alive:
            self.victory_conditions = translate.get("werewolf_victory","werewolf victory")
        if not has_werewolf_alive:
            self.victory_conditions = translate.get("villager_victory","villager victory")
        if not has_villager_alive and not has_werewolf_alive:
            self.victory_conditions = translate.get("draw","draw")
        return self.victory_conditions
        
__GameController = GameController()

#endregion

#region 游戏流程展示

class UISystem:
    def __init__(self) -> None:
        config = ProjectConfig()
        print(config.FindItem("Translate",{}).get("ui_system_registered","ui system registered"))
        Architecture.RegisterGeneric(
            self,
            lambda: __logger__.log(
                logging.INFO,
                config.FindItem("Translate",{}).get("ui_system_registered","ui system registered")
            )
        )

    def title(self,title:str,level:int=1) -> None:
        print(f"{'#'*level} {title}")

    def phase(self,phase:str) -> None:
        print(f"- {phase}")

    def public_speech(self,playerId:str,role:str,message:str) -> None:
        print(f"\t- {playerId}({role})：{message}")

    def private_speech(self,playerId:str,role:str,message:str) -> None:
        print(f"\t- {playerId}({role})：{message}")

    def system_message(self,message:str) -> None:
        print(f"\t- {message}")

__UISystem = UISystem()

#endregion

#region 发言-投票[-辩护-投票]-放逐 白天环节

class DaySystem:
    def __init__(self) -> None:
        Architecture.RegisterGeneric(
            self,
            lambda: None,
            GameController
        )
        self.vote_data:Dict[str,int] = {}

    def start(self) -> None:
        game:GameController = Architecture.Get(GameController)
        ui:UISystem = Architecture.Get(UISystem)
        # 检查胜利条件
        victory_condition = game.check_victory_conditions()
        if victory_condition:
            return

        self._speech_and_vote()

    def _speech_and_vote(self) -> None:
        self.vote_data.clear()
        
        config = ProjectConfig()
        ui:UISystem = Architecture.Get(UISystem)
        game:GameController = Architecture.Get(GameController)
        speech_translate = config.FindItem("Translate",{}).get("speech","speech")
        vote_translate = config.FindItem("Translate",{}).get("vote","vote")
        # 进入发言阶段
        ui.phase(speech_translate)
        game.current_phase = speech_translate
        for player in game.players.values():
            game.current_player = player
            player.speech()
        # 进入第一轮投票
        ui.phase(vote_translate)
        game.current_phase = vote_translate
        for player in game.players.values():
            game.current_player = player
            player.vote()
        # 第一轮投票结束
        result = self._check_vote_result()
        if len(result) == 1:
            self._banished(result[0])
        else:
            self._justify_and_vote(result)
    
    def _justify_and_vote(self, targetIds:List[str]) -> None:
        self.vote_data.clear()

        config = ProjectConfig()
        ui:UISystem = Architecture.Get(UISystem)
        game:GameController = Architecture.Get(GameController)
        justify_translate = config.FindItem("Translate",{}).get("justify","justify")
        vote_translate = config.FindItem("Translate",{}).get("vote","vote")
        # 进入辩护发言阶段
        ui.phase(justify_translate)
        game.current_phase = justify_translate
        for targetId in targetIds:
            game.current_player = game.players[targetId]
            game.current_player.justify()
        # 进入第二轮投票
        ui.phase(vote_translate)
        game.current_phase = vote_translate
        for player in game.players.values():
            game.current_player = player
            player.vote()
        result = self._check_vote_result()
        # 辩护发言与第二轮投票结束
        if len(result) == 1:
            self._banished(result[0])
        else:
            self._abandon_banishment()

    def vote(self,targetId:str) -> None:
        if targetId not in self.vote_data:
            self.vote_data[targetId] = 1
        else:
            self.vote_data[targetId] += 1

    def _check_vote_result(self) -> List[str]:
        result:List[str] = []
        cur:int = 0
        for targetId,vote in self.vote_data.items():
            if vote > cur:
                cur = vote
                result.append(targetId)
        return result

    def _banished(self, targetId:str) -> None:
        config = ProjectConfig()
        game:GameController = Architecture.Get(GameController)
        game.players[targetId].kill(config.FindItem("Translate",{}).get("banished","banished"))
        ui:UISystem = Architecture.Get(UISystem)
        ui.system_message(
            config.FindItem("Translate",{}).get("banished_result",f"banished result:{targetId} has been banished")
            )
        self._back_to_day_system()

    def _abandon_banishment(self) -> None:
        config = ProjectConfig()
        ui:UISystem = Architecture.Get(UISystem)
        ui.system_message(
            config.FindItem("Translate",{}).get("abandon_banishment",f"no one has been banished")
            )
        self._back_to_day_system()

    def _back_to_day_system(self) -> None:
        pass
        
__DaySystem = DaySystem()

#endregion

#region 拥有夜晚行动能力的角色依次进行{群体讨论/思考-决策发动技能} 夜晚环节

class NightSystem:
    def __init__(self) -> None:
        Architecture.RegisterGeneric(
            self,
            lambda: None,
            GameController
        )
        self.night_kill_target: Optional[str] = None
        self.seer_investigation_result: Optional[str] = None
        self.witch_save_used: bool = False
        self.witch_poison_used: bool = False

    def start(self) -> None:
        config = ProjectConfig()
        ui: UISystem = Architecture.Get(UISystem)
        game: GameController = Architecture.Get(GameController)
        
        # 检查胜利条件
        victory_condition = game.check_victory_conditions()
        if victory_condition:
            return
        
        ui.phase(config.FindItem("Translate",{}).get("night_phase","night phase"))
        game.current_phase = "night"
        
        self._werewolf_start()
        self._seer_start()
        self._witch_start()
        
        # 执行夜晚结果
        self._execute_night_results()

    def _werewolf_start(self) -> None:
        """狼人夜晚行动"""
        config = ProjectConfig()
        game: GameController = Architecture.Get(GameController)
        ui: UISystem = Architecture.Get(UISystem)
        
        # 获取所有存活的狼人
        werewolves = [player for player in game.players.values() 
                     if player.is_werewolf and player.is_alive]
        
        if not werewolves:
            return
            
        ui.phase(config.FindItem("Translate",{}).get("werewolf_action","werewolf action"))
        
        # 狼人群体讨论和投票
        werewolf_votes = {}
        for werewolf in werewolves:
            game.current_player = werewolf
            werewolf.night_action("werewolf_kill")
            
            # 这里假设狼人通过night_action方法进行投票
            # 实际实现中需要从AI响应中获取投票结果
            # 暂时使用随机选择作为示例
            import random
            alive_villagers = [p for p in game.players.values() 
                             if p.is_villager and p.is_alive]
            if alive_villagers:
                target = random.choice(alive_villagers).playerId
                werewolf_votes[target] = werewolf_votes.get(target, 0) + 1
        
        # 确定狼人击杀目标
        if werewolf_votes:
            max_votes = max(werewolf_votes.values())
            candidates = [target for target, votes in werewolf_votes.items() 
                         if votes == max_votes]
            if len(candidates) == 1:
                self.night_kill_target = candidates[0]

    def _seer_start(self) -> None:
        """预言家夜晚行动"""
        config = ProjectConfig()
        game: GameController = Architecture.Get(GameController)
        ui: UISystem = Architecture.Get(UISystem)
        
        # 获取存活的预言家
        seers = [player for player in game.players.values() 
                if player.playerRole == config.FindItem("Translate",{}).get("seer","seer") 
                and player.is_alive]
        
        if not seers:
            return
            
        ui.phase(config.FindItem("Translate",{}).get("seer_action","seer action"))
        
        for seer in seers:
            game.current_player = seer
            seer.night_action("seer_investigate")

    def _witch_start(self) -> None:
        """女巫夜晚行动"""
        config = ProjectConfig()
        game: GameController = Architecture.Get(GameController)
        ui: UISystem = Architecture.Get(UISystem)
        
        # 获取存活的女巫
        witches = [player for player in game.players.values() 
                  if player.playerRole == config.FindItem("Translate",{}).get("witch","witch") 
                  and player.is_alive]
        
        if not witches:
            return
            
        ui.phase(config.FindItem("Translate",{}).get("witch_action","witch action"))
        
        for witch in witches:
            game.current_player = witch
            witch.night_action("witch_action")

    def _execute_night_results(self) -> None:
        """执行夜晚结果"""
        config = ProjectConfig()
        game: GameController = Architecture.Get(GameController)
        ui: UISystem = Architecture.Get(UISystem)
        
        # 处理狼人击杀
        if self.night_kill_target and self.night_kill_target in game.players:
            target_player = game.players[self.night_kill_target]
            if target_player.is_alive:
                target_player.kill(config.FindItem("Translate",{}).get("werewolf_kill","werewolf kill"))
                ui.system_message(
                    config.FindItem("Translate",{}).get("night_death",f"night death: {self.night_kill_target} was killed by werewolves")
                )
        
        # 重置夜晚状态
        self.night_kill_target = None
        self.seer_investigation_result = None

    def get_night_kill_target(self) -> Optional[str]:
        """获取狼人击杀目标"""
        return self.night_kill_target

    def set_night_kill_target(self, target: str) -> None:
        """设置狼人击杀目标"""
        self.night_kill_target = target

    def get_seer_result(self) -> Optional[str]:
        """获取预言家查验结果"""
        return self.seer_investigation_result

    def set_seer_result(self, result: str) -> None:
        """设置预言家查验结果"""
        self.seer_investigation_result = result

    def is_witch_save_used(self) -> bool:
        """检查女巫解药是否已使用"""
        return self.witch_save_used

    def set_witch_save_used(self, used: bool) -> None:
        """设置女巫解药使用状态"""
        self.witch_save_used = used

    def is_witch_poison_used(self) -> bool:
        """检查女巫毒药是否已使用"""
        return self.witch_poison_used

    def set_witch_poison_used(self, used: bool) -> None:
        """设置女巫毒药使用状态"""
        self.witch_poison_used = used

__NightSystem = NightSystem()

#endregion
