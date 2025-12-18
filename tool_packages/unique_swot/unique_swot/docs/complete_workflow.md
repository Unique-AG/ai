# Complete SWOT Analysis Workflow

This document provides an end-to-end view of the SWOT analysis workflow, from user request to final report delivery, with detailed sequence diagrams for each phase.

## Overview

The SWOT analysis workflow consists of six main phases executed sequentially by the `SWOTOrchestrator`:

1. **Initialization**: Tool setup and dependency injection
2. **Collection**: Gather sources from multiple data sources
3. **Prioritization**: LLM-based source ordering by relevance
4. **Selection & Generation**: Per-source filtering and SWOT component generation
5. **Summarization**: Executive summary generation with citation remapping
6. **Delivery**: Multi-format report rendering and delivery

## High-Level Flow

```mermaid
flowchart TD
    Start([User Request]) --> Init[Tool Initialization]
    Init --> Orch[Orchestrator Start]
    
    Orch --> P1[Phase 1: Collection]
    P1 --> P2[Phase 2: Prioritization]
    P2 --> P3[Phase 3: Selection + Generation Loop]
    P3 --> P4[Phase 4: Summarization]
    P4 --> P5[Phase 5: Delivery]
    
    P5 --> End([Report to User])
    
    subgraph "For Each Source (in priority order)"
        P3
    end
```

## Phase 1: Initialization

### Tool Setup

```mermaid
sequenceDiagram
    participant User
    participant Toolkit as Unique Toolkit
    participant Tool as SwotAnalysisTool
    participant Deps as Dependencies
    
    User->>Toolkit: SWOT Analysis Request + Plan
    Toolkit->>Tool: Initialize tool with event
    
    Note over Tool: Parse session config
    Tool->>Tool: _try_load_session_config()
    
    Note over Tool: Initialize services
    Tool->>Deps: Create KnowledgeBaseService
    Tool->>Deps: Create ShortTermMemoryService
    Tool->>Deps: Create ChatService
    Tool->>Deps: Create QuartrService (earnings)
    
    Note over Tool: Create memory service
    Tool->>Deps: SwotMemoryService(cache_scope=session_id)
    
    Note over Tool: Create registries
    Tool->>Deps: ContentChunkRegistry(memory_service)
    Tool->>Deps: SWOTReportRegistry()
    
    Note over Tool: Create agents
    Tool->>Deps: SourceCollectionManager
    Tool->>Deps: SourceIterationAgent
    Tool->>Deps: SourceSelectionAgent
    Tool->>Deps: GenerationAgent
    Tool->>Deps: SummarizationAgent
    Tool->>Deps: ReportDeliveryService
    
    Note over Tool: Create orchestrator
    Tool->>Deps: SWOTOrchestrator(all protocols)
    
    Tool-->>Toolkit: Tool ready
    Toolkit->>Tool: execute(plan)
```

### Configuration Loading

The tool loads configuration from multiple sources:

1. **Tool Config**: Default settings from `SwotAnalysisToolConfig`
2. **Session Config**: Company and analysis metadata from event payload
3. **Runtime Config**: Dynamic settings based on user request

```python
# Session config
session_config = SessionConfig.model_validate(event.payload.session_config)

# Collection context
collection_context = CollectionContext(
    company_name=session_config.company.display_name,
    company_tickers=session_config.company.tickers,
    start_date=datetime.now() - timedelta(days=365),
    end_date=datetime.now(),
    metadata_filter=metadata_filter,
)

# Memory service
memory_service = SwotMemoryService(
    short_term_memory_service=stm_service,
    cache_scope=f"swot_{session_config.session_id}",
)
```

## Phase 2: Source Collection

