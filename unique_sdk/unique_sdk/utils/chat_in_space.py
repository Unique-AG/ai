import asyncio
from typing import List

from unique_sdk.api_resources._content import Content
from unique_sdk.api_resources._space import Space
from unique_sdk.utils.file_io import upload_file


async def send_message_and_wait_for_completion(
    user_id: str,
    company_id: str,
    assistant_id: str,
    text: str,
    tool_choices: List[str] = None,
    scope_rules: dict | None = None,
    chat_id: str = None,
    poll_interval: float = 1.0,
    max_wait: float = 60.0,
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

    max_attempts = int(max_wait // poll_interval)
    for _ in range(max_attempts):
        answer = Space.get_latest_message(user_id, company_id, chat_id)
        if answer.get("stoppedStreamingAt") is not None:
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

        await wait_for_ingestion_completion(
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
        if chat_id:
            Space.delete_chat(
                user_id=user_id,
                company_id=company_id,
                chat_id=chat_id,
            )


async def wait_for_ingestion_completion(
    user_id: str,
    company_id: str,
    content_id: str,
    chat_id: str = None,
    poll_interval: float = 1.0,
    max_wait: float = 60.0,
):
    """
    Polls until the content ingestion is finished or the maximum wait time is reached and throws in case ingestion fails. The function assumes that the content exists.
    """
    max_attempts = int(max_wait // poll_interval)
    for _ in range(max_attempts):
        searched_content = Content.search(
            user_id=user_id,
            company_id=company_id,
            where={"id": {"equals": content_id}},
            chatId=chat_id,
            includeFailedContent=True,
        )
        if searched_content:
            ingestion_state = searched_content[0].get("ingestionState")
            if ingestion_state == "FINISHED":
                return ingestion_state
            if isinstance(ingestion_state, str) and ingestion_state.startswith(
                "FAILED"
            ):
                raise RuntimeError(f"Ingestion failed with state: {ingestion_state}")
        await asyncio.sleep(poll_interval)
    raise TimeoutError("Timed out waiting for file ingestion to finish.")
