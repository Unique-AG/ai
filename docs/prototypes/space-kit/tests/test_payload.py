import pytest

from space_kit.base import SpaceKitError
from space_kit.mcp import McpCatalog, McpChange, McpPlan
from space_kit.paths import Assignment, get_path
from space_kit.payload import (
    ClonePlan,
    McpContext,
    build_create_payload,
    build_update_payload,
)
from tests.support.fake_api import conduct_template, mcp_servers

pytestmark = pytest.mark.ai


def _context() -> McpContext:
    return McpContext(catalog=McpCatalog.from_api(rows=mcp_servers()))


def _plan(**overrides: object) -> ClonePlan:
    values: dict[str, object] = {
        "name": "variant-low",
        "template_id": "assistant_template",
        "assignments": (Assignment(path="claude.effort", value="low"),),
    }
    values.update(overrides)
    return ClonePlan.model_validate(values)


def test_create_payload_is_a_conduct_space_with_the_full_config() -> None:
    built = build_create_payload(
        template=conduct_template(), plan=_plan(), context=_context()
    )
    payload = built.payload
    module = payload["modules"][0]

    assert payload["uiType"] == "SWAPPABLE_INTELLIGENCE"
    assert payload["fallbackModule"] == "SwappableIntelligence"
    assert module["name"] == "SwappableIntelligence"
    assert module["weight"] == 500
    assert get_path(data=module["configuration"], path="claude.effort") == "low"
    assert get_path(data=module["configuration"], path="codex.model")
    assert payload["settings"] == {
        "allowUserMemory": False,
        "imageUpload": "ENABLED",
    }


def test_create_payload_sets_the_project_name_to_the_space_name() -> None:
    built = build_create_payload(
        template=conduct_template(), plan=_plan(), context=_context()
    )

    assert get_path(data=built.configuration, path="space.projectName") == (
        "variant-low"
    )
    assert built.changed_paths == ("claude.effort", "space.projectName")


def test_create_payload_carries_mcp_in_both_places() -> None:
    built = build_create_payload(
        template=conduct_template(), plan=_plan(), context=_context()
    )

    assert built.payload["mcpServers"] == [
        {"mcpServerId": "mcp_kb", "tools": []},
        {
            "mcpServerId": "mcp_yahoo",
            "tools": [
                {"name": "get_quote", "isEnabled": True},
                {"name": "search", "isEnabled": True},
            ],
        },
    ]
    assert get_path(data=built.configuration, path="tools[search@mcp_yahoo].isEnabled")


def test_create_payload_drops_prompt_ids_and_ids_of_modules() -> None:
    built = build_create_payload(
        template=conduct_template(), plan=_plan(), context=_context()
    )

    assert built.payload["assistantPrompts"] == [
        {"title": "Start", "prompt": "Hi", "order": 0}
    ]
    assert "id" not in built.payload["modules"][0]
    assert "id" not in built.payload


def test_mcp_change_updates_request_and_module_entries() -> None:
    plan = _plan(
        mcp=McpPlan(changes=(McpChange(server="yahoo-finance", tools="none"),))
    )

    built = build_create_payload(
        template=conduct_template(), plan=plan, context=_context()
    )

    assert {"mcpServerId": "mcp_yahoo", "tools": []} in built.payload["mcpServers"]
    assert "tools[get_quote].isEnabled" in built.changed_paths


def test_mcp_replace_switches_off_module_entries_of_unselected_servers() -> None:
    plan = _plan(
        mcp=McpPlan(
            replace=True,
            changes=(McpChange(server="yahoo-finance", tools="all"),),
        )
    )

    built = build_create_payload(
        template=conduct_template(), plan=plan, context=_context()
    )

    mcp_entries = [
        t for t in built.configuration["tools"] if t["configuration"].get("mcpTool")
    ]
    enabled = {t["configuration"]["mcpServerId"] for t in mcp_entries if t["isEnabled"]}
    assert enabled == {"mcp_yahoo"}
    assert [s["mcpServerId"] for s in built.payload["mcpServers"]] == ["mcp_yahoo"]


def test_not_copied_fields_are_reported() -> None:
    template = conduct_template()
    template["scopeRules"] = [{"id": "rule"}]

    built = build_create_payload(template=template, plan=_plan(), context=_context())

    assert any("scope rules" in w for w in built.warnings)


def test_unknown_space_field_is_refused() -> None:
    with pytest.raises(SpaceKitError, match="unsupported space field"):
        _ = build_create_payload(
            template=conduct_template(),
            plan=_plan(space_fields={"scopeRules": []}),
            context=_context(),
        )


def test_update_payload_sends_the_whole_module_config_by_module_id() -> None:
    built = build_update_payload(
        space=conduct_template(), plan=_plan(), context=_context()
    )

    assert list(built.payload) == ["modules"]
    update = built.payload["modules"][0]
    assert update["moduleId"] == "module_template"
    assert get_path(data=update["configuration"], path="claude.effort") == "low"
    assert get_path(data=update["configuration"], path="space.projectName") == (
        "base-space"
    )