```mermaid
sequenceDiagram
    participant Orch as Orchestrator
    participant Coll as SourceCollectionManager
    participant KB as KnowledgeBase Collector
    participant EC as EarningsCall Collector
    participant Web as Web Collector
    participant Notify as StepNotifier
    participant Quartr as Quartr API
    participant KBS as KnowledgeBase Service
    
    Orch->>Coll: collect(step_notifier)
    Coll->>Notify: notify("Collecting sources...")
    
    par Parallel Collection
        Coll->>KB: collect(context)
        KB->>KBS: query(metadata_filter)
        KBS-->>KB: documents
        KB-->>Coll: KB Contents
    and
        Coll->>EC: collect(context)
        EC->>KBS: check_existing_earnings_calls()
        KBS-->>EC: existing_calls
        EC->>Quartr: fetch_transcripts(company, date_range)
        Quartr-->>EC: new_transcripts
        EC->>EC: convert_to_docx()
        EC->>KBS: ingest_docx(transcript)
        EC-->>Coll: EC Contents
    and
        Coll->>Web: collect(context)
        Web->>Web: web_search(company)
        Web->>Web: scrape_content()
        Web-->>Coll: Web Contents
    end
    
    Coll->>Notify: notify("Collected N sources", completed=True)
    Coll-->>Orch: list[Content]
```

### Collection Details

**Knowledge Base**:
- Filters by metadata (document type, date range, tags)
- Returns structured `Content` objects with chunks
- Average: 5-10 documents

**Earnings Calls**:
- Checks cache to avoid re-ingestion
- Fetches from Quartr API if not cached
- Converts transcripts to DOCX
- Ingests to Knowledge Base for future use
- Average: 4-8 earnings calls

**Web Sources**:
- Performs web search for company
- Scrapes and processes content
- Structures into `Content` objects
- Average: 3-5 web articles

## Phase 3: Source Prioritization

```mermaid
sequenceDiagram
    participant Orch as Orchestrator
    participant Iter as SourceIterationAgent
    participant LLM as Language Model
    participant Notify as StepNotifier
    
    Orch->>Iter: iterate(contents, step_notifier)
    Iter->>Notify: notify("Sorting sources")
    
    Note over Iter: Prepare content previews
    loop For each content
        Iter->>Iter: generate_unique_id()
        Iter->>Iter: extract_preview_chunks(max=5)
        Iter->>Iter: store in content_map
    end
    
    Note over Iter: Build LLM prompt
    Iter->>Iter: compose_system_prompt(objective)
    Iter->>Iter: compose_user_prompt(previews)
    
    Iter->>LLM: generate_structured_output(prompts)
    Note over LLM: Order sources by relevance
    LLM-->>Iter: SourceIterationResults
    
    Note over Iter: Handle results
    alt All sources ordered
        Iter->>Iter: yield in LLM order
    else Some sources missed
        Iter->>Iter: yield missed first (safety)
        Iter->>Iter: yield ordered sources
    else LLM failure
        Iter->>Iter: yield in original order
    end
    
    Iter->>Notify: notify(results_summary, completed=True)
    Iter-->>Orch: AsyncIterator[Content]
```

### Prioritization Logic

**LLM Objective**: Order sources from most to least relevant for SWOT analysis

**Criteria**:
1. **Relevance**: Direct SWOT information vs. tangential content
2. **Recency**: Newer information prioritized
3. **Quality**: Comprehensive analysis vs. brief mentions
4. **Document Type**: Financial reports > News articles > General content

**Output**: Async iterator yielding sources in priority order

## Phase 4: Selection & Generation Loop

