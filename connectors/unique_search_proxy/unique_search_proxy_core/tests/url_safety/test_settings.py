import pytest

from unique_search_proxy_core.http_client import ProxySettings
from unique_search_proxy_core.url_safety import (
    UrlSafetySettings,
    validate_url_safety_proxy_configuration,
)


@pytest.mark.ai
def test_url_safety_enabled__defaults_to_true() -> None:
    """
    Purpose: Verify application URL checks remain the default.
    Why this matters: Deployments must be protected without additional configuration.
    Setup summary: Construct default settings and assert checks are enabled.
    """
    settings = UrlSafetySettings()

    assert settings.enabled is True


@pytest.mark.ai
def test_url_safety_enabled__loads_false_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify application checks can be disabled by environment.
    Why this matters: Customer deployments configure this security boundary through Helm.
    Setup summary: Set URL_SAFETY_ENABLED and assert boolean parsing.
    """
    monkeypatch.setenv("URL_SAFETY_ENABLED", "false")

    settings = UrlSafetySettings()

    assert settings.enabled is False


@pytest.mark.ai
def test_validate_proxy_configuration__application_mode_allows_direct_egress() -> None:
    """
    Purpose: Verify normal application checks do not require a corporate proxy.
    Why this matters: Existing protected deployments use direct egress.
    Setup summary: Validate default URL safety and proxy settings without an exception.
    """
    validate_url_safety_proxy_configuration(
        UrlSafetySettings(enabled=True),
        ProxySettings(),
    )


@pytest.mark.ai
def test_validate_proxy_configuration__disabled_mode_requires_proxy_endpoint() -> None:
    """
    Purpose: Verify disabled mode fails without a proxy endpoint.
    Why this matters: URL checks must never be bypassed while traffic leaves directly.
    Setup summary: Disable checks without proxy host or port and assert failure.
    """
    with pytest.raises(
        ValueError,
        match="URL_SAFETY_ENABLED=false is incompatible with direct egress",
    ):
        validate_url_safety_proxy_configuration(
            UrlSafetySettings(enabled=False),
            ProxySettings(),
        )


@pytest.mark.ai
def test_validate_proxy_configuration__disabled_mode_rejects_direct_route() -> None:
    """
    Purpose: Verify host and port alone cannot authorize a bypassed safety policy.
    Why this matters: The current no-auth route uses direct egress despite endpoint values.
    Setup summary: Configure an unused endpoint and assert fail-closed validation.
    """
    with pytest.raises(
        ValueError,
        match="URL_SAFETY_ENABLED=false requires every request",
    ):
        validate_url_safety_proxy_configuration(
            UrlSafetySettings(enabled=False),
            ProxySettings(
                proxy_host="proxy.example.com",
                proxy_port=8080,
            ),
        )


@pytest.mark.ai
def test_validate_proxy_configuration__disabled_mode_accepts_authenticated_proxy() -> (
    None
):
    """
    Purpose: Verify an authenticated proxy permits disabled mode.
    Why this matters: Corporate proxy deployments need an intentional bypass mechanism.
    Setup summary: Configure username/password proxy settings and assert validation passes.
    """
    validate_url_safety_proxy_configuration(
        UrlSafetySettings(enabled=False),
        ProxySettings(
            proxy_auth_mode="username_password",
            proxy_host="proxy.example.com",
            proxy_port=8080,
            proxy_username="service-user",
        ),
    )


@pytest.mark.ai
def test_validate_proxy_configuration__disabled_mode_rejects_partial_tenant_proxy() -> (
    None
):
    """
    Purpose: Verify a tenant allowlist cannot protect a process-wide URL safety bypass.
    Why this matters: Non-allowlisted tenants would otherwise use unvalidated direct egress.
    Setup summary: Configure per-user proxying for one tenant and assert failure.
    """
    with pytest.raises(
        ValueError,
        match="URL_SAFETY_ENABLED=false requires every request",
    ):
        validate_url_safety_proxy_configuration(
            UrlSafetySettings(enabled=False),
            ProxySettings(
                proxy_username_source="user_metadata",
                proxy_host="proxy.example.com",
                proxy_port=8080,
                per_user_proxy_company_ids=["company-a"],
            ),
        )


@pytest.mark.ai
def test_validate_proxy_configuration__disabled_mode_accepts_global_user_proxy() -> (
    None
):
    """
    Purpose: Verify globally required per-user proxying permits disabled mode.
    Why this matters: BNPP-style identity-aware proxies resolve credentials per request.
    Setup summary: Configure user-metadata proxying for all tenants and assert success.
    """
    validate_url_safety_proxy_configuration(
        UrlSafetySettings(enabled=False),
        ProxySettings(
            proxy_username_source="user_metadata",
            proxy_host="proxy.example.com",
            proxy_port=8080,
        ),
    )


@pytest.mark.ai
def test_validate_proxy_configuration__disabled_ssl_mode_requires_certificate() -> None:
    """
    Purpose: Verify incomplete mutual-TLS proxy settings fail during startup.
    Why this matters: Disabled mode must not defer broken proxy configuration to a request.
    Setup summary: Select SSL proxy auth without a certificate and assert failure.
    """
    with pytest.raises(
        ValueError,
        match="URL_SAFETY_ENABLED=false with ssl_tls proxy authentication",
    ):
        validate_url_safety_proxy_configuration(
            UrlSafetySettings(enabled=False),
            ProxySettings(
                proxy_auth_mode="ssl_tls",
                proxy_host="proxy.example.com",
                proxy_port=8443,
            ),
        )
