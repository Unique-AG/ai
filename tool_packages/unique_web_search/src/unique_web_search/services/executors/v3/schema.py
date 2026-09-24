"""V3 WebSearch tool parameters: a flat schema with exactly one of ``query`` or ``urls`` per call."""

from __future__ import annotations

import typing
from enum import StrEnum
from typing import cast

from pydantic import BaseModel, ConfigDict, Field, create_model
from pydantic.alias_generators import to_camel
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams

from unique_web_search.services.search_engine.base import SearchEngineMode

# Strict LLM-facing config: camelCase aliases + forbid extras, while still
# inheriting ExposedParams.model_json_schema (strips title/default noise).
_LLM_TOOL_MODEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    extra="forbid",
)

_STANDARD_QUERY_DESCRIPTION = (
    "Short search-engine keyword line (~3–8 words, not a sentence). "
    "Do not pack multiple facets into one query—issue parallel `search` calls with "
    "one `gap` each instead. Do not paste the user question or `gap` text here."
)
_AGENT_QUERY_DESCRIPTION = (
    "One comprehensive natural-language research request that preserves the user's "
    "full intent, context, and constraints. Do not condense it into keywords—the "
    "agent-based search engine performs query planning and source diversification "
    "internally."
)
_AGENT_PHASE_DESCRIPTION = (
    "Research phase for this call. "
    "`exploratory` — sense what exists on the web and what is closest to the user's ask "
    "(broad, mapping requests). "
    "`target` — pursue the research request in `payload.query` for the facet identified "
    "by `payload.gap`. "
    "`redirect` — last resort when the exact facet is not on the public web; find related, "
    "attributable context (sector, peers, parent entity, adjacent news)—not invented facts."
)


class Command(StrEnum):
    SEARCH = "search"
    FETCH_URLS = "read_urls"


class SearchPhase(StrEnum):
    """How this WebSearch call fits in the research arc."""

    EXPLORATORY = "exploratory"
    TARGET = "target"
    REDIRECT = "redirect"


class SearchPayload(ExposedParams):
    model_config = _LLM_TOOL_MODEL_CONFIG

    gap: str = Field(
        description=(
            "One atomic facet this call addresses (e.g. '2023 revenue band for Company X in CH')—"
            "not the whole user question. Pair with `phase`: exploratory scopes the topic; "
            "target pursues this facet precisely; redirect seeks related context when the facet "
            "is unlikely to be on the public web."
        )
    )
    query: str = Field(description=_STANDARD_QUERY_DESCRIPTION)

    @classmethod
    def with_exposed_params(
        cls,
        exposed: type[ExposedParams] | None,
    ) -> type[SearchPayload]:
        """Graft admin-exposed engine knobs onto the search payload model."""
        return cls.with_search_engine_mode(SearchEngineMode.STANDARD, exposed)

    @classmethod
    def with_search_engine_mode(
        cls,
        mode: SearchEngineMode,
        exposed: type[ExposedParams] | None = None,
    ) -> type[SearchPayload]:
        """Build a search payload with mode-specific query guidance and engine knobs."""
        if exposed is None:
            if mode == SearchEngineMode.STANDARD:
                return cls
            return create_model(
                cls.__name__,
                __base__=cls,
                query=(str, Field(description=_AGENT_QUERY_DESCRIPTION)),
            )
        if mode == SearchEngineMode.AGENT:
            return cast(
                type[SearchPayload],
                create_model(
                    cls.__name__,
                    __base__=(cls, exposed),
                    query=(str, Field(description=_AGENT_QUERY_DESCRIPTION)),
                ),
            )
        return cast(
            type[SearchPayload],
            create_model(
                cls.__name__,
                __base__=(cls, exposed),
            ),
        )


class FetchUrlsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    urls: list[str] = Field(
        description="HTTP(S) URLs to crawl for full-page text. Use only URLs returned by a prior search or pasted by the user."
    )


