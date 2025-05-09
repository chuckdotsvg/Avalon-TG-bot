from enum import Enum

class Role(Enum):
    MERLIN = ("Merlin", True)
    LSOA = ("Loyal Servant of Arthur", True)
    ASSASSIN = ("Assassin", False)
    MOM = ("Minion of Mordred", False)

    def get_faction(self) -> str:
        """
        Get the faction of the role.
        :return: True if the role is part of the good faction, False otherwise.
        """
        return "Good" if self.value[1] else "Evil"

    def __getitem__(self, index: int):
        return self.value[index]
