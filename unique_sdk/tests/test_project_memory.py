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

    mock_request.assert_called_once_with("get", URL, USER_ID, COMPANY_ID)
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
    )
    assert result == MEMORY


@patch.object(ProjectMemory, "_static_request")
def test_modify_without_state_sends_only_the_document(mock_request):
    # The endpoint keeps the stored state when the body has no state.
    mock_request.return_value = MEMORY

    ProjectMemory.modify(USER_ID, COMPANY_ID, PROJECT_ID, document="# New")

    mock_request.assert_called_once_with(
        "patch", URL, USER_ID, COMPANY_ID, params={"document": "# New"}
    )


@patch.object(ProjectMemory, "_static_request")
def test_delete_removes_the_project_memory(mock_request):
    mock_request.return_value = DELETED

    result = ProjectMemory.delete(USER_ID, COMPANY_ID, PROJECT_ID)

    mock_request.assert_called_once_with("delete", URL, USER_ID, COMPANY_ID)
    assert result == DELETED


@patch.object(ProjectMemory, "_static_request_async", new_callable=AsyncMock)
async def test_retrieve_async_requests_the_project_memory(mock_request):
    mock_request.return_value = MEMORY

    result = await ProjectMemory.retrieve_async(USER_ID, COMPANY_ID, PROJECT_ID)

    mock_request.assert_awaited_once_with("get", URL, USER_ID, COMPANY_ID)
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
    )
    assert result == MEMORY


@patch.object(ProjectMemory, "_static_request_async", new_callable=AsyncMock)
async def test_delete_async_removes_the_project_memory(mock_request):
    mock_request.return_value = DELETED

    result = await ProjectMemory.delete_async(USER_ID, COMPANY_ID, PROJECT_ID)

    mock_request.assert_awaited_once_with("delete", URL, USER_ID, COMPANY_ID)
    assert result == DELETED


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
        "patch", URL, USER_ID, COMPANY_ID, params={"document": "# New"}
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
