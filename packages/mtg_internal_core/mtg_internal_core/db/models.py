from dataclasses import dataclass


@dataclass
class CardRow:
    id: int
    name: str
    set_code: str | None = None
