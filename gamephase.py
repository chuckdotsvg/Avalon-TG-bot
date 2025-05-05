from enum import Enum

class GamePhase(Enum):
    """
    Enum representing the different phases of a game.
    """
    LOBBY = 0
    TEAM_SELECTION = 1
    QUEST_PHASE = 2
    LAST_CHANCE = 3
    GAME_OVER = 4
    PAUSED = 5

    def __str__(self):
        return self.name
