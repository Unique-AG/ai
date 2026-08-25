import pytest
from unique_sdk.api_resources._agentic_table import MagicTableAction

from unique_toolkit.agentic_table.schemas import (
    ArtifactData,
    ArtifactType,
    BaseMetadata,
    DDMetadata,
    LibrarySheetRowVerifiedMetadata,
    LibrarySheetRowVerifiedRow,
    MagicTableEvent,
    MagicTableEventTypes,
    MagicTableGenerateArtifactPayload,
    MagicTableLibrarySheetRowVerifiedPayload,
    MagicTableRerunRowPayload,
    MagicTableRerunRowsPayload,
    RerunRowMetadata,
    RerunRowsMetadata,
    SheetType,
)


class TestArtifactType:
    """Test suite for ArtifactType enum."""

    def test_artifact_type_has_questions(self):
        """Test that ArtifactType has QUESTIONS value."""
        assert ArtifactType.QUESTIONS == "QUESTIONS"
        assert "QUESTIONS" in ArtifactType.__members__.values()

    def test_artifact_type_has_full_report(self):
        """Test that ArtifactType has FULL_REPORT value."""
        assert ArtifactType.FULL_REPORT == "FULL_REPORT"
        assert "FULL_REPORT" in ArtifactType.__members__.values()

    def test_artifact_type_has_agentic_report(self):
        """Test that ArtifactType has AGENTIC_REPORT value."""
        assert ArtifactType.AGENTIC_REPORT == "AGENTIC_REPORT"
        assert "AGENTIC_REPORT" in ArtifactType.__members__.values()

    def test_artifact_type_member_count(self):
        """Test that ArtifactType has exactly three members."""
        assert len(ArtifactType) == 3

    def test_artifact_type_all_members(self):
        """Test that all expected artifact types are present."""
        expected_types = {"QUESTIONS", "FULL_REPORT", "AGENTIC_REPORT"}
        actual_types = {member.value for member in ArtifactType}
        assert actual_types == expected_types


class TestArtifactData:
    """Test suite for ArtifactData model."""

    def test_artifact_data_with_questions_type(self):
        """Test ArtifactData creation with QUESTIONS type."""
        data = ArtifactData(artifact_type=ArtifactType.QUESTIONS)
        assert data.artifact_type == ArtifactType.QUESTIONS

    def test_artifact_data_with_full_report_type(self):
        """Test ArtifactData creation with FULL_REPORT type."""
        data = ArtifactData(artifact_type=ArtifactType.FULL_REPORT)
        assert data.artifact_type == ArtifactType.FULL_REPORT

    def test_artifact_data_with_agentic_report_type(self):
        """Test ArtifactData creation with AGENTIC_REPORT type."""
        data = ArtifactData(artifact_type=ArtifactType.AGENTIC_REPORT)
        assert data.artifact_type == ArtifactType.AGENTIC_REPORT

    def test_artifact_data_serialization_questions(self):
        """Test ArtifactData serialization with QUESTIONS type."""
        data = ArtifactData(artifact_type=ArtifactType.QUESTIONS)
        serialized = data.model_dump()
        assert serialized["artifact_type"] == "QUESTIONS"

    def test_artifact_data_serialization_full_report(self):
        """Test ArtifactData serialization with FULL_REPORT type."""
        data = ArtifactData(artifact_type=ArtifactType.FULL_REPORT)
        serialized = data.model_dump()
        assert serialized["artifact_type"] == "FULL_REPORT"

    def test_artifact_data_serialization_agentic_report(self):
        """Test ArtifactData serialization with AGENTIC_REPORT type."""
        data = ArtifactData(artifact_type=ArtifactType.AGENTIC_REPORT)
        serialized = data.model_dump()
        assert serialized["artifact_type"] == "AGENTIC_REPORT"

    def test_artifact_data_deserialization_from_dict_agentic_report(self):
        """Test ArtifactData deserialization from dict with AGENTIC_REPORT."""
        data_dict = {"artifact_type": "AGENTIC_REPORT"}
        data = ArtifactData.model_validate(data_dict)
        assert data.artifact_type == ArtifactType.AGENTIC_REPORT

    def test_artifact_data_deserialization_from_json_agentic_report(self):
        """Test ArtifactData deserialization from JSON with AGENTIC_REPORT."""
        json_str = '{"artifactType": "AGENTIC_REPORT"}'
        data = ArtifactData.model_validate_json(json_str)
        assert data.artifact_type == ArtifactType.AGENTIC_REPORT

    def test_artifact_data_with_string_value(self):
        """Test ArtifactData creation with string value."""
        data = ArtifactData(artifact_type="AGENTIC_REPORT")
        assert data.artifact_type == ArtifactType.AGENTIC_REPORT


