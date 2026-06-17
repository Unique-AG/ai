import pytest
from unique_search_proxy_core.errors import EngineNotConfiguredError

from unique_search_proxy_client.web.core.registry import (
    clear_registries_for_tests,
    get_search_engine,
    registered_search_engines,
)


@pytest.fixture(autouse=True)
def _clear_registry() -> None:
    clear_registries_for_tests()
    yield
    clear_registries_for_tests()


class TestGetSearchEngine:
    @pytest.mark.ai
    def test_registry_starts_empty(self) -> None:
        assert registered_search_engines() == frozenset()

    @pytest.mark.ai
    def test_unregistered_engine_raises(self) -> None:
        with pytest.raises(EngineNotConfiguredError, match="not registered"):
            get_search_engine("google")
