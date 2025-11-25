# Unique AI - SDK & Toolkit Documentation

Welcome to the Unique AI SDK & Toolkit documentation. This repository contains multiple packages and tools developed by the Unique team.

## Getting Started

Each package has its own documentation section. Start with the **Unique Toolkit** if you're new to the platform.

## Available Packages

### Unique SDK
The low-level api calls to the public API of Unique AI Platform. We recommend using the Unique Toolkit for most development.

### Unique Toolkit
The main toolkit for AI development, providing services for chat, content management, embeddings, and language model interactions.

### Unique Orchestrator
The orchestrator is the core component of the Unique AI Agentic Framework. It is responsible for the agentic loop, planning, tool execution, streaming, evaluation, and post-processing.

### Tool Packages
The tool packages are the tools that can be used in the Unique AI Agentic Framework. 

#### Unique Deep Research Tool
The deep research tool is a tool that can be used to perform deep research on a given topic.

#### Unique Internal Search Tool
Internal Search Tool to find documents in the Knowledge Base

#### Unique SWOT Tool
The SWOT Analysis Tool is an agentic tool built on the Unique Toolkit framework that automatically analyzes multiple data sources to produce structured, well-cited SWOT analysis reports. It leverages large language models with structured output to extract insights and generate professional-grade analysis documents.

#### Unique Web Search Tool
A powerful, configurable web search tool for retrieving and processing the latest information from the internet. This package provides intelligent search capabilities with support for multiple search engines, web crawlers, and content processing strategies.



## Development

This is a monorepo using Poetry for dependency management. To build the documentation locally:

```bash
# Install dependencies
poetry install --with dev

# Build documentation
poetry run mkdocs build

# Serve documentation locally
poetry run mkdocs serve
```

## Contributing

Please refer to individual package documentation for contribution guidelines.