class TestMagicTableGenerateArtifactPayload:
    """Test suite for MagicTableGenerateArtifactPayload with different artifact types."""

    def test_generate_artifact_payload_with_agentic_report(self):
        """Test MagicTableGenerateArtifactPayload with AGENTIC_REPORT type."""
        payload = MagicTableGenerateArtifactPayload(
            name="test_module",
            sheet_name="test_sheet",
            action=MagicTableAction.GENERATE_ARTIFACT,
            chat_id="chat_123",
            assistant_id="assistant_123",
            table_id="table_123",
            metadata=BaseMetadata(),
            data=ArtifactData(artifact_type=ArtifactType.AGENTIC_REPORT),
        )
        assert payload.data.artifact_type == ArtifactType.AGENTIC_REPORT
        assert payload.action == MagicTableAction.GENERATE_ARTIFACT

    def test_generate_artifact_payload_with_questions(self):
        """Test MagicTableGenerateArtifactPayload with QUESTIONS type."""
        payload = MagicTableGenerateArtifactPayload(
            name="test_module",
            sheet_name="test_sheet",
            action=MagicTableAction.GENERATE_ARTIFACT,
            chat_id="chat_123",
            assistant_id="assistant_123",
            table_id="table_123",
            metadata=BaseMetadata(),
            data=ArtifactData(artifact_type=ArtifactType.QUESTIONS),
        )
        assert payload.data.artifact_type == ArtifactType.QUESTIONS

    def test_generate_artifact_payload_with_full_report(self):
        """Test MagicTableGenerateArtifactPayload with FULL_REPORT type."""
        payload = MagicTableGenerateArtifactPayload(
            name="test_module",
            sheet_name="test_sheet",
            action=MagicTableAction.GENERATE_ARTIFACT,
            chat_id="chat_123",
            assistant_id="assistant_123",
            table_id="table_123",
            metadata=BaseMetadata(),
            data=ArtifactData(artifact_type=ArtifactType.FULL_REPORT),
        )
        assert payload.data.artifact_type == ArtifactType.FULL_REPORT

    def test_generate_artifact_payload_requested_by_user_id_from_camel_case(self):
        payload = MagicTableGenerateArtifactPayload.model_validate(
            {
                "name": "test_module",
                "sheetName": "test_sheet",
                "action": MagicTableAction.GENERATE_ARTIFACT,
                "chatId": "chat_123",
                "assistantId": "assistant_123",
                "tableId": "table_123",
                "metadata": {},
                "data": {"artifactType": ArtifactType.AGENTIC_REPORT},
                "requestedByUserId": "answer-360",
            }
        )
        assert payload.requested_by_user_id == "answer-360"

    def test_generate_artifact_payload_serialization_agentic_report(self):
        """Test payload serialization with AGENTIC_REPORT maintains type."""
        payload = MagicTableGenerateArtifactPayload(
            name="test_module",
            sheet_name="test_sheet",
            action=MagicTableAction.GENERATE_ARTIFACT,
            chat_id="chat_123",
            assistant_id="assistant_123",
            table_id="table_123",
            metadata=BaseMetadata(),
            data=ArtifactData(artifact_type=ArtifactType.AGENTIC_REPORT),
        )
        serialized = payload.model_dump()
        assert serialized["data"]["artifact_type"] == "AGENTIC_REPORT"


