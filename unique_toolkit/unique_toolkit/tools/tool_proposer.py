# %%
import json
from pathlib import Path

import jinja2
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition

from unique_toolkit.framework_utilities.openai.client import (
    UniqueSettings,
    get_openai_client,
)
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)

settings = UniqueSettings.from_env(Path(__file__).parent / ".env.api_key")

client = get_openai_client(settings)

hr_ticket_creator_tool_description = """
Create a ticket for a given issue. 
Useful when the user needs help to fullfill a task and feels blocked.
The `hr_ticket_creator` tool will create a ticket in the HR system.

Examples where this tool can help: 
- "How can I get my batch number?"
- "How can I get information about my salary for my taxes?"
- "How much time can I take time off if my kid is sick?"
"""

access_request_ticket_creator_tool_description = """
Create a ticket for a given issue. 
Useful when the user needs help to fullfill a technicaltask and feels blocked.
The `access_request_ticket_creator` tool will create a ticket in the Jira system.

Examples where this tool can help: 
- "I need access to a this <this> git repository"
- "I cannot reach this internal webpage"
- "I cannot use the Slack app anymore
"""

tool_proposer_dict = {
    "hr_ticket_creator": hr_ticket_creator_tool_description,
    "access_request_ticket_creator": access_request_ticket_creator_tool_description,
}

# TODO: move jinja template to a separate file
tool_description = jinja2.Template("""
The tool proposer can be used to propose a utility used in the
next chat completion.

You can propose the following tools:

{% for tool_name, tool_description in tool_proposer_dict.items() %}
---
**{{ tool_name }}**: {{ tool_description }}
---
{% endfor %}

""").render(tool_proposer_dict=tool_proposer_dict)

print(tool_description)

# %%


tool_proposer_tool_description = ChatCompletionToolParam(
    function=FunctionDefinition(
        name="tool_proposer",
        description=tool_description,
        parameters={
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "The name of the tool to use as seent in the description",
                    "enum": list(tool_proposer_dict.keys()),
                },
            },
            "required": ["tool_name"],
            "additionalProperties": False,
        },
        strict=True,
    ),
    type="function",
)

messages = (
    OpenAIMessageBuilder()
    .append_system_message(
        content="You are a helpful assistant that can propose tools to use in the next chat completion."
    )
    .append_user_message(
        content="Can you please provide me with the process and requirements for requesting paid time off?"
    )
    .messages
)


completion = client.chat.completions.create(
    model="AZURE_GPT_4o_2024_0806",
    messages=messages,
    tools=[tool_proposer_tool_description],
)


# %%

proposed_tools = set()

if completion.choices[0].message.tool_calls:
    for tool_call in completion.choices[0].message.tool_calls:
        if tool_call.function.name == "tool_proposer":
            tool_args = json.loads(tool_call.function.arguments)
            proposed_tools.add(tool_args["tool_name"])

    print(f"Proposed tools: {proposed_tools}")

else:
    print("No tool calls found")

# %%
# TODO: move jinja template to a separate file
tool_proposer_assistant_message = jinja2.Template("""
Hey, I think one of the following tools can help you:

{% for tool_name in proposed_tools %}
- **{{ tool_name }}**: {{ tool_proposer_dict[tool_name] }}
{% endfor %}

Please select the tools you want to use and confirm your choice
by sending the prompt added to the input field.
""").render(proposed_tools=proposed_tools, tool_proposer_dict=tool_proposer_dict)

print(tool_proposer_assistant_message)


# %%
completion.choices[0].message.content
# %%
