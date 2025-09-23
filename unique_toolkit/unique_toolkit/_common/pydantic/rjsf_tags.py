"""
React JSON Schema Form (RJSF) metadata tags for Pydantic models.

This module provides utilities for generating React JSON Schema Form uiSchemas
from Pydantic models using type annotations. It allows developers to specify
UI metadata directly in their Pydantic model definitions using Annotated types.

Key components:
- RJSFMetaTag: Factory class for creating RJSF metadata tags
- ui_schema_for_model(): Main function to generate uiSchema from Pydantic models
- Helper functions for processing type annotations and metadata
"""

from __future__ import annotations

from typing import Annotated, Any, Union, get_args, get_origin

from pydantic import BaseModel
from typing_extensions import get_type_hints


# --------- Base Metadata carrier ----------
class RJSFMetaTag:
    def __init__(self, attrs: dict[str, Any] | None = None):
        """Initialize with either a dict or keyword arguments.

        Args:
            attrs: Dictionary of attributes (preferred)
            **kwargs: Keyword arguments (for backward compatibility)
        """
        self.attrs = attrs if attrs is not None else {}

    # --------- Widget Type Subclasses ----------

    class BooleanWidget:
        """Widgets for boolean fields: radio, select, checkbox (default)."""

        @classmethod
        def radio(
            cls,
            *,
            disabled: bool = False,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a radio button group for boolean values."""
            attrs = {
                "ui:widget": "radio",
                "ui:disabled": disabled,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def select(
            cls,
            *,
            disabled: bool = False,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a select dropdown for boolean values."""
            attrs = {
                "ui:widget": "select",
                "ui:disabled": disabled,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def checkbox(
            cls,
            *,
            disabled: bool = False,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a checkbox for boolean values (default widget)."""
            attrs = {
                "ui:widget": "checkbox",
                "ui:disabled": disabled,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

    class StringWidget:
        """Widgets for string fields: text, textarea, password, color, email, url, date, datetime, time, file."""

        @classmethod
        def textfield(
            cls,
            *,
            placeholder: str | None = None,
            disabled: bool = False,
            readonly: bool = False,
            autofocus: bool = False,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            class_names: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a text field (default for strings)."""
            attrs: dict[str, Any] = {
                "ui:widget": "text",
                "ui:placeholder": placeholder,
                "ui:disabled": disabled,
                "ui:readonly": readonly,
                "ui:autofocus": autofocus,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                "ui:classNames": class_names,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def textarea(
            cls,
            *,
            placeholder: str | None = None,
            disabled: bool = False,
            readonly: bool = False,
            rows: int | None = None,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a textarea field."""
            attrs: dict[str, Any] = {
                "ui:widget": "textarea",
                "ui:placeholder": placeholder,
                "ui:disabled": disabled,
                "ui:readonly": readonly,
                "ui:options": {"rows": rows} if rows else None,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def password(
            cls,
            *,
            placeholder: str | None = None,
            disabled: bool = False,
            readonly: bool = False,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a password field."""
            attrs = {
                "ui:widget": "password",
                "ui:placeholder": placeholder,
                "ui:disabled": disabled,
                "ui:readonly": readonly,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def color(
            cls,
            *,
            disabled: bool = False,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a color picker field."""
            attrs = {
                "ui:widget": "color",
                "ui:disabled": disabled,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def email(
            cls,
            *,
            placeholder: str | None = None,
            disabled: bool = False,
            readonly: bool = False,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create an email field."""
            attrs = {
                "ui:widget": "email",
                "ui:placeholder": placeholder,
                "ui:disabled": disabled,
                "ui:readonly": readonly,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def url(
            cls,
            *,
            placeholder: str | None = None,
            disabled: bool = False,
            readonly: bool = False,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a URL field."""
            attrs = {
                "ui:widget": "uri",
                "ui:placeholder": placeholder,
                "ui:disabled": disabled,
                "ui:readonly": readonly,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def date(
            cls,
            *,
            disabled: bool = False,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a date field."""
            attrs = {
                "ui:widget": "date",
                "ui:disabled": disabled,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def datetime(
            cls,
            *,
            disabled: bool = False,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a datetime field."""
            attrs = {
                "ui:widget": "datetime",
                "ui:disabled": disabled,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def time(
            cls,
            *,
            disabled: bool = False,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a time field."""
            attrs = {
                "ui:widget": "time",
                "ui:disabled": disabled,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def file(
            cls,
            *,
            disabled: bool = False,
            accept: str | None = None,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a file upload field."""
            attrs = {
                "ui:widget": "file",
                "ui:disabled": disabled,
                "ui:options": {"accept": accept} if accept else None,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

    class NumberWidget:
        """Widgets for number and integer fields: updown, range, radio (with enum)."""

        @classmethod
        def updown(
            cls,
            *,
            placeholder: str | None = None,
            disabled: bool = False,
            readonly: bool = False,
            min: int | float | None = None,
            max: int | float | None = None,
            step: int | float | None = None,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a number updown field (default for numbers)."""
            options: dict[str, Any] = {
                "min": min,
                "max": max,
                "step": step,
            }
            options = {k: v for k, v in options.items() if v is not None}

            attrs = {
                "ui:widget": "updown",
                "ui:placeholder": placeholder,
                "ui:disabled": disabled,
                "ui:readonly": readonly,
                "ui:options": options if options else None,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def range(
            cls,
            *,
            disabled: bool = False,
            min: int | float | None = None,
            max: int | float | None = None,
            step: int | float | None = None,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a range slider field."""
            options: dict[str, Any] = {
                "min": min,
                "max": max,
                "step": step,
            }
            options = {k: v for k, v in options.items() if v is not None}

            attrs = {
                "ui:widget": "range",
                "ui:disabled": str(disabled).lower() if disabled else None,
                "ui:options": options if options else None,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def radio(
            cls,
            *,
            disabled: bool = False,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create radio buttons for number enum values."""
            attrs = {
                "ui:widget": "radio",
                "ui:disabled": disabled,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

    class ArrayWidget:
        """Widgets for array fields: checkboxes, select, radio."""

        @classmethod
        def checkboxes(
            cls,
            *,
            disabled: bool = False,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create checkboxes for array values."""
            attrs = {
                "ui:widget": "checkboxes",
                "ui:disabled": disabled,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def select(
            cls,
            *,
            disabled: bool = False,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a select dropdown for array values."""
            attrs = {
                "ui:widget": "select",
                "ui:disabled": disabled,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def radio(
            cls,
            *,
            disabled: bool = False,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create radio buttons for array values."""
            attrs = {
                "ui:widget": "radio",
                "ui:disabled": disabled,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

    class ObjectWidget:
        """Widgets for object fields: expandable, collapsible."""

        @classmethod
        def expandable(
            cls,
            *,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create an expandable object field."""
            attrs = {
                "ui:expandable": True,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def collapsible(
            cls,
            *,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a collapsible object field."""
            attrs = {
                "ui:collapsible": True,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

    class SpecialWidget:
        """Special widgets: hidden, custom fields."""

        @classmethod
        def hidden(
            cls,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a hidden field."""
            attrs = {
                "ui:widget": "hidden",
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})

        @classmethod
        def custom_field(
            cls,
            field_name: str,
            *,
            title: str | None = None,
            description: str | None = None,
            help: str | None = None,
            **kwargs: Any,
        ) -> RJSFMetaTag:
            """Create a custom field."""
            attrs = {
                "ui:field": field_name,
                "ui:title": title,
                "ui:description": description,
                "ui:help": help,
                **kwargs,
            }
            return RJSFMetaTag({k: v for k, v in attrs.items() if v is not None})


# --------- Helpers ----------
_NONE_TYPES = {type(None)}
"""
Set containing the None type for use in Union type processing.
Used by _unwrap_optional to identify and filter out None types from Union annotations.
"""


def _strip_annotated(ann: Any) -> tuple[Any, list[Any]]:
    """
    Extract the base type and metadata from an Annotated type.

    This function unwraps a single level of Annotated[...] to get the base type
    and any metadata annotations. For non-Annotated types, it returns the
    type unchanged with an empty metadata list.

    Args:
        ann: The type annotation to process (may be Annotated or not)

    Returns:
        A tuple of (base_type, metadata_list) where:
        - base_type: The underlying type (e.g., str, int, list[str])
        - metadata_list: List of metadata objects (RJSFMetaTag instances, etc.)
    """
    if get_origin(ann) is Annotated:
        base, *extras = get_args(ann)
        return base, extras
    return ann, []


def _collect_metatags(extras: list[Any]) -> dict[str, Any]:
    """
    Extract and merge RJSF metadata from a list of annotation extras.

    This function processes a list of metadata objects (from Annotated[...])
    and extracts all RJSFMetaTag instances, merging their attributes into
    a single dictionary. Later tags override earlier ones for duplicate keys.

    Args:
        extras: List of metadata objects from Annotated type annotations

    Returns:
        A dictionary containing all merged RJSF metadata attributes
    """
    out: dict[str, Any] = {}
    for x in extras:
        if isinstance(x, RJSFMetaTag):
            out.update(x.attrs)
    return out


def _unwrap_optional(ann: Any) -> Any:
    """
    Unwrap Optional[Type] or Union[Type, None] to just Type.

    This function simplifies Union types that contain None by removing the
    None option and returning the non-None type. If there are multiple
    non-None types, the original Union is returned unchanged.

    Args:
        ann: The type annotation to process

    Returns:
        The unwrapped type if it was Optional/Union with None, otherwise
        the original type unchanged
    """
    if get_origin(ann) is Union:
        args = [a for a in get_args(ann) if a not in _NONE_TYPES]
        if len(args) == 1:
            return args[0]
    return ann


def _walk_annotated_chain(ann: Any) -> tuple[Any, dict[str, Any]]:
    """
    Recursively unwrap nested Annotated types and collect all metadata.

    This function processes deeply nested Annotated[...] types by walking
    through the chain and collecting all RJSF metadata from each level.
    It handles cases like Annotated[Annotated[Type, meta1], meta2].

    Args:
        ann: The type annotation to process (may be deeply nested)

    Returns:
        A tuple of (final_base_type, merged_metadata_dict) where:
        - final_base_type: The innermost non-Annotated type
        - merged_metadata_dict: All RJSF metadata merged from all levels
    """
    merged: dict[str, Any] = {}
    cur = ann
    while get_origin(cur) is Annotated:
        base, extras = _strip_annotated(cur)
        merged.update(_collect_metatags(extras))
        cur = base
    return cur, merged


def _is_pyd_model(t: Any) -> bool:
    try:
        return isinstance(t, type) and issubclass(t, BaseModel)
    except TypeError:
        return False


# --------- Build RJSF-style uiSchema dict from a model *type* ----------
def ui_schema_for_model(model_cls: type[BaseModel]) -> dict[str, Any]:
    """
    Generate a React JSON Schema Form (RJSF) uiSchema from a Pydantic model.

    This function analyzes a Pydantic BaseModel class and extracts all RJSF metadata
    from field annotations to create a complete uiSchema dictionary. The resulting
    schema can be used directly with React JSON Schema Form components.

    The function handles:
    - Simple fields with RJSF metadata annotations
    - Nested Pydantic models (inline expansion)
    - List/array fields with item-level metadata
    - Dictionary fields with value-type metadata
    - Union types with multiple branches (anyOf)
    - Optional fields (Union with None)

    Args:
        model_cls: A Pydantic BaseModel subclass to analyze

    Returns:
        A dictionary representing the RJSF uiSchema with the structure:
        {
            "field_name": {
                "ui:widget": "text",
                "ui:placeholder": "Enter value",
                # ... other RJSF metadata
                # For nested models, fields are inlined:
                "nested_field": { ... },
                # For arrays:
                "items": { ... },
                # For dicts:
                "additionalProperties": { ... },
                # For unions:
                "anyOf": [{ ... }, { ... }]
            }
        }

    Raises:
        TypeError: If model_cls is not a Pydantic BaseModel subclass
    """
    if not _is_pyd_model(model_cls):
        raise TypeError(f"{model_cls!r} is not a Pydantic BaseModel subclass")

    hints = get_type_hints(model_cls, include_extras=True)
    ui: dict[str, Any] = {}

    for fname, ann in hints.items():
        node: dict[str, Any] = {}

        base, meta = _walk_annotated_chain(ann)
        base = _unwrap_optional(base)
        # Start with field-level metadata (flat dict)
        if meta:
            node.update(meta)

        origin = get_origin(base)

        # Nested model -> inline children
        if _is_pyd_model(base):
            node.update(ui_schema_for_model(base))

        # Array-like -> items
        elif origin in (list, set, tuple):
            (item_type, *_) = get_args(base) or (Any,)
            item_base, item_meta = _walk_annotated_chain(item_type)
            item_base = _unwrap_optional(item_base)

            item_node: dict[str, Any] = {}
            if item_meta:
                item_node.update(item_meta)
            if _is_pyd_model(item_base):
                item_node.update(ui_schema_for_model(item_base))
            node["items"] = item_node

        # Dict -> additionalProperties (value side)
        elif origin is dict:
            key_t, val_t = get_args(base) or (Any, Any)
            val_base, val_meta = _walk_annotated_chain(val_t)
            val_base = _unwrap_optional(val_base)

            val_node: dict[str, Any] = {}
            if val_meta:
                val_node.update(val_meta)
            if _is_pyd_model(val_base):
                val_node.update(ui_schema_for_model(val_base))
            node["additionalProperties"] = val_node

        # Union -> anyOf branches
        elif origin is Union:
            branches = []
            for alt in get_args(base):
                if alt in _NONE_TYPES:
                    continue
                alt_b, alt_meta = _walk_annotated_chain(alt)
                branch: dict[str, Any] = {}
                if alt_meta:
                    branch.update(alt_meta)
                if _is_pyd_model(alt_b):
                    branch.update(ui_schema_for_model(alt_b))
                branches.append(branch)
            if branches:
                node["anyOf"] = branches

        # Scalars: node already has metadata if any

        ui[fname] = node

    return ui


# --------- Example ---------
if __name__ == "__main__":

    class Address(BaseModel):
        street: Annotated[str, RJSFMetaTag.StringWidget.textfield(placeholder="Street")]
        zip: Annotated[str, RJSFMetaTag.NumberWidget.updown(placeholder="12345")]

    class User(BaseModel):
        id: Annotated[int, RJSFMetaTag.NumberWidget.updown(disabled=True)]
        name: Annotated[
            str,
            RJSFMetaTag.StringWidget.textfield(
                placeholder="Enter your name", autofocus=True
            ),
        ]
        address: Annotated[
            Address, RJSFMetaTag.SpecialWidget.custom_field("AddressField")
        ]
        tags: Annotated[
            list[Annotated[str, RJSFMetaTag.ArrayWidget.checkboxes()]],
            RJSFMetaTag.ArrayWidget.checkboxes(title="Tags"),
        ]
        prefs: dict[str, Annotated[int, RJSFMetaTag.NumberWidget.range(min=0, max=100)]]
        alt: Union[
            Annotated[Address, RJSFMetaTag.ObjectWidget.expandable(role="home")], None
        ]

    import json

    print(json.dumps(ui_schema_for_model(User), indent=7))
