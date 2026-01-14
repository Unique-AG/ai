"""Shared test fixtures and configurations for SWOT analysis tests."""

from unittest.mock import AsyncMock, Mock

import pytest
from unique_toolkit.content import Content, ContentChunk

from unique_swot.services.generation.models.base import (
    SWOTReportComponents,
    SWOTReportComponentSection,
    SWOTReportSectionEntry,
)
from unique_swot.services.schemas import SWOTOperation, SWOTPlan, SWOTStepPlan

# ============================================================================
# External Service Mocks
# ============================================================================


@pytest.fixture
def mock_knowledge_base_service():
    """Mock KnowledgeBaseService for testing."""
    service = Mock()
    service.search_content.return_value = []
    service.upload_content_from_bytes.return_value = Mock(id="test_content_id")
    service.download_content_to_bytes.return_value = b'{"test": "data"}'
    return service


@pytest.fixture
def mock_language_model_service():
    """Mock LanguageModelService for testing."""
    service = Mock()
    service.generate_text = AsyncMock(return_value="Generated text")
    service.complete_async = AsyncMock()
    return service


@pytest.fixture
def mock_short_term_memory_service():
    """Mock ShortTermMemoryService for testing."""
    service = Mock()
    service.create_memory.return_value = None
    service.find_latest_memory.return_value = None
    return service


@pytest.fixture
def mock_chat_service():
    """Mock ChatService for testing."""
    service = Mock()
    service.assistant_message_id = "test_message_id"
    service.create_message_log.return_value = Mock(message_log_id="test_log_id")
    service.create_message_execution.return_value = None
    service.update_message_execution.return_value = None
    service.modify_assistant_message.return_value = None
    service.upload_to_chat_from_bytes.return_value = Mock(
        id="uploaded_content_id", title="Test Document", key="test.docx"
    )
    return service


@pytest.fixture
def mock_quartr_service():
    """Mock QuartrService for testing."""
    service = Mock()
    service.get_earnings_calls = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_docx_generator():
    """Mock DocxGeneratorService for testing."""
    service = Mock()
    service.generate.return_value = b"fake docx content"
    return service


# ============================================================================
# Content & Chunk Fixtures
# ============================================================================


@pytest.fixture
def sample_content_chunk():
    """Create a sample ContentChunk for testing."""
    return ContentChunk(
        id="content_123",
        chunk_id="chunk_456",
        title="Test Document",
        key="test_doc.pdf",
        text="This is sample content for testing.",
        start_page=1,
        end_page=2,
        order=0,
    )


@pytest.fixture
def sample_content(sample_content_chunk):
    """Create a sample Content object with chunks."""
    chunk2 = ContentChunk(
        id="content_123",
        chunk_id="chunk_789",
        title="Test Document",
        key="test_doc.pdf",
        text="This is more sample content.",
        start_page=3,
        end_page=4,
        order=1,
    )
    return Content(
        id="content_123",
        title="Test Document",
        key="test_doc.pdf",
        chunks=[sample_content_chunk, chunk2],
    )


@pytest.fixture
def sample_contents(sample_content):
    """Create a list of sample Content objects."""
    content2 = Content(
        id="content_456",
        title="Second Document",
        key="second_doc.pdf",
        chunks=[
            ContentChunk(
                id="content_456",
                chunk_id="chunk_abc",
                title="Second Document",
                key="second_doc.pdf",
                text="Second document content.",
                start_page=1,
                end_page=1,
                order=0,
            )
        ],
    )
    return [sample_content, content2]


# ============================================================================
# SWOT Plan Fixtures
# ============================================================================


@pytest.fixture
def sample_swot_step_plan():
    """Create a sample SWOTStepPlan for testing."""
    return SWOTStepPlan(
        operation=SWOTOperation.GENERATE,
        modify_instruction=None,
    )


@pytest.fixture
def sample_swot_plan(sample_swot_step_plan):
    """Create a sample SWOTPlan for testing."""
    return SWOTPlan(
        objective="Analyze company X's competitive position",
        strengths=sample_swot_step_plan,
        weaknesses=sample_swot_step_plan,
        opportunities=sample_swot_step_plan,
        threats=sample_swot_step_plan,
    )


@pytest.fixture
def sample_modify_swot_plan():
    """Create a sample SWOTPlan with modify operations."""
    return SWOTPlan(
        objective="Update existing SWOT analysis",
        strengths=SWOTStepPlan(
            operation=SWOTOperation.MODIFY,
            modify_instruction="Update with new data",
        ),
        weaknesses=SWOTStepPlan(
            operation=SWOTOperation.NOT_REQUESTED,
            modify_instruction=None,
        ),
        opportunities=SWOTStepPlan(
            operation=SWOTOperation.GENERATE,
            modify_instruction=None,
        ),
        threats=SWOTStepPlan(
            operation=SWOTOperation.MODIFY,
            modify_instruction="Add recent threats",
        ),
    )


