from pydantic_settings import BaseSettings

from unique_search_proxy_client.web.helm.metadata import helm_settings
from unique_search_proxy_client.web.settings.base import get_settings

PROMETHEUS_ENV_PREFIX = "PROMETHEUS_"


@helm_settings(
    title="Prometheus",
    helm_key=None,
    kind="internal",
    egress=None,
    env_prefix=PROMETHEUS_ENV_PREFIX,
)
class PrometheusSettings(BaseSettings):
    enabled: bool = True


def get_prometheus_settings() -> PrometheusSettings:
    return get_settings(PrometheusSettings, env_prefix=PROMETHEUS_ENV_PREFIX)


prometheus_settings: PrometheusSettings = get_prometheus_settings()
