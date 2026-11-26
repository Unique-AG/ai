from __future__ import annotations

import asyncio
import logging
import warnings
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Literal

from unique_sdk.api_resources._message import Message
from unique_sdk.api_resources._space import Space
from unique_sdk.utils.file_io import upload_file
from unique_sdk.utils.file_io import (
    wait_for_ingestion_completion as _wait_for_ingestion_completion,
)

_log = logging.getLogger(__name__)

_ABANDON_STOP_TIMEOUT_S = 5.0

# asyncio holds tasks weakly. A stop that outlives its cancelled caller needs a
# strong reference until it finishes.
_abandon_stops: set[asyncio.Task[bool]] = set()


class MessageWaitTimeoutError(TimeoutError):
    """The assistant turn did not finish within ``max_wait``.

    ``turn_stopped`` is False when no stop was requested or the stop failed.
    """

    def __init__(self, *, chat_id: str, message_id: str, turn_stopped: bool) -> None:
        super().__init__("Timed out waiting for prompt completion.")
        self.chat_id = chat_id
        self.message_id = message_id
        self.turn_stopped = turn_stopped


class MessageWaitInterruptedError(Exception):
    """``interrupt`` ended the wait. The assistant turn keeps running."""

    def __init__(self, *, chat_id: str, message_id: str) -> None:
        super().__init__("The wait for prompt completion was interrupted.")
        self.chat_id = chat_id
        self.message_id = message_id


def get_message_invocations(message: Space.Message) -> list[dict[str, Any]]:
    """Per-LLM-invocation stats for a completed Space message, read from
    `debugInfo.llm_invocations` (a plain list, one entry per LLM call).

    Each entry has `modelName`, `tokenUsage`, and `source` keys.
    """
    debug_info = message.get("debugInfo") or {}
    llm_invocations = debug_info.get("llm_invocations")
    return llm_invocations if isinstance(llm_invocations, list) else []