class TestDDMetadata:
    def test_rerun_defaults_false(self):
        meta = DDMetadata()
        assert meta.rerun is False

    def test_rerun_from_camel_case_json(self):
        meta = DDMetadata.model_validate_json('{"rerun": true}')
        assert meta.rerun is True

    def test_rerun_from_legacy_rerun_key(self):
        meta = DDMetadata.model_validate({"Rerun": True})
        assert meta.rerun is True


class TestBaseMetadata:
    def test_additional_sheet_information_default_value(self):
        """Test that additional_sheet_information defaults to empty dict."""
        metadata = BaseMetadata()
        assert metadata.additional_sheet_information == {}

    def test_additional_sheet_information_with_client_data(self):
        """Test that additional_sheet_information can hold complex nested data."""
        client_info = {
            "clientInformation": {
                "type": "natural_person",
                "clientId": "321",
                "fullName": "Test Name",
                "dateOfBirth": "2026-01-08T23:00:00.000Z",
                "locationOfBirth": "Y",
                "associatedEntities": [
                    {
                        "type": "trust",
                        "clientId": "764545",
                        "trustName": "Test Trust",
                        "trustDomicile": "X",
                    }
                ],
            }
        }
        metadata = BaseMetadata(additional_sheet_information=client_info)
        assert metadata.additional_sheet_information == client_info
        assert (
            metadata.additional_sheet_information["clientInformation"]["type"]
            == "natural_person"
        )
        assert (
            metadata.additional_sheet_information["clientInformation"]["clientId"]
            == "321"
        )

    def test_additional_sheet_information_with_nullable_fields(self):
        """Test that additional_sheet_information can handle null values."""
        client_info = {
            "clientInformation": {
                "type": "natural_person",
                "clientId": "321",
                "fullName": "Test Name",
                "dateOfBirth": None,  # Nullable field
                "locationOfBirth": "",  # Empty string
                "associatedEntities": [],
            }
        }
        metadata = BaseMetadata(additional_sheet_information=client_info)
        assert (
            metadata.additional_sheet_information["clientInformation"]["dateOfBirth"]
            is None
        )
        assert (
            metadata.additional_sheet_information["clientInformation"][
                "locationOfBirth"
            ]
            == ""
        )

    def test_additional_sheet_information_deserialization_from_json(self):
        """Test deserialization from JSON with camelCase."""
        json_data = """{
            "additionalSheetInformation": {
                "clientInformation": {
                    "type": "natural_person",
                    "clientId": "123"
                }
            }
        }"""
        metadata = BaseMetadata.model_validate_json(json_data)
        assert (
            metadata.additional_sheet_information["clientInformation"]["type"]
            == "natural_person"
        )
        assert (
            metadata.additional_sheet_information["clientInformation"]["clientId"]
            == "123"
        )


