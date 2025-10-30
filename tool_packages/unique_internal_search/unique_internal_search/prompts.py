DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT = (
    "You can use the InternalSearch tool to access internal company documentations, including information on policies, procedures, benefits, groups, financial details, and specific individuals. "
    "If this tool can help answer your question, feel free to use it to search the internal knowledge base for more information. "
    "If possible always try to get information from the internal knowledge base with the InternalSearch tool before using other tools.\n"
    "Use cases for the Internal Knowledge Search are:\n"
    "- User asks to work with a document: Most likely the document is uploaded to the chat and mentioned in a message and can be loaded with this tool\n"
    "- Policy and Procedure Verification: Use the internal search tool to find the most current company policies, procedures, or guidelines to ensure compliance and accuracy in responses.\n"
    "- Project-Specific Information: When answering questions related to ongoing projects or initiatives, use the internal search to access project documents, reports, or meeting notes for precise details.\n"
    "- Employee Directory and Contact Information: Utilize the internal search to locate contact details or organizational charts to facilitate communication and collaboration within the company.\n"
    "- Confidential and Proprietary Information: When dealing with sensitive topics that require proprietary knowledge or confidential data, use the internal search to ensure the information is sourced from secure and authorized company documents.\n\n"
    "**Instruction Query Splitting**\n"
    'You should split the user question into multiple search strings when the user\'s question needs to be decomposed / rewritten to find different facts. Perform for each search string an individual tool call. Avoid short queries that are extremely broad and will return unrelated results. Strip the search string of any extraneous details, e.g. instructions or unnecessary context. However, you must fill in relevant context from the rest of the conversation to make the question complete. E.g. "What was their age?" => "What was Kevin\'s age?" because the preceding conversation makes it clear that the user is talking about Kevin.\n\n'
    "Here are some examples of how to use the InternalSearch tool:\n"
    'User: What was the GDP of France and Italy in the 1970s? => search strings: ["france gdp 1970", "italy gdp 1970"] # Splitting of the query into 2 queries and perform 2 tool calls\n'
    'User: What does the report say about the GPT4 performance on MMLU? => search strings: ["GPT4 performance on MMLU?"] # Simplify the query'
)

DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT = (
    "Whenever you use information retrieved with the InternalSearch, you must adhere to strict reference guidelines. "
    "You must strictly reference each fact used with the `source_number` of the corresponding passage, in the following format: '[source<source_number>]'.\n\n"
    "Example:\n"
    "- The stock price of Apple Inc. is $150 [source0] and the company's revenue increased by 10% [source1].\n"
    "- Moreover, the company's market capitalization is $2 trillion [source2][source3].\n"
    "- Our internal documents tell us to invest[source4] (Internal)\n\n"
    "A fact is preferably referenced by ONLY ONE source, e.g [sourceX], which should be the most relevant source for the fact.\n"
    "Follow these guidelines closely and be sure to use the proper `source_number` when referencing facts.\n"
    "Make sure that your reference follow the format [sourceX] and that the source number is correct.\n"
    "Source is written in singular form and the number is written in digits.\n\n"
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

DEFAULT_TOOL_DESCRIPTION = (
    "Search in the company knowledge base for information on policies, procedures, benefits, groups, financial information or specific people. "
    "This should be your go-to tool if no other tools are applicable."
)
DEFAULT_SEARCH_STRING_PARAM_DESCRIPTION = "An expanded term that is optimized for vector and full text search based on the users query it must be in english."

DEFAULT_LANGUAGE_PARAM_DESCRIPTION = "The language that the user wrote the query in"
