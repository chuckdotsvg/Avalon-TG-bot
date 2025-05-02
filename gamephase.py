from enum import Enum

class GamePhase(Enum):
    """
    Enum representing the different phases of a game.
    """
    LOBBY = 0
    TEAM_SELECTION = 1
    QUEST_PHASE = 2
    GAME_OVER = 3
    PAUSED = 4

    def __str__(self):
        return self.name
