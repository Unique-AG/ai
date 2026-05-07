from __future__ import annotations


def child_exit(server, worker) -> None:
    """Gunicorn child_exit hook: clean up dead worker's per-PID metric files.

    Wire this up in gunicorn.conf.py:

        from unique_toolkit.monitoring.gunicorn import child_exit  # noqa: F401

    Gunicorn calls any function named child_exit(server, worker) in the
    config file whenever a worker process exits. Without this, dead workers'
    .db files accumulate in PROMETHEUS_MULTIPROC_DIR and inflate aggregated
    metric values on every future scrape.
    """
    from prometheus_client import multiprocess  # pyright: ignore[reportMissingImports]

    multiprocess.mark_process_dead(worker.pid)
