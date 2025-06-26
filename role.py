from enum import Enum


class Role(Enum):
    MERLIN = (
        "Merlin 🧙‍♂️",
        True,
        (
            "You know who the evil players are, help the good team win!\n"
            "But don't be too obvious, or the Assassin could kill you at the end of the game.\n"
        ),
    )
    LSOA = (
        "Loyal Servant of Arthur 🛡️",
        True,
        "No special abilities, just defend the honor of goods!",
    )

    ASSASSIN = (
        "Assassin 🩸",
        False,
        (
            "You are the last chance for the evil team to win if 3 mission are succesful:\n"
            "If you manage to kill Merlin at the end of the game, evil team wins!\n"
        ),
    )
    MOM = (
        "Minion of Mordred 👿",
        False,
        "No special abilites, just sow discord among players!",
    )

    # def get_faction(self) -> str:
    #     """
    #     Get the faction of the role.
    #     :return: True if the role is part of the good faction, False otherwise.
    #     """
    #     return "Good" if self.value[1] else "Evil"

    def description(self) -> str:
        return self.value[2]

    def __getitem__(self, index: int):
        return self.value[index]

    def __str__(self):
        return self.value[0]
