# Unique AI - SDK & Toolkit Documentation

👋 Welcome to the Unique AI SDK & Toolkit documentation. This repository contains multiple packages and tools developed by the Unique team.

## 🚀 Getting Started

If you have a usecase in mind that you want to implement on the Unique Platform, you can find implementation guidelines [here](usecase_realization_guidelines.md).

Depending on your usecase and needs, if you find yourself needing to develop an agent/module/mcp server then you can find instructions on how to do this using the **[Unique Toolkit](unique-toolkit/latest/)** package.

In addition to the Unique Toolkit, there are other accompanying packages that can be used to develop your own applications on the Unique Platform.

## 📚 Core Documentation

<div class="grid cards" markdown>

-   ⚙️ __Unique SDK__

    ---

    The low-level API for direct integration with the Unique AI Platform. Provides REST client and resource classes.

    [SDK Documentation](https://unique-ag.github.io/ai/unique-sdk/latest/)

-   🛠️ __Unique Toolkit__

    ---

    High-level services and agentic framework for AI development, including chat, knowledge base, and event-driven applications.

    [Toolkit Documentation](https://unique-ag.github.io/ai/unique-toolkit/latest/)

</div>

## 📦 Available Packages

### 🎼 Unique Orchestrator
The orchestrator is the core component of the Unique AI Agentic Framework. It is responsible for the agentic loop, planning, tool execution, streaming, evaluation, and post-processing.

### 🔧 Tool Packages
The tool packages are the tools that can be used in the Unique AI Agentic Framework. 

#### 🔍 Unique Deep Research Tool
The deep research tool is a tool that can be used to perform deep research on a given topic.

#### 📚 Unique Internal Search Tool
Internal Search Tool to find documents in the Knowledge Base

#### 📊 Unique SWOT Tool
The SWOT Analysis Tool is an agentic tool built on the Unique Toolkit framework that automatically analyzes multiple data sources to produce structured, well-cited SWOT analysis reports. It leverages large language models with structured output to extract insights and generate professional-grade analysis documents.

#### 🌐 Unique Web Search Tool
A powerful, configurable web search tool for retrieving and processing the latest information from the internet. This package provides intelligent search capabilities with support for multiple search engines, web crawlers, and content processing strategies.



## 💻 Development

This is a monorepo using uv for dependency management. To build the documentation locally:

```bash
# Install dependencies
uv sync

# Build versioned documentation locally (simulates CI)
./.github/scripts/docs_build_versioned.sh --clean --serve

# Or build root site only for quick iteration
uv run mkdocs serve
```

## 🤝 Contributing

Please refer to individual package documentation for contribution guidelines.
