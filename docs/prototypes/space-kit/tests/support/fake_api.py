"""In-memory stand-in for the public space and MCP endpoints.

It mirrors the behaviour space-kit relies on: `mcpServers` writes the
attachments, a listed server gets exactly the listed tools, a
space-restricted server is refused unless allow-listed, and the caller of
POST /space owns the new space.
"""

import copy
import json
from collections.abc import Mapping
from urllib.parse import parse_qs, urlparse

from space_kit.api import HttpResponse
from space_kit.base import JsonObject, JsonValue

API_BASE = "https://gateway.qa.example.com/public/chat-gen2"


def conduct_template() -> JsonObject:
    return {
        "id": "assistant_template",
        "name": "base-space",
        "object": "space",
        "uiType": "SWAPPABLE_INTELLIGENCE",
        "fallbackModule": "SwappableIntelligence",
        "explanation": "Eval control",
        "alert": "Verify sources.",
        "chatUpload": "ENABLED",
        "languageModel": None,
        "isExternal": False,
        "isPinned": False,
        "allowModelSwitching": False,
        "switchableLanguageModels": [],
        "isSubAgent": False,
        "subAgentSettings": None,
        "title": None,
        "scopeRules": [],
        "subAgents": [],
        "briefing": None,
        "assistantPrompts": [
            {"id": "prompt_1", "title": "Start", "prompt": "Hi", "order": 0}
        ],
        "settings": {"allowUserMemory": False, "imageUpload": "ENABLED"},
        "modules": [
            {
                "id": "module_template",
                "name": "SwappableIntelligence",
                "description": None,
                "weight": 500,
                "isExternal": False,
                "isCustomInstructionEnabled": False,
                "toolDefinition": {},
                "configuration": {
                    "strategy": "claude_code",
                    "space": {"projectName": "base-space"},
                    "claude": {
                        "model": "anthropic-claude-sonnet-5-5",
                        "effort": "auto",
                        "maxBudgetUsd": 0,
                    },
                    "codex": {
                        "model": "AZURE_GPT_56_SOL_2026_0709",
                        "modelReasoningEffort": "medium",
                    },
                    "piAgent": {"modelName": "x", "thinkingLevel": "high"},
                    "setup": {
                        "agentMdInstructions": None,
                        "historyIncluded": True,
                        "scopeIds": [],
                    },
                    "tools": [
                        {
                            "name": "WebSearch",
                            "isEnabled": True,
                            "configuration": {},
                        },
                        {
                            "name": "search",
                            "isEnabled": True,
                            "configuration": {
                                "mcpTool": True,
                                "mcpServerId": "mcp_yahoo",
                            },
                        },
                        {
                            "name": "get_quote",
                            "isEnabled": True,
                            "configuration": {
                                "mcpTool": True,
                                "mcpServerId": "mcp_yahoo",
                            },
                        },
                        {
                            "name": "retired_tool",
                            "isEnabled": True,
                            "configuration": {
                                "mcpTool": True,
                                "mcpServerId": "mcp_yahoo",
                            },
                        },
                        {
                            "name": "search",
                            "isEnabled": False,
                            "configuration": {
                                "mcpTool": True,
                                "mcpServerId": "mcp_kb",
                            },
                        },
                    ],
                },
            }
        ],
        "assistantMcpServers": [
            {
                "id": "ams_1",
                "name": "yahoo-finance",
                "mcpServerId": "mcp_yahoo",
                "isEnabled": True,
                "tools": [
                    {"name": "get_quote", "isEnabled": True},
                    {"name": "retired_tool", "isEnabled": True},
                    {"name": "search", "isEnabled": True},
                ],
            },
            {
                "id": "ams_2",
                "name": "Unique Search MCP QA",
                "mcpServerId": "mcp_kb",
                "isEnabled": False,
                "tools": [{"name": "search", "isEnabled": False}],
            },
        ],
    }


def mcp_servers() -> list[JsonObject]:
    return [
        {
            "id": "mcp_yahoo",
            "name": "yahoo-finance",
            "isSpaceRestricted": False,
            "allowedSpaceIds": [],
            "requiresOAuth": False,
            "tools": [
                {"name": "get_quote", "description": None},
                {"name": "search", "description": None},
                {"name": "get_chart", "description": None},
            ],
        },
        {
            "id": "mcp_kb",
            "name": "Unique Search MCP QA",
            "isSpaceRestricted": False,
            "allowedSpaceIds": [],
            "requiresOAuth": True,
            "tools": [{"name": "search", "description": None}],
        },
        {
            "id": "mcp_atl_1",
            "name": "mcp.atlassian.com",
            "isSpaceRestricted": False,
            "allowedSpaceIds": [],
            "requiresOAuth": True,
            "tools": [{"name": "getJiraIssue", "description": None}],
        },
        {
            "id": "mcp_atl_2",
            "name": "mcp.atlassian.com",
            "isSpaceRestricted": False,
            "allowedSpaceIds": [],
            "requiresOAuth": True,
            "tools": [{"name": "getJiraIssue", "description": None}],
        },
        {
            "id": "mcp_secret",
            "name": "Elicitation Tester",
            "isSpaceRestricted": True,
            "allowedSpaceIds": [],
            "requiresOAuth": False,
            "tools": [{"name": "ask", "description": None}],
        },
    ]


