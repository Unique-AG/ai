from pydantic import BaseModel


class WebPageChunk(BaseModel):
    url: str
    display_link: str
    title: str
    snippet: str
    content: str
    order: str
