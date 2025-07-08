from enum import Enum

class GamePhase(Enum):
    """
    Enum representing the different phases of a game.
    """
    LOBBY = 0
    BUILD_TEAM = 1
    QUEST = 2
    LAST_CHANCE = 3

    def __str__(self):
        return self.name
