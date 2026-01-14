# SWOT Analysis Test Suite

This directory contains comprehensive component-level functional tests for the SWOT analysis tool package.

## Test Philosophy

The test suite follows a **component-level testing approach** with these principles:

1. **Component Isolation**: Each major component is tested independently
2. **Mock External Dependencies**: All external services (LLM, KB, Quartr, Chat) are mocked
3. **Functional Focus**: Tests verify complete workflows and behaviors, not just individual methods
4. **Protocol Compliance**: Tests verify that components correctly implement protocol interfaces
5. **Comprehensive Coverage**: Tests cover happy paths, edge cases, and error conditions

## Test Structure

```
tests/
├── conftest.py                              # Shared fixtures and test configuration
├── test_schemas.py                          # Core data schema tests
├── test_utils.py                            # Utility function tests
├── README.md                                # This file
└── services/
    ├── test_orchestrator.py                 # Orchestration workflow tests
    ├── test_citations.py                    # Citation management tests
    ├── test_registry.py                     # Content chunk registry tests
    ├── test_notification.py                 # Step notifier tests
    ├── test_summarization.py                # Summarization agent tests
    ├── generation/
    │   ├── test_generation_agent.py         # Generation agent workflow tests
    │   ├── test_plan_executor.py            # Agentic plan executor tests
    │   └── test_report_registry.py          # SWOT report registry tests
    ├── source_management/
    │   ├── test_collection.py               # Source collection manager tests
    │   ├── test_selection.py                # Source selection agent tests
    │   └── test_iteration.py                # Source iteration agent tests
    ├── report/
    │   ├── test_delivery.py                 # Report delivery service tests
    │   └── test_docx_conversion.py          # DOCX conversion utility tests
    └── memory/
        └── test_memory_service.py           # Memory service tests
```

## Test Coverage by Component

### Core Schemas (`test_schemas.py`)
- SWOTPlan validation and component counting
- SWOTResult initialization and assignment
- Plan-to-result conversion
- Modify operation validation

### Utilities (`test_utils.py`)
- Structured output generation with retries
- LLM failure handling
- Response parsing

### Orchestration (`test_orchestrator.py`)
- Complete workflow: collect → iterate → select → generate → get_reports
- Source selection and skipping
- Protocol-based component integration
- Empty source handling
- Parameter passing between components

### Citations (`test_citations.py`)
- Citation format conversion (DOCX, Chat, Stream)
- Duplicate citation handling
- Missing chunk placeholder
- Reference generation
- Page number formatting

### Registry (`test_registry.py`)
- Chunk registration with unique ID generation
- Chunk retrieval
- Store persistence to memory
- Registry initialization from existing store
- ID collision handling

### Notifications (`test_notification.py`)
- Progress notifications with percentages
- Source/reference tracking
- Completion flags
- Multiple sequential notifications

### Generation (`generation/`)

**Generation Agent** (`test_generation_agent.py`):
- Complete generation workflow
- Source batch preparation
- Chunk registration
- Operation handling (GENERATE, MODIFY, NOT_REQUESTED)
- Notification sending

**Plan Executor** (`test_plan_executor.py`):
- Sequential vs concurrent execution
- Max concurrent tasks limiting
- Task failure handling
- Queue management

**Report Registry** (`test_report_registry.py`):
- Section registration and retrieval
- Component-specific section queries
- Section updates
- ID uniqueness

### Source Management (`source_management/`)

**Collection** (`test_collection.py`):
- Multi-source collection (KB, Earnings Calls, Web)
- Source enabling/disabling
- Metadata filter handling
- Quartr service integration
- Notification workflow

**Selection** (`test_selection.py`):
- Relevant source selection
- Irrelevant source rejection
- LLM failure fallback
- Chunk limiting

**Iteration** (`test_iteration.py`):
- Source ordering by LLM
- Missed document handling
- Original order fallback
- Empty source list handling

### Report Delivery (`report/`)

**Delivery Service** (`test_delivery.py`):
- Report rendering with Jinja templates
- DOCX mode delivery with upload
- Chat mode delivery with references
- Citation application
- Citation footer addition
- Reference numbering

**DOCX Conversion** (`test_docx_conversion.py`):
- Markdown to DOCX conversion
- Citation footer addition
- Special character handling
- Complex markdown elements

### Summarization (`test_summarization.py`)
- Executive summary generation
- LLM failure handling
- Company name inclusion
- Report content usage
- Reference counting

### Memory (`memory/test_memory_service.py`)
- Memory retrieval from KB
- Memory creation and updates
- Cache scope ID handling
- JSON serialization
- Error handling

## Running Tests

### Run All Tests
```bash
pytest unique_swot/tests/
```

### Run Specific Test File
```bash
pytest unique_swot/tests/test_schemas.py
```

### Run Tests with Coverage
```bash
pytest unique_swot/tests/ --cov=unique_swot --cov-report=html
```

