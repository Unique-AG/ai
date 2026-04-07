try:
    from prometheus_client import CollectorRegistry  # noqa: F401

    _MONITORING_AVAILABLE = True
except ImportError:
    _MONITORING_AVAILABLE = False


def _check_monitoring_available() -> None:
    if not _MONITORING_AVAILABLE:
        raise ImportError(
            "prometheus_client is not installed. "
            "Install it with: pip install unique_toolkit[monitoring]"
        )


if _MONITORING_AVAILABLE:
    from unique_toolkit.monitoring.middleware import MetricsMiddleware
    from unique_toolkit.monitoring.registry import (
        REGISTRY,
        MetricNamespace,
        get_metrics,
        metric_scope,
        track_execution,
    )

    __all__ = [
        "REGISTRY",
        "MetricNamespace",
        "MetricsMiddleware",
        "get_metrics",
        "metric_scope",
        "track_execution",
        "_MONITORING_AVAILABLE",
    ]
else:

    def __getattr__(name: str):
        _check_monitoring_available()
