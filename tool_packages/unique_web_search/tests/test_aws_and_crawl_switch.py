import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel, Field
from unique_search_proxy_core.search_engines.google.schema import GoogleConfig
from unique_search_proxy_sdk._generated.models.providers_list_response import (
    ProvidersListResponse,
)

from unique_web_search.config import WebSearchConfig
from unique_web_search.services import crawling
from unique_web_search.services.executors.v2.config import WebSearchV2Config
from unique_web_search.services.executors.v2.executor import WebSearchV2Executor
from unique_web_search.services.executors.v2.schema import (
    Step,
    StepType,
    WebSearchPlan,
)
from unique_web_search.services.executors.v2.strategy import WebSearchV2Strategy
from unique_web_search.services.executors.v3.config import WebSearchV3Config
from unique_web_search.services.executors.v3.schema import WebSearchV3ToolParameters
from unique_web_search.services.executors.v3.strategy import WebSearchV3Strategy
from unique_web_search.services.search_engine.aws import trim_aws_query
from unique_web_search.services.search_engine.base import SearchEngineMode
from unique_web_search.settings import env_settings


def test_trim_aws_query_keeps_a_prefix_that_ends_on_a_word() -> None:
    query = "find " + "x" * 195 + " more"
    assert trim_aws_query(query) == "find " + "x" * 195


def test_trim_aws_query_keeps_short_queries() -> None:
    assert trim_aws_query("Swiss National Bank") == "Swiss National Bank"


def test_trim_aws_query_cuts_on_a_word_boundary() -> None:
    query = ("alpha " * 50).strip()
    trimmed = trim_aws_query(query)
    assert len(trimmed) <= 200
    assert not trimmed.endswith(" ")
    assert trimmed.endswith("alpha")


def test_crawling_is_enabled_without_a_search_proxy(monkeypatch) -> None:
    monkeypatch.setattr(env_settings, "search_proxy_base_url", None)
    fetch = Mock()
    monkeypatch.setattr(crawling, "_fetch_crawling_enabled", fetch)
    assert crawling.crawling_enabled() is True
    fetch.assert_not_called()


def test_crawling_enabled_follows_the_proxy_and_is_cached(monkeypatch) -> None:
    monkeypatch.setattr(env_settings, "search_proxy_base_url", "http://proxy.test")
    sync = Mock(
        return_value=ProvidersListResponse(
            search_engines=[], crawlers=[], crawling_enabled=False
        )
    )
    monkeypatch.setattr(crawling.list_providers, "sync", sync)
    assert crawling.crawling_enabled() is False
    assert crawling.crawling_enabled() is False
    sync.assert_called_once()


def test_crawling_stays_enabled_when_the_proxy_is_unreachable(monkeypatch) -> None:
    monkeypatch.setattr(env_settings, "search_proxy_base_url", "http://proxy.test")
    monkeypatch.setattr(
        crawling.list_providers, "sync", Mock(side_effect=OSError("refused"))
    )
    assert crawling.crawling_enabled() is True


def test_stale_cache_refreshes_in_the_background_on_an_event_loop(
    monkeypatch,
) -> None:
    monkeypatch.setattr(env_settings, "search_proxy_base_url", "http://proxy.test")
    sync = Mock(side_effect=AssertionError("blocking fetch on the event loop"))
    monkeypatch.setattr(crawling, "_fetch_crawling_enabled", sync)

    async def fetch_async(base_url: str) -> bool:
        return False

    monkeypatch.setattr(crawling, "_fetch_crawling_enabled_async", fetch_async)
    monkeypatch.setattr(crawling, "_cached", (-1_000.0, True))

    async def run() -> tuple[bool, bool]:
        stale = crawling.crawling_enabled()
        assert crawling._refresh is not None
        await crawling._refresh[1]
        return stale, crawling.crawling_enabled()

    assert asyncio.run(run()) == (True, False)
    sync.assert_not_called()


def test_async_fetch_reads_the_proxy_and_fails_open(monkeypatch) -> None:
    monkeypatch.setattr(
        crawling.list_providers,
        "asyncio",
        AsyncMock(
            return_value=ProvidersListResponse(
                search_engines=[], crawlers=[], crawling_enabled=False
            )
        ),
    )
    assert (
        asyncio.run(crawling._fetch_crawling_enabled_async("http://proxy.test"))
        is False
    )
    monkeypatch.setattr(
        crawling.list_providers, "asyncio", AsyncMock(side_effect=OSError("refused"))
    )
    assert (
        asyncio.run(crawling._fetch_crawling_enabled_async("http://proxy.test")) is True
    )


def test_stale_cache_is_fetched_directly_without_an_event_loop(monkeypatch) -> None:
    monkeypatch.setattr(env_settings, "search_proxy_base_url", "http://proxy.test")
    monkeypatch.setattr(crawling, "_fetch_crawling_enabled", lambda base_url: False)
    monkeypatch.setattr(crawling, "_cached", (-1_000.0, True))
    assert crawling.crawling_enabled() is False


def test_crawler_settings_stay_visible_by_default() -> None:
    schema = WebSearchConfig.model_json_schema()
    assert (
        "crawlerConfig" in schema["properties"]
        or "crawler_config" in schema["properties"]
    )


@pytest.mark.usefixtures("crawl_off")
def test_crawler_settings_are_hidden_when_crawling_is_off() -> None:
    schema = WebSearchConfig.model_json_schema()
    assert "crawlerConfig" not in schema["properties"]
    assert "crawler_config" not in schema["properties"]


