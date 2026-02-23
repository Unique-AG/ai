import logging
from typing import Unpack

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.language_model import TypeDecoder, TypeEncoder

from unique_web_search.services.content_processing.processing_strategies.base import (
    ProcessingStrategyKwargs,
    WebSearchResult,
)

_LOGGER = logging.getLogger(__name__)


class TruncateConfig(BaseModel):
    model_config = get_configuration_dict()
    enabled: bool = Field(
        default=True,
        title="Enable Content Length Limit",
        description="When enabled, web page content that exceeds the maximum length is automatically shortened.",
    )
    max_tokens: int = Field(
        default=10000,
        title="Maximum Content Length",
        description="Maximum amount of content to keep from each web page (measured in tokens, roughly 1 token = 4 characters). Content beyond this limit is cut off.",
    )


class Truncate:
    def __init__(
        self, encoder: TypeEncoder, decoder: TypeDecoder, config: TruncateConfig
    ):
        self._config = config
        self._encoder = encoder
        self._decoder = decoder

    @property
    def is_enabled(self) -> bool:
        return self._config.enabled

    async def __call__(
        self, **kwargs: Unpack[ProcessingStrategyKwargs]
    ) -> WebSearchResult:
        page = kwargs["page"]

        if not self._config.enabled:
            _LOGGER.warning("Truncate strategy is disabled, skipping")
            return page

        _LOGGER.info(f"Truncating page {page.url} with truncate strategy")
        tokens = self._encoder(page.content)
        if len(tokens) > self._config.max_tokens:
            page.content = self._decoder(tokens[: self._config.max_tokens])
        return page
