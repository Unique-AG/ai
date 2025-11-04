from pydantic import BaseModel, Field


class Embeddings(BaseModel):
    embeddings: list[list[float]] = Field(description="The embeddings of the text")
