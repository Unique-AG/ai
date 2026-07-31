from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient


def _load_account_review_server() -> Any:
    server_path = (
        Path(__file__).resolve().parents[3]
        / "datasets"
        / "account_review"
        / "fastmcp"
        / "server.py"
    )
    spec = importlib.util.spec_from_file_location(
        "account_review_server_for_admin_test", server_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.ai
def test_AI_admin_site__serves_html_and_status_api__for_db_console() -> None:
    """
    Purpose: Verify the FastMCP process exposes an admin HTML UI and /api/status.
    Why this matters: Azure deploy needs a browser surface to edit/reset the demo DB.
    Setup summary: Load the account_review server module and hit routes via TestClient.
    """
    module = _load_account_review_server()
    module.repo.ensure_ready()
    app = module.mcp.http_app()

    with TestClient(app) as client:
        home = client.get("/")
        assert home.status_code == 200
        assert "text/html" in home.headers.get("content-type", "")
        assert "database admin" in home.text.lower()

        status = client.get("/api/status")
        assert status.status_code == 200
        payload = status.json()
        assert payload["dataset"] == "account_review"
        assert "clients" in payload["tables"]
        assert payload["auth_disabled"] is True


@pytest.mark.ai
def test_AI_admin_site__lists_and_updates_rows__via_rest_api() -> None:
    """
    Purpose: Verify admin REST list/PATCH can edit a clients row and reset restores seed.
    Why this matters: Operators need to tweak demo data without MCP tool calls.
    Setup summary: List clients, patch one status field, then POST /api/reset.
    """
    module = _load_account_review_server()
    module.repo.ensure_ready()
    app = module.mcp.http_app()

    with TestClient(app) as client:
        listed = client.get("/api/tables/clients/rows", params={"limit": 5})
        assert listed.status_code == 200
        body = listed.json()
        assert body["total_matching"] >= 1
        row = body["rows"][0]
        row_id = row["id"]

        patched = client.patch(
            f"/api/tables/clients/rows/{row_id}",
            json={"fields": {"case_action_status": "Compliant"}},
        )
        assert patched.status_code == 200
        assert patched.json()["row"]["case_action_status"] == "Compliant"

        reset = client.post("/api/reset")
        assert reset.status_code == 200
        assert reset.json()["tables"]
