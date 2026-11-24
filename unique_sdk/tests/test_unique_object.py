"""Tests for UniqueObject identity attributes, copying and pickling."""

import copy
import pickle
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk._list_object import ListObject
from unique_sdk._unique_object import UniqueObject
from unique_sdk._util import convert_to_unique_object
from unique_sdk.api_resources._message import Message

_USER_ID = "user-1"
_COMPANY_ID = "company-1"

_COPIERS = pytest.mark.parametrize(
    "copier", [copy.copy, copy.deepcopy], ids=["copy", "deepcopy"]
)


def _message() -> UniqueObject:
    """A message as the public API returns it, with nested debug info."""
    return convert_to_unique_object(
        {
            "id": "msg_1",
            "text": "hello",
            "debugInfo": {
                "run_stats": {
                    "ledger_cost": 0.01,
                    "ledger_usage": [{"model": "m1"}, {"model": "m2"}],
                }
            },
        },
        _USER_ID,
        _COMPANY_ID,
    )


@pytest.mark.ai
def test_init__keeps_identity_out_of_the_dict__when_constructed_directly() -> None:
    """Purpose: user_id and company_id are instance attributes, not dict items.

    Why this matters: As dict items they would look like API fields and be
    cleared by a refresh, after which reading them raises.
    Setup summary: Construct directly, assert the keys and both attributes.
    """
    obj = UniqueObject(_USER_ID, _COMPANY_ID, "obj_1")

    assert list(obj.keys()) == ["id"]
    assert obj.user_id == _USER_ID
    assert obj.company_id == _COMPANY_ID


@pytest.mark.ai
def test_refresh_from__keeps_identity__when_built_from_api_response() -> None:
    """Purpose: user_id and company_id survive the refresh in construct_from.

    Why this matters: Every object returned by the API goes through that
    refresh. Losing the identity there breaks copying, pickling and paging.
    Setup summary: Convert an API payload, assert attributes on every level.
    """
    message = _message()
    run_stats = message["debugInfo"]["run_stats"]

    assert (message.user_id, message.company_id) == (_USER_ID, _COMPANY_ID)
    assert (run_stats.user_id, run_stats.company_id) == (_USER_ID, _COMPANY_ID)
    assert list(message.keys()) == ["id", "text", "debugInfo"]
    assert list(run_stats.keys()) == ["ledger_cost", "ledger_usage"]


@pytest.mark.ai
def test_setattr__updates_identity_attribute__without_adding_a_dict_item() -> None:
    """Purpose: Assigning user_id later still does not create a dict item.

    Why this matters: A stray key would show up in copies and serialized data.
    Setup summary: Reassign both attributes, assert values and unchanged keys.
    """
    obj = UniqueObject(_USER_ID, _COMPANY_ID, "obj_1")

    obj.user_id = "user-2"
    obj.company_id = "company-2"

    assert (obj.user_id, obj.company_id) == ("user-2", "company-2")
    assert list(obj.keys()) == ["id"]


@pytest.mark.ai
@_COPIERS
def test_copy__returns_equal_object_with_same_keys__for_top_level_object(
    copier: Callable[[Any], Any],
) -> None:
    """Purpose: A top-level API object can be copied and deep-copied.

    Why this matters: Callers deep-copy responses that embed SDK objects, for
    example pydantic's model_copy(deep=True); a failure aborts the whole run.
    Setup summary: Copy an API-built message, assert equality, keys, identity.
    """
    message = _message()

    copied = copier(message)

    assert copied is not message
    assert copied == message
    assert list(copied.keys()) == list(message.keys())
    assert (copied.user_id, copied.company_id) == (_USER_ID, _COMPANY_ID)


@pytest.mark.ai
@_COPIERS
def test_copy__returns_equal_object_with_same_keys__for_nested_object(
    copier: Callable[[Any], Any],
) -> None:
    """Purpose: A nested object such as debugInfo.run_stats can be copied.

    Why this matters: Nested objects go through the same refresh as top-level
    ones, and a deep copy of a response visits every one of them.
    Setup summary: Copy the nested run_stats, assert equality, keys, identity.
    """
    run_stats = _message()["debugInfo"]["run_stats"]

    copied = copier(run_stats)

    assert copied is not run_stats
    assert copied == run_stats
    assert list(copied.keys()) == ["ledger_cost", "ledger_usage"]
    assert (copied.user_id, copied.company_id) == (_USER_ID, _COMPANY_ID)


