import random
import constants
from role import Role as ROLE
from gamephase import GamePhase as PHASE
from collections import Counter
from player import Player


class Game:
    def __init__(
        self,
        creator: Player,
        id: int
    ):
        """
        Initialize the Game instance.
        :param id: Unique identifier for the game, takes the group ID.
        :param creator: Player object representing the creator of the game.
        """

        self._id: int = id
        self.turn: int = 0
        self.missions: list[bool | None] = [None, None, None, None, None]
        self.rejection_count: int = 0
        self.votes: list[bool] = []
        self.creator: Player = creator
        self._players: list[Player] = [creator]
        self.team: dict[Player, bool | None] = {}
        self.leader_idx: int = -1
        self.phase: PHASE = PHASE.LOBBY
        self.special_roles: list[ROLE] = [ROLE.MERLIN, ROLE.ASSASSIN]
        self.team_sizes: list[int]

    def add_player(self, player: Player):
        """
        Adds a player to the game.
        :param player: Player object to be added.
        :return: True if the player was added successfully, False otherwise.
        """
        self.players.append(player)


    def remove_player(self, player: Player):
        """
        Removes a player from the game.
        :param player: Player object to be removed.
        """
        self.players.remove(player)

    def check_winner(self) -> bool | None:
        winner = Counter(self.missions).most_common(1)[0][0]

        return winner

    def update_missions(self, mission_votes: list[bool]):
        """
        Updates the missions with the results of the latest missions.
        :param mission_results: List of boolean values indicating if a mission is successful
        """
        self.missions[self.turn] = mission_votes.count(True) >= len(mission_votes) / 2
        self.turn += 1

    def is_vote_successful(self, votes: list[bool]) -> bool:
        """
        Determines if the vote is successful based on the votes received.
        :param votes: List of boolean values indicating the votes from players
        :return: True if the vote is successful, False otherwise
        """

        result = votes.count(True) >= len(votes) / 2
        self.rejection_count += result

        return result

    def add_player_vote(self, player: Player, vote: bool):
        """
        Adds a player's vote to the game.
        :param player: Player object who is voting.
        :param vote: Boolean value indicating the player's vote.
        """
        self.team[player] = vote

        if None not in self.team.values():
            pass
            # call phase handler to manage the next phase

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
    def set_needed_team_members(self, team: list[tuple[str, bool]]):
        pass

    def change_phase(self):
        """
        Changes the phase of the game based on the current phase.
        Called at the end of each phase.
        """
        if self.phase == PHASE.TEAM_SELECTION:
            self.phase = PHASE.QUEST_PHASE
            # fai cose
        elif self.phase == PHASE.QUEST_PHASE:
            if self.check_winner() is not None:
                if not self.check_winner():
                    self.phase = PHASE.GAME_OVER
                else:
                    self.phase = PHASE.LAST_CHANCE
            else:
                self.phase = PHASE.TEAM_SELECTION

    def start_game(self):
        """
        Starts the game by initializing the game state.
        """
        num_players = len(self.players)

        self.team_sizes = constants.playersToRules[num_players][0]
        self.phase = PHASE.TEAM_SELECTION

        # assign roles
        self.set_roles()

        random.shuffle(self.players)
        self.leader_idx = random.randrange(num_players)

    def set_roles(self):
        """
        Assigns roles to players based on the game rules.
        """
        num_players = len(self.players)
        num_of_servants = constants.playersToRules[len(self.players)][1] - [x[1] for x in self.special_roles].count(True)
        num_of_minions = len(self.players) - num_of_servants - len(self.special_roles)

        i = 0
        j = 0

        for i in range(len(self.special_roles)):
            self.players[i].role = self.special_roles[i]

        for j in range(num_of_servants):
            self.players[j + i + 1].role = ROLE.LSOA

        for k in range(num_of_minions):
            self.players[k + j + 1].role = ROLE.MOM

    def voting_phase(self):
        """
        Handles the voting phase of the game.
        """
        self.votes = [False] * len(self.players)
        self.rejection_count = 0
        self.leader_idx = (self.leader_idx + 1) % len(self.players)

    def create_team(self, team: list[Player]):
        """
        Creates a team for the current mission.
        :param team: List of Player objects representing the team members.
        """
        for p in team:
            self.team[p] = None

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
