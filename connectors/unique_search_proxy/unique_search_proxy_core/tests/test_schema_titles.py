from pydantic import BaseModel, Field

from unique_search_proxy_core.schema import field_title_generator, model_title_generator


class SampleRequest(BaseModel):
    search_query: str = Field(description="Query text")


def test_field_title_generator_decamelizes() -> None:
    title = field_title_generator(
        "searchQuery", SampleRequest.model_fields["search_query"]
    )
    assert title == "Search Query"


def test_model_title_generator_decamelizes() -> None:
    assert model_title_generator(SampleRequest) == "Sample Request"
