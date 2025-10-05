"""Integration tests for folder CRUD operations using generated SDK."""

import pytest

import unique_toolkit.generated.generated_routes.public as unique_SDK


@pytest.mark.integration
@pytest.mark.ai_generated
class TestFolderCRUD:
    """Test complete CRUD cycle for folder operations."""

    def test_folder_crud_cycle__create_update_delete__completes_successfully(
        self, request_context, cleanup_items
    ):
        """
        Purpose: Verify folder CRUD operations work end-to-end with generated SDK.
        Why: Ensures generated code works with real API.
        Setup: RequestContext from test.env, unique_SDK client.
        """
        # Arrange
        test_folder_path = "/test_integration/folder_crud"
        created_scope_id = None

        try:
            # Act 1: Create folder
            create_response = unique_SDK.folder.CreateFolderStructure.request(
                context=request_context,
                paths=[test_folder_path],
            )

            # Assert: Create succeeded
            assert create_response is not None
            assert isinstance(create_response, list)
            assert len(create_response) > 0

            # Extract scope_id from created folder
            created_scope_id = (
                create_response[0].get("id")
                if isinstance(create_response[0], dict)
                else None
            )
            assert created_scope_id is not None, "Created folder should have an ID"

            cleanup_items.append(("folder", created_scope_id))

            # Act 2: Update folder
            update_response = unique_SDK.folder.scopeId.Update.request(
                context=request_context,
                scope_id=created_scope_id,
                name="Updated Folder Name",
                parent_id=None,
            )

            # Assert: Update succeeded
            assert update_response is not None

            # Act 3: Delete folder
            delete_response = unique_SDK.folder.scopeId.DeleteFolder.request(
                context=request_context,
                scope_id=created_scope_id,
            )

            # Assert: Delete succeeded
            assert delete_response is not None

            # Remove from cleanup since we deleted it
            cleanup_items.remove(("folder", created_scope_id))

        except Exception as e:
            # If test fails, ensure cleanup happens
            if created_scope_id:
                try:
                    unique_SDK.folder.scopeId.DeleteFolder.request(
                        context=request_context,
                        scope_id=created_scope_id,
                    )
                except Exception:
                    pass  # Cleanup failed, item might not exist
            raise e

    def test_folder_info__retrieves_folder_details__successfully(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify folder info retrieval works with generated SDK.
        Why: Read operations are critical for SDK completeness.
        Setup: Existing folder scope_id from test.env.
        """
        # Arrange
        test_scope_id = integration_env.get("test_folder_scope_id")
        if not test_scope_id:
            pytest.skip("TEST_FOLDER_SCOPE_ID not set in test.env")

        # Act
        info_response = unique_SDK.folder.info.Get.request(
            context=request_context,
            scope_ids=[test_scope_id],
        )

        # Assert
        assert info_response is not None
        assert isinstance(info_response, (list, dict))
