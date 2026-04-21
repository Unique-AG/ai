from __future__ import annotations

import pytest

from unique_mcp.context_requirements import (
    CONTEXT_REQUIREMENTS_META_KEY,
    ContextRequirements,
    merge_tool_meta,
)
from unique_mcp.meta_keys import MetaKeys


@pytest.mark.ai
def test_to_tool_meta_emits_canonical_key() -> None:
    reqs = ContextRequirements(
        required=[MetaKeys.USER_ID, MetaKeys.COMPANY_ID],
        optional=["unique.app/search/content-ids"],
    )
    meta = reqs.to_tool_meta()
    assert CONTEXT_REQUIREMENTS_META_KEY in meta
    payload = meta[CONTEXT_REQUIREMENTS_META_KEY]
    assert isinstance(payload, dict)
    assert payload["required"] == [MetaKeys.USER_ID, MetaKeys.COMPANY_ID]
    assert payload["optional"] == ["unique.app/search/content-ids"]
    assert payload["accepts_custom"] is False


@pytest.mark.ai
def test_merge_tool_meta_preserves_existing_keys() -> None:
    base: dict[str, object] = {
        "unique.app/icon": "data:image/svg",
        "other": 1,
    }
    reqs = ContextRequirements(required=[MetaKeys.USER_ID])
    merged = merge_tool_meta(base, reqs)

    assert merged["unique.app/icon"] == "data:image/svg"
    assert merged["other"] == 1
    assert CONTEXT_REQUIREMENTS_META_KEY in merged
    assert base == {"unique.app/icon": "data:image/svg", "other": 1}, (
        "merge_tool_meta must not mutate the input base dict"
    )


@pytest.mark.ai
def test_accepts_custom_flag_serialises() -> None:
    reqs = ContextRequirements(required=[MetaKeys.USER_ID], accepts_custom=True)
    payload = reqs.to_tool_meta()[CONTEXT_REQUIREMENTS_META_KEY]
    assert isinstance(payload, dict)
    assert payload["accepts_custom"] is True


@pytest.mark.ai
def test_merge_tool_meta_with_none_base() -> None:
    reqs = ContextRequirements(required=[MetaKeys.USER_ID])
    merged = merge_tool_meta(None, reqs)
    assert list(merged.keys()) == [CONTEXT_REQUIREMENTS_META_KEY]
