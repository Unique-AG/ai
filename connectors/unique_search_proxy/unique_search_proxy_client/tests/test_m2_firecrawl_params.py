from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError
from unique_search_proxy_core.crawlers.firecrawl.schema import (
    FIRECRAWL_MAX_CACHE_AGE_SECONDS,
)
from unique_search_proxy_core.errors import BadRequestProxyError
from unique_search_proxy_core.search_engines.config_types import parse_search_request
from unique_search_proxy_core.search_engines.firecrawl.schema import (
    FIRECRAWL_MAX_QUERY_LENGTH,
    FIRECRAWL_MAX_RESULTS,
    ExposableCategory,
    ExposableCountry,
    ExposableDomainList,
    ExposableLocation,
    ExposableTimeFilter,
    FirecrawlSearchConfig,
    FirecrawlSearchRequest,
)

from unique_search_proxy_client.web.core.search_engines.firecrawl.request_body import (
    build_firecrawl_search_body,
)


def _body(config: FirecrawlSearchConfig | None = None, **overrides: Any) -> dict:
    request = (config or FirecrawlSearchConfig()).merge(overrides, query="hello")
    return build_firecrawl_search_body(query="hello", request=request)


class TestFirecrawlMerge:
    @pytest.mark.ai
    def test_merge__lets_call_value_win__for_exposed_time_filter(self) -> None:
        """
        Purpose: Verify per-call values override the admin default and plain
            settings are kept.
        Why this matters: The model picks the time filter per question; the
            admin's other settings must still apply to every search.
        Setup summary: Merge a config with a week filter and `qdr:d` from the
            call; assert the call value wins and the country is kept.
        """
        config = FirecrawlSearchConfig(
            time_filter=ExposableTimeFilter(expose=True, value="qdr:w"),
            country=ExposableCountry(expose=False, value="CH"),
            fetch_size=5,
        )

        request = config.merge({"timeFilter": "qdr:d"}, query="hello")

        assert isinstance(request, FirecrawlSearchRequest)
        assert request.query == "hello"
        assert request.time_filter == "qdr:d"
        assert request.country == "CH"
        assert request.fetch_size == 5
        assert request.sources == "web"
        assert request.scrape_results is False

    @pytest.mark.ai
    def test_parse_search_request__accepts_camel_case_payload__for_firecrawl(
        self,
    ) -> None:
        """
        Purpose: Verify the flat camelCase wire payload parses into the request.
        Why this matters: This is the body the SDK and the web search tool send.
        Setup summary: Parse a firecrawl payload; assert the typed fields.
        """
        request = parse_search_request(
            {
                "engine": "firecrawl",
                "query": "unique ag",
                "fetchSize": 5,
                "sources": "web_and_news",
                "scrapeResults": True,
                "includeDomains": ["example.com"],
                "timeFilter": "qdr:m",
            },
        )

        assert isinstance(request, FirecrawlSearchRequest)
        assert request.fetch_size == 5
        assert request.sources == "web_and_news"
        assert request.scrape_results is True
        assert request.include_domains == ["example.com"]
        assert request.time_filter == "qdr:m"


