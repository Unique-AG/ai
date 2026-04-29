"""Tests for Briefing API resource."""

from unittest.mock import patch

import pytest

from unique_sdk import Briefing as BriefingPublic
from unique_sdk.api_resources._briefing import Briefing


@pytest.mark.ai
def test_AI_briefing_exported_from_unique_sdk():
    """Briefing class is re-exported from the package root.

    Why this matters: Public API consumers import from unique_sdk directly.
    Setup summary: Compare public import to module class. Assert identity.
    """
    assert BriefingPublic is Briefing


@pytest.mark.ai
@patch.object(Briefing, "_static_request", autospec=True)
def test_AI_upsert_for_assistant_calls_put_with_encoded_path(mock_static):
    """upsert_for_assistant issues PUT /briefings/{assistantId} with body keys.

    Why this matters: Contract with OpenAPI BriefingController_upsertForAssistant.
    Setup summary: Mock _static_request. Call upsert_for_assistant with content.
    Assert method, URL path encoding, params.
    """
    mock_static.return_value = {
        "id": "bf1",
        "object": "briefing",
        "assistantId": "as/x",
        "content": "c",
        "title": None,
        "createdAt": "t1",
        "updatedAt": "t2",
    }

    Briefing.upsert_for_assistant(
        user_id="u1",
        company_id="co1",
        assistant_id="as/x",
        content="Briefing markdown",
    )

    mock_static.assert_called_once()
    call_args = mock_static.call_args[0]
    method = call_args[0]
    url = call_args[1]
    uid = call_args[2]
    cid = call_args[3]
    params = call_args[4]
    assert method == "put"
    assert uid == "u1"
    assert cid == "co1"
    assert "/briefings/as%2Fx" == url
    assert params == {"content": "Briefing markdown"}


@pytest.mark.ai
@pytest.mark.asyncio
@patch.object(Briefing, "_static_request_async", autospec=True)
async def test_AI_upsert_for_assistant_async_calls_put(mock_async):
    """Async variant mirrors sync PUT semantics.

    Why this matters: Async callers must hit the same route and serialize the same body.
    Setup summary: Mock _static_request_async. Await upsert_for_assistant_async.
    Assert put and params.
    """
    mock_async.return_value = {
        "id": "bf1",
        "object": "briefing",
        "assistantId": "aid",
        "content": "c",
        "title": None,
        "createdAt": "t1",
        "updatedAt": "t2",
    }

    await Briefing.upsert_for_assistant_async(
        user_id="u1",
        company_id="co1",
        assistant_id="aid",
        content="txt",
    )

    mock_async.assert_called_once()
    acall = mock_async.call_args[0]
    assert acall[0] == "put"
    assert acall[1] == "/briefings/aid"
    assert acall[4] == {"content": "txt"}
