"""Per-request identity resolution for knowledge-base search.

Delegates to :func:`unique_mcp.get_unique_settings_async`, which resolves:

1. ``_meta`` auth (canonical keys + flat ``userId``/``companyId`` fallback)
2. Zitadel JWT claims
3. Zitadel ``/userinfo``
4. Environment ``UNIQUE_AUTH_*`` — only when there is no OAuth session

When an access token is present but identity cannot be resolved, the shared
injector raises instead of falling back to a fixed service user.
"""

from __future__ import annotations

from unique_mcp import get_unique_settings_async
from unique_toolkit.app.unique_settings import UniqueSettings


async def resolve_search_settings(
    settings: UniqueSettings | None = None,
) -> UniqueSettings:
    """Return settings whose auth is the logged-in user (or trusted ``_meta``).

    The ``settings`` argument is accepted for call-site compatibility with
    ``Depends(get_unique_settings)`` but is ignored — resolution always goes
    through :func:`get_unique_settings_async` so meta/JWT/userinfo handling
    cannot drift from the shared injector.

    Raises:
        ValueError: An OAuth token is present but neither JWT claims nor
            Zitadel userinfo yield both ``user_id`` and ``company_id``.
    """
    del settings  # identity comes from the shared async resolver only
    return await get_unique_settings_async()
