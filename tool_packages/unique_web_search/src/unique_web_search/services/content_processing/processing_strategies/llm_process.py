import logging
from typing import Annotated, Unpack

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.language_model import (
    LanguageModelService,
    TypeDecoder,
    TypeEncoder,
)
from unique_toolkit.language_model.builder import MessagesBuilder

from unique_web_search.services.content_processing.processing_strategies.base import (
    ProcessingStrategyKwargs,
    WebSearchResult,
)
from unique_web_search.services.content_processing.processing_strategies.schema import (
    LLMProcessorResponse,
)
from unique_web_search.services.content_processing.processing_strategies.settings import (
    SanitizeMode,
    processing_strategies_settings,
)

_LOGGER = logging.getLogger(__name__)

_LLM_PROCESSOR_ENV_CONFIG = processing_strategies_settings.llm_processor_config
_UI_DISABLED = bool(_LLM_PROCESSOR_ENV_CONFIG.model_fields_set)


class PrivacyFilterConfig(BaseModel):
    """Privacy filtering settings — controls if and how GDPR Art. 9 data is redacted."""

    model_config = get_configuration_dict()

    sanitize: Annotated[bool, RJSFMetaTag({"ui:disabled": _UI_DISABLED})] = Field(
        default=_LLM_PROCESSOR_ENV_CONFIG.privacy_filter.sanitize,
        validate_default=True,
        title="Enable Privacy Filtering",
        description="When enabled, instructs the AI to remove personal data from the content for privacy compliance.",
    )

    sanitize_mode: Annotated[
        SanitizeMode,
        RJSFMetaTag(
            {
                "ui:disabled": _UI_DISABLED,
                "ui:enumNames": SanitizeMode.get_enum_names(),
            }
        ),
    ] = Field(
        default=_LLM_PROCESSOR_ENV_CONFIG.privacy_filter.sanitize_mode,
        validate_default=True,
        title="Sanitization Pipeline Mode",
        description="Controls how privacy filtering is applied when 'Enable Privacy Filtering' is on.",
    )

    flag_message: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_LLM_PROCESSOR_ENV_CONFIG.privacy_filter.flag_message.split("\n")),
            disabled=_UI_DISABLED,
        ),
    ] = Field(
        default=_LLM_PROCESSOR_ENV_CONFIG.privacy_filter.flag_message,
        validate_default=True,
        title="Sensitive Content Flag Message",
        description="Message that replaces the content and snippet of pages flagged as sensitive when using the 'Judge Only' sanitization mode.",
    )

    sanitize_rules: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(
                _LLM_PROCESSOR_ENV_CONFIG.privacy_filter.sanitize_rules.split("\n")
            ),
            disabled=_UI_DISABLED,
        ),
    ] = Field(
        default=_LLM_PROCESSOR_ENV_CONFIG.privacy_filter.sanitize_rules,
        validate_default=True,
        title="Privacy Filtering Rules",
        description="Rules given to the AI for identifying and removing personal data. Only used when Privacy Filtering is enabled.",
    )


class PromptConfig(BaseModel):
    """Advanced prompt templates — Jinja2 templates sent to the LLM for each page."""

    model_config = get_configuration_dict()

    system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_LLM_PROCESSOR_ENV_CONFIG.prompts.system_prompt.split("\n")),
            disabled=_UI_DISABLED,
        ),
    ] = Field(
        default=_LLM_PROCESSOR_ENV_CONFIG.prompts.system_prompt,
        validate_default=True,
        title="System Instructions",
        description="The system-level instructions for summarize and always-sanitize modes. Uses Jinja2 template syntax.",
    )

    user_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_LLM_PROCESSOR_ENV_CONFIG.prompts.user_prompt.split("\n")),
            disabled=_UI_DISABLED,
        ),
    ] = Field(
        default=_LLM_PROCESSOR_ENV_CONFIG.prompts.user_prompt,
        validate_default=True,
        title="User Instructions",
        description="The per-page user prompt for summarize and always-sanitize modes. Uses Jinja2 template syntax.",
    )

    judge_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_LLM_PROCESSOR_ENV_CONFIG.prompts.judge_prompt.split("\n")),
            disabled=_UI_DISABLED,
        ),
    ] = Field(
        default=_LLM_PROCESSOR_ENV_CONFIG.prompts.judge_prompt,
        validate_default=True,
        title="Judge System Instructions",
        description="System prompt for the lightweight GDPR Art. 9 classification call (Judge Only and Judge then Sanitize modes). Uses Jinja2 template syntax.",
    )

    judge_and_sanitize_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(
                _LLM_PROCESSOR_ENV_CONFIG.prompts.judge_and_sanitize_prompt.split("\n")
            ),
            disabled=_UI_DISABLED,
        ),
    ] = Field(
        default=_LLM_PROCESSOR_ENV_CONFIG.prompts.judge_and_sanitize_prompt,
        validate_default=True,
        title="Judge and Sanitize System Instructions",
        description="System prompt for the single-call classify-and-sanitize mode (Judge and Sanitize). Uses Jinja2 template syntax.",
    )

    page_context_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_LLM_PROCESSOR_ENV_CONFIG.prompts.page_context_prompt.split("\n")),
            disabled=_UI_DISABLED,
        ),
    ] = Field(
        default=_LLM_PROCESSOR_ENV_CONFIG.prompts.page_context_prompt,
        validate_default=True,
        title="Page Context User Prompt",
        description="User prompt template that provides the web page context for the judge call and keyword redact modes. Uses Jinja2 template syntax.",
    )

    keyword_extract_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(
                _LLM_PROCESSOR_ENV_CONFIG.prompts.keyword_extract_prompt.split("\n")
            ),
            disabled=_UI_DISABLED,
        ),
    ] = Field(
        default=_LLM_PROCESSOR_ENV_CONFIG.prompts.keyword_extract_prompt,
        validate_default=True,
        title="Keyword Extraction System Instructions",
        description="System prompt for extracting sensitive verbatim phrases in the Keyword Redact mode. Uses Jinja2 template syntax.",
    )