@pytest.mark.usefixtures("crawl_off")
def test_crawler_settings_are_hidden_when_the_config_is_nested() -> None:
    class Manifest(BaseModel):
        configuration: WebSearchConfig = Field(default_factory=WebSearchConfig)

    schema = Manifest.model_json_schema()
    properties = schema["$defs"]["WebSearchConfig"]["properties"]
    assert "crawlerConfig" not in properties
    assert "crawler_config" not in properties


@pytest.mark.usefixtures("crawl_off")
def test_v2_plan_hint_drops_read_url_when_crawling_is_off() -> None:
    hint = WebSearchPlan.schema_hint(SearchEngineMode.STANDARD)
    assert '"step_type": "search"' in hint
    assert "read_url" not in hint


@pytest.mark.usefixtures("crawl_off")
def test_v3_hint_drops_read_urls_when_crawling_is_off() -> None:
    hint = WebSearchV3ToolParameters.schema_hint()
    assert "read_urls" not in hint
    model = WebSearchV3ToolParameters.with_exposed_params(None)
    assert "read_urls" not in model.model_json_schema()


def _v3_prompts() -> tuple[str, str]:
    strategy = WebSearchV3Strategy(WebSearchV3Config())
    ctx = Mock(exposed_params_cls=None, date_string="24 November 2026")
    return strategy.tool_description(ctx), strategy.system_prompt(ctx)


@pytest.mark.usefixtures("crawl_off")
def test_v3_prompts_stop_offering_read_urls_when_crawling_is_off() -> None:
    description, system_prompt = _v3_prompts()
    assert "read_urls" not in description
    assert "read_urls" not in system_prompt
    assert "Full-page reads are turned off" in description
    assert "Pages cannot be opened" in system_prompt


def test_v3_prompts_offer_read_urls_by_default() -> None:
    description, system_prompt = _v3_prompts()
    assert 'command: "read_urls"' in description
    assert 'the first call should be `command: "read_urls"`' in system_prompt


@pytest.mark.usefixtures("crawl_off")
@pytest.mark.asyncio
async def test_v2_drops_read_steps_before_max_steps_truncates(
    executor_context_objects: dict,
    mock_executor_dependencies: dict,
) -> None:
    plan = WebSearchPlan(
        objective="o",
        query_analysis="a",
        steps=[
            Step(
                step_type=StepType.READ_URL, objective="r", query_or_url="https://x.ch"
            ),
            Step(step_type=StepType.SEARCH, objective="s", query_or_url="SNB rate"),
        ],
        expected_outcome="e",
    )
    executor = WebSearchV2Executor(
        services=executor_context_objects["services"],
        config=executor_context_objects["config"],
        callbacks=executor_context_objects["callbacks"],
        tool_call=mock_executor_dependencies["tool_call"],
        tool_parameters=plan,
        max_steps=1,
    )
    executor._drop_read_steps_if_crawling_is_off()
    await executor._enforce_max_steps()
    assert [step.step_type for step in executor.tool_parameters.steps] == [
        StepType.SEARCH
    ]


def test_v2_search_only_plan_does_not_look_up_the_crawl_switch(
    monkeypatch, executor_context_objects: dict, mock_executor_dependencies: dict
) -> None:
    lookup = Mock(return_value=False)
    monkeypatch.setattr(
        "unique_web_search.services.executors.v2.executor.crawling_enabled", lookup
    )
    plan = WebSearchPlan(
        objective="o",
        query_analysis="a",
        steps=[Step(step_type=StepType.SEARCH, objective="s", query_or_url="q")],
        expected_outcome="e",
    )
    executor = WebSearchV2Executor(
        services=executor_context_objects["services"],
        config=executor_context_objects["config"],
        callbacks=executor_context_objects["callbacks"],
        tool_call=mock_executor_dependencies["tool_call"],
        tool_parameters=plan,
    )
    executor._drop_read_steps_if_crawling_is_off()
    lookup.assert_not_called()
    assert len(executor.tool_parameters.steps) == 1


def test_v2_schema_hint_reads_the_crawl_switch_once(monkeypatch) -> None:
    lookup = Mock(side_effect=[True, False, False])
    monkeypatch.setattr(
        "unique_web_search.services.executors.v2.schema.crawling_enabled", lookup
    )
    hint = WebSearchPlan.schema_hint(SearchEngineMode.STANDARD)
    assert lookup.call_count == 1
    assert "search | read_url" in hint
    assert "read_url steps" in hint


def test_v3_schema_hint_reads_the_crawl_switch_once(monkeypatch) -> None:
    lookup = Mock(side_effect=[True, False, False])
    monkeypatch.setattr(
        "unique_web_search.services.executors.v3.schema.crawling_enabled", lookup
    )
    hint = WebSearchV3ToolParameters.schema_hint()
    assert lookup.call_count == 1
    assert '`"read_urls"`' in hint
    assert 'For `"read_urls"`' in hint


def _v2_system_prompt() -> str:
    strategy = WebSearchV2Strategy(WebSearchV2Config())
    ctx = Mock(
        search_engine_config=GoogleConfig(search_engine_id="cx-123"),
        date_string="24 November 2026",
    )
    return strategy.system_prompt(ctx)


@pytest.mark.usefixtures("crawl_off")
def test_v2_prompt_and_examples_drop_read_url_when_crawling_is_off() -> None:
    system_prompt = _v2_system_prompt()
    assert "read_url" not in system_prompt
    assert "plan only `search` steps" in system_prompt


def test_v2_prompt_and_examples_keep_read_url_by_default() -> None:
    system_prompt = _v2_system_prompt()
    assert '"step_type": "read_url"' in system_prompt
    assert "URL Reading Steps" in system_prompt
