"""Configuration for Web Search V3 (search SERP + fetch URLs)."""

from hashlib import sha256
from logging import getLogger
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic.json_schema import SkipJsonSchema
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit.agentic.tools.config import get_configuration_dict

from unique_web_search.prompts import (
    DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT_V3,
)
from unique_web_search.services.executors.base_config import (
    BaseWebSearchModeConfig,
    WebSearchMode,
)
from unique_web_search.services.executors.v3.prompts import (
    DEFAULT_TOOL_DESCRIPTION,
    DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
)
from unique_web_search.services.helpers import clean_model_title_generator

_LOGGER = getLogger(__name__)

# SHA-256 fingerprints of the pre-engine-mode defaults, with and without the
# trailing newline. Fingerprints let us identify unchanged defaults without
# embedding a second copy of each long prompt in this module.
_LEGACY_TOOL_DESCRIPTION_DIGESTS = frozenset(
    {
        "6b29c1a4a323f22e2024fcdd7f707be2ac1051b161b352b59db75db9464ee4ae",
        "d5862ddda5a7994fc72dc52f5346270f064c8244e98ca2983d7f13fe68ed78c5",
    }
)
_LEGACY_SYSTEM_PROMPT_DIGESTS = frozenset(
    {
        "966bfcec1380612c91ad1ef6ffecf87645bb5376d787cc9bf5b6cf2c6f3eb898",
        "2fe15780dd87bfa09162f72cf1b07d5db47c3703bbdd1169784bceea37b330c8",
    }
)


def _migrate_legacy_default(
    value: str,
    *,
    legacy_digests: frozenset[str],
    current_default: str,
    field_name: str,
) -> str:
    """Replace an unchanged legacy default while preserving custom prompts."""
    if sha256(value.encode()).hexdigest() not in legacy_digests:
        return value
    _LOGGER.warning(
        "V3 web-search config contains the legacy mode-blind default for '%s'; "
        "replacing it with the mode-aware default.",
        field_name,
    )
    return current_default


class WebSearchV3Config(BaseWebSearchModeConfig[WebSearchMode.V3]):
    """V3 mode: ``search`` returns SERP rows as JSON chunks; ``fetch_urls`` crawls and processes pages."""

    model_config = get_configuration_dict(
        model_title_generator=clean_model_title_generator
    )
    mode: SkipJsonSchema[Literal[WebSearchMode.V3]] = WebSearchMode.V3

    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(DEFAULT_TOOL_DESCRIPTION.split("\n"))
        ),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION,
        title="Tool Description",
        description="Advanced: Description that helps the AI model decide when to use web search.",
    )
    tool_description_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=int(len(DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT.split("\n")) / 2)
        ),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
        title="Tool Description for System Prompt",
        description="Advanced: Description that helps the AI model decide when to use web search (V3).",
    )
    tool_format_information_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=int(
                len(DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT_V3.split("\n"))
                / 3
            )
        ),
    ] = Field(
        default=DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT_V3,
        title="Tool Format Information For System Prompt",
        description="Advanced: Instructions that tell the AI how to cite web search sources in its answers (V3 includes domain diversity requirements).",
    )

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, v: str) -> Literal["v3"]:
        if "v3" in v.lower():
            return "v3"
        raise ValueError(f"Invalid mode: {v}")

    @field_validator("tool_description", mode="after")
    @classmethod
    def migrate_legacy_tool_description(cls, value: str) -> str:
        """Upgrade the unchanged pre-engine-mode tool description."""
        return _migrate_legacy_default(
            value,
            legacy_digests=_LEGACY_TOOL_DESCRIPTION_DIGESTS,
            current_default=DEFAULT_TOOL_DESCRIPTION,
            field_name="tool_description",
        )

    @field_validator("tool_description_for_system_prompt", mode="after")
    @classmethod
    def migrate_legacy_system_prompt(cls, value: str) -> str:
        """Upgrade the unchanged pre-engine-mode system prompt."""
        return _migrate_legacy_default(
            value,
            legacy_digests=_LEGACY_SYSTEM_PROMPT_DIGESTS,
            current_default=DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
            field_name="tool_description_for_system_prompt",
        )