class WebSearchV3ToolParameters(ExposedParams):
    """Root JSON for the V3 WebSearch tool: set exactly one of ``query`` or ``urls``."""

    model_config = _LLM_TOOL_MODEL_CONFIG

    command: Command = Field(
        description="The command to execute. Must be either 'search' or 'read_urls'."
    )

    phase: SearchPhase = Field(
        description=(
            "Research phase for this call. "
            "`exploratory` — sense what exists on the web and what is closest to the user's ask "
            "(broad, mapping queries). "
            "`target` — pursue one specific facet in `payload.gap` with a precise, short `query`. "
            "`redirect` — last resort when the exact facet is not on the public web; find related, "
            "attributable context (sector, peers, parent entity, adjacent news)—not invented facts."
        )
    )

    payload: SearchPayload | FetchUrlsPayload = Field(
        description="The payload of the command. Must be either a SearchPayload or a FetchUrlsPayload."
    )

    @classmethod
    def with_exposed_params(
        cls,
        exposed: type[ExposedParams] | None,
    ) -> type[WebSearchV3ToolParameters]:
        """Rebuild the payload union with an exposed ``SearchPayload`` subtype."""
        return cls.with_search_engine_mode(SearchEngineMode.STANDARD, exposed)

    @classmethod
    def with_search_engine_mode(
        cls,
        mode: SearchEngineMode,
        exposed: type[ExposedParams] | None = None,
    ) -> type[WebSearchV3ToolParameters]:
        """Build V3 parameters with mode-specific search guidance and engine knobs."""
        search_payload = SearchPayload.with_search_engine_mode(mode, exposed)
        if search_payload is SearchPayload:
            return cls
        payload_field = (
            search_payload | FetchUrlsPayload,
            Field(
                description=(
                    "The payload of the command. Must be either a SearchPayload "
                    "or a FetchUrlsPayload."
                ),
            ),
        )
        if mode == SearchEngineMode.AGENT:
            return create_model(
                cls.__name__,
                __base__=cls,
                phase=(SearchPhase, Field(description=_AGENT_PHASE_DESCRIPTION)),
                payload=payload_field,
            )
        return create_model(
            cls.__name__,
            __base__=cls,
            payload=payload_field,
        )

    def relevance_focus(self) -> str:
        """Focus string for notify UI, snippet judging, and content processing."""
        phase_label = self.phase.value
        if isinstance(self.payload, SearchPayload):
            return f"[{phase_label}] {self.payload.gap}"
        urls_preview = ", ".join(self.payload.urls[:3])
        if len(self.payload.urls) > 3:
            urls_preview += ", …"
        return f"[{phase_label}] {urls_preview}"

    @classmethod
    def schema_hint(
        cls,
        exposed: type[ExposedParams] | None = None,
        *,
        mode: SearchEngineMode = SearchEngineMode.STANDARD,
    ) -> str:
        """Return a markdown-bulleted hint mirroring the field descriptions of this model.

        Mirrors the legacy hand-written prompt block: one bullet per top-level
        field, with the ``payload`` bullet expanded into one inline JSON sketch
        per ``command`` value (since ``payload`` is a discriminated union).
        Field descriptions are inlined as ``<...>`` placeholders so the prompt
        stays in sync with the Pydantic model. Exposed knobs render under their
        camelCase aliases.
        """

        def _inline_json(payload_model: type[BaseModel]) -> str:
            parts: list[str] = []
            for name, field in payload_model.model_fields.items():
                key = field.alias or name
                placeholder = f"<{field.description or key}>"
                if typing.get_origin(field.annotation) is list:
                    placeholder = f"[{placeholder}]"
                parts.append(f'"{key}": {placeholder}')
            return "{ " + ", ".join(parts) + " }"

        parameters_model = cls.with_search_engine_mode(mode, exposed)
        lines: list[str] = []
        for name, field in parameters_model.model_fields.items():
            if name == "command":
                choices = " or ".join(f'`"{c.value}"`' for c in Command)
                lines.append(f"- **`{name}`** — {choices}.")
            elif name == "phase":
                choices = " | ".join(f'`"{c.value}"`' for c in SearchPhase)
                lines.append(f"- **`{name}`** — {choices}.")
            elif name == "payload":
                continue
            else:
                lines.append(f"- **`{name}`** — {field.description or name}")

        lines.append("- **`payload`** — Shape depends on `command`:")
        search_payload = SearchPayload.with_search_engine_mode(mode, exposed)
        for cmd, payload_model in (
            (Command.SEARCH, search_payload),
            (Command.FETCH_URLS, FetchUrlsPayload),
        ):
            lines.append(f'  - For `"{cmd.value}"`: `{_inline_json(payload_model)}`.')

        return "\n".join(lines)
