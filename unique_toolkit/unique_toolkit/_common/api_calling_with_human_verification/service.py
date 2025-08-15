import json
import urllib.parse
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from unique_toolkit import ChatService
from unique_toolkit._common.to_string import (
    dict_to_markdown_table,
    extract_dicts_from_string,
)
from unique_toolkit.app.dev_util import ChatEvent, get_event_generator, init_unique_sdk
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.client import OpenAI, get_openai_client
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class JiraTicketStatus(StrEnum):
    TO_DO = "to_do"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    IN_TEST = "in_test"
    DONE = "done"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class HumanResourcesTicketData(BaseModel):
    title: str = Field(description="The title of the ticket")
    user_story: str = Field(description="The user story of the ticket")
    status: TicketStatus = Field(description="The new status of the ticket")
    priority: Priority = Field(description="The priority of the ticket")
    detailed_description: str = Field(
        description="A detailed description of the ticket",
    )


class JiraTicketData(BaseModel):
    title: str = Field(description="The title of the ticket")
    user_story: str = Field(description="The user story of the ticket")
    labels: list[str] = Field(description="The labels of the ticket")
    status: JiraTicketStatus = Field(description="The new status of the ticket")
    priority: Priority = Field(description="The priority of the ticket")


class UserConfirmation(BaseModel):
    question: str = Field(description="The question to ask the user")
    api_to_use_data_for: str = Field(description="The API to use the data for")
    data_for_api_usage: dict[str, Any] = Field(
        description="The data to present to the user as a json object",
    )


user_confirmation_tool_description = LanguageModelToolDescription(
    name="user_confirmation_tool",
    description="""This tool is used to present the information (json) by the user.
 It will show the user and ask them for confirmation. This should be used to whenever
 you want to do an API call and you want to ensure the user has confirmed the content
 of the API call.""",
    parameters=UserConfirmation,
)


class ApiDescription(BaseModel):
    name: str = Field(description="The name of the API")
    payload: type[BaseModel] = Field(description="The data of the API")
    verification_tool_name: str = Field(
        description="The name of the verification tool the LLM should use",
    )
    verification_tool_purpose: str = Field(
        description="The description of the verification tool the LLM should use",
    )

    def to_system_prompt_part(self):
        return f"{self.name}: \n"
        f"Generate a json according to the following schema and use the `{self.verification_tool_name}` to {self.verification_tool_purpose}\n"
        f"json schema: \n {json.dumps(self.payload.model_json_schema(), indent=2)}"


class ApiCallRequest(BaseModel):
    api_name: str = Field(description="The name of the API to call")
    payload: dict[str, Any] = Field(description="The data to call the API with")


def detect_api_calls_from_user_message(user_message: str) -> list[ApiCallRequest]:
    api_calls = []
    dict_of_api_calls = extract_dicts_from_string(user_message)

    if dict_of_api_calls:
        api_calls = [
            ApiCallRequest.model_validate(api_call) for api_call in dict_of_api_calls
        ]

    return api_calls


api_descriptions = [
    ApiDescription(
        name="Human Resources Ticket",
        payload=HumanResourcesTicketData,
        verification_tool_name=user_confirmation_tool_description.name,
        verification_tool_purpose="present the data to the user and ask him for confirmation",
    ),
    ApiDescription(
        name="Jira Ticket",
        payload=JiraTicketData,
        verification_tool_name=user_confirmation_tool_description.name,
        verification_tool_purpose="present the data to the user and ask him for confirmation",
    ),
]


