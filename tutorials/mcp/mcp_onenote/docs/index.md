<!-- confluence-page-id: 1878556679 -->
<!-- confluence-space-key: PUBDOC -->

!!! danger "Prototype Disclaimer"
    As clearly outlined in [**Experimental Prototypes**](https://unique-ch.atlassian.net/wiki/x/DwDtbw) this is a prototype. 
    
    Prototypes are provided as-is for demonstration and evaluation only — **not products** — with no support, warranties, or production use. Any assistance or commercialization requires a separate commercial agreement.

## Overview

MCP server integrating Microsoft OneNote with Unique AI Chat using [FastMCP](https://github.com/jlowin/fastmcp) and [Microsoft Graph CLI](https://learn.microsoft.com/en-us/graph/cli/overview).

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'fontSize': '14px' }}}%%
sequenceDiagram
    participant Chat as Unique AI Chat
    participant MCP as MCP Server (FastMCP)
    participant Graph as mgc CLI
    participant OneNote as OneNote API

    Chat->>MCP: list_notebooks()
    MCP->>Graph: mgc onenote notebooks list
    Graph->>OneNote: GET /me/onenote/notebooks
    OneNote-->>Graph: JSON
    Graph-->>MCP: Output
    MCP-->>Chat: Tool Result
```

## Tools

| Tool | Description |
|------|-------------|
| `list_notebooks` | List notebooks |
| `list_sections` | List sections in a notebook |
| `list_pages` | List pages in a section |
| `get_page_content` | Get page content |
| `search_pages` | Search pages by keyword |
