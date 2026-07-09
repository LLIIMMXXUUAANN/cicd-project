from pydantic import BaseModel, Field


class Quote(BaseModel):
    id: int
    text: str = Field(min_length=1)
    author: str = Field(min_length=1)


class QuoteCreate(BaseModel):
    text: str = Field(min_length=1)
    author: str = Field(min_length=1)
