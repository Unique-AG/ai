from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient


def _load_account_review_server() -> Any:
    app_path = (
        Path(__file__).resolve().parents[3]
        / "datasets"
        / "account_review"
        / "fastmcp"
        / "app.py"
    )
    dataset_root = str(app_path.parent)
    if dataset_root not in sys.path:
        sys.path.insert(0, dataset_root)
    spec = importlib.util.spec_from_file_location(
        "account_review_app_for_admin_test", app_path
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
        assert "demo data editor" in home.text.lower()
        assert "by client" in home.text.lower()

        status = client.get("/api/status")
        assert status.status_code == 200
        payload = status.json()
        assert payload["dataset"] == "account_review"
        assert "clients" in payload["tables"]
        assert "case_actions" in payload["tables"]
        assert "figure_metrics" in payload["tables"]
        assert payload["auth_disabled"] is True


@pytest.mark.ai
def test_AI_admin_site__lists_and_updates_rows__via_rest_api() -> None:
    """
    Purpose: Verify admin REST list/PATCH can edit a case_actions row and reset restores seed.
    Why this matters: Operators need to tweak demo data without MCP tool calls.
    Setup summary: List clients, patch status on case_actions, then POST /api/reset.
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
            f"/api/tables/case_actions/rows/{row_id}",
            json={"fields": {"status": "Compliant"}},
        )
        assert patched.status_code == 200
        assert patched.json()["row"]["status"] == "Compliant"
        assert patched.json()["row"]["client_id"] == row_id

        reset = client.post("/api/reset")
        assert reset.status_code == 200
        summary = reset.json()
        table_names = {item["table"] for item in summary["tables"]}
        assert {
            "clients",
            "contacts",
            "case_actions",
            "figure_metrics",
        }.issubset(table_names)


@pytest.mark.ai
def test_AI_admin_site__client_bundle_and_section_patch__for_by_client_editor() -> None:
    """
    Purpose: Verify /api/clients list + bundle + section PATCH power the by-client UI.
    Why this matters: Editing should be client-centric across normalized tables.
    Setup summary: List clients, load one bundle, patch case_actions.status via section API.
    """
    module = _load_account_review_server()
    module.repo.reset_from_excel()
    app = module.mcp.http_app()

    with TestClient(app) as client:
        listed = client.get("/api/clients", params={"limit": 10})
        assert listed.status_code == 200
        body = listed.json()
        assert body["total_matching"] >= 1
        summary = body["rows"][0]
        client_id = summary["id"]
        assert summary["name"]
        assert summary["reference"]
        assert "status" in summary

        bundle = client.get(f"/api/clients/{client_id}")
        assert bundle.status_code == 200
        payload = bundle.json()
        assert payload["id"] == client_id
        assert "clients" in payload["sections"]
        assert "case_actions" in payload["sections"]
        assert "contacts" in payload["sections"]
        assert isinstance(payload["figure_metrics"], list)
        assert payload["sections"]["case_actions"]["client_id"] == client_id

        patched = client.patch(
            f"/api/clients/{client_id}/sections/case_actions",
            json={"fields": {"status": "Compliant", "client_id": 999}},
        )
        assert patched.status_code == 200
        assert patched.json()["row"]["status"] == "Compliant"
        # client_id must not be retargeted by the section editor
        assert patched.json()["row"]["client_id"] == client_id

        refreshed = client.get(f"/api/clients/{client_id}").json()
        assert refreshed["status"] == "Compliant"
        assert refreshed["sections"]["case_actions"]["status"] == "Compliant"
