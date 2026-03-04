import io
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import xlsxwriter

from unique_toolkit._common.excel_generator.config import ExcelGeneratorConfig

_LOGGER = logging.getLogger(__name__)


class ExcelGeneratorService:
    def __init__(self, config: ExcelGeneratorConfig) -> None:
        self._config = config
        self._excel_is_initiated = False
        self._excel_is_empty = True
        self._buffer: io.BytesIO | None = None
        self._workbook: xlsxwriter.Workbook | None = None
        self._table_header_format: xlsxwriter.format.Format | None = None
        self._table_data_format: xlsxwriter.format.Format | None = None
        self._file_export_name: str = ""

    @property
    def file_export_name(self) -> str:
        """The final filename used for the generated workbook."""
        return self._file_export_name

    def init_workbook(self, file_name: str, suffix: str | None = None) -> None:
        """Initialize an in-memory xlsxwriter workbook.

        Args:
            file_name: Base file name (stem is extracted; callers should strip
                any chat prefixes before passing this value).
            suffix: Override the suffix from config. Defaults to config.upload_suffix.
        """
        self._excel_is_initiated = True
        self._excel_is_empty = True

        base_file_name = Path(file_name).stem
        effective_suffix = suffix if suffix is not None else self._config.upload_suffix
        self._file_export_name = f"{base_file_name}{effective_suffix}"

        self._buffer = io.BytesIO()
        self._workbook = xlsxwriter.Workbook(self._buffer, {"in_memory": True})
        self._table_header_format = self._workbook.add_format(
            self._config.table_header_format
        )
        self._table_data_format = self._workbook.add_format(
            self._config.table_data_format
        )

    def add_worksheet(self, dataframe: pd.DataFrame, worksheet_name: str) -> None:
        """Add a worksheet from a DataFrame.

        Args:
            dataframe: Data to write. Empty DataFrames are silently skipped.
            worksheet_name: Name of the worksheet (Excel limit: 31 characters).
        """
        if not self._excel_is_initiated or self._workbook is None:
            _LOGGER.error(
                "Workbook not initialized. Call init_workbook() before add_worksheet()."
            )
            return

        if dataframe.empty:
            return

        self._excel_is_empty = False
        dataframe = dataframe.fillna("")

        if self._config.rename_col_map:
            dataframe = dataframe.rename(columns=self._config.rename_col_map)

        worksheet = self._workbook.add_worksheet(worksheet_name)

        for col_num, column in enumerate(dataframe.columns):
            worksheet.write(0, col_num, column, self._table_header_format)

        for row_num, row in dataframe.iterrows():
            for col_num, column in enumerate(dataframe.columns):
                worksheet.write(
                    row_num + 1,  # type: ignore[operator]
                    col_num,
                    row[column],
                    self._table_data_format,
                )

        worksheet.autofilter(0, 0, len(dataframe) - 1, len(dataframe.columns) - 1)

        for idx, col in enumerate(dataframe.columns):
            max_length = (
                max(
                    float(np.median([dataframe[col].astype(str).map(len).max()])),
                    float(len(col)),
                )
                + 2
            )
            worksheet.set_column(idx, idx, min(max_length, 70))

    def generate(self) -> bytes | None:
        """Close the workbook and return the raw XLSX bytes.

        Returns:
            XLSX bytes, or None if the workbook was not initialised or is empty.
        """
        if not self._excel_is_initiated or self._workbook is None:
            _LOGGER.error(
                "Workbook not initialized. Call init_workbook() before generate()."
            )
            return None

        if self._excel_is_empty:
            _LOGGER.warning("The Excel file is empty. Returning None.")
            return None

        self._workbook.close()
        assert self._buffer is not None
        self._buffer.seek(0)
        return self._buffer.getvalue()
