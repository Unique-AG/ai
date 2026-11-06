import pytest
from pydantic import ValidationError

from package_name.contract.base import Model


class Item(Model):
    name: str


def test_model_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Item(name="a", extra="no")
