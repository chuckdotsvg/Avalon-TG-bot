from .role import Role as ROLE

class Player:
    def __init__(self, userid: int, username: str):
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

    def is_good(self) -> bool:
        """
        Checks if the player's role is a good role.
        :return: True if the player's role is good, False otherwise.
        """
        return self.role[1]