@pytest.fixture
def sample_plan_strengths_only():
    """Create a SWOTPlan with only strengths requested."""
    return SWOTPlan(
        objective="Analyze company strengths",
        strengths=SWOTStepPlan(
            operation=SWOTOperation.GENERATE, modify_instruction=None
        ),
        weaknesses=SWOTStepPlan(
            operation=SWOTOperation.NOT_REQUESTED, modify_instruction=None
        ),
        opportunities=SWOTStepPlan(
            operation=SWOTOperation.NOT_REQUESTED, modify_instruction=None
        ),
        threats=SWOTStepPlan(
            operation=SWOTOperation.NOT_REQUESTED, modify_instruction=None
        ),
    )


# ============================================================================
# SWOT Report Fixtures
# ============================================================================


@pytest.fixture
def sample_report_section():
    """Create a sample SWOTReportComponentSection."""
    return SWOTReportComponentSection(
        h2="Strong Market Position",
        entries=[
            SWOTReportSectionEntry(
                preview="Leading market share",
                content="The company holds a 35% market share in the technology sector [chunk_a].",
            ),
            SWOTReportSectionEntry(
                preview="Brand recognition",
                content="Strong brand recognition globally [chunk_b].",
            ),
        ],
    )


@pytest.fixture
def sample_report_components(sample_report_section):
    """Create a sample SWOTReportComponents."""
    return SWOTReportComponents(
        strengths=[sample_report_section],
        weaknesses=[],
        opportunities=[],
        threats=[],
    )


# ============================================================================
# Service Component Mocks
# ============================================================================


@pytest.fixture
def mock_step_notifier():
    """Mock StepNotifier for testing."""
    notifier = Mock()
    notifier.notify = AsyncMock()
    notifier.get_total_number_of_references.return_value = 0
    return notifier


@pytest.fixture
def mock_swot_memory_service():
    """Mock SwotMemoryService for testing."""
    service = Mock()
    service.get.return_value = None
    service.set.return_value = None
    return service


@pytest.fixture
def mock_content_chunk_registry():
    """Mock ContentChunkRegistry for testing."""
    registry = Mock()
    registry.register.return_value = "chunk_generated_id"
    registry.retrieve.return_value = None
    registry.save.return_value = None
    return registry


@pytest.fixture
def mock_swot_report_registry():
    """Mock SWOTReportRegistry for testing."""
    registry = Mock()
    registry.register_section.return_value = "section_id_123"
    registry.retrieve_section.return_value = None
    registry.retrieve_component_sections.return_value = []
    registry.retrieve_sections_for_component.return_value = "{}"
    return registry


@pytest.fixture
def mock_agentic_executor():
    """Mock AgenticPlanExecutor for testing."""
    executor = Mock()
    executor.execute = AsyncMock(return_value=None)
    return executor


@pytest.fixture
def mock_citation_manager():
    """Mock CitationManager for testing."""
    manager = Mock()
    manager.add_citations_to_report.return_value = "Report with citations"
    manager.get_references.return_value = []
    manager.get_citations_for_docx.return_value = []
    manager.get_referenced_content_chunks.return_value = []
    return manager


@pytest.fixture
def mock_llm():
    """Mock LLM (Language Model Interface) for testing."""
    llm = Mock()
    llm.name = "test-model"
    llm.encoder_name = "cl100k_base"
    return llm


# ============================================================================
# Protocol Implementation Mocks
# ============================================================================


@pytest.fixture
def mock_source_collector():
    """Mock SourceCollector protocol for testing."""
    collector = Mock()
    collector.collect = AsyncMock(return_value=[])
    return collector


@pytest.fixture
def mock_source_selector():
    """Mock SourceSelector protocol for testing."""
    selector = Mock()
    selector.select = AsyncMock()
    return selector


@pytest.fixture
def mock_source_iterator():
    """Mock SourceIterator protocol for testing."""
    iterator = Mock()

    async def _iterate(contents, step_notifier):
        for content in contents:
            yield content

    iterator.iterate = _iterate
    return iterator


@pytest.fixture
def mock_reporting_agent():
    """Mock ReportingAgent protocol for testing."""
    agent = Mock()
    agent.generate = AsyncMock()
    agent.get_reports.return_value = SWOTReportComponents(
        strengths=[], weaknesses=[], opportunities=[], threats=[]
    )
    return agent
