# Tool template

Copy this shape. Swap the config model, `_META` strings, and Unique toolkit calls.

```python
import logging
from typing import Annotated

from fastmcp.dependencies import Depends
from fastmcp.tools import tool
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import BaseModel, Field

from unique_mcp import (
    ConfigSchemaMeta,
    ContextRequirements,
    MetaKeys,
    UniqueAIToolMeta,
    get_tool_config,
    get_unique_settings_async,
    merge_tool_meta,
)

_LOGGER = logging.getLogger(__name__)


class MyToolConfig(BaseModel):
    limit: int = 20


_META = merge_tool_meta(
    {"unique.app/icon": "search"},
    ContextRequirements(required=[MetaKeys.USER_ID, MetaKeys.COMPANY_ID]),
    ConfigSchemaMeta(MyToolConfig),
    UniqueAIToolMeta(
        tool_description_for_system_prompt="Choose this tool to …",
        tool_format_information_for_system_prompt="Paste markdown links the tool returns as-is.",
    ),
)


@tool(
    name="my_tool",
    description="One sentence for the model: what it does and when to call it.",
    meta=_META,
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def my_tool(
    query: Annotated[str, Field(description="What the model must supply.")],
    config: MyToolConfig = Depends(get_tool_config(MyToolConfig)),
) -> CallToolResult:
    try:
        settings = await get_unique_settings_async()
        # bind Unique toolkit services with `settings`; use `config` for admin knobs
        _ = settings, config, query
        text = "ok"
    except Exception as exc:
        _LOGGER.exception("my_tool error")
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=str(exc))],
        )
    return CallToolResult(content=[TextContent(type="text", text=text)])
```

Server bootstrap (local `MemoryStore` — replace in prod):

```python
from fastmcp import FastMCP
from key_value.aio.stores.memory import MemoryStore

from unique_mcp.auth.zitadel.oauth_proxy import (
    ZitadelOAuthProxySettings,
    create_zitadel_oauth_proxy,
)
from unique_mcp.logging import configure_logging
from unique_mcp.monitoring import setup_ops
from unique_mcp.settings import ServerSettings

configure_logging()
server_settings = ServerSettings()
oauth = create_zitadel_oauth_proxy(
    client_storage=MemoryStore(),
    mcp_server_base_url=server_settings.base_url.encoded_string(),
    zitadel_oauth_proxy_settings=ZitadelOAuthProxySettings(),
)
mcp = FastMCP("my-server", auth=oauth)
middleware = [setup_ops(mcp)]
mcp.run(transport=server_settings.transport_scheme, middleware=middleware)
```