async def send_message_and_wait_for_completion(
    user_id: str,
    company_id: str,
    assistant_id: str,
    text: str,
    tool_choices: list[str] | None = None,
    skill_choices: Sequence[Space.SkillChoice] = (),
    scope_rules: dict[str, Any] | None = None,
    chat_id: str | None = None,
    poll_interval: float = 1.0,
    max_wait: float = 60.0,
    stop_condition: Literal["stoppedStreamingAt", "completedAt"] = "stoppedStreamingAt",
    correlation: Space.Correlation | None = None,
    auto_approve_elicitation: bool | None = None,
    language_model: str | None = None,
    on_message_update: Callable[[Space.Message], Awaitable[None]] | None = None,
    wait_for_invocations: bool = False,
    stop_on_abandon: bool = False,
    on_message_created: Callable[[Space.Message], Awaitable[None]] | None = None,
    interrupt: Callable[[], Awaitable[bool]] | None = None,
) -> Space.Message:
    """
    Sends a prompt asynchronously and polls for completion. (until stoppedStreamingAt is not None)

    Args:
        user_id: The user ID.
        company_id: The company ID.
        assistant_id: The assistant ID.
        text: The prompt text.
        tool_choices: List of tool names to use.
        skill_choices: Sequence of selected skill objects to use.
        scope_rules: Scope rules for filtering content.
        chat_id: Optional chat ID to continue an existing chat.
        poll_interval: Seconds between polls.
        max_wait: Maximum seconds to wait for completion.
        stop_condition: Defines when to expect a response back, when the assistant stop streaming or when it completes the message. (default: "stoppedStreamingAt")
            Note: `debugInfo.llm_invocations` (see `get_message_invocations`) is written
            near the very end of the orchestrator's run -- after postprocessors and
            evaluations, which happen after the visible text stream ends. With the default
            `"stoppedStreamingAt"`, or even `"completedAt"` (set slightly before the debugInfo
            write completes), the returned message's invocations can still be incomplete
            immediately after this function returns. Re-fetch the message after a short delay
            if you need the full invocation list.
        correlation: Optional correlation data to link this message to a parent message in another chat.
            Should contain: parentMessageId, parentChatId, parentAssistantId.
        auto_approve_elicitation: When True, automatically approves elicitation requests during
            the assistant run. Use for non-interactive automation where no user is present.
        language_model: Optional language model group name to answer this single message
            with (e.g. ``"AZURE_GPT_4o_2024_1120"`` or ``"litellm:gemini-2-5-pro"``).
            Forwarded to Unique API as ``languageModel``. Requires access to use the space,
            ``allowModelSwitching`` enabled on it, and a model from its
            ``switchableLanguageModels``. When omitted, the space default is used.
        on_message_update: Optional async callback called whenever the latest assistant
            message changes while waiting for completion.
        wait_for_invocations: When True, briefly wait for the orchestrator's final
            ``debugInfo.llm_invocations`` write after the visible response completes.
        stop_on_abandon: When True, stop the assistant turn if the wait ends without
            an answer. See ``wait_for_message_completion``.
        on_message_created: Optional async callback called once with the posted USER
            message, before the wait starts. Its ``chatId`` and ``id`` identify the
            turn, for example to stop it with ``Message.stop_async``.
        interrupt: See ``wait_for_message_completion``.

    Returns:
        The completed Space.Message.

    Raises:
        MessageWaitTimeoutError: The turn did not finish within ``max_wait``.
        MessageWaitInterruptedError: ``interrupt`` ended the wait.
    """
    create_message_params: Space.CreateMessageParams = {
        "assistantId": assistant_id,
        "text": text,
        "toolChoices": tool_choices,
        "skillChoices": list(skill_choices),
        "scopeRules": scope_rules,
        "correlation": correlation,
    }
    if chat_id is not None:
        create_message_params["chatId"] = chat_id
    if auto_approve_elicitation is not None:
        create_message_params["autoApproveElicitation"] = auto_approve_elicitation
    if language_model is not None:
        create_message_params["languageModel"] = language_model

    response = await Space.create_message_async(
        user_id=user_id,
        company_id=company_id,
        **create_message_params,
    )
    if on_message_created is not None:
        try:
            await on_message_created(response)
        except BaseException:
            if stop_on_abandon:
                _ = await _stop_turn_despite_cancellation(
                    user_id=user_id,
                    company_id=company_id,
                    chat_id=response["chatId"],
                    message_id=response["id"],
                )
            raise
    return await wait_for_message_completion(
        user_id=user_id,
        company_id=company_id,
        chat_id=response["chatId"],
        message_id=response["id"],
        poll_interval=poll_interval,
        max_wait=max_wait,
        stop_condition=stop_condition,
        on_message_update=on_message_update,
        wait_for_invocations=wait_for_invocations,
        stop_on_abandon=stop_on_abandon,
        interrupt=interrupt,
    )


async def wait_for_message_completion(
    user_id: str,
    company_id: str,
    chat_id: str,
    message_id: str,
    poll_interval: float = 1.0,
    max_wait: float = 60.0,
    stop_condition: Literal["stoppedStreamingAt", "completedAt"] = "stoppedStreamingAt",
    on_message_update: Callable[[Space.Message], Awaitable[None]] | None = None,
    wait_for_invocations: bool = False,
    stop_on_abandon: bool = False,
    interrupt: Callable[[], Awaitable[bool]] | None = None,
) -> Space.Message:
    """
    Polls a chat until the assistant turn started by an already posted message finishes.

    Args:
        user_id: The user ID.
        company_id: The company ID.
        chat_id: The chat the message was posted to.
        message_id: The ID of the posted USER message that started the turn.
        poll_interval: Seconds between polls.
        max_wait: Maximum seconds to wait for completion.
        stop_condition: See ``send_message_and_wait_for_completion``.
        on_message_update: See ``send_message_and_wait_for_completion``.
        wait_for_invocations: See ``send_message_and_wait_for_completion``.
        stop_on_abandon: When True, stop the assistant turn if this wait ends without
            an answer: at ``max_wait``, on cancellation, or on an error.
        interrupt: Optional async check that runs after every poll that found no
            answer. When it returns True the wait ends with
            ``MessageWaitInterruptedError``. The turn is not stopped, even with
            ``stop_on_abandon``. Wait for the same message again to resume.

    Returns:
        The completed Space.Message.

    Raises:
        MessageWaitTimeoutError: The turn did not finish within ``max_wait``. It is a
            ``TimeoutError`` and says whether the turn was stopped.
        MessageWaitInterruptedError: ``interrupt`` ended the wait.
    """
    try:
        answer = await _poll_for_completion(
            user_id=user_id,
            company_id=company_id,
            chat_id=chat_id,
            message_id=message_id,
            poll_interval=poll_interval,
            max_wait=max_wait,
            stop_condition=stop_condition,
            on_message_update=on_message_update,
            wait_for_invocations=wait_for_invocations,
            interrupt=interrupt,
        )
    except MessageWaitInterruptedError:
        raise
    except BaseException:
        if stop_on_abandon:
            _ = await _stop_turn_despite_cancellation(
                user_id=user_id,
                company_id=company_id,
                chat_id=chat_id,
                message_id=message_id,
            )
        raise
    if answer is not None:
        return answer

    turn_stopped = stop_on_abandon and await _stop_turn_despite_cancellation(
        user_id=user_id,
        company_id=company_id,
        chat_id=chat_id,
        message_id=message_id,
    )
    raise MessageWaitTimeoutError(
        chat_id=chat_id, message_id=message_id, turn_stopped=turn_stopped
    )


