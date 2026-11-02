from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PdfDocumentHandle")


@_attrs_define
class PdfDocumentHandle:
    """Short-lived reference to a pod-local PDF hold for out-of-band download.

    Attributes:
        document_id (str): Opaque id of the held PDF on the owning pod
        download_url (str): Internal URL on the owning pod that streams the held bytes
        token (str): One-time bearer token required by GET /v1/document-holds/{id}
        expires_at (str): UTC expiry of the hold as an ISO-8601 string
        byte_size (int): Held PDF size in bytes
        page_count (int | None | Unset): Page count when known at hold time; null when not inspected
    """

    document_id: str
    download_url: str
    token: str
    expires_at: str
    byte_size: int
    page_count: int | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        document_id = self.document_id

        download_url = self.download_url

        token = self.token

        expires_at = self.expires_at

        byte_size = self.byte_size

        page_count: int | None | Unset
        if isinstance(self.page_count, Unset):
            page_count = UNSET
        else:
            page_count = self.page_count

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "documentId": document_id,
                "downloadUrl": download_url,
                "token": token,
                "expiresAt": expires_at,
                "byteSize": byte_size,
            }
        )
        if page_count is not UNSET:
            field_dict["pageCount"] = page_count

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        document_id = d.pop("documentId")

        download_url = d.pop("downloadUrl")

        token = d.pop("token")

        expires_at = d.pop("expiresAt")

        byte_size = d.pop("byteSize")

        def _parse_page_count(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        page_count = _parse_page_count(d.pop("pageCount", UNSET))

        pdf_document_handle = cls(
            document_id=document_id,
            download_url=download_url,
            token=token,
            expires_at=expires_at,
            byte_size=byte_size,
            page_count=page_count,
        )

        pdf_document_handle.additional_properties = d
        return pdf_document_handle

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
