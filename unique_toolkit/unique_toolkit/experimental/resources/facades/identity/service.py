"""The :class:`Identity` facade — users + groups in one place.

.. warning::

    **Experimental.** Lives under :mod:`unique_toolkit.experimental`. The
    public API, method names, and return shapes may change without notice
    and are not covered by the toolkit's normal stability guarantees.

:class:`Identity` is a *client*: it owns no CRUD logic of its own and simply
composes two resource services:

- :attr:`Identity.users` — an instance of
  :class:`~unique_toolkit.experimental.resources.users.Users`.
- :attr:`Identity.groups` — an instance of
  :class:`~unique_toolkit.experimental.resources.groups.Groups`.

Both sub-services share the same ``(user_id, company_id)`` pair, so
instantiating :class:`Identity` is equivalent to building both sub-services
manually.

**Acting user** — every API call is made on behalf of ``user_id``. That user
needs the usual directory permissions; most reads are open to any
authenticated user, group mutations require admin-equivalent rights.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.experimental.resources.groups.service import Groups
from unique_toolkit.experimental.resources.users.service import Users

if TYPE_CHECKING:
    from unique_toolkit.app.unique_settings import UniqueContext


class Identity:
    """Unified users + groups facade for a ``(user_id, company_id)`` context.

    .. warning::

        **Experimental.** Import path is
        :mod:`unique_toolkit.experimental.resources.facades.identity`. The API may
        change without notice.

    :class:`Identity` owns two sub-services:

    - :attr:`users` — an instance of
      :class:`~unique_toolkit.experimental.resources.users.Users`.
    - :attr:`groups` — an instance of
      :class:`~unique_toolkit.experimental.resources.groups.Groups`.

    ``Identity`` itself is stateless beyond the credentials it holds; the
    actual CRUD surface lives on the sub-services so callers write
    ``identity.users.list()`` or ``identity.groups.add_members(...)``.
    """

    def __init__(self, *, user_id: str, company_id: str) -> None:
        [user_id, company_id] = validate_required_values([user_id, company_id])
        self._user_id = user_id
        self._company_id = company_id
        self._users = Users(user_id=user_id, company_id=company_id)
        self._groups = Groups(user_id=user_id, company_id=company_id)

    @classmethod
    def from_context(cls, context: UniqueContext) -> Self:
        """Create from a :class:`UniqueContext` (preferred constructor)."""
        return cls(
            user_id=context.auth.get_confidential_user_id(),
            company_id=context.auth.get_confidential_company_id(),
        )

    @classmethod
    def from_settings(
        cls,
        settings: UniqueSettings | str | None = None,
    ) -> Self:
        """Create from :class:`UniqueSettings` — standalone convenience only.

        Mirrors :meth:`KnowledgeBaseService.from_settings` so callers can write
        ``Identity.from_settings()`` in standalone scripts:

        - ``settings=None`` auto-loads from ``unique.env`` via
          :meth:`UniqueSettings.from_env_auto_with_sdk_init`.
        - ``settings="my.env"`` loads from the given env file name.
        - ``settings=<UniqueSettings>`` uses the provided instance as-is.

        .. note::

            :class:`Identity` is **not** registered with
            :class:`UniqueServiceFactory`; experimental services are
            constructed directly so the experimental dependency stays visible
            at every call site.
        """
        if settings is None:
            settings = UniqueSettings.from_env_auto_with_sdk_init()
        elif isinstance(settings, str):
            settings = UniqueSettings.from_env_auto_with_sdk_init(filename=settings)

        return cls(
            user_id=settings.authcontext.get_confidential_user_id(),
            company_id=settings.authcontext.get_confidential_company_id(),
        )

    @property
    def users(self) -> Users:
        return self._users

    @property
    def groups(self) -> Groups:
        return self._groups
