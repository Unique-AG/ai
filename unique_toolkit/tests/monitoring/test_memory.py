"""Tests for unique_toolkit.monitoring.memory module."""

import threading

import pytest

from unique_toolkit.monitoring import memory

pytestmark = pytest.mark.ai


@pytest.fixture(autouse=True)
def _reset_module_state(monkeypatch: pytest.MonkeyPatch):
    """Each test gets a clean slate for the module's memoized/idempotency state."""
    monkeypatch.setattr(memory, "_libc", None)
    monkeypatch.setattr(memory, "_trimmer_started", False)
    monkeypatch.setattr(memory, "_watcher_started", False)


def test_trim_memory__calls_gc_collect_and_malloc_trim__on_linux(
    monkeypatch: pytest.MonkeyPatch,
):
    gc_calls: list[None] = []
    monkeypatch.setattr(memory.gc, "collect", lambda: gc_calls.append(None) or 0)

    trim_calls: list[int] = []
    fake_libc = type(
        "FakeLibc", (), {"malloc_trim": lambda self, n: trim_calls.append(n)}
    )()
    monkeypatch.setattr(memory, "_get_libc", lambda: fake_libc)
    monkeypatch.delenv("MEMORY_TRIM_MALLOC_TRIM", raising=False)
    monkeypatch.delenv("LD_PRELOAD", raising=False)

    memory.trim_memory("test")

    assert gc_calls == [None]
    assert trim_calls == [0]


def test_trim_memory__skips_malloc_trim__when_disabled_via_env(
    monkeypatch: pytest.MonkeyPatch,
):
    trim_calls: list[int] = []
    fake_libc = type(
        "FakeLibc", (), {"malloc_trim": lambda self, n: trim_calls.append(n)}
    )()
    monkeypatch.setattr(memory, "_get_libc", lambda: fake_libc)
    monkeypatch.setenv("MEMORY_TRIM_MALLOC_TRIM", "false")
    monkeypatch.delenv("LD_PRELOAD", raising=False)

    memory.trim_memory("test")

    assert trim_calls == []


def test_trim_memory__skips_malloc_trim__when_jemalloc_preloaded(
    monkeypatch: pytest.MonkeyPatch,
):
    trim_calls: list[int] = []
    fake_libc = type(
        "FakeLibc", (), {"malloc_trim": lambda self, n: trim_calls.append(n)}
    )()
    monkeypatch.setattr(memory, "_get_libc", lambda: fake_libc)
    monkeypatch.delenv("MEMORY_TRIM_MALLOC_TRIM", raising=False)
    monkeypatch.setenv("LD_PRELOAD", "/usr/lib/libjemalloc.so.2")

    memory.trim_memory("test")

    assert trim_calls == []


def test_get_libc__returns_none__when_malloc_trim_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(memory.platform, "system", lambda: "Linux")
    monkeypatch.setattr(memory.ctypes, "CDLL", lambda *args, **kwargs: object())

    assert memory._get_libc() is None


def test_start_memory_trimmer__is_idempotent(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MEMORY_TRIM_INTERVAL_SECONDS", "10")
    started: list[threading.Thread] = []
    monkeypatch.setattr(threading.Thread, "start", lambda self: started.append(self))

    memory.start_memory_trimmer()
    memory.start_memory_trimmer()

    trimmer_threads = [t for t in started if t.name == "memory-trimmer"]
    assert len(trimmer_threads) == 1


def test_start_rss_ceiling_watcher__noops__with_no_env_set(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("MEMORY_TRIM_MAX_RSS_MIB", raising=False)
    monkeypatch.delenv("CONTAINER_MEMORY_LIMIT_MIB", raising=False)
    started: list[threading.Thread] = []
    monkeypatch.setattr(
        threading.Thread,
        "start",
        lambda self: started.append(self),
    )

    memory.start_rss_ceiling_watcher()

    assert started == []
    assert memory._watcher_started is False


@pytest.mark.parametrize(
    "limit_mib,process_count,expected",
    [
        (1000, 2, 450),
        (512, 1, 460),
    ],
)
def test_resolve_max_rss_mib__computes_from_container_limit_and_process_count(
    monkeypatch: pytest.MonkeyPatch, limit_mib: int, process_count: int, expected: int
):
    monkeypatch.delenv("MEMORY_TRIM_MAX_RSS_MIB", raising=False)
    monkeypatch.setenv("CONTAINER_MEMORY_LIMIT_MIB", str(limit_mib))
    monkeypatch.setenv("MEMORY_TRIM_PROCESS_COUNT", str(process_count))

    assert memory._resolve_max_rss_mib() == expected


def test_resolve_max_rss_mib__explicit_override_wins(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MEMORY_TRIM_MAX_RSS_MIB", "777")
    monkeypatch.setenv("CONTAINER_MEMORY_LIMIT_MIB", "1000")

    assert memory._resolve_max_rss_mib() == 777


def test_rss_check_tick__requires_two_consecutive_over_limit_checks__before_kill(
    monkeypatch: pytest.MonkeyPatch,
):
    kill_calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        memory.os, "kill", lambda pid, sig: kill_calls.append((pid, sig))
    )

    consecutive = memory._rss_check_tick(
        rss_mib=600, max_rss_mib=500, consecutive_high=0
    )
    assert consecutive == 1
    assert kill_calls == []

    consecutive = memory._rss_check_tick(
        rss_mib=600, max_rss_mib=500, consecutive_high=consecutive
    )
    assert consecutive == 2
    assert kill_calls == [(memory.os.getpid(), memory.signal.SIGTERM)]


def test_rss_check_tick__resets_streak__when_back_under_limit(
    monkeypatch: pytest.MonkeyPatch,
):
    kill_calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        memory.os, "kill", lambda pid, sig: kill_calls.append((pid, sig))
    )

    consecutive = memory._rss_check_tick(
        rss_mib=600, max_rss_mib=500, consecutive_high=0
    )
    assert consecutive == 1

    consecutive = memory._rss_check_tick(
        rss_mib=400, max_rss_mib=500, consecutive_high=consecutive
    )
    assert consecutive == 0
    assert kill_calls == []
