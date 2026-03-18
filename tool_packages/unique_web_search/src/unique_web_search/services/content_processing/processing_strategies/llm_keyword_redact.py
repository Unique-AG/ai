import logging
import re
from typing import Unpack

from pydantic import BaseModel, ConfigDict, Field
from rapidfuzz import fuzz
from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit.language_model import LanguageModelService
from unique_toolkit.language_model.builder import MessagesBuilder

from unique_web_search.services.content_processing.processing_strategies.base import (
    ProcessingStrategyKwargs,
    WebSearchResult,
)
from unique_web_search.services.content_processing.processing_strategies.llm_process import (
    LLMProcessorConfig,
)

_LOGGER = logging.getLogger(__name__)

_KEYWORD_TASK_PREFIX = (
    "Extract every GDPR Art. 9 sensitive phrase from the web page below."
)

_FUZZY_MATCH_THRESHOLD = 85
_WINDOW_SLACK = 0.30


def _fuzzy_redact_pass(text: str, phrase: str, tag: str) -> str:
    """Replace near-matches of *phrase* in *text* with *tag* using a sliding window.

    This is the second pass, run only on text that survived the exact-regex pass.
    Windows are scored with fuzz.ratio so that significant length mismatches are
    penalised.  All qualifying, non-overlapping spans (highest score wins on
    conflict) are collected and then applied right-to-left to preserve offsets.
    """
    phrase_len = len(phrase)
    if phrase_len == 0:
        return text

    slack = max(1, int(phrase_len * _WINDOW_SLACK))
    win_min = max(3, phrase_len - slack)
    win_max = phrase_len + slack
    phrase_lower = phrase.lower()

    # (score, start, end) for every window that clears the threshold
    candidates: list[tuple[int, int, int]] = []
    text_len = len(text)

    for win_len in range(win_min, win_max + 1):
        for start in range(text_len - win_len + 1):
            end = start + win_len
            window = text[start:end].lower()
            score = fuzz.ratio(phrase_lower, window)
            if score >= _FUZZY_MATCH_THRESHOLD:
                candidates.append((int(score), start, end))

    if not candidates:
        return text

    # greedy non-overlapping selection: sort by score desc, then left-to-right
    candidates.sort(key=lambda c: (-c[0], c[1]))
    selected: list[tuple[int, int, int]] = []
    occupied: set[int] = set()
    for score, start, end in candidates:
        span = set(range(start, end))
        if span.isdisjoint(occupied):
            selected.append((score, start, end))
            occupied |= span

    # apply right-to-left so earlier offsets stay valid
    selected.sort(key=lambda c: -c[1])
    result = text
    for _, start, end in selected:
        result = result[:start] + tag + result[end:]

    return result


class SensitiveKeyword(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phrase: str = Field(
        description=(
            "The exact verbatim sensitive phrase as it appears in the source text. "
            "Do not paraphrase, normalise casing, or change punctuation."
        )
    )
    tag: str = Field(
        description=(
            "The typed GDPR Art. 9 redaction tag that must replace this phrase. "
            "Must be one of: [RedactHealth], [RedactPoliticalOpinion], [RedactReligiousBelief], "
            "[RedactRacialOrEthnic], [RedactSexualOrientation], [RedactTradeUnion], "
            "[RedactGeneticData], [RedactBiometricData]."
        )
    )


def _redact_text(text: str, keywords: list[SensitiveKeyword]) -> str:
    """Two-pass redaction: exact regex first, fuzzy sliding-window second."""
    for kw in keywords:
        # Pass 1 – exact, case-insensitive
        pattern = re.compile(re.escape(kw.phrase), re.IGNORECASE)
        text = pattern.sub(kw.tag, text)

    for kw in keywords:
        # Pass 2 – fuzzy, only touches text not yet redacted by pass 1
        text = _fuzzy_redact_pass(text, kw.phrase, kw.tag)

    return text


class KeywordRedactResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensitive_keywords: list[SensitiveKeyword] = Field(
        description=(
            "An exhaustive list of every GDPR Art. 9 sensitive verbatim phrase found on the page. "
            "Include all surface forms and all individuals mentioned. "
            "If no sensitive data is found, return an empty list."
        )
    )

    def apply_to_page(self, page: WebSearchResult) -> WebSearchResult:
        page.content = _redact_text(page.content, self.sensitive_keywords)
        page.snippet = _redact_text(page.snippet, self.sensitive_keywords)
        return page


class LLMKeywordRedact:
    """Mode D: keyword extraction via LLM followed by local regex replacement.

    One LLM call extracts a list of verbatim sensitive phrases and their redaction tags.
    A local regex pass then replaces every occurrence in the page content and snippet —
    no summarization is performed, preserving the full original page structure.
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
        page = kwargs["page"]
        query = kwargs.get("query") or ""

        system_prompt = render_template(
            self._config.prompts.keyword_extract_prompt,
            sanitize_rules=self._config.privacy_filter.sanitize_rules,
            output_schema=KeywordRedactResponse.model_json_schema(),
        )

        user_prompt = render_template(
            self._config.prompts.page_context_prompt,
            page=page,
            query=query,
            task_description=_KEYWORD_TASK_PREFIX,
        )

        messages = (
            MessagesBuilder()
            .system_message_append(system_prompt)
            .user_message_append(user_prompt)
            .build()
        )

        _LOGGER.info(
            f"Running keyword extraction for page {page.url} "
            f"(model={self._config.language_model.name})"
        )

        response = await self._llm_service.complete_async(
            messages=messages,
            model_name=self._config.language_model.name,
            structured_output_model=KeywordRedactResponse,
            structured_output_enforce_schema=True,
        )

        if response.choices[0].message.parsed is None:
            raise ValueError("Keyword extraction call returned no parsed response")

        parsed = KeywordRedactResponse.model_validate(
            response.choices[0].message.parsed
        )

        _LOGGER.info(
            f"Extracted {len(parsed.sensitive_keywords)} sensitive keyword(s) from {page.url}"
        )

        return parsed.apply_to_page(page)
