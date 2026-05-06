from __future__ import annotations

DEFAULT_TOOL_DESCRIPTION = (
    "PRIORITY TOOL — call FIRST before any other tool when a skill matches. "
    "Execute a skill to activate specialized capabilities and domain knowledge. "
    "When a skill matches the user's request, this is a BLOCKING REQUIREMENT: "
    "invoke the Skill tool BEFORE calling any other tool or generating any "
    "response. NEVER mention a skill without actually calling this tool."
)

DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT = (
    "Execute a skill within the main conversation.\n\n"
    "CRITICAL — Skill tool has HIGHEST PRIORITY among all tools:\n"
    "1. Before you call ANY other tool (InternalSearch, OpenFile, etc.) or "
    "generate ANY response, check if a skill matches the user's request.\n"
    "2. If a skill matches, you MUST invoke the Skill tool FIRST as your "
    "very first action. This is a BLOCKING REQUIREMENT — do not call other "
    "tools or produce text until the skill is loaded.\n"
    "3. NEVER mention a skill without actually calling the tool.\n"
    "4. Do not invoke a skill that is already active in the current turn "
    "(check for <skill_loaded> tags in the conversation).\n"
    "5. After the skill is loaded, follow its instructions directly. The "
    "skill may tell you to call other tools (e.g. InternalSearch) as part "
    "of its workflow — that is expected.\n\n"
    "Important:\n"
    "- Available skills are listed in system-reminder messages in the "
    "conversation. The listing is refreshed every turn — do not rely on a "
    "name unless it appears in the most recent reminder.\n"
    "- The skill description in the listing is a summary. The full "
    "instructions are injected into the conversation only after you invoke "
    "the tool.\n\n"
    "How to invoke:\n"
    '- name: "analyze-data" — invoke a skill by name\n'
    '- name: "summarize", arguments: "focus on key metrics" — invoke with arguments'
)

DEFAULT_TOOL_DESCRIPTION_FOR_USER_PROMPT = ""

DEFAULT_TOOL_SYSTEM_REMINDER_FOR_USER_MESSAGE = (
    "<system-reminder>\n"
    "The following skills are available. Use the Skill tool to invoke them.\n"
    "\n"
    "{{ skill_list }}\n"
    "</system-reminder>"
)

DEFAULT_TOOL_PARAMETER_SKILL_NAME_DESCRIPTION = (
    "The name of the skill to invoke. Must be one of the available skills."
)

DEFAULT_TOOL_PARAMETER_ARGUMENTS_DESCRIPTION = (
    "Optional arguments or context to pass to the skill."
)
