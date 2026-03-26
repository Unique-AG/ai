import logging

from pydantic import BaseModel, Field
from unique_toolkit import LanguageModelService
from unique_toolkit.language_model.builder import MessagesBuilder

_LOGGER = logging.getLogger(__name__)
_MAX_RETRIES = 3


class GeneratedPage(BaseModel):
    """Structured output model for LLM-generated web pages."""

    url: str = Field(description="A realistic-looking fake URL for this page")
    title: str = Field(description="HTML page title")
    snippet: str = Field(description="A short meta-description snippet")
    content: str = Field(description="Full HTML content of the page")


async def generate_page(
    *,
    query: str,
    system_prompt: str,
    model_name: str,
    llm_service: LanguageModelService,
) -> GeneratedPage | None:
    """Generate a web page using the LLM with structured output and retries.

    Mirrors the pattern from unique_swot/utils.py generate_structured_output.
    Returns None when every attempt fails.
    """
    _LOGGER.info("Generating page for query: %s", query)

    def _build_messages(error: str | None = None) -> list:
        builder = (
            MessagesBuilder()
            .system_message_append(system_prompt)
            .user_message_append(
                f"Generate a realistic HTML web page about: {query}"
            )
        )
        if error:
            builder.user_message_append(
                f"The following error occurred, please retry and fix the error:\n```{error}```"
            )
        return builder.build()

    last_error = ""
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = await llm_service.complete_async(
                model_name=model_name,
                messages=_build_messages(last_error if last_error else None),
                structured_output_model=GeneratedPage,
                structured_output_enforce_schema=True,
            )
            return GeneratedPage.model_validate(
                response.choices[0].message.parsed
            )
        except Exception as exc:
            last_error = str(exc)
            _LOGGER.exception(
                "Error generating page (attempt %s/%s): %s",
                attempt,
                _MAX_RETRIES,
                last_error,
            )

    _LOGGER.error(
        "Failed to generate page after %s retries: %s",
        _MAX_RETRIES,
        last_error,
    )
    return None
