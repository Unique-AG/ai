"""Process-level memory trimming and optional RSS ceiling monitoring."""

from __future__ import annotations

import ctypes
import gc
import logging
import os
import platform
import signal
import threading
import time

logger = logging.getLogger(__name__)

_SAFETY_FACTOR = 0.9

_libc = None


def _get_libc():
    global _libc
    if _libc is None and platform.system() == "Linux":
        try:
            lib = ctypes.CDLL("libc.so.6", use_errno=True)
            lib.malloc_trim.argtypes = [ctypes.c_size_t]
            lib.malloc_trim.restype = ctypes.c_int
            _libc = lib
        except (AttributeError, OSError):
            _libc = False
    return _libc or None


def _read_rss_mib() -> float | None:
    """Return this process's resident set size in MiB, or None off Linux."""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    return None


def trim_memory(reason: str) -> None:
    """Collect garbage and ask glibc to return free pages to the OS."""
    before = _read_rss_mib()
    t0 = time.time()

    unreachable = gc.collect()

    if os.getenv(
        "MEMORY_TRIM_MALLOC_TRIM", "true"
    ).lower() == "true" and "jemalloc" not in os.getenv("LD_PRELOAD", ""):
        libc = _get_libc()
        if libc is not None:
            getattr(libc, "malloc_trim")(0)

    after = _read_rss_mib()
    reclaimed = before - after if before is not None and after is not None else None
    logger.info(
        "[MEMORY-TRIM:%s] rss: %s MiB | reclaimed: %s MiB | trim_ms: %.0f | "
        "gc_unreachable: %d | gc_garbage: %d",
        reason,
        f"{after:.0f}" if after is not None else "n/a",
        f"{reclaimed:.2f}" if reclaimed is not None else "n/a",
        (time.time() - t0) * 1000,
        unreachable,
        len(gc.garbage),
    )


_trimmer_started = False
_trimmer_lock = threading.Lock()


def start_memory_trimmer() -> None:
    """Start an idempotent daemon thread that periodically trims process memory."""
    global _trimmer_started
    with _trimmer_lock:
        if _trimmer_started:
            return
        _trimmer_started = True

    try:
        interval = max(10, int(os.getenv("MEMORY_TRIM_INTERVAL_SECONDS", "120")))
    except ValueError:
        interval = 120

    def _loop() -> None:
        while True:
            time.sleep(interval)
            try:
                trim_memory("periodic")
            except Exception:
                logger.exception("memory-trimmer cycle failed; continuing")

    threading.Thread(target=_loop, name="memory-trimmer", daemon=True).start()
    logger.info("[MEMORY-TRIM] periodic trimmer armed: interval=%ds", interval)


def _resolve_max_rss_mib() -> int:
    """Resolve the per-process RSS ceiling from environment variables."""
    explicit = os.getenv("MEMORY_TRIM_MAX_RSS_MIB")
    if explicit is not None:
        try:
            return int(explicit)
        except ValueError:
            logger.warning(
                "[MEMORY-LIMIT] MEMORY_TRIM_MAX_RSS_MIB=%r is not a valid integer — ignoring",
                explicit,
            )

    try:
        limit_mib = int(os.getenv("CONTAINER_MEMORY_LIMIT_MIB", "0"))
    except ValueError:
        return 0
    if limit_mib <= 0:
        return 0

    try:
        process_count = max(1, int(os.getenv("MEMORY_TRIM_PROCESS_COUNT", "1")))
    except ValueError:
        process_count = 1
    return int(limit_mib / process_count * _SAFETY_FACTOR)


def _rss_check_tick(
    rss_mib: float | None, max_rss_mib: int, consecutive_high: int
) -> int | None:
    """Update the over-limit streak and terminate after two high readings."""
    if rss_mib is None:
        return consecutive_high
    if rss_mib <= max_rss_mib:
        return 0

    consecutive_high += 1
    logger.info(
        "[MEMORY-LIMIT] RSS %.0f MiB > limit %d MiB (strike %d/2)",
        rss_mib,
        max_rss_mib,
        consecutive_high,
    )
    if consecutive_high >= 2:
        logger.info("[MEMORY-LIMIT] RSS sustained above limit — sending SIGTERM")
        os.kill(os.getpid(), signal.SIGTERM)
        return None
    return consecutive_high


_watcher_started = False
_watcher_lock = threading.Lock()


def start_rss_ceiling_watcher() -> None:
    """Start an idempotent daemon that SIGTERMs the process after high RSS readings."""
    max_rss_mib = _resolve_max_rss_mib()
    if max_rss_mib <= 0:
        logger.info("[MEMORY-LIMIT] RSS ceiling watcher disabled (no limit configured)")
        return

    global _watcher_started
    with _watcher_lock:
        if _watcher_started:
            return
        _watcher_started = True

    try:
        interval = max(
            5, int(os.getenv("MEMORY_TRIM_RSS_CHECK_INTERVAL_SECONDS", "30"))
        )
    except ValueError:
        interval = 30

    def _loop() -> None:
        consecutive_high = 0
        while True:
            time.sleep(interval)
            try:
                next_consecutive_high = _rss_check_tick(
                    _read_rss_mib(), max_rss_mib, consecutive_high
                )
                if next_consecutive_high is None:
                    return
                consecutive_high = next_consecutive_high
            except Exception:
                logger.exception("rss-ceiling-watcher cycle failed; continuing")

    threading.Thread(target=_loop, name="rss-ceiling-watcher", daemon=True).start()
    logger.info(
        "[MEMORY-LIMIT] RSS ceiling watcher armed: max_rss_mib=%d interval=%ds",
        max_rss_mib,
        interval,
    )
