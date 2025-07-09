from enum import Enum

class GamePhase(Enum):
    """
    Enum representing the different phases of a game.
    """
    LOBBY = 0
    PREPARATION = 1
    BUILD_TEAM = 2
    QUEST = 3
    LAST_CHANCE = 4

    def __str__(self):
        return self.name
