from game import Game
from role import Role as ROLE

class Player:
    def __init__(self, userid: int, username: str, is_host: bool):
        self.userid: int = userid
        self.tg_name: str = username
        self.role: ROLE | None = None
        self.is_online: bool = True

    def __str__(self):
        return self.tg_name

    def mention(self) -> str:
        """
        Returns a string that mentions the player in Telegram.
        :return: A string formatted for mentioning the player.
        """
        return f'<a href="tg://user?id={self.userid}">{self.tg_name}</a>'

    # def is_creator(self, game: Game) -> bool:
    #     """
    #     Checks if the player is the creator of the game.
    #     :param game: The game instance to check against.
    #     :return: True if the player is the creator, False otherwise.
    #     """
    #     return self.userid == game.creator.userid

    def is_good(self) -> bool:
        """
        Checks if the player's role is a good role.
        :return: True if the player's role is good, False otherwise.
        """
        return self.role[1]
