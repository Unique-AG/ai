"""Unit tests for unique_toolkit._common.excel_generator."""

import pandas as pd

from unique_toolkit._common.excel_generator.config import ExcelGeneratorConfig
from unique_toolkit._common.excel_generator.service import ExcelGeneratorService

# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestExcelGeneratorConfig:
    def test_defaults(self):
        config = ExcelGeneratorConfig()
        assert config.upload_suffix == "_answers.xlsx"
        assert config.rename_col_map is None
        assert config.table_header_format["bold"] is True
        assert config.table_data_format["border"] == 1

    def test_custom_suffix(self):
        config = ExcelGeneratorConfig(upload_suffix="_report.xlsx")
        assert config.upload_suffix == "_report.xlsx"

    def test_custom_rename_col_map(self):
        config = ExcelGeneratorConfig(rename_col_map={"old": "new"})
        assert config.rename_col_map == {"old": "new"}

    def test_custom_header_format(self):
        custom = {
            "bg_color": "#000000",
            "bold": False,
            "font_color": "red",
            "text_wrap": False,
        }
        config = ExcelGeneratorConfig(table_header_format=custom)
        assert config.table_header_format["bg_color"] == "#000000"


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestExcelGeneratorService:
    def _make_df(self) -> pd.DataFrame:
        return pd.DataFrame({"Name": ["Alice", "Bob"], "Score": [85, 90]})

    def test_file_export_name_uses_stem_and_suffix(self):
        svc = ExcelGeneratorService(ExcelGeneratorConfig())
        svc.init_workbook("report.docx")
        assert svc.file_export_name == "report_answers.xlsx"

    def test_file_export_name_custom_suffix(self):
        svc = ExcelGeneratorService(ExcelGeneratorConfig())
        svc.init_workbook("report", suffix="_custom.xlsx")
        assert svc.file_export_name == "report_custom.xlsx"

    def test_file_export_name_from_config_suffix(self):
        svc = ExcelGeneratorService(ExcelGeneratorConfig(upload_suffix="_out.xlsx"))
        svc.init_workbook("data")
        assert svc.file_export_name == "data_out.xlsx"

    def test_generate_returns_bytes(self):
        svc = ExcelGeneratorService(ExcelGeneratorConfig())
        svc.init_workbook("test")
        svc.add_worksheet(self._make_df(), worksheet_name="Sheet1")
        result = svc.generate()
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_valid_xlsx_magic_bytes(self):
        svc = ExcelGeneratorService(ExcelGeneratorConfig())
        svc.init_workbook("test")
        svc.add_worksheet(self._make_df(), worksheet_name="Sheet1")
        result = svc.generate()
        # XLSX (ZIP) files start with PK\x03\x04
        assert result is not None
        assert result[:4] == b"PK\x03\x04"

    def test_generate_returns_none_when_not_initialized(self):
        svc = ExcelGeneratorService(ExcelGeneratorConfig())
        assert svc.generate() is None

    def test_generate_returns_none_when_empty(self):
        svc = ExcelGeneratorService(ExcelGeneratorConfig())
        svc.init_workbook("test")
        # No worksheet added
        assert svc.generate() is None

    def test_add_worksheet_skips_empty_dataframe(self):
        svc = ExcelGeneratorService(ExcelGeneratorConfig())
        svc.init_workbook("test")
        svc.add_worksheet(pd.DataFrame(), worksheet_name="Empty")
        assert svc.generate() is None

    def test_add_worksheet_before_init_logs_error(self, caplog):
        import logging

        svc = ExcelGeneratorService(ExcelGeneratorConfig())
        with caplog.at_level(logging.ERROR):
            svc.add_worksheet(self._make_df(), worksheet_name="Sheet1")
        assert "not initialized" in caplog.text.lower()

    def test_rename_col_map_applied(self):
        svc = ExcelGeneratorService(
            ExcelGeneratorConfig(rename_col_map={"Name": "Full Name"})
        )
        svc.init_workbook("test")
        svc.add_worksheet(self._make_df(), worksheet_name="Sheet1")
        result = svc.generate()
        assert isinstance(result, bytes)

    def test_multiple_worksheets(self):
        svc = ExcelGeneratorService(ExcelGeneratorConfig())
        svc.init_workbook("multi")
        svc.add_worksheet(self._make_df(), worksheet_name="Sheet1")
        svc.add_worksheet(
            pd.DataFrame({"A": [1, 2], "B": [3, 4]}), worksheet_name="Sheet2"
        )
        result = svc.generate()
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_dataframe_with_nan_values(self):
        import numpy as np

        df = pd.DataFrame({"A": ["x", None, "z"], "B": [1, np.nan, 3]})
        svc = ExcelGeneratorService(ExcelGeneratorConfig())
        svc.init_workbook("nan_test")
        svc.add_worksheet(df, worksheet_name="NaN")
        result = svc.generate()
        assert isinstance(result, bytes)

    def test_original_dataframe_not_mutated(self):
        df = pd.DataFrame({"old_col": ["a", "b"]})
        original_columns = list(df.columns)
        svc = ExcelGeneratorService(
            ExcelGeneratorConfig(rename_col_map={"old_col": "new_col"})
        )
        svc.init_workbook("mut_test")
        svc.add_worksheet(df, worksheet_name="Sheet1")
        assert list(df.columns) == original_columns
