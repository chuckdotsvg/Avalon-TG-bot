from typing import Any
from .role import Role as ROLE

# each value of the key is a tuple:
# 1st element is the mission team size
# 2nd element is the number of good members
PLAYERS_TO_RULES: dict[int, dict[str, Any]] = {
    5: {"team_sizes": [2, 3, 2, 3, 3], "num_goods": 3},
    6: {"team_sizes": [2, 3, 4, 3, 4], "num_goods": 4},
    7: {"team_sizes": [2, 3, 3, 4, 4], "num_goods": 4},
    8: {"team_sizes": [3, 4, 4, 5, 5], "num_goods": 5},
    9: {"team_sizes": [3, 4, 4, 5, 5], "num_goods": 6},
    10: {"team_sizes": [3, 4, 4, 5, 5], "num_goods": 6},
}

MANDATORY_ROLES: set[ROLE] = {ROLE.MERLIN, ROLE.ASSASSIN}

MAX_TEAM_REJECTS = 5
MAX_PLAYERS = max(PLAYERS_TO_RULES.keys())
MIN_PLAYERS = min(PLAYERS_TO_RULES.keys())
