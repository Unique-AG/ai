import logging
from typing import TypeVar, Unpack

from pydantic import BaseModel, ConfigDict, Field
from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit.language_model import LanguageModelService
from unique_toolkit.language_model.builder import MessagesBuilder

from unique_web_search.services.content_processing.processing_strategies.base import (
    ProcessingStrategyKwargs,
    WebSearchResult,
)
from unique_web_search.services.content_processing.processing_strategies.llm_process import (
    LLMProcessorConfig,
    SanitizeMode,
)

_LOGGER = logging.getLogger(__name__)

_JUDGE_TASK_PREFIX = (
    "Evaluate the following web page for GDPR Art. 9 sensitive personal data."
)

_T = TypeVar("_T", bound=BaseModel)


class LLMGuardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(
        description=(
            "FILL THIS FIRST. A concise, step-by-step account of your GDPR Art. 9 compliance review. "
            "List every category of sensitive data you identified on the page (e.g. health, religion, sexual orientation), "
            "name the individuals it pertains to, explain why each item falls under Art. 9, "
            "and state which redaction tag was applied. "
            "If no sensitive data was found, explicitly confirm that the page contains no Art. 9 data. "
            "This field is audited — vague or incomplete reasoning is not acceptable."
        ),
    )

    sanitized_snippet: str = Field(
        description=(
            "A short, self-contained excerpt (2-3 sentences) capturing the most relevant finding from the page "
            "in relation to the search query. "
            "Every piece of GDPR Art. 9 sensitive data — including health conditions, diagnoses, treatments, "
            "religious or philosophical beliefs, political opinions, sexual orientation, gender identity, "
            "racial or ethnic origin, trade union membership, genetic data, and biometric data — "
            "must be replaced inline with the appropriate typed redaction tag "
            "(e.g. [RedactHealth], [RedactReligiousBelief], [RedactPoliticalOpinion], [RedactSexualOrientation], "
            "[RedactRacialOrEthnic], [RedactTradeUnion], [RedactGeneticData], [RedactBiometricData]). "
            "This applies to all individuals mentioned, not only the subject of the search query. "
            "The surrounding sentence structure must remain intact and readable."
        ),
    )

    sanitized_summary: str = Field(
        description=(
            "A comprehensive summary of the page content focused on information relevant to the search query. "
            "Preserves key facts, data points, dates, statistics, and conclusions — "
            "except any that constitute GDPR Art. 9 sensitive data, which must be replaced inline with the appropriate "
            "typed redaction tag (e.g. [RedactHealth], [RedactReligiousBelief], [RedactPoliticalOpinion], "
            "[RedactSexualOrientation], [RedactRacialOrEthnic], [RedactTradeUnion], [RedactGeneticData], [RedactBiometricData]). "
            "Applies to all individuals mentioned on the page. "
            "A less complete summary that is fully sanitized is always preferred over a complete summary containing sensitive data."
        ),
    )

    def apply_to_page(self, page: WebSearchResult) -> WebSearchResult:
        page.snippet = self.sanitized_snippet
        page.content = self.sanitized_summary
        return page


class JudgeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(
        description=(
            "FILL THIS FIRST. A concise, step-by-step reasoning that justifies the classification below. "
            "List every piece of GDPR Art. 9 sensitive data found on the page (e.g. health conditions, political opinions, "
            "religious beliefs, sexual orientation, racial or ethnic origin, trade union membership, genetic or biometric data) "
            "and the individuals it pertains to. "
            "If no sensitive data was found, explicitly confirm that the page contains no Art. 9 data. "
            "This field is audited — produce your reasoning before setting needs_sanitization."
        )
    )

    needs_sanitization: bool = Field(
        description=(
            "Set to true if the page contains GDPR Art. 9 special-category personal data "
            "(health/medical, political opinions, religious/philosophical beliefs, racial or ethnic origin, "
            "sexual orientation, trade union membership, genetic data, biometric data) about any identifiable individual. "
            "Set to false if the page contains no such data."
        )
    )


class JudgeAndSanitizeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(
        description=(
            "FILL THIS FIRST. A concise, step-by-step account of your GDPR Art. 9 compliance review. "
            "List every category of sensitive data you identified on the page (e.g. health, religion, sexual orientation), "
            "name the individuals it pertains to, explain why each item falls under Art. 9, "
            "and state which redaction tag was applied. "
            "If no sensitive data was found, explicitly confirm that the page contains no Art. 9 data."
        ),
    )

    needs_sanitization: bool = Field(
        description=(
            "Set to true if any GDPR Art. 9 sensitive data was found and redacted. "
            "Set to false if the page contains no Art. 9 data (in which case sanitized_snippet and "
            "sanitized_summary mirror the original content)."
        )
    )

    sanitized_snippet: str = Field(
        description=(
            "A short, self-contained excerpt (2-3 sentences) capturing the most relevant finding from the page "
            "in relation to the search query. "
            "Every piece of GDPR Art. 9 sensitive data must be replaced inline with the appropriate typed redaction tag "
            "(e.g. [RedactHealth], [RedactReligiousBelief], [RedactPoliticalOpinion], [RedactSexualOrientation], "
            "[RedactRacialOrEthnic], [RedactTradeUnion], [RedactGeneticData], [RedactBiometricData]). "
            "If needs_sanitization is false, reproduce the original snippet without modification."
        ),
    )

    sanitized_summary: str = Field(
        description=(
            "A comprehensive summary of the page content focused on information relevant to the search query. "
            "Preserves key facts, data points, dates, statistics, and conclusions — "
            "except any that constitute GDPR Art. 9 sensitive data, which must be replaced inline with the appropriate "
            "typed redaction tag. "
            "If needs_sanitization is false, reproduce the original content summary without modification."
        ),
    )

    def apply_to_page(self, page: WebSearchResult) -> WebSearchResult:
        page.snippet = self.sanitized_snippet
        page.content = self.sanitized_summary
        return page