class TestFirecrawlRequestBody:
    @pytest.mark.ai
    def test_build_body__asks_for_previews_only__by_default(self) -> None:
        """
        Purpose: Verify the default body asks Firecrawl for ten web results
            and no page content.
        Why this matters: Defaults decide cost and data flow for every space
            that does not change them. Reading pages inside the search costs a
            credit per result on every search, so it must be a choice.
        Setup summary: Build the body from a default config; assert it in full.
        """
        assert _body() == {
            "query": "hello",
            "limit": 10,
            "sources": ["web"],
            "timeout": 60000,
            "ignoreInvalidURLs": True,
        }

    @pytest.mark.ai
    def test_build_body__reads_recent_pages_as_markdown__when_scraping(self) -> None:
        """
        Purpose: Verify reading pages inside the search asks for Markdown, at
            most ten minutes old, with PDFs capped at 10 pages.
        Why this matters: These options decide the cost and freshness of every
            page Firecrawl reads for the space.
        Setup summary: Build the body with page reading on; assert the options.
        """
        body = _body(FirecrawlSearchConfig(scrape_results=True))

        assert body["scrapeOptions"] == {
            "formats": [{"type": "markdown"}],
            "onlyMainContent": True,
            "removeBase64Images": True,
            "maxAge": 600_000,
            "parsers": [{"type": "pdf", "maxPages": 10}, "image"],
        }

    @pytest.mark.ai
    def test_build_body__maps_search_options__to_firecrawl_fields(self) -> None:
        """
        Purpose: Verify previews, safe search, category and date sorting use
            Firecrawl's field names and combine with the time filter.
        Why this matters: Firecrawl ignores unknown fields without an error, so
            a wrong name would leave the option silently off.
        Setup summary: Turn each option away from its default; assert the body.
        """
        config = FirecrawlSearchConfig(
            highlights=False,
            safe_search=True,
            sort_by_date=True,
            ignore_invalid_urls=False,
            time_filter=ExposableTimeFilter(expose=False, value="qdr:w"),
            category=ExposableCategory(expose=False, value="pdf"),
        )

        body = _body(config)

        assert body["highlights"] is False
        assert body["safe"] is True
        assert body["tbs"] == "sbd:1,qdr:w"
        assert body["categories"] == ["pdf"]
        assert body["ignoreInvalidURLs"] is False

    @pytest.mark.ai
    def test_build_body__sorts_by_date__without_a_time_filter(self) -> None:
        """
        Purpose: Verify date sorting alone is sent as `tbs`.
        Why this matters: Sorting must not depend on a time filter being set.
        Setup summary: Build the body with only date sorting; assert `tbs`.
        """
        body = _body(FirecrawlSearchConfig(sort_by_date=True))

        assert body["tbs"] == "sbd:1"

    @pytest.mark.ai
    def test_merge__lets_call_choose_category__when_exposed(self) -> None:
        """
        Purpose: Verify the model can pick a category per search once exposed.
        Why this matters: In search mode V3 the model narrows a search to PDFs
            or government sources itself; the admin default must not block it.
        Setup summary: Expose the category; merge `gov` from the call; assert it.
        """
        config = FirecrawlSearchConfig(
            category=ExposableCategory(expose=True, value=None)
        )

        request = config.merge({"category": "gov"}, query="hello")

        assert request.category == "gov"
        assert "category" in config.exposed_params_model().model_fields

    @pytest.mark.ai
    def test_build_body__omits_parsers__when_pdf_pages_unlimited(self) -> None:
        """
        Purpose: Verify "No limit" leaves Firecrawl's own parsers in place.
        Why this matters: The base merge drops unset values; without the
            override the 10-page default would silently come back.
        Setup summary: Build the body from a config with no PDF limit; assert
            no `parsers`.
        """
        body = _body(FirecrawlSearchConfig(scrape_results=True, max_pdf_pages=None))

        assert "parsers" not in body["scrapeOptions"]

    @pytest.mark.ai
    def test_config__rejects_pdf_pages__outside_firecrawl_range(self) -> None:
        """
        Purpose: Verify the PDF page limit stays within what Firecrawl accepts.
        Why this matters: Firecrawl rejects `maxPages` below 1 or above 10000,
            which would fail every search of the space.
        Setup summary: Build configs with 0 and 10001 pages; assert both fail.
        """
        with pytest.raises(ValidationError):
            FirecrawlSearchConfig(max_pdf_pages=0)
        with pytest.raises(ValidationError):
            FirecrawlSearchConfig(max_pdf_pages=10_001)

    @pytest.mark.ai
    def test_build_body__omits_scrape_options__when_pages_are_not_read(self) -> None:
        """
        Purpose: Verify no scrape options are sent when Firecrawl does not read
            the result pages.
        Why this matters: Sending them makes Firecrawl fetch every result page
            and charge a credit for each, against the admin's setting.
        Setup summary: Build the body with page reading off; assert the key
            is absent.
        """
        body = _body(FirecrawlSearchConfig(scrape_results=False))

        assert "scrapeOptions" not in body

    @pytest.mark.ai
    def test_build_body__maps_optional_settings__to_firecrawl_fields(self) -> None:
        """
        Purpose: Verify optional settings use Firecrawl's field names.
        Why this matters: A wrong field name is ignored by Firecrawl without an
            error, so the filter would silently not apply.
        Setup summary: Set time filter, country, location and cache age; assert
            each Firecrawl field, with the cache age converted from seconds to
            milliseconds.
        """
        config = FirecrawlSearchConfig(
            time_filter=ExposableTimeFilter(expose=False, value="qdr:w"),
            country=ExposableCountry(expose=False, value="CH"),
            location=ExposableLocation(expose=False, value="Zurich,Switzerland"),
            scrape_results=True,
            max_cache_age_seconds=30,
            only_main_content=False,
        )

        body = _body(config)

        assert body["tbs"] == "qdr:w"
        assert body["country"] == "CH"
        assert body["location"] == "Zurich,Switzerland"
        assert body["scrapeOptions"]["maxAge"] == 30_000
        assert body["scrapeOptions"]["onlyMainContent"] is False

    @pytest.mark.ai
    def test_build_body__converts_timeout_to_milliseconds(self) -> None:
        """
        Purpose: Verify the timeout in seconds is sent to Firecrawl in milliseconds.
        Why this matters: Sent as seconds, Firecrawl would give up after a
            fraction of a second and every search would time out.
        Setup summary: Build the body with a 45 second timeout; assert 45000.
        """
        body = _body(FirecrawlSearchConfig(timeout=45))

        assert body["timeout"] == 45_000

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("enterprise", "expected"),
        [(None, None), ([], None), (["zdr"], ["zdr"])],
        ids=["unset", "empty", "zdr"],
    )
    def test_build_body__sends_enterprise__only_when_a_mode_is_set(
        self,
        enterprise: list[str] | None,
        expected: list[str] | None,
    ) -> None:
        """
        Purpose: Verify ``enterprise`` is sent only when a mode is configured.
        Why this matters: Firecrawl rejects the field for accounts without zero
            data retention, so an empty value must not be sent.
        Setup summary: Build the body per case; assert the field or its absence.
        """
        request = FirecrawlSearchConfig().merge({}, query="hello")

        body = build_firecrawl_search_body(
            query="hello", request=request, enterprise=enterprise
        )

        assert body.get("enterprise") == expected

    @pytest.mark.ai
    def test_build_body__truncates_query__above_firecrawl_limit(self) -> None:
        """
        Purpose: Verify a query longer than Firecrawl's limit is truncated.
        Why this matters: Firecrawl rejects longer queries, which would fail
            the whole search instead of running a slightly shorter one.
        Setup summary: Build the body with an over-long query; assert its length.
        """
        query = "a" * (FIRECRAWL_MAX_QUERY_LENGTH + 20)
        request = FirecrawlSearchConfig().merge({}, query=query)

        body = build_firecrawl_search_body(query=query, request=request)

        assert len(body["query"]) == FIRECRAWL_MAX_QUERY_LENGTH