```mermaid
sequenceDiagram
    participant Orch as Orchestrator
    participant Iter as Source Iterator
    participant Sel as SourceSelectionAgent
    participant Gen as GenerationAgent
    participant Exec as AgenticPlanExecutor
    participant Reg as ContentChunkRegistry
    participant RepReg as SWOTReportRegistry
    participant Notify as StepNotifier
    participant LLM as Language Model
    
    Orch->>Iter: iterate (async iterator)
    
    loop For each source (in priority order)
        Iter-->>Orch: content
        
        Note over Orch: Selection Phase
        Orch->>Sel: select(content, step_notifier)
        Sel->>Notify: notify("Reviewing source...")
        Sel->>LLM: Is this relevant?
        LLM-->>Sel: SourceSelectionResult
        Sel->>Notify: notify(reason, completed=True)
        Sel-->>Orch: should_select
        
        alt Source is relevant
            Note over Orch: Generation Phase
            Orch->>Gen: generate(plan, content)
            Gen->>Notify: notify("Processing...", progress=0)
            
            Note over Gen: Register chunks
            loop For each chunk
                Gen->>Reg: register(chunk)
                Reg-->>Gen: chunk_id
            end
            
            Note over Gen: Prepare batches
            Gen->>Gen: _prepare_source_batches()
            
            Note over Gen: Process components
            loop For S, W, O, T
                alt operation == GENERATE
                    Gen->>Exec: add(extract_task)
                else operation == MODIFY
                    Note over Gen: Not implemented, use GENERATE
                    Gen->>Exec: add(extract_task)
                else operation == NOT_REQUESTED
                    Note over Gen: Skip
                end
                Gen->>Notify: notify("Processing...", progress=X%)
            end
            
            Note over Exec: Execute tasks
            Exec->>Exec: run() (sequential or concurrent)
            loop For each task
                Exec->>LLM: Extract SWOT component
                LLM-->>Exec: SWOTSection
            end
            Exec-->>Gen: results
            
            Note over Gen: Store results
            loop For each result
                alt Success
                    Gen->>RepReg: register(component, section)
                else Failure
                    Note over Gen: Log error, continue
                end
            end
            
            Gen->>Notify: notify("Completed!", progress=100, completed=True)
            Gen-->>Orch: None
        else Source is irrelevant
            Note over Orch: Skip to next source
        end
    end
    
    Note over Orch: All sources processed
```

### Selection Criteria

The LLM evaluates each source for:
1. **Direct SWOT Content**: Does it discuss strengths, weaknesses, opportunities, or threats?
2. **Company Relevance**: Is it about the target company (not competitors)?
3. **Information Quality**: Does it provide substantive analysis (not just mentions)?
4. **Recency**: Is the information current and actionable?

### Generation Per Source

For each relevant source:
1. **Chunk Registration**: Register all chunks with unique IDs
2. **Batch Preparation**: Create citable batches with IDs
3. **Component Processing**: Generate S/W/O/T sections based on plan
4. **Task Execution**: Execute via `AgenticPlanExecutor` (sequential or concurrent)
5. **Result Storage**: Store sections in `SWOTReportRegistry`

## Phase 5: Summarization

```mermaid
sequenceDiagram
    participant Tool as SwotAnalysisTool
    participant Orch as Orchestrator
    participant Sum as SummarizationAgent
    participant Rep as ReportDeliveryService
    participant Cit as CitationManager
    participant LLM as Language Model
    participant Chat as ChatService
    
    Orch-->>Tool: SWOTReportComponents
    Tool->>Gen: get_reports()
    Gen->>RepReg: retrieve_component_sections()
    RepReg-->>Gen: all sections
    Gen-->>Tool: SWOTReportComponents
    
    Tool->>Sum: summarize(result, citation_mgr, report_handler)
    
    Note over Sum: Step 1: Render report
    Sum->>Rep: render_report(result, citation_fn)
    Rep->>Cit: add_citations_to_report(report, "stream")
    Note over Cit: [chunk_X] → [source1]
    Cit-->>Rep: markdown with stream citations
    Rep-->>Sum: rendered_report
    
    Note over Sum: Step 2: Prepare chunks
    Sum->>Cit: get_referenced_content_chunks()
    Cit-->>Sum: list[ContentChunk]
    Sum->>Sum: add_pages_postfix()
    
    Note over Sum: Step 3: Generate summary
    Sum->>Chat: complete_with_references_async(messages, chunks)
    Chat->>LLM: Generate executive summary
    LLM-->>Chat: summary with [1], [2] citations
    Chat-->>Sum: response
    
    Note over Sum: Step 4: Remap references
    Sum->>Sum: _remap_references_to_chunks()
    Note over Sum: [1] → [chunk_abc123]
    
    Note over Sum: Step 5: Reset citation manager
    Sum->>Cit: reset_maps()
    
    Sum-->>Tool: (summary_text, summarized_result, num_refs)
```

### Summarization Purpose

The summarization phase:
1. **Condenses**: Reduces full analysis to 2-3 paragraph executive summary
2. **Highlights**: Emphasizes key insights from each SWOT component
3. **Maintains Citations**: Preserves all references to source documents
4. **Provides Context**: Gives overview without requiring full report read

