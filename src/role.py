from enum import Enum
import os


class Role(Enum):
    MERLIN = (
        "Merlin 🧙‍♂️",
        True,
    )
    LSOA = (
        "Loyal Servant of Arthur 🛡️",
        True,
    )

    ASSASSIN = (
        "Assassin 🩸",
        False,
    )
    MOM = (
        "Minion of Mordred 👿",
        False,
    )

    def description(self) -> str:
        filename = f"{self.name.lower()}.md"
        filepath = os.path.join("/resources/roles/", filename)

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as file:
                return file.read()
        else:
            return "Description not found."

    def __getitem__(self, index: int):
        return self.value[index]

    def __str__(self):
        return self.value[0]
