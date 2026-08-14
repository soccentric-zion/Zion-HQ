from pydantic import BaseModel


class Page(BaseModel):
    total: int
    limit: int
    offset: int
