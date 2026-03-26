import pytest

from tests.test_obj_factory import get_event_obj
from unique_toolkit.agentic.tools.experimental.open_file_tool import OpenFileTool
from unique_toolkit.language_model.schemas import LanguageModelFunction


@pytest.fixture
def event():
    return get_event_obj(
        user_id="user_1",
        company_id="company_1",
        assistant_id="assistant_1",
        chat_id="chat_1",
    )


@pytest.fixture
def registry():
    return []


@pytest.fixture
def tool(event, registry):
    return OpenFileTool(event=event, registry=registry)


async def test_open_file_tool__run__adds_content_ids_to_registry(tool, registry):
    call = LanguageModelFunction(
        id="call_1",
        name="OpenFile",
        arguments={"content_ids": ["cont_abc", "cont_def"]},
    )

    response = await tool.run(call)

    assert registry == ["cont_abc", "cont_def"]
    assert "Added" in response.content
    assert not response.error_message


async def test_open_file_tool__run__deduplicates_ids(tool, registry):
    registry.append("cont_abc")

    call = LanguageModelFunction(
        id="call_1",
        name="OpenFile",
        arguments={"content_ids": ["cont_abc", "cont_new"]},
    )

    response = await tool.run(call)

    assert registry == ["cont_abc", "cont_new"]
    assert "Already registered" in response.content
    assert "Added" in response.content


async def test_open_file_tool__run__rejects_empty_list(tool, registry):
    call = LanguageModelFunction(
        id="call_1",
        name="OpenFile",
        arguments={"content_ids": []},
    )

    response = await tool.run(call)

    assert response.error_message is not None
    assert "non-empty" in response.error_message
    assert registry == []


async def test_open_file_tool__run__rejects_invalid_ids(tool, registry):
    call = LanguageModelFunction(
        id="call_1",
        name="OpenFile",
        arguments={"content_ids": ["invalid_id", "cont_ok"]},
    )

    response = await tool.run(call)

    assert response.error_message is not None
    assert "invalid_id" in response.error_message
    assert registry == []


async def test_open_file_tool__run__handles_missing_arguments(tool, registry):
    call = LanguageModelFunction(
        id="call_1",
        name="OpenFile",
        arguments={},
    )

    response = await tool.run(call)

    assert response.error_message is not None
    assert registry == []


def test_open_file_tool__evaluation_check_list__returns_empty(tool):
    assert tool.evaluation_check_list() == []


def test_open_file_tool__tool_description__has_correct_name(tool):
    desc = tool.tool_description()
    assert desc.name == "OpenFile"
    assert "content_ids" in str(desc.parameters)


def test_open_file_tool__display_name__returns_open_file(tool):
    assert tool.display_name() == "Open File"
