from pathlib import Path

from dotenv import dotenv_values
from openai import OpenAI
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class UniqueAuth(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    user_id: SecretStr
    company_id: SecretStr

    def headers(self) -> dict[str, str]:
        return {
            "x-user-id": self.user_id.get_secret_value(),
            "x-company-id": self.company_id.get_secret_value(),
        }


class UniqueApi(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    api_base: SecretStr
    api_key: SecretStr
    api_version: str

    def headers(self):
        return {"x-api-version": self.api_version}


class UniqueApp(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    app_id: SecretStr
    app_key: SecretStr

    def headers(
        self,
    ):
        return {
            "x-app-id": self.app_id.get_secret_value(),
            "Authorization": f"Bearer {self.app_key.get_secret_value()}",
        }


def get_secrets(env_file: Path) -> tuple[UniqueApp, UniqueApi, UniqueAuth]:
    env_dict = dotenv_values(dotenv_path=env_file)
    env_dict = {k: v for k, v in env_dict.items() if v}
    app_settings = UniqueApp(**env_dict)
    api_settings = UniqueApi(**env_dict)
    auth_settings = UniqueAuth(**env_dict)
    return app_settings, api_settings, auth_settings


def get_default_headers(env_file: Path):
    app_settings, api_settings, auth_settings = get_secrets(env_file=env_file)
    default_headers = {}
    default_headers.update(app_settings.headers())
    default_headers.update(auth_settings.headers())
    default_headers.update(api_settings.headers())
    return default_headers


def get_extra_headers(model: str, env_file: Path) -> dict[str, str]:
    # Set custom headers required by your API
    extra_headers = {
        "x-model": model,
    }
    app_settings, api_settings, auth_settings = get_secrets(env_file=env_file)
    extra_headers.update(app_settings.headers())
    extra_headers.update(auth_settings.headers())
    extra_headers.update(api_settings.headers())
    return extra_headers


def get_openai_client(env_file: Path) -> OpenAI:
    app_settings, api_settings, auth_settings = get_secrets(env_file=env_file)
    # Set custom headers required by your API

    default_headers = get_default_headers(env_file=env_file)

    return OpenAI(
        api_key=api_settings.api_key,
        base_url=api_settings.api_base + "/openai-proxy/",
        default_headers=default_headers,
    )
