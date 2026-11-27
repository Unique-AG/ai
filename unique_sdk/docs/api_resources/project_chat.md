# Project Chat API

The Project Chat API searches and reads the earlier chats of a project that belongs to the calling user.

## Overview

A project groups a user's chats in a space. Each chat of a project is indexed in chunks of consecutive question and answer pairs. Three calls work on that index:

- `search` - the chunks that best match a query, with highlights
- `list_chunks` - the chunks of one chat in order, one page at a time
- `list_recent` - the chats of the project, most recently active first

The Projects feature must be enabled for the company; otherwise every call gets `403 Forbidden` (`PermissionError`). Only the project's owner can call them; any other caller, or a project that does not exist, gets `404 Not Found` (`InvalidRequestError`). While project chat indexing is off for the company, `search` returns an empty list.

Arguments left as `None` are not sent, so the endpoint applies its defaults. Times can be timezone-aware `datetime` objects or ISO 8601 strings.

## Methods

??? example "`unique_sdk.ProjectChat.search` - Search the chats of a project"

    Return the chunks of the project's chats that best match a query.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `project_id` (str, required) - Project to search
    - `query` (str, required) - What to look for, at most 2000 characters
    - `chat_ids` (list[str], optional) - Only search these chats, at most 200
    - `exclude_chat_ids` (list[str], optional) - Leave out these chats, at most 200, for example the current one
    - `created_after` (datetime | str, optional) - Only chunks whose first message is at or after this time
    - `created_before` (datetime | str, optional) - Only chunks whose first message is at or before this time
    - `limit` (int, optional) - Number of chunks, 1 to 50. Default 20
    - `include_chat_stats` (bool, optional) - Also return chunk and token totals of the chats in the result

    **Returns:**

    Returns a [`ChunkList`](#chunklist). Each chunk has `score` and `highlights` set. `nextCursor` is always `None`.

    **Example:**

    ```python
    result = unique_sdk.ProjectChat.search(
        user_id=user_id,
        company_id=company_id,
        project_id=project_id,
        query="What did we decide about the Q3 budget?",
        exclude_chat_ids=[current_chat_id],
        limit=10,
    )

    for chunk in result["data"]:
        print(chunk.chatTitle, chunk.score, chunk.highlights)
    ```

??? example "`unique_sdk.ProjectChat.list_chunks` - Read one chat in order"

    Return the chunks of one chat of the project in order, one page at a time.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `project_id` (str, required) - Project of the chat
    - `chat_id` (str, required) - Chat to read
    - `limit` (int, optional) - Number of chunks per page, 1 to 50. Default 20
    - `after` (str, optional) - `nextCursor` of the previous page
    - `include_chat_stats` (bool, optional) - Also return the chunk and token totals of the chat

    **Returns:**

    Returns a [`ChunkList`](#chunklist) ordered by `chunkIndex`. `score` and `highlights` are `None`.

    **Example - Read a whole chat:**

    ```python
    chunks = []
    after = None
    while True:
        page = unique_sdk.ProjectChat.list_chunks(
            user_id=user_id,
            company_id=company_id,
            project_id=project_id,
            chat_id=chat_id,
            after=after,
        )
        chunks.extend(page["data"])
        after = page["nextCursor"]
        if after is None:
            break
    ```

??? example "`unique_sdk.ProjectChat.list_recent` - List recent chats"

    Return one entry per chat of the project, most recently active first.

    **Parameters:**

    - `user_id` (str, required) - User identifier
    - `company_id` (str, required) - Company identifier
    - `project_id` (str, required) - Project to list
    - `exclude_chat_ids` (list[str], optional) - Leave out these chats, at most 200
    - `updated_after` (datetime | str, optional) - Only chats active at or after this time
    - `updated_before` (datetime | str, optional) - Only chats last active at or before this time
    - `limit` (int, optional) - Number of chats per page, 1 to 20. Default 20
    - `after` (str, optional) - `nextCursor` of the previous page

    **Returns:**

    Returns a [`ChatList`](#chatlist).

    **Example:**

    ```python
    recent = unique_sdk.ProjectChat.list_recent(
        user_id=user_id,
        company_id=company_id,
        project_id=project_id,
        exclude_chat_ids=[current_chat_id],
        limit=5,
    )

    for chat in recent["data"]:
        print(chat.chatTitle, chat.updatedAt)
    ```

## Async Methods

All methods have async variants with an `_async` suffix:

- `search_async`
- `list_chunks_async`
- `list_recent_async`

```python
result = await unique_sdk.ProjectChat.search_async(
    user_id=user_id,
    company_id=company_id,
    project_id=project_id,
    query="Q3 budget",
)
```

## Return Types

#### ChunkList {#chunklist}

??? note "A page of chunks, returned by `search` and `list_chunks`"

    **Fields:**

    - `object` (Literal["list"]) - Object type identifier
    - `data` (list[[`ProjectChatChunk`](#projectchatchunk)]) - The chunks
    - `chatStats` (list[ChatStats]) - `chatId`, `chunkCount` and `tokenCount` per chat. Empty unless `include_chat_stats` is set
    - `nextCursor` (str | None) - Pass as `after` to get the next page. `None` on the last page and always for search

#### ProjectChatChunk {#projectchatchunk}

??? note "A chunk of consecutive question and answer pairs of one chat"

    **Fields:**

    - `chatId` (str) - Chat the chunk belongs to
    - `chatTitle` (str | None) - Title of the chat
    - `chunkIndex` (int) - Position of the chunk in its chat, from 0
    - `pairIndexStart` (int) - First question and answer pair in the chunk, from 1
    - `pairIndexEnd` (int) - Last question and answer pair in the chunk
    - `messageIds` (list[str]) - Messages in the chunk
    - `text` (str) - Text of the chunk
    - `tokenCount` (int) - Number of tokens in `text`
    - `isOpen` (bool) - `True` for the last chunk of the chat
    - `createdAt` (str) - Time of the first message in the chunk, ISO 8601
    - `updatedAt` (str) - Time of the last message in the chunk, ISO 8601
    - `score` (float | None) - Relevance score, search only
    - `highlights` (list[str] | None) - Highlighted passages, search only
    - `object` (Literal["search.project-chat-chunk"]) - Object type identifier

#### ChatList {#chatlist}

??? note "A page of chats, returned by `list_recent`"

    **Fields:**

    - `object` (Literal["list"]) - Object type identifier
    - `data` (list[[`ProjectChat`](#projectchat)]) - The chats, most recently active first
    - `nextCursor` (str | None) - Pass as `after` to get the next page. `None` on the last page

#### ProjectChat {#projectchat}

??? note "One chat of a project"

    **Fields:**

    - `chatId` (str) - Chat identifier
    - `chatTitle` (str | None) - Title of the chat
    - `chatCreatedAt` (str) - Creation time of the chat, ISO 8601
    - `updatedAt` (str) - Time of the last message, ISO 8601
    - `chunkCount` (int) - Number of indexed chunks in the chat
    - `object` (Literal["search.project-chat"]) - Object type identifier

## Related Resources

- [Project Memory API](project_memory.md) - Per-project memory of a user's project chats
- [Search API](search.md) - Search the knowledge base
