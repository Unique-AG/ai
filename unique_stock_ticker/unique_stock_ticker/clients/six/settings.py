import base64
import logging
from typing import NamedTuple

from pydantic import BaseModel, RootModel
from settings import env_settings
from unique_toolkit.tools.utils.execution.execution import failsafe

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


class SixApiSettings(BaseModel):
    creds: str | None = env_settings.six_api_creds
    company_ids: list[str] = env_settings.six_api_activated_companies

    @property
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
            res = {company_id: parsed_creds for company_id in self.company_ids}

        if outdated_format:
            logger.warning(
                "Six API credentials supplied in an outdated format. Please update them."
            )
            if len(self.company_ids) > 0:
                logger.warning("Supplied companies will be ignored.")

        return res

    def creds_for_company(self, company_id: str) -> CertificateCredentials | None:
        return self._loaded_creds.get(company_id, None)


six_api_settings = SixApiSettings()
