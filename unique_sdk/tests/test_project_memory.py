from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk import ProjectMemory as PublicProjectMemory
from unique_sdk._util import convert_to_unique_object
from unique_sdk.api_resources._project_memory import ProjectMemory

pytestmark = pytest.mark.ai

USER_ID = "user_1"
COMPANY_ID = "company_1"
PROJECT_ID = "custom_space_1"
URL = f"/projects/{PROJECT_ID}/memory"
SERVICE_ID = "assistants-core"
SERVICE_HEADERS = {"x-service-id": SERVICE_ID}
MEMORY = {
    "id": "project_memory_1",
    "projectId": PROJECT_ID,
    "document": "# Project memory",
    "state": '{"schema_version": 3}',
    "createdAt": "2026-11-19T12:00:00.000Z",
    "updatedAt": "2026-11-20T02:00:00.000Z",
    "object": "project-memory",
}
EMPTY = {
    "id": None,
    "projectId": PROJECT_ID,
    "document": None,
    "state": None,
    "createdAt": None,
    "updatedAt": None,
    "object": "project-memory",
}
DELETED = {"id": PROJECT_ID, "object": "project-memory", "deleted": True}


def test_project_memory_is_exported():
    assert PublicProjectMemory is ProjectMemory
    assert ProjectMemory.OBJECT_NAME == "project-memory"


def test_responses_convert_to_project_memory():
    # The object registry maps "project-memory" responses to the resource
    # class, so results are real ProjectMemory instances, not UniqueObject.
    result = convert_to_unique_object(dict(MEMORY), USER_ID, COMPANY_ID)

    assert isinstance(result, ProjectMemory)
    assert result.document == "# Project memory"
    assert result.state == '{"schema_version": 3}'


@patch.object(ProjectMemory, "_static_request")
def test_retrieve_requests_the_project_memory(mock_request):
    mock_request.return_value = EMPTY

    result = ProjectMemory.retrieve(USER_ID, COMPANY_ID, PROJECT_ID)

    mock_request.assert_called_once_with(
        "get", URL, USER_ID, COMPANY_ID, supplied_headers=None
    )
    assert result == EMPTY


@patch.object(ProjectMemory, "_static_request")
def test_modify_patches_document_and_state(mock_request):
    mock_request.return_value = MEMORY

    result = ProjectMemory.modify(
        USER_ID,
        COMPANY_ID,
        PROJECT_ID,
        document="# Project memory",
        state='{"schema_version": 3}',
    )

    mock_request.assert_called_once_with(
        "patch",
        URL,
        USER_ID,
        COMPANY_ID,
        params={"document": "# Project memory", "state": '{"schema_version": 3}'},
        supplied_headers=None,
    )
    assert result == MEMORY


@patch.object(ProjectMemory, "_static_request")
def test_modify_without_state_sends_only_the_document(mock_request):
    # The endpoint keeps the stored state when the body has no state.
    mock_request.return_value = MEMORY

    ProjectMemory.modify(USER_ID, COMPANY_ID, PROJECT_ID, document="# New")

    mock_request.assert_called_once_with(
        "patch",
        URL,
        USER_ID,
        COMPANY_ID,
        params={"document": "# New"},
        supplied_headers=None,
    )


@patch.object(ProjectMemory, "_static_request")
def test_delete_removes_the_project_memory(mock_request):
    mock_request.return_value = DELETED

    result = ProjectMemory.delete(USER_ID, COMPANY_ID, PROJECT_ID)

    mock_request.assert_called_once_with(
        "delete", URL, USER_ID, COMPANY_ID, supplied_headers=None
    )
    assert result == DELETED


@patch.object(ProjectMemory, "_static_request_async", new_callable=AsyncMock)
async def test_retrieve_async_requests_the_project_memory(mock_request):
    mock_request.return_value = MEMORY

    result = await ProjectMemory.retrieve_async(USER_ID, COMPANY_ID, PROJECT_ID)

    mock_request.assert_awaited_once_with(
        "get", URL, USER_ID, COMPANY_ID, supplied_headers=None
    )
    assert result == MEMORY


