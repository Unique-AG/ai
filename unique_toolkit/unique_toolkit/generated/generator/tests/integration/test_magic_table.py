"""Integration tests for magic table operations using generated SDK."""

import pytest

import unique_toolkit.generated.generated_routes.public as unique_SDK


@pytest.mark.integration
@pytest.mark.ai_generated
class TestMagicTableOperations:
    """Test magic table CRUD operations."""

    def test_magic_table_get__retrieves_table__successfully(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify magic table retrieval works.
        Why: Table access is fundamental for table operations.
        Setup: Request context and test table ID.
        """
        # Arrange
        test_table_id = integration_env.get("test_table_id")
        if not test_table_id:
            pytest.skip("TEST_TABLE_ID required for magic table tests")

        # Act
        response = unique_SDK.magic_table.tableId.GetTable.request(
            context=request_context,
            table_id=test_table_id,
        )

        # Assert
        assert response is not None

    def test_magic_table_create_row__adds_row__successfully(
        self, request_context, integration_env, cleanup_items
    ):
        """
        Purpose: Verify row creation in magic table works.
        Why: Row operations are core table functionality.
        Setup: Request context and test table ID.
        """
        # Arrange
        test_table_id = integration_env.get("test_table_id")
        if not test_table_id:
            pytest.skip("TEST_TABLE_ID required")

        # Act
        response = unique_SDK.magic_table.tableId.create_row_with_empty_cells.CreateRowWithEmptyCells.request(
            context=request_context,
            table_id=test_table_id,
        )

        # Assert
        assert response is not None
        row_id = response.id if hasattr(response, "id") else response.get("id")

        if row_id:
            cleanup_items.append(("table_row", row_id))

    def test_magic_table_get_rows__retrieves_all_rows__successfully(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify retrieving all rows from table works.
        Why: Bulk row access is common operation.
        Setup: Request context and test table ID.
        """
        # Arrange
        test_table_id = integration_env.get("test_table_id")
        if not test_table_id:
            pytest.skip("TEST_TABLE_ID required")

        # Act
        response = unique_SDK.magic_table.tableId.rows.GetRows.request(
            context=request_context,
            table_id=test_table_id,
        )

        # Assert
        assert response is not None

    def test_magic_table_bulk_upsert_cells__updates_multiple_cells__successfully(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify bulk cell upsert operation works.
        Why: Batch updates are important for table performance.
        Setup: Request context, table ID, and cell data.
        """
        # Arrange
        test_table_id = integration_env.get("test_table_id")
        if not test_table_id:
            pytest.skip("TEST_TABLE_ID required")

        # Act
        response = (
            unique_SDK.magic_table.tableId.cells.bulk_upsert.BulkUpsertCells.request(
                context=request_context,
                table_id=test_table_id,
                cells=[
                    {
                        "rowId": "test_row_1",
                        "columnId": "test_col_1",
                        "value": "Integration test value",
                    }
                ],
            )
        )

        # Assert
        assert response is not None
