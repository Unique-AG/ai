"""Process-level memory hygiene: periodic glibc malloc_trim + an opt-in RSS ceiling watcher.

Call once at process startup, after any forking — e.g. right before
`mcp.run()` for a `unique_mcp` server, or from a gunicorn `post_worker_init`
hook (which already runs post-fork, once per worker). Calling this before a
fork (e.g. from `preload_app`) is unsupported: the background thread doesn't
survive the fork, but the idempotency guard does, so every worker would
silently inherit "already started" and never get one.
"""

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

_LIBC = None


def _get_libc():
    global _LIBC
    if _LIBC is None and platform.system() == "Linux":
        try:
            lib = ctypes.CDLL("libc.so.6", use_errno=True)
            lib.malloc_trim.argtypes = [ctypes.c_size_t]
            lib.malloc_trim.restype = ctypes.c_int
            _LIBC = lib
        except OSError:
            _LIBC = False
    return _LIBC or None


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
    """Run gc.collect() then ask glibc to return free pages to the OS.

    Logs reclaimed MiB, trim latency, gc cycle count, and uncollectable
    objects so dashboards can confirm the trim is working.

    No-op for malloc_trim (gc still runs) when:
    - not running on Linux
    - MEMORY_TRIM_MALLOC_TRIM=false
    - jemalloc is preloaded via LD_PRELOAD (jemalloc returns pages via its
      own background thread; calling libc malloc_trim would be a no-op anyway)
    """
    before = _read_rss_mib()
    t0 = time.time()

    unreachable = gc.collect()

    if os.getenv(
        "MEMORY_TRIM_MALLOC_TRIM", "true"
    ).lower() == "true" and "jemalloc" not in os.getenv("LD_PRELOAD", ""):
        libc = _get_libc()
        if libc is not None:
            libc.malloc_trim(0)

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
    """Start a background daemon thread that periodically trims memory.

    Call once at process startup. Idempotent: safe to call multiple times.
    """
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
    """Return the per-process RSS ceiling in MiB.

    Precedence:
    1. MEMORY_TRIM_MAX_RSS_MIB — explicit override (0 = disabled)
    2. CONTAINER_MEMORY_LIMIT_MIB / MEMORY_TRIM_PROCESS_COUNT * 0.9
       (injected by Kubernetes Downward API from resources.limits.memory)
    3. 0 (disabled) if no limit is configured

    Migration note: MEMORY_TRIM_PROCESS_COUNT replaces assistants-core's
    GUNICORN_WORKERS as the divisor here. A multi-worker gunicorn deployment
    adopting this function MUST set MEMORY_TRIM_PROCESS_COUNT to its actual
    worker count — the default of 1 assumes a single-process service. Left
    unset on a multi-worker deployment, each worker computes its ceiling as
    if it were the only process, so N workers can together exceed the
    container's real memory limit before any one of them individually trips
    the watcher.
    """
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
) -> int:
    """Run one check cycle; return the updated consecutive-over-limit count.

    Requires two consecutive over-limit checks before sending SIGTERM, so a
    single transient spike (e.g. a large in-flight request) doesn't recycle
    the process — only RSS that's still over the ceiling on the next check,
    one interval later, does.
    """
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
    return consecutive_high


_watcher_started = False
_watcher_lock = threading.Lock()


def start_rss_ceiling_watcher() -> None:
    """Start a background daemon that SIGTERMs this process if RSS stays over a ceiling.

    Opt-in: only takes effect once a ceiling resolves to > 0 (see
    `_resolve_max_rss_mib`) — otherwise this is a no-op and no thread is
    spawned. Call explicitly from a service that wants this safety net; it is
    not started automatically by anything else in this module. Idempotent:
    safe to call multiple times.
    """
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
                consecutive_high = _rss_check_tick(
                    _read_rss_mib(), max_rss_mib, consecutive_high
                )
            except Exception:
                logger.exception("rss-ceiling-watcher cycle failed; continuing")

    threading.Thread(target=_loop, name="rss-ceiling-watcher", daemon=True).start()
    logger.info(
        "[MEMORY-LIMIT] RSS ceiling watcher armed: max_rss_mib=%d interval=%ds",
        max_rss_mib,
        interval,
    )