@patch.object(ProjectMemory, "_static_request_async", new_callable=AsyncMock)
async def test_modify_async_patches_document_and_state(mock_request):
    mock_request.return_value = MEMORY

    result = await ProjectMemory.modify_async(
        USER_ID,
        COMPANY_ID,
        PROJECT_ID,
        document="# Project memory",
        state='{"schema_version": 3}',
    )

    mock_request.assert_awaited_once_with(
        "patch",
        URL,
        USER_ID,
        COMPANY_ID,
        params={"document": "# Project memory", "state": '{"schema_version": 3}'},
        supplied_headers=None,
    )
    assert result == MEMORY


@patch.object(ProjectMemory, "_static_request_async", new_callable=AsyncMock)
async def test_delete_async_removes_the_project_memory(mock_request):
    mock_request.return_value = DELETED

    result = await ProjectMemory.delete_async(USER_ID, COMPANY_ID, PROJECT_ID)

    mock_request.assert_awaited_once_with(
        "delete", URL, USER_ID, COMPANY_ID, supplied_headers=None
    )
    assert result == DELETED


@patch.object(ProjectMemory, "_static_request")
def test_service_id_is_sent_as_x_service_id(mock_request):
    # The endpoint is service-only: the project memory service calls it for
    # the owner and identifies itself with x-service-id.
    mock_request.return_value = MEMORY

    ProjectMemory.retrieve(USER_ID, COMPANY_ID, PROJECT_ID, service_id=SERVICE_ID)
    ProjectMemory.modify(
        USER_ID,
        COMPANY_ID,
        PROJECT_ID,
        document="# New",
        state="{}",
        service_id=SERVICE_ID,
    )
    ProjectMemory.delete(USER_ID, COMPANY_ID, PROJECT_ID, service_id=SERVICE_ID)

    calls = mock_request.call_args_list
    assert [call.args[0] for call in calls] == ["get", "patch", "delete"]
    assert all(call.args[1:] == (URL, USER_ID, COMPANY_ID) for call in calls)
    assert all(call.kwargs["supplied_headers"] == SERVICE_HEADERS for call in calls)
    assert calls[1].kwargs["params"] == {"document": "# New", "state": "{}"}


@patch.object(ProjectMemory, "_static_request_async", new_callable=AsyncMock)
async def test_service_id_is_sent_as_x_service_id_async(mock_request):
    mock_request.return_value = MEMORY

    await ProjectMemory.retrieve_async(
        USER_ID, COMPANY_ID, PROJECT_ID, service_id=SERVICE_ID
    )
    await ProjectMemory.modify_async(
        USER_ID, COMPANY_ID, PROJECT_ID, document="# New", service_id=SERVICE_ID
    )
    await ProjectMemory.delete_async(
        USER_ID, COMPANY_ID, PROJECT_ID, service_id=SERVICE_ID
    )

    calls = mock_request.await_args_list
    assert [call.args[0] for call in calls] == ["get", "patch", "delete"]
    assert all(call.kwargs["supplied_headers"] == SERVICE_HEADERS for call in calls)
    # The service id never ends up in the PATCH body.
    assert calls[1].kwargs["params"] == {"document": "# New"}


@pytest.mark.parametrize("service_id", ["", "   "])
@patch.object(ProjectMemory, "_static_request")
def test_empty_service_id_is_rejected(mock_request, service_id):
    with pytest.raises(ValueError):
        ProjectMemory.retrieve(USER_ID, COMPANY_ID, PROJECT_ID, service_id=service_id)
    with pytest.raises(ValueError):
        ProjectMemory.modify(
            USER_ID, COMPANY_ID, PROJECT_ID, document="# New", service_id=service_id
        )
    with pytest.raises(ValueError):
        ProjectMemory.delete(USER_ID, COMPANY_ID, PROJECT_ID, service_id=service_id)
    mock_request.assert_not_called()


@patch.object(ProjectMemory, "_static_request")
def test_service_id_is_keyword_only(mock_request):
    # Positional use could be confused with project_id or document.
    with pytest.raises(TypeError):
        ProjectMemory.retrieve(USER_ID, COMPANY_ID, PROJECT_ID, SERVICE_ID)  # type: ignore[misc]
    with pytest.raises(TypeError):
        ProjectMemory.delete(USER_ID, COMPANY_ID, PROJECT_ID, SERVICE_ID)  # type: ignore[misc]
    mock_request.assert_not_called()


