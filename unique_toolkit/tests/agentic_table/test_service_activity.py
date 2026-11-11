from unittest.mock import AsyncMock, patch

import pytest
from unique_sdk.api_resources._agentic_table import ActivityKind, ActivityStatus

from unique_toolkit.agentic_table.schemas import MagicTableAction
from unique_toolkit.agentic_table.service import AgenticTableService

pytestmark = pytest.mark.ai

_SET_ACTIVITY = "unique_toolkit.agentic_table.service.AgenticTable.set_activity"


def _service() -> AgenticTableService:
    return AgenticTableService(
        user_id="u1", company_id="c1", table_id="t1", event_id="e1"
    )


@pytest.mark.asyncio
async def test_set_activity_sends_the_kind():
    with patch(_SET_ACTIVITY, new=AsyncMock()) as set_activity:
        await _service().set_activity(
            text="Some tags were skipped.",
            activity=MagicTableAction.ADD_META_DATA,
            status=ActivityStatus.COMPLETED,
            kind=ActivityKind.METADATA_TAGS_SKIPPED,
        )

    set_activity.assert_awaited_once_with(
        user_id="u1",
        company_id="c1",
        tableId="t1",
        activity="AddMetaData",
        status="COMPLETED",
        text="Some tags were skipped.",
        kind="METADATA_TAGS_SKIPPED",
    )


@pytest.mark.asyncio
async def test_set_activity_omits_the_kind_by_default():
    with patch(_SET_ACTIVITY, new=AsyncMock()) as set_activity:
        await _service().set_activity(
            text="Importing.", activity=MagicTableAction.ADD_META_DATA
        )

    set_activity.assert_awaited_once_with(
        user_id="u1",
        company_id="c1",
        tableId="t1",
        activity="AddMetaData",
        status="IN_PROGRESS",
        text="Importing.",
    )
