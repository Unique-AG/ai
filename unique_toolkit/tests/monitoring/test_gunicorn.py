"""Tests for unique_toolkit.monitoring.gunicorn module."""

import pytest

pytest.importorskip("prometheus_client")

from unique_toolkit.monitoring.gunicorn import child_exit  # noqa: E402


class _FakeWorker:
    def __init__(self, pid: int) -> None:
        self.pid = pid


@pytest.mark.ai
def test_child_exit__calls_mark_process_dead__with_worker_pid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify child_exit calls multiprocess.mark_process_dead with the worker's PID.
    Why this matters: Without this call, dead workers' .db files accumulate in
    PROMETHEUS_MULTIPROC_DIR and inflate aggregated metric values on every future scrape.
    Setup summary: Monkeypatch mark_process_dead, call child_exit with a FakeWorker(pid=12345),
    assert mark_process_dead was called exactly once with 12345.
    """
    import prometheus_client.multiprocess as mp_module

    calls: list[int] = []
    monkeypatch.setattr(mp_module, "mark_process_dead", lambda pid: calls.append(pid))

    child_exit(server=None, worker=_FakeWorker(pid=12345))

    assert calls == [12345]
