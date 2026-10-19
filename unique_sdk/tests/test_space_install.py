from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk.api_resources._mcp import MCP
from unique_sdk.api_resources._space import Space


def test_create_space_forwards_a_conduct_space() -> None:
    modules: list[Space.ModuleParams] = [
        {
            "name": "SwappableIntelligence",
            "weight": 500,
            "configuration": {"claude": {}, "space": {"projectName": "Install"}},
        }
    ]

    with patch.object(
        Space, "_static_request", return_value={"id": "assistant_install"}
    ) as request:
        Space.create_space(
            user_id="user_1",
            company_id="company_1",
            name="Install",
            uiType="SWAPPABLE_INTELLIGENCE",
            fallbackModule="SwappableIntelligence",
            modules=modules,
        )

    request.assert_called_once_with(
        "post",
        "/space",
        "user_1",
        "company_1",
        params={
            "name": "Install",
            "uiType": "SWAPPABLE_INTELLIGENCE",
            "fallbackModule": "SwappableIntelligence",
            "modules": modules,
        },
    )


def test_create_space_forwards_mcp_servers() -> None:
    mcp_servers: list[Space.McpServerParams] = [
        {
            "mcpServerId": "mcp_server_1",
            "tools": [{"name": "search_issues", "isEnabled": True}],
        },
        {"mcpServerId": "mcp_server_2"},
    ]

    with patch.object(
        Space, "_static_request", return_value={"id": "assistant_new"}
    ) as request:
        Space.create_space(
            user_id="user_1",
            company_id="company_1",
            name="Space with connectors",
            fallbackModule="UniqueAi",
            modules=[{"name": "UniqueAi"}],
            mcpServers=mcp_servers,
        )

    assert request.call_args.kwargs["params"]["mcpServers"] == mcp_servers


def test_update_space_forwards_mcp_servers() -> None:
    with patch.object(
        Space, "_static_request", return_value={"id": "assistant_1"}
    ) as request:
        Space.update_space(
            user_id="user_1",
            company_id="company_1",
            space_id="assistant_1",
            mcpServers=[{"mcpServerId": "mcp_server_1", "tools": []}],
        )

    request.assert_called_once_with(
        "patch",
        "/space/assistant_1",
        "user_1",
        "company_1",
        params={"mcpServers": [{"mcpServerId": "mcp_server_1", "tools": []}]},
    )


def test_get_mcp_server_status_gets_status_route() -> None:
    status = {
        "object": "space-mcp-server-status",
        "spaceId": "assistant_1",
        "mcpServers": [],
    }
    with patch.object(Space, "_static_request", return_value=status) as request:
        result = Space.get_mcp_server_status(
            user_id="user_1",
            company_id="company_1",
            space_id="assistant_1",
        )

    request.assert_called_once_with(
        "get",
        "/space/assistant_1/mcp-servers/status",
        "user_1",
        "company_1",
    )
    assert result["spaceId"] == "assistant_1"


@pytest.mark.asyncio
async def test_get_mcp_server_status_async_gets_status_route() -> None:
    with patch.object(
        Space,
        "_static_request_async",
        new=AsyncMock(return_value={"spaceId": "assistant_1", "mcpServers": []}),
    ) as request:
        await Space.get_mcp_server_status_async(
            user_id="user_1",
            company_id="company_1",
            space_id="assistant_1",
        )

    request.assert_awaited_once_with(
        "get",
        "/space/assistant_1/mcp-servers/status",
        "user_1",
        "company_1",
    )


def test_list_mcp_servers_gets_servers_route() -> None:
    servers = {"object": "mcp-servers", "mcpServers": []}
    with patch.object(MCP, "_static_request", return_value=servers) as request:
        result = MCP.list_servers(user_id="user_1", company_id="company_1")

    request.assert_called_once_with("get", "/mcp/servers", "user_1", "company_1")
    assert result["mcpServers"] == []


@pytest.mark.asyncio
async def test_list_mcp_servers_async_gets_servers_route() -> None:
    with patch.object(
        MCP,
        "_static_request_async",
        new=AsyncMock(return_value={"mcpServers": []}),
    ) as request:
        await MCP.list_servers_async(user_id="user_1", company_id="company_1")

    request.assert_awaited_once_with("get", "/mcp/servers", "user_1", "company_1")