class LLMGuardJudge:
    """LLM-based judge for GDPR Art. 9 compliance checks.

    Exposes two public methods that map directly to the pipeline modes that involve a
    judge step:

    - ``judge_only`` — lightweight classification call using the dedicated judge prompt.
      Returns the original page unmodified; the caller handles flagging.
    - ``judge_and_sanitize`` — single structured-output call that classifies and, when
      flagged, returns sanitized content/snippet in one round trip.

    Both methods share the ``_complete`` helper which handles message construction, the
    LLM call, and response parsing.
    """

    def __init__(
        self,
        config: LLMProcessorConfig,
        llm_service: LanguageModelService,
    ):
        self._config = config
        self._llm_service = llm_service

    async def __call__(
        self, **kwargs: Unpack[ProcessingStrategyKwargs]
    ) -> WebSearchResult:
        """Dispatch to the appropriate sanitization flow based on ``sanitize_mode``."""
        mode = self._config.privacy_filter.sanitize_mode

        if mode == SanitizeMode.ALWAYS_SANITIZE:
            return await self.sanitize_page(**kwargs)

        if mode == SanitizeMode.JUDGE_ONLY:
            needs_sanitization, _ = await self.judge_only(**kwargs)
            page = kwargs["page"]
            if not needs_sanitization:
                _LOGGER.info(
                    f"Page {page.url} does not require sanitization — keeping as-is"
                )
                return page
            _LOGGER.info(
                f"Page {page.url} flagged — replacing content with flag message"
            )
            return page.model_copy(
                update={
                    "content": self._config.privacy_filter.flag_message,
                    "snippet": self._config.privacy_filter.flag_message,
                }
            )

        if mode == SanitizeMode.JUDGE_AND_SANITIZE:
            _, page = await self.judge_and_sanitize(**kwargs)
            return page

        if mode == SanitizeMode.JUDGE_THEN_SANITIZE:
            needs_sanitization, _ = await self.judge_only(**kwargs)
            if not needs_sanitization:
                _LOGGER.info(
                    f"Page {kwargs['page'].url} does not require sanitization — keeping as-is"
                )
                return kwargs["page"]
            _LOGGER.info(
                f"Page {kwargs['page'].url} flagged — running full sanitize call"
            )
            return await self.sanitize_page(**kwargs)

        raise ValueError(f"Unknown sanitize_mode: {mode}")

    async def sanitize_page(
        self, **kwargs: Unpack[ProcessingStrategyKwargs]
    ) -> WebSearchResult:
        """Run a full summarize-and-sanitize LLM call unconditionally."""
        page = kwargs["page"]
        query = kwargs["query"]

        system_prompt = render_template(
            self._config.prompts.system_prompt,
            sanitize=True,
            sanitize_rules=self._config.privacy_filter.sanitize_rules,
            output_schema=LLMGuardResponse.model_json_schema(),
        )
        user_prompt = render_template(
            self._config.prompts.user_prompt,
            page=page,
            query=query,
            sanitize=True,
        )

        parsed = await self._complete(LLMGuardResponse, system_prompt, user_prompt)
        return parsed.apply_to_page(page)

    async def judge_only(
        self, **kwargs: Unpack[ProcessingStrategyKwargs]
    ) -> tuple[bool, WebSearchResult]:
        """Cheap classification call: determine whether the page needs sanitization.

        Returns:
            (needs_sanitization, page) — the original unmodified page is always returned.
            The caller decides what to do when the page is flagged.
        """
        page = kwargs["page"]
        query = kwargs["query"]

        system_prompt = render_template(
            self._config.prompts.judge_prompt,
            sanitize_rules=self._config.privacy_filter.sanitize_rules,
            output_schema=JudgeResponse.model_json_schema(),
        )
        user_prompt = render_template(
            self._config.prompts.page_context_prompt,
            page=page,
            query=query,
            task_description=_JUDGE_TASK_PREFIX,
        )

        parsed = await self._complete(JudgeResponse, system_prompt, user_prompt)

        _LOGGER.info(
            f"Judge result for {page.url}: needs_sanitization={parsed.needs_sanitization}"
        )

        return parsed.needs_sanitization, page

    async def judge_and_sanitize(
        self, **kwargs: Unpack[ProcessingStrategyKwargs]
    ) -> tuple[bool, WebSearchResult]:
        """Single-call flow: classify and produce sanitized output in one structured call.

        Returns:
            (needs_sanitization, page) — `page` already has sanitized content/snippet
            applied when `needs_sanitization` is True; otherwise the original page is returned.
        """
        page = kwargs["page"]
        query = kwargs["query"]

        system_prompt = render_template(
            self._config.prompts.judge_and_sanitize_prompt,
            sanitize_rules=self._config.privacy_filter.sanitize_rules,
            output_schema=JudgeAndSanitizeResponse.model_json_schema(),
        )
        user_prompt = render_template(
            self._config.prompts.user_prompt,
            page=page,
            query=query,
            sanitize=True,
        )

        parsed = await self._complete(
            JudgeAndSanitizeResponse, system_prompt, user_prompt
        )

        _LOGGER.info(
            f"Judge result for {page.url}: needs_sanitization={parsed.needs_sanitization}"
        )

        if parsed.needs_sanitization:
            page = parsed.apply_to_page(page)

        return parsed.needs_sanitization, page

    # ------------------------------------------------------------------
    # Generic LLM call helper
    # ------------------------------------------------------------------

    async def _complete(
        self,
        response_model: type[_T],
        system_prompt: str,
        user_prompt: str,
    ) -> _T:
        """Build messages, call the LLM, and return the parsed structured response."""
        messages = (
            MessagesBuilder()
            .system_message_append(system_prompt)
            .user_message_append(user_prompt)
            .build()
        )

        _LOGGER.info(
            f"Running judge call (model={self._config.language_model.name}, "
            f"response_model={response_model.__name__})"
        )

        response = await self._llm_service.complete_async(
            messages=messages,
            model_name=self._config.language_model.name,
            structured_output_model=response_model,
            structured_output_enforce_schema=True,
        )

        if response.choices[0].message.parsed is None:
            raise ValueError("Judge call returned no parsed response")

        return response_model.model_validate(response.choices[0].message.parsed)
