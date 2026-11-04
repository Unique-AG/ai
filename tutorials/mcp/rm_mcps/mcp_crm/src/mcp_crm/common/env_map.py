"""env_map.py — environment-aware KB content-id resolution.

The RM Agent MCPs are a SINGLE deployment shared across environments
(QA / UAT / prod-bnpp / prod-sales / local). KB content ids ("cont_…") are
env-specific — the same document has a different id in each environment's KB — so
the CRM tools must return the id for the *caller's* environment, not a baked one.

How the env is detected (see ``env_from_ctx``)
----------------------------------------------
1. **Connector URL path segment** — ``https://…/<env>/mcp`` (e.g. ``/sales/mcp``), set
   per environment on the connector's URL in admin. This is the PRIMARY signal: the
   admin accepts a plain path (it rejects a ``?env=`` query), and it needs NO platform
   feature. A small ASGI middleware (``mcp_crm.EnvPathMiddleware``) reads the ``<env>``
   segment, stashes it for this request, and rewrites the path back to ``/mcp`` so
   FastMCP still routes the endpoint. Robust to ``/<env>/mcp`` and ``/mcp/<env>``.
2. **Connector URL query** — ``https://…/mcp?env=<env>``. Same effect, but the prod
   admin rejects a query string, so this is only useful for direct / local testing.
3. **Forwarded company id** — ``_meta.companyId`` mapped via ``COMPANY_ENV``, IF the
   connector has the ``unique.app/auth/`` forwarding namespace enabled (node-chat:
   extended-mcp-server sets ``_meta.companyId`` / ``_meta.userId``).
4. Otherwise ``DEFAULT_ENV``.

The resolved env keys into the ``content_id_map(env, map_key, content_id)`` table
(seeded per env by ``generate_sql``).

Graceful degradation
---------------------
If auth-forwarding is off, the company is unknown, or the ``(env, map_key)`` has no
row, ``content_id_for`` returns ``""`` — callers then open by ``filePath`` (which is
env-agnostic) instead of a wrong/dead content id. So a missing map never breaks a
link; it just drops the "open by content id" upgrade.
"""

import contextvars
import json
import os

from common.db import query_one

# company_id → env label. Extend/override at deploy time with RM_COMPANY_ENV_JSON
# (a JSON object {"<company_id>": "<env>"}), so new tenants don't need a code change.
COMPANY_ENV: dict[str, str] = {
    "225319369280852798": "qa",
    "331003534495449220": "uat",
    "295318162692374905": "bnpp",
    "304938286579712187": "sales",
    "372585284832854019": "local",
}
try:
    COMPANY_ENV.update(json.loads(os.getenv("RM_COMPANY_ENV_JSON", "") or "{}"))
except Exception:
    pass

# Env used when the caller's company can't be determined (forwarding off / unknown).
DEFAULT_ENV = (os.getenv("RM_DEFAULT_ENV") or "qa").strip() or "qa"

# The set of addressable env labels — used both as the content_id_map key space and as
# the allowlist for the URL-path signal (only these segments are treated as an env, so
# a stray path segment can never be mistaken for one, and `env` is never raw input).
KNOWN_ENVS = frozenset(COMPANY_ENV.values())

# Per-request env parsed from the connector URL path by the ASGI middleware
# (mcp_crm.EnvPathMiddleware), read back by `_env_from_request`. A ContextVar so it is
# isolated per request/task and never leaks across concurrent calls.
_URL_ENV: contextvars.ContextVar[str] = contextvars.ContextVar("rm_url_env", default="")


def set_url_env(env: str) -> None:
    """Record the env parsed from the request URL path (called by the middleware).

    Ignores anything not in ``KNOWN_ENVS`` so only a real, allowlisted env label is ever
    stored — the value later interpolated nowhere as SQL, only compared / used as a key."""
    _URL_ENV.set(env if env in KNOWN_ENVS else "")


