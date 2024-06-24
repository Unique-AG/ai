from copy import deepcopy
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Self,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

import unique_sdk
from unique_sdk import _util
from unique_sdk._unique_response import UniqueResponse


class UniqueObject(Dict[str, Any]):
    _retrieve_params: Dict[str, Any]

    user_id: Optional[str]
    company_id: Optional[str]

    def __init__(
        self,
        user_id: Optional[str],
        company_id: Optional[str],
        id: Optional[str] = None,
        last_response: Optional[UniqueResponse] = None,
        **params: Any,
    ):
        super(UniqueObject, self).__init__()

        self.user_id = user_id
        self.company_id = company_id

        self._unsaved_values: Set[str] = set()
        self._transient_values: Set[str] = set()
        self._last_response = last_response
        self._retrieve_params = params
        self._previous = None

        if id:
            self["id"] = id

    @property
    def last_response(self) -> Optional[UniqueResponse]:
        return self._last_response

    # UniqueObject inherits from `dict` which has an update method, and this doesn't quite match
    # the full signature of the update method in MutableMapping. But we ignore.
    def update(  # pyright: ignore
        self, update_dict: Mapping[str, Any]
    ) -> None:
        for k in update_dict:
            self._unsaved_values.add(k)

        return super(UniqueObject, self).update(update_dict)

    if not TYPE_CHECKING:

        def __setattr__(self, k, v):
            if k[0] == "_" or k in self.__dict__:
                return super(UniqueObject, self).__setattr__(k, v)

            self[k] = v
            return None

        def __getattr__(self, k):
            if k[0] == "_":
                raise AttributeError(k)

            try:
                return self[k]
            except KeyError as err:
                raise AttributeError(*err.args)

        def __delattr__(self, k):
            if k[0] == "_" or k in self.__dict__:
                return super(UniqueObject, self).__delattr__(k)
            else:
                del self[k]

    def __setitem__(self, k: str, v: Any) -> None:
        if v == "":
            raise ValueError(
                "You cannot set %s to an empty string on this object. "
                "The empty string is treated specially in our requests. "
                "If you'd like to delete the property using the save() method on this object, you may set %s.%s=None. "
                "Alternatively, you can pass %s='' to delete the property when using a resource method such as modify()."
                % (k, str(self), k, k)
            )

        # Allows for unpickling in Python 3.x
        if not hasattr(self, "_unsaved_values"):
            self._unsaved_values = set()

        self._unsaved_values.add(k)

        super(UniqueObject, self).__setitem__(k, v)

    def __getitem__(self, k: str) -> Any:
        try:
            return super(UniqueObject, self).__getitem__(k)
        except KeyError as err:
            if k in self._transient_values:
                raise KeyError(
                    "%r.  HINT: The %r attribute was set in the past."
                    "It was then wiped when refreshing the object with "
                    "the result returned by Unique's API, probably as a "
                    "result of a save().  The attributes currently "
                    "available on this object are: %s"
                    % (k, k, ", ".join(list(self.keys())))
                )
            else:
                raise err

    def __delitem__(self, k: str) -> None:
        super(UniqueObject, self).__delitem__(k)

        # Allows for unpickling in Python 3.x
        if hasattr(self, "_unsaved_values") and k in self._unsaved_values:
            self._unsaved_values.remove(k)

    # Custom unpickling method that uses `update` to update the dictionary
    # without calling __setitem__, which would fail if any value is an empty
    # string
    def __setstate__(self, state: Dict[str, Any]) -> None:
        self.update(state)

    # Custom pickling method to ensure the instance is pickled as a custom
    # class and not as a dict, otherwise __setstate__ would not be called when
    # unpickling.
    def __reduce__(self) -> Tuple[Any, ...]:
        reduce_value = (
            type(self),  # callable
            (  # args
                self.user_id,
                self.company_id,
                self.get("id", None),
            ),
            dict(self),  # state
        )
        return reduce_value

    @classmethod
    def construct_from(
        cls,
        values: Dict[str, Any],
        user_id: Optional[str],
        company_id: Optional[str],
        last_response: Optional[UniqueResponse] = None,
    ) -> Self:
        instance = cls(
            user_id=user_id,
            company_id=company_id,
            id=values.get("id"),
            last_response=last_response,
        )

        instance.refresh_from(
            values,
            user_id=user_id,
            company_id=company_id,
            last_response=last_response,
        )

        return instance

    def refresh_from(
        self,
        values: Dict[str, Any],
        user_id: Optional[str],
        company_id: Optional[str],
        partial: Optional[bool] = False,
        last_response: Optional[UniqueResponse] = None,
    ) -> None:
        self._last_response = last_response or getattr(values, "_last_response", None)

        if partial:
            self._unsaved_values = self._unsaved_values - set(values)
        else:
            removed = set(self.keys()) - set(values)
            self._transient_values = self._transient_values | removed
            self._unsaved_values = set()
            self.clear()

        self._transient_values = self._transient_values - set(values)

        for k, v in values.items():
            inner_class = self._get_inner_class_type(k)
            is_dict = self._get_inner_class_is_beneath_dict(k)
            if is_dict:
                obj = {
                    k: None
                    if v is None
                    else cast(
                        UniqueObject,
                        _util.convert_to_unique_object(
                            v,
                            user_id,
                            company_id,
                            None,
                            inner_class,
                        ),
                    )
                    for k, v in v.items()
                }
            else:
                obj = cast(
                    Union[UniqueObject, List[UniqueObject]],
                    _util.convert_to_unique_object(
                        v,
                        user_id,
                        company_id,
                        None,
                        inner_class,
                    ),
                )
            super(UniqueObject, self).__setitem__(k, obj)

        self._previous = values

    def request(
        self,
        method: Literal["get", "post", "patch", "delete"],
        url: str,
        user_id: Optional[str],
        company_id: Optional[str],
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> "UniqueObject":
        return UniqueObject._request(
            self,
            method,
            url,
            user_id,
            company_id,
            headers=headers,
            params=params,
        )

    # The `method_` and `url_` arguments are suffixed with an underscore to
    # avoid conflicting with actual request parameters in `params`.
    def _request(
        self,
        method_: Literal["get", "post", "patch", "delete"],
        url_: str,
        user_id: Optional[str],
        company_id: Optional[str],
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
    ) -> "UniqueObject":
        params = None if params is None else dict(params)

        user_id = user_id or self.user_id
        company_id = company_id or self.company_id

        params = params or self._retrieve_params

        requestor = unique_sdk.APIRequestor(user_id=user_id, company_id=company_id)

        response = requestor.request(method_, url_, params, headers)

        return _util.convert_to_unique_object(response, user_id, company_id, params)

    # This class overrides __setitem__ to throw exceptions on inputs that it
    # doesn't like. This can cause problems when we try to copy an object
    # wholesale because some data that's returned from the API may not be valid
    # if it was set to be set manually. Here we override the class' copy
    # arguments so that we can bypass these possible exceptions on __setitem__.
    def __copy__(self) -> "UniqueObject":
        copied = UniqueObject(
            self.user_id,
            self.company_id,
            self.get("id"),
        )

        copied._retrieve_params = self._retrieve_params

        for k, v in self.items():
            # Call parent's __setitem__ to avoid checks that we've added in the
            # overridden version that can throw exceptions.
            super(UniqueObject, copied).__setitem__(k, v)

        return copied

    # This class overrides __setitem__ to throw exceptions on inputs that it
    # doesn't like. This can cause problems when we try to copy an object
    # wholesale because some data that's returned from the API may not be valid
    # if it was set to be set manually. Here we override the class' copy
    # arguments so that we can bypass these possible exceptions on __setitem__.
    def __deepcopy__(self, memo: Dict[int, Any]) -> "UniqueObject":
        copied = self.__copy__()
        memo[id(self)] = copied

        for k, v in self.items():
            # Call parent's __setitem__ to avoid checks that we've added in the
            # overridden version that can throw exceptions.
            super(UniqueObject, copied).__setitem__(k, deepcopy(v, memo))

        return copied

    _inner_class_types: ClassVar[Dict[str, Type["UniqueObject"]]] = {}
    _inner_class_dicts: ClassVar[List[str]] = []

    def _get_inner_class_type(self, field_name: str) -> Optional[Type["UniqueObject"]]:
        return self._inner_class_types.get(field_name)

    def _get_inner_class_is_beneath_dict(self, field_name: str):
        return field_name in self._inner_class_dicts
