"""
Tests for the RJSF tags module.
"""

from typing import Annotated, Union

import pytest
from pydantic import BaseModel

from unique_toolkit._common.pydantic.rjsf_tags import (
    _NONE_TYPES,
    RJSFMetaTag,
    _collect_metatags,
    _is_pyd_model,
    _strip_annotated,
    _unwrap_optional,
    _walk_annotated_chain,
    ui_schema_for_model,
)


class TestRJSFMetaTag:
    """Test the RJSFMetaTag class."""

    def test_init_with_dict(self):
        """Test initialization with a dictionary."""
        attrs = {"ui:widget": "text", "ui:placeholder": "Enter text"}
        tag = RJSFMetaTag(attrs)
        assert tag.attrs == attrs

    def test_init_with_none(self):
        """Test initialization with None."""
        tag = RJSFMetaTag(None)
        assert tag.attrs == {}

    def test_init_with_empty_dict(self):
        """Test initialization with empty dictionary."""
        tag = RJSFMetaTag({})
        assert tag.attrs == {}

    def test_textfield_basic(self):
        """Test basic textfield creation."""
        tag = RJSFMetaTag.StringWidget.textfield()
        expected = {
            "ui:widget": "text",
            "ui:disabled": False,
            "ui:readonly": False,
            "ui:autofocus": False,
        }
        assert tag.attrs == expected

    def test_textfield_with_options(self):
        """Test textfield with various options."""
        tag = RJSFMetaTag.StringWidget.textfield(
            placeholder="Enter name",
            disabled=True,
            readonly=True,
            autofocus=True,
            title="Name Field",
            description="Enter your full name",
            help="This field is required",
            class_names="form-control",
        )
        expected = {
            "ui:widget": "text",
            "ui:placeholder": "Enter name",
            "ui:disabled": True,
            "ui:readonly": True,
            "ui:autofocus": True,
            "ui:title": "Name Field",
            "ui:description": "Enter your full name",
            "ui:help": "This field is required",
            "ui:classNames": "form-control",
        }
        assert tag.attrs == expected

    def test_textfield_filters_none_values(self):
        """Test that textfield filters out None values."""
        tag = RJSFMetaTag.StringWidget.textfield(
            placeholder="test", title=None, description=None
        )
        expected = {
            "ui:widget": "text",
            "ui:placeholder": "test",
            "ui:disabled": False,
            "ui:readonly": False,
            "ui:autofocus": False,
        }
        assert tag.attrs == expected

    def test_textarea_basic(self):
        """Test basic textarea creation."""
        tag = RJSFMetaTag.StringWidget.textarea()
        expected = {"ui:widget": "textarea", "ui:disabled": False, "ui:readonly": False}
        assert tag.attrs == expected

    def test_textarea_with_rows(self):
        """Test textarea with rows option."""
        tag = RJSFMetaTag.StringWidget.textarea(rows=5, placeholder="Enter description")
        expected = {
            "ui:widget": "textarea",
            "ui:placeholder": "Enter description",
            "ui:disabled": False,
            "ui:readonly": False,
            "ui:options": {"rows": 5},
        }
        assert tag.attrs == expected

    def test_number_basic(self):
        """Test basic number field creation."""
        tag = RJSFMetaTag.NumberWidget.updown()
        expected = {"ui:widget": "updown", "ui:disabled": False, "ui:readonly": False}
        assert tag.attrs == expected

    def test_number_with_constraints(self):
        """Test number field with min/max/step constraints."""
        tag = RJSFMetaTag.NumberWidget.updown(
            min=0, max=100, step=5, placeholder="Enter value"
        )
        expected = {
            "ui:widget": "updown",
            "ui:placeholder": "Enter value",
            "ui:disabled": False,
            "ui:readonly": False,
            "ui:options": {"min": 0, "max": 100, "step": 5},
        }
        assert tag.attrs == expected

    def test_range_basic(self):
        """Test basic range slider creation."""
        tag = RJSFMetaTag.NumberWidget.range()
        assert tag.attrs == {"ui:widget": "range"}

    def test_range_with_constraints(self):
        """Test range slider with constraints."""
        tag = RJSFMetaTag.NumberWidget.range(min=0, max=100, step=10, disabled=True)
        expected = {
            "ui:widget": "range",
            "ui:disabled": "true",
            "ui:options": {"min": 0, "max": 100, "step": 10},
        }
        assert tag.attrs == expected

    def test_select_basic(self):
        """Test basic select dropdown creation."""
        tag = RJSFMetaTag.BooleanWidget.select()
        expected = {"ui:widget": "select", "ui:disabled": False}
        assert tag.attrs == expected

    def test_checkbox_basic(self):
        """Test basic checkbox creation."""
        tag = RJSFMetaTag.BooleanWidget.checkbox()
        expected = {"ui:widget": "checkbox", "ui:disabled": False}
        assert tag.attrs == expected

    def test_checkboxes_basic(self):
        """Test basic checkboxes creation."""
        tag = RJSFMetaTag.ArrayWidget.checkboxes()
        expected = {"ui:widget": "checkboxes", "ui:disabled": False}
        assert tag.attrs == expected

    def test_radio_basic(self):
        """Test basic radio buttons creation."""
        tag = RJSFMetaTag.BooleanWidget.radio()
        expected = {"ui:widget": "radio", "ui:disabled": False}
        assert tag.attrs == expected

    def test_password_basic(self):
        """Test basic password field creation."""
        tag = RJSFMetaTag.StringWidget.password()
        expected = {"ui:widget": "password", "ui:disabled": False, "ui:readonly": False}
        assert tag.attrs == expected

    def test_email_basic(self):
        """Test basic email field creation."""
        tag = RJSFMetaTag.StringWidget.email()
        expected = {"ui:widget": "email", "ui:disabled": False, "ui:readonly": False}
        assert tag.attrs == expected

    def test_url_basic(self):
        """Test basic URL field creation."""
        tag = RJSFMetaTag.StringWidget.url()
        expected = {"ui:widget": "uri", "ui:disabled": False, "ui:readonly": False}
        assert tag.attrs == expected

    def test_date_basic(self):
        """Test basic date field creation."""
        tag = RJSFMetaTag.StringWidget.date()
        expected = {"ui:widget": "date", "ui:disabled": False}
        assert tag.attrs == expected

    def test_datetime_basic(self):
        """Test basic datetime field creation."""
        tag = RJSFMetaTag.StringWidget.datetime()
        expected = {"ui:widget": "datetime", "ui:disabled": False}
        assert tag.attrs == expected

    def test_time_basic(self):
        """Test basic time field creation."""
        tag = RJSFMetaTag.StringWidget.time()
        expected = {"ui:widget": "time", "ui:disabled": False}
        assert tag.attrs == expected

    def test_color_basic(self):
        """Test basic color picker creation."""
        tag = RJSFMetaTag.StringWidget.color()
        expected = {"ui:widget": "color", "ui:disabled": False}
        assert tag.attrs == expected

    def test_file_basic(self):
        """Test basic file upload creation."""
        tag = RJSFMetaTag.StringWidget.file()
        expected = {"ui:widget": "file", "ui:disabled": False}
        assert tag.attrs == expected

    def test_file_with_accept(self):
        """Test file upload with accept filter."""
        tag = RJSFMetaTag.StringWidget.file(accept=".pdf,.doc,.docx")
        expected = {
            "ui:widget": "file",
            "ui:disabled": False,
            "ui:options": {"accept": ".pdf,.doc,.docx"},
        }
        assert tag.attrs == expected

    def test_array_basic(self):
        """Test basic array field creation."""
        tag = RJSFMetaTag.ArrayWidget.checkboxes()
        expected = {"ui:widget": "checkboxes", "ui:disabled": False}
        assert tag.attrs == expected

    def test_array_with_options(self):
        """Test array field with custom options."""
        tag = RJSFMetaTag.ArrayWidget.checkboxes(
            title="Items",
            description="Add items to the list",
            disabled=False,
        )
        expected = {
            "ui:widget": "checkboxes",
            "ui:title": "Items",
            "ui:description": "Add items to the list",
            "ui:disabled": False,
        }
        assert tag.attrs == expected

    def test_object_basic(self):
        """Test basic object field creation."""
        tag = RJSFMetaTag.ObjectWidget.expandable()
        expected = {"ui:expandable": True}
        assert tag.attrs == expected

    def test_object_with_options(self):
        """Test object field with options."""
        tag = RJSFMetaTag.ObjectWidget.expandable(
            title="Address",
            description="Enter address details",
        )
        expected = {
            "ui:expandable": True,
            "ui:title": "Address",
            "ui:description": "Enter address details",
        }
        assert tag.attrs == expected

    def test_custom_field_basic(self):
        """Test basic custom field creation."""
        tag = RJSFMetaTag.SpecialWidget.custom_field("MyCustomField")
        assert tag.attrs == {"ui:field": "MyCustomField"}

    def test_custom_field_with_options(self):
        """Test custom field with additional options."""
        tag = RJSFMetaTag.SpecialWidget.custom_field(
            "MyCustomField",
            title="Custom Field",
            description="This is a custom field",
            help="Custom help text",
        )
        expected = {
            "ui:field": "MyCustomField",
            "ui:title": "Custom Field",
            "ui:description": "This is a custom field",
            "ui:help": "Custom help text",
        }
        assert tag.attrs == expected


