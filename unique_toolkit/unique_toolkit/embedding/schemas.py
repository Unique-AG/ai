from pydantic import BaseModel


class Embeddings(BaseModel):
    embeddings: list[list[float]]
