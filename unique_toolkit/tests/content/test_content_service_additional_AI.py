"""
Additional tests for content service to improve coverage.
These tests focus on class methods, deprecated properties, and file type detection.
"""

from unittest.mock import Mock, patch

import pytest

from unique_toolkit.app.schemas import BaseEvent, EventName
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.service import ContentService


@pytest.mark.ai
class TestContentServiceAdditional:
    """Additional tests for content service to improve coverage."""

    def test_from_event__with_chat_event_AI(self, base_chat_event):
        """
        Purpose: Verify from_event class method works with ChatEvent.
        Why this matters: Tests the class method factory pattern.
        Setup summary: Use base_chat_event fixture and test from_event method.
        """
        # Arrange
        chat_event = base_chat_event

        # Act
        service = ContentService.from_event(chat_event)

        # Assert
        assert service._company_id == "test_company_123"
        assert service._user_id == "test_user_123"
        assert service._chat_id == "test_chat_123"
        assert service._metadata_filter is None

    def test_from_event__with_base_event_AI(self):
        """
        Purpose: Verify from_event class method works with BaseEvent.
        Why this matters: Tests the class method factory pattern with different event types.
        Setup summary: Create BaseEvent and test from_event method.
        """
        # Arrange
        base_event = BaseEvent(
            id="test-id",
            company_id="base_company",
            user_id="base_user",
            event=EventName.EXTERNAL_MODULE_CHOSEN,
        )

        # Act
        service = ContentService.from_event(base_event)

        # Assert
        assert service._company_id == "base_company"
        assert service._user_id == "base_user"
        assert service._chat_id is None
        assert service._metadata_filter is None

    def test_from_settings__with_none_AI(self):
        """
        Purpose: Verify from_settings class method with None parameter.
        Why this matters: Tests the class method factory pattern with default settings.
        Setup summary: Mock UniqueSettings and test from_settings method.
        """
        # Arrange
        with patch.object(
            UniqueSettings, "from_env_auto_with_sdk_init"
        ) as mock_from_env:
            mock_settings = Mock()
            mock_settings.auth.company_id.get_secret_value.return_value = "test_company"
            mock_settings.auth.user_id.get_secret_value.return_value = "test_user"
            mock_from_env.return_value = mock_settings

            # Act
            service = ContentService.from_settings()

            # Assert
            assert service._company_id == "test_company"
            assert service._user_id == "test_user"
            assert service._metadata_filter is None

    def test_from_settings__with_string_AI(self):
        """
        Purpose: Verify from_settings class method with string parameter.
        Why this matters: Tests the class method factory pattern with filename.
        Setup summary: Mock UniqueSettings and test from_settings method with string.
        """
        # Arrange
        with patch.object(
            UniqueSettings, "from_env_auto_with_sdk_init"
        ) as mock_from_env:
            mock_settings = Mock()
            mock_settings.auth.company_id.get_secret_value.return_value = "test_company"
            mock_settings.auth.user_id.get_secret_value.return_value = "test_user"
            mock_from_env.return_value = mock_settings

            # Act
            service = ContentService.from_settings("config.json")

            # Assert
            assert service._company_id == "test_company"
            assert service._user_id == "test_user"
            assert service._metadata_filter is None
            mock_from_env.assert_called_once_with(filename="config.json")

    def test_from_settings__with_settings_object_AI(self):
        """
        Purpose: Verify from_settings class method with settings object.
        Why this matters: Tests the class method factory pattern with existing settings.
        Setup summary: Create mock settings object and test from_settings method.
        """
        # Arrange
        mock_settings = Mock()
        mock_settings.auth.company_id.get_secret_value.return_value = "test_company"
        mock_settings.auth.user_id.get_secret_value.return_value = "test_user"

        # Act
        service = ContentService.from_settings(mock_settings)

        # Assert
        assert service._company_id == "test_company"
        assert service._user_id == "test_user"
        assert service._metadata_filter is None

    def test_from_settings__with_metadata_filter_AI(self):
        """
        Purpose: Verify from_settings class method with metadata filter.
        Why this matters: Tests the class method factory pattern with metadata filter.
        Setup summary: Create mock settings object and test from_settings method with metadata filter.
        """
        # Arrange
        mock_settings = Mock()
        mock_settings.auth.company_id.get_secret_value.return_value = "test_company"
        mock_settings.auth.user_id.get_secret_value.return_value = "test_user"
        metadata_filter = {"key": "value"}

        # Act
        service = ContentService.from_settings(mock_settings, metadata_filter)

        # Assert
        assert service._company_id == "test_company"
        assert service._user_id == "test_user"
        assert service._metadata_filter == metadata_filter

    def test_deprecated_event_property_AI(self):
        """
        Purpose: Verify deprecated event property still works.
        Why this matters: Ensures backward compatibility for deprecated properties.
        Setup summary: Create service with event and test deprecated property.
        """
        # Arrange
        from tests.test_obj_factory import get_event_obj

        event = get_event_obj(
            user_id="test_user",
            company_id="test_company",
            chat_id="test_chat",
            assistant_id="test_assistant",
        )
        service = ContentService(event)

        # Act
        result = service.event

        # Assert
        assert result == event

    def test_deprecated_company_id_property_AI(self):
        """
        Purpose: Verify deprecated company_id property still works.
        Why this matters: Ensures backward compatibility for deprecated properties.
        Setup summary: Create service and test deprecated property.
        """
        # Arrange
        service = ContentService(company_id="test_company", user_id="test_user")

        # Act
        result = service.company_id

        # Assert
        assert result == "test_company"

    def test_deprecated_company_id_setter_AI(self):
        """
        Purpose: Verify deprecated company_id setter still works.
        Why this matters: Ensures backward compatibility for deprecated properties.
        Setup summary: Create service and test deprecated setter.
        """
        # Arrange
        service = ContentService(company_id="test_company", user_id="test_user")

        # Act
        service.company_id = "new_company"

        # Assert
        assert service._company_id == "new_company"

    def test_deprecated_user_id_property_AI(self):
        """
        Purpose: Verify deprecated user_id property still works.
        Why this matters: Ensures backward compatibility for deprecated properties.
        Setup summary: Create service and test deprecated property.
        """
        # Arrange
        service = ContentService(company_id="test_company", user_id="test_user")

        # Act
        result = service.user_id

        # Assert
        assert result == "test_user"

    def test_deprecated_user_id_setter_AI(self):
        """
        Purpose: Verify deprecated user_id setter still works.
        Why this matters: Ensures backward compatibility for deprecated properties.
        Setup summary: Create service and test deprecated setter.
        """
        # Arrange
        service = ContentService(company_id="test_company", user_id="test_user")

        # Act
        service.user_id = "new_user"

        # Assert
        assert service._user_id == "new_user"

    def test_deprecated_chat_id_property_AI(self):
        """
        Purpose: Verify deprecated chat_id property still works.
        Why this matters: Ensures backward compatibility for deprecated properties.
        Setup summary: Create service and test deprecated property.
        """
        # Arrange
        service = ContentService(
            company_id="test_company", user_id="test_user", chat_id="test_chat"
        )

        # Act
        result = service.chat_id

        # Assert
        assert result == "test_chat"

    def test_deprecated_chat_id_setter_AI(self):
        """
        Purpose: Verify deprecated chat_id setter still works.
        Why this matters: Ensures backward compatibility for deprecated properties.
        Setup summary: Create service and test deprecated setter.
        """
        # Arrange
        service = ContentService(
            company_id="test_company", user_id="test_user", chat_id="test_chat"
        )

        # Act
        service.chat_id = "new_chat"

        # Assert
        assert service._chat_id == "new_chat"

    def test_deprecated_metadata_filter_property_AI(self):
        """
        Purpose: Verify deprecated metadata_filter property still works.
        Why this matters: Ensures backward compatibility for deprecated properties.
        Setup summary: Create service and test deprecated property.
        """
        # Arrange
        metadata_filter = {"key": "value"}
        service = ContentService(
            company_id="test_company",
            user_id="test_user",
            metadata_filter=metadata_filter,
        )

        # Act
        result = service.metadata_filter

        # Assert
        assert result == metadata_filter

    def test_deprecated_metadata_filter_setter_AI(self):
        """
        Purpose: Verify deprecated metadata_filter setter still works.
        Why this matters: Ensures backward compatibility for deprecated properties.
        Setup summary: Create service and test deprecated setter.
        """
        # Arrange
        service = ContentService(company_id="test_company", user_id="test_user")

        # Act
        service.metadata_filter = {"new_key": "new_value"}

        # Assert
        assert service._metadata_filter == {"new_key": "new_value"}

    def test_is_file_content__with_pdf_AI(self):
        """
        Purpose: Verify is_file_content correctly identifies PDF files.
        Why this matters: Tests file type detection for document files.
        Setup summary: Test is_file_content with PDF filename.
        """
        # Arrange
        service = ContentService(company_id="test_company", user_id="test_user")

        # Act
        result = service.is_file_content("document.pdf")

        # Assert
        assert result is True

    def test_is_file_content__with_docx_AI(self):
        """
        Purpose: Verify is_file_content correctly identifies DOCX files.
        Why this matters: Tests file type detection for document files.
        Setup summary: Test is_file_content with DOCX filename.
        """
        # Arrange
        service = ContentService(company_id="test_company", user_id="test_user")

        # Act
        result = service.is_file_content("document.docx")

        # Assert
        assert result is True

    def test_is_file_content__with_xlsx_AI(self):
        """
        Purpose: Verify is_file_content correctly identifies XLSX files.
        Why this matters: Tests file type detection for spreadsheet files.
        Setup summary: Test is_file_content with XLSX filename.
        """
        # Arrange
        service = ContentService(company_id="test_company", user_id="test_user")

        # Act
        result = service.is_file_content("spreadsheet.xlsx")

        # Assert
        assert result is True

    def test_is_file_content__with_unknown_extension_AI(self):
        """
        Purpose: Verify is_file_content returns False for unknown file types.
        Why this matters: Tests file type detection for unrecognized files.
        Setup summary: Test is_file_content with unknown filename.
        """
        # Arrange
        service = ContentService(company_id="test_company", user_id="test_user")

        # Act
        result = service.is_file_content("unknown.xyz")

        # Assert
        assert result is False

    def test_is_file_content__with_no_extension_AI(self):
        """
        Purpose: Verify is_file_content returns False for files without extensions.
        Why this matters: Tests file type detection for files without extensions.
        Setup summary: Test is_file_content with filename without extension.
        """
        # Arrange
        service = ContentService(company_id="test_company", user_id="test_user")

        # Act
        result = service.is_file_content("filename")

        # Assert
        assert result is False

    def test_is_image_content__with_jpeg_AI(self):
        """
        Purpose: Verify is_image_content correctly identifies JPEG files.
        Why this matters: Tests file type detection for image files.
        Setup summary: Test is_image_content with JPEG filename.
        """
        # Arrange
        service = ContentService(company_id="test_company", user_id="test_user")

        # Act
        result = service.is_image_content("image.jpg")

        # Assert
        assert result is True

    def test_is_image_content__with_png_AI(self):
        """
        Purpose: Verify is_image_content correctly identifies PNG files.
        Why this matters: Tests file type detection for image files.
        Setup summary: Test is_image_content with PNG filename.
        """
        # Arrange
        service = ContentService(company_id="test_company", user_id="test_user")

        # Act
        result = service.is_image_content("image.png")

        # Assert
        assert result is True

    def test_is_image_content__with_gif_AI(self):
        """
        Purpose: Verify is_image_content correctly identifies GIF files.
        Why this matters: Tests file type detection for image files.
        Setup summary: Test is_image_content with GIF filename.
        """
        # Arrange
        service = ContentService(company_id="test_company", user_id="test_user")

        # Act
        result = service.is_image_content("image.gif")

        # Assert
        assert result is True

    def test_is_image_content__with_unknown_extension_AI(self):
        """
        Purpose: Verify is_image_content returns False for unknown file types.
        Why this matters: Tests file type detection for unrecognized files.
        Setup summary: Test is_image_content with unknown filename.
        """
        # Arrange
        service = ContentService(company_id="test_company", user_id="test_user")

        # Act
        result = service.is_image_content("unknown.xyz")

        # Assert
        assert result is False

    def test_is_image_content__with_no_extension_AI(self):
        """
        Purpose: Verify is_image_content returns False for files without extensions.
        Why this matters: Tests file type detection for files without extensions.
        Setup summary: Test is_image_content with filename without extension.
        """
        # Arrange
        service = ContentService(company_id="test_company", user_id="test_user")

        # Act
        result = service.is_image_content("filename")

        # Assert
        assert result is False

    def test_get_documents_uploaded_to_chat_AI(self):
        """
        Purpose: Verify get_documents_uploaded_to_chat returns only file content.
        Why this matters: Tests filtering logic for document content.
        Setup summary: Mock search_contents to return mixed content types.
        """
        # Arrange
        service = ContentService(
            company_id="test_company", user_id="test_user", chat_id="test_chat"
        )

        mock_contents = [
            Mock(key="document.pdf", id="1"),
            Mock(key="image.jpg", id="2"),
            Mock(key="spreadsheet.xlsx", id="3"),
        ]

        with patch.object(service, "search_contents", return_value=mock_contents):
            with patch.object(service, "is_file_content") as mock_is_file:
                mock_is_file.side_effect = [
                    True,
                    False,
                    True,
                ]  # PDF and XLSX are files, JPG is not

                # Act
                result = service.get_documents_uploaded_to_chat()

                # Assert
                assert len(result) == 2
                assert result[0].id == "1"  # PDF
                assert result[1].id == "3"  # XLSX

    def test_get_images_uploaded_to_chat_AI(self):
        """
        Purpose: Verify get_images_uploaded_to_chat returns only image content.
        Why this matters: Tests filtering logic for image content.
        Setup summary: Mock search_contents to return mixed content types.
        """
        # Arrange
        service = ContentService(
            company_id="test_company", user_id="test_user", chat_id="test_chat"
        )

        mock_contents = [
            Mock(key="document.pdf", id="1"),
            Mock(key="image.jpg", id="2"),
            Mock(key="image.png", id="3"),
        ]

        with patch.object(service, "search_contents", return_value=mock_contents):
            with patch.object(service, "is_image_content") as mock_is_image:
                mock_is_image.side_effect = [
                    False,
                    True,
                    True,
                ]  # PDF is not image, JPG and PNG are

                # Act
                result = service.get_images_uploaded_to_chat()

                # Assert
                assert len(result) == 2
                assert result[0].id == "2"  # JPG
                assert result[1].id == "3"  # PNG
