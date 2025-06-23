from enum import Enum

class GamePhase(Enum):
    """
    Enum representing the different phases of a game.
    """
    LOBBY = 0
    BUILD_TEAM = 1
    QUEST = 2
    TEAM_VERDICT = 3
    LAST_CHANCE = 4
    GAME_OVER = 5
    PAUSED = 6

    def __str__(self):
        return self.name
