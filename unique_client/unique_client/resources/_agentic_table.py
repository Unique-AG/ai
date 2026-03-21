from typing import Any

from unique_sdk.api_resources._agentic_table import AgenticTable

from .._base import BaseManager, DomainObject


class AgenticTableCellObject(DomainObject):
    """A single agentic table cell."""


class AgenticTableSheetObject(DomainObject):
    """An agentic table sheet with mutation methods."""

    async def update_state(self, **params: Any) -> Any:
        return await AgenticTable.update_sheet_state_async(
            self._user_id, self._company_id, **params
        )

    async def get_data(self, **params: Any) -> Any:
        return await AgenticTable.get_sheet_data_async(
            self._user_id, self._company_id, **params
        )

    async def get_state(self, table_id: str) -> Any:
        return await AgenticTable.get_sheet_state_async(
            self._user_id, self._company_id, table_id
        )

    async def set_column_metadata(self, **params: Any) -> Any:
        return await AgenticTable.set_column_metadata_async(
            self._user_id, self._company_id, **params
        )

    async def bulk_update_status(self, **params: Any) -> Any:
        return await AgenticTable.bulk_update_status_async(
            self._user_id, self._company_id, **params
        )


class AgenticTableManager(BaseManager):
    """Manage AI-powered spreadsheet (agentic table) operations."""

    async def set_cell(self, **params: Any) -> AgenticTableCellObject:
        result = await AgenticTable.set_cell_async(
            self._user_id, self._company_id, **params
        )
        return AgenticTableCellObject(self._user_id, self._company_id, result)

    async def get_cell(self, **params: Any) -> AgenticTableCellObject:
        result = await AgenticTable.get_cell_async(
            self._user_id, self._company_id, **params
        )
        return AgenticTableCellObject(self._user_id, self._company_id, result)

    async def set_activity(self, **params: Any) -> AgenticTableCellObject:
        result = await AgenticTable.set_activity_async(
            self._user_id, self._company_id, **params
        )
        return AgenticTableCellObject(self._user_id, self._company_id, result)

    async def set_artifact(self, **params: Any) -> AgenticTableCellObject:
        result = await AgenticTable.set_artifact_async(
            self._user_id, self._company_id, **params
        )
        return AgenticTableCellObject(self._user_id, self._company_id, result)

    async def update_sheet_state(self, **params: Any) -> Any:
        return await AgenticTable.update_sheet_state_async(
            self._user_id, self._company_id, **params
        )

    async def set_column_metadata(self, **params: Any) -> Any:
        return await AgenticTable.set_column_metadata_async(
            self._user_id, self._company_id, **params
        )

    async def get_sheet_data(self, **params: Any) -> AgenticTableSheetObject:
        result = await AgenticTable.get_sheet_data_async(
            self._user_id, self._company_id, **params
        )
        return AgenticTableSheetObject(self._user_id, self._company_id, result)

    async def get_sheet_state(self, table_id: str) -> Any:
        return await AgenticTable.get_sheet_state_async(
            self._user_id, self._company_id, table_id
        )

    async def set_cell_metadata(self, **params: Any) -> Any:
        return await AgenticTable.set_cell_metadata_async(
            self._user_id, self._company_id, **params
        )

    async def set_multiple_cells(self, table_id: str, cells: list[Any]) -> Any:
        return await AgenticTable.set_multiple_cells_async(
            self._user_id, self._company_id, table_id, cells
        )

    async def bulk_update_status(self, **params: Any) -> Any:
        return await AgenticTable.bulk_update_status_async(
            self._user_id, self._company_id, **params
        )
