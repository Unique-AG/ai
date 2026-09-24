# `_meta` convention

MCP `_meta` is an opaque reverse-DNS bag. Unique uses `unique.app/…` as a side channel so the LLM never invents tenant IDs, chat IDs, or admin config.

## Two directions

| Surface | Writer | Unique payload |
| ------- | ------ | -------------- |
| `tools/list` | Server | `config-schema`, `context-requirements`, icon, system-prompt, format-information |
| `tools/call` | Host | `config`, `auth/*`, `chat/*` |

Build list-time meta with `merge_tool_meta(base, *parts)` and pass it to `@tool(..., meta=_META)`.

## Advertise

```python
from unique_mcp import (
    ConfigSchemaMeta,
    ContextRequirements,
    MetaKeys,
    UniqueAIToolMeta,
    merge_tool_meta,
)

_META = merge_tool_meta(
    {"unique.app/icon": "search"},
    ContextRequirements(required=[MetaKeys.USER_ID, MetaKeys.COMPANY_ID]),
    ConfigSchemaMeta(MyConfig),  # every field needs a default
    UniqueAIToolMeta(
        tool_description_for_system_prompt="Choose this tool when …",
        tool_format_information_for_system_prompt="Cite with the markdown links returned.",
    ),
)
```

`ContextRequirements` is a **declaration** (Unique AI uses it to know what to forward). The server does not enforce it. Domain keys are allowed, e.g. `unique.app/search/content-ids` on `optional`.

`ConfigSchemaMeta` publishes `{json_schema, ui_schema, default_config}` for the Unique AI admin form. Use toolkit `RJSFMetaTag` / `get_configuration_dict` for custom widgets. CamelCase `alias_generator` is forwarded.

Presentation keys (`icon`, `system-prompt`, `tool-format-information`, `user-prompt`) are **list-only** — Unique AI does not echo them on `tools/call`.

## Inject

```python
config: MyConfig = Depends(get_tool_config(MyConfig))
settings = await get_unique_settings_async()  # in body
meta = get_request_meta()  # custom keys only
```

`get_tool_config` lookup: `_meta["unique.app/config"]` (dict or JSON string) → env `UNIQUE_MCP_TOOL_{SERVER}_{CONFIG}_CONFIG` → `Model()` defaults.

## Key catalogue

Auth: `unique.app/auth/user-id`, `unique.app/auth/company-id` (`MetaKeys.USER_ID` / `COMPANY_ID`).

Chat: `unique.app/chat/chat-id`, `user-message-id`, `assistant-id`, `parent-chat-id`, `last-assistant-message-id`, `last-user-message-text`.

Listing: `unique.app/icon`, `unique.app/system-prompt`, `unique.app/user-prompt`, `unique.app/tool-format-information`.

Not on `MetaKeys`: `unique.app/config-schema`, `unique.app/config`, `unique.app/context-requirements`.

Flat aliases (`userId`, `companyId`, …) are feature-flag fallback only. New writers always use namespaced keys.

## Extending

Implement `MetaPart` (`_META_KEY` + `merge_into_meta`). For a new call-time key: add `unique.app/…`, list it in `ContextRequirements`, read with `get_request_meta()`. No secrets in `_meta`.
