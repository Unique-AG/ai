"""Tests for Briefing API resource."""

from unittest.mock import patch

import pytest

from unique_sdk import Briefing as BriefingPublic
from unique_sdk.api_resources._briefing import Briefing

_FIXED_ISO = "2020-06-01T12:34:56.789Z"
_MIN_PROMPTS: list[Briefing.BriefingPromptItem] = [
    {"title": "Smoke", "body": "Prompt body for tests."}
]


@pytest.mark.ai
def test_AI_briefing_exported_from_unique_sdk():
    """Briefing class is re-exported from the package root.

    Why this matters: Public API consumers import from unique_sdk directly.
    Setup summary: Compare public import to module-level Briefing class.
    """
    assert BriefingPublic is Briefing


@pytest.mark.ai
@patch.object(Briefing, "_static_request", autospec=True)
def test_AI_upsert_for_assistant_calls_put_with_text_generated_at_and_prompts(
    mock_static,
):
    """upsert sends PUT JSON with ``text``, ``generatedAt``, and ``prompts``.

    Why this matters: Server validates PublicUpsertBriefingRequestDto keys and types.
    Setup summary: Mock _static_request. Pass text + generatedAt + prompts. Assert payload.
    """
    mock_static.return_value = {
        "id": "bf1",
        "object": "briefing",
        "assistantId": "as/x",
        "text": "c",
        "createdAt": "t1",
        "updatedAt": "t2",
    }

    Briefing.upsert_for_assistant(
        user_id="u1",
        company_id="co1",
        assistant_id="as/x",
        text="Briefing markdown",
        generatedAt=_FIXED_ISO,
        prompts=_MIN_PROMPTS,
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
    assert params == {
        "text": "Briefing markdown",
        "generatedAt": _FIXED_ISO,
        "prompts": _MIN_PROMPTS,
    }


@pytest.mark.ai
@pytest.mark.asyncio
@patch.object(Briefing, "_static_request_async", autospec=True)
async def test_AI_upsert_for_assistant_async_calls_put(mock_async):
    """Async variant mirrors sync PUT semantics.

    Why this matters: Async callers must serialize the same JSON body.
    Setup summary: Mock _static_request_async. Await upsert_for_assistant_async.
    Assert put and payload.
    """
    mock_async.return_value = {
        "id": "bf1",
        "object": "briefing",
        "assistantId": "aid",
        "text": "c",
        "createdAt": "t1",
        "updatedAt": "t2",
    }

    await Briefing.upsert_for_assistant_async(
        user_id="u1",
        company_id="co1",
        assistant_id="aid",
        text="txt",
        generatedAt=_FIXED_ISO,
        prompts=[],
    )

    mock_async.assert_called_once()
    acall = mock_async.call_args[0]
    assert acall[0] == "put"
    assert acall[1] == "/briefings/aid"
    assert acall[4] == {"text": "txt", "generatedAt": _FIXED_ISO, "prompts": []}


@pytest.mark.ai
@patch.object(Briefing, "_static_request", autospec=True)
def test_AI_upsert_maps_content_kwarg_to_text(mock_static):
    """Legacy content= keyword is forwarded as JSON ``text``.

    Why this matters: Backwards compatibility during OpenAPI-aligned naming rollout.
    Setup summary: Call upsert with content= only, generatedAt frozen. Expect text.
    """
    mock_static.return_value = {
        "id": "bf1",
        "object": "briefing",
        "assistantId": "a",
        "text": "c",
        "createdAt": "t1",
        "updatedAt": "t2",
    }

    Briefing.upsert_for_assistant(
        user_id="u",
        company_id="c",
        assistant_id="aid",
        content="legacy body",
        generatedAt=_FIXED_ISO,
        prompts=[],
    )

    params = mock_static.call_args[0][4]
    assert params == {
        "text": "legacy body",
        "generatedAt": _FIXED_ISO,
        "prompts": [],
    }


@pytest.mark.ai
@patch.object(Briefing, "_static_request", autospec=True)
@patch("unique_sdk.api_resources._briefing._utc_iso8601_now")
def test_AI_upsert_defaults_generated_at_when_blank(mock_now, mock_static):
    """Omitted blank ``generatedAt`` uses fixed UTC ISO default.

    Why this matters: API requires ISO 8601; SDK supplies now when unspecified.
    Setup summary: Patch _utc_iso8601_now. Call with text only. Expect default.
    """
    mock_now.return_value = _FIXED_ISO
    mock_static.return_value = {
        "id": "bf",
        "object": "briefing",
        "assistantId": "a",
        "text": "hello",
        "generatedAt": _FIXED_ISO,
    }

    Briefing.upsert_for_assistant(
        user_id="u",
        company_id="co",
        assistant_id="a1",
        text="hello",
        prompts=[{"title": "t", "body": "b"}],
    )

    mock_static.assert_called_once()
    mock_now.assert_called_once()
    assert mock_static.call_args[0][4] == {
        "text": "hello",
        "generatedAt": _FIXED_ISO,
        "prompts": [{"title": "t", "body": "b"}],
    }


@pytest.mark.ai
@patch.object(Briefing, "_static_request", autospec=True)
def test_AI_upsert_strips_request_option_keys_from_json_body(mock_static):
    """Per-call ``api_key`` / ``api_base`` / ``headers`` are not sent in the PUT body.

    Why this matters: POST/PUT JSON must match the API DTO only.
    Setup summary: Pass api_key alongside briefing fields. Assert body omits it.
    """
    mock_now_iso = _FIXED_ISO

    mock_static.return_value = {
        "id": "bf",
        "object": "briefing",
        "externalId": "x",
        "text": "t",
        "generatedAt": mock_now_iso,
        "prompts": [],
        "createdAt": "c",
        "updatedAt": "u",
    }

    Briefing.upsert_for_assistant(
        user_id="u",
        company_id="c",
        assistant_id="aid",
        text="body",
        generatedAt=mock_now_iso,
        prompts=[],
        api_key="secret-should-not-be-in-body",
        api_base="https://example.invalid/base",
        headers={"X-Foo": "bar"},
    )

    sent = mock_static.call_args[0][4]
    assert set(sent.keys()) == {"text", "generatedAt", "prompts"}
    assert sent["text"] == "body"
    assert sent["prompts"] == []
    assert sent["generatedAt"] == mock_now_iso


@pytest.mark.ai
def test_AI_upsert_raises_when_text_over_4000():
    """Overlong ``text`` is rejected locally before hitting the wire.

    Why this matters: Matches OpenAPI/server max length; avoids needless round trip.
    Setup summary: Call _finalize indirectly via upsert keyword text of length 4001.
    Expect ValueError.
    """

    big = "a" * 4001
    with pytest.raises(ValueError, match="4000"):
        Briefing.upsert_for_assistant(
            user_id="u",
            company_id="c",
            assistant_id="a",
            text=big,
            generatedAt=_FIXED_ISO,
            prompts=[{"title": "x", "body": "y"}],
        )


@pytest.mark.ai
def test_AI_upsert_raises_when_prompts_omitted():
    """Missing ``prompts`` is rejected (OpenAPI-required field).

    Why this matters: Server expects a list (possibly empty) for full replacement.
    Setup summary: Omit prompts. Expect ValueError mentioning prompts.
    """

    with pytest.raises(ValueError, match="prompts"):
        Briefing.upsert_for_assistant(  # type: ignore[call-arg]
            user_id="u",
            company_id="c",
            assistant_id="a",
            text="hello",
            generatedAt=_FIXED_ISO,
        )


@pytest.mark.ai
def test_AI_upsert_raises_when_too_many_prompts():
    """More than 200 prompts are rejected locally."""

    prompts: list[Briefing.BriefingPromptItem] = [
        {"title": str(i), "body": "b"} for i in range(201)
    ]
    with pytest.raises(ValueError, match="200"):
        Briefing.upsert_for_assistant(
            user_id="u",
            company_id="c",
            assistant_id="a",
            text="t",
            prompts=prompts,
        )


@pytest.mark.ai
def test_AI_upsert_raises_when_prompt_body_too_long():
    """Prompt body over 4000 characters is rejected."""

    long_body = "b" * 4001
    with pytest.raises(ValueError, match="4000"):
        Briefing.upsert_for_assistant(
            user_id="u",
            company_id="c",
            assistant_id="a",
            text="txt",
            prompts=[{"title": "x", "body": long_body}],
        )


@pytest.mark.ai
@patch.object(Briefing, "_static_request", autospec=True)
def test_AI_retrieve_for_assistant_calls_get(mock_static):
    """retrieve_for_assistant issues GET on /briefings/{assistantId}."""
    mock_static.return_value = {
        "object": "briefing",
        "externalId": "as/x",
        "text": "body",
        "generatedAt": _FIXED_ISO,
        "prompts": [],
        "createdAt": "t1",
        "updatedAt": "t2",
    }

    Briefing.retrieve_for_assistant(
        user_id="u1",
        company_id="co1",
        assistant_id="as/x",
    )

    mock_static.assert_called_once_with("get", "/briefings/as%2Fx", "u1", "co1")


@pytest.mark.ai
@pytest.mark.asyncio
@patch.object(Briefing, "_static_request_async", autospec=True)
async def test_AI_retrieve_for_assistant_async_calls_get(mock_async):
    """Async retrieve mirrors sync GET URL and method."""
    mock_async.return_value = {
        "object": "briefing",
        "externalId": "aid",
        "text": "c",
        "generatedAt": _FIXED_ISO,
        "prompts": [],
        "createdAt": "t1",
        "updatedAt": "t2",
    }

    await Briefing.retrieve_for_assistant_async(
        user_id="u1",
        company_id="co1",
        assistant_id="aid",
    )

    mock_async.assert_called_once_with("get", "/briefings/aid", "u1", "co1")


@pytest.mark.ai
@patch.object(Briefing, "_static_request", autospec=True)
def test_AI_delete_for_assistant_calls_delete(mock_static):
    """delete_for_assistant issues DELETE on /briefings/{assistantId}."""
    mock_static.return_value = {
        "object": "deleted-briefing",
        "id": "as/x",
        "deleted": True,
    }

    result = Briefing.delete_for_assistant(
        user_id="u1",
        company_id="co1",
        assistant_id="as/x",
    )

    mock_static.assert_called_once_with("delete", "/briefings/as%2Fx", "u1", "co1")
    assert result["object"] == "deleted-briefing"
    assert result["deleted"] is True


@pytest.mark.ai
@pytest.mark.asyncio
@patch.object(Briefing, "_static_request_async", autospec=True)
async def test_AI_delete_for_assistant_async_calls_delete(mock_async):
    """Async delete mirrors sync DELETE semantics."""
    mock_async.return_value = {
        "object": "deleted-briefing",
        "id": "aid",
        "deleted": True,
    }

    await Briefing.delete_for_assistant_async(
        user_id="u1",
        company_id="co1",
        assistant_id="aid",
    )

    mock_async.assert_called_once_with("delete", "/briefings/aid", "u1", "co1")


@pytest.mark.ai
@patch.object(Briefing, "_static_request", autospec=True)
def test_AI_upsert_sends_title_when_provided(mock_static):
    """Optional title= is included in the PUT JSON body."""
    mock_static.return_value = {
        "object": "briefing",
        "externalId": "aid",
        "text": "t",
        "title": "Today's Briefing",
        "generatedAt": _FIXED_ISO,
        "prompts": [],
        "createdAt": "c",
        "updatedAt": "u",
    }

    Briefing.upsert_for_assistant(
        user_id="u",
        company_id="c",
        assistant_id="aid",
        text="body",
        title="Today's Briefing",
        generatedAt=_FIXED_ISO,
        prompts=[],
    )

    payload = mock_static.call_args[0][4]
    assert payload["title"] == "Today's Briefing"


@pytest.mark.ai
def test_AI_upsert_raises_when_title_over_100():
    """Overlong title is rejected locally before hitting the wire."""
    with pytest.raises(ValueError, match="100"):
        Briefing.upsert_for_assistant(
            user_id="u",
            company_id="c",
            assistant_id="a",
            text="txt",
            title="t" * 101,
            prompts=[],
        )
