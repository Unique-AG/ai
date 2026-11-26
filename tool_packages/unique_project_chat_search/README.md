# unique_project_chat_search

The `ProjectChatSearch` tool lets Unique AI search and read the user's earlier chats in the current project.

It needs a chat event that carries a `project_id` (a project chat while Projects is enabled). It is meant to be added by the orchestrator only for such events, not configured per space, so it does not appear in the UI; that wiring lands in a follow-up PR.

## Input

One flat schema; `mode` picks what the tool does:

| `mode` | Needs | Does |
|---|---|---|
| `search` | `query` (and optionally `chat_id`) | Best-matching excerpts across the project's other chats, or inside one chat |
| `read` | `chat_id` | That chat from the start, in order, one `page` at a time |
| `recent` | nothing | The project's other chats, most recently active first |

`after` / `before` (`YYYY-MM-DD`) limit search and recent to activity in that window. `page` (from 1) pages read and recent.

## Output

The same sources as InternalSearch and WebSearch: one `ContentChunk` per excerpt (or per listed chat), in the knowledge-base chunk layout (`<|document|>` and `<|info|>` sections, then the text). The model cites them with `[n]`; each reference is named `Chat: "<title>"` and links to the chat (`chat_url_template`, default `/chat/{chat_id}`).

A `page` of read and recent holds as many results as fit in `max_tokens` (at most `chunks_per_page` / `recent_limit`), so the next page continues exactly where it stopped. The next-page hint, and for search the number of excerpts left out for the token budget, come back in the response's `system_reminder`.
