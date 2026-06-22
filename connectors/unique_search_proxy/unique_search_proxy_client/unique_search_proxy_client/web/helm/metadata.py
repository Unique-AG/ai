"""Helm-registry metadata, decoupled from credential checking.

``@helm_settings`` attaches the metadata the Helm generator and startup report
need (title, ``helm_key``, ``kind``, egress derivation) to *any* ``BaseSettings``
class. Provider classes combine it with ``@provider_credentials`` (which owns
``_env_prefix`` for secret validation); non-provider settings such as
``HttpClientSettings`` and ``PrometheusSettings`` use only ``@helm_settings`` and
pass their ``env_prefix`` here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TypeVar

from pydantic_settings import BaseSettings


@dataclass(frozen=True)
class EgressEndpointField:
    """Egress host derived by URL-parsing one connection field at render time.

    Use when every operation talks to a single host carried by a full-URL field
    (e.g. ``api_endpoint``). The generated Cilium rule pins that exact host and
    follows a per-environment override of the field.
    """

    field_name: str = "api_endpoint"


@dataclass(frozen=True)
class EgressDomainWildcard:
    """Egress allowed via a wildcard FQDN over a domain field's value.

    Use when a provider reaches several computed subdomains of a single domain
    (e.g. Jina's reader/search hosts under ``api_domain``). Emits a Cilium
    ``toFQDNs: matchPattern: "*.<domain>"`` rule, so it covers every subdomain
    and still follows a per-environment override of the domain field.
    """

    field_name: str
    port: str = "443"


EgressRule = EgressEndpointField | EgressDomainWildcard
"""How a settings group's outbound egress hosts are derived from its settings."""

_DEFAULT_EGRESS: EgressRule = EgressEndpointField()

HelmSettingsKind = Literal["provider", "httpClient", "urlSafety", "internal"]


@dataclass(frozen=True)
class HelmGroupMeta:
    """Helm-registry metadata attached to a settings class by ``helm_settings``."""

    model: type[BaseSettings]
    title: str
    helm_key: str | None
    kind: HelmSettingsKind
    egress: EgressRule | None = None


_HELM_META_ATTR = "_helm_meta"
_ENV_PREFIX_ATTR = "_env_prefix"

S = TypeVar("S", bound=type[BaseSettings])


def helm_settings(
    *,
    title: str,
    helm_key: str | None,
    kind: HelmSettingsKind = "provider",
    egress: EgressRule | None = _DEFAULT_EGRESS,
    env_prefix: str | None = None,
) -> Callable[[S], S]:
    """Attach Helm-registry metadata to a settings class.

    Pass ``env_prefix`` for classes that are *not* credential providers (their
    ``_env_prefix`` is otherwise unset); for provider classes leave it out, since
    ``@provider_credentials`` already owns ``_env_prefix``.
    """

    def decorate(cls: S) -> S:
        setattr(
            cls,
            _HELM_META_ATTR,
            HelmGroupMeta(
                model=cls,
                title=title,
                helm_key=helm_key,
                kind=kind,
                egress=egress,
            ),
        )
        if env_prefix is not None:
            setattr(cls, _ENV_PREFIX_ATTR, env_prefix)
        return cls

    return decorate


def helm_meta(cls: type) -> HelmGroupMeta:
    """Return the Helm metadata attached by ``@helm_settings`` (or fail loudly)."""
    meta = getattr(cls, _HELM_META_ATTR, None)
    if not isinstance(meta, HelmGroupMeta):
        raise TypeError(f"{cls.__name__} is missing @helm_settings metadata")
    return meta


def helm_env_prefix(cls: type) -> str:
    """Return the env-var prefix set by ``@provider_credentials``/``helm_settings``."""
    env_prefix = getattr(cls, _ENV_PREFIX_ATTR, None)
    if not isinstance(env_prefix, str):
        raise TypeError(
            f"{cls.__name__} has no env prefix; set it via @provider_credentials "
            "or helm_settings(env_prefix=...)"
        )
    return env_prefix
