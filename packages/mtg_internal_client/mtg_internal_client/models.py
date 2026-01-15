from dataclasses import dataclass


@dataclass
class Card:
    name: str
    set_code: str | None = None
    mana_cost: str | None = None
