from src.engine.game_engine import *
from src.engine.player_engine import *

class Game:
    pass

Architecture.RegisterGeneric(
    Game(),
     lambda: Architecture.Get(GameController).start_game(),
     type(GameController)
     )