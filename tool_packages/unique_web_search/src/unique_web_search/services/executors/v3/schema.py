"""V3 WebSearch tool parameters: a flat schema with exactly one of ``query`` or ``urls`` per call."""

import typing
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, create_model
from unique_search_proxy_core.search_engines.call_schema import (
    ExposedToolParameterModel,
    _stamp_exposed_field_names,
)


class Command(StrEnum):
    SEARCH = "search"
    FETCH_URLS = "read_urls"


class SearchPhase(StrEnum):
    """How this WebSearch call fits in the research arc."""

    EXPLORATORY = "exploratory"
    TARGET = "target"
    REDIRECT = "redirect"


class SearchPayload(ExposedToolParameterModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    gap: str = Field(
        description=(
            "One atomic facet this call addresses (e.g. '2023 revenue band for Company X in CH')—"
            "not the whole user question. Pair with `phase`: exploratory scopes the topic; "
            "target pursues this facet precisely; redirect seeks related context when the facet "
            "is unlikely to be on the public web."
        )
    )
    query: str = Field(
        description=(
            "Short search-engine keyword line (~3–8 words, not a sentence). "
            "Do not pack multiple facets into one query—issue parallel `search` calls with "
            "one `gap` each instead. Do not paste the user question or `gap` text here."
        )
    )

    @classmethod
    def with_exposed_fields(
        cls,
        exposed_field_defs: dict[str, tuple[Any, Any]] | None,
    ) -> type["SearchPayload"]:
        return super().with_exposed_fields(exposed_field_defs)


class FetchUrlsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    urls: list[str] = Field(
        description="HTTP(S) URLs to crawl for full-page text. Use only URLs returned by a prior search or pasted by the user."
    )


class WebSearchV3ToolParameters(ExposedToolParameterModel):
    """Root JSON for the V3 WebSearch tool: set exactly one of ``query`` or ``urls``."""

    model_config = ConfigDict(extra="forbid")

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
    def with_exposed_fields(
        cls,
        exposed_field_defs: dict[str, tuple[Any, Any]] | None,
    ) -> type["WebSearchV3ToolParameters"]:
        search_payload = SearchPayload.with_exposed_fields(exposed_field_defs)
        if search_payload is SearchPayload:
            return cls
        model = create_model(
            cls.__name__,
            __base__=cls,
            payload=(
                search_payload | FetchUrlsPayload,
                Field(
                    description=(
                        "The payload of the command. Must be either a SearchPayload "
                        "or a FetchUrlsPayload."
                    ),
                ),
            ),
        )
        _stamp_exposed_field_names(model, exposed_field_defs)
        return model

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
        exposed_field_defs: dict[str, tuple[Any, Any]] | None = None,
    ) -> str:
        """Return a markdown-bulleted hint mirroring the field descriptions of this model.

        Mirrors the legacy hand-written prompt block: one bullet per top-level
        field, with the ``payload`` bullet expanded into one inline JSON sketch
        per ``command`` value (since ``payload`` is a discriminated union).
        Field descriptions are inlined as ``<...>`` placeholders so the prompt
        stays in sync with the Pydantic model.
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

        lines: list[str] = []
        for name, field in cls.model_fields.items():
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
        search_payload = SearchPayload.with_exposed_fields(exposed_field_defs)
        for cmd, payload_model in (
            (Command.SEARCH, search_payload),
            (Command.FETCH_URLS, FetchUrlsPayload),
        ):
            lines.append(f'  - For `"{cmd.value}"`: `{_inline_json(payload_model)}`.')

        return "\n".join(lines)