class TestFirecrawlDomainFilters:
    @pytest.mark.ai
    def test_build_body__sends_exclude_domains__without_an_include_list(self) -> None:
        """
        Purpose: Verify the admin's excluded domains are sent, normalised.
        Why this matters: The exclude list keeps unwanted sources out of every
            search; hostnames typed with capitals or spaces must still match.
        Setup summary: Exclude two unnormalised hosts; assert the cleaned list.
        """
        body = _body(FirecrawlSearchConfig(exclude_domains=[" Example.com ", "b.org."]))

        assert body["excludeDomains"] == ["example.com", "b.org"]
        assert "includeDomains" not in body

    @pytest.mark.ai
    def test_build_body__removes_excluded_hosts__from_the_include_list(self) -> None:
        """
        Purpose: Verify excluded hosts and their subdomains are removed from the
            include list, and only one list is sent.
        Why this matters: Firecrawl rejects a request with both lists; dropping
            the exclusions instead would let a blocked source back in.
        Setup summary: Include three hosts and exclude one of them; assert the
            include list keeps only the allowed host.
        """
        config = FirecrawlSearchConfig(
            include_domains=ExposableDomainList(
                expose=False,
                value=["snb.ch", "blocked.com", "news.blocked.com"],
            ),
            exclude_domains=["blocked.com"],
        )

        body = _body(config)

        assert body["includeDomains"] == ["snb.ch"]
        assert "excludeDomains" not in body

    @pytest.mark.ai
    def test_build_body__rejects_search__when_every_include_domain_is_excluded(
        self,
    ) -> None:
        """
        Purpose: Verify the search is refused when no include domain remains.
        Why this matters: Falling back to an unrestricted search would return
            results from the whole web, the opposite of what was configured.
        Setup summary: Include and exclude the same host; assert the error.
        """
        config = FirecrawlSearchConfig(
            include_domains=ExposableDomainList(expose=False, value=["blocked.com"]),
            exclude_domains=["blocked.com"],
        )

        with pytest.raises(BadRequestProxyError, match="also excluded"):
            _body(config)