def human_verification_tool_call_handler(
    user_confirmation_tool_call: LanguageModelFunction,
    chat_service: ChatService,
    client: OpenAI,
    builder: OpenAIMessageBuilder,
    model: LanguageModelName = LanguageModelName.AZURE_GPT_4o_2024_1120,
):
    tool_name = ""
    data_to_present: dict[str, Any] = {}

    # Case where the data arrives as a dict
    if isinstance(user_confirmation_tool_call.arguments, dict):
        tool_name = user_confirmation_tool_call.arguments.get(
            "api_to_use_data_for",
            "",
        )
        data_to_present = user_confirmation_tool_call.arguments.get(
            "data_for_api_usage",
            {},
        )

    # Case where the data arrives as a string
    if isinstance(user_confirmation_tool_call.arguments, str):
        tool_name = json.loads(user_confirmation_tool_call.arguments).get(
            "api_to_use_data_for",
            "",
        )
        data_to_present = json.loads(user_confirmation_tool_call.arguments).get(
            "data_for_api_usage",
            {},
        )

    # Case where the data arrives as a string
    if isinstance(user_confirmation_tool_call.arguments, str):
        tool_name = json.loads(user_confirmation_tool_call.arguments).get(
            "api_to_use_data_for",
            "",
        )
        data_to_present = json.loads(user_confirmation_tool_call.arguments).get(
            "data_for_api_usage",
            {},
        )
    # Only one API call is allowed
    model_data = None
    for api_description in api_descriptions:
        if api_description.name == tool_name:
            model_data = None
            try:
                model_data = api_description.payload.model_validate(data_to_present)
            except ValidationError as v:
                print(v)

            # If the first call to the LLM fails to produce the data using structured output
            if not model_data:
                completion = client.beta.chat.completions.parse(
                    model=model,
                    messages=builder.messages,
                    response_format=api_description.payload,
                )
                model_data = completion.choices[0].message.parsed

    verified_data = model_data.model_dump() if model_data else {}

    api_call_request = ApiCallRequest(api_name=tool_name, payload=verified_data)
    markdown_table = dict_to_markdown_table(verified_data)

    button_text = "Please Confirm the above data by clicking here and sending the data in your next message"
    proposed_next_prompt = (
        "I confirm the data below \n\n\n --- \n "
        + f"{json.dumps(api_call_request.model_dump(), indent=2)}"
    )

    chat_service.create_assistant_message(
        content=f"I would like to call the {tool_name} tool with the following data: \n {markdown_table} \n\n "
        f"[{button_text}](https://prompt={urllib.parse.quote(proposed_next_prompt)})",
        set_completed_at=True,
    )


if __name__ == "__main__":
    unique_settings = UniqueSettings.from_env(
        env_file=Path(__file__).parent.parent.parent.parent / "notebooks" / ".env.test",
    )
    init_unique_sdk(unique_settings=unique_settings)

    model = LanguageModelName.AZURE_GPT_4o_2024_1120
    client = get_openai_client(unique_settings)

    for event in get_event_generator(
        unique_settings=unique_settings, event_type=ChatEvent
    ):
        chat_service = ChatService(event)

        # Request build up

        api_descriptions_text = "\n".join(
            [
                api_description.to_system_prompt_part()
                for api_description in api_descriptions
            ]
        )

        builder = OpenAIMessageBuilder().system_message_append(
            "You are a helpful assistant"
            "You have access to the following APIs: \n"
            f"{api_descriptions_text}"
            "You can use the following tool to request the user for an approval for the API call: \n"
            f" {user_confirmation_tool_description}",
            "You can only ask a request for approval for a single API call at a time. ",
        )

        for m in [m.to_openai_param() for m in chat_service.get_full_history()]:
            builder.append(m)

        builder.user_message_append(
            event.payload.user_message.text,
        )

        api_calls = detect_api_calls_from_user_message(event.payload.user_message.text)

        for api_call in api_calls:
            print(api_call)

            # TODO: replace with the actual API call
            data = {"ticket_id": "123456"}
            builder.assistant_message_append(
                f"The following API has been called: {api_call.api_name}\n"
                f"with the following data: \n {dict_to_markdown_table(api_call.payload)}\n"
                f"the result of the API call is: \n {json.dumps(data, indent=2)}",
            ).user_message_append(content="Good to hear.")

        response = chat_service.complete_with_references(
            messages=builder.messages,
            model_name=model,
            tools=[user_confirmation_tool_description],
        )

        if response.tool_calls:
            # Deal with the user confirmation tool call
            if response.tool_calls[0].name == "user_confirmation_tool":
                user_confirmation_tool_call = response.tool_calls[0]

                human_verification_tool_call_handler(
                    user_confirmation_tool_call=user_confirmation_tool_call,
                    chat_service=chat_service,
                    client=client,
                    model=model,
                    builder=builder,
                )
        print(response.tool_calls)
