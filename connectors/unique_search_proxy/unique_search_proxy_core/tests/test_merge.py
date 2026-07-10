"""Config.merge: deployment defaults + overrides -> validated request."""

import pytest
from pydantic import ValidationError

from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_search_proxy_core.search_engines.google.schema import (
    ExposableStrOrNone,
    GoogleConfig,
    GoogleSearchRequest,
)


class TestMerge:
    @pytest.mark.ai
    def test_admin_default_merged(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=False, value="d7"),
        )
        request = config.merge({}, query="x")
        assert isinstance(request, GoogleSearchRequest)
        assert request.date_restrict == "d7"

    @pytest.mark.ai
    def test_deactivated_knob_dropped(self) -> None:
        config = GoogleConfig(
            date_restrict=ExposableStrOrNone(expose=True, value=None),
        )
        request = config.merge({}, query="x")
        assert request.date_restrict is None

    @pytest.mark.ai
    def test_override_wins_over_admin_default(self) -> None:
        config = GoogleConfig(
            gl=ExposableStrOrNone(expose=True, value="us"),
        )
        request = config.merge({"gl": "de"}, query="x")
        assert request.gl == "de"

    @pytest.mark.ai
    def test_query_required(self) -> None:
        with pytest.raises(ValidationError):
            GoogleConfig().merge({}, query="")

    @pytest.mark.ai
    def test_engine_injected_from_config(self) -> None:
        request = GoogleConfig().merge({}, query="x")
        assert request.engine == SearchEngineType.GOOGLE

    @pytest.mark.ai
    def test_plain_config_fields_carried_over(self) -> None:
        config = GoogleConfig(fetch_size=5, safe="off")
        request = config.merge({}, query="x")
        assert request.fetch_size == 5
        assert request.safe == "off"

    @pytest.mark.ai
    def test_invalid_override_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GoogleConfig().merge({"fetch_size": 0}, query="x")