class TestRerunRowMetadata:
    """Test suite for RerunRowMetadata model."""

    def test_rerun_row_metadata_creation(self):
        """Test RerunRowMetadata creation with required fields."""
        metadata = RerunRowMetadata(
            source_file_ids=["file-1", "file-2"],
            row_order=5,
            sheet_type=SheetType.DEFAULT,
        )
        assert metadata.source_file_ids == ["file-1", "file-2"]
        assert metadata.row_order == 5
        assert metadata.sheet_type == SheetType.DEFAULT
        assert metadata.context == ""  # Default value

    def test_rerun_row_metadata_with_context(self):
        """Test RerunRowMetadata creation with optional context."""
        metadata = RerunRowMetadata(
            source_file_ids=["file-1"],
            row_order=10,
            sheet_type=SheetType.LIBRARY,
            context="Additional context for rerun",
        )
        assert metadata.context == "Additional context for rerun"

    def test_rerun_row_metadata_context_none_normalized(self):
        """Test that None context is normalized to empty string."""
        metadata = RerunRowMetadata(
            source_file_ids=["file-1"],
            row_order=1,
            sheet_type=SheetType.DEFAULT,
            context=None,
        )
        assert metadata.context == ""

    def test_rerun_row_metadata_with_additional_sheet_information(self):
        """Test RerunRowMetadata with inherited additional_sheet_information."""
        additional_info = {"clientId": "123", "category": "DDQ"}
        metadata = RerunRowMetadata(
            source_file_ids=["file-1"],
            row_order=3,
            sheet_type=SheetType.DEFAULT,
            additional_sheet_information=additional_info,
        )
        assert metadata.additional_sheet_information == additional_info

    def test_rerun_row_metadata_serialization(self):
        """Test RerunRowMetadata serialization to dict."""
        metadata = RerunRowMetadata(
            source_file_ids=["file-1", "file-2"],
            row_order=5,
            sheet_type=SheetType.DEFAULT,
            context="Test context",
        )
        serialized = metadata.model_dump()
        assert serialized["source_file_ids"] == ["file-1", "file-2"]
        assert serialized["row_order"] == 5
        assert serialized["context"] == "Test context"

    def test_rerun_row_metadata_deserialization_from_json(self):
        """Test RerunRowMetadata deserialization from JSON with camelCase."""
        json_data = """{
            "sourceFileIds": ["file-abc", "file-xyz"],
            "rowOrder": 7,
            "sheetType": "DEFAULT",
            "context": "Rerun for correction"
        }"""
        metadata = RerunRowMetadata.model_validate_json(json_data)
        assert metadata.source_file_ids == ["file-abc", "file-xyz"]
        assert metadata.row_order == 7
        assert metadata.sheet_type == SheetType.DEFAULT
        assert metadata.context == "Rerun for correction"


class TestMagicTableRerunRowPayload:
    """Test suite for MagicTableRerunRowPayload - validates payload structure
    matches monorepo's rfp_agent usage."""

    def test_rerun_row_payload_creation(self):
        """Test MagicTableRerunRowPayload creation matching monorepo pattern."""
        payload = MagicTableRerunRowPayload(
            name="rfp_agent",
            sheet_name="Test Sheet",
            action=MagicTableAction.RERUN_ROW,
            chat_id="chat-123",
            assistant_id="asst-123",
            table_id="table-123",
            metadata=RerunRowMetadata(
                source_file_ids=["file-1", "file-2"],
                row_order=5,
                sheet_type=SheetType.DEFAULT,
                context="Rerun context",
            ),
        )
        assert payload.name == "rfp_agent"
        assert payload.action == MagicTableAction.RERUN_ROW
        assert payload.metadata.source_file_ids == ["file-1", "file-2"]
        assert payload.metadata.row_order == 5
        assert payload.metadata.context == "Rerun context"

    def test_rerun_row_payload_without_context(self):
        """Test payload creation without optional context (like monorepo test_handle_rerun_row_invalid_row)."""
        payload = MagicTableRerunRowPayload(
            name="rfp_agent",
            sheet_name="Test Sheet",
            action=MagicTableAction.RERUN_ROW,
            chat_id="chat-123",
            assistant_id="asst-123",
            table_id="table-123",
            metadata=RerunRowMetadata(
                source_file_ids=["file-1"],
                row_order=99,
                sheet_type=SheetType.DEFAULT,
            ),
        )
        assert payload.metadata.row_order == 99
        assert payload.metadata.context == ""

    def test_rerun_row_payload_serialization(self):
        """Test payload serialization maintains structure."""
        payload = MagicTableRerunRowPayload(
            name="rfp_agent",
            sheet_name="Test Sheet",
            action=MagicTableAction.RERUN_ROW,
            chat_id="chat-123",
            assistant_id="asst-123",
            table_id="table-123",
            metadata=RerunRowMetadata(
                source_file_ids=["file-1"],
                row_order=1,
                sheet_type=SheetType.DEFAULT,
            ),
        )
        serialized = payload.model_dump()
        assert serialized["action"] == "RerunRow"
        assert serialized["metadata"]["source_file_ids"] == ["file-1"]
        assert serialized["metadata"]["row_order"] == 1

    def test_rerun_row_payload_deserialization_from_json(self):
        """Test payload deserialization from JSON (simulating API request)."""
        json_data = """{
            "name": "rfp_agent",
            "sheetName": "Test Sheet",
            "action": "RerunRow",
            "chatId": "chat-456",
            "assistantId": "asst-456",
            "tableId": "table-456",
            "metadata": {
                "sourceFileIds": ["file-a", "file-b"],
                "rowOrder": 10,
                "sheetType": "DEFAULT",
                "context": "Retry with new sources"
            }
        }"""
        payload = MagicTableRerunRowPayload.model_validate_json(json_data)
        assert payload.name == "rfp_agent"
        assert payload.action == MagicTableAction.RERUN_ROW
        assert payload.chat_id == "chat-456"
        assert payload.metadata.source_file_ids == ["file-a", "file-b"]
        assert payload.metadata.row_order == 10
        assert payload.metadata.context == "Retry with new sources"

    def test_rerun_row_action_enum_value(self):
        """Test that RERUN_ROW action is correctly recognized."""
        assert MagicTableAction.RERUN_ROW == "RerunRow"


