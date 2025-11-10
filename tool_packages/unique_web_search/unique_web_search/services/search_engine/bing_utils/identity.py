from logging import getLogger

import certifi
from azure.core.credentials import TokenCredential
from azure.core.pipeline.transport._requests_basic import RequestsTransport
from azure.identity import DefaultAzureCredential, WorkloadIdentityCredential

from unique_web_search.settings import env_settings

_LOGGER = getLogger(__name__)


def _get_workload_identity_credentials(
    with_request_transport: bool = False,
) -> WorkloadIdentityCredential:
    if with_request_transport:
        transport = RequestsTransport(connection_verify=certifi.where())
        credentials = WorkloadIdentityCredential(transport=transport)
    else:
        credentials = WorkloadIdentityCredential()

    return credentials


def get_crendentials():
    match env_settings.azure_identity_credential_type:
        case "workload":
            return _get_workload_identity_credentials(
                env_settings.use_unique_private_endpoint_transport
            )
        case "default":
            return DefaultAzureCredential()
        case _:
            raise ValueError(
                f"Invalid Azure identity credential type: {env_settings.azure_identity_credential_type}"
            )


def credentials_are_valid(credentials: TokenCredential) -> bool:
    _LOGGER.info("Validating Azure identity credentials")
    try:
        credentials.get_token(
            env_settings.azure_identity_credentials_validate_token_url
        )
        _LOGGER.info("Azure identity credentials are valid")
        return True
    except Exception as e:
        _LOGGER.error(f"Azure identity credentials are invalid: {e}")
        return False