class TestFirecrawlConfigExposure:
    @pytest.mark.ai
    def test_exposed_params__contain_only_time_filter__by_default(self) -> None:
        """
        Purpose: Verify the model can set only the time filter by default.
        Why this matters: Anything exposed here can be chosen per search by the
            model; region and domain filters must stay under admin control.
        Setup summary: Build the exposed model from a default config; assert
            its properties.
        """
        exposed = FirecrawlSearchConfig().exposed_params_model()

        assert exposed is not None
        assert set(exposed.model_json_schema()["properties"]) == {"timeFilter"}

    @pytest.mark.ai
    def test_exposed_params__include_domains__when_admin_exposes_them(self) -> None:
        """
        Purpose: Verify an admin can expose the include list to the model.
        Why this matters: Some spaces want the model to narrow a search to
            specific sites; the exclude list must stay hidden regardless.
        Setup summary: Expose include_domains; assert it appears under its
            camelCase alias and exclude_domains does not.
        """
        config = FirecrawlSearchConfig(
            include_domains=ExposableDomainList(expose=True, value=None),
        )

        exposed = config.exposed_params_model()

        assert exposed is not None
        properties = exposed.model_json_schema()["properties"]
        assert "includeDomains" in properties
        assert "excludeDomains" not in properties


class TestFirecrawlConfigValidation:
    @pytest.mark.ai
    def test_config__rejects_free_form_time_filter(self) -> None:
        """
        Purpose: Verify only the five preset time filters are accepted.
        Why this matters: The value is passed to the search engine as-is and
            can be set by the model, so free-form input must not get through.
        Setup summary: Merge a custom date-range string; assert validation fails.
        """
        with pytest.raises(ValidationError):
            FirecrawlSearchConfig().merge(
                {"timeFilter": "cdr:1,cd_min:1/1/2024"}, query="hello"
            )

    @pytest.mark.ai
    def test_config__rejects_country__that_is_not_two_capital_letters(self) -> None:
        """
        Purpose: Verify the country must be an ISO 3166-1 alpha-2 code.
        Why this matters: Firecrawl ignores unknown countries and falls back to
            the US, so a typo would silently localise results wrongly.
        Setup summary: Build a config with `Switzerland`; assert validation fails.
        """
        with pytest.raises(ValidationError):
            FirecrawlSearchConfig(
                country=ExposableCountry(expose=False, value="Switzerland"),
            )

    @pytest.mark.ai
    def test_config__uses_defaults__when_dropdowns_are_null(self) -> None:
        """
        Purpose: Verify null dropdowns load as their defaults.
        Why this matters: The admin form can store null after an engine switch;
            failing on it would make the space's web search unusable.
        Setup summary: Validate a config with both null; assert web only and
            the deployment's zero data retention.
        """
        config = FirecrawlSearchConfig.model_validate(
            {"engine": "firecrawl", "sources": None, "zeroDataRetention": None}
        )

        assert config.sources == "web"
        assert config.zero_data_retention == "deployment"

    @pytest.mark.ai
    def test_build_body__sends_news_only__for_the_news_source(self) -> None:
        """
        Purpose: Verify the "News" choice searches news alone.
        Why this matters: Sending web as well would double the cost of a
            search the admin limited to news.
        Setup summary: Build the body with news; assert the source list.
        """
        body = _body(FirecrawlSearchConfig(sources="news"))

        assert body["sources"] == ["news"]

    @pytest.mark.ai
    def test_build_body__sends_both_sources__for_web_and_news(self) -> None:
        """
        Purpose: Verify the "Web and news" choice becomes both Firecrawl sources.
        Why this matters: Firecrawl only knows source lists; a wrong mapping
            would silently drop news or the web.
        Setup summary: Build the body with web and news; assert the list.
        """
        body = _body(FirecrawlSearchConfig(sources="web_and_news"))

        assert body["sources"] == ["web", "news"]

    @pytest.mark.ai
    def test_build_body__omits_cache_age__when_firecrawl_default_is_chosen(
        self,
    ) -> None:
        """
        Purpose: Verify choosing Firecrawl's default cache sends no `maxAge`.
        Why this matters: Sending 0 would force live reads the admin turned off.
        Setup summary: Build the body with no cache age; assert the key is absent.
        """
        body = _body(
            FirecrawlSearchConfig(scrape_results=True, max_cache_age_seconds=None)
        )

        assert "maxAge" not in body["scrapeOptions"]

    @pytest.mark.ai
    def test_config__rejects_fetch_size__above_the_firecrawl_cap(self) -> None:
        """
        Purpose: Verify the result count is capped for admins and for requests.
        Why this matters: Firecrawl rejects more than 100 results, which would
            fail every search of the space.
        Setup summary: Build a config and merge a request above the cap; assert
            both fail validation.
        """
        with pytest.raises(ValidationError):
            FirecrawlSearchConfig(fetch_size=FIRECRAWL_MAX_RESULTS + 1)
        with pytest.raises(ValidationError):
            FirecrawlSearchConfig().merge(
                {"fetchSize": FIRECRAWL_MAX_RESULTS + 1}, query="hello"
            )

    @pytest.mark.ai
    def test_config__rejects_cache_age__above_seven_days(self) -> None:
        """
        Purpose: Verify the cache age cannot exceed Firecrawl's seven-day cap.
        Why this matters: Firecrawl silently lowers larger values, so the admin
            would see a setting that is not applied.
        Setup summary: Build a config one second over seven days; assert
            validation fails.
        """
        with pytest.raises(ValidationError):
            FirecrawlSearchConfig(
                max_cache_age_seconds=FIRECRAWL_MAX_CACHE_AGE_SECONDS + 1
            )


