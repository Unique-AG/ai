from typing import Any, Generic, Iterator, List, Mapping, Optional, TypeVar, cast

from typing_extensions import Self

from unique_sdk._unique_object import UniqueObject

T = TypeVar("T", bound=UniqueObject)


class ListObject(UniqueObject, Generic[T]):
    OBJECT_NAME = "list"
    data: List[T]
    has_more: bool
    url: str

    def _list(self, user_id: str, company_id: str, **params: Mapping[str, Any]) -> Self:
        url = self.get("url")
        if not isinstance(url, str):
            raise ValueError(
                'Cannot call .list on a list object without a string "url" property'
            )
        return cast(
            Self,
            self._request(
                "get",
                url,
                user_id=user_id,
                company_id=company_id,
                params=params,
            ),
        )

    def __getitem__(self, k: str) -> T:
        if isinstance(k, str):
            return super(ListObject, self).__getitem__(k)
        else:
            raise KeyError(
                "You tried to access the %s index, but ListObject types only "
                "support string keys. (HINT: List calls return an object with "
                "a 'data' (which is the data array). You likely want to call "
                ".data[%s])" % (repr(k), repr(k))
            )

    #  Pyright doesn't like this because ListObject inherits from UniqueObject inherits from Dict[str, Any]
    #  and so it wants the type of __iter__ to agree with __iter__ from Dict[str, Any]
    #  But we are iterating through "data", which is a List[T].
    def __iter__(self) -> Iterator[T]:  # pyright: ignore
        return getattr(self, "data", []).__iter__()

    def __len__(self) -> int:
        return getattr(self, "data", []).__len__()

    def __reversed__(self) -> Iterator[T]:  # pyright: ignore (see above)
        return getattr(self, "data", []).__reversed__()

    def auto_paging_iter(self) -> Iterator[T]:
        page = self

        while True:
            if (
                "ending_before" in self._retrieve_params
                and "starting_after" not in self._retrieve_params
            ):
                for item in reversed(page):
                    yield item
                page = page.previous_page()
            else:
                for item in page:
                    yield item
                page = page.next_page()

            if page.is_empty:
                break

    @classmethod
    def _empty_list(
        cls,
        user_id: Optional[str],
        company_id: Optional[str],
    ) -> Self:
        return cls.construct_from(
            {"data": []},
            user_id=user_id,
            company_id=company_id,
            last_response=None,
        )

    @property
    def is_empty(self) -> bool:
        return not self.data

    def next_page(self, **params: Mapping[str, Any]) -> Self:
        if not self.has_more:
            return self._empty_list(self.user_id, self.company_id)

        last_id = getattr(self.data[-1], "id")
        if not last_id:
            raise ValueError("Unexpected: element in .data of list object had no id")

        params_with_filters = self._retrieve_params.copy()
        params_with_filters.update({"starting_after": last_id})
        params_with_filters.update(params)

        result = self._list(**params_with_filters)
        return result

    def previous_page(self, **params: Mapping[str, Any]) -> Self:
        if not self.has_more:
            return self._empty_list(self.user_id, self.company_id)

        first_id = getattr(self.data[0], "id")
        if not first_id:
            raise ValueError("Unexpected: element in .data of list object had no id")

        params_with_filters = self._retrieve_params.copy()
        params_with_filters.update({"ending_before": first_id})
        params_with_filters.update(params)

        result = self._list(**params_with_filters)
        return result
