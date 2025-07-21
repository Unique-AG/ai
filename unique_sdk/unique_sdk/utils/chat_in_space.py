import asyncio
from typing import List

from unique_sdk.api_resources._space import Space


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
    # Send the prompt asynchronously
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
        # Poll for the answer
        answer = Space.get_latest_message(user_id, company_id, chat_id)
        if answer.get("stoppedStreamingAt") is not None:
            return answer
        await asyncio.sleep(poll_interval)

    raise TimeoutError("Timed out waiting for prompt completion.")
