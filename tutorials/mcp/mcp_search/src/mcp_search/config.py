"""Tool-level configuration for the Knowledge Base Search MCP tool.

``SearchToolConfig`` is the single RJSF config model for the search tool.
It holds one ``service_config`` key — either ``KBSearchConfig`` or ``ChatSearchConfig``
— which is passed directly to the corresponding internal-search service via
``from_config()``, with no field mapping required.

Admin sets ``service_config.type`` once at deployment time to choose the search backend.
``post_processing`` controls post-retrieval behaviour (token budget, reranking).

Notes on the discriminated union and RJSF
------------------------------------------
- ``KBSearchConfig`` and ``ChatSearchConfig`` add a ``type`` literal field to
  their respective toolkit base classes so Pydantic can emit a ``oneOf`` +
  ``discriminator`` JSON schema that RJSF renders as a variant selector.
- The ``type`` field is never stored by the LLM or passed by the caller — it
  lives only in admin-managed config.
- Stored configs must always include ``"type"`` explicitly; ``model_dump()``
  emits it automatically so anything saved from the admin UI is always valid.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.experimental.components.internal_search import (
    ChatInternalSearchConfig,
    KnowledgeBaseInternalSearchConfig,
    PostProcessorConfig,
)


class KBSearchConfig(KnowledgeBaseInternalSearchConfig):
    model_config = get_configuration_dict(title="Knowledge Base")
    type: Literal["kb"] = "kb"


class ChatSearchConfig(ChatInternalSearchConfig):
    model_config = get_configuration_dict(title="Chat")
    type: Literal["chat"] = "chat"


class SearchToolConfig(BaseModel):
    model_config = get_configuration_dict()

    service_config: Annotated[
        KBSearchConfig | ChatSearchConfig,
        Field(discriminator="type"),
    ] = Field(default_factory=KBSearchConfig)
    post_processing: PostProcessorConfig = Field(default_factory=PostProcessorConfig)
