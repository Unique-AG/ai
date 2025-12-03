import io
import logging
from pathlib import Path
from typing import Optional, Protocol

import numpy as np
import pandas as pd
import xlsxwriter

from unique_toolkit._common.utils.files import FileMimeType
from unique_toolkit.document_generators.excel_generator.config import (
    ExcelGeneratorConfig,
)

logger = logging.getLogger(__name__)


class UploadStrategy(Protocol):
    """
    Base class for uploading the excel file
    Usage:
    class ChatUploadStrategy(UploadStrategy):
        def __init__(self, content_service: ContentService, chat_id: str, skip_ingestion: bool):
            self.content_service = content_service
            self.chat_id = chat_id
            self.skip_ingestion = skip_ingestion

        def upload(self, excel_data: bytes, file_name: str) -> str:
            created_content = self.content_service.upload_content_from_bytes(
                content=excel_data,
                content_name=file_name,
                mime_type=self.mime_type,
                chat_id=self.chat_id,
                skip_ingestion=self.skip_ingestion,
            )
            return created_content.id
    """

    def upload(self, excel_data: bytes, file_name: str) -> str:
        raise NotImplementedError

    @property
    def mime_type(self) -> str:
        return FileMimeType.XLSX.value


class ExcelGeneratorService:
    """
    A class for generating excel document
    """

    def __init__(self, config: ExcelGeneratorConfig):
        self.config = config

        self.excel_is_initiated = False
        self.excel_is_empty = True
        self.buffer: io.BytesIO = io.BytesIO()
        self.workbook = None
        self.file_export_name: Optional[str] = None

    def init_workbook(self, file_name: str, suffix: Optional[str] = None):
        suffix = suffix or self.config.upload_suffix
        base = Path(file_name).stem
        self.file_export_name = f"{base}{suffix}"

        self.workbook = xlsxwriter.Workbook(self.buffer, {"in_memory": True})

        self.header_format = self.workbook.add_format(self.config.table_header_format)
        self.data_format = self.workbook.add_format(self.config.table_data_format)

        self.excel_is_initiated = True

    def add_worksheet(self, df: pd.DataFrame, name: str):
        if not self.excel_is_initiated:
            raise RuntimeError("Must call init_workbook() first.")

        if df.empty:
            return

        self.excel_is_empty = False
        df = df.fillna("")  # no NaNs

        if self.config.rename_col_map:
            df.rename(columns=self.config.rename_col_map, inplace=True)

        worksheet = self.workbook.add_worksheet(name)

        # headers
        for col, col_name in enumerate(df.columns):
            worksheet.write(0, col, col_name, self.header_format)

        # data
        for row_num, question in df.iterrows():
            for col_num, column in enumerate(df.columns):
                worksheet.write(
                    row_num + 1, col_num, question[column], self.table_data_format
                )

        # autofilter
        worksheet.autofilter(0, 0, len(df) - 1, len(df.columns) - 1)

        # Adjust column widths
        for idx, col in enumerate(df.columns):
            max_length = (
                max(np.median([df[col].astype(str).map(len).max()]), len(col)) + 2
            )
            column_width = min([max_length, 70])
            worksheet.set_column(idx, idx, column_width)

    def finalize(self) -> Optional[bytes]:
        if not self.excel_is_initiated:
            return None

        if self.excel_is_empty:
            return None

        self.workbook.close()
        self.buffer.seek(0)
        return self.buffer.getvalue()

    def get_excel_data_for_upload(self) -> Optional[bytes]:
        excel_data = self.finalize()
        if not excel_data or not self.file_export_name:
            return None

        return excel_data

    def upload(self, uploader: UploadStrategy) -> Optional[str]:
        if excel_data := self.get_excel_data_for_upload():
            return uploader.upload(excel_data, self.file_export_name)

        return None
