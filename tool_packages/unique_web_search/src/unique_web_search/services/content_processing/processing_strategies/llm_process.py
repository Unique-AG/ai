import json
import logging
from enum import StrEnum
from typing import Annotated, TypeVar, Unpack

from humps import camelize
from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.language_model import (
    DEFAULT_LANGUAGE_MODEL,
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
    DEFAULT_JUDGE_AND_SANITIZE_PROMPT_TEMPLATE,
    DEFAULT_JUDGE_PROMPT_TEMPLATE,
    DEFAULT_KEYWORD_EXTRACT_PROMPT_TEMPLATE,
    DEFAULT_PAGE_CONTEXT_TEMPLATE,
    DEFAULT_SANITIZE_RULES,
    DEFAULT_SYSTEM_PROMPT_TEMPLATE,
    DEFAULT_USER_PROMPT_TEMPLATE,
)
from unique_web_search.services.content_processing.processing_strategies.schema import (
    LLMProcessorResponse,
)
from unique_web_search.settings import env_settings


class SanitizeMode(StrEnum):
    ALWAYS_SANITIZE = "always_sanitize"
    JUDGE_ONLY = "judge_only"
    JUDGE_AND_SANITIZE = "judge_and_sanitize"
    JUDGE_THEN_SANITIZE = "judge_then_sanitize"
    KEYWORD_REDACT = "keyword_redact"

    @staticmethod
    def get_enum_names() -> list[str]:
        return [
            "Always Sanitize — summarize and redact every page unconditionally",
            "Judge Only — judge first; if flagged, replace content and snippet with a compliance notice",
            "Judge and Sanitize — single LLM call that judges and returns sanitized content when flagged",
            "Judge then Sanitize — judge first; if flagged, run a full summarize-and-sanitize call",
            "Keyword Redact — extract sensitive phrases and apply local regex replacement (no summarization)",
        ]


_DEFAULT_FLAG_MESSAGE = (
    "THIS PAGE MAY CONTAIN SENSITIVE INFORMATION. "
    "ITS CONTENT HAS BEEN WITHHELD FOR COMPLIANCE REASONS. "
    "YOU CAN REFERENCE THE PAGE TO THE USER SO HE CAN EXPLORE THE CONTENT HIMSELF."
)

_LOGGER = logging.getLogger(__name__)


_LLM_PROCESS_CONFIG: dict = json.loads(env_settings.llm_process_config or "{}")

T = TypeVar("T")


def _should_disable_ui_config() -> bool:
    return len(_LLM_PROCESS_CONFIG) > 0


def _get_from_env(key: str, default: T) -> T:
    if key in _LLM_PROCESS_CONFIG:
        return _LLM_PROCESS_CONFIG[key]
    camel = camelize(key)
    if camel in _LLM_PROCESS_CONFIG:
        return _LLM_PROCESS_CONFIG[camel]
    return default


_PRIVACY_FILTER_DEFAULTS = {
    "sanitize": _get_from_env("sanitize", False),
    "sanitize_mode": _get_from_env("sanitize_mode", SanitizeMode.ALWAYS_SANITIZE),
    "flag_message": _get_from_env("flag_message", _DEFAULT_FLAG_MESSAGE),
    "sanitize_rules": _get_from_env("sanitize_rules", DEFAULT_SANITIZE_RULES),
}

_PROMPT_DEFAULTS = {
    "system_prompt": _get_from_env("system_prompt", DEFAULT_SYSTEM_PROMPT_TEMPLATE),
    "user_prompt": _get_from_env("user_prompt", DEFAULT_USER_PROMPT_TEMPLATE),
    "judge_prompt": _get_from_env("judge_prompt", DEFAULT_JUDGE_PROMPT_TEMPLATE),
    "judge_and_sanitize_prompt": _get_from_env(
        "judge_and_sanitize_prompt", DEFAULT_JUDGE_AND_SANITIZE_PROMPT_TEMPLATE
    ),
    "page_context_prompt": _get_from_env(
        "page_context_prompt", DEFAULT_PAGE_CONTEXT_TEMPLATE
    ),
    "keyword_extract_prompt": _get_from_env(
        "keyword_extract_prompt", DEFAULT_KEYWORD_EXTRACT_PROMPT_TEMPLATE
    ),
}

_DEFAULTS = {
    # General
    "enabled": _get_from_env("enabled", False),
    # TODO [UN-17646] Check the Language model selector
    "language_model": _get_from_env("language_model", DEFAULT_LANGUAGE_MODEL),
    "min_tokens": _get_from_env("min_tokens", 5000),
    # Sub-models — keys match LLMProcessorConfig.model_fields
    "privacy_filter": _PRIVACY_FILTER_DEFAULTS,
    "prompts": _PROMPT_DEFAULTS,
}

_UI_DISABLED = _should_disable_ui_config()


