from pathlib import Path
from enum import Enum


class Role(Enum):
    PERCIVAL = (
        "Percival 🏰",
        True,
    )

    MORGANA = (
        "Morgana 🧛‍♀️",
        False,
    )
    MORDRED = (
        "Mordred 🐉",
        False,
    )
    OBERON = (
        "Oberon 🦄",
        False,
    )

    MERLIN = (
        "Merlin 🧙‍♂️",
        True,
    )
    ASSASSIN = (
        "Assassin 🩸",
        False,
    )

    LSOA = (
        "Loyal Servant of Arthur 🛡️",
        True,
    )
    MOM = (
        "Minion of Mordred 👿",
        False,
    )

    def description(self) -> str:
        filepath = self.role_file

        if filepath.exists():
            content = filepath.read_text(encoding="utf-8").strip()
        else:
            content = f"Description for {self.name} not found."

        return content

    @property
    def role_file(self) -> Path:
        return (
            Path(__file__).parent.parent.parent
            / "resources/roles"
            / f"{self.name.lower()}.html"
        )

    @property
    def is_good(self) -> bool:
        return self.value[1]

    def __getitem__(self, index: int):
        return self.value[index]

    def __str__(self):
        return self.value[0]

    @property
    def is_special(self) -> bool:
        return self not in {self.MOM, self.LSOA}
