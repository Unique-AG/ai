import base64
import logging
import os
from functools import cached_property
from typing import NamedTuple

from pydantic import RootModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from unique_toolkit._common.execution import failsafe

logger = logging.getLogger(__name__)


class CertificateCredentials(NamedTuple):
    cert: str
    key: str


# TODO: Remove first two formats once all creds are updated
SixApiCredentialsParser = RootModel[
    list[tuple[list[str], CertificateCredentials]]
    | dict[str, CertificateCredentials]
    | CertificateCredentials
]


class SixApiBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.environ.get("UNIQUE_ENV_FILE") or None,
        env_file_encoding="utf-8",
        env_prefix="SIX_API_",
        case_sensitive=False,
        extra="ignore",
    )
    creds: str | None = None
    activated_companies: list[str] = []

    @cached_property
    @failsafe(failure_return_value={}, logger=logger)
    def _loaded_creds(self) -> dict[str, CertificateCredentials]:
        if self.creds is None:
            logger.warning("Six API credentials are not set")
            return {}

        decoded_creds = base64.b64decode(self.creds).decode("utf-8")
        parsed_creds = SixApiCredentialsParser.model_validate_json(decoded_creds).root

        outdated_format = False
        if isinstance(parsed_creds, list):
            res = {
                company_id: creds
                for company_ids, creds in parsed_creds
                for company_id in company_ids
            }
            outdated_format = True
        elif isinstance(parsed_creds, dict):
            res = parsed_creds
            outdated_format = True
        else:
            res = {company_id: parsed_creds for company_id in self.activated_companies}

        if outdated_format:
            logger.warning(
                "Six API credentials supplied in an outdated format. Please update them."
            )
            if len(self.activated_companies) > 0:
                logger.warning("Supplied companies will be ignored.")

        return res

    def creds_for_company(self, company_id: str) -> CertificateCredentials | None:
        return self._loaded_creds.get(company_id, None)


def get_six_api_settings() -> SixApiBaseSettings:
    return SixApiBaseSettings()


six_api_settings = get_six_api_settings()
