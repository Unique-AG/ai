from unique_toolkit.agentic_table.schemas import BaseMetadata


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
            metadata.additional_sheet_information["clientInformation"]["locationOfBirth"]
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
        assert metadata.additional_sheet_information["clientInformation"]["type"] == "natural_person"
        assert metadata.additional_sheet_information["clientInformation"]["clientId"] == "123"

