from typing import List, Tuple

import regex as re

import unique_sdk
from unique_sdk.utils.token import count_tokens

SYSTEM_MESSAGE_PREFIX = "[SYSTEM] "


def load_history(
    userId, companyId, chatId, maxTokens, percentOfMaxTokens=0.15, maxMessages=4
):
    def get_chat_history(userId, companyId, chatId):
        messages = unique_sdk.Message.list(
            user_id=userId,
            company_id=companyId,
            chatId=chatId,
        )

        messages = messages["data"][:-2]
        filteredMessages = []
        for message in messages:
            if message["text"] is None:
                continue
            elif SYSTEM_MESSAGE_PREFIX in message["text"]:
                continue
            else:
                filteredMessages.append(message)
        return filteredMessages

    def get_context_from_history(fullHistory, maxTokens, maxMessages=4):
        messages = fullHistory[-maxMessages:]
        filtered_messages = [m for m in messages if m["text"]]
        mapped_messages = []

        for m in filtered_messages:
            text = re.sub(r"<sup>\d+</sup>", "", m["text"])
            role = "assistant" if m["role"].lower() == "assistant" else "user"
            mapped_messages.append({"role": role, "content": text})

        return pick_messages_in_reverse_for_token_window(mapped_messages, maxTokens)

    def pick_messages_in_reverse_for_token_window(messages, limit):
        if len(messages) < 1 or limit < 1:
            return []

        last_index = len(messages) - 1
        token_count = count_tokens(messages[last_index]["content"])
        while token_count > limit:
            print(
                f"Limit too low for the initial message. Last message TokenCount {token_count} available tokens {limit} - cutting message in half until it fits"
            )
            content = messages[last_index]["content"]
            messages[last_index]["content"] = content[: len(content) // 2] + "..."
            token_count = count_tokens(messages[last_index]["content"])

        while token_count <= limit and last_index > 0:
            token_count = count_tokens(
                "".join([msg["content"] for msg in messages[:last_index]])
            )
            if token_count <= limit:
                last_index -= 1

        last_index = max(0, last_index)
        return messages[last_index:]

    fullHistory = get_chat_history(userId, companyId, chatId)
    selectedHistory = get_context_from_history(
        fullHistory, int(round(maxTokens * percentOfMaxTokens)), maxMessages
    )

    return fullHistory, selectedHistory


def convert_chat_history_to_injectable_string(history) -> Tuple[List[str], int]:
    chatHistory = []
    for msg in history:
        if msg["role"].lower() == "assistant":
            chatHistory.append(f"previous_answer: {msg['content']}")
        else:
            chatHistory.append(f"previous_question: {msg['content']}")
    chatContext = "\n".join(chatHistory)
    chatContextTokenLength = count_tokens(chatContext)
    return chatHistory, chatContextTokenLength
