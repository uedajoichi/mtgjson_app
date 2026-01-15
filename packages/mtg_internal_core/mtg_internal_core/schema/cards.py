from pydantic import BaseModel


class CardSchema(BaseModel):
    name: str
    set_code: str | None = None
