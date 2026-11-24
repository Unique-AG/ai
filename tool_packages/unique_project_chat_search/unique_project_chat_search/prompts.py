"""Default prompt texts of the ProjectChatSearch tool."""

TOOL_DESCRIPTION = (
    "Search and read the user's earlier chats in this project. Use it when the "
    "user refers to something discussed before, asks what they worked on, or "
    "when earlier chats in this project could hold the answer.\n"
    "Pick a `mode`:\n"
    '- search: find passages. Example: {"mode": "search", "query": "Q3 budget decision"}\n'
    '- read: read one earlier chat in order. Example: {"mode": "read", "chat_id": "chat_abc"}\n'
    '- recent: list the earlier chats, newest first. Example: {"mode": "recent"}\n'
    "Optional: `after` / `before` (YYYY-MM-DD) for search and recent, "
    "`chat_id` with search to stay inside one chat, `page` for read and recent."
)

SYSTEM_PROMPT = (
    "ProjectChatSearch gives access to the user's own earlier chats in this "
    "project. The current chat is never part of its results.\n"
    "- When the user refers to an earlier discussion, decision or result, "
    "search the earlier chats before answering.\n"
    "- Results are sources like any other: cite them with [n] and say which "
    "chat the information comes from.\n"
    "- A 'recent' listing only shows chat titles and dates. Read a chat "
    "(mode=read) before quoting what was said in it."
)
