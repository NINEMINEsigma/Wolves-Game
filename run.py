from src.engine.game_engine import *
from src.engine.player_engine import *

class GameEntry:
    def start(self) -> None:
        config = ProjectConfig()
        room:Dict[str,int] = config.FindItem("room")
        game:GameController = Architecture.Get(GameController)
        playerId:int = 1
        for playerRole,playerCount in room.items():
            for i in range(playerCount):
                game.add_player(PlayerAgent(
                        create_player_tools(playerRole),
                        f"player{playerId}",
                        playerRole
                    ))
                playerId += 1
        Architecture.Get(GameController).start_game()

Architecture.RegisterGeneric(
    GameEntry(),
     lambda: Architecture.Get(GameEntry).start(),
     type(GameEntry)
     )