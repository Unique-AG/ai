import logging
from typing import Annotated, Unpack

from pydantic import BaseModel, ConfigDict, Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.language_model import (
    DEFAULT_LANGUAGE_MODEL,
    LanguageModelMessages,
    LanguageModelService,
    TypeDecoder,
    TypeEncoder,
)
from unique_toolkit.language_model.builder import MessagesBuilder

from unique_web_search.services.content_processing.processing_strategies.base import (
    ProcessingStrategyKwargs,
    WebSearchResult,
)
from unique_web_search.services.content_processing.processing_strategies.prompts import (
    DEFAULT_SANITIZE_GUIDELINE,
    DEFAULT_SYSTEM_PROMPT_TEMPLATE,
    DEFAULT_USER_PROMPT_TEMPLATE,
)

_LOGGER = logging.getLogger(__name__)


class LLMProcessorConfig(BaseModel):
    model_config = get_configuration_dict()

    enabled: bool = Field(
        default=False,
        title="Enable AI Summarization",
        description="When enabled, an AI model processes and summarizes long web page content to extract the most relevant information.",
    )
    sanitize: bool = Field(
        default=False,
        title="Enable Privacy Filtering",
        description="When enabled, instructs the AI to remove personal data (names, emails, phone numbers, etc.) from the content for privacy compliance.",
    )
    sanitize_guideline: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(DEFAULT_SANITIZE_GUIDELINE.split("\n"))
        ),
    ] = Field(
        default=DEFAULT_SANITIZE_GUIDELINE,
        title="Privacy Filtering Instructions",
        description="Instructions given to the AI for identifying and removing personal data. Only used when Privacy Filtering is enabled.",
    )
    language_model: LMI = get_LMI_default_field(DEFAULT_LANGUAGE_MODEL)

    min_tokens: int = Field(
        default=5000,
        title="Minimum Content Length for Summarization",
        description="Web pages with content shorter than this threshold (in tokens) will be kept as-is without AI summarization. Only longer pages are summarized.",
    )
    system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(DEFAULT_SYSTEM_PROMPT_TEMPLATE.split("\n"))
        ),
    ] = Field(
        default=DEFAULT_SYSTEM_PROMPT_TEMPLATE,
        title="AI System Instructions",
        description="Advanced: The system-level instructions given to the AI model. Uses Jinja2 template syntax.",
    )
    user_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(DEFAULT_USER_PROMPT_TEMPLATE.split("\n"))
        ),
    ] = Field(
        default=DEFAULT_USER_PROMPT_TEMPLATE,
        title="AI User Instructions",
        description="Advanced: The per-page instructions given to the AI model. Uses Jinja2 template syntax.",
    )

    def should_run(self, encoder: TypeEncoder, content: str) -> bool:
        # Always run if sanitization is enabled
        if self.sanitize:
            return True

        # Run if content is longer than minimum length
        return len(encoder(content)) > self.min_tokens


class LLMProcessorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sanitized_snippet: str = Field(
        description="The sanitized snippet of the content.",
    )
    sanitized_content: str = Field(
        description="The sanitized content of the page.",
    )
    summary: str = Field(
        description="The summary of the content.",
    )


class LLMProcess:
    def __init__(
        self,
        config: LLMProcessorConfig,
        llm_service: LanguageModelService,
        encoder: TypeEncoder,
        decoder: TypeDecoder,
    ):
        self._config = config
        self._llm_service = llm_service
        self._encoder = encoder
        self._decoder = decoder

    @property
    def is_enabled(self) -> bool:
        return self._config.enabled

    async def __call__(
        self, **kwargs: Unpack[ProcessingStrategyKwargs]
    ) -> WebSearchResult:
        page = kwargs["page"]
        query = kwargs.get("query", None)
        if query is None:
            raise ValueError("Query is required to process page with LLM processor")

        if not self._config.enabled:
            _LOGGER.warning("LLM processor is disabled, skipping")
            return page

        if not self._config.should_run(self._encoder, page.content):
            _LOGGER.warning(
                f"Content is already short enough, skipping LLM processing for page {page.url}"
            )
            return page

        _LOGGER.info(f"Processing page {page.url} with LLM processor")

        messages = (
            MessagesBuilder()
            .system_message_append(
                render_template(
                    self._config.system_prompt,
                    sanitize_guideline=self._config.sanitize_guideline
                    if self._config.sanitize
                    else "",
                )
            )
            .user_message_append(
                render_template(
                    self._config.user_prompt,
                    page=page,
                    query=query,
                )
            )
            .build()
        )

        if self._config.sanitize:
            return await self._handle_sanitization(messages, page)

        return await self._handle_summarization(messages, page)

    async def _handle_sanitization(
        self, messages: LanguageModelMessages, page: WebSearchResult
    ) -> WebSearchResult:
        response = await self._llm_service.complete_async(
            messages=messages,
            model_name=self._config.language_model.name,
            structured_output_model=LLMProcessorResponse,
            structured_output_enforce_schema=True,
        )
        if response.choices[0].message.parsed is None:
            raise ValueError("Failed to parse response")
        parsed = LLMProcessorResponse.model_validate(response.choices[0].message.parsed)

        page.snippet = parsed.sanitized_snippet
        page.content = parsed.sanitized_content

        return page

    async def _handle_summarization(
        self, messages: LanguageModelMessages, page: WebSearchResult
    ) -> WebSearchResult:
        response = await self._llm_service.complete_async(
            messages=messages,
            model_name=self._config.language_model.name,
        )
        if not isinstance(response.choices[0].message.content, str):
            raise ValueError(
                f"Response must be a string, got {type(response.choices[0].message.content)}"
            )

        page.content = response.choices[0].message.content

        return page
