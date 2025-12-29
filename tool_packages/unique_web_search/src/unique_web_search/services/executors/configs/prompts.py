_DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_V1 = """Use the `WebSearch` tool to access up-to-date information from the web or when responding to the user requires information about their location. Some examples of when to use the `WebSearch` tool include:
- Local Information: Use the `WebSearch` tool to respond to questions that require information about the user's location, such as the weather, local businesses, or events.
- Freshness: If up-to-date information on a topic could potentially change or enhance the answer, call the `WebSearch` tool any time you would otherwise refuse to answer a question because your knowledge might be out of date.
- Niche Information: If the answer would benefit from detailed information not widely known or understood (which might be found on the internet), such as details about a small neighborhood, a less well-known company, or arcane regulations, use web sources directly rather than relying on the distilled knowledge from pretraining.
- Accuracy: If the cost of a small mistake or outdated information is high (e.g., using an outdated version of a software library or not knowing the date of the next game for a sports team), then use the `WebSearch` tool.

### Instruction Query Splitting
You should split the user question into multiple queries when the user's question needs to be decomposed / rewritten to find different facts. Perform for each query an individual tool call. Avoid short queries that are extremely broad and will return unrelated results. Strip the search string of any extraneous details, e.g. instructions or unnecessary context. However, you must fill in relevant context from the rest of the conversation to make the question complete. E.g. "What was their age?" => "What was Kevin's age?" because the preceding conversation makes it clear that the user is talking about Kevin.

Here are some examples of how to use the WebSearch tool:
User: What was the GDP of France and Italy in the 1970s? => queries: ["france gdp 1970", "italy gdp 1970"] # Splitting of the query into 2 queries and perform 2 tool calls
User: What does the report say about the GPT4 performance on MMLU? => queries: ["GPT4 performance on MMLU?"] # Simplify the query"""

_DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_V2 = """Use the `WebSearch` tool to access up-to-date information from the web when your knowledge might be insufficient, outdated, or when the user's query requires current information. This tool uses a structured planning approach to conduct comprehensive research.

### When to Use WebSearch

**Required Usage Scenarios:**
- **Current Events & News**: Any topic that changes frequently or requires the latest information
- **Local Information**: Weather, local businesses, events, or location-specific queries
- **Real-time Data**: Stock prices, sports scores, breaking news, or live updates  
- **Recent Developments**: Software updates, policy changes, or recent announcements
- **Niche/Specialized Information**: Details about specific companies, products, or technical specifications not widely known
- **Fact Verification**: When accuracy is critical and outdated information could be harmful

**Quality Indicators for Usage:**
- **Freshness**: If up-to-date information could potentially change or enhance the answer
- **Accuracy**: When the cost of outdated information is high (e.g., software versions, dates, regulations)
- **Completeness**: When detailed information not in your training data would improve the response

**Maximum Number of Steps:**
The web search should not exceed $max_steps steps.

### Tool Parameters

The WebSearch tool uses a structured planning approach with the following schema:

```json
{
  "objective": "Clear statement of what you're trying to accomplish",
  "query_analysis": "Analysis of what information is needed and why",
  "steps": [
    {
      "step_type": "search", // or "read_url"
      "objective": "Specific goal for this step",
      "query_or_url": "optimized search query or specific URL"
    }
  ],
  "expected_outcome": "What you expect to find and how it will help"
}
```

### Research Planning Strategy

**1. Define Clear Objective:**
- State exactly what information you need to accomplish
- Be specific about the scope and purpose of your research
- Example: "Find current stock price and recent performance data for Apple Inc."

**2. Analyze Information Requirements:**
- Break down what types of information are needed
- Identify potential sources and search strategies
- Consider what might be missing from your current knowledge
- Example: "Need current stock price, quarterly performance, and any recent news affecting the stock"

**3. Plan Sequential Steps:**
- Create logical sequence of searches and URL reads
- Each step should build toward the overall objective
- Consider dependencies between steps
- Balance breadth vs. depth of information gathering

**4. Set Expected Outcomes:**
- Specify what each step should accomplish
- Define success criteria for the research plan
- Anticipate how the information will be used

### Step Types and Optimization

**Search Steps (`"step_type": "search"`):**
- Use for discovering information through search engines
- Optimize queries with 3-6 key words maximum
- Remove unnecessary context but preserve essential specifics
- Add context from conversation history when needed
- Example: "What was their age?" → "Kevin's age" (if Kevin was mentioned earlier)

**URL Reading Steps (`"step_type": "read_url"`):**
- Use for reading specific documents or pages found in previous searches
- Include full URLs from search results
- Useful for diving deeper into specific sources
- Good for accessing reports, documents, or detailed articles

**Query Optimization Techniques:**
- `"exact phrase"` for precise matches
- `site:domain.com` to search specific websites
- `-word` to exclude terms
- `intitle:` or `inurl:` for title/URL targeting
- `2020..2023` for date ranges
- `OR` for alternatives

### Multi-Step Research Planning

**Effective Planning Examples:**

**Simple Research Plan:**
```json
{
  "objective": "Get current weather information for New York City",
  "query_analysis": "Need current weather conditions, temperature, and forecast for NYC",
  "steps": [
    {
      "step_type": "search",
      "objective": "Find current weather conditions in NYC",
      "query_or_url": "New York City weather today current conditions"
    }
  ],
  "expected_outcome": "Current temperature, weather conditions, and short-term forecast for NYC"
}
```

**Complex Multi-Step Research Plan:**
```json
{
  "objective": "Research Tesla's recent financial performance and market position",
  "query_analysis": "Need latest quarterly results, stock performance, and competitive analysis to understand Tesla's current market position",
  "steps": [
    {
      "step_type": "search",
      "objective": "Find Tesla's latest quarterly earnings",
      "query_or_url": "Tesla Q3 2024 earnings results financial performance"
    },
    {
      "step_type": "search", 
      "objective": "Get current Tesla stock price and recent performance",
      "query_or_url": "Tesla stock price TSLA recent performance 2024"
    },
    {
      "step_type": "read_url",
      "objective": "Read detailed earnings report",
      "query_or_url": "[URL from previous search results]"
    }
  ],
  "expected_outcome": "Comprehensive view of Tesla's financial health, stock performance, and market position"
}
```
""".strip()

DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT = {
    "v1": _DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_V1,
    "v2": _DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_V2,
}


_DEFAULT_TOOL_DESCRIPTION_V1 = """Issues a query to a search engine and displays the results from the web.
If user provide a specific link, you should include it in the query (not only the domain)."""

_DEFAULT_TOOL_DESCRIPTION_V2 = """The WebSearch tool conducts structured web research using a planning-based approach. It searches the internet and reads specific URLs to gather current, accurate information on any topic.

## When to Use

Use WebSearch when you need:
- Current events, news, or real-time data
- Recent information that may have changed since your training
- Specific facts, statistics, or details not in your knowledge base
- Local or location-specific information
- Verification of time-sensitive information"""


DEFAULT_TOOL_DESCRIPTION = {
    "v1": _DEFAULT_TOOL_DESCRIPTION_V1,
    "v2": _DEFAULT_TOOL_DESCRIPTION_V2,
}


### V1 Specific Prompts

RESTRICT_DATE_DESCRIPTION = """
Restricts results to a recent time window. Format: `[period][number]` — `d`=days, `w`=weeks, `m`=months, `y`=years.  
Examples: `d1` (24h), `w1` (1 week), `m3` (3 months), `y1` (1 year).  
Omit for no date filter. Avoid adding date terms in the main query.
""".strip()

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
