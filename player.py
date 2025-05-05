from role import Role as ROLE

class Player:
    def __init__(self, userid: int):
        self.userid: int = userid
        self.role: ROLE | None = None
        self.isleader: bool = False
        self.isteammate: bool = False

    def __str__(self):
        return f"Player(role={self.role}, isleader={self.isleader}, isteammate={self.isteammate})"

    def buildTeam(self, team: list):
        """
        Build a team with the given players.
        :param team: List of players to be added to the team.
        """
        self.team = team
        for player in team:
            player.isteammate = True
        self.isleader = True
        self.isteammate = True

    def vote(self, player: 'Player') -> bool:
        """
        Vote for a player.
        :param player: The player to vote for.
        """
        if self.isleader:
            print(f"Leader {self} votes for {player}")
        else:
            print(f"Player {self} votes for {player}")


