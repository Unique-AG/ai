import io
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import xlsxwriter
from quart import g, has_app_context
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.content.service import ContentService
from unique_toolkit._common.string_utilities import remove_chat_prefix

from .config import ExcelGeneratorConfig


class ExcelGeneratorService:
    def __init__(
        self,
        content_service: ContentService,
        config: ExcelGeneratorConfig,
        chat_service: ChatService,
    ):
        """Initialize the ExcelGenerator class. This class is responsible for generating an Excel file out of a pandas dataframe.

        Args:
            event (ChatEvent): The event object.
            config (ExcelGeneratorConfig): The configuration object.
            logger (Logger): The logger object.
        """
        self.config = config

        self.content_service = content_service
        self.chat_service = chat_service

        self.excel_is_initiated = False
        self.excel_is_empty = True
        module_name = (
            getattr(g, "module_name", "NO_CONTEXT")
            if has_app_context()
            else ""
        )
        self.logger = logging.getLogger(f"{module_name}.{__name__}")

    def init_workbook(self, file_name: str, suffix: Optional[str] = None):
        """Initialize the workbook and create the Excel file.

        Args:
            tmp_save_dir (Path): The directory where the generated Excel file will be saved.
            file_name (str): The name of the file to be exported.
            suffix (Optional[str], optional): The suffix to be added to the file name. Defaults to None.
        """

        self.excel_is_initiated = True

        base_file_name = remove_chat_prefix(Path(file_name).stem)

        suffix = suffix or self.config.upload_suffix

        self.file_export_name = f"{base_file_name}{suffix}"

        options = {
            "in_memory": True,
        }
        self.buffer = io.BytesIO()
        self.workbook = xlsxwriter.Workbook(self.buffer, options=options)

        self.table_header_format = self.workbook.add_format(
            self.config.table_header_format
        )
        self.table_data_format = self.workbook.add_format(
            self.config.table_data_format
        )

    def add_worksheet(
        self,
        dataframe: pd.DataFrame,
        worksheet_name: str,
    ) -> None:
        """Create a worksheet out of a pandas dataframe and add it to the Excel file.

        Args:
            dataframe (pd.DataFrame): The dataframe containing the relevant questions.
            worksheet_name (str): The name of the worksheet.
        """
        if not self.excel_is_initiated:
            self.logger.error(
                "It seems that you forgot to initialize the workbook."
                "Make sure to call the init_workbook method before adding a worksheet."
            )
            return

        if not dataframe.empty:
            self.excel_is_empty = False
        else:
            return

        dataframe = dataframe.fillna("")
        if self.config.rename_col_map:
            dataframe.rename(columns=self.config.rename_col_map, inplace=True)

        # Create a worksheet and add a worksheet
        worksheet = self.workbook.add_worksheet(worksheet_name)

        # Write headers
        for col_num, column in enumerate(dataframe.columns):
            worksheet.write(0, col_num, column, self.table_header_format)

        # Write rows
        for row_num, question in dataframe.iterrows():
            for col_num, column in enumerate(dataframe.columns):
                worksheet.write(
                    row_num + 1,  # type: ignore
                    col_num,
                    question[column],
                    self.table_data_format,  # type: ignore
                )

        # Add autofilter on the first table headers
        worksheet.autofilter(
            0, 0, len(dataframe) - 1, len(dataframe.columns) - 1
        )  # type: ignore

        # Adjust column widths
        for idx, col in enumerate(dataframe.columns):
            max_length = (
                max(
                    [
                        np.median([dataframe[col].astype(str).map(len).max()]),
                        len(col),
                    ]
                )
                + 2
            )

            column_width = min([max_length, 70])
            worksheet.set_column(idx, idx, column_width)

    def reference_and_upload(
        self, sequence_number: int
    ) -> ContentReference | None:
        """Reference the Excel file and upload it to the chat.

        Args:
            sequence_number (int): The sequence number of the content.

        Returns:
            ContentReference | None: The reference to the uploaded content.
        """

        # Close the workbook
        self.workbook.close()

        # Reset the buffer to the beginning
        self.buffer.seek(0)

        # Get the Excel data
        excel_data = self.buffer.getvalue()

        if not self.excel_is_initiated:
            self.logger.error(
                "It seems that you forgot to initialize the workbook."
                "Make sure to call the init_workbook method before referencing and uploading the file."
            )
            return None

        if self.excel_is_empty:
            self.logger.warning(
                "The Excel file is empty. No content will be uploaded."
            )
            return None

        # Upload the file
        mime_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Always upload to chat by default
        if self.config.upload_to_chat:
            created_content_chat = (
                self.content_service.upload_content_from_bytes(
                    content=excel_data,
                    content_name=self.file_export_name,
                    mime_type=mime_type,
                    chat_id=self.chat_service.chat_id,
                    skip_ingestion=self.config.skip_ingestion,
                )
            )
            id = created_content_chat.id

        # Upload to additional scope if scope_id is provided
        if self.config.upload_scope_id:
            created_content_scope = (
                self.content_service.upload_content_from_bytes(
                    content=excel_data,
                    content_name=self.file_export_name,
                    mime_type=mime_type,
                    chat_id=None,
                    scope_id=self.config.upload_scope_id,
                    skip_ingestion=self.config.skip_ingestion,
                )
            )
            id = created_content_scope.id

        # return reference
        return ContentReference(
            id=id,  # type: ignore
            sequence_number=sequence_number,
            message_id=self.chat_service.assistant_message_id,  # type: ignore
            name=self.file_export_name,
            source=self.file_export_name,
            source_id=id,  # type: ignore
            url=f"unique://content/{id}",  # type: ignore
        )
