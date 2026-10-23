from pydantic import BaseModel, ConfigDict

type JsonValue = (
    bool | int | float | str | list[JsonValue] | dict[str, JsonValue] | None
)
type JsonObject = dict[str, JsonValue]


class KitModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SpaceKitError(Exception):
    """A failure the user can act on. The message says what to do."""


def as_object(*, value: object, what: str) -> JsonObject:
    if not isinstance(value, dict):
        msg = f"{what} is not a JSON object"
        raise SpaceKitError(msg)
    return value  # pyright: ignore[reportReturnType] -- JSON from the API is validated by shape at each use


def as_list(*, value: object, what: str) -> list[JsonValue]:
    if value is None:
        return []
    if not isinstance(value, list):
        msg = f"{what} is not a JSON list"
        raise SpaceKitError(msg)
    return value  # pyright: ignore[reportReturnType] -- JSON from the API is validated by shape at each use


def text_or_empty(*, value: JsonValue) -> str:
    return value if isinstance(value, str) else ""
