"""Tests for Dynamic Frontend SDK and CLI helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import unique_sdk
from unique_sdk.api_resources._dynamic_frontend import DynamicFrontend
from unique_sdk.cli.commands.dynamic_frontend import (
    _format_space,
    cmd_dynamic_frontend_deploy,
    cmd_dynamic_frontend_list,
)
from unique_sdk.cli.config import Config
from unique_sdk.cli.state import ShellState

pytestmark = pytest.mark.ai


class _FakeSpace(dict[str, object]):
    def __getattr__(self, name: str) -> object:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def _state(path: str = "/Apps", scope_id: str | None = "scope_apps") -> ShellState:
    state = ShellState(
        Config(
            user_id="user_1",
            company_id="company_1",
            api_key="key",
            app_id="app",
            api_base="https://example.com",
        )
    )
    state._path = path
    state._scope_id = scope_id
    return state


def _space(
    *,
    space_id: str = "space_1",
    name: str = "Revenue Dashboard",
    content_id: str = "cont_1",
    status: dict[str, object] | None = None,
) -> _FakeSpace:
    return _FakeSpace(
        {
            "id": space_id,
            "spaceId": space_id,
            "name": name,
            "contentId": content_id,
            "status": status,
        }
    )


def test_dynamic_frontend_object_name__returns_api_resource_name() -> None:
    """Purpose: Verify the SDK resource object name is stable.
    Why this matters: The base SDK resource machinery depends on each resource's object name.
    Setup summary: Read the class property and assert it matches the API resource name.
    """
    assert DynamicFrontend.OBJECT_NAME == "dynamic-frontend"


@patch.object(DynamicFrontend, "_static_request", autospec=True)
def test_dynamic_frontend_create__calls_expected_endpoint(
    mock_request: MagicMock,
) -> None:
    """Purpose: Verify creating a Dynamic Frontend space sends the expected request.
    Why this matters: Incorrect method, path, or payload would create a broken SDK wrapper.
    Setup summary: Mock _static_request, call create, and assert the request shape.
    """
    mock_request.return_value = _space()

    result = DynamicFrontend.create(
        user_id="user_1",
        company_id="company_1",
        name="Revenue Dashboard",
        contentId="cont_1",
    )

    assert result["spaceId"] == "space_1"
    mock_request.assert_called_once_with(
        "post",
        "/dynamic-frontend",
        "user_1",
        "company_1",
        params={"name": "Revenue Dashboard", "contentId": "cont_1"},
    )


@patch.object(DynamicFrontend, "_static_request", autospec=True)
def test_dynamic_frontend_modify__calls_expected_endpoint(
    mock_request: MagicMock,
) -> None:
    """Purpose: Verify updating a Dynamic Frontend space sends the expected request.
    Why this matters: Update calls must target the existing space by id.
    Setup summary: Mock _static_request, call modify, and assert PATCH path and payload.
    """
    mock_request.return_value = _space(content_id="cont_2")

    result = DynamicFrontend.modify(
        "space_1",
        user_id="user_1",
        company_id="company_1",
        contentId="cont_2",
        name=None,
    )

    assert result["contentId"] == "cont_2"
    mock_request.assert_called_once_with(
        "patch",
        "/dynamic-frontend/space_1",
        "user_1",
        "company_1",
        params={"contentId": "cont_2", "name": None},
    )


@patch.object(DynamicFrontend, "_static_request", autospec=True)
def test_dynamic_frontend_list__returns_response_data(
    mock_request: MagicMock,
) -> None:
    """Purpose: Verify listing spaces unwraps the API data collection.
    Why this matters: CLI callers expect a plain list of manageable Dynamic Frontend spaces.
    Setup summary: Mock a data response, call list, and assert the returned collection.
    """
    mock_request.return_value = {"data": [_space()]}

    spaces = DynamicFrontend.list(user_id="user_1", company_id="company_1")

    assert spaces == [_space()]
    mock_request.assert_called_once_with(
        "get",
        "/dynamic-frontend",
        "user_1",
        "company_1",
    )


@patch.object(DynamicFrontend, "_static_request", autospec=True)
def test_dynamic_frontend_list__non_dict_response_returns_empty(
    mock_request: MagicMock,
) -> None:
    """Purpose: Verify malformed list responses degrade to an empty list.
    Why this matters: The command formatter can handle no spaces without crashing.
    Setup summary: Mock a non-dict response, call list, and assert an empty list.
    """
    mock_request.return_value = object()

    assert DynamicFrontend.list(user_id="user_1", company_id="company_1") == []


@patch("unique_sdk.cli.commands.dynamic_frontend.upload_file")
@patch("unique_sdk.DynamicFrontend.create")
def test_cmd_dynamic_frontend_deploy__uploads_file_and_creates_space(
    mock_create: MagicMock,
    mock_upload_file: MagicMock,
    tmp_path: Path,
) -> None:
    """Purpose: Verify deploy uploads a ZIP bundle and creates a new space.
    Why this matters: This is the main CLI path for publishing a Dynamic Frontend app.
    Setup summary: Create a local bundle, mock upload/create, and assert output plus API args.
    """
    bundle = tmp_path / "app.zip"
    bundle.write_bytes(b"zip")
    mock_upload_file.return_value = MagicMock(id="cont_1")
    mock_create.return_value = _space()

    output = cmd_dynamic_frontend_deploy(
        _state(),
        file=str(bundle),
        name="Revenue Dashboard",
    )

    assert 'Created Dynamic Frontend space "Revenue Dashboard" (space_1)' in output
    assert "Content: cont_1" in output
    mock_upload_file.assert_called_once_with(
        userId="user_1",
        companyId="company_1",
        path_to_file=str(bundle.resolve()),
        displayed_filename="app.zip",
        mime_type="application/zip",
        scope_or_unique_path="scope_apps",
    )
    mock_create.assert_called_once_with(
        user_id="user_1",
        company_id="company_1",
        name="Revenue Dashboard",
        contentId="cont_1",
    )


@patch("unique_sdk.DynamicFrontend.modify")
def test_cmd_dynamic_frontend_deploy__updates_existing_space(
    mock_modify: MagicMock,
) -> None:
    """Purpose: Verify deploy can update an existing Dynamic Frontend space.
    Why this matters: Iterating on an app should not require creating a new space each time.
    Setup summary: Mock modify, deploy by content id and space id, then assert payload.
    """
    mock_modify.return_value = _space(content_id="cont_2")

    output = cmd_dynamic_frontend_deploy(
        _state(),
        content_id="cont_2",
        space_id="space_1",
        name="Revenue Dashboard v2",
    )

    assert 'Updated Dynamic Frontend space "Revenue Dashboard" (space_1)' in output
    mock_modify.assert_called_once_with(
        "space_1",
        user_id="user_1",
        company_id="company_1",
        contentId="cont_2",
        name="Revenue Dashboard v2",
    )


def test_cmd_dynamic_frontend_deploy__validates_input() -> None:
    """Purpose: Verify deploy rejects missing or conflicting input before API calls.
    Why this matters: Clear CLI errors prevent confusing partial deployments.
    Setup summary: Call deploy without required input and assert the validation message.
    """
    assert "provide either --file or --content-id" in cmd_dynamic_frontend_deploy(
        _state(),
        name="Revenue Dashboard",
    )


def test_cmd_dynamic_frontend_deploy__requires_folder_for_upload(
    tmp_path: Path,
) -> None:
    """Purpose: Verify file upload refuses the root folder.
    Why this matters: Uploaded bundles need a concrete KB scope to store content.
    Setup summary: Create a bundle, use root state, and assert a helpful error.
    """
    bundle = tmp_path / "app.zip"
    bundle.write_bytes(b"zip")

    output = cmd_dynamic_frontend_deploy(
        _state(path="/", scope_id=None),
        file=str(bundle),
        name="Revenue Dashboard",
    )

    assert "cannot upload bundle to root" in output


@patch("unique_sdk.DynamicFrontend.create")
def test_cmd_dynamic_frontend_deploy__json_output(
    mock_create: MagicMock,
) -> None:
    """Purpose: Verify deploy can emit raw JSON for scripting.
    Why this matters: CI and automation consumers need machine-readable output.
    Setup summary: Mock create, deploy by content id with JSON output, and parse the result.
    """
    mock_create.return_value = _space()

    output = cmd_dynamic_frontend_deploy(
        _state(),
        content_id="cont_1",
        name="Revenue Dashboard",
        output_json=True,
    )

    assert json.loads(output)["spaceId"] == "space_1"


@patch("unique_sdk.DynamicFrontend.create")
def test_cmd_dynamic_frontend_deploy__api_error_is_returned(
    mock_create: MagicMock,
) -> None:
    """Purpose: Verify deploy reports SDK API errors as CLI output.
    Why this matters: CLI callers should receive actionable errors instead of tracebacks.
    Setup summary: Make create raise APIError and assert the returned message.
    """
    mock_create.side_effect = unique_sdk.APIError("upstream boom")

    output = cmd_dynamic_frontend_deploy(
        _state(),
        content_id="cont_1",
        name="Revenue Dashboard",
    )

    assert "dynamic-frontend deploy: upstream boom" in output


def test_format_space__includes_status_fields() -> None:
    """Purpose: Verify list formatting includes status phase and URL when present.
    Why this matters: Operators need deployment status and URL from list output.
    Setup summary: Format a fake space with status metadata and assert tabular fields.
    """
    output = _format_space(
        _space(status={"phase": "READY", "url": "https://app.example.com"})
    )

    assert (
        output == "space_1\tRevenue Dashboard\tcont_1\tREADY\thttps://app.example.com"
    )


@patch("unique_sdk.DynamicFrontend.list")
def test_cmd_dynamic_frontend_list__formats_spaces(mock_list: MagicMock) -> None:
    """Purpose: Verify list renders manageable Dynamic Frontend spaces.
    Why this matters: The default CLI output should be readable without JSON parsing.
    Setup summary: Mock one space, call list, and assert formatted content.
    """
    mock_list.return_value = [_space()]

    output = cmd_dynamic_frontend_list(_state())

    assert output == "space_1\tRevenue Dashboard\tcont_1"
    mock_list.assert_called_once_with(user_id="user_1", company_id="company_1")


@patch("unique_sdk.DynamicFrontend.list")
def test_cmd_dynamic_frontend_list__empty_result(mock_list: MagicMock) -> None:
    """Purpose: Verify list handles no manageable spaces.
    Why this matters: Empty accounts should get a clear message rather than blank output.
    Setup summary: Mock an empty list and assert the user-facing message.
    """
    mock_list.return_value = []

    assert (
        cmd_dynamic_frontend_list(_state())
        == "No manageable Dynamic Frontend spaces found."
    )


@patch("unique_sdk.DynamicFrontend.list")
def test_cmd_dynamic_frontend_list__json_output(mock_list: MagicMock) -> None:
    """Purpose: Verify list can emit raw JSON for scripting.
    Why this matters: Automation can consume full API fields without parsing table output.
    Setup summary: Mock one dict-like space, request JSON output, and parse it.
    """
    mock_list.return_value = [_space()]

    output = cmd_dynamic_frontend_list(_state(), output_json=True)

    assert json.loads(output)[0]["spaceId"] == "space_1"


@patch("unique_sdk.DynamicFrontend.list")
def test_cmd_dynamic_frontend_list__api_error_is_returned(mock_list: MagicMock) -> None:
    """Purpose: Verify list reports SDK API errors as CLI output.
    Why this matters: CLI users need an error string instead of an unhandled traceback.
    Setup summary: Make list raise APIError and assert the returned message.
    """
    mock_list.side_effect = unique_sdk.APIError("upstream boom")

    output = cmd_dynamic_frontend_list(_state())

    assert "dynamic-frontend list: upstream boom" in output
