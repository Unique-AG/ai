# Unique Web Search

A powerful, configurable web search tool for retrieving and processing the latest information from the internet. This package provides intelligent search capabilities with support for multiple search engines, web crawlers, and content processing strategies.

## Architecture

The following diagram illustrates the complete architecture and workflow of the unique_web_search package:

![Web Search Tool Architecture](docs/images/architecture-diagram.svg)

## Key Features

- **Dual Execution Modes**:
  - **V1 (Traditional)**: Query refinement with single or multiple search strategies
  - **V2 (Step-based Planning)**: Advanced research planning with parallel execution
  
- **Multiple Search Engines**:
  - Google Search
  - Bing Search
  - Brave Search
  - Jina Search
  - Tavily Search
  - Firecrawl Search
  - VertexAI (Gemini with Grounding)
  - Custom API (integrate any compatible web search API)

- **Multiple Web Crawlers**:
  - Basic HTTP Crawler
  - Crawl4AI
  - Jina Reader
  - Tavily Crawler
  - Firecrawl Crawler

- **Intelligent Content Processing**:
  - LLM-based summarization
  - Token-based truncation
  - Relevancy scoring and sorting
  - Content chunking and optimization

- **Query Refinement**:
  - **BASIC Mode**: Single optimized search query
  - **ADVANCED Mode**: Multiple targeted search queries for complex research

- **Performance Optimized**:
  - Parallel execution of search and crawl operations
  - Token limit management
  - Configurable timeouts and error handling

## Detailed Subsystem Docs

For deeper dives into each subsystem, see the dedicated READMEs:

- [Search Engines](./unique_web_search/services/search_engine/README.md) &mdash; full catalogue of supported engines, configuration, and usage examples.
- [Crawlers](./unique_web_search/services/crawlers/README.md) &mdash; comparison of crawling strategies (Basic, Crawl4AI, Tavily, Firecrawl, Jina) with setup guides.
- [Executors](./unique_web_search/services/executors/README.md) &mdash; orchestration layer (V1 & V2) covering query refinement, planning, logging, and best practices.

## Configuration

The tool uses environment variables and configuration files to manage API keys and settings. Key configuration areas include:

- Search engine selection and API keys
- Crawler selection and configuration
- Content processing strategies (SUMMARIZE, TRUNCATE, NONE)
- Token limits and relevancy thresholds
- Proxy configuration
- Debug and monitoring options

## Dependency management (uv.lock + min/latest testing)

This package is a **library** and uses `uv` for dependency management.

We run tests additionally with minimal dependencies to ensure that the listed ranges are valid. NOTE: We use lowest-direct, not lowest. 
Lowest attempts to use the lowest possible dependency versions _tarnsitively_ causing issues if a dependency has incorrect metadata. Example:
- google-cloud-aiplatform says it works with shapely<3.0.0.
- The lowest resolver assumes 1.0 which needs python 2 -> breaks
Therefore we use lowest-direct which only sets our direct dependencies to lowest. However, this only correctly verifies our min dependencies
if our code correctly lists all the required dependencies and never imports a transitive dependency. We therefore use deptry to ansure we
don't use transitive dependencies and that we have no unused dependencies.

### Test locally

- **Latest deps and deptry**:

```bash
cd tool_packages/unique_web_search
uv sync
uv run pytest
uv run deptry
```



- **Min deps**:

```bash
cd tool_packages/unique_web_search
uv venv
# Install runtime deps at minimum versions
uv pip install -e . --resolution=lowest-direct
# Install dev deps from [dependency-groups] (we only care about runtime dep minimums)
uv export --only-group dev --no-hashes | uv pip install -r -
# Use --no-sync to prevent uv from "fixing" the versions
uv run --no-sync pytest
```

## Workflow

1. **Input**: User query or structured search plan
2. **Configuration**: Load settings and initialize services
3. **Execution**: 
   - V1: Query refinement → Search → Crawl → Process
   - V2: Execute planned steps in parallel → Process
4. **Content Processing**: Clean, summarize/truncate, and chunk content
5. **Optimization**: Reduce to token limits and sort by relevance
6. **Output**: Return structured content chunks optimized for LLM consumption