### Run Tests with Verbose Output
```bash
pytest unique_swot/tests/ -v
```

### Run Tests for Specific Module
```bash
pytest unique_swot/tests/services/generation/
```

### Run Tests Matching Pattern
```bash
pytest unique_swot/tests/ -k "test_orchestrator"
```

## Shared Fixtures

The `conftest.py` file provides comprehensive fixtures for all tests:

### External Service Mocks
- `mock_knowledge_base_service` - Mock KnowledgeBaseService
- `mock_language_model_service` - Mock LanguageModelService with AsyncMock methods
- `mock_short_term_memory_service` - Mock ShortTermMemoryService
- `mock_chat_service` - Mock ChatService with upload capabilities
- `mock_quartr_service` - Mock QuartrService for earnings calls
- `mock_docx_generator` - Mock DocxGeneratorService

### Content & Chunk Fixtures
- `sample_content_chunk` - Single ContentChunk
- `sample_content` - Content with multiple chunks
- `sample_contents` - List of Content objects

### SWOT Plan Fixtures
- `sample_swot_step_plan` - Basic SWOTStepPlan
- `sample_swot_plan` - Complete SWOTPlan
- `sample_modify_swot_plan` - Plan with MODIFY operations
- `sample_plan_strengths_only` - Plan with only strengths requested

### SWOT Report Fixtures
- `sample_report_section` - SWOTReportComponentSection
- `sample_report_components` - Complete SWOTReportComponents

### Service Component Mocks
- `mock_step_notifier` - Mock StepNotifier with AsyncMock
- `mock_swot_memory_service` - Mock SwotMemoryService
- `mock_content_chunk_registry` - Mock ContentChunkRegistry
- `mock_swot_report_registry` - Mock SWOTReportRegistry
- `mock_agentic_executor` - Mock AgenticPlanExecutor
- `mock_citation_manager` - Mock CitationManager
- `mock_llm` - Mock LLM interface

### Protocol Implementation Mocks
- `mock_source_collector` - Mock SourceCollector protocol
- `mock_source_selector` - Mock SourceSelector protocol
- `mock_source_iterator` - Mock SourceIterator protocol
- `mock_reporting_agent` - Mock ReportingAgent protocol

## Mock Strategy

All tests follow a consistent mocking strategy:

1. **External Services**: Always mocked to avoid network calls and external dependencies
2. **Async Methods**: Use `AsyncMock` for all async functions
3. **Realistic Responses**: Mocks return realistic data structures matching actual responses
4. **Error Simulation**: Tests include error cases with mocked exceptions
5. **Protocol Compliance**: Protocol mocks implement the full protocol interface

## Adding New Tests

When adding new tests:

1. **Place in Correct Directory**: Match the source code structure
2. **Use Descriptive Names**: Start with `test_` and clearly describe what is tested
3. **Leverage Fixtures**: Reuse fixtures from `conftest.py` when possible
4. **Mock External Dependencies**: Never make real API calls or database queries
5. **Test Multiple Scenarios**: Include happy path, edge cases, and error conditions
6. **Document with Docstrings**: Explain what each test validates
7. **Follow Naming Conventions**: Use consistent naming patterns

### Example Test Structure

```python
@pytest.mark.asyncio
async def test_component_handles_specific_scenario(mock_dependency):
    """Test that component correctly handles a specific scenario."""
    # Arrange: Set up test data and mocks
    mock_dependency.method.return_value = expected_value
    component = Component(dependency=mock_dependency)
    
    # Act: Execute the functionality
    result = await component.process(test_input)
    
    # Assert: Verify expectations
    assert result == expected_output
    mock_dependency.method.assert_called_once()
```

## Test Dependencies

The test suite requires:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-mock` - Enhanced mocking capabilities
- `unittest.mock` - Standard library mocking (Mock, AsyncMock)

These are specified in the project's `pyproject.toml` file.

## Continuous Integration

Tests are designed to run quickly (< 10 seconds total) and reliably in CI environments:
- All external dependencies are mocked
- No network calls or file I/O (except in-memory)
- Deterministic test execution
- No test interdependencies

## Troubleshooting

### Tests Failing After Code Changes

1. Check if the component interface changed
2. Update mocks to match new signatures
3. Verify fixtures still match expected data structures
4. Check for new required parameters

### Async Test Issues

- Ensure `@pytest.mark.asyncio` decorator is present
- Use `AsyncMock` for async methods, not regular `Mock`
- Verify `await` is used for async calls

### Mock Assertion Failures

- Use `assert_called_once()` for regular mocks
- Use `assert_awaited_once()` for AsyncMocks
- Check `call_args` and `call_kwargs` for parameter verification

## Contributing

When contributing tests:
1. Follow the existing test structure and patterns
2. Ensure all tests pass before submitting
3. Add tests for new features and bug fixes
4. Update this README if adding new test categories
5. Maintain high test coverage (aim for >80%)
