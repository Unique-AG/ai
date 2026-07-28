import asyncio
from typing import override

from pydantic import Field
from unique_search_proxy_core.agent_engines.base import AgentEngineType
from unique_search_proxy_core.agent_engines.bing.schema import BingAgentConfig
from unique_search_proxy_core.context import LOCAL_REQUEST_CONTEXT, RequestContext
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_toolkit._common.default_language_model import DEFAULT_LANGUAGE_MODEL
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.language_model import LanguageModelService

from unique_web_search.services.proxy.bridge import (
    search_proxy_client_enabled,
)
from unique_web_search.services.search_engine.base import SearchEngine, SearchEngineMode
from unique_web_search.services.search_engine.registry import register_search_engine
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.services.search_engine.utils.grounding import (
    JsonConversionStrategy,
    LLMParserStrategy,
)
from unique_web_search.services.search_engine.utils.grounding.bing import (
    create_and_process_run,
    credentials_are_valid,
    get_credentials,
    get_project_client,
)
from unique_web_search.settings import env_settings


class BingSearchConfig(BingAgentConfig):
    agent_id: str = Field(
        default=env_settings.azure_ai_assistant_id or "",
        description="The ID of the agent to use for the search. **This parameter is temporary and will be auto-provisioned in future versions.**",
    )
    endpoint: str = Field(
        default=env_settings.azure_ai_project_endpoint or "",
        description="The endpoint to use for the search. **This parameter is not required to be set. It's loaded automatically from auto-provisioned resource**",
    )
    language_model: LMI = get_LMI_default_field(
        DEFAULT_LANGUAGE_MODEL,
        description="The language model to use in as a fallback parser if the agent response is not a valid JSON.",
    )
    requires_scraping: bool = Field(
        default=False,
        description="Whether the search engine requires scraping.",
    )


@register_search_engine(
    name="bing",
    key=AgentEngineType.BING,
    config_cls=BingSearchConfig,
    mode=SearchEngineMode.AGENT,
    config_display_name="Grounding with Bing",
    needs_language_model=True,
)
class BingSearch(SearchEngine[BingSearchConfig]):
    def __init__(
        self,
        config: BingSearchConfig,
        language_model_service: LanguageModelService,
        *,
        request_context: RequestContext = LOCAL_REQUEST_CONTEXT,
    ):
        super().__init__(config, request_context=request_context)
        self.credentials = get_credentials()

        self.response_parsers = [
            JsonConversionStrategy(),
            LLMParserStrategy(
                config.language_model,
                language_model_service,
            ),
        ]

    @property
    def is_configured(self) -> bool:
        if search_proxy_client_enabled:
            return True

        async def _is_configured() -> bool:
            return await credentials_are_valid(self.credentials)

        return asyncio.run(_is_configured())

    @property
    def requires_scraping(self) -> bool:
        return self.config.requires_scraping

    @override
    async def _legacy_search(
        self,
        query: str,
        params: ExposedParams | None,
    ) -> list[WebSearchResult]:
        del params
        agent_client = get_project_client(self.credentials, self.config.endpoint)

        async with agent_client:
            search_results = await create_and_process_run(
                agent_client,
                agent_id=self.config.agent_id,
                query=query,
                fetch_size=self.config.fetch_size,
                response_parsers_strategies=self.response_parsers,
                generation_instructions=self.config.generation_instructions,
            )

        return search_results
