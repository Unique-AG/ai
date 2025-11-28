# Search Engine Documentation

This directory contains implementations for various web search engines. Each search engine implements the `SearchEngine` base class and provides a consistent interface for performing web searches.

## Table of Contents

- [Overview](#overview)
- [Available Search Engines](#available-search-engines)
  - [Google Search](#google-search)
  - [Bing Search](#bing-search)
  - [Brave Search](#brave-search)
  - [Tavily Search](#tavily-search)
  - [Jina Search](#jina-search)
  - [Firecrawl Search](#firecrawl-search)
  - [VertexAI Search](#vertexai-search)
  - [Custom API Search](#custom-api-search)
- [Common Configuration](#common-configuration)
- [Choosing a Search Engine](#choosing-a-search-engine)

## Overview

Each search engine returns results in the standard `WebSearchResult` format:

```python
class WebSearchResult(BaseModel):
    url: str
    title: str
    snippet: str
    content: str
```

All search engines implement the following interface:

```python
class SearchEngine[Config]:
    config: Config
    is_configured: bool  # Whether API keys/credentials are set
    
    async def search(self, query: str, **kwargs) -> list[WebSearchResult]
    
    @property
    def requires_scraping(self) -> bool  # Whether results need web scraping
```

## Available Search Engines

### Google Search

**Provider:** Google Custom Search API  
**Requires Scraping:** Yes (returns only URLs and snippets)  
**Configuration Required:** API Key + Search Engine ID

#### Features
- Pagination support (up to 100 results)
- Date restriction filtering
- Safe search controls
- Site restriction (include/exclude domains)
- Custom search configuration

#### Environment Variables

```bash
GOOGLE_SEARCH_API_KEY=your_google_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id
```

#### Configuration

```python
from unique_web_search.services.search_engine.google import GoogleConfig, GoogleSearch
from unique_web_search.services.search_engine.utils.google.schema import GoogleSearchOptionalQueryParams

config = GoogleConfig(
    search_engine_name=SearchEngineType.GOOGLE,
    fetch_size=10,  # Number of results to fetch
    custom_search_config=GoogleSearchOptionalQueryParams(
        safe="active",  # Safe search: off, active, high
        cr="countryUS",  # Country restriction
        lr="lang_en",  # Language restriction
        siteSearch="example.com",  # Limit to specific site
        dateRestrict="m1"  # Results from last month
    )
)

search = GoogleSearch(config)
results = await search.search("artificial intelligence")
```

#### Best For
- General web searches
- When you need Google's comprehensive index
- Academic and research queries

---

### Bing Search

**Provider:** Microsoft Bing via Azure AI Foundry Agents (Grounding)  
**Requires Scraping:** Configurable (default: No)  
**Configuration Required:** Azure Workload Identity + AI Project endpoint + Agent ID

#### Features
- AI-powered search with Bing grounding
- Agent-based conversation threads
- Structured result extraction via LLM
- Enterprise-grade Azure authentication
- Workload Identity or Default Azure Credentials support
- Full content extraction without additional scraping

#### Authentication

Bing Search uses Azure AI Foundry Agents which requires Azure authentication via:

1. **Workload Identity** (recommended for production):
   - Uses Managed Identity in Azure environments
   - Requires Azure AD configuration
   
2. **Default Azure Credential** (for development):
   - Uses `az login` credentials
   - Falls back to environment variables, managed identity, etc.

#### Environment Variables

```bash
# Azure AI Project Configuration
AZURE_AI_PROJECT_ENDPOINT=https://your-project.openai.azure.com
AZURE_AI_AGENT_ID=your_agent_id

# Azure Authentication
AZURE_IDENTITY_CREDENTIAL_TYPE=workload  # or "default"
AZURE_IDENTITY_CREDENTIALS_VALIDATE_TOKEN_URL=https://management.azure.com/.default

# Optional: For private endpoints
USE_UNIQUE_PRIVATE_ENDPOINT_TRANSPORT=false
```

#### Configuration

```python
from unique_web_search.services.search_engine.bing import BingSearchConfig, BingSearch

config = BingSearchConfig(
    search_engine_name=SearchEngineType.BING,
    agent_id="your-agent-id",  # Azure AI Agent ID
    endpoint="https://your-project.openai.azure.com",  # Azure AI Project endpoint
    requires_scraping=False  # Grounding returns full content
)

search = BingSearch(config, language_model_service, lmi)
results = await search.search("machine learning")
```

#### How It Works

1. **Thread Creation**: Creates a conversation thread in Azure AI Agents
2. **Message Submission**: Sends the query as a user message
3. **Agent Processing**: Agent uses Bing grounding to search and process results
4. **Structured Extraction**: Uses LLM to extract structured `WebSearchResult` objects from agent's response

#### Setup Requirements

1. **Azure AI Foundry Project**:
   - Create an AI Foundry project in Azure Portal
   - Note the project endpoint URL

2. **Create an Agent**:
   - Create an agent with Bing Search grounding enabled
   - Note the agent ID

3. **Configure Authentication**:
   - For Workload Identity: Set up Managed Identity in Azure
   - For Default: Run `az login` locally

4. **Environment Variables**:
   - Set `AZURE_AI_PROJECT_ENDPOINT`
   - Set `AZURE_AI_AGENT_ID`
   - Set `AZURE_IDENTITY_CREDENTIAL_TYPE` to "workload" or "default"

#### Best For
- Enterprise Azure environments
- When you need Bing's index with AI processing
- Managed identity authentication requirements
- Agent-based workflows

---

### Brave Search

**Provider:** Brave Search API  
**Requires Scraping:** Yes  
**Configuration Required:** API subscription key

#### Features
- Privacy-focused search
- No tracking or profiling
- Safe search controls
- Maximum 20 results per request
- Independent web index

#### Environment Variables

```bash
BRAVE_SEARCH_API_KEY=your_brave_api_key
```

#### Configuration

```python
from unique_web_search.services.search_engine.brave import BraveSearchConfig, BraveSearch

config = BraveSearchConfig(
    search_engine_name=SearchEngineType.BRAVE,
    fetch_size=10
)

search = BraveSearch(config)
results = await search.search("privacy-focused search")
```

#### Best For
- Privacy-conscious applications
- Independent search results
- When avoiding major search engine bias

---

### Tavily Search

**Provider:** Tavily AI Search API  
**Requires Scraping:** No (returns full content)  
**Configuration Required:** API key

#### Features
- AI-optimized search results
- Full content extraction included
- No additional scraping needed
- Topic-specific search (general, news, finance)
- Search depth control (basic, advanced)
- Time range filtering
- Domain inclusion/exclusion

#### Environment Variables

```bash
TAVILY_API_KEY=your_tavily_api_key
```

#### Configuration

```python
from unique_web_search.services.search_engine.tavily import TavilyConfig, TavilySearch

config = TavilyConfig(
    search_engine_name=SearchEngineType.TAVILY,
    fetch_size=5,
    custom_search_config={
        "search_depth": "advanced",  # or "basic"
        "topic": "news",  # general, news, finance
        "time_range": "week",  # day, week, month, year
        "include_domains": ["example.com"],
        "exclude_domains": ["spam.com"],
        "include_answer": True,  # Include AI-generated answer
        "include_raw_content": True
    }
)

search = TavilySearch(config)
results = await search.search("latest AI developments")
```

#### Best For
- AI/LLM applications (optimized for RAG)
- When full content is needed immediately
- Research with time-sensitive queries
- News and finance searches

---

### Jina Search

**Provider:** Jina AI Search API  
**Requires Scraping:** No (returns full content)  
**Configuration Required:** API key

#### Features
- Full content extraction via Reader API
- No additional scraping needed
- Markdown and HTML support
- Image extraction
- Link and reference preservation

#### Environment Variables

```bash
JINA_API_KEY=your_jina_api_key
```

#### Configuration

```python
from unique_web_search.services.search_engine.jina import JinaConfig, JinaSearch

config = JinaConfig(
    search_engine_name=SearchEngineType.JINA,
    fetch_size=5
)

search = JinaSearch(config)
results = await search.search("web scraping techniques")
```

#### Best For
- Content-heavy applications
- When you need clean, formatted content
- LLM-optimized content structure

---

### Firecrawl Search

**Provider:** Firecrawl API  
**Requires Scraping:** No (returns full content)  
**Configuration Required:** API key

#### Features
- Deep web scraping included
- Full content extraction
- JavaScript rendering support
- Clean, structured output
- Multiple format support

#### Environment Variables

```bash
FIRECRAWL_API_KEY=your_firecrawl_api_key
```

#### Configuration

```python
from unique_web_search.services.search_engine.firecrawl import FireCrawlConfig, FireCrawlSearch

config = FireCrawlConfig(
    search_engine_name=SearchEngineType.FIRECRAWL,
    fetch_size=5
)

search = FireCrawlSearch(config)
results = await search.search("dynamic web content")
```

#### Best For
- JavaScript-heavy websites
- Dynamic content extraction
- When you need comprehensive page content

---

### VertexAI Search

**Provider:** Google Vertex AI (Gemini with Grounding)  
**Requires Scraping:** No (returns AI-generated content with citations)  
**Configuration Required:** Google Cloud credentials

#### Features
- AI-powered search with grounding
- Automatic citation generation
- Structured result extraction
- Enterprise search support
- URL redirect resolution
- Customizable system instructions

#### Environment Variables

```bash
# Google Cloud authentication via Application Default Credentials (ADC)
# Set up using: gcloud auth application-default login
# Or set GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

#### Configuration

```python
from unique_web_search.services.search_engine.vertexai import VertexAIConfig, VertexAI

config = VertexAIConfig(
    search_engine_name=SearchEngineType.VERTEXAI,
    model_name="gemini-2.5-flash",  # or "gemini-2.5-pro"
    grounding_system_instruction="Provide detailed technical answers with citations",
    enable_entreprise_search=False,  # Use enterprise search if available
    enable_redirect_resolution=True,  # Resolve URL redirects
    requires_scraping=False
)

search = VertexAI(config, language_model_service, lmi)
results = await search.search("quantum computing breakthroughs")
```

#### How It Works

1. **Grounding Phase**: Uses Gemini with Google Search grounding to generate an answer with citations
2. **Extraction Phase**: Parses the grounded response into structured `WebSearchResult` objects
3. **Resolution Phase** (optional): Resolves any URL redirects to final destinations

#### Best For
- AI-powered research
- When you want synthesized answers with sources
- Complex queries requiring interpretation
- Enterprise environments with Google Cloud

---

### Custom API Search

**Provider:** Your custom search API  
**Requires Scraping:** Configurable  
**Configuration Required:** API endpoint and authentication

#### Features
- Support for any compatible search API
- Both GET and POST request methods
- Flexible parameter configuration
- Custom headers and authentication
- Separate query params and body params
- Configurable timeout

#### API Specification

Your custom API must return responses in this format:

```json
{
  "results": [
    {
      "url": "https://example.com/page",
      "title": "Page Title",
      "snippet": "Brief description",
      "content": "Full page content"
    }
  ]
}
```

#### Environment Variables

```bash
CUSTOM_WEB_SEARCH_API_ENDPOINT=https://your-api.example.com/search
CUSTOM_WEB_SEARCH_API_METHOD=POST  # GET or POST
CUSTOM_WEB_SEARCH_API_HEADERS='{"Authorization": "Bearer YOUR_KEY"}'
CUSTOM_WEB_SEARCH_API_ADDITIONAL_QUERY_PARAMS='{"api_version": "v2", "format": "json"}'
CUSTOM_WEB_SEARCH_API_ADDITIONAL_BODY_PARAMS='{"lang": "en", "safe": true}'
```

#### Configuration

**GET Request Example:**
```python
from unique_web_search.services.search_engine.custom_api import CustomAPIConfig, CustomAPI
from unique_web_search.settings import CUSTOM_API_REQUEST_METHOD

config = CustomAPIConfig(
    search_engine_name=SearchEngineType.CUSTOM_API,
    api_endpoint="https://your-api.example.com/search",
    api_request_method=CUSTOM_API_REQUEST_METHOD.GET,
    api_headers={"X-API-Key": "your_api_key"},
    api_additional_query_params={
        "limit": 10,
        "format": "json",
        "lang": "en"
    },
    timeout=60
)
```

Request will be:
```
GET https://your-api.example.com/search?query=test&limit=10&format=json&lang=en
Headers: X-API-Key: your_api_key
```

**POST Request Example:**
```python
config = CustomAPIConfig(
    search_engine_name=SearchEngineType.CUSTOM_API,
    api_endpoint="https://your-api.example.com/search",
    api_request_method=CUSTOM_API_REQUEST_METHOD.POST,
    api_headers={
        "Authorization": "Bearer YOUR_TOKEN",
        "Content-Type": "application/json"
    },
    api_additional_query_params={
        "api_version": "v2"  # Goes in URL
    },
    api_additional_body_params={
        "lang": "en",
        "safe_search": True,
        "max_results": 10  # Goes in body
    },
    timeout=120,
    requires_scraping=False
)

search = CustomAPI(config)
results = await search.search("custom search query")
```

Request will be:
```
POST https://your-api.example.com/search?api_version=v2
Headers:
  Authorization: Bearer YOUR_TOKEN
  Content-Type: application/json
Body:
{
  "query": "custom search query",
  "lang": "en",
  "safe_search": true,
  "max_results": 10
}
```

#### Best For
- Integrating proprietary search APIs
- Using domain-specific search engines
- Custom authentication requirements
- When you have your own search infrastructure

---

## Common Configuration

All search engines support these common configuration options:

### BaseSearchEngineConfig

```python
class BaseSearchEngineConfig:
    search_engine_name: SearchEngineType  # Required
    fetch_size: int = 5  # Number of results to fetch (where applicable)
```

### Factory Pattern

Use the factory function to create search engines:

```python
from unique_web_search.services.search_engine import get_search_engine_service

# The factory automatically creates the correct search engine instance
search_engine = get_search_engine_service(
    config,  # Any search engine config
    language_model_service,  # Required for some engines
    lmi  # Language model info
)

results = await search_engine.search("your query")
```

## Choosing a Search Engine

### Decision Matrix

| Search Engine | Best For | Requires Scraping | Cost | Setup Complexity |
|--------------|----------|-------------------|------|------------------|
| **Google** | General searches, comprehensive results | Yes | Pay per query | Medium |
| **Bing** | Azure environments, AI agents | Configurable | Azure AI costs | High |
| **Brave** | Privacy-focused, independent | Yes | Pay per query | Low |
| **Tavily** | AI/RAG applications, research | No | Pay per query | Low |
| **Jina** | Content extraction, clean formatting | No | Pay per query | Low |
| **Firecrawl** | Dynamic sites, JS-heavy content | No | Pay per query | Low |
| **VertexAI** | AI-powered synthesis, citations | Configurable | GCP charges | High |
| **Custom API** | Your own infrastructure | Configurable | Your costs | Variable |

### Recommendations

#### Choose Google or Bing if:
- You need the most comprehensive web coverage
- **Google**: You're okay with additional scraping
- **Bing**: You're using Azure AI Foundry and want AI agent integration
- You want familiar, proven search results

#### Choose Brave if:
- Privacy is a concern
- You want independent search results
- You're willing to do additional scraping

#### Choose Tavily if:
- You're building AI/LLM applications
- You need content immediately without scraping
- Time-sensitive queries are important
- You want AI-optimized results

#### Choose Jina if:
- You need clean, well-formatted content
- Content quality is more important than quantity
- You want markdown-formatted results

#### Choose Firecrawl if:
- You're dealing with JavaScript-heavy sites
- You need comprehensive content extraction
- Dynamic content is critical

#### Choose VertexAI if:
- You want AI-synthesized answers with citations
- You're already using Google Cloud
- You need enterprise-grade search
- You want grounded, fact-checked responses

#### Choose Custom API if:
- You have your own search infrastructure
- You need domain-specific search
- You require custom authentication
- Standard search engines don't meet your needs

## Usage Example

```python
from unique_web_search.services.search_engine import get_search_engine_service
from unique_web_search.services.search_engine.tavily import TavilyConfig

# Configure search engine
config = TavilyConfig(
    search_engine_name=SearchEngineType.TAVILY,
    fetch_size=5
)

# Create service
search = get_search_engine_service(config, lm_service, lmi)

# Check if configured
if not search.is_configured:
    raise ValueError("Search engine not properly configured")

# Perform search
results = await search.search("quantum computing")

# Use results
for result in results:
    print(f"Title: {result.title}")
    print(f"URL: {result.url}")
    print(f"Content: {result.content[:200]}...")
```

## Error Handling

All search engines may raise the following exceptions:

- `httpx.HTTPError`: Network or HTTP errors
- `ValidationError`: Invalid API responses
- `AssertionError`: Missing configuration or credentials

Always wrap search calls in try-except blocks:

```python
try:
    results = await search.search("query")
except httpx.HTTPError as e:
    logger.error(f"HTTP error: {e}")
except ValidationError as e:
    logger.error(f"Invalid response format: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

## Adding a New Search Engine

To add a new search engine:

1. Create a new file in this directory (e.g., `newsearchengine.py`)
2. Implement the configuration class inheriting from `BaseSearchEngineConfig`
3. Implement the search engine class inheriting from `SearchEngine`
4. Add the search engine type to `SearchEngineType` enum in `base.py`
5. Register it in `__init__.py`'s factory function
6. Add tests in `tests/test_search_engines.py`

Example template:

```python
class NewSearchEngineConfig(BaseSearchEngineConfig[SearchEngineType.NEW]):
    search_engine_name: Literal[SearchEngineType.NEW] = SearchEngineType.NEW
    # Add custom configuration fields

class NewSearchEngine(SearchEngine[NewSearchEngineConfig]):
    def __init__(self, config: NewSearchEngineConfig):
        super().__init__(config)
        self.is_configured = True  # Check API keys/credentials
    
    @property
    def requires_scraping(self) -> bool:
        return False  # or True, depending on your implementation
    
    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        # Implement search logic
        pass
```

## Performance Considerations

- **With Scraping (Google, Bing, Brave)**: Slower but cheaper per query
- **Without Scraping (Tavily, Jina, Firecrawl)**: Faster but may cost more
- **VertexAI**: Best for complex queries requiring synthesis
- **Custom API**: Performance depends on your implementation

## License & Attribution

When using these search engines, ensure you comply with their respective terms of service and attribution requirements.

