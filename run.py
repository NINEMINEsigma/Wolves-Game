from src.engine.game_engine import *
from src.engine.player_engine import *

__UISystem = UISystem()
__GameController = GameController()
__DaySystem = DaySystem()
__NightSystem = NightSystem()
__PublicMemory = PublicMemory()

class GameEntry:
    def start(self) -> None:
        config = ProjectConfig()
        # 配置游戏房间
        room:Dict[str,int] = config.FindItem("room")
        game:GameController = Architecture.Get(GameController)
        playerId:int = 1
        for playerRole,playerCount in room.items():
            for i in range(playerCount):
                game.add_player(PlayerAgent.create(f"player{playerId}",playerRole))
                playerId += 1
        # 开始游戏
        game.start_game()

entry:GameEntry = GameEntry()

Architecture.RegisterGeneric(
    entry,
     lambda: entry.start(),
     GameController
     )