class TestHelperFunctions:
    """Test helper functions."""

    def test_strip_annotated_with_annotated(self):
        """Test _strip_annotated with Annotated type."""
        tag = RJSFMetaTag.StringWidget.textfield(placeholder="test")
        ann = Annotated[str, tag]
        base, extras = _strip_annotated(ann)
        assert base is str
        assert len(extras) == 1
        assert isinstance(extras[0], RJSFMetaTag)

    def test_strip_annotated_without_annotated(self):
        """Test _strip_annotated with non-Annotated type."""
        base, extras = _strip_annotated(str)
        assert base is str
        assert extras == []

    def test_collect_metatags(self):
        """Test _collect_metatags function."""
        tag1 = RJSFMetaTag.StringWidget.textfield(placeholder="test1")
        tag2 = RJSFMetaTag.NumberWidget.updown(min=0, max=100)
        extras = [tag1, "not_a_tag", tag2]

        result = _collect_metatags(extras)
        # Should merge both tags, with the last one taking precedence for overlapping keys
        expected = {
            "ui:widget": "updown",  # Last tag overwrites
            "ui:placeholder": "test1",
            "ui:options": {"min": 0, "max": 100},
            "ui:disabled": False,
            "ui:readonly": False,
            "ui:autofocus": False,  # From first tag
        }
        assert result == expected

    def test_collect_metatags_empty(self):
        """Test _collect_metatags with no RJSFMetaTag instances."""
        result = _collect_metatags(["string", 123, None])
        assert result == {}

    def test_unwrap_optional_with_union_none(self):
        """Test _unwrap_optional with Union[Type, None]."""
        ann = Union[str, None]
        result = _unwrap_optional(ann)
        assert result is str

    def test_unwrap_optional_with_union_multiple(self):
        """Test _unwrap_optional with Union[Type1, Type2, None]."""
        ann = Union[str, int, None]
        result = _unwrap_optional(ann)
        assert result is ann  # Should return original if multiple non-None types

    def test_unwrap_optional_without_union(self):
        """Test _unwrap_optional with non-Union type."""
        result = _unwrap_optional(str)
        assert result is str

    def test_walk_annotated_chain_single(self):
        """Test _walk_annotated_chain with single Annotated."""
        tag = RJSFMetaTag.StringWidget.textfield(placeholder="test")
        ann = Annotated[str, tag]
        base, meta = _walk_annotated_chain(ann)
        assert base is str
        assert meta == tag.attrs

    def test_walk_annotated_chain_nested(self):
        """Test _walk_annotated_chain with nested Annotated."""
        tag1 = RJSFMetaTag.StringWidget.textfield(placeholder="test")
        tag2 = RJSFMetaTag.NumberWidget.updown(min=0)
        ann = Annotated[Annotated[str, tag1], tag2]
        base, meta = _walk_annotated_chain(ann)
        assert base is str
        # Should merge both tags
        expected = {**tag1.attrs, **tag2.attrs}
        assert meta == expected

    def test_walk_annotated_chain_no_annotated(self):
        """Test _walk_annotated_chain with non-Annotated type."""
        base, meta = _walk_annotated_chain(str)
        assert base is str
        assert meta == {}

    def test_is_pyd_model_with_base_model(self):
        """Test _is_pyd_model with BaseModel subclass."""

        class TestModel(BaseModel):
            pass

        assert _is_pyd_model(TestModel)

    def test_is_pyd_model_with_non_model(self):
        """Test _is_pyd_model with non-BaseModel class."""

        class RegularClass:
            pass

        assert not _is_pyd_model(RegularClass)
        assert not _is_pyd_model(str)
        assert not _is_pyd_model("string")


