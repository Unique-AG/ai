"""Tests for the generic self-registration registry core."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pytest
from pydantic import BaseModel

from unique_web_search.services._registry import BaseSpec, Registry


class _Kind(StrEnum):
    ALPHA = "alpha"
    BETA = "beta"
    GAMMA = "gamma"


@dataclass(frozen=True)
class _Spec(BaseSpec[_Kind]):
    pass


class _AlphaConfig(BaseModel):
    kind: _Kind = _Kind.ALPHA


class _BetaConfig(BaseModel):
    kind: _Kind = _Kind.BETA


class _AlphaImpl:
    pass


class _BetaImpl:
    pass


@pytest.fixture
def registry() -> Registry[_Kind, _Spec]:
    return Registry(_Spec)


def test_registry__register__stores_spec(registry: Registry[_Kind, _Spec]) -> None:
    @registry.register(name="alpha", key=_Kind.ALPHA, config_cls=_AlphaConfig)
    class _Alpha(_AlphaImpl):
        pass

    spec = registry[_Kind.ALPHA]
    assert spec.name == "alpha"
    assert spec.config_cls is _AlphaConfig
    assert spec.impl_cls is _Alpha


def test_registry__register__raises_on_duplicate_key(
    registry: Registry[_Kind, _Spec],
) -> None:
    @registry.register(name="alpha", key=_Kind.ALPHA, config_cls=_AlphaConfig)
    class _Alpha(_AlphaImpl):
        pass

    with pytest.raises(ValueError, match="already registered"):

        @registry.register(name="alpha2", key=_Kind.ALPHA, config_cls=_AlphaConfig)
        class _AlphaDuplicate(_AlphaImpl):
            pass


def test_registry__name_to_config__maps_names_to_config_classes(
    registry: Registry[_Kind, _Spec],
) -> None:
    @registry.register(name="alpha", key=_Kind.ALPHA, config_cls=_AlphaConfig)
    class _Alpha(_AlphaImpl):
        pass

    @registry.register(name="beta", key=_Kind.BETA, config_cls=_BetaConfig)
    class _Beta(_BetaImpl):
        pass

    assert registry.name_to_config() == {
        "alpha": _AlphaConfig,
        "beta": _BetaConfig,
    }


def test_registry__config_types_from_names__returns_single_type(
    registry: Registry[_Kind, _Spec],
) -> None:
    @registry.register(name="alpha", key=_Kind.ALPHA, config_cls=_AlphaConfig)
    class _Alpha(_AlphaImpl):
        pass

    assert registry.config_types_from_names(["alpha"]) is _AlphaConfig


def test_registry__config_types_from_names__returns_union(
    registry: Registry[_Kind, _Spec],
) -> None:
    @registry.register(name="alpha", key=_Kind.ALPHA, config_cls=_AlphaConfig)
    class _Alpha(_AlphaImpl):
        pass

    @registry.register(name="beta", key=_Kind.BETA, config_cls=_BetaConfig)
    class _Beta(_BetaImpl):
        pass

    union_type = registry.config_types_from_names(["alpha", "beta"])
    assert union_type == (_AlphaConfig | _BetaConfig)


def test_registry__config_types_from_names__raises_for_unknown_name(
    registry: Registry[_Kind, _Spec],
) -> None:
    with pytest.raises(ValueError, match="No config found"):
        registry.config_types_from_names(["missing"])


def test_registry__default_config__returns_first_name(
    registry: Registry[_Kind, _Spec],
) -> None:
    @registry.register(name="alpha", key=_Kind.ALPHA, config_cls=_AlphaConfig)
    class _Alpha(_AlphaImpl):
        pass

    @registry.register(name="beta", key=_Kind.BETA, config_cls=_BetaConfig)
    class _Beta(_BetaImpl):
        pass

    assert registry.default_config(["alpha", "beta"]) is _AlphaConfig


def test_registry__assert_enum_coverage__passes_when_complete(
    registry: Registry[_Kind, _Spec],
) -> None:
    @registry.register(name="alpha", key=_Kind.ALPHA, config_cls=_AlphaConfig)
    class _Alpha(_AlphaImpl):
        pass

    @registry.register(name="beta", key=_Kind.BETA, config_cls=_BetaConfig)
    class _Beta(_BetaImpl):
        pass

    registry.assert_enum_coverage(_Kind, exempt={_Kind.GAMMA})


def test_registry__assert_enum_coverage__raises_for_missing_member(
    registry: Registry[_Kind, _Spec],
) -> None:
    @registry.register(name="alpha", key=_Kind.ALPHA, config_cls=_AlphaConfig)
    class _Alpha(_AlphaImpl):
        pass

    with pytest.raises(AssertionError, match="BETA"):
        registry.assert_enum_coverage(_Kind)
