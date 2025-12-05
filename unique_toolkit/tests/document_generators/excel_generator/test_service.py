import pandas as pd
import pytest

from unique_toolkit.document_generators.excel_generator.config import (
    ExcelGeneratorConfig,
)
from unique_toolkit.document_generators.excel_generator.service import (
    ExcelGeneratorService,
)


class FakeUploadStrategy:
    def __init__(self):
        self.upload_called = False
        self.last_excel_data = None
        self.last_file_name = None

    def upload(self, excel_data: bytes, file_name: str) -> str:
        self.upload_called = True
        self.last_excel_data = excel_data
        self.last_file_name = file_name
        return "fake-id-123"


@pytest.fixture
def config():
    return ExcelGeneratorConfig(
        upload_suffix="_export.xlsx",
        table_header_format={"bold": True},
        table_data_format={},
        rename_col_map=None,
    )


@pytest.fixture
def service(config):
    return ExcelGeneratorService(config=config)


@pytest.mark.ai
def test_init_workbook(service):
    service.init_workbook("report.xlsx")

    assert service.excel_is_initiated is True
    assert service.file_export_name == "report_export.xlsx"
    assert service.workbook is not None


@pytest.mark.ai
def test_add_worksheet_skips_empty_df(service):
    service.init_workbook("report.xlsx")
    df = pd.DataFrame()

    service.add_worksheet(df, "Sheet1")

    # still empty because no data
    assert service.excel_is_empty is True


@pytest.mark.ai
def test_add_worksheet_sets_non_empty(service):
    service.init_workbook("report.xlsx")
    df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})

    service.add_worksheet(df, "Sheet1")

    # once data is written
    assert service.excel_is_empty is False


@pytest.mark.ai
def test_finalize_returns_none_when_not_initiated(service):
    result = service.finalize()
    assert result is None


@pytest.mark.ai
def test_finalize_returns_none_when_empty(service):
    service.init_workbook("file.xlsx")

    # no sheets added -> still empty
    result = service.finalize()
    assert result is None


@pytest.mark.ai
def test_finalize_returns_bytes(service):
    service.init_workbook("file.xlsx")
    df = pd.DataFrame({"x": [10, 20]})

    service.add_worksheet(df, "SheetA")

    excel_data = service.finalize()
    assert isinstance(excel_data, (bytes, bytearray))
    assert len(excel_data) > 100  # XLSX is never tiny


@pytest.mark.ai
def test_upload_calls_strategy(service):
    strategy = FakeUploadStrategy()

    service.init_workbook("report.xlsx")
    df = pd.DataFrame({"c": [1]})
    service.add_worksheet(df, "Sheet1")

    upload_id = service.upload(strategy)

    assert upload_id == "fake-id-123"
    assert strategy.upload_called is True
    assert strategy.last_file_name == "report_export.xlsx"
    assert isinstance(strategy.last_excel_data, bytes)