def _company_from_ctx(ctx) -> str:
    """Best-effort read of the forwarded caller company id from the tool-call ``_meta``.

    Defensive across fastmcp / mcp-SDK versions — ``companyId`` is a custom ``_meta``
    key, so it may surface as a model attribute, in ``model_extra``, or as a plain
    dict entry. Returns "" if not present (→ DEFAULT_ENV)."""
    if ctx is None:
        return ""
    meta = None
    for accessor in (
        lambda: ctx.request_context.meta,
        lambda: ctx.request_context.request.params.meta,
        lambda: ctx.meta,
    ):
        try:
            meta = accessor()
            if meta is not None:
                break
        except Exception:
            continue
    if meta is None:
        return ""
    for getter in (
        lambda: getattr(meta, "companyId", None),
        lambda: meta.get("companyId") if isinstance(meta, dict) else None,
        lambda: (getattr(meta, "model_extra", None) or {}).get("companyId"),
    ):
        try:
            v = getter()
            if v:
                return str(v)
        except Exception:
            continue
    return ""


def _env_from_request() -> str:
    """Explicit env from the connector URL, without any platform feature.

    Priority:
      1. the URL **path segment** ``…/<env>/mcp``, captured by the ASGI path middleware
         (``mcp_crm.EnvPathMiddleware``) into ``_URL_ENV`` — the signal the admin accepts;
      2. a ``?env=<env>`` **query** param (direct / local testing; prod admin rejects it);
      3. a known-env segment still present in the raw request path (belt-and-suspenders,
         e.g. if the middleware is not installed).
    """
    e = _URL_ENV.get()
    if e:
        return e
    try:
        from fastmcp.server.dependencies import get_http_request

        req = get_http_request()
        scoped = req.scope.get("rm_env")            # set by EnvPathMiddleware on the scope
        if scoped in KNOWN_ENVS:
            return scoped
        q = (req.query_params.get("env") or "").strip().lower()
        if q:
            return q
        for seg in req.url.path.strip("/").split("/"):
            if seg in KNOWN_ENVS:
                return seg
    except Exception:
        pass
    return ""


def env_from_ctx(ctx) -> str:
    """Resolve the caller's environment, in priority order:

      1. the connector URL signal — ``/<env>/mcp`` path segment (or ``?env=``) — which
         needs no platform feature (see ``_env_from_request``);
      2. else the forwarded ``_meta.companyId`` → env (needs ``unique.app/auth/``
         forwarding enabled on the connector);
      3. else ``DEFAULT_ENV``.
    """
    e = _env_from_request()
    if e:
        return e
    company = _company_from_ctx(ctx)
    if company in COMPANY_ENV:
        return COMPANY_ENV[company]
    return DEFAULT_ENV


def content_id_for(env: str, map_key: str) -> str:
    """KB content id for (env, map_key) from content_id_map; "" when absent.

    map_key convention (see generate_sql.build_content_id_map_sql):
      • ``dashboard:<client_id>``  — the client's investment-proposal dashboard
      • ``cockpit``                — the shared cockpit page
      • ``doc:<client_id>:<file>`` — a catalogued document
    """
    if not env or not map_key:
        return ""
    try:
        row = query_one(
            "SELECT content_id FROM content_id_map WHERE env = %s AND map_key = %s",
            (env, map_key),
        )
    except Exception:
        # No content_id_map table / DB unreachable → degrade to filePath (return "").
        return ""
    return (row.get("content_id") if row else "") or ""


def remap_content_id(env: str, baked_content_id: str) -> str:
    """Correct a BAKED (seed-env) KB content id to the caller's env.

    Tools whose rows carry a fixed content id baked at seed time (e.g. ``list_documents``
    over the editable ``rm_documents`` table) can't key by filename, so they remap the id
    itself via the ``cid:<baked-id>`` rows in ``content_id_map`` (see
    generate_sql.build_content_id_map_sql). Returns the env-correct id, or the original id
    unchanged when there's no remap row (already env-correct, unknown, or a user-added id) —
    so a link is never broken, only upgraded."""
    if not env or not baked_content_id:
        return baked_content_id
    mapped = content_id_for(env, f"cid:{baked_content_id}")
    return mapped or baked_content_id
