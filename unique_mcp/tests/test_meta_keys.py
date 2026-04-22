from __future__ import annotations

import pytest

from unique_mcp.meta_keys import META_FLAT_ALIASES, MetaKeys


@pytest.mark.ai
def test_metakeys_is_str_enum() -> None:
    """Every member must behave as a plain string (StrEnum contract)."""
    assert isinstance(MetaKeys.USER_ID, str)
    assert MetaKeys.USER_ID == "unique.app/auth/user-id"


@pytest.mark.ai
def test_all_flat_aliases_map_to_known_canonical_keys() -> None:
    canonical_values = {member.value for member in MetaKeys}
    for canonical in META_FLAT_ALIASES:
        assert canonical in canonical_values


@pytest.mark.ai
def test_all_canonical_keys_are_namespaced() -> None:
    for member in MetaKeys:
        assert member.value.startswith("unique.app/"), (
            f"{member.name}={member.value!r} must be under the unique.app/ namespace"
        )


@pytest.mark.ai
def test_flat_aliases_are_camel_case_strings() -> None:
    for alias in META_FLAT_ALIASES.values():
        assert isinstance(alias, str) and alias
        assert "/" not in alias, (
            f"Flat aliases should be camelCase (no slashes); got {alias!r}"
        )


@pytest.mark.ai
def test_metakeys_reverse_lookup() -> None:
    """Round-tripping a wire value produces the matching enum member."""
    assert MetaKeys("unique.app/chat/chat-id") is MetaKeys.CHAT_ID
