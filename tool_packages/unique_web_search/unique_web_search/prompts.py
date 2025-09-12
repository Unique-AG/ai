DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT = (
    "Use the `WebSearch` tool to access up-to-date information from the web or when responding to the user requires information about their location. Some examples of when to use the `WebSearch` tool include:\n"
    "- Local Information: Use the `WebSearch` tool to respond to questions that require information about the user's location, such as the weather, local businesses, or events.\n"
    "- Freshness: If up-to-date information on a topic could potentially change or enhance the answer, call the `WebSearch` tool any time you would otherwise refuse to answer a question because your knowledge might be out of date.\n"
    "- Niche Information: If the answer would benefit from detailed information not widely known or understood (which might be found on the internet), such as details about a small neighborhood, a less well-known company, or arcane regulations, use web sources directly rather than relying on the distilled knowledge from pretraining.\n"
    "- Accuracy: If the cost of a small mistake or outdated information is high (e.g., using an outdated version of a software library or not knowing the date of the next game for a sports team), then use the `WebSearch` tool.\n\n"
    "**Instruction Query Splitting**\n"
    'You should split the user question into multiple queries when the user\'s question needs to be decomposed / rewritten to find different facts. Perform for each query an individual tool call. Avoid short queries that are extremely broad and will return unrelated results. Strip the search string of any extraneous details, e.g. instructions or unnecessary context. However, you must fill in relevant context from the rest of the conversation to make the question complete. E.g. "What was their age?" => "What was Kevin\'s age?" because the preceding conversation makes it clear that the user is talking about Kevin.\n\n'
    "Here are some examples of how to use the WebSearch tool:\n"
    'User: What was the GDP of France and Italy in the 1970s? => queries: ["france gdp 1970", "italy gdp 1970"] # Splitting of the query into 2 queries and perform 2 tool calls\n'
    'User: What does the report say about the GPT4 performance on MMLU? => queries: ["GPT4 performance on MMLU?"] # Simplify the query'
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
    "BE AWARE:All tool calls have been filtered to remove uncited sources. Tool calls return much more data than you see.\n\n"
    "### Web Search Answering Protocol for Employee Questions\n"
    "When using web search to assist employees, follow\n"
    "this structured approach to ensure accurate,\n"
    "well-sourced, and relevant responses:\n\n"
    "#### 1. Evaluate and Prioritize Web Sources\n"
    "Give strong preference to:\n"
    "- **Top-ranked results**, especially the first 3–5\n"
    "- **Reliable sources**, such as:\n"
    "  - Established news organizations\n"
    "  - Academic institutions\n"
    "  - Government websites\n"
    "  - Recognized industry authorities\n"
    "- **Recent content**, particularly when the topic requires up-to-date information\n"
    "- **Primary sources** over summaries or interpretations\n\n"
    "#### 2. Source Reliability Guidelines\n"
    "- Give **highest weight** to:\n"
    "  - Peer-reviewed publications\n"
    "  - Trusted media (e.g., *BBC*, *Reuters*, *The New York Times*)\n"
    "  - Official or governmental resources\n"
    "- Be cautious with:\n"
    "  - Blogs, forums, or unaudited websites\n"
    "- Recognize and prioritize **domain expertise** (e.g., medical content from healthcare institutions)\n"
    "- Always consider the **recency** and **relevance** of the content\n\n"
    "#### 3. Acknowledge Limitations\n"
    "- If the search results do not confidently answer the question, **clearly state** this limitation."
)

DEFAULT_TOOL_DESCRIPTION = (
    "Issues a query to a search engine and displays the results from the web. "
    "If user provide a specific link, you should include it in the query (not only the domain)."
)

RESTRICT_DATE_DESCRIPTION = """
Restricts results to a recent time window. Format: `[period][number]` — `d`=days, `w`=weeks, `m`=months, `y`=years.  
Examples: `d1` (24h), `w1` (1 week), `m3` (3 months), `y1` (1 year).  
Omit for no date filter. Avoid adding date terms in the main query.
"""

REFINE_QUERY_SYSTEM_PROMPT = """
You're task consist of a query for a search engine.

** Refine the query Guidelines **
- The query should be a string that does not exceed 6 key words.
- Never include temporal information in the refined query. There is a separate field for this purpose.
- You may add the additional advanced syntax when relevant to refine the results:
- Use quotes `"..."` for exact words (avoid doing it for phrases as it will dramatically reduce the number of results).
- Use `-word` to exclude terms.
- Use `site:domain.com` to restrict to a site.
- Use `intitle:`, `inurl:` to target title/URL.
- Use `OR` for alternatives, `*` as a wildcard.
- Use `..` for number ranges (e.g., 2010..2020).
- Use `AROUND(N)` to find terms close together.
- Use `define:word` for definitions.
- Combine operators for powerful filtering.

** IMPORTANT **
- You should not use any date restriction in the refined query.
""".strip()
