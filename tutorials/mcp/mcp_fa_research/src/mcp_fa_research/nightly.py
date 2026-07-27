"""nightly.py — the in-process document scheduler (per environment, Zurich time).

Two daily jobs, running INSIDE the MCP webapp (one deployment serves every env):

  00:00 Europe/Zurich   REGENERATE per environment: optionally rebase the demo state
                        to the new day, rebuild the six coverage reviews + coverage
                        cards (canvases.build_all, stamped `fa-nightly: <iso>`), and
                        upload them to that environment's KB via the Unique SDK
                        (unique_toolkit KnowledgeBaseService — path-upsert, ids stable).
  08:00 Europe/Zurich   VERIFY per environment: download a stamped review and check
                        the stamp is from last night and carries the right env.

Configuration (webapp app settings):
  FA_SDK_CREDS_JSON     {"qa": {"api_base","app_id","app_key","company_id","user_id"}, …}
                        — envs without creds are skipped.
  FA_NOTE_IDS_BY_ENV_JSON  {"qa": {"MC FP": {"initiation": "cont_…", …}, …}, …}
  FA_NIGHTLY_REBASE     "1" (default) to rebase each env's story dates to the new day.
  FA_NIGHTLY_ENVS       csv override of which envs to run (default: all with creds).

Status is kept in memory (NIGHTLY_STATUS), served on /admin/api/nightly and shown in
the console header. POST /admin/api/nightly/run {"env","job":"regen"|"verify"} runs a
job immediately. NOTE: the webapp needs Always On, or the container sleeps at night.
"""

from __future__ import annotations

import json
import os
import threading
import time
import traceback
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import seed

ZURICH = ZoneInfo("Europe/Zurich")
REGEN_AT = (0, 0)    # 00:00
VERIFY_AT = (8, 0)   # 08:00

NIGHTLY_STATUS: dict = {"regen": {}, "verify": {}, "scheduler": "not started"}

try:
    SDK_CREDS: dict = json.loads(os.getenv("FA_SDK_CREDS_JSON", "") or "{}")
except Exception:
    SDK_CREDS = {}
try:
    NOTE_IDS_BY_ENV: dict = json.loads(os.getenv("FA_NOTE_IDS_BY_ENV_JSON", "") or "{}")
except Exception:
    NOTE_IDS_BY_ENV = {}

_ENVS = [e.strip() for e in (os.getenv("FA_NIGHTLY_ENVS") or ",".join(SDK_CREDS)).split(",")
         if e.strip() and e.strip() in SDK_CREDS]
_REBASE = (os.getenv("FA_NIGHTLY_REBASE") or "1").strip() != "0"

_SDK_LOCK = threading.Lock()  # unique_sdk config is module-global — serialize env use


def _kb(env: str):
    """Point the global unique_sdk config at ONE env and return its KB service."""
    import unique_sdk
    from unique_toolkit import KnowledgeBaseService

    c = SDK_CREDS[env]
    unique_sdk.api_base = c["api_base"]
    unique_sdk.api_key = c["app_key"]
    unique_sdk.app_id = c["app_id"]
    return KnowledgeBaseService(company_id=c["company_id"], user_id=c["user_id"])


def _scope_for(env: str, folder_path: str) -> str:
    import unique_sdk

    c = SDK_CREDS[env]
    sid = unique_sdk.Folder.resolve_scope_id_from_folder_path_with_create(
        c["user_id"], c["company_id"], folder_path=folder_path,
        create_if_not_exists=False)
    if not (sid or "").startswith("scope_"):
        raise RuntimeError(f"cannot resolve scope for {folder_path!r} in {env}")
    return sid


def _rebase_env_state(env: str) -> int:
    """Shift the env's live state so story-today = today (shared seed helper)."""
    import env_state

    st = env_state.STATES.setdefault(env, seed.baseline(env))
    return seed.rebase_state(st)


