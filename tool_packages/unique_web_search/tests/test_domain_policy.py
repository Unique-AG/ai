from unittest.mock import AsyncMock

import pytest
from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.search_engines.google.schema import GoogleConfig

from unique_web_search.services.executors.v2.executor import WebSearchV2Executor
from unique_web_search.services.executors.v2.schema import Step, StepType, WebSearchPlan
from unique_web_search.services.executors.v3.executor import WebSearchV3Executor
from unique_web_search.services.executors.v3.schema import WebSearchV3ToolParameters
from unique_web_search.services.search_engine.domain_policy import DomainPolicy
from unique_web_search.services.search_engine.google import GoogleSearch
from unique_web_search.services.search_engine.perplexity import (
    PerplexitySearch,
    PerplexitySearchConfig,
)

WIKI = "https://en.wikipedia.org/wiki/Swiss_National_Bank"


def test_policy_without_domains_allows_everything() -> None:
    assert DomainPolicy().allows(WIKI)


def test_exclude_blocks_the_host_but_not_its_siblings() -> None:
    policy = DomainPolicy.of(exclude=["en.wikipedia.org"])
    assert not policy.allows(WIKI)
    assert policy.allows("https://de.wikipedia.org/wiki/Schweizerische_Nationalbank")


def test_exclude_of_a_parent_domain_covers_its_subdomains() -> None:
    policy = DomainPolicy.of(exclude=["wikipedia.org"])
    assert not policy.allows(WIKI)
    assert not policy.allows("https://wikipedia.org/")
    assert policy.allows("https://notwikipedia.org/")


def test_exclude_of_one_subdomain_does_not_cover_another() -> None:
    assert DomainPolicy.of(exclude=["www.wikipedia.org"]).allows(WIKI)


def test_include_allows_listed_domains_and_their_subdomains() -> None:
    policy = DomainPolicy.of(include=["snb.ch"])
    assert policy.allows("https://www.snb.ch/en/")
    assert policy.allows("https://snb.ch/en/")
    assert not policy.allows(WIKI)


def test_exclude_wins_over_include() -> None:
    policy = DomainPolicy.of(include=["en.wikipedia.org"], exclude=["en.wikipedia.org"])
    assert not policy.allows(WIKI)


def test_trailing_root_dot_does_not_bypass_an_exclude() -> None:
    policy = DomainPolicy.of(exclude=["en.wikipedia.org."])
    assert not policy.allows("https://en.wikipedia.org./wiki/Swiss_National_Bank")
    assert not policy.allows(WIKI)


def test_trailing_root_dot_still_matches_an_include() -> None:
    policy = DomainPolicy.of(include=["snb.ch"])
    assert policy.allows("https://www.snb.ch./en/")


def test_malformed_url_is_blocked_when_filters_apply() -> None:
    assert not DomainPolicy.of(exclude=["en.wikipedia.org"]).allows("http://[abc/")


def test_malformed_url_is_left_to_the_crawler_without_filters() -> None:
    assert DomainPolicy().allows("http://[abc/")


def test_tld_rule_with_leading_dot_matches_every_host_under_it() -> None:
    policy = DomainPolicy.of(include=[".gov"])
    assert policy.allows("https://www.nasa.gov/missions/")
    assert policy.allows("https://nasa.gov/")
    assert not policy.allows("https://www.snb.ch/")
    assert not policy.allows("https://notgov.com/")


def test_tld_rule_with_leading_dot_excludes_every_host_under_it() -> None:
    policy = DomainPolicy.of(exclude=[".gov"])
    assert not policy.allows("https://www.nasa.gov/missions/")
    assert policy.allows("https://www.snb.ch/")


def test_path_rule_includes_only_that_section() -> None:
    policy = DomainPolicy.of(include=["nature.com/articles"])
    assert policy.allows("https://www.nature.com/articles/intro")
    assert policy.allows("https://nature.com/articles")
    assert not policy.allows("https://www.nature.com/articles-old/intro")
    assert not policy.allows("https://www.nature.com/news/")


def test_path_rule_excludes_only_that_section() -> None:
    policy = DomainPolicy.of(exclude=["nature.com/articles/"])
    assert not policy.allows("https://www.nature.com/articles/intro")
    assert policy.allows("https://www.nature.com/articles-old/intro")
    assert policy.allows("https://www.nature.com/news/")


@pytest.mark.parametrize(
    "url",
    [
        "https://www.nature.com/news/../articles/intro",
        "https://www.nature.com/news/./../articles/intro",
        "https://www.nature.com/news/%2e%2e/articles/intro",
        "https://www.nature.com/news/%2E%2E/articles/intro",
    ],
)
def test_dot_segments_do_not_bypass_an_exclude_path_rule(url: str) -> None:
    policy = DomainPolicy.of(exclude=["nature.com/articles"])
    assert not policy.allows(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.nature.com/articles/../news/intro",
        "https://www.nature.com/articles/%2e%2e/news/intro",
    ],
)
def test_dot_segments_do_not_escape_an_include_path_rule(url: str) -> None:
    policy = DomainPolicy.of(include=["nature.com/articles"])
    assert not policy.allows(url)


def test_resolved_dot_segments_still_match_path_rules() -> None:
    policy = DomainPolicy.of(include=["nature.com/articles"])
    assert policy.allows("https://www.nature.com/news/../articles/intro")
    assert not policy.allows("https://www.nature.com/news/../articles-old/intro")


