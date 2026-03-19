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

_DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_V3 = """Use the `WebSearch` tool to access up-to-date information from the web when your knowledge might be insufficient, outdated, or when the user's query requires current information. This mode uses a structured planning approach and pre-filters search results by relevance before fetching full pages, so only the most relevant URLs are read.

### FSI-Specific Planning Rule

When the user's question is related to the Financial Services Industry (FSI), infer the most relevant FSI domain directly from the user's question and use it to shape the search plan.

Examples of FSI domains include:
- banking
- commercial banking
- investment banking
- private banking
- asset management
- wealth management
- payments
- insurance
- capital markets
- lending
- fintech
- compliance
- risk

### Mandatory Query Generation Rules

For FSI-related questions:
- ALWAYS generate at least 5 search queries
- Query 1 must be a broad base query without any FSI domain attached
- Queries 2, 3, 4, and 5 must reuse the exact full query text from query 1 and only append explicit website domains directly inside `query_or_url`
- Do not rewrite, shorten, expand, reorder, or substitute any non-domain terms from query 1 when forming queries 2-5
- Each of queries 2-5 must include exactly 5 website domains in the query string itself
- The 5 website domains used in one follow-up query should be different from the 5 website domains used in the other follow-up queries
- Place multiple website domains as plain space-separated terms in the query string
- The FSI domain must be inferred from the user's question
- If multiple FSI domains are plausible, use the strongest candidates across queries 2-5
- The generated queries must be shown explicitly in the `steps` list inside `query_or_url`
- Do not only describe domains in prose; write the website domains directly into the query string itself

### When to Use WebSearch

**Required Usage Scenarios:**
- **Current Events & News**: Any topic that changes frequently or requires the latest information
- **Real-time Data**: Stock prices, sports scores, breaking news, or live updates
- **Recent Developments**: Software updates, policy changes, or recent announcements
- **Niche/Specialized Information**: Details about specific companies, products, vendors, or regulations not widely known
- **Fact Verification**: When accuracy is critical and outdated information could be harmful
- **FSI Research**: Any company, vendor, trend, regulation, product, workflow, or market topic connected to financial institutions

**Quality Indicators for Usage:**
- **Freshness**: If up-to-date information could potentially change or enhance the answer
- **Accuracy**: When the cost of outdated information is high
- **Completeness**: When detailed information not in your training data would improve the response
- **Domain Precision**: When the user's question should be narrowed using an inferred FSI domain

**Current Date Context:**
- The current date is {{ date_string }}
- For recent news, recent developments, current status, or time-sensitive research, actively use the current date context when forming search queries
- When useful, derive the relevant recent year or month and year directly from {{ date_string }} and include it in the search string to bias results toward fresh coverage
- Example: if {{ date_string }} is Wednesday March 18, 2026, queries like `NVIDIA news 2026`, `NVIDIA latest developments March 2026`, or `NVIDIA earnings March 2026 reuters.com bloomberg.com ft.com wsj.com cnbc.com` are appropriate when recency matters
- Do not force date terms for timeless or explicitly historical questions unless recency is part of the objective

**Maximum Number of Steps:**
The web search should not exceed {{ max_steps }} steps.

### Tool Parameters

The WebSearch tool uses a structured planning approach with the following schema:

```json
{
  "objective": "Clear statement of what you're trying to accomplish",
  "query_analysis": "Analysis of what information is needed and why, including the inferred FSI domain or candidate FSI domains",
  "steps": [
    {
      "step_type": "search",
      "objective": "Broad discovery goal",
      "query_or_url": "broad query without FSI domain"
    },
    {
      "step_type": "search",
      "objective": "FSI domain query 1",
      "query_or_url": "same base query plus 5 website domains"
    },
    {
      "step_type": "search",
      "objective": "FSI domain query 2",
      "query_or_url": "same base query plus 5 different website domains"
    },
    {
      "step_type": "search",
      "objective": "FSI domain query 3",
      "query_or_url": "same base query plus 5 different website domains"
    },
    {
      "step_type": "search",
      "objective": "FSI domain query 4",
      "query_or_url": "same base query plus 5 different website domains"
    }
  ],
  "expected_outcome": "What you expect to find and how it will help"
}
```

### Research Planning Strategy

**1. Define Clear Objective:**
- State exactly what information you need to accomplish
- Be specific about the scope and purpose of your research
- If the user question is in an FSI context, define the objective in that business context

**2. Infer the FSI Domain From the User Question:**
- Infer the most relevant FSI domain directly from the user's wording and intent
- State that inferred domain explicitly in `query_analysis`
- If the user question is broad, infer the most likely FSI interpretation rather than staying generic

**3. Generate the Query Plan:**
- ALWAYS generate at least 5 search queries
- Query 1 must be broad and must not include an FSI domain
- Queries 2-5 must reuse the same base query as query 1 and append explicit website domains
- Each of queries 2-5 must include exactly 5 website domains in the query string
- Write those website domains directly into `query_or_url`, for example `reuters.com`, `ft.com`, `bloomberg.com`, `wsj.com`, and `cnbc.com`
- Keep the inferred FSI interpretation attached together with the website domains in the query string
- Use the later queries to test the most relevant FSI interpretations of the user's question
- Keep the wording as close as possible to query 1 so that the base query stays stable while the website domains are made explicit
- For recent or time-sensitive questions, use the current date context `{{ date_string }}` and derive the relevant recent year or month and year directly from it when adding temporal cues to the generated query strings

**4. Set Expected Outcomes:**
- Specify what each step should accomplish
- Define success criteria for the research plan
- Anticipate how the information will be used

### Step Types and Optimization

**Search Steps (`"step_type": "search"`):**
- Use for discovering information through search engines
- Optimize queries with 3-8 key words maximum
- Remove unnecessary context but preserve essential specifics
- Keep the base query stable across the 5 planned searches
- Queries 2-5 must explicitly include website domains in the query string itself
- Queries 2-5 must repeat the exact full query from query 1 and only differ by the added website domains
- Each of queries 2-5 must contain exactly 5 website domains
- The 5 website domains in one query should differ from the 5 website domains in the other follow-up queries
- For FSI requests, the attached website domains are the most important variables after the first broad query
- Prefer patterns like:
  - `reuters.com ft.com bloomberg.com wsj.com cnbc.com Nvidia latest developments asset management`
  - `marketwatch.com forbes.com barrons.com morningstar.com fool.com Nvidia latest developments asset management`
  - `businessinsider.com yahoo.com investing.com seekingalpha.com nasdaq.com Nvidia latest developments asset management`
  - `theinformation.com techcrunch.com venturebeat.com wired.com economist.com Nvidia latest developments asset management`

**URL Reading Steps (`"step_type": "read_url"`):**
- Use for reading specific documents or pages found in previous searches
- Use when a highly relevant URL should be read directly after the search phase

**Query Optimization Techniques:**
- `"exact phrase"` for precise matches
- `site:domain.com` to search specific websites
- `-word` to exclude terms
- `intitle:` or `inurl:` for title/URL targeting
- `OR` for alternatives
- For FSI questions, append domain terms such as `asset management`, `wealth management`, `investment banking`, `payments`, `insurance`, `capital markets`, `banking`, `compliance`, or `risk`
- For FSI questions, append 5 explicit website domains directly in each of queries 2-5
- For FSI questions, make sure the inferred FSI wording already appears in query 1 if it should also appear in queries 2-5
- When you need to include multiple website domains in one query, write them as plain space-separated terms

### FSI Example With Nvidia

```json
{
  "objective": "Understand Nvidia's relevance in Financial Services",
  "query_analysis": "The user is asking about Nvidia in an FSI context. The strongest inferred FSI interpretation is asset management, so query 1 already includes that wording. Queries 2-5 must repeat the exact same full query text from query 1 and only append website domains directly in the search string. Each follow-up query contains 5 different website domains.",
  "steps": [
    {
      "step_type": "search",
      "objective": "Get broad FSI context on Nvidia",
      "query_or_url": "Nvidia latest developments asset management"
    },
    {
      "step_type": "search",
      "objective": "Run the exact same Nvidia query against a first set of financial and news domains",
      "query_or_url": "Nvidia latest developments asset management reuters.com ft.com bloomberg.com wsj.com cnbc.com"
    },
    {
      "step_type": "search",
      "objective": "Run the exact same Nvidia query against a second set of financial and analysis domains",
      "query_or_url": "Nvidia latest developments asset management marketwatch.com forbes.com barrons.com morningstar.com fool.com"
    },
    {
      "step_type": "search",
      "objective": "Run the exact same Nvidia query against a third set of market and investing domains",
      "query_or_url": "Nvidia latest developments asset management businessinsider.com yahoo.com investing.com seekingalpha.com nasdaq.com"
    },
    {
      "step_type": "search",
      "objective": "Run the exact same Nvidia query against a fourth set of technology and business domains",
      "query_or_url": "Nvidia latest developments asset management theinformation.com techcrunch.com venturebeat.com wired.com economist.com"
    }
  ],
  "expected_outcome": "A broad overview first, followed by four searches that repeat the exact same query text with different sets of attached website domains"
}
```
""".strip()

DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT = {
    "v1": _DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_V1,
    "v2": _DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_V2,
    "v3": _DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_V3,
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


_DEFAULT_TOOL_DESCRIPTION_V3 = """The WebSearch tool conducts structured web research using a planning-based approach. It searches the internet and reads specific URLs to gather current, accurate information on any topic.

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
    "v3": _DEFAULT_TOOL_DESCRIPTION_V3,
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
