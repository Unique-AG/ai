from typing import Any

from unique_sdk.api_resources._elicitation import Elicitation

from .._base import BaseManager, DomainObject


class ElicitationObject(DomainObject):
    """A pending elicitation (human-in-the-loop request) with respond capability."""

    async def respond(self, **params: Any) -> Any:
        return await Elicitation.respond_to_elicitation_async(
            self._user_id, self._company_id, **params
        )


class ElicitationManager(BaseManager):
    """Create and manage elicitations (human-in-the-loop approvals / form inputs)."""

    async def create(self, **params: Any) -> ElicitationObject:
        result = await Elicitation.create_elicitation_async(
            self._user_id, self._company_id, **params
        )
        return ElicitationObject(self._user_id, self._company_id, result)

    async def get_pending(self) -> Any:
        return await Elicitation.get_pending_elicitations_async(
            self._user_id, self._company_id
        )

    async def get(self, elicitation_id: str) -> ElicitationObject:
        result = await Elicitation.get_elicitation_async(
            self._user_id, self._company_id, elicitation_id
        )
        return ElicitationObject(self._user_id, self._company_id, result)

    async def respond(self, **params: Any) -> Any:
        return await Elicitation.respond_to_elicitation_async(
            self._user_id, self._company_id, **params
        )
