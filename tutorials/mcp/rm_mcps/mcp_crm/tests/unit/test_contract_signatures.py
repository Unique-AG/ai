"""Env-agnostic contract test: every CRM tool must ACCEPT every argument the
MCP_SERVERS.md documents for it (no DB — signature inspection only)."""

import inspect

import client_memory
import crm
import meetings
import person_lookup

CONTRACT = {
    # identity / relationship (per-client): name or client_id
    "get_party_identity": {"input", "client_id"},
    "get_identifiers": {"input", "client_id"},
    "get_relationship": {"input", "client_id"},
    "get_mandate_objectives": {"input", "client_id"},
    "get_history": {"input", "client_id"},
    "get_entity_ownership": {"input", "client_id"},
    # roster + catalog
    "list_clients": {"q", "status", "segment", "rm", "limit", "skip"},
    "list_available_documents": {"input", "client_id"},
    # calendar
    "get_meetings": {"input"},
    "get_next_meeting": {"input"},
    # editable client memory (get / upsert / delete) — accept client_id OR input
    "get_talking_points": {"client_id", "input"},
    "get_open_questions": {"client_id", "input"},
    "list_documents": {"client_id", "input"},
    "upsert_talking_point": {"client_id", "input", "position", "text"},
    "upsert_open_question": {"client_id", "input", "position", "text"},
    "upsert_document": {"client_id", "input", "position", "title", "contentId"},
    "delete_talking_point": {"client_id", "input", "position"},
    "delete_open_question": {"client_id", "input", "position"},
    "delete_document": {"client_id", "input", "position"},
    # person screening (WorldCheck)
    "screen_person": {"name", "country", "nationality", "date_of_birth", "dob_tolerance_years",
                      "place_of_birth", "gender", "entity_type", "passport_number", "national_id",
                      "tax_id", "wc_uid", "threshold", "max_results"},
}


def _all_tools(fake_mcp):
    for mod in (crm, client_memory, meetings, person_lookup):
        mod.register(fake_mcp)
    return fake_mcp.tools


def test_every_documented_arg_is_accepted(fake_mcp):
    tools = _all_tools(fake_mcp)
    missing = {}
    for name, args in CONTRACT.items():
        assert name in tools, f"tool {name} not registered"
        params = set(inspect.signature(tools[name]).parameters)
        gap = args - params
        if gap:
            missing[name] = sorted(gap)
    assert not missing, f"tools missing documented args: {missing}"


def test_all_contract_tools_exist(fake_mcp):
    tools = _all_tools(fake_mcp)
    assert set(CONTRACT) <= set(tools), f"unregistered: {set(CONTRACT) - set(tools)}"
