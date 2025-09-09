import logging
import warnings
from typing import TypeVar

import humps
from pydantic import BaseModel, ConfigDict, Field, create_model
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


ModelTypeA = TypeVar("ModelTypeA", bound=BaseModel)
ModelTypeB = TypeVar("ModelTypeB", bound=BaseModel)


def _name_intersection(
    model_type_a: type[ModelTypeA], model_type_b: type[ModelTypeB]
) -> set[str]:
    field_names_a = model_type_a.model_fields.keys()
    field_names_b = model_type_b.model_fields.keys()
    return field_names_a.intersection(field_names_b)


def create_union_model(
    model_type_a: type[ModelTypeA],
    model_type_b: type[ModelTypeB],
    model_name: str = "UnionModel",
    config_dict: ConfigDict = ConfigDict(),
) -> type[BaseModel]:
    """
    Creates a model that is the union of the two input models.
    Prefers fields from model_type_a.
    """

    if len(_name_intersection(model_type_a, model_type_b)) > 0:
        warnings.warn(
            f"The two input models have common field names: {_name_intersection(model_type_a, model_type_b)}"
        )

    fields = {}
    for name, field in model_type_b.model_fields.items():
        fields[name] = (field.annotation, field)
    for name, field in model_type_a.model_fields.items():
        fields[name] = (field.annotation, field)

    CombinedModel = create_model(model_name, __config__=config_dict, **fields)
    return CombinedModel


def create_intersection_model(
    model_type_a: type[ModelTypeA],
    model_type_b: type[ModelTypeB],
    model_name: str = "IntersectionModel",
    config_dict: ConfigDict = ConfigDict(),
) -> type[BaseModel]:
    """
    Creates a model that is the intersection of the two input models.
    Prefers fields from model_type_a.
    """

    if len(_name_intersection(model_type_a, model_type_b)) == 0:
        warnings.warn(
            f"The two input models have no common field names: {_name_intersection(model_type_a, model_type_b)}"
        )

    fields = {}
    field_names1 = model_type_a.model_fields.keys()
    field_names2 = model_type_b.model_fields.keys()
    common_field_names = field_names1.intersection(field_names2)

    for name, field in common_field_names.items():
        if name in field_names1.intersection(field_names2):
            fields[name] = (field.annotation, field)

    IntersectionModel = create_model(model_name, __config__=config_dict, **fields)
    return IntersectionModel


def create_complement_model(
    model_type_a: type[ModelTypeA],
    model_type_b: type[ModelTypeB],
    model_name: str = "ComplementModel",
    config_dict: ConfigDict = ConfigDict(),
) -> type[BaseModel]:
    """
    Creates a model that is the complement of the two input models
    i.e all fields from model_type_a that are not in model_type_b
    """

    if len(_name_intersection(model_type_a, model_type_b)) == 0:
        warnings.warn(
            f"The two input models have no common field names: {_name_intersection(model_type_a, model_type_b)}"
        )

    fields = {}
    field_names_a = model_type_a.model_fields.keys()
    field_names_b = model_type_b.model_fields.keys()
    complement_field_names = field_names_a.difference(field_names_b)

    for name in complement_field_names:
        fields[name] = (
            model_type_a.model_fields[name].annotation,
            model_type_a.model_fields[name],
        )

    ComplementModel = create_model(model_name, __config__=config_dict, **fields)

    return ComplementModel


if __name__ == "__main__":

    class ModelType1(BaseModel):
        field1: int = Field(default=1, description="Field 1")
        field2: str = Field(
            default="test",
            description="Field 2",
            json_schema_extra={"title": "Field 2"},
        )

    class ModelType2(BaseModel):
        field3: float
        field4: bool

    combined_model = create_union_model(ModelType1, ModelType2)

    print(combined_model.model_fields)
