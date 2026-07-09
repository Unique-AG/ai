"""env_map.py — environment-aware KB content-id resolution.

The RM Agent MCPs are a SINGLE deployment shared across environments
(QA / UAT / prod-bnpp / prod-sales / local). KB content ids ("cont_…") are
env-specific — the same document has a different id in each environment's KB — so
the CRM tools must return the id for the *caller's* environment, not a baked one.

How the env is detected (see ``env_from_ctx``)
----------------------------------------------
1. **Connector URL query** — ``https://…/mcp?env=<env>``, set per environment on the
   connector's URL in admin. Works with NO platform feature (the MCP client preserves
   the URL's query string) — this is the primary signal.
2. **Forwarded company id** — ``_meta.companyId`` mapped via ``COMPANY_ENV``, IF the
   connector has the ``unique.app/auth/`` forwarding namespace enabled (node-chat:
   extended-mcp-server sets ``_meta.companyId`` / ``_meta.userId``).
3. Otherwise ``DEFAULT_ENV``.

The resolved env keys into the ``content_id_map(env, map_key, content_id)`` table
(seeded per env by ``generate_sql``).

Graceful degradation
---------------------
If auth-forwarding is off, the company is unknown, or the ``(env, map_key)`` has no
row, ``content_id_for`` returns ``""`` — callers then open by ``filePath`` (which is
env-agnostic) instead of a wrong/dead content id. So a missing map never breaks a
link; it just drops the "open by content id" upgrade.
"""

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
    """Explicit env from the connector URL query — `https://…/mcp?env=<env>`.

    This is the signal that works WITHOUT platform context-forwarding: set it once per
    environment on the connector's URL in admin. Read server-side from the HTTP request
    (the MCP client preserves the URL's query string on every call)."""
    try:
        from fastmcp.server.dependencies import get_http_request

        return (get_http_request().query_params.get("env") or "").strip().lower()
    except Exception:
        return ""


def env_from_ctx(ctx) -> str:
    """Resolve the caller's environment, in priority order:

      1. explicit ``?env=<env>`` on the connector URL — no forwarding required;
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