class TestFirecrawlConfigForm:
    @pytest.mark.ai
    def test_json_schema__labels_time_filter_codes__for_the_admin_form(self) -> None:
        """
        Purpose: Verify the admin form gets a readable label for every time
            filter code.
        Why this matters: Without labels the form lists `qdr:h` to `qdr:y`,
            which an admin cannot interpret.
        Setup summary: Read the time filter value schema; assert the labelled
            options and that no bare `enum` overrides them.
        """
        defs = FirecrawlSearchConfig.model_json_schema()["$defs"]
        time_filter = next(
            branch
            for definition in defs.values()
            for branch in definition.get("properties", {})
            .get("value", {})
            .get("anyOf", [])
            if branch.get("title") == "Recent results only"
        )

        assert "enum" not in time_filter
        assert time_filter["oneOf"] == [
            {"const": "qdr:h", "title": "Past hour"},
            {"const": "qdr:d", "title": "Past day"},
            {"const": "qdr:w", "title": "Past week"},
            {"const": "qdr:m", "title": "Past month"},
            {"const": "qdr:y", "title": "Past year"},
        ]

    @pytest.mark.ai
    def test_exposed_params__keep_plain_time_filter_codes__for_the_model(
        self,
    ) -> None:
        """
        Purpose: Verify the model-facing schema still lists the plain codes.
        Why this matters: The form labels are for admins; the model must send
            the codes Firecrawl accepts.
        Setup summary: Read the exposed params schema; assert the code enum.
        """
        schema = FirecrawlSearchConfig().exposed_params_model().model_json_schema()

        assert schema["properties"]["timeFilter"]["anyOf"][0]["enum"] == [
            "qdr:h",
            "qdr:d",
            "qdr:w",
            "qdr:m",
            "qdr:y",
        ]
