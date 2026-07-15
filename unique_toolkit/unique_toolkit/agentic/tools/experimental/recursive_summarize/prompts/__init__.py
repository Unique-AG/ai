from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def _load(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text().strip()


MAP_SYSTEM_PROMPT = _load("map_system.j2")
MAP_USER_TEMPLATE = _load("map_user.j2")
REDUCE_SYSTEM_PROMPT = _load("reduce_system.j2")
REDUCE_USER_TEMPLATE = _load("reduce_user.j2")

TOOL_DESCRIPTION_TEMPLATE = (
    "Summarize a document that may exceed the model context window. Use when the user "
    "asks to summarize a file. Call this tool ONCE PER FILE. "
    "For a file uploaded to this chat, pass its file_name; when several files are "
    "uploaded, make a separate call for each one. "
    "For a file that lives in the knowledge base (not uploaded to this chat), first run "
    "internal search to locate it, then pass the content_id from the best-matching "
    "result instead of file_name. "
    "Provide a clear task_description describing what to focus on in the summary."
)

SYSTEM_PROMPT_TEMPLATE = (
    "You have access to the RecursiveSummarize tool for summarizing large "
    "documents via recursive map-reduce when a single prompt would exceed the context limit. "
    "Call it when the user requests a summary of a document. "
    "Summarize one file per call: for a chat-uploaded file pass that file's file_name. When "
    "the user has uploaded several files, issue one separate call per file (each runs as its "
    "own step) rather than one combined call. "
    "When the user asks to summarize a file that is in the knowledge base rather than uploaded "
    "to this chat, first use internal search to find it, then call RecursiveSummarize with the "
    "content_id taken from the best-matching search result. "
    "RecursiveSummarize returns the draft summary in the tool `content` field plus compact "
    "source metadata for citations — not a finished user-facing answer. You MUST present "
    "that summary to the user with [sourceN] on every factual claim. Never reply with an "
    "uncited summary. Never use document filenames or page numbers in prose "
    "(e.g. [report.pdf, p. 5])."
)

# Copied from unique_internal_search.prompts
# DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT (tool name adjusted).
TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT_TEMPLATE = (
    "Whenever you use information retrieved with the RecursiveSummarize, you must adhere to strict reference guidelines. "
    "You must strictly reference each fact used with the `source_number` of the corresponding passage, in the following format: '[source<source_number>]'.\n\n"
    "Example:\n"
    "- The stock price of Apple Inc. is $150 [source0] and the company's revenue increased by 10% [source1].\n"
    "- Moreover, the company's market capitalization is $2 trillion [source2][source3].\n"
    "- Our internal documents tell us to invest[source4] (Internal)\n\n"
    "A fact is preferably referenced by ONLY ONE source, e.g [sourceX], which should be the most relevant source for the fact.\n"
    "Follow these guidelines closely and be sure to use the proper `source_number` when referencing facts.\n"
    "Make sure that your reference follow the format [sourceX] and that the source number is correct.\n"
    "Source is written in singular form and the number is written in digits.\n"
    "Never cite using document filenames, page numbers in prose, or patterns like [filename, p. N]. "
    "Only use [sourceX] where X is the source_number from the RecursiveSummarize tool response.\n\n"
    "IT IS VERY IMPORTANT TO FOLLOW THESE GUIDELINES!!\n"
    "NEVER CITE A source_number THAT YOU DON'T SEE IN THE TOOL CALL RESPONSE!!!\n"
    "The source_number in old assistant messages are no longer valid.\n"
    "EXAMPLE: If you see [source34] and [source35] in the assistant message, you can't use [source34] again in the next assistant message, this has to be the number you find in the message with role 'tool'.\n"
    "BE AWARE:All tool calls have been filtered to remove uncited sources. Tool calls return much more data than you see\n\n"
    "### Internal Document Answering Protocol for Employee Questions\n"
    "When assisting employees using internal documents, follow\n"
    "this structured approach to ensure precise, well-grounded,\n"
    "and context-aware responses:\n\n"
    "#### 1. Locate and Prioritize Relevant Internal Sources\n"
    "Give strong preference to:\n"
    "- **Most relevant documents**, such as:\n"
    "- **Documents authored by or involving** the employee or team in question\n"
    "- **Cross-validated sources**, especially when multiple documents agree\n"
    "  - Project trackers, design docs, decision logs, and OKRs\n"
    "  - Recently updated or active files\n\n"
    "#### 2. Source Reliability Guidelines\n"
    "- Prioritize information that is:\n"
    "  - **Directly written by domain experts or stakeholders**\n"
    "  - **Part of approved or finalized documentation**\n"
    "  - **Recently modified or reviewed**, if recency matters\n"
    "- Be cautious with:\n"
    "  - Outdated drafts\n"
    "  - Undocumented opinions or partial records\n\n"
    "#### 3. Acknowledge Limitations\n"
    "- If no relevant information is found, or documents conflict, clearly state this\n"
    "- Indicate where further clarification or investigation may be required"
)

# Legacy path when the summary is not placed in tool `content` (draft + citation rules).
TOOL_RESPONSE_DRAFT_SUMMARY_SECTION_TEMPLATE = """\
## Draft summary — present to the user WITH [sourceX] on every fact

RecursiveSummarize produced this draft from the document. Present this information to the user.
You MUST add [sourceX] immediately after EVERY factual claim, matching the claim to the \
source passages above by `source_number`.
Do NOT deliver this draft without citations. Do NOT use document filenames or page numbers.

{summary}"""

# Copied from unique_internal_search.prompts DEFAULT_TOOL_RESPONSE_SYSTEM_REMINDER_PROMPT
# (tool name adjusted). Enabled by default via ToolResponseSystemReminderConfig.
TOOL_RESPONSE_SYSTEM_REMINDER_PROMPT_TEMPLATE = """
## Reminder: Cite Every Fact from the Summary

The tool message `content` field contains the draft summary. Source metadata (with `source_number`) is appended below it for citations.

You MUST reference every fact you use from the summary with its `source_number` in the format [sourceX].

**Rules — no exceptions:**
1. Place [sourceX] immediately after each fact drawn from the summary.
2. Use ONLY source numbers present in THIS tool response. Previous source numbers are invalid.
3. One source per fact is preferred; use multiple only when the same fact is corroborated by several passages.
4. Never fabricate a source number. If a fact cannot be tied to a specific source, do not cite it.
5. Never state a fact from the summary without a citation — uncited facts are treated as hallucinations.
6. Never cite using document filenames or page numbers in prose (e.g. [report.pdf, p. 5]). Use [sourceX] only.

**Quick check before responding:**
- Does every claim from RecursiveSummarize have a [sourceX] citation?
- Does every [sourceX] you wrote actually appear in this tool response?

Failure to cite correctly undermines trust in your answer.
"""
