"""V3 WebSearch tool parameters: a flat schema with exactly one of ``query`` or ``urls`` per call."""

import typing
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Command(StrEnum):
    SEARCH = "search"
    FETCH_URLS = "read_urls"


class SearchPayload(BaseModel):
    gap: str = Field(
        description="A brief description of the gap that the query is meant to fill"
    )
    query: str = Field(
        description="Search query for the configured search engine. Query must be fixed for the entire rounds."
    )


class FetchUrlsPayload(BaseModel):
    urls: list[str] = Field(
        description="HTTP(S) URLs to crawl. Use only URLs returned by a prior search or pasted by the user. Prefer 1-2 high-signal URLs to reduce latency."
    )


class WebSearchV3ToolParameters(BaseModel):
    """Root JSON for the V3 WebSearch tool: set exactly one of ``query`` or ``urls``."""

    model_config = ConfigDict(extra="forbid")

    command: Command = Field(
        description="The command to execute. Must be either 'search' or 'read_urls'."
    )

    objective: str = Field(
        description="One concise sentence: what this call is meant to accomplish."
    )

    payload: SearchPayload | FetchUrlsPayload = Field(
        description="The payload of the command. Must be either a SearchPayload or a FetchUrlsPayload."
    )

    @classmethod
    def schema_hint(cls) -> str:
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
                placeholder = f"<{field.description or name}>"
                if typing.get_origin(field.annotation) is list:
                    placeholder = f"[{placeholder}]"
                parts.append(f'"{name}": {placeholder}')
            return "{ " + ", ".join(parts) + " }"

        lines: list[str] = []
        for name, field in cls.model_fields.items():
            if name == "command":
                choices = " or ".join(f'`"{c.value}"`' for c in Command)
                lines.append(f"- **`{name}`** — {choices}.")
            elif name == "payload":
                continue
            else:
                lines.append(f"- **`{name}`** — {field.description or name}")

        lines.append("- **`payload`** — Shape depends on `command`:")
        for cmd, payload_model in (
            (Command.SEARCH, SearchPayload),
            (Command.FETCH_URLS, FetchUrlsPayload),
        ):
            lines.append(f'  - For `"{cmd.value}"`: `{_inline_json(payload_model)}`.')

        return "\n".join(lines)

    def get_display_name_suffix(self) -> str:
        if self.command == Command.SEARCH:
            return " - Searching"
        elif self.command == Command.FETCH_URLS:
            return " - Reading Pages"
        else:
            raise ValueError(f"Invalid command: {self.command}")
