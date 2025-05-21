from typing import ClassVar, List, Literal, Optional, TypedDict, Unpack, cast

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class Folder(APIResource["Folder"]):
    OBJECT_NAME: ClassVar[Literal["folder"]] = "folder"
    RESOURCE_URL = "/folder"

    class CreatedFolder(TypedDict):
        id: str
        object: str
        name: str
        parentId: Optional[str]

    class CreateFolderStructureResponse(TypedDict):
        createdFolders: List["Folder.CreatedFolder"]

    class CreateParams(RequestOptions):
        paths: List[str]

    @classmethod
    def create_paths(
            cls, user_id: str, company_id: str, **params: Unpack["Folder.CreateParams"]
    ) -> "Folder.CreateFolderStructureResponse":
        return cast(
            "Folder",
            cls._static_request(
                "post",
                cls.RESOURCE_URL,
                user_id,
                company_id=company_id,
                params=params,
            ),
        )

    @classmethod
    async def create_paths_async(
            cls, user_id: str, company_id: str, **params: Unpack["Folder.CreateParams"]
    ) -> "Folder.CreateFolderStructureResponse":
        return cast(
            "Folder",
            await cls._static_request_async(
                "post",
                cls.RESOURCE_URL,
                user_id,
                company_id=company_id,
                params=params,
            ),
        )