class TestLibrarySheetRowVerifiedMetadata:
    def test_legacy_payload_without_row_id_still_parses(self):
        metadata = LibrarySheetRowVerifiedMetadata.model_validate({"rowOrder": 3})

        assert metadata.row_order == 3
        assert metadata.row_id is None
        assert metadata.rows == []
        assert metadata.verified_rows == [
            LibrarySheetRowVerifiedRow(row_order=3, row_id=None)
        ]

    def test_optional_row_id_and_rows_default_when_omitted(self):
        metadata = LibrarySheetRowVerifiedMetadata(row_order=3)

        assert metadata.row_order == 3
        assert metadata.row_id is None
        assert metadata.rows == []

    def test_bulk_rows_parse_from_camel_case(self):
        metadata = LibrarySheetRowVerifiedMetadata.model_validate(
            {
                "rowOrder": 3,
                "rowId": "row-3",
                "rows": [
                    {"rowOrder": 3, "rowId": "row-3"},
                    {"rowOrder": 8, "rowId": "row-8"},
                    {"rowOrder": 9},
                ],
            }
        )

        assert metadata.rows == [
            LibrarySheetRowVerifiedRow(row_order=3, row_id="row-3"),
            LibrarySheetRowVerifiedRow(row_order=8, row_id="row-8"),
            LibrarySheetRowVerifiedRow(row_order=9, row_id=None),
        ]
        assert metadata.verified_rows is metadata.rows

    def test_bulk_first_row_order_must_match_scalar(self):
        with pytest.raises(
            ValueError,
            match=r"rows\[0\]\.row_order must match row_order",
        ):
            LibrarySheetRowVerifiedMetadata.model_validate(
                {
                    "rowOrder": 3,
                    "rows": [{"rowOrder": 8, "rowId": "row-8"}],
                }
            )

    def test_bulk_first_row_id_must_match_scalar_when_both_are_present(self):
        with pytest.raises(
            ValueError,
            match=r"rows\[0\]\.row_id must match row_id",
        ):
            LibrarySheetRowVerifiedMetadata.model_validate(
                {
                    "rowOrder": 3,
                    "rowId": "row-3",
                    "rows": [{"rowOrder": 3, "rowId": "different-row"}],
                }
            )

    def test_null_rows_normalize_to_empty(self):
        metadata = LibrarySheetRowVerifiedMetadata.model_validate(
            {"rowOrder": 3, "rowId": "row-3", "rows": None}
        )

        assert metadata.row_id == "row-3"
        assert metadata.rows == []


