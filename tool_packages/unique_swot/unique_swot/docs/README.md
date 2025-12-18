# SWOT Analysis Tool - Documentation

Welcome to the comprehensive documentation for the SWOT Analysis Tool v1.1.0. This documentation covers the protocol-based architecture, agentic generation system, and intelligent source management pipeline.

## Documentation Structure

### 📚 Core Documentation

1. **[Architecture Overview](./architecture.md)** - Start here!
   - High-level architecture and design principles
   - Protocol-based orchestration pattern
   - SWOTOrchestrator coordination logic
   - Component interactions and design decisions

2. **[Source Management](./source_management.md)**
   - SourceCollectionManager (KB, Earnings, Web)
   - SourceIterationAgent (LLM-powered prioritization)
   - SourceSelectionAgent (LLM-powered filtering)
   - ContentChunkRegistry (citation tracking)

3. **[Generation Services](./generation.md)**
   - GenerationAgent (document-by-document processing)
   - AgenticPlanExecutor (sequential/concurrent execution)
   - SWOTReportRegistry (component-organized storage)

4. **[Reporting Services](./reporting.md)**
   - SummarizationAgent (executive summary generation)
   - ReportDeliveryService (DOCX/Chat rendering)
   - CitationManager (citation formatting and deduplication)

5. **[Supporting Services](./supporting_services.md)**
   - StepNotifier Protocol (progress tracking)
   - SwotMemoryService (state persistence)
   - SessionConfig (company and session information)

6. **[Complete Workflow](./complete_workflow.md)**
   - End-to-end flow with sequence diagrams
   - Phase-by-phase execution details
   - Error handling strategies
   - Performance characteristics

## Quick Navigation

### By Role

**For Architects**: Start with [Architecture Overview](./architecture.md) to understand the protocol-based design and orchestration patterns.

**For Developers**: Read [Complete Workflow](./complete_workflow.md) for end-to-end understanding, then dive into specific service documentation as needed.

**For QA/Testers**: Focus on [Complete Workflow](./complete_workflow.md) for test scenarios and error handling, plus individual service docs for component testing.

### By Component

| Component | Documentation | Key Concepts |
|-----------|--------------|--------------|
| Orchestrator | [Architecture](./architecture.md) | Protocols, Dependency Injection, Workflow Coordination |
| Source Pipeline | [Source Management](./source_management.md) | Collection, Prioritization, Selection, Registry |
| Generation | [Generation](./generation.md) | Agentic Processing, Execution Modes, Report Registry |
| Reporting | [Reporting](./reporting.md) | Summarization, Multi-format Delivery, Citations |
| Infrastructure | [Supporting Services](./supporting_services.md) | Notifications, Memory, Session |
| Full Flow | [Complete Workflow](./complete_workflow.md) | Phases, Sequences, Error Handling |

## Key Concepts

### Protocol-Based Architecture
All major components interact through well-defined Python protocols, enabling:
- Dependency injection for testability
- Easy component replacement
- Clear separation of concerns
- Mock-friendly design

### Agentic Processing
LLM agents make intelligent decisions at each stage:
- **Source Iteration**: Prioritize sources by relevance
- **Source Selection**: Filter irrelevant sources
- **Generation**: Extract structured SWOT components
- **Summarization**: Create executive summaries

### State Management
Persistent memory service with:
- Registry patterns for content and reports
- Cache scope isolation for multi-user scenarios
- Generic type support for different store models
- Graceful degradation on persistence failures

### Citation Integrity
Comprehensive citation tracking:
- Unique ID generation with collision detection
- Reference tracking throughout pipeline
- Multiple format support (DOCX, Chat, Stream)
- Automatic deduplication and remapping

## Architecture Diagrams

All documentation includes Mermaid diagrams for visual understanding:
- Component interaction diagrams
- Sequence diagrams for each phase
- Flowcharts for decision logic
- System overview diagrams

## Code Examples

Each service documentation includes:
- Real implementation snippets
- Usage examples
- Configuration examples
- Testing patterns

## Version History

- **v1.1.0** (2025-12-17): Protocol-based architecture, agentic generation, intelligent source management
- **v1.0.0** (2025-12-08): Initial architecture with execution manager

## Related Documentation

- [Project README](../../../README.md) - User-facing documentation and features
- [Test Documentation](../tests/README.md) - Testing guidelines and patterns
- [ChangeLog](../../../ChangeLog.md) - Version history and changes

## Getting Started

1. **Understand the Architecture**: Read [Architecture Overview](./architecture.md)
2. **Follow the Workflow**: Study [Complete Workflow](./complete_workflow.md)
3. **Dive into Services**: Explore specific service documentation as needed
4. **Review Tests**: See `tests/` directory for implementation examples

## Contributing

When updating documentation:
- Maintain consistent formatting and structure
- Include Mermaid diagrams for visual concepts
- Provide code examples where applicable
- Update cross-references when adding new sections
- Keep design decision rationales up to date

## Questions?

For questions about:
- **Architecture**: See [Architecture Overview](./architecture.md)
- **Specific Services**: Refer to individual service documentation
- **Implementation**: Check code examples and test files
- **Workflow**: Review [Complete Workflow](./complete_workflow.md)


