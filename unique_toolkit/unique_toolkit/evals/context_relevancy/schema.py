from pydantic import BaseModel, Field, create_model
from pydantic.json_schema import SkipJsonSchema

from unique_toolkit.tools.config import get_configuration_dict

from unique_toolkit._common.utils.structured_output.schema import StructuredOutputModel


class StructuredOutputConfig(BaseModel):
    model_config = get_configuration_dict()

    enabled: bool = Field(
        default=False,
        description="Whether to use structured output for the evaluation.",
    )
    extract_fact_list: bool = Field(
        default=False,
        description="Whether to extract a list of relevant facts from context chunks with structured output.",
    )
    reason_description: str = Field(
        default="A brief explanation justifying your evaluation decision.",
        description="The description of the reason field for structured output.",
    )
    value_description: str = Field(
        default="Assessment of how relevant the facts are to the query. Must be one of: ['low', 'medium', 'high'].",
        description="The description of the value field for structured output.",
    )

    fact_description: str = Field(
        default="A fact is an information that is directly answers the user's query. Make sure to emphasize the important information from the fact with bold text.",
        description="The description of the fact field for structured output.",
    )
    fact_list_description: str = Field(
        default="A list of relevant facts extracted from the source that supports or answers the user's query.",
        description="The description of the fact list field for structured output.",
    )


class Fact(StructuredOutputModel):
    fact: str


class EvaluationSchemaStructuredOutput(StructuredOutputModel):
    reason: str
    value: str

    fact_list: list[Fact] = Field(default_factory=list[Fact])

    @classmethod
    def get_with_descriptions(cls, config: StructuredOutputConfig):
        if config.extract_fact_list:
            FactWithDescription = create_model(
                "Fact",
                fact=(str, Field(..., description=config.fact_description)),
                __base__=Fact,
            )
            fact_list_field = (
                list[FactWithDescription],
                Field(
                    description=config.fact_list_description,
                ),
            )
        else:
            fact_list_field = (
                SkipJsonSchema[list[Fact]],
                Field(default_factory=list[Fact]),
            )

        return create_model(
            "EvaluationSchemaStructuredOutputWithDescription",
            reason=(
                str,
                Field(..., description=config.reason_description),
            ),
            value=(
                str,
                Field(..., description=config.value_description),
            ),
            fact_list=fact_list_field,
            __base__=cls,
        )
