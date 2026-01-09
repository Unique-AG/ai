import base64
import logging

import requests
from fastmcp.server.dependencies import get_access_token
from pydantic import BaseModel, SecretStr

from unique_mcp.auth.zitadel.oauth_proxy import ZitadelOAuthProxySettings
from unique_toolkit.app.unique_settings import UniqueAuth

logger = logging.getLogger(__name__)


class User(BaseModel):
    email: str
    user_id: str
    name: str
    company_id: str
    metadata: dict[str, str] = {}


def _decode_metadata_dict(metadata_dict: dict[str, str]) -> dict[str, str]:
    """
    Decode all base64-encoded values in a metadata dictionary.

    Zitadel returns metadata as a dict where each value is base64-encoded.
    Base64 strings need padding (multiple of 4), so we add it if missing.
    """

    def decode_value(value: str) -> str:
        padding_needed = (4 - (len(value) % 4)) % 4
        if padding_needed:
            value += "=" * padding_needed
        return base64.b64decode(value).decode("utf-8")

    return {key: decode_value(value) for key, value in metadata_dict.items()}


def get_user(zitadel_oauth_proxy_settings: ZitadelOAuthProxySettings) -> User:
    token = get_access_token()

    if token is None:
        raise Exception("Unable to retrieve access token for user retrieval")

    headers = {
        "Authorization": f"Bearer {token.token}",
    }
    response = requests.get(
        zitadel_oauth_proxy_settings.userinfo_endpoint(), headers=headers
    )
    response.raise_for_status()

    zitadel_user_info = response.json()

    # Extract and decode custom metadata if present
    metadata = None

    if not isinstance(zitadel_user_info, dict):
        raise ValueError("Zitadel user info is not a dictionary")

    metadata_claim = zitadel_user_info.get("urn:zitadel:iam:user:metadata")

    if isinstance(metadata_claim, dict):
        metadata = _decode_metadata_dict(metadata_claim)

    user = User(
        email=zitadel_user_info.get("email"),
        user_id=zitadel_user_info.get("sub"),
        name=zitadel_user_info.get("name"),
        company_id=zitadel_user_info.get("urn:zitadel:iam:user:resourceowner:id"),
        metadata=metadata or {},
    )
    print(user)
    return user


def get_unique_auth_from_zitadel_user(
    unique_auth: UniqueAuth | None = None,
) -> UniqueAuth:
    if unique_auth is None:
        user = get_user(ZitadelOAuthProxySettings())
        unique_auth = UniqueAuth(
            user_id=SecretStr(user.user_id),
            company_id=SecretStr(user.company_id),
        )

    return unique_auth