## Phase 6: Delivery

```mermaid
sequenceDiagram
    participant Tool as SwotAnalysisTool
    participant Del as ReportDeliveryService
    participant Cit as CitationManager
    participant DOCX as DocxGeneratorService
    participant KB as KnowledgeBase Service
    participant User
    
    Tool->>Del: deliver_report(DOCX, markdown, citation_mgr)
    
    alt DOCX Mode
        Note over Del: DOCX Generation
        Del->>Cit: add_citations_to_report(markdown, "docx")
        Note over Cit: [chunk_X] → [1: p5]
        Cit-->>Del: report with doc citations
        
        Del->>Cit: get_citations_for_docx()
        Cit-->>Del: [(1, "Doc A (p5)"), ...]
        
        Del->>Del: _render_citation_footer()
        Del->>Del: append footer to report
        
        Del->>DOCX: convert_markdown_to_docx()
        DOCX-->>Del: docx_bytes
        
        Del->>KB: upload_content_async()
        KB-->>Del: content_id
        
        Del-->>Tool: ToolCallResponse(attachments=[docx])
        Tool-->>User: Download link
    else Chat Mode
        Note over Del: Chat Markdown
        Del->>Cit: add_citations_to_report(markdown, "chat")
        Note over Cit: [chunk_X] → superscript refs
        Cit-->>Del: report with superscripts
        
        Del->>Cit: get_referenced_content_chunks()
        Cit-->>Del: chunks for clickable refs
        
        Del-->>Tool: ToolCallResponse(content=markdown, references=chunks)
        Tool-->>User: Rich markdown with clickable citations
    end
```

### Delivery Modes

**DOCX Mode**:
- Professional Word document
- Document-level citations: `[1: p5]`, `[2: p10-12]`
- Citation footer with full source list
- Uploaded to Knowledge Base
- Downloadable attachment

**Chat Mode**:
- Rich markdown formatting
- Superscript citations that are clickable
- References panel in chat interface
- Immediate display, no download

## Complete End-to-End Sequence

```mermaid
sequenceDiagram
    participant User
    participant Tool as SwotAnalysisTool
    participant Orch as Orchestrator
    participant Sources as Source Pipeline
    participant Gen as Generation Pipeline
    participant Report as Report Pipeline
    
    User->>Tool: Request SWOT Analysis + Plan
    
    Note over Tool: Phase 1: Initialize
    Tool->>Tool: Load config, create services
    Tool->>Orch: Create with all dependencies
    
    Tool->>Orch: run(company_name, plan)
    
    Note over Orch: Phase 2: Collect
    Orch->>Sources: collect()
    Sources-->>Orch: 15 contents
    
    Note over Orch: Phase 3: Prioritize
    Orch->>Sources: iterate(contents)
    Sources-->>Orch: AsyncIterator (ordered)
    
    Note over Orch: Phase 4: Select + Generate
    loop For each source (priority order)
        Orch->>Sources: select(content)
        Sources-->>Orch: should_select
        
        alt Relevant
            Orch->>Gen: generate(plan, content)
            Gen-->>Orch: sections stored
        else Irrelevant
            Note over Orch: Skip
        end
    end
    
    Orch->>Gen: get_reports()
    Gen-->>Orch: SWOTReportComponents
    Orch-->>Tool: components
    
    Note over Tool: Phase 5: Summarize
    Tool->>Report: summarize(components)
    Report-->>Tool: (summary, result, refs)
    
    Note over Tool: Phase 6: Deliver
    Tool->>Report: deliver_report(result)
    Report-->>Tool: ToolCallResponse
    
    Tool-->>User: SWOT Analysis Report
```

## Error Handling Strategy

### Source Collection Errors
- **Error**: Source collector fails (e.g., API timeout)
- **Handling**: Log error, continue with other sources
- **Impact**: Partial collection, analysis proceeds

### LLM Failures

#### Prioritization Failure
- **Error**: LLM fails to order sources
- **Handling**: Return sources in original order
- **Impact**: Suboptimal processing order, no data loss

