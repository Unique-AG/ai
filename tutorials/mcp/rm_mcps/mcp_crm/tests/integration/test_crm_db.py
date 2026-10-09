"""Integration tests against a real, seeded Postgres (the env setup).

Skipped automatically if no database is reachable. Run with:
    uv run pytest -m integration
"""

import json

import pytest

pytestmark = pytest.mark.integration

from common.db import get_conn  # noqa: E402

try:
    _c = get_conn()
    _c.close()
except Exception:  # pragma: no cover
    pytest.skip("no Postgres reachable", allow_module_level=True)

import client_memory  # noqa: E402
import crm  # noqa: E402
import meetings  # noqa: E402


def test_party_identity_resolves_name(fake_mcp):
    crm.register(fake_mcp)
    r = json.loads(fake_mcp.tools["get_party_identity"](input="Brunner"))
    assert r["client_id"] == "PTY-0002005"


def test_list_clients_status_filter(fake_mcp):
    crm.register(fake_mcp)
    r = json.loads(fake_mcp.tools["list_clients"](status="client"))
    assert r["total"] == 4  # Markus, Hofer, Lavanchy, Sophia Brown


def test_entity_ownership(fake_mcp):
    crm.register(fake_mcp)
    r = json.loads(fake_mcp.tools["get_entity_ownership"](input="Hofer"))
    assert r["client_id"] == "PTY-0002002" and "entity_type" in r


def test_unknown_client_fails_gracefully(fake_mcp):
    crm.register(fake_mcp)
    r = json.loads(fake_mcp.tools["get_party_identity"](input="ghost"))
    assert "Unknown client" in r["error"]


def test_next_meeting_for_client(fake_mcp):
    meetings.register(fake_mcp)
    # Use a client that reliably has a seeded meeting (Markus has no calendar event).
    r = json.loads(fake_mcp.tools["get_next_meeting"](input="Lavanchy"))
    assert r["next_meeting"] is not None


def test_client_memory_crud_round_trip(fake_mcp):
    client_memory.register(fake_mcp)
    get = fake_mcp.tools["get_talking_points"]
    upsert = fake_mcp.tools["upsert_talking_point"]
    delete = fake_mcp.tools["delete_talking_point"]

    # Markus is seeded with talking points at positions 1-5; use a free slot that is
    # still within the enforced MEMORY_MAX_POINTS (MAXITEMS) cap.
    before = len(json.loads(get(client_id="Markus")))
    upsert(client_id="Markus", position=20, text="integration test point")
    mid = json.loads(get(client_id="Markus"))
    assert any(r["position"] == 20 for r in mid)
    delete(client_id="Markus", position=20)
    after = len(json.loads(get(client_id="Markus")))
    assert after == before  # cleaned up, back to baseline


def test_reset_restores_baseline(fake_mcp):
    """Editing then resetting restores the seeded client memory."""
    import mcp_crm  # registers Reset_Demo_Data on its module-level `mcp`; use the helper directly
    from common.db import reset_demo_data
    import os
    sql_dir = os.path.join(os.path.dirname(mcp_crm.__file__), "sql")

    client_memory.register(fake_mcp)
    get = fake_mcp.tools["get_talking_points"]
    upsert = fake_mcp.tools["upsert_talking_point"]

    baseline = len(json.loads(get(client_id="Markus")))
    upsert(client_id="Markus", position=19, text="to be wiped by reset")  # free slot within MAXITEMS
    assert any(r["position"] == 19 for r in json.loads(get(client_id="Markus")))

    result = reset_demo_data(sql_dir)
    assert result["reset"] is True

    after = json.loads(get(client_id="Markus"))
    assert len(after) == baseline and not any(r["position"] == 19 for r in after)
