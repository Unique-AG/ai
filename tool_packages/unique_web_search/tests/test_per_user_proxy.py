from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr
from unique_search_proxy_core.context import RequestContext

import unique_web_search.services.client.proxy_config as proxy_config
from unique_web_search.settings import Base


def _context(external_user_id: str | None = "client-user") -> RequestContext:
    return RequestContext(
        company_id="company-1",
        user_id="internal-user",
        chat_id="chat-1",
        external_user_id=external_user_id,
    )


def _settings(password: str | None = "placeholder") -> Base:
    return Base(
        proxy_host="proxy.example.com",
        proxy_port=8080,
        per_user_proxy_company_ids=["company-1"],
        per_user_proxy_password=(SecretStr(password) if password is not None else None),
    )


@pytest.mark.ai
def test_build_legacy_crawl_client_uses_external_user_proxy_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_proxy: dict[str, object] = {}
    client = MagicMock()

    class FakeProxy:
        def __init__(self, **kwargs: object) -> None:
            captured_proxy.update(kwargs)

    async_client = MagicMock(return_value=client)
    monkeypatch.setattr(proxy_config, "env_settings", _settings())
    monkeypatch.setattr(proxy_config, "Proxy", FakeProxy)
    monkeypatch.setattr(proxy_config, "AsyncClient", async_client)

    result = proxy_config.build_legacy_crawl_client(_context(), timeout=12.0)

    assert result is client
    assert captured_proxy["url"] == "http://proxy.example.com:8080"
    assert captured_proxy["auth"] == ("client-user", "placeholder")
    async_client.assert_called_once()
    assert async_client.call_args.kwargs["proxy"].__class__ is FakeProxy
    assert async_client.call_args.kwargs["trust_env"] is False
    assert async_client.call_args.kwargs["timeout"] == 12.0


@pytest.mark.ai
def test_build_legacy_crawl_client_accepts_empty_placeholder_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_proxy: dict[str, object] = {}

    class FakeProxy:
        def __init__(self, **kwargs: object) -> None:
            captured_proxy.update(kwargs)

    monkeypatch.setattr(proxy_config, "env_settings", _settings(""))
    monkeypatch.setattr(proxy_config, "Proxy", FakeProxy)
    monkeypatch.setattr(proxy_config, "AsyncClient", MagicMock())

    proxy_config.build_legacy_crawl_client(_context())

    assert captured_proxy["auth"] == ("client-user", "")


@pytest.mark.ai
def test_build_legacy_crawl_client_fails_closed_without_external_user_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(proxy_config, "env_settings", _settings())

    with pytest.raises(ValueError, match="External user ID"):
        proxy_config.build_legacy_crawl_client(_context(None))


@pytest.mark.ai
def test_build_legacy_crawl_client_fails_closed_without_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(proxy_config, "env_settings", _settings(None))

    with pytest.raises(ValueError, match="password must be configured"):
        proxy_config.build_legacy_crawl_client(_context())


@pytest.mark.ai
def test_build_legacy_crawl_client_keeps_shared_client_for_ungated_company(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared_client = MagicMock()
    shared_factory = MagicMock(return_value=shared_client)
    monkeypatch.setattr(proxy_config, "env_settings", Base())
    monkeypatch.setattr(proxy_config, "async_client", shared_factory)

    result = proxy_config.build_legacy_crawl_client(_context(), timeout=12.0)

    assert result is shared_client
    shared_factory.assert_called_once_with(timeout=12.0)