#### Selection Failure
- **Error**: LLM fails to evaluate relevance
- **Handling**: Default to including source (safety)
- **Impact**: Potentially irrelevant source processed

#### Generation Failure
- **Error**: LLM fails to extract SWOT component
- **Handling**: Exception captured, other components proceed
- **Impact**: Missing one component section, analysis continues

### Memory Persistence Errors
- **Error**: Failed to save/load from memory
- **Handling**: Continue with in-memory state, log error
- **Impact**: No cached state, analysis proceeds from scratch

### Delivery Errors
- **Error**: DOCX generation or upload fails
- **Handling**: Fallback to chat mode or return error message
- **Impact**: User receives report in alternative format

## Performance Characteristics

### Typical Execution Times

| Phase | Time Range | Notes |
|-------|-----------|-------|
| Initialization | 1-2s | Service setup |
| Collection | 10-30s | Depends on source count |
| Prioritization | 5-10s | Single LLM call |
| Selection (per source) | 2-5s | LLM evaluation |
| Generation (per source) | 10-20s | 4 LLM calls (S/W/O/T) |
| Summarization | 5-10s | Single LLM call |
| Delivery | 2-5s | Document generation |
| **Total** | **2-5 minutes** | For 10-15 sources |

### Optimization Opportunities

1. **Concurrent Generation**: Use `ExecutionMode.CONCURRENT` for faster SWOT extraction
2. **Parallel Selection**: Future enhancement to evaluate multiple sources simultaneously
3. **Caching**: Memory service reduces re-computation in iterative workflows
4. **Chunk Limiting**: Reduce `max_number_of_selected_chunks` for faster LLM calls

## Workflow Variations

### Partial SWOT Analysis

User requests only Strengths and Weaknesses:

```python
plan = SWOTPlan(
    objective="Focus on internal factors",
    strengths=SWOTStep(operation=SWOTOperation.GENERATE),
    weaknesses=SWOTStep(operation=SWOTOperation.GENERATE),
    opportunities=SWOTStep(operation=SWOTOperation.NOT_REQUESTED),
    threats=SWOTStep(operation=SWOTOperation.NOT_REQUESTED),
)
```

**Impact**: Only S and W components generated, faster execution

### Modification Workflow

User wants to modify existing analysis:

```python
plan = SWOTPlan(
    objective="Update with new earnings data",
    strengths=SWOTStep(operation=SWOTOperation.MODIFY),
    # ... other components
)
```

**Note**: MODIFY not yet fully implemented, currently falls back to GENERATE

### Different Source Configurations

**Knowledge Base Only**:
```python
collection_config = SourceCollectionConfig(
    knowledge_base=KnowledgeBaseSourceConfig(enabled=True),
    earnings_calls=EarningsCallSourceConfig(enabled=False),
    web=WebSourceConfig(enabled=False),
)
```

**Earnings Calls Only**:
```python
collection_config = SourceCollectionConfig(
    knowledge_base=KnowledgeBaseSourceConfig(enabled=False),
    earnings_calls=EarningsCallSourceConfig(enabled=True),
    web=WebSourceConfig(enabled=False),
)
```

## Testing the Complete Workflow

End-to-end tests verify the entire workflow:

```python
@pytest.mark.asyncio
async def test_complete_workflow():
    # Setup mocks for all services
    mock_kb_service = MockKnowledgeBaseService()
    mock_llm_service = MockLanguageModelService()
    mock_chat_service = MockChatService()
    
    # Create tool
    tool = SwotAnalysisTool(config=test_config)
    
    # Execute
    result = await tool.execute(plan=test_plan)
    
    # Verify
    assert result.strengths is not None
    assert result.weaknesses is not None
    assert len(result.strengths) > 0
```

See `tests/services/test_orchestrator.py` for comprehensive workflow tests.

## Next Steps

For detailed information about specific components:
- [Architecture Overview](./architecture.md) - Protocol-based design and orchestrator
- [Source Management](./source_management.md) - Collection, iteration, selection, registry
- [Generation Services](./generation.md) - Agentic generation and execution
- [Reporting Services](./reporting.md) - Summarization and delivery
- [Supporting Services](./supporting_services.md) - Notification, memory, session