def test_perplexity_policy_reads_tld_and_path_rules() -> None:
    config = PerplexitySearchConfig(
        search_domain_filter=ExposableParam(
            expose=False, value=["-.gov", "-nature.com/articles"]
        )
    )
    policy = PerplexitySearch(config).domain_policy()
    assert not policy.allows("https://www.nasa.gov/")
    assert not policy.allows("https://www.nature.com/articles/intro")
    assert policy.allows("https://www.nature.com/news/")


def test_perplexity_policy_reads_minus_prefix_as_exclude() -> None:
    config = PerplexitySearchConfig(
        search_domain_filter=ExposableParam(
            expose=False, value=["www.snb.ch", "-en.wikipedia.org"]
        )
    )
    policy = PerplexitySearch(config).domain_policy()
    assert policy.include == frozenset({"www.snb.ch"})
    assert policy.exclude == frozenset({"en.wikipedia.org"})


@pytest.mark.parametrize(
    ("site_filter", "allowed"),
    [("e", False), ("i", True), (None, True)],
)
def test_google_policy_follows_site_search_filter(
    site_filter: str | None, allowed: bool
) -> None:
    config = GoogleConfig(
        search_engine_id="cx-123",
        site_search=ExposableParam(expose=False, value="en.wikipedia.org"),
        site_search_filter=ExposableParam(expose=False, value=site_filter),
    )
    policy = GoogleSearch(config).domain_policy()
    assert policy.allows(WIKI) is allowed
    assert policy.allows("https://www.snb.ch/") is (site_filter == "e")


def test_google_policy_is_open_without_site_search() -> None:
    config = GoogleConfig(search_engine_id="cx-123")
    assert GoogleSearch(config).domain_policy() == DomainPolicy()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_v2_read_url_skips_a_blocked_url(
    executor_context_objects: dict,
    mock_executor_dependencies: dict,
    sample_web_search_plan: WebSearchPlan,
) -> None:
    mock_executor_dependencies[
        "search_service"
    ].domain_policy.return_value = DomainPolicy.of(exclude=["en.wikipedia.org"])
    mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
        return_value=["page"]
    )
    executor = WebSearchV2Executor(
        services=executor_context_objects["services"],
        config=executor_context_objects["config"],
        callbacks=executor_context_objects["callbacks"],
        tool_call=mock_executor_dependencies["tool_call"],
        tool_parameters=sample_web_search_plan,
    )

    result = await executor._execute_read_url_step(
        Step(step_type=StepType.READ_URL, objective="Read", query_or_url=WIKI)
    )

    assert result == []
    mock_executor_dependencies["crawler_service"].crawl.assert_not_called()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_v3_read_urls_reads_only_allowed_urls(
    executor_context_objects: dict,
    mock_executor_dependencies: dict,
) -> None:
    mock_executor_dependencies[
        "search_service"
    ].domain_policy.return_value = DomainPolicy.of(exclude=["en.wikipedia.org"])
    mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
        return_value=["page"]
    )
    tool_parameters = WebSearchV3ToolParameters.model_validate(
        {
            "command": "read_urls",
            "phase": "target",
            "payload": {"urls": [WIKI, "https://www.snb.ch/en/"]},
        }
    )
    executor = WebSearchV3Executor(
        services=executor_context_objects["services"],
        config=executor_context_objects["config"],
        callbacks=executor_context_objects["callbacks"],
        tool_call=mock_executor_dependencies["tool_call"],
        tool_parameters=tool_parameters,
    )

    await executor.run()

    mock_executor_dependencies["crawler_service"].crawl.assert_called_once_with(
        ["https://www.snb.ch/en/"]
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_v3_read_urls_crawls_nothing_when_every_url_is_blocked(
    executor_context_objects: dict,
    mock_executor_dependencies: dict,
) -> None:
    mock_executor_dependencies[
        "search_service"
    ].domain_policy.return_value = DomainPolicy.of(exclude=["en.wikipedia.org"])
    mock_executor_dependencies["crawler_service"].crawl = AsyncMock()
    tool_parameters = WebSearchV3ToolParameters.model_validate(
        {"command": "read_urls", "phase": "target", "payload": {"urls": [WIKI]}}
    )
    executor = WebSearchV3Executor(
        services=executor_context_objects["services"],
        config=executor_context_objects["config"],
        callbacks=executor_context_objects["callbacks"],
        tool_call=mock_executor_dependencies["tool_call"],
        tool_parameters=tool_parameters,
    )

    assert await executor.run() == []
    mock_executor_dependencies["crawler_service"].crawl.assert_not_called()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_v3_read_urls_keeps_valid_urls_next_to_a_malformed_one(
    executor_context_objects: dict,
    mock_executor_dependencies: dict,
) -> None:
    mock_executor_dependencies[
        "search_service"
    ].domain_policy.return_value = DomainPolicy.of(exclude=["en.wikipedia.org"])
    mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
        return_value=["page"]
    )
    tool_parameters = WebSearchV3ToolParameters.model_validate(
        {
            "command": "read_urls",
            "phase": "target",
            "payload": {"urls": ["http://[abc/", "https://www.snb.ch/en/"]},
        }
    )
    executor = WebSearchV3Executor(
        services=executor_context_objects["services"],
        config=executor_context_objects["config"],
        callbacks=executor_context_objects["callbacks"],
        tool_call=mock_executor_dependencies["tool_call"],
        tool_parameters=tool_parameters,
    )

    await executor.run()

    mock_executor_dependencies["crawler_service"].crawl.assert_called_once_with(
        ["https://www.snb.ch/en/"]
    )
