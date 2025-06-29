import random
import constants
from role import Role as ROLE
from gamephase import GamePhase as PHASE
from collections import Counter
from player import Player


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
        self.votes: list[bool] = []
        self.creator: Player = creator
        self._players: list[Player] = [creator]
        self.team: list[Player] = []
        self.leader_idx: int = -1
        self.phase: PHASE = PHASE.LOBBY
        self.special_roles: list[ROLE] = [ROLE.MERLIN, ROLE.ASSASSIN]
        self.team_sizes: list[int]

    def player_join(self, player: Player):
        """
        Adds a player to the game.
        :param player: Player object to be added.
        """

        if player in self.players:
            index = self.players.index(player)
            if not self.players[index].is_online:
                # player is already in the game, but offline, so set online status to True
                self.players[index].is_online = True
        else:
            # player is not in the game, so add them
            self.players.append(player)

    def player_leave(self, player: Player) -> bool:
        """
        When game is ongoing, "stops" the game, otherwise removes the player from the lobby.
        :param player: Player object to be removed.
        :return: True there is at least one player left/online in the game, False otherwise.
        """
        if player in self.players:
            index = self.players.index(player)
            if self.is_ongoing():
                # if the game is ongoing, set the player as offline
                self.players[index].is_online = False
            else:
                # if the game is in lobby, remove the player from the game
                del self.players[index]

                # if the creator leaves in lobby, give the command to another player
                if self.creator == player:
                    self.creator = self.players[random.randrange(len(self.players))]

        return any(p.is_online for p in self.players)

    def __update_winner(self):
        temp_winner, temp_win_count = Counter(self.missions).most_common(1)[0]

        if self.rejection_count >= constants.MAX_TEAM_REJECTS:
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
        result = self.votes.count(False) <= (
            self.turn + 1 == 4 and len(self.players) >= 7
        )  # consider indexing from 0

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

        result = self.votes.count(True) >= len(self.votes) / 2
        self.__setup_new_election(result)

        # if rejected 3 times, the game is over
        self.__update_winner()

        return result

    def add_player_vote(self, vote: bool) -> bool:
        """
        Adds a player's vote to the game.
        :param vote: Boolean value indicating the player's vote.
        :return: True if the everyone has voted, False otherwise.
        """
        # list of votes is empty at the beginning of the voting phase
        self.votes.append(vote)

        required_votes = len(self.team if self.phase == PHASE.QUEST else self.players)

        return len(self.votes) == required_votes

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

        self.team_sizes = constants.playersToRules[num_players][0]

        random.shuffle(self.players)

        # assign roles
        self.__set_roles()

        self.leader_idx = random.randrange(num_players)

        # finally change the phase to TEAM_BUILD
        self.__change_phase()

    def __set_roles(self):
        """
        Assigns roles to players based on the game rules.
        """
        num_players = len(self.players)
        num_special = len(self.special_roles)
        num_of_servants = constants.playersToRules[num_players][1] - [
            x[1] for x in self.special_roles
        ].count(True)
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
        self.team = team

    def is_ongoing(self) -> bool:
        """
        Checks if the game is currently ongoing.
        :return: True if not in lobby and everyone is online, False otherwise.
        """
        return self.phase != PHASE.LOBBY and False not in [
            p.is_online for p in self.players
        ]

    @property
    def players(self):
        """The players property."""
        return self._players

    @players.setter
    def players(self, value):
        self._players = value

    @property
    def id(self):
        """The id property."""
        return self._id

    @id.setter
    def id(self, value):
        self._id = value
