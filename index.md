# AI Monorepo Documentation

Welcome to the AI Monorepo documentation. This repository contains multiple AI-related packages and tools developed by the Unique team.

## Available Packages

### [Unique Toolkit](./unique_toolkit/)
The main toolkit for AI development, providing services for chat, content management, embeddings, and language model interactions.

### Other Packages
- **Unique SDK**: Core SDK for interacting with the Unique platform
- **Unique Stock Ticker**: Stock ticker detection and analysis tools
- **Unique Follow Up Questions**: Post-processing tools for generating follow-up questions
- **Tool Packages**: Various specialized tools and utilities

## Getting Started

Each package has its own documentation section. Start with the [Unique Toolkit](./unique_toolkit/) if you're new to the platform.

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
