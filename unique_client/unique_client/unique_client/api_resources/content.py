"""
Content API resource for the Unique SDK v2.
"""

from pydantic import RootModel

from unique_client.core import APIResource

# TODO: Import these DTOs when they become available
from unique_client.unique_client.api_resources.api_dtos import (
    ContentInfoDto,
    ContentUpsertDto,
    ExcelExportRequestDto,
    ExcelExportResultDto,
    PublicContentDto,
    PublicContentInfoDto,
    PublicContentUpsertMutationDto,
    QueryTableAnswertDto,
    QueryTableRequest,
    SearchDto,
)


class PublicContentListDto(RootModel):
    root: list[PublicContentDto]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __len__(self):
        return len(self.root)


class Content(APIResource):
    """
    Content API resource for managing content operations.

    This class provides both sync and async methods for searching, upserting, querying tables,
    exporting to Excel, and retrieving content files.

    All methods use the intrinsic RequestContextProtocol for automatic header and URL handling.
    """

    OBJECT_NAME = "content"

    # Synchronous methods
    # ==================

    def search(self, params: SearchDto) -> PublicContentListDto:
        """Search content using the intrinsic RequestContextProtocol."""
        return self._request(
            "post",
            "/content/search",
            model_class=PublicContentListDto,
            params=params,
        )

    def upsert(self, params: ContentUpsertDto) -> PublicContentUpsertMutationDto:
        """Upsert content using the intrinsic RequestContextProtocol."""
        return self._request(
            "post",
            "/content/upsert",
            model_class=PublicContentUpsertMutationDto,
            params=params,
        )

    def info(self, params: ContentInfoDto) -> PublicContentInfoDto:
        """Get content info using the intrinsic RequestContextProtocol."""
        return self._request(
            "post",
            "/content/info",
            model_class=PublicContentInfoDto,
            params=params,
        )

    def query_table(self, params: QueryTableRequest) -> QueryTableAnswertDto:
        """Query table using the intrinsic RequestContextProtocol."""
        return self._request(
            "post",
            "/content/query-table",
            model_class=QueryTableAnswertDto,
            params=params,
        )

    def export_excel(self, params: ExcelExportRequestDto) -> ExcelExportResultDto:
        """Export to Excel using the intrinsic RequestContextProtocol."""
        return self._request(
            "post",
            "/content/export/excel",
            model_class=ExcelExportResultDto,
            params=params,
        )

    # TODO: Inconsistent with Pydantic approach - commented out for now
    # These methods don't follow the standard _request pattern and return non-Pydantic types
    # Need to create proper Pydantic models for responses and update to use _request method

    # TODO: Try to remove dependency on UniqueResponse
    # def table_attributes(self, params: TableConfigDto) -> Dict[str, any]:
    #     """Get table attributes using the intrinsic RequestContextProtocol."""
    #     from unique_client.core.requestor import APIRequestor
    #
    #     # Build URL and headers from intrinsic context
    #     full_url = self.context.build_full_url("/content/table-atttributes")
    #     headers = self.context.build_headers("get")
    #
    #     serialized_params = params.model_dump(by_alias=True, exclude_none=True)
    #     rbody, rcode, rheaders = APIRequestor.request(
    #         "get", full_url, headers, serialized_params
    #     )
    #
    #     # Parse the response as dict
    #     if not (200 <= rcode < 300):
    #         from unique_client.core.response import UniqueResponse
    #
    #         if hasattr(rbody, "decode"):
    #             rbody_decoded = rbody.decode("utf-8")
    #         else:
    #             rbody_decoded = rbody
    #         resp = UniqueResponse(rbody_decoded, rcode, rheaders)
    #         APIRequestor._handle_error_response(
    #             rbody_decoded, rcode, resp.data, rheaders
    #         )
    #
    #     # Decode and parse as JSON dict
    #     if hasattr(rbody, "decode"):
    #         rbody = rbody.decode("utf-8")
    #
    #     import json
    #
    #     return json.loads(rbody)

    # TODO: Try to remove dependency on UniqueResponse
    # def file_content(self, content_id: str, chat_id: str) -> bytes:
    #     """
    #     Get file content stream using the intrinsic RequestContextProtocol.
    #
    #     Args:
    #         content_id: The content ID to retrieve file for
    #         chat_id: The chat ID (required query parameter)
    #
    #     Returns:
    #         bytes: Binary file content
    #     """
    #     from unique_client.core.requestor import APIRequestor
    #
    #     # Build URL and headers from intrinsic context
    #     full_url = self.context.build_full_url(f"/content/{content_id}/file")
    #     headers = self.context.build_headers("get")
    #
    #     params = {"chatId": chat_id}
    #     rbody, rcode, rheaders = APIRequestor.request("get", full_url, headers, params)
    #
    #     # For file content, we expect the raw bytes response
    #     if not (200 <= rcode < 300):
    #         from unique_client.core.response import UniqueResponse
    #
    #         if hasattr(rbody, "decode"):
    #             rbody_decoded = rbody.decode("utf-8")
    #         else:
    #             rbody_decoded = rbody
    #         resp = UniqueResponse(rbody_decoded, rcode, rheaders)
    #         APIRequestor._handle_error_response(
    #             rbody_decoded, rcode, resp.data, rheaders
    #         )
    #
    #     return rbody

    # Asynchronous methods
    # ===================

    async def search_async(self, params: SearchDto) -> PublicContentListDto:
        """Search content asynchronously using the intrinsic RequestContextProtocol."""
        return await self._request_async(
            "post",
            "/content/search",
            model_class=PublicContentListDto,
            params=params,
        )

    async def upsert_async(
        self, params: ContentUpsertDto
    ) -> PublicContentUpsertMutationDto:
        """Upsert content asynchronously using the intrinsic RequestContextProtocol."""
        return await self._request_async(
            "post",
            "/content/upsert",
            model_class=PublicContentUpsertMutationDto,
            params=params,
        )

    async def info_async(self, params: ContentInfoDto) -> PublicContentInfoDto:
        """Get content info asynchronously using the intrinsic RequestContextProtocol."""
        return await self._request_async(
            "post",
            "/content/info",
            model_class=PublicContentInfoDto,
            params=params,
        )

    async def query_table_async(
        self, params: QueryTableRequest
    ) -> QueryTableAnswertDto:
        """Query table asynchronously using the intrinsic RequestContextProtocol."""
        return await self._request_async(
            "post",
            "/content/query-table",
            model_class=QueryTableAnswertDto,
            params=params,
        )

    async def export_excel_async(
        self, params: ExcelExportRequestDto
    ) -> ExcelExportResultDto:
        """Export to Excel asynchronously using the intrinsic RequestContextProtocol."""
        return await self._request_async(
            "post",
            "/content/export/excel",
            model_class=ExcelExportResultDto,
            params=params,
        )

    # TODO: Inconsistent with Pydantic approach - commented out for now
    # These async methods don't follow the standard _request_async pattern and return non-Pydantic types
    # Need to create proper Pydantic models for responses and update to use _request_async method

    # TODO: Try to remove dependency on UniqueResponse
    # async def table_attributes_async(self, params: TableConfigDto) -> Dict[str, any]:
    #     """Get table attributes asynchronously using the intrinsic RequestContextProtocol."""
    #     from unique_client.core.requestor import APIRequestor
    #
    #     # Build URL and headers from intrinsic context
    #     full_url = self.context.build_full_url("/content/table-atttributes")
    #     headers = self.context.build_headers("get")
    #
    #     serialized_params = params.model_dump(by_alias=True, exclude_none=True)
    #     rbody, rcode, rheaders = await APIRequestor.request_async(
    #         "get", full_url, headers, serialized_params
    #     )
    #
    #     # Parse the response as dict
    #     if not (200 <= rcode < 300):
    #         from unique_client.core.response import UniqueResponse
    #
    #         if hasattr(rbody, "decode"):
    #             rbody_decoded = rbody.decode("utf-8")
    #         else:
    #             rbody_decoded = rbody
    #         resp = UniqueResponse(rbody_decoded, rcode, rheaders)
    #         APIRequestor._handle_error_response(
    #             rbody_decoded, rcode, resp.data, rheaders
    #         )
    #
    #     # Decode and parse as JSON dict
    #     if hasattr(rbody, "decode"):
    #         rbody = rbody.decode("utf-8")
    #
    #     import json
    #
    #     return json.loads(rbody)

    # TODO: Try to remove dependency on UniqueResponse
    # async def file_content_async(self, content_id: str, chat_id: str) -> bytes:
    #     """
    #     Get file content stream asynchronously using the intrinsic RequestContextProtocol.
    #
    #     Args:
    #         content_id: The content ID to retrieve file for
    #         chat_id: The chat ID (required query parameter)
    #
    #     Returns:
    #         bytes: Binary file content
    #     """
    #     from unique_client.core.requestor import APIRequestor
    #
    #     # Build URL and headers from intrinsic context
    #     full_url = self.context.build_full_url(f"/content/{content_id}/file")
    #     headers = self.context.build_headers("get")
    #
    #     params = {"chatId": chat_id}
    #     rbody, rcode, rheaders = await APIRequestor.request_async(
    #         "get", full_url, headers, params
    #     )
    #
    #     # For file content, we expect the raw bytes response
    #     if not (200 <= rcode < 300):
    #         from unique_client.core.response import UniqueResponse
    #
    #         if hasattr(rbody, "decode"):
    #             rbody_decoded = rbody.decode("utf-8")
    #         else:
    #             rbody_decoded = rbody
    #         resp = UniqueResponse(rbody_decoded, rcode, resp.data, rheaders)
    #         APIRequestor._handle_error_response(
    #             rbody_decoded, rcode, resp.data, rheaders
    #         )
    #
    #     return rbody
