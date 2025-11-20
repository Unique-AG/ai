# SWOT Analysis Tool

A sophisticated AI-powered tool for generating comprehensive SWOT (Strengths, Weaknesses, Opportunities, Threats) analysis reports based on internal documents, earnings calls, and external web resources.

## Overview

The SWOT Analysis Tool is an agentic tool built on the Unique Toolkit framework that automatically analyzes multiple data sources to produce structured, well-cited SWOT analysis reports. It leverages large language models with structured output to extract insights and generate professional-grade analysis documents.

## Architecture

![Overall Architecture Flow](docs/images/Overall%20Architecture%20Flow.svg)

## Project Structure
```
unique_swot/
├── service.py                 # Main SwotAnalysisTool
├── services/
│   ├── citations.py          # Citation management
│   ├── executor.py           # Execution orchestration
│   ├── notifier.py           # Progress notifications
│   ├── collection/           # Source collection
│   ├── generation/           # LLM-based generation
│   ├── memory/              # State management
│   └── report/              # Report rendering
├── tests/                   # Comprehensive test suite
└── docs/                    # Architecture documentation
```

## How It Works

### 1. **Plan Reception & Validation**
The tool receives a SWOT plan specifying which components to analyze (Strengths, Weaknesses, Opportunities, Threats) and the analysis objective. Each component can be set to:
- `GENERATE` - Create new analysis from sources
- `MODIFY` - Update existing analysis with new information
- `NOT_REQUESTED` - Skip this component

### 2. **Multi-Source Data Collection**
The tool collects relevant information from multiple sources:
- **Knowledge Base**: Internal documents filtered by metadata
- **Earnings Calls**: Financial earnings call transcripts fetched from Quartr API, automatically converted to DOCX, and ingested into the knowledge base
- **Web Sources**: External web research and articles

All collected content is registered in a central registry with unique identifiers for citation tracking. The tool intelligently caches earnings call content to avoid redundant ingestion.

### 3. **Two-Phase Generation Process**

For each requested SWOT component:

#### Phase 1: Extraction
- Sources are split into manageable batches based on token limits
- Each batch is processed by the language model with structured output enforcement
- The LLM extracts specific SWOT items (e.g., individual strengths) with reasoning
- Extracted items include citation placeholders linking back to source chunks
- Results from all batches are aggregated into a structured model

#### Phase 2: Summarization
- The aggregated extraction results are synthesized
- The LLM generates a coherent narrative summary
- The summary maintains all citation references
- Output is formatted with proper structure and citations

### 4. **Citation Management**
The tool implements a streamlined citation system:

- **Inline Citations**: `[chunk_X]` → Converted to document-level references like `[1: p5]`
- **Citation Footer**: DOCX reports include a comprehensive citations section listing all referenced documents
- **Reference Tracking**: Automatic deduplication of document references

This ensures every claim in the report is traceable back to its source material with minimal clutter.

### 5. **Report Delivery**

The final report can be delivered in two formats:

**DOCX Mode** (Document):
- Markdown converted to professional Word document
- Full citations with document titles and page numbers
- Uploaded as downloadable attachment

**Chat Mode** (Markdown):
- Rich markdown formatting displayed in chat
- Inline superscript citations
- Clickable references to source documents

### 6. **Memory & Caching**
- Extraction results are cached in memory for potential modifications
- Content chunk registry persisted for citation lookup
- Supports iterative refinement of analysis

## Key Features

### 🎯 Comprehensive Analysis
- Analyzes all four SWOT dimensions
- Processes multiple sources simultaneously
- Maintains context across large document sets

### 📊 Intelligent Batch Processing
- Automatically splits sources based on token limits
- Processes batches in parallel where possible (planned but not supported yet)
- Handles sources of any size

### 🔗 Advanced Citation System
- Every point backed by source references
- Document-level inline citations with page numbers
- Citation footer in DOCX reports
- Traceable to specific pages and documents

### 📈 Real-Time Progress Tracking
- Visual progress bar with emoji indicators
- Step-by-step progress updates with contextual messages
- Percentage completion calculation
- Support for success/failure states

### 💾 State Management
- Caches extraction results for modifications
- Persistent storage in Knowledge Base
- Quick lookups via Short-Term Memory

### 🎨 Multiple Output Formats
- Professional DOCX reports
- Rich markdown for chat
- Customizable templates

### 🛡️ Robust Error Handling
- Graceful degradation on failures
- Automatic retry logic
- Detailed error logging

## Workflow Example

```
User Request → SWOT Plan
    ↓
Source Collection (KB + Earnings + Web)
    ↓
For Each Component (Strengths, Weaknesses, Opportunities, Threats):
    ├── Split Sources into Batches
    ├── Extract SWOT Items from Each Batch (LLM)
    ├── Aggregate Extraction Results
    ├── Generate Summary (LLM)
    └── Save to Memory
    ↓
Format Citations
    ↓
Render Report (DOCX or Markdown)
    ↓
Deliver to User
```

## Core Services

| Service | Responsibility |
|---------|---------------|
| **SwotAnalysisTool** | Main orchestrator, validates plans, manages workflow |
| **SourceCollectionManager** | Collects data from KB, earnings calls, and web |
| **SWOTExecutionManager** | Executes analysis for each SWOT component |
| **BatchProcessor** | Manages batch processing with token limits |
| **CitationManager** | Tracks and formats citations |
| **MemoryService** | Persists state and caches results |
| **ReportDeliveryService** | Renders and delivers final reports |
| **ProgressNotifier** | Provides real-time progress updates |

## Configuration

The tool is configured via `SwotAnalysisToolConfig` which includes:
- Report generation settings (batch size, token limits)
- Language model configuration
- Prompt templates for extraction and summarization
- Report rendering preferences (DOCX vs Chat)
- Cache scope for state management

## Technology Stack

- **Framework**: Unique Toolkit (Python)
- **Validation**: Pydantic models with strict typing
- **LLM Integration**: Structured output with schema enforcement
- **Storage**: Knowledge Base for persistence, Short-Term Memory for caching
- **Templating**: Jinja2 for report templates
- **Document Processing**: DOCX generation, Markdown rendering
- **Progress Tracking**: Real-time message execution updates

## Use Cases

- **Strategic Planning**: Generate comprehensive SWOT analyses for business strategy
- **Market Analysis**: Analyze market position based on multiple data sources
- **Competitive Intelligence**: Assess strengths and weaknesses vs competitors
- **Investment Research**: Evaluate opportunities and threats for investments
- **Due Diligence**: Comprehensive analysis for M&A or partnerships

## Output Quality

The tool produces high-quality analysis by:
- Using structured output to enforce consistency
- Extracting before summarizing for thorough coverage
- Maintaining citation integrity throughout the pipeline
- Validating all outputs against Pydantic schemas
- Applying domain-specific prompt engineering