@pytest.mark.parametrize(
    "option",
    [{"api_key": "ukey_x"}, {"api_base": "https://x"}, {"headers": {"x": "y"}}],
)
@patch.object(ProjectMemory, "_static_request")
def test_modify_rejects_request_options_instead_of_sending_them(mock_request, option):
    with pytest.raises(TypeError):
        ProjectMemory.modify(  # type: ignore[call-arg]
            USER_ID, COMPANY_ID, PROJECT_ID, document="# New", **option
        )
    mock_request.assert_not_called()


@patch.object(ProjectMemory, "_static_request_async", new_callable=AsyncMock)
async def test_modify_async_rejects_request_options(mock_request):
    with pytest.raises(TypeError):
        await ProjectMemory.modify_async(  # type: ignore[call-arg]
            USER_ID, COMPANY_ID, PROJECT_ID, document="# New", api_key="ukey_x"
        )
    mock_request.assert_not_awaited()


@patch.object(ProjectMemory, "_static_request")
def test_modify_with_state_none_keeps_the_stored_state(mock_request):
    mock_request.return_value = MEMORY

    ProjectMemory.modify(USER_ID, COMPANY_ID, PROJECT_ID, document="# New", state=None)

    mock_request.assert_called_once_with(
        "patch",
        URL,
        USER_ID,
        COMPANY_ID,
        params={"document": "# New"},
        supplied_headers=None,
    )


@patch.object(ProjectMemory, "_static_request")
def test_project_id_is_escaped_into_one_path_segment(mock_request):
    # An id with "/", ".." or "?" (e.g. supplied by an agent) must not reach
    # another endpoint such as /context-memory.
    mock_request.return_value = MEMORY
    crafted = "../../context-memory?x=1#y"
    expected = "/projects/..%2F..%2Fcontext-memory%3Fx%3D1%23y/memory"

    ProjectMemory.retrieve(USER_ID, COMPANY_ID, crafted)
    ProjectMemory.modify(USER_ID, COMPANY_ID, crafted, document="# New")
    ProjectMemory.delete(USER_ID, COMPANY_ID, crafted)

    paths = [call.args[1] for call in mock_request.call_args_list]
    assert paths == [expected, expected, expected]


@pytest.mark.parametrize("project_id", ["", ".", ".."])
@patch.object(ProjectMemory, "_static_request")
def test_dot_only_or_empty_project_ids_are_rejected(mock_request, project_id):
    # quote() leaves "." and ".." as they are and HTTP clients collapse them
    # (/projects/../memory -> /memory), so these never reach the network.
    with pytest.raises(ValueError):
        ProjectMemory.retrieve(USER_ID, COMPANY_ID, project_id)
    with pytest.raises(ValueError):
        ProjectMemory.modify(USER_ID, COMPANY_ID, project_id, document="# New")
    with pytest.raises(ValueError):
        ProjectMemory.delete(USER_ID, COMPANY_ID, project_id)
    mock_request.assert_not_called()


@pytest.mark.parametrize("project_id", ["", ".", ".."])
@patch.object(ProjectMemory, "_static_request_async", new_callable=AsyncMock)
async def test_dot_only_or_empty_project_ids_are_rejected_async(
    mock_request, project_id
):
    with pytest.raises(ValueError):
        await ProjectMemory.retrieve_async(USER_ID, COMPANY_ID, project_id)
    with pytest.raises(ValueError):
        await ProjectMemory.modify_async(
            USER_ID, COMPANY_ID, project_id, document="# New"
        )
    with pytest.raises(ValueError):
        await ProjectMemory.delete_async(USER_ID, COMPANY_ID, project_id)
    mock_request.assert_not_awaited()


@patch.object(ProjectMemory, "_static_request")
def test_ids_that_only_contain_dots_are_still_allowed(mock_request):
    mock_request.return_value = MEMORY

    ProjectMemory.retrieve(USER_ID, COMPANY_ID, "a.b")
    ProjectMemory.retrieve(USER_ID, COMPANY_ID, "..x")

    paths = [call.args[1] for call in mock_request.call_args_list]
    assert paths == ["/projects/a.b/memory", "/projects/..x/memory"]