class LLMProcessorConfig(BaseModel):
    model_config = get_configuration_dict()

    enabled: Annotated[bool, RJSFMetaTag({"ui:disabled": _UI_DISABLED})] = Field(
        default=_LLM_PROCESSOR_ENV_CONFIG.enabled,
        validate_default=True,
        title="Enable AI Summarization",
        description="When enabled, an AI model processes and summarizes long web page content to extract the most relevant information.",
    )

    language_model: Annotated[LMI, RJSFMetaTag({"ui:disabled": _UI_DISABLED})] = (
        get_LMI_default_field(_LLM_PROCESSOR_ENV_CONFIG.language_model)
    )

    min_tokens: Annotated[int, RJSFMetaTag({"ui:disabled": _UI_DISABLED})] = Field(
        default=_LLM_PROCESSOR_ENV_CONFIG.min_tokens,
        validate_default=True,
        title="Minimum Content Length for Summarization",
        description="Web pages with content shorter than this threshold (in tokens) will be kept as-is without AI summarization. Only longer pages are summarized. Ignored when privacy filtering is enabled.",
    )

    privacy_filter: PrivacyFilterConfig = Field(
        default_factory=PrivacyFilterConfig,
        title="Privacy Filtering",
        description="Controls if and how GDPR Art. 9 sensitive data is detected and redacted from web page content.",
    )

    prompts: PromptConfig = Field(
        default_factory=PromptConfig,
        title="Advanced Prompts",
        description="Jinja2 prompt templates sent to the AI model. Edit only if you need to customise the AI instructions.",
    )

    def should_run(self, encoder: TypeEncoder, content: str) -> bool:
        if self.privacy_filter.sanitize:
            return True
        return len(encoder(content)) > self.min_tokens


class LLMProcess:
    def __init__(
        self,
        config: LLMProcessorConfig,
        llm_service: LanguageModelService,
        encoder: TypeEncoder,
        decoder: TypeDecoder,
    ):
        self._config = _merge_config_with_env(config)
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

        _LOGGER.info(
            f"Processing page {page.url} with LLM processor "
            f"(sanitize={self._config.privacy_filter.sanitize}, mode={self._config.privacy_filter.sanitize_mode})"
        )

        if not self._config.privacy_filter.sanitize:
            return await self._run_summarize(**kwargs)

        if self._config.privacy_filter.sanitize_mode == SanitizeMode.KEYWORD_REDACT:
            return await self._run_keyword_redact(**kwargs)

        return await self._run_guard_judge(**kwargs)

    async def _run_keyword_redact(self, **kwargs: Unpack[ProcessingStrategyKwargs]):
        from unique_web_search.services.content_processing.processing_strategies.llm_keyword_redact import (
            LLMKeywordRedact,
        )

        llm_keyword_redact_service = LLMKeywordRedact(
            config=self._config, llm_service=self._llm_service
        )
        return await llm_keyword_redact_service(**kwargs)

    async def _run_guard_judge(self, **kwargs: Unpack[ProcessingStrategyKwargs]):
        from unique_web_search.services.content_processing.processing_strategies.llm_guard_judge import (
            LLMGuardJudge,
        )

        llm_guard_judge_service = LLMGuardJudge(
            config=self._config, llm_service=self._llm_service
        )
        return await llm_guard_judge_service(**kwargs)

    async def _run_summarize(
        self, **kwargs: Unpack[ProcessingStrategyKwargs]
    ) -> WebSearchResult:
        """Baseline mode: summarize page content without any sanitization."""
        page = kwargs["page"]
        query = kwargs.get("query", "")

        messages = (
            MessagesBuilder()
            .system_message_append(
                render_template(
                    self._config.prompts.system_prompt,
                    sanitize=False,
                    sanitize_rules=self._config.privacy_filter.sanitize_rules,
                    output_schema=LLMProcessorResponse.model_json_schema(),
                )
            )
            .user_message_append(
                render_template(
                    self._config.prompts.user_prompt,
                    page=page,
                    query=query,
                    sanitize=False,
                )
            )
            .build()
        )

        response = await self._llm_service.complete_async(
            messages=messages,
            model_name=self._config.language_model.name,
            structured_output_model=LLMProcessorResponse,
            structured_output_enforce_schema=True,
        )

        if response.choices[0].message.parsed is None:
            raise ValueError("Failed to parse response")

        parsed = LLMProcessorResponse.model_validate(response.choices[0].message.parsed)
        return parsed.apply_to_page(page)


def _deep_merge(base: dict, overrides: dict) -> dict:
    """Recursively merge *overrides* into *base*, returning a new dict."""
    merged = {**base}
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _merge_config_with_env(config: LLMProcessorConfig) -> LLMProcessorConfig:
    """Merge space-admin config with env overrides.

    Only fields that were explicitly set in the env JSON take precedence;
    everything else keeps the space-admin's values.
    """
    env_config = processing_strategies_settings.llm_processor_config
    if not env_config.model_fields_set:
        return config

    config_dict = config.model_dump()
    env_overrides = env_config.model_dump(exclude_unset=True)

    return LLMProcessorConfig.model_validate(_deep_merge(config_dict, env_overrides))
