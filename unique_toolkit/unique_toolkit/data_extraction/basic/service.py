from typing_extensions import override

from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit.data_extraction.base import (
    BaseDataExtractionResult,
    BaseDataExtractor,
    ExtractionSchema,
)
from unique_toolkit.data_extraction.basic.config import (
    StructuredOutputDataExtractorConfig,
)
from unique_toolkit.language_model import LanguageModelService
from unique_toolkit.language_model.builder import MessagesBuilder


class StructuredOutputDataExtractor(BaseDataExtractor):
    """
    Basic Structured Output Data Extraction.
    """

    def __init__(
        self,
        config: StructuredOutputDataExtractorConfig,
        language_model_service: LanguageModelService,
    ):
        self._config = config
        self._language_model_service = language_model_service

    @override
    async def extract_data_from_text(
        self, text: str, schema: type[ExtractionSchema]
    ) -> BaseDataExtractionResult[ExtractionSchema]:
        messages_builder = (
            MessagesBuilder()
            .system_message_append(self._config.system_prompt_template)
            .user_message_append(
                render_template(
                    self._config.user_prompt_template,
                    {
                        "text": text,
                    },
                )
            )
        )
        response = await self._language_model_service.complete_async(
            messages=messages_builder.build(),
            model_name=self._config.language_model.name,
            structured_output_model=schema,
            temperature=0.0,
            structured_output_enforce_schema=self._config.structured_output_enforce_schema,
        )

        return BaseDataExtractionResult(
            data=schema.model_validate(response.choices[0].message.parsed),
        )
