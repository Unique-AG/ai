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
    def mock_notifier(self):
        """Create a mock notifier."""
        notifier = Mock()
        notifier.notify.return_value = None
        notifier.update_progress.return_value = None
        return notifier

    @pytest.fixture
    def collection_context(self):
        """Create a basic collection context."""
        return CollectionContext(
            use_earnings_calls=False,
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
    ):
        """Create a SourceCollectionManager instance."""
        return SourceCollectionManager(
            context=collection_context,
            knowledge_base_service=mock_knowledge_base_service,
            content_chunk_registry=mock_registry,
            notifier=mock_notifier,
        )

    def test_manager_initialization(self, manager):
        """Test SourceCollectionManager initialization."""
        assert manager._context is not None
        assert manager._knowledge_base_service is not None
        assert manager._content_chunk_registry is not None

    def test_collect_sources_basic(self, manager, mock_registry):
        """Test basic source collection."""
        with patch(
            "unique_swot.services.collection.base.collect_knowledge_base",
            return_value=[Mock(spec=Source)],
        ):
            sources = manager.collect_sources()

            # Should return sources as a list
            assert isinstance(sources, list)
            # Should save the registry after collection
            mock_registry.save.assert_called_once()

    def test_collect_sources_empty_result(
        self, mock_knowledge_base_service, mock_registry, mock_notifier
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
            notifier=mock_notifier,
        )

        with patch(
            "unique_swot.services.collection.base.collect_knowledge_base",
            return_value=[],
        ):
            sources = manager.collect_sources()

            assert sources == []
            mock_registry.save.assert_called_once()