class TestMagicTableLibrarySheetRowVerifiedPayload:
    def test_bulk_verified_payload_parses_from_wire_format(self):
        payload = MagicTableLibrarySheetRowVerifiedPayload.model_validate(
            {
                "name": "rfp_agent",
                "sheetName": "Library",
                "action": "LibrarySheetRowVerified",
                "chatId": "chat-1",
                "assistantId": "assistant-1",
                "tableId": "table-1",
                "metadata": {
                    "rowOrder": 3,
                    "rowId": "row-3",
                    "rows": [
                        {"rowOrder": 3, "rowId": "row-3"},
                        {"rowOrder": 8, "rowId": "row-8"},
                    ],
                },
            }
        )

        assert payload.action == MagicTableAction.LIBRARY_SHEET_ROW_VERIFIED
        assert payload.metadata.row_order == 3
        assert payload.metadata.row_id == "row-3"
        assert [row.row_order for row in payload.metadata.rows] == [3, 8]

    def test_legacy_payload_without_row_id_still_parses(self):
        payload = MagicTableLibrarySheetRowVerifiedPayload.model_validate(
            {
                "name": "rfp_agent",
                "sheetName": "Library",
                "action": "LibrarySheetRowVerified",
                "chatId": "chat-1",
                "assistantId": "assistant-1",
                "tableId": "table-1",
                "metadata": {"rowOrder": 3},
            }
        )

        assert payload.metadata.row_order == 3
        assert payload.metadata.row_id is None
        assert payload.metadata.rows == []


class TestRerunRowsMetadata:
    """Test suite for RerunRowsMetadata model (bulk re-run of a row selection)."""

    def test_rerun_rows_metadata_creation(self):
        """Test RerunRowsMetadata creation with required fields."""
        metadata = RerunRowsMetadata(
            source_file_ids=["file-1", "file-2"],
            row_orders=[3, 5, 8],
            sheet_type=SheetType.DEFAULT,
        )
        assert metadata.source_file_ids == ["file-1", "file-2"]
        assert metadata.row_orders == [3, 5, 8]
        assert metadata.sheet_type == SheetType.DEFAULT
        assert metadata.context == ""  # Default value

    def test_rerun_rows_metadata_preserves_selection_order(self):
        """Selection order is part of the contract: rows run in the order sent."""
        metadata = RerunRowsMetadata(
            source_file_ids=["file-1"],
            row_orders=[9, 2, 7],
            sheet_type=SheetType.DEFAULT,
        )
        assert metadata.row_orders == [9, 2, 7]

    def test_rerun_rows_metadata_dedupes_and_drops_non_positive_rows(self):
        """Duplicates and non-positive rows (header row 0 / negatives) are dropped."""
        metadata = RerunRowsMetadata(
            source_file_ids=["file-1"],
            row_orders=[4, 4, 0, -1, 4, 2],
            sheet_type=SheetType.DEFAULT,
        )
        assert metadata.row_orders == [4, 2]

    def test_rerun_rows_metadata_accepts_empty_selection(self):
        """An empty selection parses; the agent fails the run and releases the lock."""
        metadata = RerunRowsMetadata(
            source_file_ids=["file-1"],
            row_orders=[],
            sheet_type=SheetType.DEFAULT,
        )
        assert metadata.row_orders == []

    def test_rerun_rows_metadata_omitted_lists_default_to_empty(self):
        """Missing sourceFileIds / rowOrders still parse so the agent can fail and unlock."""
        metadata = RerunRowsMetadata(sheet_type=SheetType.DEFAULT)
        assert metadata.source_file_ids == []
        assert metadata.row_orders == []

    def test_rerun_rows_metadata_null_lists_normalized(self):
        """Null sourceFileIds / rowOrders become empty lists, same as omitted."""
        metadata = RerunRowsMetadata(
            source_file_ids=None,
            row_orders=None,
            sheet_type=SheetType.DEFAULT,
        )
        assert metadata.source_file_ids == []
        assert metadata.row_orders == []

    def test_rerun_rows_metadata_context_none_normalized(self):
        """Test that None context is normalized to empty string."""
        metadata = RerunRowsMetadata(
            source_file_ids=["file-1"],
            row_orders=[1],
            sheet_type=SheetType.DEFAULT,
            context=None,
        )
        assert metadata.context == ""

    def test_rerun_rows_metadata_with_additional_sheet_information(self):
        """Test RerunRowsMetadata with inherited additional_sheet_information."""
        additional_info = {"clientId": "123", "category": "DDQ"}
        metadata = RerunRowsMetadata(
            source_file_ids=["file-1"],
            row_orders=[1, 2],
            sheet_type=SheetType.DEFAULT,
            additional_sheet_information=additional_info,
        )
        assert metadata.additional_sheet_information == additional_info

    def test_rerun_rows_metadata_deserialization_from_json(self):
        """Test RerunRowsMetadata deserialization from JSON with camelCase."""
        json_data = """{
            "sourceFileIds": ["file-abc", "file-xyz"],
            "rowOrders": [7, 11],
            "sheetType": "DEFAULT",
            "context": "Rerun for correction"
        }"""
        metadata = RerunRowsMetadata.model_validate_json(json_data)
        assert metadata.source_file_ids == ["file-abc", "file-xyz"]
        assert metadata.row_orders == [7, 11]
        assert metadata.sheet_type == SheetType.DEFAULT
        assert metadata.context == "Rerun for correction"

    def test_rerun_rows_metadata_json_drops_duplicates_and_non_positive(self):
        """Wire camelCase lists are normalized the same way as constructor input."""
        json_data = """{
            "sourceFileIds": null,
            "rowOrders": [4, 0, 4, -1, 2]
        }"""
        metadata = RerunRowsMetadata.model_validate_json(json_data)
        assert metadata.source_file_ids == []
        assert metadata.row_orders == [4, 2]


