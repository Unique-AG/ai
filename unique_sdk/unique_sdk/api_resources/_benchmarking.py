from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Literal,
    NotRequired,
    TypedDict,
    cast,
)

import requests

import unique_sdk
from unique_sdk._api_requestor import APIRequestor
from unique_sdk._api_resource import APIResource
from unique_sdk._util import classproperty

if TYPE_CHECKING:
    from unique_sdk._client import _BaseClient

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_TIMEOUT = 600.0


class Benchmarking(APIResource["Benchmarking"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["benchmarking"]:
        return "benchmarking"

    RESOURCE_URL = "/benchmarking"

    class BenchmarkStatusNumbers(TypedDict):
        done: int
        error: int
        total: int

    class ProcessUploadResponse(TypedDict):
        benchmarkStatus: "Benchmarking.BenchmarkStatusNumbers"

    class StatusSnapshot(TypedDict):
        done: int
        error: int
        total: int
        filename: str
        status: str
        benchmarkId: NotRequired[str]

    @classmethod
    def _requestor_and_headers(
        cls, user_id: str, company_id: str, client: "_BaseClient | None" = None
    ) -> tuple[APIRequestor, dict[str, str]]:
        requestor = APIRequestor(user_id=user_id, company_id=company_id, client=client)
        api_key = requestor.api_key or unique_sdk.api_key
        app_id = requestor.app_id or unique_sdk.app_id
        headers = requestor.request_headers(api_key, app_id, "get")
        return requestor, headers

    @classmethod
    def process_upload(
        cls,
        user_id: str,
        company_id: str,
        file: bytes,
        filename: str,
        force: bool | None = None,
        client: "_BaseClient | None" = None,
    ) -> "Benchmarking.ProcessUploadResponse":
        """Upload a benchmarking spreadsheet for processing."""
        _, headers = cls._requestor_and_headers(user_id, company_id, client)
        resp = requests.post(
            f"{unique_sdk.api_base}{cls.RESOURCE_URL}",
            headers=headers,
            params={"force": "true" if force else "false"}
            if force is not None
            else None,
            files={"file": (filename, file, _XLSX)},
            timeout=_TIMEOUT,
            verify=unique_sdk.api_verify_mode,
        )
        if not (200 <= resp.status_code < 300):
            raise Exception(
                f"Error uploading benchmarking file: Status code {resp.status_code}"
            )
        return cast("Benchmarking.ProcessUploadResponse", resp.json())

    @classmethod
    async def process_upload_async(
        cls,
        user_id: str,
        company_id: str,
        file: bytes,
        filename: str,
        force: bool | None = None,
        client: "_BaseClient | None" = None,
    ) -> "Benchmarking.ProcessUploadResponse":
        """Async upload a benchmarking spreadsheet for processing."""
        return await asyncio.to_thread(
            cls.process_upload, user_id, company_id, file, filename, force, client
        )

    @classmethod
    def get_status(
        cls, user_id: str, company_id: str, client: "_BaseClient | None" = None
    ) -> "Benchmarking.StatusSnapshot":
        """Get the current benchmarking status for the company."""
        return cast(
            "Benchmarking.StatusSnapshot",
            cls._static_request(
                "get",
                f"{cls.RESOURCE_URL}/status",
                user_id,
                company_id,
                client=client,
            ),
        )

    @classmethod
    async def get_status_async(
        cls, user_id: str, company_id: str, client: "_BaseClient | None" = None
    ) -> "Benchmarking.StatusSnapshot":
        """Async get the current benchmarking status for the company."""
        return cast(
            "Benchmarking.StatusSnapshot",
            await cls._static_request_async(
                "get",
                f"{cls.RESOURCE_URL}/status",
                user_id,
                company_id,
                client=client,
            ),
        )

    @classmethod
    def _download_to_tmp(
        cls,
        user_id: str,
        company_id: str,
        path: str,
        filename: str,
        client: "_BaseClient | None" = None,
    ) -> Path:
        _, headers = cls._requestor_and_headers(user_id, company_id, client)
        url = f"{unique_sdk.api_base}{path}"
        response = requests.get(
            url,
            headers=headers,
            timeout=_TIMEOUT,
            verify=unique_sdk.api_verify_mode,
        )
        if response.status_code == 200:
            random_dir = tempfile.mkdtemp(dir="/tmp")
            file_path = Path(random_dir) / filename
            with open(file_path, "wb") as f:
                f.write(response.content)
            return file_path
        raise Exception(f"Error downloading file: Status code {response.status_code}")

    @classmethod
    def download_processed(
        cls,
        user_id: str,
        company_id: str,
        filename: str = "benchmarking_result.xlsx",
        client: "_BaseClient | None" = None,
    ) -> Path:
        """Download the processed benchmarking workbook to a temp file and return its path."""
        return cls._download_to_tmp(
            user_id, company_id, f"{cls.RESOURCE_URL}/action/download", filename, client
        )

    @classmethod
    async def download_processed_async(
        cls,
        user_id: str,
        company_id: str,
        filename: str = "benchmarking_result.xlsx",
        client: "_BaseClient | None" = None,
    ) -> Path:
        """Async download the processed benchmarking workbook."""
        return await asyncio.to_thread(
            cls.download_processed, user_id, company_id, filename, client
        )

    @classmethod
    def download_template(
        cls,
        user_id: str,
        company_id: str,
        filename: str = "benchmarking_template.xlsx",
        client: "_BaseClient | None" = None,
    ) -> Path:
        """Download the benchmarking input template to a temp file and return its path."""
        return cls._download_to_tmp(
            user_id,
            company_id,
            f"{cls.RESOURCE_URL}/action/template-download",
            filename,
            client,
        )

    @classmethod
    async def download_template_async(
        cls,
        user_id: str,
        company_id: str,
        filename: str = "benchmarking_template.xlsx",
        client: "_BaseClient | None" = None,
    ) -> Path:
        """Async download the benchmarking input template."""
        return await asyncio.to_thread(
            cls.download_template, user_id, company_id, filename, client
        )
