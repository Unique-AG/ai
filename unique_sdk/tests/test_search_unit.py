"""Unit tests for ``Search`` / ``SearchString`` (public search DTO parity)."""

from __future__ import annotations

import unique_sdk


def test_AI_search_create_params_allows_minimal_body():
    """Public create search only requires searchString and searchType."""
    params: unique_sdk.Search.CreateParams = {
        "searchString": "query",
        "searchType": "COMBINED",
    }
    assert params["searchType"] == "COMBINED"


def test_AI_search_string_history_message_accepts_any_role_string():
    """History entries use the same role strings as stored messages (not only lowercase)."""
    msg: unique_sdk.SearchString.HistoryMessage = {"role": "USER", "text": "hi"}
    assert msg["role"] == "USER"


def test_AI_search_string_create_accepts_freeform_language_model():
    """languageModel is an open string on the public create DTO."""
    params: unique_sdk.SearchString.CreateParams = {
        "prompt": "expand",
        "languageModel": "gpt-4o-mini",
    }
    assert params["languageModel"] == "gpt-4o-mini"
