import logging

import humps
from pydantic import ConfigDict
from pydantic.fields import ComputedFieldInfo, FieldInfo

logger = logging.getLogger(__name__)


def field_title_generator(
    title: str,
    info: FieldInfo | ComputedFieldInfo,
) -> str:
    return humps.decamelize(title).replace("_", " ").title()


def model_title_generator(model: type) -> str:
    return humps.decamelize(model.__name__).replace("_", " ").title()


def get_configuration_dict(**kwargs) -> ConfigDict:
    return ConfigDict(
        # alias_generator=to_camel,
        field_title_generator=field_title_generator,
        model_title_generator=model_title_generator,
        # populate_by_name=True,
        # protected_namespaces=(),
        **kwargs,
    )
