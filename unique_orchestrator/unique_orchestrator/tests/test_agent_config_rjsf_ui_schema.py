from humps import camelize
from unique_toolkit._common.pydantic.rjsf_tags import ui_schema_for_model

from unique_orchestrator.config import UniqueAIAgentConfig


def _nested_get(data: dict, path: str) -> object:
    current: object = data
    for part in path.split("."):
        assert isinstance(current, dict)
        current = current[part]
    return current


def test_unique_ai_agent_config__prompt_fields__textarea_widgets() -> None:
    ui_schema = ui_schema_for_model(UniqueAIAgentConfig, key_transform=camelize)
    assert _nested_get(ui_schema, "promptConfig.systemPromptTemplate") == {
        "ui:widget": "textarea",
        "ui:disabled": False,
        "ui:readonly": False,
        "ui:options": {"rows": 25},
        "ui:emptyValue": "",
    }
    assert _nested_get(ui_schema, "promptConfig.userMessagePromptTemplate") == {
        "ui:widget": "textarea",
        "ui:disabled": False,
        "ui:readonly": False,
        "ui:options": {"rows": 4},
        "ui:emptyValue": "",
    }
    assert _nested_get(ui_schema, "services.followUpQuestionsConfig.userPrompt") == {
        "ui:widget": "textarea",
        "ui:disabled": False,
        "ui:readonly": False,
        "ui:options": {"rows": 10},
        "ui:emptyValue": "",
    }
    assert _nested_get(ui_schema, "services.followUpQuestionsConfig.systemPrompt") == {
        "ui:widget": "textarea",
        "ui:disabled": False,
        "ui:readonly": False,
        "ui:options": {"rows": 15},
        "ui:emptyValue": "",
    }
    assert _nested_get(
        ui_schema, "services.followUpQuestionsConfig.suggestionsFormat"
    ) == {
        "ui:widget": "textarea",
        "ui:disabled": False,
        "ui:readonly": False,
        "ui:options": {"rows": 8},
        "ui:emptyValue": "",
    }
