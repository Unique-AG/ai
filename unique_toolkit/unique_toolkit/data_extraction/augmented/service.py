from docxtpl.template import Any
from pydantic import BaseModel, create_model
from pydantic.alias_generators import to_pascal
from pydantic.fields import FieldInfo
from typing_extensions import override

from unique_toolkit.data_extraction.base import (
    BaseDataExtractionResult,
    BaseDataExtractor,
    ExtractionSchema,
)


def _build_augmented_model_for_field(
    field_name: str,
    field_type: Any | tuple[Any, FieldInfo],
    strict: bool = False,
    **extra_fields: Any | tuple[Any, FieldInfo],
) -> type[BaseModel]:
    camelized_field_name = to_pascal(field_name)

    fields = {
        **extra_fields,
        field_name: field_type,
    }

    return create_model(
        f"{camelized_field_name}Value",
        **fields,  # type: ignore
        __config__={"extra": "forbid" if strict else "ignore"},
    )


class AugmentedDataExtractionResult(BaseDataExtractionResult[ExtractionSchema]):
    """
    Result of data extraction from text using an augmented schema.
    """

    augmented_data: BaseModel


class AugmentedDataExtractor(BaseDataExtractor):
    def __init__(
        self,
        base_data_extractor: BaseDataExtractor,
        strict: bool = False,
        **extra_fields: Any | tuple[Any, FieldInfo],
    ):
        self._base_data_extractor = base_data_extractor
        self._extra_fields = extra_fields
        self._strict = strict

    def _prepare_schema(self, schema: type[ExtractionSchema]) -> type[BaseModel]:
        fields = {}

        for field_name, field_type in schema.model_fields.items():
            wrapped_field = _build_augmented_model_for_field(
                field_name,
                (field_type.annotation, field_type),
                strict=self._strict,
                **self._extra_fields,
            )
            fields[field_name] = wrapped_field

        return create_model(
            schema.__name__,
            **fields,
            __config__={"extra": "forbid" if self._strict else "ignore"},
            __doc__=schema.__doc__,
        )

    def _extract_output(
        self, llm_output: BaseModel, schema: type[ExtractionSchema]
    ) -> ExtractionSchema:
        output_data = {
            field_name: getattr(value, field_name) for field_name, value in llm_output
        }
        return schema.model_validate(output_data)

    @override
    async def extract_data_from_text(
        self, text: str, schema: type[ExtractionSchema]
    ) -> AugmentedDataExtractionResult[ExtractionSchema]:
        model_with_extra_fields = self._prepare_schema(schema)
        augmented_data = (
            await self._base_data_extractor.extract_data_from_text(
                text, model_with_extra_fields
            )
        ).data
        return AugmentedDataExtractionResult(
            data=self._extract_output(augmented_data, schema),
            augmented_data=augmented_data,
        )
