"""jobs_engine.py — makes the cockpit's demo jobs actually run on their schedule.

The storyline jobs (seed.JOBS_SEED, per-env state) carry run_at ("YYYY-MM-DD HH:MM",
Europe/Zurich) + recurrence (once|daily — once is the default so nothing recurs, and
consumes tokens, unless opted in). A small ticker thread checks every materialized
environment and, when a scheduled job's run_at comes due, executes it. Editing a
job's schedule in the console is therefore LIVE: set run_at a minute ahead and watch.

Executor kinds:
  control_sweep  REAL (in-memory) — SLA watchdog over the maker/checker queue:
              flags pending control items past their priority's SLA (URGENT 2h,
              send-by 24h, standard 48h) by prefixing "⚠ OVERDUE" onto the
              priority the Control Room canvas displays, and posts the cockpit
              notification ("N awaiting control, M overdue"). No tokens.
  sdk_regen   REAL — rebuild the six coverage reviews + coverage cards and upload
              them to that env's Knowledge Base via the Unique SDK (same engine as
              the 00:00 nightly). Per-document progress + content ids are written
              into job["last_run"] as uploads happen, so the console and cockpit
              show the run progressing and, afterwards, exactly what was generated.
  (none)      simulated — scheduled → running → done on a short timer; storyline
              colour only, no tokens, no uploads.

After a run: recurrence "daily" advances run_at to the next FUTURE day (same time)
and re-arms the job; "once" parks it at done. POST /admin/api/job/{idx}/run (the
console ▶ button) starts a job immediately, ignoring run_at.
"""

from __future__ import annotations

import threading
import time
import traceback
from datetime import date, datetime, timedelta

import env_state
import nightly

SIM_SECONDS = 30      # simulated jobs "run" this long
TICK_SECONDS = 10     # schedule check cadence

_LAUNCHED: set[int] = set()   # id(job) of jobs with a live worker thread


def _now_minute() -> str:
    return datetime.now(nightly.ZURICH).strftime("%Y-%m-%d %H:%M")


def _advance(job: dict) -> None:
    """Post-run scheduling: daily → next future occurrence, once → done."""
    if (job.get("recurrence") or "once") == "daily" and job.get("run_at"):
        try:
            d = date.fromisoformat(job["run_at"][:10])
            suffix = job["run_at"][10:]
            now_s = _now_minute()
            while d.isoformat() + suffix <= now_s:
                d += timedelta(days=1)
            job["run_at"] = d.isoformat() + suffix
            job["status"] = "scheduled"
        except ValueError:
            job["status"] = "done"
    else:
        job["status"] = "done"


_SLA_HOURS = (("URGENT", 2), ("Send-by", 24))   # priority keyword → hours; else 48
_OVERDUE = "⚠ OVERDUE · "


def _control_sweep(env: str, lr: dict) -> None:
    st = env_state.STATES[env]
    now = datetime.now(nightly.ZURICH)
    pending, overdue = 0, []
    for it in st.get("control_queue", []):
        if it.get("status") != "pending":
            continue
        pending += 1
        try:
            sub = datetime.strptime(it["submitted_at"].replace(_OVERDUE, ""),
                                    "%Y-%m-%d %H:%M").replace(tzinfo=nightly.ZURICH)
        except (KeyError, ValueError):
            continue
        base_prio = it["priority"].replace(_OVERDUE, "").split(" — pending ")[0]
        sla = next((h for kw, h in _SLA_HOURS if kw.lower() in base_prio.lower()), 48)
        age_h = (now - sub).total_seconds() / 3600
        if age_h > sla:
            overdue.append(it["id"])
            it["priority"] = f"{_OVERDUE}{base_prio} — pending {age_h:.0f}h (SLA {sla}h)"
        else:
            it["priority"] = base_prio
    lr["pending"], lr["overdue"] = pending, overdue
    lr["summary"] = (f"{pending} product(s) awaiting control, {len(overdue)} overdue "
                     f"({', '.join(overdue) or '—'})")
    lr["summary_short"] = f"{pending} pending · {len(overdue)} overdue"
    if pending:
        st["jobs"]["notification"] = (
            f"Control sweep: {pending} product(s) awaiting pre-publication control"
            + (f" — {len(overdue)} OVERDUE, checker action required." if overdue else "."))
    lr["ok"] = True


def _run(env: str, job: dict) -> None:
    executor = job.get("executor")
    kind = executor if executor in ("sdk_regen", "control_sweep") else "simulated"
    lr = job["last_run"] = {
        "started": datetime.now(nightly.ZURICH).isoformat(timespec="seconds"),
        "kind": kind,
        "done": 0, "total": 0, "files": [], "ok": None,
    }
    try:
        if lr["kind"] == "control_sweep":
            _control_sweep(env, lr)
            lr["finished"] = datetime.now(nightly.ZURICH).isoformat(timespec="seconds")
            _advance(job)
        elif lr["kind"] == "sdk_regen":
            if env not in nightly.SDK_CREDS:
                lr["ok"] = False
                lr["error"] = (f"no Unique SDK credentials for env {env!r} — "
                               "real runs work in qa / uat / sales")
            else:
                def progress(done, total, relpath, cid):
                    lr["done"], lr["total"] = done, total
                    lr["files"].append({"path": relpath, "content_id": cid})

                res = nightly.regen_env(env, progress=progress, rebase=False)
                lr["ok"] = bool(res.get("ok"))
                if res.get("error"):
                    lr["error"] = res["error"]
                if res.get("id_drift"):
                    lr["id_drift"] = res["id_drift"]
            lr["finished"] = datetime.now(nightly.ZURICH).isoformat(timespec="seconds")
            _advance(job)
        else:
            lr["sim_ends"] = time.time() + SIM_SECONDS   # the ticker completes it
    except Exception as ex:
        lr["ok"] = False
        lr["error"] = f"{type(ex).__name__}: {ex}"
        lr["finished"] = datetime.now(nightly.ZURICH).isoformat(timespec="seconds")
        traceback.print_exc()
        _advance(job)
    finally:
        _LAUNCHED.discard(id(job))


def launch(env: str, job: dict) -> dict:
    """Start a job now (ticker or console ▶). Returns a small status dict."""
    if job.get("status") == "running" or id(job) in _LAUNCHED:
        return {"started": False, "error": "job is already running"}
    _LAUNCHED.add(id(job))
    job["status"] = "running"
    threading.Thread(target=_run, args=(env, job),
                     name=f"fa-job-{env}", daemon=True).start()
    ex = job.get("executor")
    return {"started": True,
            "kind": ex if ex in ("sdk_regen", "control_sweep") else "simulated"}


def _tick() -> None:
    now_s = _now_minute()
    for env in list(env_state.STATES.keys()):
        st = env_state.STATES.get(env)
        if not st:
            continue
        for job in st["jobs"]["jobs"]:
            status = job.get("status")
            if status == "scheduled" and job.get("run_at") and job["run_at"] <= now_s:
                launch(env, job)
            elif status == "running":
                lr = job.get("last_run") or {}
                if lr.get("kind") == "simulated" and lr.get("sim_ends") \
                        and time.time() >= lr["sim_ends"]:
                    lr["ok"] = True
                    lr["finished"] = datetime.now(nightly.ZURICH).isoformat(
                        timespec="seconds")
                    lr.pop("sim_ends", None)
                    _advance(job)


def _loop() -> None:
    while True:
        try:
            _tick()
        except Exception:
            traceback.print_exc()
        time.sleep(TICK_SECONDS)


def start() -> None:
    threading.Thread(target=_loop, name="fa-jobs", daemon=True).start()