def regen_env(env: str, progress=None, rebase: bool | None = None) -> dict:
    """Regenerate + upload one env's reviews/cards; progress(done, total, relpath, cid)
    fires after each SDK upload. Used by the 00:00 nightly AND the cockpit's real job."""
    import canvases

    started = datetime.now(ZURICH).isoformat(timespec="seconds")
    result = {"started": started, "ok": False, "files": 0, "id_drift": [],
              "rebased_days": 0}
    try:
        if _REBASE if rebase is None else rebase:
            result["rebased_days"] = _rebase_env_state(env)
        review_ids = dict(seed.REVIEW_IDS_BY_ENV.get(env) or {})
        note_ids = NOTE_IDS_BY_ENV.get(env) or {}
        files = canvases.build_all(env, review_ids, note_ids, started)
        with _SDK_LOCK:
            kb = _kb(env)
            for relpath, text in files.items():
                folder = "/Fundamental Analyst/" + relpath.rsplit("/", 1)[0]
                name = relpath.rsplit("/", 1)[1]
                scope = _scope_for(env, folder)
                mime = "text/html" if name.endswith(".html") else "text/markdown"
                up = kb.upload_content_from_bytes(
                    content=text.encode("utf-8"), content_name=name,
                    mime_type=mime, scope_id=scope)
                cid = getattr(up, "id", None) or (up.get("id") if isinstance(up, dict) else "")
                tk = relpath.split("/")[1]
                expected = review_ids.get(tk)
                if name == "review.html" and expected and cid and cid != expected:
                    result["id_drift"].append(f"{tk}: {expected} -> {cid}")
                result["files"] += 1
                if progress:
                    progress(result["files"], len(files), relpath, cid)
        result["ok"] = not result["id_drift"]
    except Exception as ex:
        result["error"] = f"{type(ex).__name__}: {ex}"
        traceback.print_exc()
    result["finished"] = datetime.now(ZURICH).isoformat(timespec="seconds")
    return result


def run_regen(env: str) -> dict:
    result = regen_env(env)
    NIGHTLY_STATUS["regen"][env] = result
    return result


def run_verify(env: str) -> dict:
    started = datetime.now(ZURICH).isoformat(timespec="seconds")
    result = {"started": started, "ok": False}
    try:
        review_ids = seed.REVIEW_IDS_BY_ENV.get(env) or {}
        cid = review_ids.get("MC FP")
        if not cid:
            raise RuntimeError(f"no review id map for env {env}")
        with _SDK_LOCK:
            kb = _kb(env)
            data = kb.download_content_to_bytes(content_id=cid).decode("utf-8", "ignore")
        has_stamp = "fa-nightly:" in data and f"env={env}" in data
        stamp_date = ""
        if has_stamp:
            stamp_date = data.split("fa-nightly:", 1)[1].strip()[:10]
        fresh = stamp_date == datetime.now(ZURICH).date().isoformat()
        result.update({"stamp_found": has_stamp, "stamp_date": stamp_date,
                       "fresh_today": fresh, "ok": has_stamp and fresh})
        if not result["ok"]:
            result["error"] = ("no nightly stamp — regen has not run against this env yet"
                               if not has_stamp else
                               f"stale stamp {stamp_date} — last night's regen missing")
    except Exception as ex:
        result["error"] = f"{type(ex).__name__}: {ex}"
    result["finished"] = datetime.now(ZURICH).isoformat(timespec="seconds")
    NIGHTLY_STATUS["verify"][env] = result
    return result


def _next_at(hh: int, mm: int) -> datetime:
    now = datetime.now(ZURICH)
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target


def _loop():
    NIGHTLY_STATUS["scheduler"] = (f"running — envs {_ENVS or ['(none — no creds)']}, "
                                   f"regen 00:00 / verify 08:00 Europe/Zurich, "
                                   f"rebase={'on' if _REBASE else 'off'}")
    while True:
        nxt_regen, nxt_verify = _next_at(*REGEN_AT), _next_at(*VERIFY_AT)
        nxt, job = min((nxt_regen, "regen"), (nxt_verify, "verify"))
        NIGHTLY_STATUS["next"] = f"{job} at {nxt.isoformat(timespec='minutes')}"
        while datetime.now(ZURICH) < nxt:
            time.sleep(30)
        for env in _ENVS:
            try:
                (run_regen if job == "regen" else run_verify)(env)
            except Exception:
                traceback.print_exc()


def start():
    if not SDK_CREDS:
        NIGHTLY_STATUS["scheduler"] = "disabled — FA_SDK_CREDS_JSON not set"
        return
    threading.Thread(target=_loop, name="fa-nightly", daemon=True).start()
