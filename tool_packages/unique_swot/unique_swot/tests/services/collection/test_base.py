"""Tests for source collection manager."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from unique_swot.services.collection.base import (
    CollectionContext,
    SourceCollectionManager,
)
from unique_swot.services.collection.schema import Source
from unique_swot.services.session.schema import UniqueCompanyListing


class TestCollectionContext:
    """Test cases for CollectionContext class."""

    @pytest.fixture
    def mock_company(self):
        """Create a mock company listing."""
        return UniqueCompanyListing(
            sourceRef=123.0,
            name="Test Company",
            display_name="Test Company Inc.",
            country="US",
            tickers=[],
            source_url="https://example.com",
            source="test",
        )

    def test_collection_context_creation(self, mock_company):
        """Test creating a CollectionContext."""
        context = CollectionContext(
            company=mock_company,
            use_earnings_calls=True,
            upload_scope_id_earnings_calls="test_scope_id",
            earnings_call_start_date=datetime(2023, 1, 1),
            use_web_sources=True,
            metadata_filter={"key": "value"},
        )

        assert context.company == mock_company
        assert context.use_earnings_calls is True
        assert context.upload_scope_id_earnings_calls == "test_scope_id"
        assert context.earnings_call_start_date == datetime(2023, 1, 1)
        assert context.use_web_sources is True
        assert context.metadata_filter == {"key": "value"}

    def test_collection_context_immutable(self, mock_company):
        """Test that CollectionContext is immutable."""
        context = CollectionContext(
            company=mock_company,
            use_earnings_calls=True,
            upload_scope_id_earnings_calls="test_scope_id",
            earnings_call_start_date=datetime(2023, 1, 1),
            use_web_sources=False,
            metadata_filter=None,
        )

        # Should not be able to modify frozen model
        with pytest.raises(Exception):
            context.use_earnings_calls = False

    def test_collection_context_with_none_metadata(self, mock_company):
        """Test CollectionContext with None metadata filter."""
        context = CollectionContext(
            company=mock_company,
            use_earnings_calls=False,
            upload_scope_id_earnings_calls="test_scope_id",
            earnings_call_start_date=datetime(2023, 1, 1),
            use_web_sources=False,
            metadata_filter=None,
        )

        assert context.metadata_filter is None


class TestSourceCollectionManager:
    """Test cases for SourceCollectionManager class."""

    @pytest.fixture
    def mock_company(self):
        """Create a mock company listing."""
        return UniqueCompanyListing(
            sourceRef=123.0,
            name="Test Company",
            display_name="Test Company Inc.",
            country="US",
            tickers=[],
            source_url="https://example.com",
            source="test",
        )

    @pytest.fixture
    def mock_knowledge_base_service(self):
        """Create a mock knowledge base service."""
        service = Mock()
        service.search_content.return_value = []
        return service

    @pytest.fixture
    def mock_registry(self):
        """Create a mock content chunk registry."""
        registry = Mock()
        registry.save.return_value = None
        return registry

    @pytest.fixture
    def mock_notifier(self):
        """Create a mock notifier."""
        notifier = Mock()
        notifier.notify.return_value = None
        notifier.update_progress.return_value = None
        return notifier

    @pytest.fixture
    def mock_docx_generator(self):
        """Create a mock docx generator service."""
        generator = Mock()
        return generator

    @pytest.fixture
    def collection_context(self, mock_company):
        """Create a basic collection context."""
        return CollectionContext(
            company=mock_company,
            use_earnings_calls=False,
            upload_scope_id_earnings_calls="test_scope_id",
            earnings_call_start_date=datetime(2023, 1, 1),
            use_web_sources=False,
            metadata_filter={"key": "value"},
        )

    @pytest.fixture
    def manager(
        self,
        collection_context,
        mock_knowledge_base_service,
        mock_registry,
        mock_notifier,
        mock_docx_generator,
    ):
        """Create a SourceCollectionManager instance."""
        return SourceCollectionManager(
            context=collection_context,
            knowledge_base_service=mock_knowledge_base_service,
            content_chunk_registry=mock_registry,
            notifier=mock_notifier,
            quartr_service=None,
            earnings_call_docx_generator_service=mock_docx_generator,
        )

    def test_manager_initialization(self, manager):
        """Test SourceCollectionManager initialization."""
        assert manager._context is not None
        assert manager._knowledge_base_service is not None
        assert manager._content_chunk_registry is not None

    async def test_collect_sources_basic(self, manager, mock_registry):
        """Test basic source collection."""
        with patch(
            "unique_swot.services.collection.base.collect_knowledge_base",
            return_value=[Mock(spec=Source)],
        ):
            sources = await manager.collect_sources()

            # Should return sources as a list
            assert isinstance(sources, list)
            # Should save the registry after collection
            mock_registry.save.assert_called_once()

    async def test_collect_sources_empty_result(
        self,
        mock_company,
        mock_knowledge_base_service,
        mock_registry,
        mock_notifier,
        mock_docx_generator,
    ):
        """Test collecting sources with no results."""
        context = CollectionContext(
            company=mock_company,
            use_earnings_calls=False,
            upload_scope_id_earnings_calls="test_scope_id",
            earnings_call_start_date=datetime(2023, 1, 1),
            use_web_sources=False,
            metadata_filter=None,
        )
        manager = SourceCollectionManager(
            context=context,
            knowledge_base_service=mock_knowledge_base_service,
            content_chunk_registry=mock_registry,
            notifier=mock_notifier,
            quartr_service=None,
            earnings_call_docx_generator_service=mock_docx_generator,
        )

        with patch(
            "unique_swot.services.collection.base.collect_knowledge_base",
            return_value=[],
        ):
            sources = await manager.collect()

            assert sources == []
            mock_registry.save.assert_called_once()
