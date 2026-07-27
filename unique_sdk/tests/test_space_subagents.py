from unittest.mock import patch

from unique_sdk.api_resources._space import Space


def test_create_space_forwards_sub_agent_fields() -> None:
    sub_agent_settings = {
        "icon": "sparkle",
        "name": "researcher",
        "displayName": "Researcher",
        "selectionPolicy": "AUTO",
        "isUserInitiatedOnly": None,
        "isExclusive": False,
        "configuration": {"depth": "high"},
    }

    with patch.object(
        Space, "_static_request", return_value={"id": "assistant_sub"}
    ) as request:
        Space.create_space(
            user_id="user_1",
            company_id="company_1",
            name="Research sub-agent",
            fallbackModule="module_1",
            modules=[],
            isSubAgent=True,
            subAgentSettings=sub_agent_settings,
            subAgentIds=["assistant_sub_1", "assistant_sub_2"],
        )

    request.assert_called_once_with(
        "post",
        "/space",
        "user_1",
        "company_1",
        params={
            "name": "Research sub-agent",
            "fallbackModule": "module_1",
            "modules": [],
            "isSubAgent": True,
            "subAgentSettings": sub_agent_settings,
            "subAgentIds": ["assistant_sub_1", "assistant_sub_2"],
        },
        client=None,
    )


def test_create_space_forwards_sub_agent_ids() -> None:
    with patch.object(
        Space, "_static_request", return_value={"id": "assistant_parent"}
    ) as request:
        Space.create_space(
            user_id="user_1",
            company_id="company_1",
            name="Parent assistant",
            fallbackModule="module_1",
            modules=[],
            subAgentIds=["assistant_sub_1", "assistant_sub_2"],
        )

    assert request.call_args.kwargs["params"]["subAgentIds"] == [
        "assistant_sub_1",
        "assistant_sub_2",
    ]


def test_update_space_forwards_sub_agent_fields() -> None:
    sub_agent_settings = {
        "icon": "sparkle",
        "name": "researcher",
        "displayName": "Researcher",
        "selectionPolicy": "MANUAL",
        "isUserInitiatedOnly": True,
        "isExclusive": True,
        "configuration": {"depth": "medium"},
    }

    with patch.object(
        Space, "_static_request", return_value={"id": "assistant_sub"}
    ) as request:
        Space.update_space(
            user_id="user_1",
            company_id="company_1",
            space_id="assistant_sub",
            isSubAgent=True,
            subAgentSettings=sub_agent_settings,
            subAgentIds=["assistant_sub_1", "assistant_sub_2"],
        )

    request.assert_called_once_with(
        "patch",
        "/space/assistant_sub",
        "user_1",
        "company_1",
        params={
            "isSubAgent": True,
            "subAgentSettings": sub_agent_settings,
            "subAgentIds": ["assistant_sub_1", "assistant_sub_2"],
        },
        client=None,
    )


def test_update_space_forwards_replacement_sub_agent_ids() -> None:
    with patch.object(
        Space, "_static_request", return_value={"id": "assistant_parent"}
    ) as request:
        Space.update_space(
            user_id="user_1",
            company_id="company_1",
            space_id="assistant_parent",
            subAgentIds=["assistant_sub_2"],
        )

    assert request.call_args.kwargs["params"]["subAgentIds"] == ["assistant_sub_2"]


def test_update_space_forwards_empty_sub_agent_ids() -> None:
    with patch.object(
        Space, "_static_request", return_value={"id": "assistant_parent"}
    ) as request:
        Space.update_space(
            user_id="user_1",
            company_id="company_1",
            space_id="assistant_parent",
            subAgentIds=[],
        )

    assert request.call_args.kwargs["params"]["subAgentIds"] == []


def test_get_space_returns_sub_agents_from_response() -> None:
    response = {
        "id": "assistant_parent",
        "name": "Parent assistant",
        "isSubAgent": False,
        "subAgentSettings": None,
        "subAgents": [
            {
                "id": "assistant_sub",
                "name": "Researcher",
                "title": None,
                "subtitle": None,
                "explanation": "Research helper",
                "isSubAgent": True,
                "settingsOverride": {
                    "icon": "sparkle",
                    "name": "researcher",
                    "displayName": "Researcher",
                    "selectionPolicy": "AUTO",
                    "isUserInitiatedOnly": None,
                    "isExclusive": False,
                    "configuration": {"depth": "high"},
                },
            }
        ],
    }

    with patch.object(Space, "_static_request", return_value=response):
        space = Space.get_space(
            user_id="user_1",
            company_id="company_1",
            space_id="assistant_parent",
        )

    assert space["isSubAgent"] is False
    assert space["subAgentSettings"] is None
    assert space["subAgents"][0]["id"] == "assistant_sub"
    assert space["subAgents"][0]["settingsOverride"]["configuration"] == {
        "depth": "high"
    }


def test_get_spaces_returns_sub_agent_fields_from_response() -> None:
    response = {
        "data": [
            {
                "id": "assistant_parent",
                "name": "Parent assistant",
                "isSubAgent": False,
                "subAgentSettings": None,
                "subAgents": [],
            }
        ]
    }

    with patch.object(Space, "_static_request", return_value=response):
        spaces = Space.get_spaces(user_id="user_1", company_id="company_1")

    assert spaces["data"][0]["isSubAgent"] is False
    assert spaces["data"][0]["subAgentSettings"] is None
    assert spaces["data"][0]["subAgents"] == []


def test_get_space_allows_partial_response_without_sub_agents() -> None:
    response = {"id": "assistant_parent", "name": "Parent assistant"}

    with patch.object(Space, "_static_request", return_value=response):
        space = Space.get_space(
            user_id="user_1",
            company_id="company_1",
            space_id="assistant_parent",
        )

    assert space == response
