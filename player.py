from role import Role as ROLE

class Player:
    def __init__(self, userid: int, username: str):
        self.userid: int = userid
        self.tg_name: str = username
        self.role: ROLE | None = None
        self.is_teammate: bool = False

    def __str__(self):
        return f"Player(role={self.role})"

    def vote(self, player: 'Player') -> bool:
        """
        Vote for a player.
        :param player: The player to vote for.
        """
        return True