async def _poll_for_completion(
    *,
    user_id: str,
    company_id: str,
    chat_id: str,
    message_id: str,
    poll_interval: float,
    max_wait: float,
    stop_condition: Literal["stoppedStreamingAt", "completedAt"],
    on_message_update: Callable[[Space.Message], Awaitable[None]] | None,
    wait_for_invocations: bool,
    interrupt: Callable[[], Awaitable[bool]] | None,
) -> Space.Message | None:
    """Return the finished message, or None when ``max_wait`` ran out."""
    max_attempts = int(max_wait // poll_interval)
    # The final up-to-3 polls spent waiting for `llm_invocations_complete`
    # happen after the stop condition is already met, so they must not eat
    # into the same budget as the wait for the stop condition itself --
    # otherwise a response that completes near the max_wait deadline would
    # spuriously time out while only debugInfo bookkeeping is still pending.
    if wait_for_invocations:
        max_attempts += 3
    last_update_signature: tuple[str | None, str | None] | None = None
    invocation_wait_attempts = 0
    for _ in range(max_attempts):
        answer = await Space.get_latest_message_async(user_id, company_id, chat_id)
        if (
            on_message_update is not None
            and answer.get("role") == "ASSISTANT"
            and answer.get("text") is not None
        ):
            update_signature = (
                answer.get("id"),
                answer.get("text"),
            )
            if update_signature != last_update_signature:
                await on_message_update(answer)
                last_update_signature = update_signature
        if answer.get(stop_condition) is not None:
            try:
                # debugInfo/llm_invocations is written via update_debug_info_async(),
                # which always targets the original USER message, not the
                # assistant reply (assistant=False in
                # ChatService._construct_message_modify_params) — re-fetch by
                # `message_id`, not the polled assistant message's own id.
                user_message = await Message.retrieve_async(
                    user_id, company_id, message_id, chatId=chat_id
                )
                debug_info = user_message.get("debugInfo")
                answer["debugInfo"] = debug_info
                answer["triggeringUserMessageId"] = message_id
                if (
                    wait_for_invocations
                    and not (debug_info or {}).get("llm_invocations_complete", False)
                    and invocation_wait_attempts < 3
                ):
                    invocation_wait_attempts += 1
                    await asyncio.sleep(poll_interval)
                    continue
            except Exception as e:
                print(f"Failed to load debug info from user message: {e}")

            return answer
        if interrupt is not None and await interrupt():
            raise MessageWaitInterruptedError(chat_id=chat_id, message_id=message_id)
        await asyncio.sleep(poll_interval)

    return None


async def _stop_turn(
    *, user_id: str, company_id: str, chat_id: str, message_id: str
) -> bool:
    """Stop the turn. Return False when the stop failed or took too long."""
    try:
        async with asyncio.timeout(_ABANDON_STOP_TIMEOUT_S):
            await Message.stop_async(user_id, company_id, message_id, chatId=chat_id)
    except Exception as exc:
        _log.warning("Could not stop the abandoned turn: %s", type(exc).__name__)
        return False
    return True


async def _stop_turn_despite_cancellation(
    *, user_id: str, company_id: str, chat_id: str, message_id: str
) -> bool:
    """Stop the turn. Wait for the stop to settle, even when cancelled."""
    stop = asyncio.ensure_future(
        _stop_turn(
            user_id=user_id,
            company_id=company_id,
            chat_id=chat_id,
            message_id=message_id,
        )
    )
    _abandon_stops.add(stop)
    stop.add_done_callback(_abandon_stops.discard)
    cancelled = False
    while not stop.done():
        try:
            _ = await asyncio.shield(stop)
        except asyncio.CancelledError:
            cancelled = True
    if cancelled:
        raise asyncio.CancelledError
    return stop.result()


async def chat_against_file(
    user_id: str,
    company_id: str,
    assistant_id: str,
    path_to_file: str,
    displayed_filename: str,
    mime_type: str,
    text: str,
    poll_interval: float = 1.0,
    max_wait: float = 60.0,
    should_delete_chat: bool = True,
) -> Space.Message:
    """
    Chat against a file by uploading it, sending a message and waiting for a reply.
    Args:

        user_id: The user ID.
        company_id: The company ID.
        assistant_id: The assistant ID.
        path_to_file: Path to the PDF file to upload.
        displayed_filename: Name to display for the uploaded file.
        mime_type: MIME type of the file (e.g., "application/pdf").
        text: Text to send after uploading the file and chat against.
        poll_interval: Seconds between polls for file ingestion.
        max_wait: Maximum seconds to wait for the final response.

    Returns:
        The final message response.
    """
    chat_id = None

    try:
        response = await send_message_and_wait_for_completion(
            user_id=user_id,
            company_id=company_id,
            assistant_id=assistant_id,
            text="I'm going to upload a file for analysis.",
        )
        chat_id = response.get("chatId")

        upload_response = upload_file(
            userId=user_id,
            companyId=company_id,
            path_to_file=path_to_file,
            displayed_filename=displayed_filename,
            mime_type=mime_type,
            chat_id=chat_id,
        )
        content_id = upload_response.get("id")
        if content_id is None:  # guard: basedpyright needs None narrowing
            raise ValueError("upload response missing id")

        await _wait_for_ingestion_completion(
            user_id=user_id,
            company_id=company_id,
            content_id=content_id,
            chat_id=chat_id,
            poll_interval=poll_interval,
            max_wait=max_wait,
        )

        final_response = await send_message_and_wait_for_completion(
            user_id=user_id,
            company_id=company_id,
            assistant_id=assistant_id,
            text=text,
            chat_id=chat_id,
            poll_interval=poll_interval,
            max_wait=max_wait,
        )

        return final_response

    except Exception as err:
        print(f"Error during chat against file: {err}")
        raise
    finally:
        if chat_id and should_delete_chat:
            await Space.delete_chat_async(
                user_id=user_id,
                company_id=company_id,
                chat_id=chat_id,
            )


async def wait_for_ingestion_completion(
    user_id: str,
    company_id: str,
    content_id: str,
    chat_id: str | None = None,
    poll_interval: float = 1.0,
    max_wait: float = 60.0,
):
    """
    Polls until the content ingestion is finished or the maximum wait time is reached and throws in case ingestion fails. The function assumes that the content exists.

    .. deprecated::
        Use :func:`unique_sdk.utils.file_io.wait_for_ingestion_completion` instead.
    """
    warnings.warn(
        "unique_sdk.utils.chat_in_space.wait_for_ingestion_completion is deprecated. "
        "Use unique_sdk.utils.file_io.wait_for_ingestion_completion instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return await _wait_for_ingestion_completion(
        user_id=user_id,
        company_id=company_id,
        content_id=content_id,
        chat_id=chat_id,
        poll_interval=poll_interval,
        max_wait=max_wait,
    )