class TestMagicTableRerunRowsPayload:
    """Test suite for MagicTableRerunRowsPayload - the bulk sibling of
    MagicTableRerunRowPayload, dispatched by the same action discriminator."""

    def test_rerun_rows_payload_creation(self):
        """Test MagicTableRerunRowsPayload creation."""
        payload = MagicTableRerunRowsPayload(
            name="rfp_agent",
            sheet_name="Test Sheet",
            action=MagicTableAction.RERUN_ROWS,
            chat_id="chat-123",
            assistant_id="asst-123",
            table_id="table-123",
            metadata=RerunRowsMetadata(
                source_file_ids=["file-1", "file-2"],
                row_orders=[5, 6],
                sheet_type=SheetType.DEFAULT,
                context="Rerun context",
            ),
        )
        assert payload.name == "rfp_agent"
        assert payload.action == MagicTableAction.RERUN_ROWS
        assert payload.metadata.source_file_ids == ["file-1", "file-2"]
        assert payload.metadata.row_orders == [5, 6]
        assert payload.metadata.context == "Rerun context"

    def test_rerun_rows_payload_serialization(self):
        """Test payload serialization maintains structure."""
        payload = MagicTableRerunRowsPayload(
            name="rfp_agent",
            sheet_name="Test Sheet",
            action=MagicTableAction.RERUN_ROWS,
            chat_id="chat-123",
            assistant_id="asst-123",
            table_id="table-123",
            metadata=RerunRowsMetadata(
                source_file_ids=["file-1"],
                row_orders=[1, 2, 3],
                sheet_type=SheetType.DEFAULT,
            ),
        )
        serialized = payload.model_dump()
        assert serialized["action"] == "RerunRows"
        assert serialized["metadata"]["source_file_ids"] == ["file-1"]
        assert serialized["metadata"]["row_orders"] == [1, 2, 3]

    def test_rerun_rows_payload_deserialization_omits_optional_lists(self):
        """User-triggered bulk rerun may omit sourceFileIds and send null rowOrders."""
        json_data = """{
            "name": "rfp_agent",
            "sheetName": "Test Sheet",
            "action": "RerunRows",
            "chatId": "chat-456",
            "assistantId": "asst-456",
            "tableId": "table-456",
            "metadata": {
                "rowOrders": null,
                "sheetType": "DEFAULT"
            }
        }"""
        payload = MagicTableRerunRowsPayload.model_validate_json(json_data)
        assert payload.metadata.source_file_ids == []
        assert payload.metadata.row_orders == []

    def test_rerun_rows_payload_deserialization_from_json(self):
        """Test payload deserialization from JSON (simulating API request)."""
        json_data = """{
            "name": "rfp_agent",
            "sheetName": "Test Sheet",
            "action": "RerunRows",
            "chatId": "chat-456",
            "assistantId": "asst-456",
            "tableId": "table-456",
            "metadata": {
                "sourceFileIds": ["file-a", "file-b"],
                "rowOrders": [10, 12],
                "sheetType": "DEFAULT",
                "context": "Retry with new sources"
            }
        }"""
        payload = MagicTableRerunRowsPayload.model_validate_json(json_data)
        assert payload.name == "rfp_agent"
        assert payload.action == MagicTableAction.RERUN_ROWS
        assert payload.chat_id == "chat-456"
        assert payload.metadata.source_file_ids == ["file-a", "file-b"]
        assert payload.metadata.row_orders == [10, 12]
        assert payload.metadata.context == "Retry with new sources"

    def test_rerun_rows_action_enum_value(self):
        """Test that RERUN_ROWS action is correctly recognized."""
        assert MagicTableAction.RERUN_ROWS == "RerunRows"


