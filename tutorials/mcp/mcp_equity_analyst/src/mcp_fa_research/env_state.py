"""env_state.py — per-environment demo state (the FA analogue of the RM CRM env map).

The FA Research MCP is ONE deployment shared across environments/tenants. Like the RM
Agent MCPs, the env signal rides on the connector URL as a PATH segment — the only
thing settable per environment in admin:

    https://fa-research-mcp.azurewebsites.net/mcp            → env "qa" (default)
    https://fa-research-mcp.azurewebsites.net/prod/mcp       → env "prod"
    https://fa-research-mcp.azurewebsites.net/pascal/mcp     → env "pascal"

Each env gets its OWN copy of the mutable demo state (coverage, brief, emails,
calendar, scenarios), lazily materialized from ``seed.baseline()`` on first touch —
so a sales person can run a personal sandbox at /<their-name>/mcp + /<their-name>/admin
without touching anyone else's demo. In-memory by design: Reset (per env) and a
container restart restore the baseline snapshot. ALL DATA IS SYNTHETIC.
"""

from __future__ import annotations

import contextvars
import re

import os

import seed

DEFAULT_ENV = "qa"
# One connector per environment, discriminated in the PATH — same convention as the
# RM Agent MCPs (qa / uat / bnpp / sales / local). These are pre-materialized at
# startup so the console lists them immediately; extra ad-hoc slugs (e.g. /pascal/…)
# still materialize lazily as personal sandboxes. Extend via FA_EXTRA_ENVS=csv.
KNOWN_ENVS: tuple[str, ...] = tuple(
    e.strip() for e in
    ("qa,uat,bnpp,sales,local," + (__import__("os").getenv("FA_EXTRA_ENVS") or "")).split(",")
    if e.strip())
_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,23}$")
_RESERVED = {"mcp", "admin", "api", "health", "favicon.ico"}

_url_env: contextvars.ContextVar[str] = contextvars.ContextVar("fa_url_env", default="")

STATES: dict[str, dict] = {}


def is_env_segment(s: str) -> bool:
    return bool(_SLUG.match(s)) and s not in _RESERVED


def set_url_env(env: str) -> None:
    _url_env.set(env or "")


def current_env() -> str:
    env = _url_env.get() or ""
    if not env:  # fallback: the request scope (survives task switches, à la RM CRM)
        try:
            from fastmcp.server.dependencies import get_http_request

            req = get_http_request()
            env = (req.scope.get("fa_env") or "") if req is not None else ""
        except Exception:
            env = ""
    return env or DEFAULT_ENV


def _fresh(env: str) -> dict:
    """A new baseline state, auto-rebased to today (Zurich) unless FA_AUTO_REBASE=0 —
    a restart or reset then never leaves past-dated scheduled jobs / stale story
    dates behind (the ticker would fire them all at boot otherwise)."""
    st = seed.baseline(env)
    if (os.getenv("FA_AUTO_REBASE") or "1").strip() != "0":
        seed.rebase_state(st)
    return st


def state() -> dict:
    """The ACTIVE environment's mutable state, materialized on first touch."""
    env = current_env()
    st = STATES.get(env)
    if st is None:
        st = STATES[env] = _fresh(env)
    return st


def reset() -> dict:
    env = current_env()
    STATES[env] = _fresh(env)
    return STATES[env]


def materialize_known() -> None:
    """Pre-create the known environments' states (startup)."""
    for e in KNOWN_ENVS:
        STATES.setdefault(e, _fresh(e))


def envs() -> list[str]:
    return sorted(set(STATES) | set(KNOWN_ENVS) | {DEFAULT_ENV})