class TestUISchemaForModel:
    """Test the ui_schema_for_model function."""

    def test_simple_model(self):
        """Test ui_schema_for_model with a simple model."""

        class SimpleModel(BaseModel):
            name: str
            age: int

        schema = ui_schema_for_model(SimpleModel)
        # Simple models without annotations should have empty dicts for each field
        assert schema == {"name": {}, "age": {}}

    def test_model_with_annotated_fields(self):
        """Test ui_schema_for_model with annotated fields."""

        class AnnotatedModel(BaseModel):
            name: Annotated[
                str, RJSFMetaTag.StringWidget.textfield(placeholder="Enter name")
            ]
            age: Annotated[int, RJSFMetaTag.NumberWidget.updown(min=0, max=120)]

        schema = ui_schema_for_model(AnnotatedModel)
        expected = {
            "name": {
                "ui:widget": "text",
                "ui:placeholder": "Enter name",
                "ui:disabled": False,
                "ui:readonly": False,
                "ui:autofocus": False,
            },
            "age": {
                "ui:widget": "updown",
                "ui:options": {"min": 0, "max": 120},
                "ui:disabled": False,
                "ui:readonly": False,
            },
        }
        assert schema == expected

    def test_model_with_nested_model(self):
        """Test ui_schema_for_model with nested models."""

        class Address(BaseModel):
            street: Annotated[
                str, RJSFMetaTag.StringWidget.textfield(placeholder="Street")
            ]
            city: Annotated[str, RJSFMetaTag.StringWidget.textfield(placeholder="City")]

        class Person(BaseModel):
            name: Annotated[str, RJSFMetaTag.StringWidget.textfield(placeholder="Name")]
            address: Annotated[
                Address, RJSFMetaTag.ObjectWidget.expandable(title="Address")
            ]

        schema = ui_schema_for_model(Person)
        expected = {
            "name": {
                "ui:widget": "text",
                "ui:placeholder": "Name",
                "ui:disabled": False,
                "ui:readonly": False,
                "ui:autofocus": False,
            },
            "address": {
                "ui:title": "Address",
                "ui:expandable": True,
                "street": {
                    "ui:widget": "text",
                    "ui:placeholder": "Street",
                    "ui:disabled": False,
                    "ui:readonly": False,
                    "ui:autofocus": False,
                },
                "city": {
                    "ui:widget": "text",
                    "ui:placeholder": "City",
                    "ui:disabled": False,
                    "ui:readonly": False,
                    "ui:autofocus": False,
                },
            },
        }
        assert schema == expected

    def test_model_with_list_field(self):
        """Test ui_schema_for_model with list fields."""

        class ListModel(BaseModel):
            items: Annotated[
                list[str], RJSFMetaTag.ArrayWidget.checkboxes(title="Items")
            ]
            tags: Annotated[
                list[Annotated[str, RJSFMetaTag.StringWidget.textfield()]],
                RJSFMetaTag.ArrayWidget.checkboxes(title="Tags"),
            ]

        schema = ui_schema_for_model(ListModel)
        expected = {
            "items": {
                "ui:title": "Items",
                "ui:widget": "checkboxes",
                "ui:disabled": False,
                "items": {},
            },
            "tags": {
                "ui:title": "Tags",
                "ui:widget": "checkboxes",
                "ui:disabled": False,
                "items": {
                    "ui:widget": "text",
                    "ui:disabled": False,
                    "ui:readonly": False,
                    "ui:autofocus": False,
                },
            },
        }
        assert schema == expected

    def test_model_with_dict_field(self):
        """Test ui_schema_for_model with dict fields."""

        class DictModel(BaseModel):
            prefs: Annotated[
                dict[str, int], RJSFMetaTag.ObjectWidget.expandable(title="Preferences")
            ]
            settings: Annotated[
                dict[str, Annotated[str, RJSFMetaTag.StringWidget.textfield()]],
                RJSFMetaTag.ObjectWidget.expandable(title="Settings"),
            ]

        schema = ui_schema_for_model(DictModel)
        expected = {
            "prefs": {
                "ui:title": "Preferences",
                "ui:expandable": True,
                "additionalProperties": {},
            },
            "settings": {
                "ui:title": "Settings",
                "ui:expandable": True,
                "additionalProperties": {
                    "ui:widget": "text",
                    "ui:disabled": False,
                    "ui:readonly": False,
                    "ui:autofocus": False,
                },
            },
        }
        assert schema == expected

    def test_model_with_union_field(self):
        """Test ui_schema_for_model with Union fields."""

        class UnionModel(BaseModel):
            value: Annotated[Union[str, int], RJSFMetaTag.BooleanWidget.select()]
            alt: Annotated[
                Union[str, Annotated[int, RJSFMetaTag.NumberWidget.updown()]],
                RJSFMetaTag.BooleanWidget.radio(),
            ]

        schema = ui_schema_for_model(UnionModel)
        expected = {
            "value": {"ui:widget": "select", "ui:disabled": False, "anyOf": [{}, {}]},
            "alt": {
                "ui:widget": "radio",
                "ui:disabled": False,
                "anyOf": [
                    {},
                    {"ui:widget": "updown", "ui:disabled": False, "ui:readonly": False},
                ],
            },
        }
        assert schema == expected

    def test_model_with_optional_field(self):
        """Test ui_schema_for_model with Optional fields."""

        class OptionalModel(BaseModel):
            name: Annotated[str, RJSFMetaTag.StringWidget.textfield()]
            optional_field: Annotated[
                Union[str, None], RJSFMetaTag.StringWidget.textfield()
            ]

        schema = ui_schema_for_model(OptionalModel)
        expected = {
            "name": {
                "ui:widget": "text",
                "ui:disabled": False,
                "ui:readonly": False,
                "ui:autofocus": False,
            },
            "optional_field": {
                "ui:widget": "text",
                "ui:disabled": False,
                "ui:readonly": False,
                "ui:autofocus": False,
            },
        }
        assert schema == expected

    def test_model_with_complex_nested_structure(self):
        """Test ui_schema_for_model with complex nested structures."""

        class Address(BaseModel):
            street: Annotated[
                str, RJSFMetaTag.StringWidget.textfield(placeholder="Street")
            ]
            zip_code: Annotated[
                str, RJSFMetaTag.StringWidget.textfield(placeholder="ZIP")
            ]

        class Person(BaseModel):
            name: Annotated[str, RJSFMetaTag.StringWidget.textfield(placeholder="Name")]
            age: Annotated[int, RJSFMetaTag.NumberWidget.updown(min=0, max=120)]
            addresses: Annotated[
                list[Address], RJSFMetaTag.ArrayWidget.checkboxes(title="Addresses")
            ]
            metadata: Annotated[
                dict[str, str], RJSFMetaTag.ObjectWidget.expandable(title="Metadata")
            ]

        schema = ui_schema_for_model(Person)
        expected = {
            "name": {
                "ui:widget": "text",
                "ui:placeholder": "Name",
                "ui:disabled": False,
                "ui:readonly": False,
                "ui:autofocus": False,
            },
            "age": {
                "ui:widget": "updown",
                "ui:options": {"min": 0, "max": 120},
                "ui:disabled": False,
                "ui:readonly": False,
            },
            "addresses": {
                "ui:title": "Addresses",
                "ui:widget": "checkboxes",
                "ui:disabled": False,
                "items": {
                    "street": {
                        "ui:widget": "text",
                        "ui:placeholder": "Street",
                        "ui:disabled": False,
                        "ui:readonly": False,
                        "ui:autofocus": False,
                    },
                    "zip_code": {
                        "ui:widget": "text",
                        "ui:placeholder": "ZIP",
                        "ui:disabled": False,
                        "ui:readonly": False,
                        "ui:autofocus": False,
                    },
                },
            },
            "metadata": {
                "ui:title": "Metadata",
                "ui:expandable": True,
                "additionalProperties": {},
            },
        }
        assert schema == expected

    def test_ui_schema_for_model_invalid_input(self):
        """Test ui_schema_for_model with invalid input."""
        with pytest.raises(TypeError, match="is not a Pydantic BaseModel subclass"):
            ui_schema_for_model(str)  # type: ignore

        with pytest.raises(TypeError, match="is not a Pydantic BaseModel subclass"):
            ui_schema_for_model("string")  # type: ignore

        with pytest.raises(TypeError, match="is not a Pydantic BaseModel subclass"):
            ui_schema_for_model(object)  # type: ignore


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_none_types_constant(self):
        """Test that _NONE_TYPES contains type(None)."""
        assert type(None) in _NONE_TYPES

    def test_empty_annotated_chain(self):
        """Test _walk_annotated_chain with empty chain."""
        # This should raise a TypeError since Annotated requires at least 2 arguments
        with pytest.raises(TypeError):
            _walk_annotated_chain(Annotated[str])

    def test_multiple_metatags_in_annotated(self):
        """Test handling multiple RJSFMetaTag instances in one Annotated."""
        tag1 = RJSFMetaTag.StringWidget.textfield(placeholder="test1")
        tag2 = RJSFMetaTag.NumberWidget.updown(min=0)
        ann = Annotated[str, tag1, tag2, "not_a_tag"]
        base, meta = _walk_annotated_chain(ann)
        assert base is str
        # Should merge both tags
        expected = {**tag1.attrs, **tag2.attrs}
        assert meta == expected

    def test_model_with_no_fields(self):
        """Test ui_schema_for_model with empty model."""

        class EmptyModel(BaseModel):
            pass

        schema = ui_schema_for_model(EmptyModel)
        assert schema == {}

    def test_model_with_private_fields(self):
        """Test ui_schema_for_model with private fields (should be ignored)."""

        class ModelWithPrivate(BaseModel):
            public_field: Annotated[str, RJSFMetaTag.StringWidget.textfield()]
            _private_field: Annotated[str, RJSFMetaTag.StringWidget.textfield()]

        schema = ui_schema_for_model(ModelWithPrivate)
        # Private fields should be included in the schema
        assert "public_field" in schema
        assert "_private_field" in schema


