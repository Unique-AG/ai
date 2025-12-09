import asyncio
import warnings
from typing import List, Literal

from unique_sdk.api_resources._message import Message
from unique_sdk.api_resources._space import Space
from unique_sdk.utils.file_io import upload_file
from unique_sdk.utils.file_io import (
    wait_for_ingestion_completion as _wait_for_ingestion_completion,
)


async def send_message_and_wait_for_completion(
    user_id: str,
    company_id: str,
    assistant_id: str,
    text: str,
    tool_choices: List[str] | None = None,
    scope_rules: dict | None = None,
    chat_id: str | None = None,
    poll_interval: float = 1.0,
    max_wait: float = 60.0,
    stop_condition: Literal["stoppedStreamingAt", "completedAt"] = "stoppedStreamingAt",
) -> "Space.Message":
    """
    Sends a prompt asynchronously and polls for completion. (until stoppedStreamingAt is not None)

    Args:
        user_id: The user ID.
        company_id: The company ID.
        assistant_id: The assistant ID.
        text: The prompt text.
        poll_interval: Seconds between polls.
        max_wait: Maximum seconds to wait for completion.
        stop_condition: Defines when to expect a response back, when the assistant stop streaming or when it completes the message. (default: "stoppedStreamingAt")
        **kwargs: Additional parameters for the prompt.

    Returns:
        The completed Space.Message.
    """
    response = await Space.create_message_async(
        user_id=user_id,
        company_id=company_id,
        assistantId=assistant_id,
        chatId=chat_id,
        text=text,
        toolChoices=tool_choices,
        scopeRules=scope_rules,
    )
    chat_id = response.get("chatId")
    message_id = response.get("id")

    max_attempts = int(max_wait // poll_interval)
    for _ in range(max_attempts):
        answer = await Space.get_latest_message_async(user_id, company_id, chat_id)
        if answer.get(stop_condition) is not None:
            try:
                user_message = await Message.retrieve_async(
                    user_id, company_id, message_id, chatId=chat_id
                )
                debug_info = user_message.get("debugInfo")
                answer["debugInfo"] = debug_info
            except Exception as e:
                print(f"Failed to load debug info from user message: {e}")

            return answer
        await asyncio.sleep(poll_interval)

    raise TimeoutError("Timed out waiting for prompt completion.")


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
) -> "Space.Message":
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
