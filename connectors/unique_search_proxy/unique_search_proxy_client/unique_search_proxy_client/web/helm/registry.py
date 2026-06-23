from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from pydantic import BaseModel
from pydantic_settings import BaseSettings

from unique_search_proxy_client.web.helm.metadata import (
    EgressRule,
    HelmSettingsKind,
    helm_env_prefix,
    helm_meta,
)
from unique_search_proxy_client.web.helm.url_safety_registration import (
    URL_SAFETY_ENV_PREFIX,
    URL_SAFETY_HELM_KEY,
    URL_SAFETY_MODEL,
    URL_SAFETY_TITLE,
    url_safety_settings,
)
from unique_search_proxy_client.web.settings.client import http_client_settings
from unique_search_proxy_client.web.settings.monitoring import prometheus_settings
from unique_search_proxy_client.web.settings.providers import (
    bing_agent_credentials,
    brave_search_credentials,
    firecrawl_crawl_credentials,
    google_search_credentials,
    jina_crawl_credentials,
    perplexity_search_credentials,
    tavily_crawl_credentials,
    vertexai_agent_credentials,
)


@dataclass(frozen=True)
class HelmSettingsGroup:
    """One env-backed settings group for startup reporting and Helm generation."""

    title: str
    model: type[BaseSettings]
    instance: BaseModel
    env_prefix: str
    helm_key: str | None
    kind: HelmSettingsKind
    gated: bool
    egress: EgressRule | None = None


# Order is authoritative: it drives the order of every generated Helm artifact
# (values.yaml, _providers.tpl, schema) and the startup report. Adding a group
# means adding its singleton here; all metadata (title, helm_key, kind, egress,
# env prefix) is declared once on the class via @helm_settings / @provider_credentials.
_REGISTERED_INSTANCES: tuple[BaseSettings, ...] = (
    google_search_credentials,
    brave_search_credentials,
    perplexity_search_credentials,
    bing_agent_credentials,
    vertexai_agent_credentials,
    tavily_crawl_credentials,
    jina_crawl_credentials,
    firecrawl_crawl_credentials,
    http_client_settings,
    prometheus_settings,
)


def _group_from_instance(instance: BaseSettings) -> HelmSettingsGroup:
    runtime_cls = type(instance)
    meta = helm_meta(runtime_cls)
    return HelmSettingsGroup(
        title=meta.title,
        # meta.model is the originally decorated class; type(instance) is the
        # dynamic ``Settings`` subclass created by get_settings (same fields).
        model=meta.model,
        instance=instance,
        env_prefix=helm_env_prefix(runtime_cls),
        helm_key=meta.helm_key,
        kind=meta.kind,
        gated=meta.gated,
        egress=meta.egress,
    )


def _url_safety_settings_group() -> HelmSettingsGroup:
    return HelmSettingsGroup(
        title=URL_SAFETY_TITLE,
        model=URL_SAFETY_MODEL,
        instance=url_safety_settings,
        env_prefix=URL_SAFETY_ENV_PREFIX,
        helm_key=URL_SAFETY_HELM_KEY,
        kind="urlSafety",
        # urlSafety has its own real ``enabled`` field (URL_SAFETY_ENABLED); it is
        # not wrapped in a synthetic helm gate.
        gated=False,
    )


def all_settings_groups() -> tuple[HelmSettingsGroup, ...]:
    """All settings groups shown in the startup report."""
    return (
        *(_group_from_instance(instance) for instance in _REGISTERED_INSTANCES),
        _url_safety_settings_group(),
    )


def helm_generated_groups() -> Iterable[HelmSettingsGroup]:
    """Settings groups that produce Helm values blocks and template hooks."""
    for group in all_settings_groups():
        if group.helm_key is not None:
            yield group


def startup_report_groups() -> Iterable[tuple[str, BaseModel, str]]:
    """Legacy tuple shape used by startup_report."""
    for group in all_settings_groups():
        yield group.title, group.instance, group.env_prefix
