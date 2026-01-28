from unique_sdk.api_resources._agentic_table import MagicTableAction

from unique_toolkit.agentic_table.schemas import (
    ArtifactData,
    ArtifactType,
    BaseMetadata,
    MagicTableGenerateArtifactPayload,
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