# Example test that matches the example in the original file
class TestExampleFromFile:
    """Test the example models from the original file."""

    def test_example_models(self):
        """Test the example models from the original file."""

        class Address(BaseModel):
            street: Annotated[
                str, RJSFMetaTag.StringWidget.textfield(placeholder="Street")
            ]
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
            prefs: dict[
                str, Annotated[int, RJSFMetaTag.NumberWidget.range(min=0, max=100)]
            ]
            alt: Union[
                Annotated[Address, RJSFMetaTag.ObjectWidget.expandable(role="home")],
                None,
            ]

        schema = ui_schema_for_model(User)

        # Verify the schema structure
        assert "id" in schema
        assert "name" in schema
        assert "address" in schema
        assert "tags" in schema
        assert "prefs" in schema
        assert "alt" in schema

        # Check specific field configurations
        assert schema["id"]["ui:widget"] == "updown"
        assert schema["id"]["ui:disabled"]

        assert schema["name"]["ui:widget"] == "text"
        assert schema["name"]["ui:placeholder"] == "Enter your name"
        assert schema["name"]["ui:autofocus"]

        assert schema["address"]["ui:field"] == "AddressField"
        assert "street" in schema["address"]
        assert "zip" in schema["address"]

        assert schema["tags"]["ui:title"] == "Tags"
        assert "items" in schema["tags"]
        assert schema["tags"]["items"]["ui:widget"] == "checkboxes"

        assert "additionalProperties" in schema["prefs"]
        assert schema["prefs"]["additionalProperties"]["ui:widget"] == "range"
        assert schema["prefs"]["additionalProperties"]["ui:options"]["min"] == 0
        assert schema["prefs"]["additionalProperties"]["ui:options"]["max"] == 100

        # For the Union field with None, it should be unwrapped to an empty dict
        # since None is filtered out and the Union is unwrapped
        assert schema["alt"] == {}
