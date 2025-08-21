import random
from .constants import (
    MAX_PLAYERS,
    MAX_TEAM_REJECTS,
    MIN_PLAYERS,
    PLAYERS_TO_RULES,
    MANDATORY_ROLES,
)
from .role import Role as ROLE
from .gamephase import GamePhase as PHASE
from collections import Counter
from .player import Player


class Game:
    def __init__(self, creator: Player, id: int):
        """
        Initialize the Game instance.
        :param id: Unique identifier for the game, takes the group ID.
        :param creator: Player object representing the creator of the game.
        """

        self._id: int = id
        self.turn: int = 0
        self.missions: list[bool | None] = [None, None, None, None, None]
        self.winner: bool | None = None
        self.rejection_count: int = 0
        self.votes: dict[Player, bool] = {}
        self.creator: Player = creator
        self._players: list[Player] = [creator]
        self.team: list[Player] = []
        self.leader_idx: int = -1
        self.phase: PHASE = PHASE.LOBBY
        self.special_roles: list[ROLE] = list(MANDATORY_ROLES)
        self.team_sizes: list[int]

    def player_join(self, player: Player):
        """
        Adds a player to the game.
        :param player: Player object to be added.
        """

        if len(self.players) >= MAX_PLAYERS:
            raise ValueError("Maximum number of players reached.")

        if player in self.players:
            index = self.players.index(player)
            if not self.players[index].is_online:
                # player is already in the game, but offline, so set online status to True
                self.players[index].is_online = True
            else:
                raise ValueError("Player is already in the game and online.")
        else:
            # player is not in the game, so add them
            self.players.append(player)

        if len(self.players) == MAX_PLAYERS and self.phase == PHASE.LOBBY:
            # if there are enough players, start the game automatically
            self.start_game()

    def player_leave(self, player: Player) -> bool:
        """
        When game is ongoing, "stops" the game, otherwise removes the player from the lobby.
        :param player: Player object to be removed.
        :return: True there is at least one player left/online in the game, False otherwise.
        """
        if player not in self.players:
            raise ValueError("Player not in game.")

        index = self.players.index(player)
        if self.is_ongoing:
            # if the game is ongoing, set the player as offline
            self.players[index].is_online = False
        else:
            # if the game is in lobby, remove the player from the game
            del self.players[index]

            # if the creator leaves in lobby, give the command to another player
            if self.creator == player and len(self.players) > 0:
                self.creator = self.players[random.randrange(len(self.players))]

        return any(p.is_online for p in self.players)

    def pass_creator(self, player: Player):
        """
        Passes the creator role to another player.
        :param player: Player object to whom the creator role is passed.
        """
        if player not in self.players:
            raise ValueError("Player not in game.")
        elif player == self.creator:
            raise ValueError("You are already the creator of the game!")

        self.creator = player

    def __update_winner(self):
        temp_winner, temp_win_count = Counter(self.missions).most_common(1)[0]

        if self.rejection_count >= MAX_TEAM_REJECTS:
            self.winner = False
        elif temp_win_count < len(self.missions) / 2:
            # if there are not enough missions, no winner can be determined
            self.winner = None
        else:
            self.winner = temp_winner

    def update_winner_after_assassination(self, choice_goods_idx: int):
        """
        Handles the assassin's choice at the end of the game.
        :param choice: Player object representing the chosen player.
        """
        goods = [p for p in self.players if p.is_good()]
        choice = goods[choice_goods_idx]

        self.winner = not choice.role == ROLE.MERLIN

    def update_after_mission(self) -> bool:
        """
        Updates the missions with the results of the last votes, and increments the turn.
        :return: True if the mission was successful, False otherwise.
        """
        # if player count is 7 or more, good win if there are 2 or less false votes on the 4th mission
        result = list(self.votes.values()).count(False) <= self.is_special_turn()

        self.missions[self.turn] = result
        self.turn += 1

        self.__update_winner()

        self.__change_phase()

        self.votes.clear()  # clear votes for the next phase

        return result

    def update_after_team_decision(self) -> bool:
        """
        Updates the game state after a team has been approved or rejected.
        :return: True if the team was approved, False otherwise.
        """

        result = list(self.votes.values()).count(True) > len(self.votes) / 2
        self.__setup_new_election(result)

        # if rejected 3 times, the game is over
        self.__update_winner()

        return result

    def add_player_vote(self, player: Player | None, vote: bool) -> bool:
        """
        Adds a player's vote to the game.
        :param vote: Boolean value indicating the player's vote.
        :return: True if the everyone has voted, False otherwise.
        """
        voters = self.team if self.phase == PHASE.QUEST else self.players

        if player not in voters:
            raise ValueError("Player not allowed to vote.")

        self.votes[player] = vote

        required_votes = len(voters)

        return len(self.votes) == required_votes

    def are_enough_players(self) -> bool:
        """
        Checks if there are enough players to start the game with the
        current list of special roles.
        :return: True if there are enough players, False otherwise.
        """
        num_players = len(self.players)
        num_special = len(self.special_roles)
        num_good = len([r for r in self.special_roles if r.is_good])
        num_bad = num_special - num_good

        return (
            (num_players >= self.__required_players)
            and (num_players <= MAX_PLAYERS)
            and (num_good <= PLAYERS_TO_RULES[num_players]["num_goods"])
            and (num_bad <= num_players - PLAYERS_TO_RULES[num_players]["num_goods"])
        )

    @property
    def __required_players(self) -> int:
        """
        Returns the minimum number of players required for the game based on the special roles.
        :return: Minimum number of players required.
        """
        return max(MIN_PLAYERS, len(self.special_roles))

    def set_special_roles(self, roles: list[ROLE]):
        """
        Sets the special roles for the game.
        :param roles: List of ROLE objects representing the special roles.
        """
        if self.phase != PHASE.LOBBY:
            raise ValueError("Cannot set special roles after the game has started.")

        set_roles = set(roles)
        set_roles.update(MANDATORY_ROLES)

        self.special_roles = list(set_roles)

    def lookup_player(self, id: int) -> Player | None:
        """
        Looks up a player by their ID.
        :param id: ID of the player to look up.
        :return: Player object if found, None otherwise.
        """
        for player in self.players:
            if player.userid == id:
                return player

        return None

    # helpers
    def __change_phase(self):
        """
        Changes the phase of the game based on the current phase.
        Called at the end of each phase.
        """
        if self.phase == PHASE.LOBBY:
            self.phase = PHASE.BUILD_TEAM
        elif self.phase == PHASE.BUILD_TEAM:
            self.phase = PHASE.QUEST
        elif self.phase == PHASE.QUEST:
            if self.winner is None:
                self.phase = PHASE.BUILD_TEAM
            elif self.winner:
                self.phase = PHASE.LAST_CHANCE

    def start_game(self):
        """
        Starts the game by initializing the game state.
        """
        num_players = len(self.players)

        self.team_sizes = PLAYERS_TO_RULES[num_players]["team_sizes"]

        # assign roles
        self.__set_roles()

        random.shuffle(self.players)

        self.leader_idx = random.randrange(num_players)

        self.turn += 1
        # finally change the phase to TEAM_BUILD
        self.__change_phase()

    def __set_roles(self):
        """
        Assigns roles to players based on the game rules.
        """
        num_players = len(self.players)
        num_special = len(self.special_roles)
        num_good = PLAYERS_TO_RULES[num_players]["num_goods"]

        if not self.are_enough_players():
            text = (
                "Not enough players for the given special roles.\n"
                f"With {num_players}, include maximum {num_good} good roles"
                f"and {num_players - num_good} evil roles.\n"
            )
            raise ValueError(text)

        num_of_servants = num_good - [x[1] for x in self.special_roles].count(True)
        num_of_minions = num_players - num_of_servants - num_special

        current_index = 0

        # Assign special roles
        for i in range(num_special):
            self.players[current_index].role = self.special_roles[i]
            current_index += 1

        # Assign servant roles
        for _ in range(num_of_servants):
            self.players[current_index].role = ROLE.LSOA
            current_index += 1

        # Assign minion roles
        for _ in range(num_of_minions):
            self.players[current_index].role = ROLE.MOM
            current_index += 1

    def __setup_new_election(self, result: bool):
        """
        Handles the voting phase of the game.
        :param result: Boolean indicating whether the vote was successful.
        """
        # Reset the votes and rejection count for a new election
        self.votes.clear()

        # change phase to QUEST if the team was approved, otherwise stay in BUILD_TEAM
        if result:
            self.__change_phase()

        # if team rejected, increment the rejection count, else reset it
        self.rejection_count = (self.rejection_count + 1) * (not result)

        self.leader_idx = (self.leader_idx + 1) % len(self.players)

    def create_team(self, team: list[Player]):
        """
        Creates a team for the current mission.
        :param team: List of Player objects representing the team members.
        """
        if len(team) != self.team_sizes[self.turn]:
            raise ValueError(
                f"Team size must be {self.team_sizes[self.turn]} for this mission."
            )

        self.team = team

    @property
    def is_ongoing(self) -> bool:
        """
        Checks if the game is currently ongoing.
        :return: True if not in lobby and everyone is online, False otherwise.
        """
        return self.phase != PHASE.LOBBY and False not in [
            p.is_online for p in self.players
        ]

    def is_special_turn(self) -> bool:
        """
        Checks if the fourth mission is special (i.e. admits one failure)
        :return: True if the fourth mission is special, False otherwise.
        """
        return self.turn + 1 == 4 and len(self.players) >= 7

    def evil_list(self, real: bool = True) -> list[Player]:
        """
        Returns a list of players with evil roles.
        :param real: If True, returns players with actual evil roles, including e.g. Mordred
        :return: List of Player objects with evil roles.
        """
        return [
            p
            for p in self.players
            if not p.is_good() and (not real or p.role != ROLE.MORDRED)
        ]

    def roles_to_players(self, roles: set[ROLE]) -> list[Player]:
        """
        Returns a list of players with specific roles.
        :param roles: Set of ROLE objects to filter players by.
        :return: List of Player objects with the specified roles.
        """
        return [p for p in self.players if p.role in roles]

    @property
    def players(self):
        """The players property."""
        return self._players

    @players.setter
    def players(self, value: list[Player]):
        self._players = value

    @property
    def id(self):
        """The id property."""
        return self._id

    @id.setter
    def id(self, value: int):
        self._id = value
