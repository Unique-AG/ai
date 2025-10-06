from pydantic import Field

from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

DEFAULT_PARAM_DESCRIPTION_SUB_AGENT_USER_MESSAGE = """
This is the message that will be sent to the sub-agent.
""".strip()

DEFAULT_FORMAT_INFORMATION_SUB_AGENT_SYSTEM_MESSAGE_TEMPLATE = """
⚠️ CRITICAL INSTRUCTION: References must always appear immediately after the fact they support.
❌ Do NOT collect, group, or move references into a list at the end.

Rules:

1. Inline placement: After every fact from {name}, immediately attach its reference(s) inline.
✅ Example:
“The stock price of Apple Inc. is $150” <sup><name>{name} 2</name>1</sup>.

2. No separate reference list: Do not place references in footnotes, bibliographies, or at the bottom.
❌ Wrong:
“The stock price of Apple Inc. is $150.”
References: <sup><name>{name} 2</name>1</sup>
✅ Correct:
“The stock price of Apple Inc. is $150” <sup><name>{name} 2</name>1</sup>.

3. Exact copy: Copy references character-for-character from {name}’s message.
Do not alter numbering, labels, or order.

4. Multiple references: If more than one reference supports a single fact, include all of them inline, in the same sentence, in the original order.
✅ Example:
“MSFT would be a good investment” <sup><name>{name} 3</name>4</sup><sup><name>{name} 3</name>8</sup>.
❌ Wrong:
“MSFT would be a good investment” <sup><name>{name} 3</name>8</sup><sup><name>{name} 3</name>4</sup>. (order changed)

5. Never at the bottom: References must always stay attached inline with the fact.
✅ Multi-fact Example (Correct):
“Tesla delivered 400,000 cars in Q2” <sup><name>{name} 4</name>2</sup>.
“Its revenue for the quarter was $24B” <sup><name>{name} 4</name>5</sup>.
“The company also expanded its Berlin factory capacity” <sup><name>{name} 4</name>7</sup>.
❌ Wrong Multi-fact Example:
“Tesla delivered 400,000 cars in Q2. Its revenue for the quarter was $24B. The company also expanded its Berlin factory capacity.”
References: <sup><name>{name} 4</name>2</sup><sup><name>{name} 4</name>5</sup><sup><name>{name} 4</name>7</sup>

6. Fact repetition: If you reuse a fact from {name}, you MUST reference it again inline with the correct format.

Reminder:
Inline = directly next to the fact, inside the same sentence or bullet.
""".strip()

DEFAULT_FORMAT_INFORMATION_FOR_USER_PROMPT = """
Rememeber to properly reference EACH fact for sub-agent {name} with the correct format INLINE.
""".strip()


class SubAgentToolConfig(BaseToolConfig):
    model_config = get_configuration_dict()

    assistant_id: str = Field(
        default="",
        description="The unique identifier of the assistant to use for the sub-agent.",
    )
    chat_id: str | None = Field(
        default=None,
        description="The chat ID to use for the sub-agent conversation. If None, a new chat will be created.",
    )
    reuse_chat: bool = Field(
        default=True,
        description="Whether to reuse the existing chat or create a new one for each sub-agent call.",
    )

    tool_description_for_system_prompt: str = Field(
        default="",
        description="Description of the tool that will be included in the system prompt.",
    )
    tool_description: str = Field(
        default="",
        description="Description of the tool that will be included in the tools sent to the model.",
    )
    param_description_sub_agent_user_message: str = Field(
        default=DEFAULT_PARAM_DESCRIPTION_SUB_AGENT_USER_MESSAGE,
        description="Description of the user message parameter that will be sent to the model.",
    )
    tool_format_information_for_system_prompt: str = Field(
        default=DEFAULT_FORMAT_INFORMATION_SUB_AGENT_SYSTEM_MESSAGE_TEMPLATE,
        description="Format information that will be included in the system prompt to guide response formatting.",
    )
    tool_description_for_user_prompt: str = Field(
        default="",
        description="Description of the tool that will be included in the user prompt.",
    )
    tool_format_information_for_user_prompt: str = Field(
        default=DEFAULT_FORMAT_INFORMATION_FOR_USER_PROMPT,
        description="Format information that will be included in the user prompt to guide response formatting.",
    )

    poll_interval: float = Field(
        default=1.0,
        description="Time interval in seconds between polling attempts when waiting for sub-agent response.",
    )
    max_wait: float = Field(
        default=120.0,
        description="Maximum time in seconds to wait for the sub-agent response before timing out.",
    )
