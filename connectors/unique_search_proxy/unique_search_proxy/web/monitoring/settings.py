from pydantic_settings import BaseSettings

from unique_search_proxy.web.settings.base import is_test_runtime, settings_config


class PrometheusSettings(BaseSettings):
    model_config = settings_config(env_prefix="PROMETHEUS_")

    enabled: bool = True


class PrometheusSettingsForTests(PrometheusSettings):
    model_config = settings_config(env_prefix="PROMETHEUS_", test=True)


def get_prometheus_settings() -> PrometheusSettings:
    if is_test_runtime():
        return PrometheusSettingsForTests()
    return PrometheusSettings()


prometheus_settings: PrometheusSettings = get_prometheus_settings()
