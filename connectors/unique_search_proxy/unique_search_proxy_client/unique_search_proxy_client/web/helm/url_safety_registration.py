"""Helm registration for URL Safety settings.

``UrlSafetySettings`` still lives in ``unique_search_proxy_core`` because the
web-search tool depends on it as legacy shared config. When that model moves
into this client package it can adopt ``@helm_settings`` like the other groups;
until then this module owns the one-off section layout and field metadata.
"""

from __future__ import annotations

from collections.abc import Mapping

from unique_search_proxy_core.url_safety.settings import (
    UrlSafetySettings,
    url_safety_settings,
)

from unique_search_proxy_client.web.helm.metadata import assign_field_sections

URL_SAFETY_ENV_PREFIX = "URL_SAFETY_"
URL_SAFETY_HELM_KEY = "urlSafety"
URL_SAFETY_TITLE = "URL Safety"

_URL_SAFETY_SECTIONS: dict[str, list[str]] = {
    "redirects": [
        "resolve_redirects",
        "max_redirect_hops",
        "redirect_timeout_seconds",
    ],
    "network": [
        "cluster_local_suffix",
        "service_suffix",
        "allowed_schemes",
        "localhost_hosts",
        "metadata_hosts",
    ],
}


def _assign_field_helm_flags(
    model: type[UrlSafetySettings],
    flags: Mapping[str, Mapping[str, bool]],
) -> None:
    """Merge extra ``helm`` keys onto named fields (e.g. ``block_level``)."""
    unknown = set(flags) - set(model.model_fields)
    if unknown:
        msg = f"{model.__name__}: unknown fields {sorted(unknown)}"
        raise ValueError(msg)

    for name, helm_flags in flags.items():
        info = model.model_fields[name]
        extra = info.json_schema_extra
        if extra is None:
            extra = {}
            info.json_schema_extra = extra
        if not isinstance(extra, dict):
            msg = f"{name!r} has non-dict json_schema_extra; cannot merge"
            raise TypeError(msg)
        helm = extra.setdefault("helm", {})
        if not isinstance(helm, dict):
            msg = f"{name!r} has non-dict helm json_schema_extra"
            raise TypeError(msg)
        for key, value in helm_flags.items():
            helm.setdefault(key, value)


def configure_url_safety_helm_model(model: type[UrlSafetySettings]) -> None:
    """Inject Helm section metadata onto ``UrlSafetySettings`` model fields."""
    assign_field_sections(model, _URL_SAFETY_SECTIONS)
    _assign_field_helm_flags(
        model,
        {
            "enabled": {"block_level": True},
            # Expose these lists to overlays so customer-managed tenants can tune
            # SSRF guardrails per environment. Overlays replace the whole list.
            "allowed_schemes": {"overridable": True},
            "localhost_hosts": {"overridable": True},
            "metadata_hosts": {"overridable": True},
        },
    )


URL_SAFETY_MODEL = type(url_safety_settings)
configure_url_safety_helm_model(URL_SAFETY_MODEL)
