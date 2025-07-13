from typing                                             import *

from Convention.Convention.Runtime.Config            import *
from Convention.Convention.Runtime.Architecture      import Architecture
from Convention.Convention.Runtime.GlobalConfig      import ProjectConfig

from abc                                                import ABC, abstractmethod

import                                                         logging

__logger__ = logging.getLogger(__name__)

class Player(ABC):
    def __init__(self,playerId:str,playerRole:str,*,skill_stats:Dict[str,bool]={}) -> None:
        self.playerId:      str     = playerId
        self.playerRole:    str     = playerRole
        self.is_alive:      bool    = True
        self.cause_of_death:Optional[str] = None
        skill_stats.update(skill_used=False)
        self.skill_stats:   Dict[str,bool] = skill_stats

    def kill(self, cause_of_death:str) -> None:
        if self.is_alive:
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
    def testament(self) -> None:
        pass

    @abstractmethod
    def night_private_speech(self) -> None:
        pass

    @abstractmethod
    def night_action(self) -> None:
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
        config = ProjectConfig()
        ui:UISystem = Architecture.Get(UISystem)
        translate = config.FindItem("Translate",{})

        self.round = 1
        self.current_phase = "night"
        self.current_player = None

        os.system("cls")

        print_colorful(ConsoleFrontColor.GREEN,translate.get("game_start","game start"))

        while True:
            ui.title(translate.get("round","round {round}").format(round=self.round))
            self.start_night()
            if self.check_victory_conditions() is not None:
                break
            self.start_day()
            if self.check_victory_conditions() is not None:
                break
            self.round += 1
        
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
            if not player.is_alive:
                continue
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

    def title(self,title:str) -> None:
        print_colorful(ConsoleFrontColor.RED,f"**{title}**")

    def phase(self,phase:str) -> None:
        print_colorful(ConsoleFrontColor.YELLOW,f"- {phase}")

    def public_speech(self,playerId:str,role:str,message:str) -> None:
        print(f"\t- {ConsoleFrontColor.LIGHTBLUE_EX}{playerId}({role}){ConsoleFrontColor.RESET}：{message}")

    def private_speech(self,playerId:str,role:str,message:str) -> None:
        print(f"\t- {ConsoleFrontColor.BLUE}{playerId}({role}){ConsoleFrontColor.RESET}：{message}")

    def system_message(self,message:str) -> None:
        print_colorful(ConsoleFrontColor.LIGHTGREEN_EX,f"\t- {message}")

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
        if game.check_victory_conditions():
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
            if player.is_alive:
                player.speech()
        # 进入第一轮投票
        ui.phase(vote_translate)
        game.current_phase = vote_translate
        for player in game.players.values():
            game.current_player = player
            if player.is_alive:
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
            if player.is_alive:
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
        game.current_phase = config.FindItem("Translate",{}).get("testament","testament")
        ui:UISystem = Architecture.Get(UISystem)
        ui.system_message(
            config.FindItem("Translate",{}
                ).get("banished_result","banished result:{targetId} has been banished"
                ).format(targetId=targetId)
            )
        game.players[targetId].kill(config.FindItem("Translate",{}).get("banished","banished"))
        game.players[targetId].testament()
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
        self.werewolf_kill_target: Optional[str] = None
        self.werewolf_vote_data:Dict[str,int] = {}

    def start(self) -> None:
        config = ProjectConfig()
        game: GameController = Architecture.Get(GameController)
        ui: UISystem = Architecture.Get(UISystem)
        
        # 检查胜利条件
        if game.check_victory_conditions():
            return
        
        self._werewolf_start()
        ui.system_message(
            config.FindItem("Translate",{}
                ).get("werewolf_current_target","werewolf current target: {targetId}")
                .format(targetId=self.werewolf_kill_target)
                )
        self._witch_start()
        self._seer_start()

        self._execute_night_results()

    def werewolf_vote(self,targetId:str) -> None:
        if targetId not in self.werewolf_vote_data:
            self.werewolf_vote_data[targetId] = 1
        else:
            self.werewolf_vote_data[targetId] += 1

    def _werewolf_vote_result(self) -> None:
        if not self.werewolf_vote_data.values():
            return
        max_vote = max(self.werewolf_vote_data.values())
        for targetId,vote in self.werewolf_vote_data.items():
            if vote == max_vote:
                self.werewolf_kill_target = targetId
                return
        return

    def _werewolf_start(self) -> None:
        """狼人夜晚行动"""
        config = ProjectConfig()
        game: GameController = Architecture.Get(GameController)
        ui: UISystem = Architecture.Get(UISystem)

        werewolves = [player for player in game.players.values() 
                     if player.is_werewolf and player.is_alive]
                     
        self.werewolf_kill_target = None
        self.werewolf_vote_data.clear()
            
        phase = config.FindItem("Translate",{}).get("werewolf_speech","werewolf speech")
        game.current_phase = phase
        ui.phase(phase)
        
        for werewolf in werewolves:
            game.current_player = werewolf
            if werewolf.is_alive:
                werewolf.night_private_speech()
        
        phase = config.FindItem("Translate",{}).get("werewolf_vote","werewolf vote")
        game.current_phase = phase
        ui.phase(phase)
        
        for werewolf in werewolves:
            game.current_player = werewolf
            if werewolf.is_alive:
                werewolf.night_action()

        self._werewolf_vote_result()

    def _seer_start(self) -> None:
        """预言家夜晚行动"""
        config = ProjectConfig()
        game: GameController = Architecture.Get(GameController)
        ui: UISystem = Architecture.Get(UISystem)
        
        seers = [player for player in game.players.values() 
                if player.playerRole == config.FindItem("Translate",{}).get("seer","seer") 
                and player.is_alive]
        
        if not seers:
            return

        phase = config.FindItem("Translate",{}).get("seer_action","seer action")
        game.current_phase = phase
        ui.phase(phase)
        
        for seer in seers:
            game.current_player = seer
            if seer.is_alive:
                seer.night_action()

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

        phase = config.FindItem("Translate",{}).get("witch_action","witch action")
        game.current_phase = phase
        ui.phase(phase)
        
        for witch in witches:
            game.current_player = witch
            if witch.is_alive:
                witch.night_action()
    
    def _execute_night_results(self) -> None:
        """执行夜晚结果"""
        config = ProjectConfig()
        game: GameController = Architecture.Get(GameController)
        ui: UISystem = Architecture.Get(UISystem)
        
        phase = config.FindItem("Translate",{}).get("night_results","night results")
        game.current_phase = phase
        ui.phase(phase)
        
        if self.werewolf_kill_target:
            game.players[self.werewolf_kill_target].kill(
                config.FindItem("Translate",{}).get("werewolf_kill","werewolf kill"))
            ui.system_message(
                config.FindItem("Translate",{}
                    ).get("night_death","night death: {playerId} was killed by werewolves"
                    ).format(playerId=self.werewolf_kill_target)
            )
        else:
            ui.system_message(
                config.FindItem("Translate",{}
                    ).get("night_no_kill","night no kill")
            )

__NightSystem = NightSystem()

#endregion
