"""Elicitation commands: create, list, get, respond, wait, and ask the user for input.

Elicitations are user-input requests routed through the Unique AI Platform.
They are the canonical mechanism for an agent (or tool) to pose a question to
the user and wait for a structured answer without leaving the conversation.

The CLI exposes both low-level operations (create / get / respond / list /
wait) and a high-level ``ask`` command that creates a FORM elicitation and
blocks until the user responds or the request expires/times out.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Literal, cast

import unique_sdk
from unique_sdk.cli.formatting import (
    format_elicitation,
    format_elicitation_response,
    format_pending_elicitations,
)
from unique_sdk.cli.state import ShellState

DEFAULT_POLL_INTERVAL_SECONDS = 2.0
DEFAULT_WAIT_TIMEOUT_SECONDS = 300
TERMINAL_STATUSES = {
    "RESPONDED",
    "ACCEPTED",
    "REJECTED",
    "DECLINED",
    "CANCELLED",
    "EXPIRED",
    "COMPLETED",
}

# --- Visibility workaround for UN-19815 ---------------------------------
#
# The chat UI (as of 2026-04-21) only renders an elicitation when the host
# assistant message is actively in ``ThinkingTimeline`` display mode *and*
# the elicitation's ``metadata.messageLogId`` matches a step inside that
# timeline. Elicitations created via the public API / CLI against a chat
# without a currently-streaming assistant turn are therefore silently
# invisible in the UI, even though the backend stores them correctly.
#
# As a workaround we synthesise a minimal thinking timeline around the
# elicitation:
#
# 1. Create a placeholder assistant message with no text and no
#    ``completedAt`` — this satisfies the UI's ``ThinkingTimeline`` gate.
# 2. Create a ``message_log`` step under it in ``RUNNING`` status — the
#    elicitation will reference this step via ``metadata.messageLogId``.
# 3. Create the elicitation with ``messageId`` pointing at the placeholder
#    and the step id wired into ``metadata.messageLogId``.
#
# After the user responds we either collapse the placeholder (set
# ``completedAt`` + a short explanatory text) or delete it entirely, based
# on ``cleanup_mode``. Cleanup runs in a ``finally`` so a Ctrl-C or API
# error doesn't leave a dangling thinking bubble in the chat.
#
# This entire workaround is obsolete once UN-19815 lands in the UI; at
# that point the ``visible`` flag can be marked as a no-op.

CleanupMode = Literal["collapse", "delete"]

DEFAULT_PLACEHOLDER_TEXT = "Waiting for your answer…"
DEFAULT_CLEANUP_MODE: CleanupMode = "collapse"
COLLAPSED_MESSAGE_TEXT_ACCEPTED = "Clarifying question answered."
COLLAPSED_MESSAGE_TEXT_OTHER = "Clarifying question closed."
COMPLETED_STEP_TEXT_ACCEPTED = "Answered."
COMPLETED_STEP_TEXT_OTHER = "Closed."

# Metadata keys used to mark an elicitation as carrying a synthetic
# placeholder so ``cmd_elicit_wait`` knows what to tear down when the
# elicitation reaches a terminal state. Prefixed with ``_uniqueSdk`` to
# stay clearly namespaced from any caller-provided metadata.
META_PLACEHOLDER_MESSAGE_ID = "_uniqueSdkPlaceholderMessageId"
META_PLACEHOLDER_STEP_ID = "_uniqueSdkPlaceholderStepId"
META_PLACEHOLDER_CHAT_ID = "_uniqueSdkPlaceholderChatId"
META_CLEANUP_MODE = "_uniqueSdkCleanupMode"


def _parse_json_arg(value: str | None, *, field: str) -> dict[str, Any] | None:
    """Parse an optional JSON string argument into a dict.

    Raises ``ValueError`` with a user-friendly message if the value is not
    valid JSON or does not decode to a JSON object.
    """
    if value is None:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON for {field}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{field} must be a JSON object")
    return parsed


def _parse_metadata_pairs(
    metadata: list[tuple[str, str]] | None,
) -> dict[str, str] | None:
    """Convert a list of ``(key, value)`` pairs into a metadata dict."""
    if not metadata:
        return None
    return dict(metadata)


def _build_create_params(
    *,
    mode: str,
    message: str,
    tool_name: str,
    schema: dict[str, Any] | None,
    url: str | None,
    chat_id: str | None,
    message_id: str | None,
    expires_in_seconds: int | None,
    external_elicitation_id: str | None,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    """Assemble the ``create_elicitation`` params dict, omitting None values."""
    params: dict[str, Any] = {
        "mode": mode,
        "message": message,
        "toolName": tool_name,
    }
    if schema is not None:
        params["schema"] = schema
    if url is not None:
        params["url"] = url
    if chat_id is not None:
        params["chatId"] = chat_id
    if message_id is not None:
        params["messageId"] = message_id
    if expires_in_seconds is not None:
        params["expiresInSeconds"] = expires_in_seconds
    if external_elicitation_id is not None:
        params["externalElicitationId"] = external_elicitation_id
    if metadata is not None:
        params["metadata"] = metadata
    return params


def _resolve_assistant_id(state: ShellState, chat_id: str) -> str | None:
    """Return an ``assistantId`` usable for ``Message.create`` in this chat.

    Resolution order:

    1. ``$UNIQUE_ASSISTANT_ID`` environment variable.
    2. The most recent ``ASSISTANT``-role message in the chat (via
       ``Message.list``) — pick up its ``assistantId`` field.

    Returns ``None`` if neither source yields a usable id. Callers are
    expected to surface a descriptive error in that case because the chat
    has no assistant context (e.g. a brand-new empty chat).
    """
    env_id = os.environ.get("UNIQUE_ASSISTANT_ID")
    if env_id:
        return env_id

    try:
        listing = unique_sdk.Message.list(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            chatId=chat_id,
        )
    except unique_sdk.APIError:
        return None

    # ``Message`` objects are dict subclasses at runtime, but the static
    # type advertises them as typed resources without ``assistantId`` on
    # the instance. Fall back to ``dict`` access to keep both the type
    # checker and the runtime happy.
    #
    # Resolution strategy:
    #   (a) Preferred: most recent ASSISTANT message's top-level
    #       ``assistantId`` — what internal/admin APIs expose.
    #   (b) Fallback: any message's ``debugInfo.assistant.id`` — the public
    #       gateway exposes the assistant only here, and populates it on
    #       USER messages (not ASSISTANT ones) because it reflects the
    #       assistant that handled the request, not the author of the
    #       message. Since the whole chat is bound to a single assistant,
    #       any message that carries this field gives us the right answer.
    messages = list(listing)

    for msg in reversed(messages):
        msg_dict = cast(dict[str, Any], cast(object, msg))
        if str(msg_dict.get("role", "")).upper() != "ASSISTANT":
            continue
        assistant_id = msg_dict.get("assistantId")
        if isinstance(assistant_id, str) and assistant_id:
            return assistant_id

    for msg in reversed(messages):
        msg_dict = cast(dict[str, Any], cast(object, msg))
        debug_info = msg_dict.get("debugInfo")
        if not isinstance(debug_info, dict):
            continue
        assistant_obj = debug_info.get("assistant")
        if not isinstance(assistant_obj, dict):
            continue
        nested_id = assistant_obj.get("id")
        if isinstance(nested_id, str) and nested_id:
            return nested_id

    return None


def _create_visibility_context(
    state: ShellState,
    *,
    chat_id: str,
    assistant_id: str,
    placeholder_text: str,
) -> tuple[str, str]:
    """Create a placeholder assistant message + running step for visibility.

    Returns ``(placeholder_message_id, step_id)``. Raises ``unique_sdk.APIError``
    (or ``ValueError`` if the platform returns malformed data) so the caller
    can fall back or surface a user-facing error.
    """
    placeholder = unique_sdk.Message.create(
        user_id=state.config.user_id,
        company_id=state.config.company_id,
        chatId=chat_id,
        assistantId=assistant_id,
        role="ASSISTANT",
        text=None,
        references=None,
        debugInfo=None,
        completedAt=None,
    )
    placeholder_id = cast(dict[str, Any], placeholder).get("id")
    if not isinstance(placeholder_id, str) or not placeholder_id:
        raise ValueError("platform did not return a placeholder message id")

    step = unique_sdk.MessageLog.create(
        user_id=state.config.user_id,
        company_id=state.config.company_id,
        messageId=placeholder_id,
        text=placeholder_text,
        status="RUNNING",
        order=0,
    )
    step_id = cast(dict[str, Any], step).get("id")
    if not isinstance(step_id, str) or not step_id:
        raise ValueError("platform did not return a step id for the placeholder")

    return placeholder_id, step_id


def _cleanup_visibility_context(
    state: ShellState,
    *,
    chat_id: str,
    placeholder_message_id: str,
    placeholder_step_id: str,
    cleanup_mode: CleanupMode,
    terminal_status: str | None,
) -> None:
    """Best-effort teardown of the synthetic thinking-timeline placeholder.

    This runs in ``finally`` paths, so it must never raise. API failures are
    swallowed — a dangling placeholder is preferable to masking the real
    error from the caller.
    """
    # Treat both the synchronous respond-action ("ACCEPT") and the backend's
    # persisted terminal status ("ACCEPTED" / "RESPONDED") as "the user
    # answered positively" for the purpose of the cleanup text.
    is_accepted = (terminal_status or "").upper() in {
        "ACCEPT",
        "ACCEPTED",
        "RESPONDED",
    }
    step_text = (
        COMPLETED_STEP_TEXT_ACCEPTED if is_accepted else COMPLETED_STEP_TEXT_OTHER
    )
    try:
        unique_sdk.MessageLog.update(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            message_log_id=placeholder_step_id,
            status="COMPLETED",
            text=step_text,
        )
    except unique_sdk.APIError:
        pass

    try:
        if cleanup_mode == "delete":
            unique_sdk.Message.delete(
                placeholder_message_id,
                state.config.user_id,
                state.config.company_id,
                chatId=chat_id,
            )
        else:
            collapse_text = (
                COLLAPSED_MESSAGE_TEXT_ACCEPTED
                if is_accepted
                else COLLAPSED_MESSAGE_TEXT_OTHER
            )
            # The public API expects ISO-8601 for ``completedAt`` in PATCH
            # bodies; serializing a raw ``datetime`` via ``json.dumps`` would
            # either raise or encode it in a way the backend rejects. Emit
            # the canonical millisecond-precision UTC Z form. The
            # ``ModifyParams`` TypedDict annotates this as ``datetime``, so
            # we cast to appease the type checker — the wire format is the
            # source of truth here.
            completed_at_iso = (
                datetime.now(tz=timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
            )
            unique_sdk.Message.modify(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                id=placeholder_message_id,
                chatId=chat_id,
                text=collapse_text,
                completedAt=cast(Any, completed_at_iso),
            )
    except unique_sdk.APIError:
        pass


def _merge_visibility_metadata(
    user_metadata: dict[str, Any] | None,
    *,
    chat_id: str,
    placeholder_message_id: str,
    placeholder_step_id: str,
    cleanup_mode: CleanupMode,
) -> dict[str, Any]:
    """Merge SDK-owned visibility markers into caller-supplied metadata.

    SDK keys win over caller keys on collision — the caller should not use
    the ``_uniqueSdk...`` namespace, and if they do, we refuse to let them
    break the cleanup contract.
    """
    merged: dict[str, Any] = dict(user_metadata or {})
    merged["messageLogId"] = placeholder_step_id
    merged[META_PLACEHOLDER_MESSAGE_ID] = placeholder_message_id
    merged[META_PLACEHOLDER_STEP_ID] = placeholder_step_id
    merged[META_PLACEHOLDER_CHAT_ID] = chat_id
    merged[META_CLEANUP_MODE] = cleanup_mode
    return merged


def _extract_visibility_context(
    elicitation: dict[str, Any] | None,
) -> tuple[str, str, str, CleanupMode] | None:
    """Return ``(chat_id, message_id, step_id, cleanup_mode)`` if markers set.

    Looks at ``metadata`` on a fetched elicitation to decide whether the
    SDK created a synthetic placeholder for this elicitation and therefore
    owns its teardown.
    """
    if not elicitation:
        return None
    metadata = elicitation.get("metadata")
    if not isinstance(metadata, dict):
        return None
    message_id = metadata.get(META_PLACEHOLDER_MESSAGE_ID)
    step_id = metadata.get(META_PLACEHOLDER_STEP_ID)
    chat_id = metadata.get(META_PLACEHOLDER_CHAT_ID)
    mode_raw = metadata.get(META_CLEANUP_MODE) or DEFAULT_CLEANUP_MODE
    if not (
        isinstance(message_id, str)
        and isinstance(step_id, str)
        and isinstance(chat_id, str)
    ):
        return None
    mode: CleanupMode = "delete" if str(mode_raw).lower() == "delete" else "collapse"
    return chat_id, message_id, step_id, mode


def cmd_elicit_create(
    state: ShellState,
    *,
    mode: str,
    message: str,
    tool_name: str,
    schema: str | None = None,
    url: str | None = None,
    chat_id: str | None = None,
    message_id: str | None = None,
    expires_in_seconds: int | None = None,
    external_elicitation_id: str | None = None,
    metadata: list[tuple[str, str]] | None = None,
    visible: bool = True,
    assistant_id: str | None = None,
    placeholder_text: str = DEFAULT_PLACEHOLDER_TEXT,
    cleanup_mode: CleanupMode = DEFAULT_CLEANUP_MODE,
) -> str:
    """Create an elicitation request (FORM or URL mode).

    When ``chat_id`` is set and ``visible`` is ``True`` (the default), the
    SDK materialises a placeholder assistant message + running step so the
    chat UI will actually render the elicitation — see the module-level
    "Visibility workaround for UN-19815" note. The placeholder stays in the
    chat's thinking state until the elicitation reaches a terminal status,
    at which point ``cmd_elicit_wait`` will collapse or delete it. Pass
    ``visible=False`` to skip this and create a bare elicitation (useful
    once the UI fix in UN-19815 ships, or for scripted flows that don't
    need a visible prompt).
    """
    try:
        mode_upper = mode.upper()
        if mode_upper not in ("FORM", "URL"):
            return f"elicit: invalid mode '{mode}' (expected FORM or URL)"

        parsed_schema = _parse_json_arg(schema, field="--schema")
        if mode_upper == "FORM" and parsed_schema is None:
            return "elicit: --schema is required when --mode FORM"
        if mode_upper == "URL" and not url:
            return "elicit: --url is required when --mode URL"

        user_metadata = _parse_metadata_pairs(metadata)
        effective_message_id = message_id
        placeholder_message_id: str | None = None
        placeholder_step_id: str | None = None

        if visible and chat_id and not message_id:
            resolved_assistant = assistant_id or _resolve_assistant_id(state, chat_id)
            if not resolved_assistant:
                return (
                    "elicit: cannot create a visible elicitation without an "
                    "assistant id; pass --assistant-id or set "
                    "UNIQUE_ASSISTANT_ID, or pass --no-visible to skip the "
                    "visibility workaround"
                )
            placeholder_message_id, placeholder_step_id = _create_visibility_context(
                state,
                chat_id=chat_id,
                assistant_id=resolved_assistant,
                placeholder_text=placeholder_text,
            )
            effective_message_id = placeholder_message_id
            user_metadata = _merge_visibility_metadata(
                user_metadata,
                chat_id=chat_id,
                placeholder_message_id=placeholder_message_id,
                placeholder_step_id=placeholder_step_id,
                cleanup_mode=cleanup_mode,
            )

        params = _build_create_params(
            mode=mode_upper,
            message=message,
            tool_name=tool_name,
            schema=parsed_schema,
            url=url,
            chat_id=chat_id,
            message_id=effective_message_id,
            expires_in_seconds=expires_in_seconds,
            external_elicitation_id=external_elicitation_id,
            metadata=user_metadata,
        )

        try:
            elicitation = unique_sdk.Elicitation.create_elicitation(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                **params,
            )
        except unique_sdk.APIError:
            # Creation failed after we materialised a placeholder; tear it
            # down so the chat doesn't keep spinning forever.
            if placeholder_message_id and placeholder_step_id and chat_id:
                _cleanup_visibility_context(
                    state,
                    chat_id=chat_id,
                    placeholder_message_id=placeholder_message_id,
                    placeholder_step_id=placeholder_step_id,
                    cleanup_mode=cleanup_mode,
                    terminal_status=None,
                )
            raise

        suffix = ""
        if placeholder_message_id:
            suffix = (
                "\n\nNote: a placeholder assistant message was created to make "
                "the elicitation visible in the chat UI. It will be "
                f"{'deleted' if cleanup_mode == 'delete' else 'collapsed'} "
                "automatically when you call `elicit wait` or when the user "
                "responds via `elicit respond`."
            )
        return (
            f"Created elicitation {elicitation.get('id', '?')}\n\n"
            f"{format_elicitation(elicitation)}{suffix}"
        )
    except (ValueError, unique_sdk.APIError) as exc:
        return f"elicit: {exc}"


def cmd_elicit_pending(state: ShellState) -> str:
    """List all pending elicitation requests for the current user.

    The backend ``GET /elicitation/pending`` endpoint returns a raw JSON array
    of elicitations. Older SDKs (and some intermediate proxies) wrap the
    payload in ``{"elicitations": [...]}``; both shapes are handled here so
    the command stays compatible across platform versions.
    """
    try:
        # The SDK typing claims ``Elicitations`` (a dict with an
        # ``elicitations`` key), but the backend actually returns a raw JSON
        # array of elicitations. Cast to ``Any`` so the runtime checks below
        # compile without an "unnecessary isinstance" warning.
        response = cast(
            Any,
            unique_sdk.Elicitation.get_pending_elicitations(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
            ),
        )
        if isinstance(response, list):
            elicitations = response
        elif isinstance(response, dict):
            elicitations = response.get("elicitations", []) or []
        else:
            elicitations = []
        return format_pending_elicitations(elicitations)
    except unique_sdk.APIError as exc:
        return f"elicit: {exc}"


def cmd_elicit_get(state: ShellState, elicitation_id: str) -> str:
    """Fetch an elicitation by ID and show its details."""
    try:
        elicitation = unique_sdk.Elicitation.get_elicitation(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            elicitation_id=elicitation_id,
        )
        return format_elicitation(elicitation)
    except unique_sdk.APIError as exc:
        return f"elicit: {exc}"


def cmd_elicit_respond(
    state: ShellState,
    elicitation_id: str,
    *,
    action: str,
    content: str | None = None,
) -> str:
    """Respond to an elicitation on behalf of the user.

    Typically the *user* responds via the Unique UI; this command is primarily
    useful for scripted workflows, tests, or declining / cancelling requests
    on their behalf.

    If the elicitation was created with the visibility workaround (see
    ``cmd_elicit_create``), the placeholder message + step are cleaned up
    after the backend accepts the response so the chat doesn't keep
    spinning in a fake thinking state.
    """
    try:
        action_upper = action.upper()
        if action_upper not in ("ACCEPT", "DECLINE", "CANCEL", "REJECT"):
            return (
                f"elicit: invalid action '{action}' "
                "(expected ACCEPT, DECLINE, CANCEL, or REJECT)"
            )

        parsed_content = _parse_json_arg(content, field="--content")
        if action_upper == "ACCEPT" and parsed_content is None:
            return "elicit: --content (JSON object) is required for ACCEPT"

        params: dict[str, Any] = {
            "elicitationId": elicitation_id,
            "action": action_upper,
        }
        if parsed_content is not None:
            params["content"] = parsed_content

        result = unique_sdk.Elicitation.respond_to_elicitation(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            **params,
        )

        # If the elicitation was created with the visibility workaround,
        # fetch it once to read the placeholder ids out of its metadata
        # and tear the placeholder down. Best-effort — never lets a
        # cleanup failure hide a successful response.
        try:
            elicitation = unique_sdk.Elicitation.get_elicitation(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                elicitation_id=elicitation_id,
            )
        except unique_sdk.APIError:
            elicitation = None
        ctx = _extract_visibility_context(dict(elicitation) if elicitation else None)
        if ctx is not None:
            vis_chat_id, placeholder_id, step_id, cleanup_mode = ctx
            _cleanup_visibility_context(
                state,
                chat_id=vis_chat_id,
                placeholder_message_id=placeholder_id,
                placeholder_step_id=step_id,
                cleanup_mode=cleanup_mode,
                terminal_status=action_upper,
            )

        return format_elicitation_response(result, elicitation_id, action_upper)
    except (ValueError, unique_sdk.APIError) as exc:
        return f"elicit: {exc}"


def cmd_elicit_wait(
    state: ShellState,
    elicitation_id: str,
    *,
    timeout: int = DEFAULT_WAIT_TIMEOUT_SECONDS,
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
) -> str:
    """Block until an elicitation transitions to a terminal state.

    Polls ``get_elicitation`` at ``poll_interval`` intervals and returns the
    formatted elicitation once its ``status`` is terminal (RESPONDED /
    ACCEPTED / REJECTED / DECLINED / CANCELLED / EXPIRED / COMPLETED), or
    when ``timeout`` seconds elapse.

    If the elicitation carries the SDK's visibility markers (see the
    "Visibility workaround for UN-19815" note at the top of this module),
    the synthetic placeholder message + step are cleaned up in a ``finally``
    once the wait returns — regardless of whether it terminated normally,
    timed out, or the backend started returning errors mid-poll. Cleanup
    is best-effort and silent.
    """
    last: dict[str, Any] | None = None
    terminal_status: str | None = None
    try:
        deadline = time.monotonic() + max(1, timeout)
        while True:
            elicitation = unique_sdk.Elicitation.get_elicitation(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                elicitation_id=elicitation_id,
            )
            last = dict(elicitation)
            status = str(elicitation.get("status", "")).upper()
            if status in TERMINAL_STATUSES:
                terminal_status = status
                return format_elicitation(elicitation)
            if time.monotonic() >= deadline:
                return (
                    f"elicit: timed out after {timeout}s waiting for "
                    f"{elicitation_id} (last status: {status or 'UNKNOWN'})\n\n"
                    f"{format_elicitation(last)}"
                )
            time.sleep(poll_interval)
    except unique_sdk.APIError as exc:
        return f"elicit: {exc}"
    finally:
        ctx = _extract_visibility_context(last)
        if ctx is not None:
            vis_chat_id, placeholder_id, step_id, cleanup_mode = ctx
            _cleanup_visibility_context(
                state,
                chat_id=vis_chat_id,
                placeholder_message_id=placeholder_id,
                placeholder_step_id=step_id,
                cleanup_mode=cleanup_mode,
                terminal_status=terminal_status,
            )


def cmd_elicit_ask(
    state: ShellState,
    *,
    message: str,
    tool_name: str = "agent_question",
    schema: str | None = None,
    chat_id: str | None = None,
    message_id: str | None = None,
    expires_in_seconds: int | None = None,
    timeout: int = DEFAULT_WAIT_TIMEOUT_SECONDS,
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    metadata: list[tuple[str, str]] | None = None,
    visible: bool = True,
    assistant_id: str | None = None,
    placeholder_text: str = DEFAULT_PLACEHOLDER_TEXT,
    cleanup_mode: CleanupMode = DEFAULT_CLEANUP_MODE,
) -> str:
    """Create a FORM elicitation and wait for the user's reply.

    When no ``--schema`` is passed, a minimal single-field form asking for a
    free-text ``answer`` is used. This is the preferred entry point when an
    agent needs to ask the user a clarifying question.

    When ``chat_id`` is set and ``visible`` is ``True`` (the default), the
    elicitation is wrapped in a placeholder thinking timeline so the chat UI
    actually renders it — see the "Visibility workaround for UN-19815" note
    at the top of this module. The placeholder is collapsed or deleted
    automatically after the user responds. Pass ``visible=False`` to skip
    this and emit a bare elicitation.
    """
    try:
        parsed_schema = _parse_json_arg(schema, field="--schema")
        if parsed_schema is None:
            parsed_schema = {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "Free-text answer to the question.",
                    },
                },
                "required": ["answer"],
            }

        user_metadata = _parse_metadata_pairs(metadata)
        effective_message_id = message_id
        placeholder_message_id: str | None = None
        placeholder_step_id: str | None = None

        if visible and chat_id and not message_id:
            resolved_assistant = assistant_id or _resolve_assistant_id(state, chat_id)
            if not resolved_assistant:
                return (
                    "elicit: cannot ask a visible question without an assistant "
                    "id; pass --assistant-id or set UNIQUE_ASSISTANT_ID, or "
                    "pass --no-visible to skip the visibility workaround"
                )
            placeholder_message_id, placeholder_step_id = _create_visibility_context(
                state,
                chat_id=chat_id,
                assistant_id=resolved_assistant,
                placeholder_text=placeholder_text,
            )
            effective_message_id = placeholder_message_id
            user_metadata = _merge_visibility_metadata(
                user_metadata,
                chat_id=chat_id,
                placeholder_message_id=placeholder_message_id,
                placeholder_step_id=placeholder_step_id,
                cleanup_mode=cleanup_mode,
            )

        def _cleanup_placeholder_if_needed() -> None:
            if placeholder_message_id and placeholder_step_id and chat_id:
                _cleanup_visibility_context(
                    state,
                    chat_id=chat_id,
                    placeholder_message_id=placeholder_message_id,
                    placeholder_step_id=placeholder_step_id,
                    cleanup_mode=cleanup_mode,
                    terminal_status=None,
                )

        params = _build_create_params(
            mode="FORM",
            message=message,
            tool_name=tool_name,
            schema=parsed_schema,
            url=None,
            chat_id=chat_id,
            message_id=effective_message_id,
            expires_in_seconds=expires_in_seconds,
            external_elicitation_id=None,
            metadata=user_metadata,
        )

        try:
            elicitation = unique_sdk.Elicitation.create_elicitation(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                **params,
            )
        except unique_sdk.APIError:
            _cleanup_placeholder_if_needed()
            raise

        elicitation_id = elicitation.get("id")
        if not elicitation_id:
            _cleanup_placeholder_if_needed()
            return "elicit: platform did not return an elicitation id"

        # ``cmd_elicit_wait`` handles its own placeholder teardown by
        # reading the markers back from the elicitation's metadata.
        return cmd_elicit_wait(
            state,
            elicitation_id,
            timeout=timeout,
            poll_interval=poll_interval,
        )
    except (ValueError, unique_sdk.APIError) as exc:
        return f"elicit: {exc}"
