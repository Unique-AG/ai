"""Unit tests for AgenticTableService lifecycle methods (create/import/export/wait helpers).

The SDK layer is patched with AsyncMocks; these tests cover parameter mapping,
model validation, error propagation, and the polling logic of the wait helpers.
"""

from unittest.mock import AsyncMock, patch

import pytest
from unique_sdk import (
    AgenticTableSheetState,
    MagicTableArtifactType,
)

from unique_toolkit.agentic_table.schemas import SheetMetadataEntryInput
from unique_toolkit.agentic_table.service import (
    AgenticTableArtifactError,
    AgenticTableRunNotStartedError,
    AgenticTableRunTimeoutError,
    AgenticTableService,
)

pytestmark = pytest.mark.ai

USER_ID = "user_1"
COMPANY_ID = "company_1"
TABLE_ID = "sheet_123"

CREATED_SHEET_RESPONSE = {
    "sheetId": TABLE_ID,
    "dueDiligenceId": "dd_1",
    "name": "UBP RFP",
    "state": "IDLE",
    "chatId": "chat_1",
    "createdBy": USER_ID,
    "companyId": COMPANY_ID,
    "createdAt": "2026-01-01T00:00:00.000Z",
    "dueAt": None,
}


@pytest.fixture
def service() -> AgenticTableService:
    return AgenticTableService(
        user_id=USER_ID, company_id=COMPANY_ID, table_id=TABLE_ID
    )


def _patch(method: str, **kwargs) -> patch:
    return patch(
        f"unique_toolkit.agentic_table.service.AgenticTable.{method}",
        new_callable=AsyncMock,
        **kwargs,
    )


class TestCreateSheet:
    async def test_returns_service_bound_to_new_sheet(self):
        with _patch("create_sheet", return_value=CREATED_SHEET_RESPONSE) as mock:
            service = await AgenticTableService.create_sheet(
                user_id=USER_ID,
                company_id=COMPANY_ID,
                assistant_id="assistant_1",
                name="UBP RFP",
            )

        mock.assert_awaited_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            assistantId="assistant_1",
            name="UBP RFP",
        )
        assert service.table_id == TABLE_ID
        assert service.created_sheet is not None
        assert service.created_sheet.due_diligence_id == "dd_1"
        assert service.created_sheet.state == AgenticTableSheetState.IDLE

    async def test_omits_optional_fields_when_not_given(self):
        with _patch("create_sheet", return_value=CREATED_SHEET_RESPONSE) as mock:
            await AgenticTableService.create_sheet(
                user_id=USER_ID,
                company_id=COMPANY_ID,
                assistant_id="assistant_1",
            )

        mock.assert_awaited_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            assistantId="assistant_1",
        )


class TestImportQuestionsAndSources:
    async def test_passes_only_provided_fields(self, service):
        with _patch("add_metadata", return_value={"status": True}) as mock:
            await service.import_questions_and_sources(
                question_file_ids=["cont_q1"],
                source_file_ids=["cont_s1"],
            )

        mock.assert_awaited_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            tableId=TABLE_ID,
            questionFileIds=["cont_q1"],
            sourceFileIds=["cont_s1"],
        )

    async def test_raises_on_failure_status(self, service):
        with _patch(
            "add_metadata",
            return_value={"status": False, "message": "Sheet is processing"},
        ):
            with pytest.raises(Exception, match="Sheet is processing"):
                await service.import_questions_and_sources(question_texts=["Q1?"])


class TestGenerateArtifacts:
    async def test_triggers_generation(self, service):
        with _patch("generate_artifact", return_value={"status": True}) as mock:
            await service.generate_artifacts([MagicTableArtifactType.FULL_REPORT])

        mock.assert_awaited_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            tableId=TABLE_ID,
            artifactTypes=[MagicTableArtifactType.FULL_REPORT],
        )

    async def test_raises_on_failure_status(self, service):
        with _patch("generate_artifact", return_value={"status": False}):
            with pytest.raises(Exception, match="Failed to trigger"):
                await service.generate_artifacts([MagicTableArtifactType.QUESTIONS])


class TestListArtifacts:
    async def test_validates_models(self, service):
        with _patch(
            "list_artifacts",
            return_value=[
                {
                    "id": "artifact_1",
                    "artifactType": "FULL_REPORT",
                    "artifactState": "DONE",
                    "contentId": "cont_export",
                    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "createdAt": "2026-01-01T00:00:00.000Z",
                    "updatedAt": "2026-01-01T00:01:00.000Z",
                }
            ],
        ):
            artifacts = await service.list_artifacts()

        assert len(artifacts) == 1
        assert artifacts[0].content_id == "cont_export"
        assert artifacts[0].artifact_type == MagicTableArtifactType.FULL_REPORT