@pytest.mark.ai
def test_deepcopy__copies_plain_dict_holding_nested_object__as_in_debug_info() -> None:
    """Purpose: A plain dict whose values are SDK objects can be deep-copied.

    Why this matters: A message's debug info reaches callers as a plain dict
    with SDK objects inside, which is exactly what the orchestrator deep-copies.
    Setup summary: Deep-copy dict(debugInfo), assert content and independence.
    """
    debug_info = dict(_message()["debugInfo"])

    copied = copy.deepcopy(debug_info)

    assert copied == debug_info
    assert copied["run_stats"] is not debug_info["run_stats"]
    assert list(copied["run_stats"].keys()) == ["ledger_cost", "ledger_usage"]


@pytest.mark.ai
@_COPIERS
def test_copy__returns_equal_items_with_same_keys__for_list_of_nested_objects(
    copier: Callable[[Any], Any],
) -> None:
    """Purpose: A list of nested objects can be copied and deep-copied.

    Why this matters: List fields such as ledger_usage hold one SDK object per
    entry, and a deep copy visits each of them.
    Setup summary: Copy the ledger_usage list, assert items, keys, identity.
    """
    ledger_usage = _message()["debugInfo"]["run_stats"]["ledger_usage"]

    copied = copier(ledger_usage)

    first, second = copied

    assert copied == ledger_usage
    assert (list(first.keys()), list(second.keys())) == (["model"], ["model"])
    assert (first.user_id, first.company_id) == (_USER_ID, _COMPANY_ID)
    assert (second.user_id, second.company_id) == (_USER_ID, _COMPANY_ID)


@pytest.mark.ai
def test_deepcopy__does_not_share_nested_objects__with_the_original() -> None:
    """Purpose: A deep copy owns its nested objects and lists.

    Why this matters: Callers mutate the copy and expect the original response
    to stay as the API returned it.
    Setup summary: Deep-copy a message, mutate the copy, assert the original.
    """
    message = _message()

    copied = copy.deepcopy(message)
    copied["debugInfo"]["run_stats"]["ledger_usage"][0]["model"] = "changed"

    assert message["debugInfo"]["run_stats"]["ledger_usage"][0]["model"] == "m1"


@pytest.mark.ai
def test_copy__shares_nested_objects__with_the_original() -> None:
    """Purpose: A shallow copy keeps the same nested objects.

    Why this matters: copy.copy must stay shallow; a silent deep copy would
    change cost and aliasing for existing callers.
    Setup summary: Shallow-copy a message, assert the nested object is shared.
    """
    message = _message()

    copied = copy.copy(message)

    assert copied["debugInfo"] is message["debugInfo"]


@pytest.mark.ai
@_COPIERS
def test_copy__keeps_only_the_id_key__for_directly_constructed_object(
    copier: Callable[[Any], Any],
) -> None:
    """Purpose: Copying an object that was never refreshed adds no keys.

    Why this matters: Identity is not response data; a copy that gains
    user_id or company_id keys no longer equals what the API returned.
    Setup summary: Copy a directly constructed object, assert keys, identity.
    """
    obj = UniqueObject(_USER_ID, _COMPANY_ID, "obj_1")

    copied = copier(obj)

    assert list(copied.keys()) == ["id"]
    assert (copied.user_id, copied.company_id) == (_USER_ID, _COMPANY_ID)


@pytest.mark.ai
@_COPIERS
def test_copy__keeps_payload_field_named_user_id__apart_from_identity(
    copier: Callable[[Any], Any],
) -> None:
    """Purpose: A response field called user_id stays a dict item on the copy.

    Why this matters: The identity attribute must not overwrite response data
    that shares its name. The field is read as an item; the attribute of the
    same name is the caller's identity.
    Setup summary: Build from a payload with user_id, copy, assert both values.
    """
    obj = convert_to_unique_object(
        {"id": "obj_1", "user_id": "payload-user"}, _USER_ID, _COMPANY_ID
    )

    copied = copier(obj)

    assert (obj["user_id"], obj.user_id) == ("payload-user", _USER_ID)
    assert (copied["user_id"], copied.user_id) == ("payload-user", _USER_ID)
    assert list(copied.keys()) == ["id", "user_id"]


@pytest.mark.ai
@_COPIERS
def test_copy__keeps_the_resource_class__for_typed_resource(
    copier: Callable[[Any], Any],
) -> None:
    """Purpose: A copy of a typed resource such as Message is still a Message.

    Why this matters: A copy that degrades to the base class loses the
    resource's methods, and dict equality does not reveal it.
    Setup summary: Build a message by its object name, copy, assert the class.
    """
    message = convert_to_unique_object(
        {"id": "msg_1", "object": "message", "text": "hello"},
        _USER_ID,
        _COMPANY_ID,
    )

    copied = copier(message)

    assert type(message) is Message
    assert type(copied) is Message
    assert copied == message