class FakeSpaceServer:
    def __init__(
        self,
        *,
        spaces: list[JsonObject] | None = None,
        servers: list[JsonObject] | None = None,
    ) -> None:
        self.spaces: dict[str, JsonObject] = {
            str(s["id"]): s for s in (spaces or [conduct_template()])
        }
        self.servers: list[JsonObject] = servers or mcp_servers()
        self.requests: list[tuple[str, str, JsonValue]] = []
        self.access: dict[str, list[JsonValue]] = {}
        self._counter: int = 0

    def writes(self) -> list[tuple[str, str, JsonValue]]:
        return [r for r in self.requests if r[0] != "GET"]

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: JsonValue,
    ) -> HttpResponse:
        assert headers["x-api-version"] == "2023-12-06"
        parsed = urlparse(url)
        path = parsed.path.removeprefix(urlparse(API_BASE).path)
        self.requests.append((method, path, copy.deepcopy(body)))
        handler = self._route(method=method, path=path)
        if handler is None:
            return HttpResponse(status=404, body={"message": "no route"})
        return handler(path=path, query=parse_qs(parsed.query), body=body)

    def _route(self, *, method: str, path: str):
        parts = path.strip("/").split("/")
        routes = {
            ("GET", 2, "mcp"): self._list_mcp,
            ("GET", 1, "space"): self._list_spaces,
            ("POST", 1, "space"): self._create,
            ("GET", 2, "space"): self._get,
            ("PATCH", 2, "space"): self._patch,
            ("DELETE", 2, "space"): self._delete,
            ("POST", 3, "space"): self._access,
        }
        return routes.get((method, len(parts), parts[0]))

    def _list_mcp(self, *, path: str, query: object, body: JsonValue) -> HttpResponse:
        return HttpResponse(
            status=200,
            body={"object": "mcp-servers", "mcpServers": self.servers},
        )

    def _list_spaces(
        self, *, path: str, query: dict[str, list[str]], body: JsonValue
    ) -> HttpResponse:
        wanted = query.get("name", [""])[0].lower()
        found: list[JsonValue] = [
            s for s in self.spaces.values() if wanted in str(s["name"]).lower()
        ]
        return HttpResponse(status=200, body={"object": "list", "data": found})

    def _get(self, *, path: str, query: object, body: JsonValue) -> HttpResponse:
        space = self.spaces.get(path.split("/")[-1])
        if space is None:
            return HttpResponse(status=404, body={"message": "not found"})
        return HttpResponse(status=200, body=copy.deepcopy(space))

    def _attachments(
        self, *, space_id: str, requested: JsonValue
    ) -> list[JsonValue] | HttpResponse:
        attachments: list[JsonValue] = []
        for item in requested if isinstance(requested, list) else []:
            assert isinstance(item, dict)
            server = next(s for s in self.servers if s["id"] == item["mcpServerId"])
            allowed = server.get("allowedSpaceIds") or []
            if server["isSpaceRestricted"] and space_id not in allowed:
                return HttpResponse(status=400, body={"message": "not allowed"})
            tools = item.get("tools") or []
            assert isinstance(tools, list)
            enabled = {
                t["name"] for t in tools if isinstance(t, dict) and t["isEnabled"]
            }
            attachments.append(
                {
                    "id": f"ams_{space_id}_{server['id']}",
                    "name": server["name"],
                    "mcpServerId": server["id"],
                    "isEnabled": bool(enabled),
                    "tools": [
                        {"name": n, "isEnabled": n in enabled}
                        for n in sorted(str(t["name"]) for t in server["tools"])
                    ],
                }
            )
        return attachments

    def _create(self, *, path: str, query: object, body: JsonValue) -> HttpResponse:
        assert isinstance(body, dict)
        self._counter += 1
        space_id = f"assistant_new{self._counter}"
        attachments = self._attachments(
            space_id=space_id, requested=body.get("mcpServers")
        )
        if isinstance(attachments, HttpResponse):
            return attachments
        modules = [
            {**m, "id": f"module_{space_id}_{i}"} for i, m in enumerate(body["modules"])
        ]
        stored: JsonObject = {
            **{k: v for k, v in body.items() if k != "mcpServers"},
            "id": space_id,
            "object": "space",
            "modules": json.loads(json.dumps(modules)),
            "assistantMcpServers": attachments,
            "scopeRules": [],
        }
        self.spaces[space_id] = stored
        return HttpResponse(status=201, body={"id": space_id, "name": body["name"]})

    def _patch(self, *, path: str, query: object, body: JsonValue) -> HttpResponse:
        space_id = path.split("/")[-1]
        space = self.spaces[space_id]
        assert isinstance(body, dict)
        for update in body.get("modules") or []:
            assert isinstance(update, dict)
            for module in space["modules"]:
                assert isinstance(module, dict)
                if module["id"] == update["moduleId"]:
                    module["configuration"] = update["configuration"]
        for key, value in body.items():
            if key not in ("modules", "mcpServers"):
                space[key] = value
        if "mcpServers" in body:
            attachments = self._attachments(
                space_id=space_id, requested=body["mcpServers"]
            )
            assert not isinstance(attachments, HttpResponse)
            space["assistantMcpServers"] = attachments
        return HttpResponse(status=200, body=copy.deepcopy(space))

    def _delete(self, *, path: str, query: object, body: JsonValue) -> HttpResponse:
        space_id = path.split("/")[-1]
        del self.spaces[space_id]
        return HttpResponse(
            status=200, body={"id": space_id, "object": "deleted-space"}
        )

    def _access(self, *, path: str, query: object, body: JsonValue) -> HttpResponse:
        space_id = path.strip("/").split("/")[1]
        assert isinstance(body, dict)
        self.access.setdefault(space_id, []).extend(body["access"])
        return HttpResponse(status=201, body={"access": self.access[space_id]})