class TestSheetMetadata:
    async def test_create_serializes_entries_with_aliases(self, service):
        with _patch("create_sheet_metadata", return_value={"status": True}) as mock:
            await service.create_sheet_metadata(
                [SheetMetadataEntryInput(key="client", value="UBP", exact_filter=True)]
            )

        mock.assert_awaited_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            tableId=TABLE_ID,
            entries=[{"key": "client", "value": "UBP", "exactFilter": True}],
        )

    async def test_delete_passes_metadata_id(self, service):
        with _patch("delete_sheet_metadata", return_value={"status": True}) as mock:
            await service.delete_sheet_metadata("meta_1")

        mock.assert_awaited_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            tableId=TABLE_ID,
            metadataId="meta_1",
        )

    async def test_create_raises_on_failure(self, service):
        with _patch(
            "create_sheet_metadata",
            return_value={"status": False, "message": "not a member"},
        ):
            with pytest.raises(Exception, match="not a member"):
                await service.create_sheet_metadata(
                    [SheetMetadataEntryInput(key="k", value="v")]
                )


class TestWaitForRun:
    async def test_waits_for_processing_then_idle(self, service):
        states = [
            AgenticTableSheetState.IDLE,
            AgenticTableSheetState.PROCESSING,
            AgenticTableSheetState.PROCESSING,
            AgenticTableSheetState.IDLE,
        ]
        with _patch("get_sheet_state", side_effect=states):
            final = await service.wait_for_run(
                start_timeout=10, completion_timeout=10, poll_interval=0
            )
        assert final == AgenticTableSheetState.IDLE

    async def test_returns_stopped_by_user(self, service):
        states = [
            AgenticTableSheetState.PROCESSING,
            AgenticTableSheetState.STOPPED_BY_USER,
        ]
        with _patch("get_sheet_state", side_effect=states):
            final = await service.wait_for_run(
                start_timeout=10, completion_timeout=10, poll_interval=0
            )
        assert final == AgenticTableSheetState.STOPPED_BY_USER

    async def test_raises_when_run_never_starts(self, service):
        with _patch("get_sheet_state", return_value=AgenticTableSheetState.IDLE):
            with pytest.raises(AgenticTableRunNotStartedError):
                await service.wait_for_run(
                    start_timeout=0, completion_timeout=10, poll_interval=0
                )

    async def test_raises_when_run_never_completes(self, service):
        with _patch("get_sheet_state", return_value=AgenticTableSheetState.PROCESSING):
            with pytest.raises(AgenticTableRunTimeoutError):
                await service.wait_for_run(
                    start_timeout=10, completion_timeout=0, poll_interval=0
                )


class TestWaitForArtifacts:
    @staticmethod
    def _artifact(artifact_type: str, state: str, artifact_id: str = "artifact_1"):
        return {
            "id": artifact_id,
            "artifactType": artifact_type,
            "artifactState": state,
            "contentId": "cont_export" if state == "DONE" else None,
            "createdAt": "2026-01-01T00:00:00.000Z",
            "updatedAt": "2026-01-01T00:01:00.000Z",
        }

    async def test_returns_when_all_types_done(self, service):
        responses = [
            [self._artifact("FULL_REPORT", "IN_PROGRESS")],
            [self._artifact("FULL_REPORT", "DONE")],
        ]
        with _patch("list_artifacts", side_effect=responses):
            artifacts = await service.wait_for_artifacts(
                [MagicTableArtifactType.FULL_REPORT], timeout=10, poll_interval=0
            )
        assert len(artifacts) == 1
        assert artifacts[0].content_id == "cont_export"

    async def test_ignores_artifacts_of_other_types(self, service):
        responses = [
            [
                self._artifact("QUESTIONS", "IN_PROGRESS", "artifact_q"),
                self._artifact("FULL_REPORT", "DONE"),
            ],
        ]
        with _patch("list_artifacts", side_effect=responses):
            artifacts = await service.wait_for_artifacts(
                [MagicTableArtifactType.FULL_REPORT], timeout=10, poll_interval=0
            )
        assert len(artifacts) == 1
        assert artifacts[0].artifact_type == MagicTableArtifactType.FULL_REPORT

    async def test_raises_on_error_state(self, service):
        with _patch(
            "list_artifacts",
            return_value=[self._artifact("FULL_REPORT", "ERROR")],
        ):
            with pytest.raises(AgenticTableArtifactError):
                await service.wait_for_artifacts(
                    [MagicTableArtifactType.FULL_REPORT], timeout=10, poll_interval=0
                )

    async def test_raises_on_timeout(self, service):
        with _patch(
            "list_artifacts",
            return_value=[self._artifact("FULL_REPORT", "IN_PROGRESS")],
        ):
            with pytest.raises(AgenticTableRunTimeoutError):
                await service.wait_for_artifacts(
                    [MagicTableArtifactType.FULL_REPORT], timeout=0, poll_interval=0
                )