@pytest.mark.ai
@_COPIERS
def test_copy__keeps_list_behaviour__for_list_object(
    copier: Callable[[Any], Any],
) -> None:
    """Purpose: A copy of a ListObject still iterates over its data.

    Why this matters: As a base-class copy it would iterate over its dict keys
    and have no paging methods.
    Setup summary: Build a list by its object name, copy, assert class, items.
    """
    page = convert_to_unique_object(
        {"object": "list", "data": [{"id": "obj_1"}], "has_more": False},
        _USER_ID,
        _COMPANY_ID,
    )

    copied = copier(page)

    assert type(copied) is ListObject
    assert list(copied) == [{"id": "obj_1"}]
    assert len(copied) == 1


@pytest.mark.ai
def test_pickle__round_trips__for_object_built_from_api_response() -> None:
    """Purpose: An API-built object can be pickled and restored.

    Why this matters: __reduce__ reads user_id and company_id, so pickling
    depends on both surviving the refresh.
    Setup summary: Pickle and unpickle a message, assert content and identity.
    """
    message = _message()

    restored = pickle.loads(pickle.dumps(message))

    assert restored == message
    assert list(restored.keys()) == list(message.keys())
    assert (restored.user_id, restored.company_id) == (_USER_ID, _COMPANY_ID)


@pytest.mark.ai
def test_request__falls_back_to_object_identity__when_none_is_passed() -> None:
    """Purpose: _request uses the object's own identity when none is given.

    Why this matters: Without the fallback a request on an API-built object
    raises instead of being sent.
    Setup summary: Patch APIRequestor, call _request with None, assert the ids.
    """
    message = _message()

    with patch("unique_sdk.APIRequestor") as requestor_cls:
        requestor_cls.return_value.request.return_value = {"id": "msg_2"}

        result = message._request("get", "/messages/msg_2", None, None)

    requestor_cls.assert_called_once_with(user_id=_USER_ID, company_id=_COMPANY_ID)
    assert (result.user_id, result.company_id) == (_USER_ID, _COMPANY_ID)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_request_async__falls_back_to_object_identity__when_none_is_passed() -> (
    None
):
    """Purpose: _request_async uses the object's own identity when none is given.

    Why this matters: The async path has its own copy of the fallback and
    needs its own coverage.
    Setup summary: Patch APIRequestor, await _request_async, assert the ids.
    """
    message = _message()

    with patch("unique_sdk.APIRequestor") as requestor_cls:
        requestor_cls.return_value.request_async = AsyncMock(
            return_value={"id": "msg_2"}
        )

        result = await message._request_async("get", "/messages/msg_2", None, None)

    requestor_cls.assert_called_once_with(user_id=_USER_ID, company_id=_COMPANY_ID)
    assert (result.user_id, result.company_id) == (_USER_ID, _COMPANY_ID)


@pytest.mark.ai
def test_request__prefers_passed_identity__over_the_object_identity() -> None:
    """Purpose: Explicit user_id and company_id still win over the object's.

    Why this matters: Resource methods always pass the caller's identity, and
    that identity decides on whose behalf the request runs.
    Setup summary: Patch APIRequestor, call _request with ids, assert them.
    """
    message = _message()

    with patch("unique_sdk.APIRequestor") as requestor_cls:
        requestor_cls.return_value.request.return_value = {"id": "msg_2"}

        message._request("get", "/messages/msg_2", "user-2", "company-2")

    requestor_cls.assert_called_once_with(user_id="user-2", company_id="company-2")


@pytest.mark.ai
@pytest.mark.parametrize("turn_page", ["next_page", "previous_page"])
def test_paging__returns_empty_list_with_identity__when_no_more_pages(
    turn_page: str,
) -> None:
    """Purpose: Paging past the end returns an empty list, not an error.

    Why this matters: next_page and previous_page read user_id and company_id
    from a list that was built from an API response.
    Setup summary: Build a list with has_more False, turn the page, assert it.
    """
    page = ListObject.construct_from(
        {"data": [{"id": "obj_1"}], "has_more": False}, _USER_ID, _COMPANY_ID
    )

    with patch.object(ListObject, "_list", autospec=True) as list_request:
        result = getattr(page, turn_page)()

    assert result.is_empty
    assert (result.user_id, result.company_id) == (_USER_ID, _COMPANY_ID)
    list_request.assert_not_called()