class TestRerunEventDiscrimination:
    """The two rerun actions must route to distinct payload models, so that adding
    the bulk variant cannot silently swallow a single-row event or vice versa."""

    def _event_json(self, *, event: str, action: str, metadata: str) -> str:
        return f"""{{
            "id": "evt-1",
            "event": "{event}",
            "userId": "user-1",
            "companyId": "company-1",
            "payload": {{
                "name": "rfp_agent",
                "sheetName": "Test Sheet",
                "action": "{action}",
                "chatId": "chat-1",
                "assistantId": "asst-1",
                "tableId": "table-1",
                "metadata": {metadata}
            }}
        }}"""

    def test_rerun_rows_event_resolves_to_bulk_payload(self):
        """A rerun-rows event parses into MagicTableRerunRowsPayload."""
        event = MagicTableEvent.model_validate_json(
            self._event_json(
                event=MagicTableEventTypes.RERUN_ROWS,
                action=MagicTableAction.RERUN_ROWS,
                metadata='{"sourceFileIds": ["file-1"], "rowOrders": [2, 4]}',
            )
        )
        assert event.event == MagicTableEventTypes.RERUN_ROWS
        assert isinstance(event.payload, MagicTableRerunRowsPayload)
        assert event.payload.metadata.row_orders == [2, 4]

    def test_rerun_rows_event_parses_when_metadata_lists_are_omitted(self):
        """A user-triggered bulk rerun with no source or row lists still parses."""
        event = MagicTableEvent.model_validate_json(
            self._event_json(
                event=MagicTableEventTypes.RERUN_ROWS,
                action=MagicTableAction.RERUN_ROWS,
                metadata="{}",
            )
        )
        assert isinstance(event.payload, MagicTableRerunRowsPayload)
        assert event.payload.metadata.source_file_ids == []
        assert event.payload.metadata.row_orders == []

    def test_rerun_row_event_still_resolves_to_single_row_payload(self):
        """The existing single-row event is unaffected by the new union member."""
        event = MagicTableEvent.model_validate_json(
            self._event_json(
                event=MagicTableEventTypes.RERUN_ROW,
                action=MagicTableAction.RERUN_ROW,
                metadata='{"sourceFileIds": ["file-1"], "rowOrder": 2}',
            )
        )
        assert isinstance(event.payload, MagicTableRerunRowPayload)
        assert event.payload.metadata.row_order == 2

    def test_rerun_rows_event_type_wire_value(self):
        """Test that the bulk event name matches the platform contract."""
        assert MagicTableEventTypes.RERUN_ROWS == "unique.magic-table.rerun-rows"
