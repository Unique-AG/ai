"""Tests for source collection manager."""

from unittest.mock import Mock, patch

import pytest

from unique_swot.services.collection.base import (
    CollectionContext,
    SourceCollectionManager,
)
from unique_swot.services.collection.schema import Source


class TestCollectionContext:
    """Test cases for CollectionContext class."""

    def test_collection_context_creation(self):
        """Test creating a CollectionContext."""
        context = CollectionContext(
            use_earnings_calls=True,
            use_web_sources=True,
            metadata_filter={"key": "value"},
        )

        assert context.use_earnings_calls is True
        assert context.use_web_sources is True
        assert context.metadata_filter == {"key": "value"}

    def test_collection_context_immutable(self):
        """Test that CollectionContext is immutable."""
        context = CollectionContext(
            use_earnings_calls=True,
            use_web_sources=False,
            metadata_filter=None,
        )

        # Should not be able to modify frozen model
        with pytest.raises(Exception):
            context.use_earnings_calls = False

    def test_collection_context_with_none_metadata(self):
        """Test CollectionContext with None metadata filter."""
        context = CollectionContext(
            use_earnings_calls=False,
            use_web_sources=False,
            metadata_filter=None,
        )

        assert context.metadata_filter is None


class TestSourceCollectionManager:
    """Test cases for SourceCollectionManager class."""

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
    def collection_context(self):
        """Create a basic collection context."""
        return CollectionContext(
            use_earnings_calls=False,
            use_web_sources=False,
            metadata_filter={"key": "value"},
        )

    @pytest.fixture
    def manager(self, collection_context, mock_knowledge_base_service, mock_registry):
        """Create a SourceCollectionManager instance."""
        return SourceCollectionManager(
            context=collection_context,
            knowledge_base_service=mock_knowledge_base_service,
            content_chunk_registry=mock_registry,
        )

    def test_manager_initialization(self, manager):
        """Test SourceCollectionManager initialization."""
        assert manager._context is not None
        assert manager._knowledge_base_service is not None
        assert manager._content_chunk_registry is not None

    def test_collect_sources_internal_only(self, manager, mock_registry):
        """Test collecting only internal documents."""
        with patch.object(
            manager, "collect_internal_documents", return_value=[Mock(spec=Source)]
        ) as mock_internal:
            sources = manager.collect_sources()

            mock_internal.assert_called_once()
            mock_registry.save.assert_called_once()
            assert len(sources) == 1

    def test_collect_sources_all_types(
        self, mock_knowledge_base_service, mock_registry
    ):
        """Test collecting all source types."""
        context = CollectionContext(
            use_earnings_calls=True,
            use_web_sources=True,
            metadata_filter={"key": "value"},
        )
        manager = SourceCollectionManager(
            context=context,
            knowledge_base_service=mock_knowledge_base_service,
            content_chunk_registry=mock_registry,
        )

        with (
            patch.object(
                manager, "collect_internal_documents", return_value=[Mock(spec=Source)]
            ) as mock_internal,
            patch.object(
                manager, "collect_earnings_calls", return_value=[Mock(spec=Source)]
            ) as mock_earnings,
            patch.object(
                manager, "collect_web_sources", return_value=[Mock(spec=Source)]
            ) as mock_web,
        ):
            sources = manager.collect_sources()

            mock_internal.assert_called_once()
            mock_earnings.assert_called_once()
            mock_web.assert_called_once()
            assert len(sources) == 3

    def test_collect_earnings_calls_enabled(self, manager, mock_registry):
        """Test collecting earnings calls when enabled."""
        with patch(
            "unique_swot.services.collection.base.collect_earnings_calls",
            return_value=[Mock(spec=Source)],
        ) as mock_collect:
            sources = manager.collect_earnings_calls(
                use_earnings_calls=True,
                chunk_registry=mock_registry,
            )

            mock_collect.assert_called_once()
            assert len(sources) == 1

    def test_collect_earnings_calls_disabled(self, manager, mock_registry):
        """Test collecting earnings calls when disabled."""
        sources = manager.collect_earnings_calls(
            use_earnings_calls=False,
            chunk_registry=mock_registry,
        )

        assert sources == []

    def test_collect_web_sources_enabled(self, manager, mock_registry):
        """Test collecting web sources when enabled."""
        with patch(
            "unique_swot.services.collection.base.collect_web_sources",
            return_value=[Mock(spec=Source)],
        ) as mock_collect:
            sources = manager.collect_web_sources(
                use_web_sources=True,
                chunk_registry=mock_registry,
            )

            mock_collect.assert_called_once()
            assert len(sources) == 1

    def test_collect_web_sources_disabled(self, manager, mock_registry):
        """Test collecting web sources when disabled."""
        sources = manager.collect_web_sources(
            use_web_sources=False,
            chunk_registry=mock_registry,
        )

        assert sources == []

    def test_collect_internal_documents_with_filter(self, manager, mock_registry):
        """Test collecting internal documents with metadata filter."""
        with patch(
            "unique_swot.services.collection.base.collect_knowledge_base",
            return_value=[Mock(spec=Source)],
        ) as mock_collect:
            sources = manager.collect_internal_documents(
                metadata_filter={"key": "value"},
                chunk_registry=mock_registry,
            )

            mock_collect.assert_called_once()
            assert len(sources) == 1

    def test_collect_internal_documents_without_filter(self, manager, mock_registry):
        """Test collecting internal documents without metadata filter."""
        sources = manager.collect_internal_documents(
            metadata_filter=None,
            chunk_registry=mock_registry,
        )

        assert sources == []

    def test_collect_sources_saves_registry(self, manager, mock_registry):
        """Test that collect_sources saves the registry."""
        with patch.object(manager, "collect_internal_documents", return_value=[]):
            manager.collect_sources()

            mock_registry.save.assert_called_once()

    def test_collect_sources_empty_result(
        self, mock_knowledge_base_service, mock_registry
    ):
        """Test collecting sources with no results."""
        context = CollectionContext(
            use_earnings_calls=False,
            use_web_sources=False,
            metadata_filter=None,
        )
        manager = SourceCollectionManager(
            context=context,
            knowledge_base_service=mock_knowledge_base_service,
            content_chunk_registry=mock_registry,
        )

        sources = manager.collect_sources()

        assert sources == []
        mock_registry.save.assert_called_once()
