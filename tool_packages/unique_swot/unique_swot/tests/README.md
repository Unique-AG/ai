# SWOT Analysis Test Suite

This directory contains comprehensive tests for the SWOT analysis tool package.

## Test Structure

```
tests/
├── conftest.py                          # Shared fixtures and test configuration
├── test_config.py                       # Tests for SwotConfig
├── test_service.py                      # Tests for SwotTool main service
└── services/                            # Tests for service modules
    ├── test_citations.py                # Citation management tests
    ├── test_executor.py                 # SWOT execution manager tests
    ├── test_notifier.py                 # Notification services tests
    ├── test_schemas.py                  # Data schema tests
    ├── collection/                      # Source collection tests
    │   ├── test_base.py                 # SourceCollectionManager tests
    │   ├── test_registry.py             # ContentChunkRegistry tests
    │   └── test_schema.py               # Collection schema tests
    ├── generation/                      # Report generation tests
    │   ├── test_batch_processor.py      # Batch processing tests
    │   └── test_config.py               # Generation config tests
    ├── memory/                          # Memory service tests
    │   └── test_base.py                 # SwotMemoryService tests
    └── report/                          # Report generation tests
        └── test_report.py               # Report template tests
```

## Test Coverage

### Core Configuration (`test_config.py`)
- SwotConfig initialization with default values
- Custom configuration settings
- Serialization and deserialization
- Tool description validation

### Main Service (`test_service.py`)
- SwotTool initialization
- Tool description methods
- Tool execution flow
- Evaluation checks
- Control taking behavior

### Schemas (`services/test_schemas.py`)
- SWOTOperation enum values
- SWOTStepPlan creation and validation
- SWOTPlan validation (including modify instruction requirements)
- SWOTResult initialization and result assignment
- Component-specific result retrieval

### Citations (`services/test_citations.py`)
- Citation processing and superscript replacement
- Multiple and duplicate citation handling
- Content chunk to reference conversion
- Missing chunk handling
- Page number formatting

### Executor (`services/test_executor.py`)
- SWOTExecutionManager initialization
- Plan execution with different operation types
- Generation and modification workflows
- Component processing (strengths, weaknesses, opportunities, threats)
- Memory service integration

### Notifier (`services/test_notifier.py`)
- LoggerNotifier functionality
- ProgressNotifier with chat service integration
- Progress percentage calculation
- Step registry management

### Collection Module
- **Base** (`services/collection/test_base.py`):
  - CollectionContext creation and immutability
  - SourceCollectionManager source collection
  - Internal documents, earnings calls, and web sources
  - Registry saving

- **Registry** (`services/collection/test_registry.py`):
  - ContentChunkRegistry initialization
  - Adding and retrieving items
  - Unique ID generation
  - Store persistence

- **Schema** (`services/collection/test_schema.py`):
  - SourceType enum
  - SourceChunk creation and validation
  - Source creation for different types
  - Serialization and deserialization

### Generation Module
- **Batch Processor** (`services/generation/test_batch_processor.py`):
  - Context splitting into batches
  - Token limit respect
  - SWOT extraction from batches
  - Summarization with error handling

- **Config** (`services/generation/test_config.py`):
  - ReportGenerationConfig defaults
  - Custom batch size and token limits
  - Configuration serialization

### Memory Module (`services/memory/test_base.py`)
- SwotMemoryService initialization
- Memory retrieval (get)
- Memory storage (set)
- Error handling for missing or invalid data
- Scope ID management
- JSON serialization/deserialization

### Report Module (`services/report/test_report.py`)
- Report template rendering
- Handling empty sections
- Markdown content support
- Citation superscripts
- Special character handling

## Running Tests

### Run All Tests
```bash
pytest unique_swot/tests/
```

### Run Specific Test File
```bash
pytest unique_swot/tests/test_config.py
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
pytest unique_swot/tests/services/collection/
```

## Test Fixtures

The `conftest.py` file provides shared fixtures across all tests:

- `mock_knowledge_base_service` - Mock KnowledgeBaseService
- `mock_language_model_service` - Mock LanguageModelService
- `mock_short_term_memory_service` - Mock ShortTermMemoryService
- `mock_chat_service` - Mock ChatService
- `sample_content_chunk` - Sample ContentChunk for testing
- `sample_source` - Sample Source for testing
- `sample_sources` - List of sample sources
- `sample_swot_step_plan` - Sample SWOTStepPlan
- `sample_swot_plan` - Complete SWOTPlan for testing
- `sample_modify_swot_plan` - SWOTPlan with modify operations
- `mock_notifier` - Mock Notifier
- `mock_event` - Mock event for tool initialization

## Test Philosophy

The test suite follows these principles:

1. **Comprehensive Coverage**: Tests cover happy paths, edge cases, and error conditions
2. **Isolation**: Each test is independent and uses mocks to avoid external dependencies
3. **Clear Documentation**: Test names and docstrings clearly describe what is being tested
4. **Fixture Reuse**: Common test data is defined in conftest.py for reuse
5. **Async Testing**: Async functions are properly tested using pytest.mark.asyncio
6. **Error Handling**: Tests verify that errors are handled gracefully

## Adding New Tests

When adding new tests:

1. Place tests in the appropriate directory matching the source code structure
2. Use descriptive test names starting with `test_`
3. Add fixtures to `conftest.py` if they'll be reused
4. Use mocks for external dependencies
5. Include docstrings explaining what each test validates
6. Follow the existing naming conventions and structure

## Dependencies

The test suite requires:
- pytest
- pytest-asyncio (for async tests)
- unittest.mock (standard library)

These are specified in the project's `pyproject.toml` file.

