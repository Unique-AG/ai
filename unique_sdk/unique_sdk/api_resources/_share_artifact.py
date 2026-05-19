from typing import (
    Literal,
    NotRequired,
    TypedDict,
    Unpack,
    cast,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


class ShareArtifact(APIResource["ShareArtifact"]):
    """Public API for the ``share-artifact`` workflow.

    The SI agent's ``share-artifact`` skill posts here once the user has
    chosen recipients and confirmed. The server:

    1. Copies the artifact into a project folder under ``/Projects``.
    2. Grants ``ScopeAccess`` (USER/GROUP × READ) to recipients.
    3. Links the source chat to the project via ``Chat.projectScopeId``.
    4. Emits an ``ARTIFACT_SHARED`` notification per recipient.

    The endpoint returns the resolved project scope, an action label
    (``created`` / ``reused`` / ``expanded`` / ``forked``) and a list of
    per-recipient notification ids so callers can surface a structured
    confirmation.
    """

    @classproperty
    def OBJECT_NAME(cls) -> Literal["share_artifact"]:
        return "share_artifact"

    class CreateParams(RequestOptions):
        sourceChatId: str
        contentId: str
        recipientUserIds: NotRequired[list[str]]
        recipientGroupIds: NotRequired[list[str]]
        projectName: str
        expandProject: NotRequired[bool | None]
        quickMessage: NotRequired[str | None]

    class RecipientNotification(TypedDict):
        userId: str
        viaGroupIds: list[str]
        notificationId: str | None

    class SkippedRecipient(TypedDict):
        userId: str
        reason: Literal["NOT_IN_COMPANY"]

    class Result(TypedDict):
        projectScopeId: str
        projectAction: Literal["created", "reused", "expanded", "forked"]
        projectPath: str
        notifications: list["ShareArtifact.RecipientNotification"]
        skippedRecipients: list["ShareArtifact.SkippedRecipient"]

    @classmethod
    def create(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["ShareArtifact.CreateParams"],
    ) -> "ShareArtifact.Result":
        """Share an artifact from a chat with a set of recipients.

        Calls ``POST /share-artifact``. The caller must own ``sourceChatId``
        and the artifact (``contentId``) must belong to that chat.
        """
        return cast(
            "ShareArtifact.Result",
            cls._static_request(
                "post",
                "/share-artifact",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def create_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["ShareArtifact.CreateParams"],
    ) -> "ShareArtifact.Result":
        """Async variant of :meth:`create`."""
        return cast(
            "ShareArtifact.Result",
            await cls._static_request_async(
                "post",
                "/share-artifact",
                user_id,
                company_id,
                params=params,
            ),
        )
