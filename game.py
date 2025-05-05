from gamephase import GamePhase as PHASE
from collections import Counter
from player import Player


class Game:
    def __init__(
        self,
        id: int
    ):
        """
        Initialize the Game instance.
        :param id: Unique identifier for the game, takes the group ID.
        """

        self._id: int = id
        self.turn: int = 0
        self.missions: list[bool | None] = [None, None, None, None, None]
        self.rejection_count: int = 0
        self.team: dict[Player, bool] = {}
        self._players: list[Player] = []
        self.phase: PHASE = PHASE.LOBBY

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
