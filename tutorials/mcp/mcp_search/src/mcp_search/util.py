import requests
from fastmcp.server.dependencies import get_access_token
from pydantic import BaseModel, SecretStr

from unique_mcp.auth.zitadel.oauth_proxy import ZitadelOAuthProxySettings
from unique_toolkit.app.unique_settings import UniqueAuth


class User(BaseModel):
    email: str
    user_id: str
    name: str
    company_id: str


def get_user(zitadel_oauth_proxy_settings: ZitadelOAuthProxySettings) -> User:
    zitadel_user_info = None
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

    user = User(
        email=zitadel_user_info.get("email"),
        user_id=zitadel_user_info.get("sub"),
        name=zitadel_user_info.get("name"),
        company_id=zitadel_user_info.get("urn:zitadel:iam:user:resourceowner:id"),
    )

    return user


def get_unique_auth_from_zitadel_user(
    unique_auth: UniqueAuth | None = None,
) -> UniqueAuth:
    if unique_auth is None:
        user = get_user(zitadel_oauth_proxy_settings=ZitadelOAuthProxySettings())
        unique_auth = UniqueAuth(
            user_id=SecretStr(user.user_id),
            company_id=SecretStr(user.company_id),
        )

    return unique_auth