class PrivacyFilterConfig(BaseModel):
    """Privacy filtering settings — controls if and how GDPR Art. 9 data is redacted."""

    model_config = get_configuration_dict()

    sanitize: Annotated[bool, RJSFMetaTag({"ui:disabled": _UI_DISABLED})] = Field(
        default=_PRIVACY_FILTER_DEFAULTS["sanitize"],
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
        default=_PRIVACY_FILTER_DEFAULTS["sanitize_mode"],
        validate_default=True,
        title="Sanitization Pipeline Mode",
        description="Controls how privacy filtering is applied when 'Enable Privacy Filtering' is on.",
    )

    flag_message: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_PRIVACY_FILTER_DEFAULTS["flag_message"].split("\n")),
            disabled=_UI_DISABLED,
        ),
    ] = Field(
        default=_PRIVACY_FILTER_DEFAULTS["flag_message"],
        validate_default=True,
        title="Sensitive Content Flag Message",
        description="Message that replaces the content and snippet of pages flagged as sensitive when using the 'Judge Only' sanitization mode.",
    )

    sanitize_rules: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_PRIVACY_FILTER_DEFAULTS["sanitize_rules"].split("\n")),
            disabled=_UI_DISABLED,
        ),
    ] = Field(
        default=_PRIVACY_FILTER_DEFAULTS["sanitize_rules"],
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
            rows=len(_PROMPT_DEFAULTS["system_prompt"].split("\n")),
            disabled=_UI_DISABLED,
        ),
    ] = Field(
        default=_PROMPT_DEFAULTS["system_prompt"],
        validate_default=True,
        title="System Instructions",
        description="The system-level instructions for summarize and always-sanitize modes. Uses Jinja2 template syntax.",
    )

    user_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_PROMPT_DEFAULTS["user_prompt"].split("\n")),
            disabled=_UI_DISABLED,
        ),
    ] = Field(
        default=_PROMPT_DEFAULTS["user_prompt"],
        validate_default=True,
        title="User Instructions",
        description="The per-page user prompt for summarize and always-sanitize modes. Uses Jinja2 template syntax.",
    )

    judge_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_PROMPT_DEFAULTS["judge_prompt"].split("\n")),
            disabled=_UI_DISABLED,
        ),
    ] = Field(
        default=_PROMPT_DEFAULTS["judge_prompt"],
        validate_default=True,
        title="Judge System Instructions",
        description="System prompt for the lightweight GDPR Art. 9 classification call (Judge Only and Judge then Sanitize modes). Uses Jinja2 template syntax.",
    )

    judge_and_sanitize_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_PROMPT_DEFAULTS["judge_and_sanitize_prompt"].split("\n")),
            disabled=_UI_DISABLED,
        ),
    ] = Field(
        default=_PROMPT_DEFAULTS["judge_and_sanitize_prompt"],
        validate_default=True,
        title="Judge and Sanitize System Instructions",
        description="System prompt for the single-call classify-and-sanitize mode (Judge and Sanitize). Uses Jinja2 template syntax.",
    )

    page_context_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_PROMPT_DEFAULTS["page_context_prompt"].split("\n")),
            disabled=_UI_DISABLED,
        ),
    ] = Field(
        default=_PROMPT_DEFAULTS["page_context_prompt"],
        validate_default=True,
        title="Page Context User Prompt",
        description="User prompt template that provides the web page context for the judge call and keyword redact modes. Uses Jinja2 template syntax.",
    )

    keyword_extract_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_PROMPT_DEFAULTS["keyword_extract_prompt"].split("\n")),
            disabled=_UI_DISABLED,
        ),
    ] = Field(
        default=_PROMPT_DEFAULTS["keyword_extract_prompt"],
        validate_default=True,
        title="Keyword Extraction System Instructions",
        description="System prompt for extracting sensitive verbatim phrases in the Keyword Redact mode. Uses Jinja2 template syntax.",
    )


class LLMProcessorConfig(BaseModel):
    model_config = get_configuration_dict()

    enabled: Annotated[bool, RJSFMetaTag({"ui:disabled": _UI_DISABLED})] = Field(
        default=_DEFAULTS["enabled"],
        validate_default=True,
        title="Enable AI Summarization",
        description="When enabled, an AI model processes and summarizes long web page content to extract the most relevant information.",
    )

    language_model: Annotated[LMI, RJSFMetaTag({"ui:disabled": _UI_DISABLED})] = (
        get_LMI_default_field(_DEFAULTS["language_model"])
    )

    min_tokens: Annotated[int, RJSFMetaTag({"ui:disabled": _UI_DISABLED})] = Field(
        default=_DEFAULTS["min_tokens"],
        validate_default=True,
        title="Minimum Content Length for Summarization",
        description="Web pages with content shorter than this threshold (in tokens) will be kept as-is without AI summarization. Only longer pages are summarized. Ignored when privacy filtering is enabled.",
    )

    privacy_filter: PrivacyFilterConfig = Field(
        default_factory=lambda: PrivacyFilterConfig(**_PRIVACY_FILTER_DEFAULTS),
        title="Privacy Filtering",
        description="Controls if and how GDPR Art. 9 sensitive data is detected and redacted from web page content.",
    )

    prompts: PromptConfig = Field(
        default_factory=lambda: PromptConfig(**_PROMPT_DEFAULTS),
        title="Advanced Prompts",
        description="Jinja2 prompt templates sent to the AI model. Edit only if you need to customise the AI instructions.",
    )

    def should_run(self, encoder: TypeEncoder, content: str) -> bool:
        # Always run for any sanitize mode (judge or full sanitize)
        if self.privacy_filter.sanitize:
            return True

        # Run if content is longer than minimum length
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


def _merge_config_with_env(config: LLMProcessorConfig) -> LLMProcessorConfig:
    if not _LLM_PROCESS_CONFIG:
        return config

    config_dict = config.model_dump(by_alias=True)
    env_overrides = LLMProcessorConfig.model_validate(_LLM_PROCESS_CONFIG).model_dump(
        by_alias=True, exclude_unset=True
    )

    updated_config_dict = {**config_dict, **env_overrides}
    return LLMProcessorConfig.model_validate(updated_config_dict)
