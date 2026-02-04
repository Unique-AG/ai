from unique_sdk import MagicTableAction

from unique_toolkit.agentic_table.schemas import (
    ArtifactData,
    ArtifactType,
    BaseMetadata,
    MagicTableGenerateArtifactPayload,
    MagicTableRerunRowPayload,
    RerunRowMetadata,
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
