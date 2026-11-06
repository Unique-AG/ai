import pytest

from space_kit.base import SpaceKitError
from space_kit.mcp import (
    McpCatalog,
    McpChange,
    apply_changes,
    build_id_map,
    check_restricted,
    parse_change,
    sync_config_tools,
    template_selection,
    to_request,
)
from space_kit.payload import module_configuration
from tests.support.fake_api import conduct_template, mcp_servers

pytestmark = pytest.mark.ai


def _catalog() -> McpCatalog:
    return McpCatalog.from_api(rows=mcp_servers())


def test_template_selection_leaves_off_tools_the_company_disabled() -> None:
    result = template_selection(space=conduct_template(), catalog=_catalog(), id_map={})

    assert result.selection["mcp_yahoo"] == {"get_quote", "search"}
    assert any("retired_tool" in w for w in result.warnings)


def test_template_selection_keeps_a_disabled_attachment_as_disabled() -> None:
    result = template_selection(space=conduct_template(), catalog=_catalog(), id_map={})

    assert result.selection["mcp_kb"] == frozenset()


def test_apply_changes_supports_all_none_and_a_tool_list() -> None:
    changed = apply_changes(
        selection={"mcp_yahoo": frozenset({"search"})},
        changes=(
            McpChange(server="yahoo-finance", tools="all"),
            McpChange(server="mcp_kb", tools=("search",)),
            McpChange(server="mcp_atl_1", tools="none"),
        ),
        catalog=_catalog(),
    )

    assert changed["mcp_yahoo"] == {"get_quote", "search", "get_chart"}
    assert changed["mcp_kb"] == {"search"}
    assert changed["mcp_atl_1"] == frozenset()


def test_apply_changes_refuses_an_unknown_tool_and_lists_callable_ones() -> None:
    with pytest.raises(SpaceKitError, match=r"no callable tool.*get_chart"):
        _ = apply_changes(
            selection={},
            changes=(McpChange(server="yahoo-finance", tools=("nope",)),),
            catalog=_catalog(),
        )


def test_an_ambiguous_server_name_must_be_given_by_id() -> None:
    with pytest.raises(SpaceKitError, match=r"ambiguous.*mcp_atl_1, mcp_atl_2"):
        _ = _catalog().resolve(ref="mcp.atlassian.com")


def test_a_restricted_server_fails_loudly_unless_skipped() -> None:
    selection = {"mcp_secret": frozenset({"ask"}), "mcp_kb": frozenset()}

    with pytest.raises(SpaceKitError, match="space-restricted"):
        _ = check_restricted(
            selection=selection, catalog=_catalog(), space_id=None, skip=False
        )
    skipped = check_restricted(
        selection=selection, catalog=_catalog(), space_id=None, skip=True
    )

    assert set(skipped.selection) == {"mcp_kb"}
    assert skipped.warnings


def test_to_request_lists_only_enabled_tools_and_empty_disables() -> None:
    request = to_request(
        selection={"mcp_b": frozenset(), "mcp_a": frozenset({"y", "x"})}
    )

    assert request == [
        {
            "mcpServerId": "mcp_a",
            "tools": [
                {"name": "x", "isEnabled": True},
                {"name": "y", "isEnabled": True},
            ],
        },
        {"mcpServerId": "mcp_b", "tools": []},
    ]


def test_sync_config_tools_matches_module_entries_to_the_selection() -> None:
    configuration = module_configuration(space=conduct_template())

    synced = sync_config_tools(
        configuration=configuration,
        selection={"mcp_yahoo": frozenset({"get_quote"})},
        catalog=_catalog(),
        id_map={},
        drop_servers=frozenset(),
    )

    states = {
        (t["name"], t["configuration"].get("mcpServerId")): t["isEnabled"]
        for t in synced["tools"]
    }
    assert states[("get_quote", "mcp_yahoo")] is True
    assert states[("search", "mcp_yahoo")] is False
    assert states[("WebSearch", None)] is True


def test_sync_config_tools_keeps_entries_the_server_no_longer_exposes() -> None:
    configuration = module_configuration(space=conduct_template())

    synced = sync_config_tools(
        configuration=configuration,
        selection={"mcp_yahoo": frozenset()},
        catalog=_catalog(),
        id_map={},
        drop_servers=frozenset(),
    )

    retired = next(t for t in synced["tools"] if t["name"] == "retired_tool")
    assert retired["isEnabled"] is True


def test_sync_config_tools_remaps_and_drops_servers() -> None:
    configuration = module_configuration(space=conduct_template())

    synced = sync_config_tools(
        configuration=configuration,
        selection={},
        catalog=_catalog(),
        id_map={"mcp_yahoo": "mcp_yahoo_local"},
        drop_servers=frozenset({"mcp_kb"}),
    )

    servers = {t["configuration"].get("mcpServerId") for t in synced["tools"]}
    assert servers == {None, "mcp_yahoo_local"}


def test_build_id_map_matches_unique_names_and_reports_the_rest() -> None:
    source = _catalog()
    target = McpCatalog.from_api(
        rows=[
            {**row, "id": f"{row['id']}_t"}
            for row in mcp_servers()
            if row["id"] != "mcp_kb"
        ]
    )

    id_map, unmapped = build_id_map(
        source_ids={"mcp_yahoo", "mcp_kb", "mcp_atl_1"},
        source=source,
        target=target,
        explicit={},
    )

    assert id_map == {"mcp_yahoo": "mcp_yahoo_t"}
    assert len(unmapped) == 2


def test_parse_change_reads_the_cli_form() -> None:
    assert parse_change(text="yahoo-finance=all").tools == "all"
    assert parse_change(text="mcp_a=x, y").tools == ("x", "y")
    with pytest.raises(SpaceKitError):
        _ = parse_change(text="yahoo-finance")
