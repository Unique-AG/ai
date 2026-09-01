"""Integration contract test (real seeded DB): drive every documented CRM input
form from MCP_SERVERS.md and assert the documented output. Skipped if no DB.
"""

import json

import pytest

pytestmark = pytest.mark.integration

from common.db import get_conn  # noqa: E402

try:
    _c = get_conn(); _c.close()
except Exception:  # pragma: no cover
    pytest.skip("no Postgres reachable", allow_module_level=True)

import client_memory  # noqa: E402
import crm  # noqa: E402
import meetings  # noqa: E402


@pytest.fixture
def tools(fake_mcp):
    for mod in (crm, client_memory, meetings):
        mod.register(fake_mcp)
    return fake_mcp.tools


def call(tools, name, **kwargs):
    return json.loads(tools[name](**kwargs))


# --- input equivalence: name == canonical id == legacy numeric id ------------------------------
def test_identity_input_forms_resolve_identically(tools):
    a = call(tools, "get_party_identity", input="Katharina Brunner")
    b = call(tools, "get_party_identity", input="PTY-0002005")
    c = call(tools, "get_party_identity", input="800870664420")          # legacy numeric
    d = call(tools, "get_party_identity", client_id="PTY-0002005")        # client_id arg
    for r in (a, b, c, d):
        assert r["client_id"] == "PTY-0002005"
    assert a == b == c == d


# --- per-client CRM tools: documented output keys (Markus = full client) -----------------------
@pytest.mark.parametrize("tool,required", [
    ("get_party_identity", {"client_id", "full_legal_name", "aliases", "date_of_birth", "place_of_birth", "gender", "nationalities", "country_of_residence", "tax_residences"}),
    ("get_identifiers", {"client_id", "internal_party_id"}),
    ("get_relationship", {"client_id", "client_vs_prospect", "owning_rm_team_booking_centre", "client_segment", "referral_source", "languages", "contact"}),
    ("get_mandate_objectives", {"client_id", "mandate_type", "investment_objective", "risk_profile", "investment_horizon_liquidity", "constraints_exclusions", "reference_currency"}),
    ("get_history", {"client_id", "interaction_log", "open_tasks", "life_events", "complaints"}),
    ("get_entity_ownership", {"client_id", "entity_type", "beneficial_owners", "directors", "controllers", "authorised_signatories", "ownership_structure_depth", "note"}),
])
def test_crm_output_keys(tools, tool, required):
    out = call(tools, tool, input="Markus")
    assert required <= set(out), f"{tool} missing {required - set(out)}"


# --- list_clients: no-args (whole book) + every documented filter ------------------------------
def test_list_clients_no_args_is_whole_book(tools):
    # The cockpit binds list_clients with {} (no args) — must return the whole book.
    out = call(tools, "list_clients")
    assert {"total", "count", "skip", "limit", "clients"} <= set(out)
    assert out["total"] == 8
    assert {"client_id", "name", "status", "segment", "rm", "open_doc_payload"} <= set(out["clients"][0])


@pytest.mark.parametrize("kwargs,expected_total", [
    ({"status": "client"}, 4),     # Markus, Hofer, Lavanchy, Sophia Brown
    ({"status": "prospect"}, 4),   # Katharina, Ellery, Moretti-Conti, Augustus Feng
    ({"segment": "UHNW"}, 4),      # Lavanchy, Moretti-Conti, Ellery, Feng
    ({"rm": "marc.dubois"}, 3),
    ({"q": "Brunner"}, 2),
])
def test_list_clients_filters(tools, kwargs, expected_total):
    assert call(tools, "list_clients", **kwargs)["total"] == expected_total


def test_list_available_documents_keys(tools):
    out = call(tools, "list_available_documents", input="Markus")
    assert {"client_id", "count", "documents", "items"} <= set(out)
    if out["count"]:
        assert {"title", "contentId", "kind"} <= set(out["documents"][0])


# --- calendar: client / RM username / 'week' / omit + next-meeting -----------------------------
def test_get_meetings_by_client(tools):
    out = call(tools, "get_meetings", input="Markus")
    assert {"count", "meetings"} <= set(out) and out.get("client_id") == "CH-PB-0049217"


def test_get_meetings_week_and_omit_return_all(tools):
    wk = call(tools, "get_meetings", input="week")
    allm = call(tools, "get_meetings", input="")
    assert "client_id" not in wk and wk["count"] == allm["count"] >= 1


def test_get_meetings_by_rm(tools):
    out = call(tools, "get_meetings", input="marc.dubois")
    assert out["count"] >= 1 and "client_id" not in out


def test_next_meeting_client_and_unknown(tools):
    nm = call(tools, "get_next_meeting", input="Markus")
    assert "next_meeting" in nm
    err = call(tools, "get_next_meeting", input="Ghost Client")
    assert "Unknown client" in err["error"]   # named miss → hint, not global earliest


# --- client memory: read array + CRUD round-trip (input alias too) -----------------------------
def test_memory_read_is_top_level_array(tools):
    rows = call(tools, "get_talking_points", client_id="Markus")
    assert isinstance(rows, list) and (not rows or {"client_id", "position", "text"} <= set(rows[0]))


def test_memory_crud_round_trip(tools):
    get = lambda: call(tools, "get_talking_points", client_id="Markus")
    before = len(get())
    pos = 17  # free slot within MEMORY_MAX_POINTS
    up = call(tools, "upsert_talking_point", input="Markus", position=pos, text="contract test")
    assert up["updated"] and up["client_id"] == "CH-PB-0049217"
    assert any(r["position"] == pos for r in get())
    call(tools, "delete_talking_point", client_id="Markus", position=pos)
    assert len(get()) == before


def test_unknown_client_hint(tools):
    out = call(tools, "get_relationship", input="Nobody McGhost")
    assert "Unknown client" in out["error"]
