"""Tests for the SourceCollectionManager."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_toolkit.content import Content, ContentChunk

from unique_swot.services.session.schema import UniqueCompanyListing
from unique_swot.services.source_management.collection.base import (
    CollectionContext,
    SourceCollectionManager,
)


def _make_company():
    """Helper to create test company listing."""
    params = {
        "sourceRef": 123.0,
        "name": "ACME Corp",
        "displayName": "ACME Corporation",
        "country": "US",
        "tickers": [],
        "sourceUrl": "https://example.com/acme",
        "source": "test",
    }
    return UniqueCompanyListing.model_validate(params)


def _make_content(content_id="content_1", title="Test Doc"):
    """Helper to create test Content."""
    return Content(
        id=content_id,
        title=title,
        key=f"{title}.pdf",
        chunks=[
            ContentChunk(
                id=content_id,
                chunk_id="chunk_1",
                title=title,
                key=f"{title}.pdf",
                text="Test content",
                start_page=1,
                end_page=1,
                order=0,
            )
        ],
    )


@pytest.mark.asyncio
async def test_collection_manager_collects_all_sources(
    mock_knowledge_base_service,
    mock_quartr_service,
    mock_docx_generator,
    mock_step_notifier,
):
    """Test that collection manager collects from all enabled sources."""
    context = CollectionContext(
        company=_make_company(),
        use_earnings_calls=True,
        upload_scope_id_earnings_calls="scope_123",
        earnings_call_start_date=datetime(2023, 1, 1),
        use_web_sources=True,
        metadata_filter={"key": "value"},
    )

    # Mock the collection functions
    with (
        patch(
            "unique_swot.services.source_management.collection.base.collect_knowledge_base",
            new_callable=AsyncMock,
            return_value=[_make_content("kb_1", "KB Doc")],
        ),
        patch(
            "unique_swot.services.source_management.collection.base.collect_earnings_calls",
            new_callable=AsyncMock,
            return_value=[_make_content("ec_1", "Earnings Call")],
        ),
        patch(
            "unique_swot.services.source_management.collection.base.collect_web_sources",
            return_value=[_make_content("web_1", "Web Source")],
        ),
    ):
        manager = SourceCollectionManager(
            context=context,
            knowledge_base_service=mock_knowledge_base_service,
            quartr_service=mock_quartr_service,
            earnings_call_docx_generator_service=mock_docx_generator,
        )

        sources = await manager.collect(step_notifier=mock_step_notifier)

        assert len(sources) == 3
        assert any(s.title == "KB Doc" for s in sources)
        assert any(s.title == "Earnings Call" for s in sources)
        assert any(s.title == "Web Source" for s in sources)


@pytest.mark.asyncio
async def test_collection_manager_skips_disabled_sources(
    mock_knowledge_base_service, mock_step_notifier
):
    """Test that disabled sources are skipped."""
    context = CollectionContext(
        company=_make_company(),
        use_earnings_calls=False,
        upload_scope_id_earnings_calls="scope_123",
        earnings_call_start_date=datetime(2023, 1, 1),
        use_web_sources=False,
        metadata_filter={"key": "value"},
    )

    with patch(
        "unique_swot.services.source_management.collection.base.collect_knowledge_base",
        new_callable=AsyncMock,
        return_value=[_make_content("kb_1", "KB Doc")],
    ):
        manager = SourceCollectionManager(
            context=context,
            knowledge_base_service=mock_knowledge_base_service,
            quartr_service=None,
            earnings_call_docx_generator_service=Mock(),
        )

        sources = await manager.collect(step_notifier=mock_step_notifier)

        # Only KB sources should be collected
        assert len(sources) == 1
        assert sources[0].title == "KB Doc"


@pytest.mark.asyncio
async def test_collection_manager_no_metadata_filter_skips_kb(
    mock_knowledge_base_service, mock_step_notifier
):
    """Test that no metadata filter skips KB collection."""
    context = CollectionContext(
        company=_make_company(),
        use_earnings_calls=False,
        upload_scope_id_earnings_calls="scope_123",
        earnings_call_start_date=datetime(2023, 1, 1),
        use_web_sources=False,
        metadata_filter=None,  # No filter
    )

    manager = SourceCollectionManager(
        context=context,
        knowledge_base_service=mock_knowledge_base_service,
        quartr_service=None,
        earnings_call_docx_generator_service=Mock(),
    )

    sources = await manager.collect(step_notifier=mock_step_notifier)

    # No sources should be collected
    assert len(sources) == 0


@pytest.mark.asyncio
async def test_collection_manager_no_quartr_service_skips_earnings(
    mock_knowledge_base_service, mock_step_notifier
):
    """Test that missing Quartr service skips earnings calls."""
    context = CollectionContext(
        company=_make_company(),
        use_earnings_calls=True,
        upload_scope_id_earnings_calls="scope_123",
        earnings_call_start_date=datetime(2023, 1, 1),
        use_web_sources=False,
        metadata_filter=None,
    )

    manager = SourceCollectionManager(
        context=context,
        knowledge_base_service=mock_knowledge_base_service,
        quartr_service=None,  # No Quartr service
        earnings_call_docx_generator_service=Mock(),
    )

    sources = await manager.collect(step_notifier=mock_step_notifier)

    # No sources should be collected
    assert len(sources) == 0


@pytest.mark.asyncio
async def test_collection_manager_sends_notifications(
    mock_knowledge_base_service, mock_step_notifier
):
    """Test that notifications are sent during collection."""
    context = CollectionContext(
        company=_make_company(),
        use_earnings_calls=False,
        upload_scope_id_earnings_calls="scope_123",
        earnings_call_start_date=datetime(2023, 1, 1),
        use_web_sources=False,
        metadata_filter={"key": "value"},
    )

    with patch(
        "unique_swot.services.source_management.collection.base.collect_knowledge_base",
        new_callable=AsyncMock,
        return_value=[_make_content()],
    ):
        manager = SourceCollectionManager(
            context=context,
            knowledge_base_service=mock_knowledge_base_service,
            quartr_service=None,
            earnings_call_docx_generator_service=Mock(),
        )

        await manager.collect(step_notifier=mock_step_notifier)

        # Verify notifications were sent
        assert mock_step_notifier.notify.await_count >= 2  # Start and end


@pytest.mark.asyncio
async def test_collection_manager_notification_title(
    mock_knowledge_base_service, mock_step_notifier
):
    """Test notification title property."""
    context = CollectionContext(
        company=_make_company(),
        use_earnings_calls=False,
        upload_scope_id_earnings_calls="scope_123",
        earnings_call_start_date=datetime(2023, 1, 1),
        use_web_sources=False,
        metadata_filter=None,
    )

    manager = SourceCollectionManager(
        context=context,
        knowledge_base_service=mock_knowledge_base_service,
        quartr_service=None,
        earnings_call_docx_generator_service=Mock(),
    )

    assert manager.notification_title == "**Collecting Sources**"


@pytest.mark.asyncio
async def test_collection_context_is_immutable():
    """Test that CollectionContext is frozen/immutable."""
    context = CollectionContext(
        company=_make_company(),
        use_earnings_calls=True,
        upload_scope_id_earnings_calls="scope_123",
        earnings_call_start_date=datetime(2023, 1, 1),
        use_web_sources=True,
        metadata_filter={"key": "value"},
    )

    # Attempting to modify should raise an error
    with pytest.raises(Exception):  # Pydantic raises ValidationError
        context.use_earnings_calls = False
