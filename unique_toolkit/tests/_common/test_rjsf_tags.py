"""
Tests for the RJSF tags module.
"""

from typing import Annotated, Union

import pytest
from humps import camelize
from pydantic import BaseModel

from unique_toolkit._common.pydantic.rjsf_tags import (
    _NONE_TYPES,
    CustomWidgetName,
    RJSFMetaTag,
    _collect_metatags,
    _is_metadata_key,
    _is_pyd_model,
    _strip_annotated,
    _transform_obj,
    _unwrap_optional,
    _walk_annotated_chain,
    transform_ui_schema,
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
        assert tag.attrs == {"ui:widget": "range", "ui:disabled": False}

    def test_range_with_constraints(self):
        """Test range slider with constraints."""
        tag = RJSFMetaTag.NumberWidget.range(min=0, max=100, step=10, disabled=True)
        expected = {
            "ui:widget": "range",
            "ui:disabled": True,
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

    @pytest.mark.ai
    def test_hidden_basic(self):
        """Test basic hidden field creation."""
        tag = RJSFMetaTag.SpecialWidget.hidden()
        expected = {"ui:widget": "hidden"}
        assert tag.attrs == expected

    @pytest.mark.ai
    def test_object_collapsible_basic(self):
        """Test basic collapsible object field creation."""
        tag = RJSFMetaTag.ObjectWidget.collapsible()
        expected = {"ui:collapsible": True}
        assert tag.attrs == expected

    @pytest.mark.ai
    def test_object_collapsible_with_options(self):
        """Test collapsible object field with options."""
        tag = RJSFMetaTag.ObjectWidget.collapsible(
            title="Section",
            description="Collapsible section",
            help="Click to expand",
        )
        expected = {
            "ui:collapsible": True,
            "ui:title": "Section",
            "ui:description": "Collapsible section",
            "ui:help": "Click to expand",
        }
        assert tag.attrs == expected

    @pytest.mark.ai
    def test_custom_widget_basic(self):
        """Test basic custom widget creation with CustomWidgetName."""
        tag = RJSFMetaTag.CustomWidget.custom(CustomWidgetName.ICON_PICKER)
        expected = {"ui:widget": "iconPicker", "ui:disabled": False}
        assert tag.attrs == expected

    @pytest.mark.ai
    def test_custom_widget_with_options(self):
        """Test custom widget with additional options."""
        tag = RJSFMetaTag.CustomWidget.custom(
            CustomWidgetName.ICON_PICKER,
            title="Icon",
            description="Pick an icon",
            help="Select from available icons",
            disabled=True,
        )
        expected = {
            "ui:widget": "iconPicker",
            "ui:disabled": True,
            "ui:title": "Icon",
            "ui:description": "Pick an icon",
            "ui:help": "Select from available icons",
        }
        assert tag.attrs == expected

    def test_optional_basic(self):
        """Test basic Optional composer creation."""
        widget = RJSFMetaTag.StringWidget.textfield(placeholder="Enter text")
        optional = RJSFMetaTag.Optional(widget)

        expected = {
            "ui:disabled": False,
            "ui:readonly": False,
            "anyOf": [
                {
                    "ui:widget": "text",
                    "ui:placeholder": "Enter text",
                    "ui:disabled": False,
                    "ui:readonly": False,
                    "ui:autofocus": False,
                },
                {"type": "null"},
            ],
        }
        assert optional.attrs == expected

    def test_optional_with_metadata(self):
        """Test Optional composer with additional metadata."""
        widget = RJSFMetaTag.NumberWidget.updown(min=0, max=100)
        optional = RJSFMetaTag.Optional(
            widget,
            title="Optional Number",
            description="Enter a number between 0 and 100",
            help="This field is optional",
            readonly=True,
            optional_title="None (optional)",
        )

        expected = {
            "ui:title": "Optional Number",
            "ui:description": "Enter a number between 0 and 100",
            "ui:help": "This field is optional",
            "ui:disabled": False,
            "ui:readonly": True,
            "anyOf": [
                {
                    "ui:widget": "updown",
                    "ui:disabled": False,
                    "ui:readonly": False,
                    "ui:options": {"min": 0, "max": 100},
                },
                {"ui:title": "None (optional)", "type": "null"},
            ],
        }
        assert optional.attrs == expected

    def test_optional_filters_none_values(self):
        """Test that Optional composer filters out None values."""
        widget = RJSFMetaTag.StringWidget.textfield(placeholder="test")
        optional = RJSFMetaTag.Optional(
            widget, title="Test Field", optional_title="Optional Test Field"
        )

        expected = {
            "ui:title": "Test Field",
            "ui:disabled": False,
            "ui:readonly": False,
            "anyOf": [
                {
                    "ui:widget": "text",
                    "ui:placeholder": "test",
                    "ui:disabled": False,
                    "ui:readonly": False,
                    "ui:autofocus": False,
                },
                {"ui:title": "Optional Test Field", "type": "null"},
            ],
        }
        assert optional.attrs == expected

    def test_union_basic(self):
        """Test basic Union composer creation."""
        widget1 = RJSFMetaTag.StringWidget.textfield(placeholder="Text")
        widget2 = RJSFMetaTag.NumberWidget.updown(min=0)
        union = RJSFMetaTag.Union([widget1, widget2])

        expected = {
            "ui:disabled": False,
            "ui:readonly": False,
            "anyOf": [
                {
                    "ui:widget": "text",
                    "ui:placeholder": "Text",
                    "ui:disabled": False,
                    "ui:readonly": False,
                    "ui:autofocus": False,
                },
                {
                    "ui:widget": "updown",
                    "ui:disabled": False,
                    "ui:readonly": False,
                    "ui:options": {"min": 0},
                },
            ],
        }
        assert union.attrs == expected

    def test_union_with_metadata(self):
        """Test Union composer with additional metadata."""
        widget1 = RJSFMetaTag.StringWidget.textfield(placeholder="Name")
        widget2 = RJSFMetaTag.NumberWidget.updown(min=0, max=120)
        union = RJSFMetaTag.Union(
            [widget1, widget2],
            title="Name or Age",
            description="Enter either a name or age",
            help="Choose one option",
        )

        expected = {
            "ui:title": "Name or Age",
            "ui:description": "Enter either a name or age",
            "ui:help": "Choose one option",
            "ui:disabled": False,
            "ui:readonly": False,
            "anyOf": [
                {
                    "ui:widget": "text",
                    "ui:placeholder": "Name",
                    "ui:disabled": False,
                    "ui:readonly": False,
                    "ui:autofocus": False,
                },
                {
                    "ui:widget": "updown",
                    "ui:disabled": False,
                    "ui:readonly": False,
                    "ui:options": {"min": 0, "max": 120},
                },
            ],
        }
        assert union.attrs == expected

    def test_union_single_widget_error(self):
        """Test that Union composer raises error for single widget."""
        widget = RJSFMetaTag.StringWidget.textfield()

        with pytest.raises(ValueError, match="Union types require multiple widgets"):
            RJSFMetaTag.Union([widget])

    def test_union_empty_list(self):
        """Test that Union composer handles empty widget list."""
        union = RJSFMetaTag.Union([])
        expected = {"ui:disabled": False, "ui:readonly": False, "anyOf": []}
        assert union.attrs == expected

    def test_union_three_widgets(self):
        """Test Union composer with three widgets."""
        widget1 = RJSFMetaTag.StringWidget.textfield(placeholder="Text")
        widget2 = RJSFMetaTag.NumberWidget.updown(min=0)
        widget3 = RJSFMetaTag.BooleanWidget.checkbox()

        union = RJSFMetaTag.Union([widget1, widget2, widget3])

        expected = {
            "ui:disabled": False,
            "ui:readonly": False,
            "anyOf": [
                {
                    "ui:widget": "text",
                    "ui:placeholder": "Text",
                    "ui:disabled": False,
                    "ui:readonly": False,
                    "ui:autofocus": False,
                },
                {
                    "ui:widget": "updown",
                    "ui:disabled": False,
                    "ui:readonly": False,
                    "ui:options": {"min": 0},
                },
                {
                    "ui:widget": "checkbox",
                    "ui:disabled": False,
                },
            ],
        }
        assert union.attrs == expected

    def test_union_with_none_values(self):
        """Test that Union composer includes None values in metadata."""
        widget1 = RJSFMetaTag.StringWidget.textfield(placeholder="test")
        widget2 = RJSFMetaTag.NumberWidget.updown(min=0)
        union = RJSFMetaTag.Union([widget1, widget2], title="Test Union")

        expected = {
            "ui:title": "Test Union",
            "ui:disabled": False,
            "ui:readonly": False,
            "anyOf": [
                {
                    "ui:widget": "text",
                    "ui:placeholder": "test",
                    "ui:disabled": False,
                    "ui:readonly": False,
                    "ui:autofocus": False,
                },
                {
                    "ui:widget": "updown",
                    "ui:disabled": False,
                    "ui:readonly": False,
                    "ui:options": {"min": 0},
                },
            ],
        }
        assert union.attrs == expected


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
        assert schema == {"name": {}, "age": {}, "ui:order": ["name", "age"]}

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
            "ui:order": ["name", "age"],
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
                "ui:order": ["street", "city"],
            },
            "ui:order": ["name", "address"],
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
            "ui:order": ["items", "tags"],
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
            "ui:order": ["prefs", "settings"],
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
            "ui:order": ["value", "alt"],
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
            "ui:order": ["name", "optional_field"],
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
                    "ui:order": ["street", "zip_code"],
                },
            },
            "metadata": {
                "ui:title": "Metadata",
                "ui:expandable": True,
                "additionalProperties": {},
            },
            "ui:order": ["name", "age", "addresses", "metadata"],
        }
        assert schema == expected

    def test_no_key_transform_returns_snake_case(self):
        """Test that key_transform=None (default) returns snake_case keys."""

        class SnakeModel(BaseModel):
            tool_description: Annotated[str, RJSFMetaTag.StringWidget.textarea(rows=10)]
            is_enabled: bool

        schema = ui_schema_for_model(SnakeModel)
        assert "tool_description" in schema
        assert "is_enabled" in schema
        assert schema["ui:order"] == ["tool_description", "is_enabled"]

    def test_key_transform_camelize(self):
        """Test key_transform=camelize converts keys and ui:order values."""

        class CamelModel(BaseModel):
            tool_description: Annotated[str, RJSFMetaTag.StringWidget.textarea(rows=10)]
            is_enabled: bool

        schema = ui_schema_for_model(CamelModel, key_transform=camelize)
        assert "toolDescription" in schema
        assert "isEnabled" in schema
        assert "tool_description" not in schema
        assert schema["ui:order"] == ["toolDescription", "isEnabled"]
        assert schema["toolDescription"]["ui:widget"] == "textarea"

    def test_key_transform_matches_standalone_helper(self):
        """Test key_transform=camelize matches transform_ui_schema(raw, camelize)."""

        class EquivModel(BaseModel):
            field_one: str
            field_two: int

        raw = ui_schema_for_model(EquivModel)
        via_param = ui_schema_for_model(EquivModel, key_transform=camelize)
        via_helper = transform_ui_schema(raw, camelize)
        assert via_param == via_helper

    def test_key_transform_with_nested_model(self):
        """Test that key_transform camelizes nested model keys and ui:order."""

        class Inner(BaseModel):
            inner_field: str

        class Outer(BaseModel):
            outer_field: str
            nested: Inner

        schema = ui_schema_for_model(Outer, key_transform=camelize)
        assert schema["ui:order"] == ["outerField", "nested"]
        assert "outerField" in schema
        assert schema["nested"]["ui:order"] == ["innerField"]
        assert "innerField" in schema["nested"]

    def test_key_transform_custom_function(self):
        """Test that an arbitrary str→str function works as key_transform."""

        class MyModel(BaseModel):
            tool_description: str
            is_enabled: bool

        schema = ui_schema_for_model(MyModel, key_transform=str.upper)
        assert "TOOL_DESCRIPTION" in schema
        assert "IS_ENABLED" in schema
        assert schema["ui:order"] == ["TOOL_DESCRIPTION", "IS_ENABLED"]
        assert "ui:order" in schema  # metadata key preserved

    def test_value_transform_defaults_to_key_transform(self):
        """Test that value_transform defaults to key_transform when omitted."""

        class MyModel(BaseModel):
            field_one: str
            field_two: int

        only_key = ui_schema_for_model(MyModel, key_transform=camelize)
        both = ui_schema_for_model(
            MyModel, key_transform=camelize, value_transform=camelize
        )
        assert only_key == both

    def test_separate_value_transform(self):
        """Test that value_transform can differ from key_transform."""

        class MyModel(BaseModel):
            field_one: str
            field_two: int

        schema = ui_schema_for_model(
            MyModel, key_transform=camelize, value_transform=str.upper
        )
        assert "fieldOne" in schema
        assert "fieldTwo" in schema
        assert schema["ui:order"] == ["FIELD_ONE", "FIELD_TWO"]

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
        assert schema == {"ui:order": []}

    def test_model_with_private_fields(self):
        """Test ui_schema_for_model with private fields (should be ignored)."""

        class ModelWithPrivate(BaseModel):
            public_field: Annotated[str, RJSFMetaTag.StringWidget.textfield()]
            _private_field: Annotated[str, RJSFMetaTag.StringWidget.textfield()]

        schema = ui_schema_for_model(ModelWithPrivate)
        assert "public_field" in schema
        assert "_private_field" not in schema
        assert schema["ui:order"] == ["public_field"]


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

        # alt: Union[Annotated[Address, expandable], None] - metadata now preserved
        assert schema["alt"]["ui:expandable"] is True
        assert schema["alt"]["role"] == "home"
        assert "street" in schema["alt"]
        assert "zip" in schema["alt"]

        assert schema["ui:order"] == ["id", "name", "address", "tags", "prefs", "alt"]
        assert schema["address"]["ui:order"] == ["street", "zip"]

    def test_model_with_optional_composer(self):
        """Test ui_schema_for_model with Optional composer."""

        class OptionalModel(BaseModel):
            name: Annotated[
                str,
                RJSFMetaTag.Optional(
                    RJSFMetaTag.StringWidget.textfield(placeholder="Enter name"),
                    title="Name Field",
                    description="Enter your name",
                    optional_title="No name provided",
                ),
            ]
            age: Annotated[
                int,
                RJSFMetaTag.Optional(
                    RJSFMetaTag.NumberWidget.updown(min=0, max=120),
                    title="Age Field",
                    help="Enter your age",
                ),
            ]

        schema = ui_schema_for_model(OptionalModel)
        expected = {
            "name": {
                "ui:title": "Name Field",
                "ui:description": "Enter your name",
                "ui:disabled": False,
                "ui:readonly": False,
                "anyOf": [
                    {
                        "ui:widget": "text",
                        "ui:placeholder": "Enter name",
                        "ui:disabled": False,
                        "ui:readonly": False,
                        "ui:autofocus": False,
                    },
                    {"ui:title": "No name provided", "type": "null"},
                ],
            },
            "age": {
                "ui:title": "Age Field",
                "ui:help": "Enter your age",
                "ui:disabled": False,
                "ui:readonly": False,
                "anyOf": [
                    {
                        "ui:widget": "updown",
                        "ui:disabled": False,
                        "ui:readonly": False,
                        "ui:options": {"min": 0, "max": 120},
                    },
                    {"type": "null"},
                ],
            },
            "ui:order": ["name", "age"],
        }
        assert schema == expected

    def test_model_with_union_composer(self):
        """Test ui_schema_for_model with Union composer."""

        class UnionModel(BaseModel):
            value: Annotated[
                Union[str, int],
                RJSFMetaTag.Union(
                    [
                        RJSFMetaTag.StringWidget.textfield(placeholder="Enter text"),
                        RJSFMetaTag.NumberWidget.updown(min=0),
                    ],
                    title="Value Field",
                    description="Enter text or number",
                ),
            ]
            choice: Annotated[
                Union[str, int, bool],
                RJSFMetaTag.Union(
                    [
                        RJSFMetaTag.StringWidget.textfield(placeholder="Text"),
                        RJSFMetaTag.NumberWidget.updown(min=0, max=100),
                        RJSFMetaTag.BooleanWidget.checkbox(),
                    ],
                    title="Choice Field",
                    help="Select one option",
                ),
            ]

        schema = ui_schema_for_model(UnionModel)
        expected = {
            "value": {
                "ui:title": "Value Field",
                "ui:description": "Enter text or number",
                "ui:disabled": False,
                "ui:readonly": False,
                "anyOf": [
                    {
                        "ui:widget": "text",
                        "ui:placeholder": "Enter text",
                        "ui:disabled": False,
                        "ui:readonly": False,
                        "ui:autofocus": False,
                    },
                    {
                        "ui:widget": "updown",
                        "ui:disabled": False,
                        "ui:readonly": False,
                        "ui:options": {"min": 0},
                    },
                ],
            },
            "choice": {
                "ui:title": "Choice Field",
                "ui:help": "Select one option",
                "ui:disabled": False,
                "ui:readonly": False,
                "anyOf": [
                    {
                        "ui:widget": "text",
                        "ui:placeholder": "Text",
                        "ui:disabled": False,
                        "ui:readonly": False,
                        "ui:autofocus": False,
                    },
                    {
                        "ui:widget": "updown",
                        "ui:disabled": False,
                        "ui:readonly": False,
                        "ui:options": {"min": 0, "max": 100},
                    },
                    {
                        "ui:widget": "checkbox",
                        "ui:disabled": False,
                    },
                ],
            },
            "ui:order": ["value", "choice"],
        }
        assert schema == expected

    def test_model_with_nested_composer_usage(self):
        """Test ui_schema_for_model with nested composer usage."""

        class Address(BaseModel):
            street: Annotated[
                str, RJSFMetaTag.StringWidget.textfield(placeholder="Street address")
            ]
            city: Annotated[str, RJSFMetaTag.StringWidget.textfield(placeholder="City")]

        class Person(BaseModel):
            name: Annotated[
                str, RJSFMetaTag.StringWidget.textfield(placeholder="Full name")
            ]
            contact: Annotated[
                Union[str, Address],
                RJSFMetaTag.Union(
                    [
                        RJSFMetaTag.StringWidget.textfield(
                            placeholder="Email or phone"
                        ),
                        RJSFMetaTag.ObjectWidget.expandable(title="Address Details"),
                    ],
                    title="Contact Information",
                    description="Provide email/phone or address",
                ),
            ]
            optional_address: Annotated[
                Address,
                RJSFMetaTag.Optional(
                    RJSFMetaTag.ObjectWidget.expandable(title="Optional Address"),
                    title="Optional Address Field",
                    optional_title="No address provided",
                ),
            ]

        schema = ui_schema_for_model(Person)

        # Check that the schema has the expected structure
        assert "name" in schema
        assert "contact" in schema
        assert "optional_address" in schema

        # Check name field
        assert schema["name"]["ui:widget"] == "text"
        assert schema["name"]["ui:placeholder"] == "Full name"

        # Check contact field (Union with composer)
        assert "anyOf" in schema["contact"]
        assert len(schema["contact"]["anyOf"]) == 2
        assert schema["contact"]["ui:title"] == "Contact Information"
        assert schema["contact"]["ui:description"] == "Provide email/phone or address"

        # Check optional_address field (Optional with composer)
        assert "anyOf" in schema["optional_address"]
        assert len(schema["optional_address"]["anyOf"]) == 2
        assert schema["optional_address"]["ui:title"] == "Optional Address Field"
        assert schema["optional_address"]["anyOf"][1]["type"] == "null"
        assert (
            schema["optional_address"]["anyOf"][1]["ui:title"] == "No address provided"
        )

        assert schema["ui:order"] == ["name", "contact", "optional_address"]


class TestIsMetadataKey:
    """Test the _is_metadata_key helper."""

    def test_ui_prefixed_keys(self):
        """Test that ui:-prefixed keys are recognised as metadata."""
        assert _is_metadata_key("ui:widget") is True
        assert _is_metadata_key("ui:order") is True
        assert _is_metadata_key("ui:options") is True
        assert _is_metadata_key("ui:disabled") is True

    def test_dollar_prefixed_keys(self):
        """Test that $-prefixed keys are recognised as metadata."""
        assert _is_metadata_key("$ref") is True
        assert _is_metadata_key("$defs") is True

    def test_structural_keys(self):
        """Test that JSON Schema structural keys are recognised."""
        for key in ("anyOf", "oneOf", "allOf", "items", "additionalProperties", "type"):
            assert _is_metadata_key(key) is True, f"{key} should be metadata"

    def test_field_name_keys(self):
        """Test that regular field names are NOT metadata."""
        assert _is_metadata_key("tool_description") is False
        assert _is_metadata_key("isEnabled") is False
        assert _is_metadata_key("configuration") is False


class TestTransformObj:
    """Test the _transform_obj internal helper."""

    def test_transforms_field_name_keys(self):
        """Test that field-name keys are transformed via key_fn."""
        obj = {
            "display_name": {"ui:widget": "text"},
            "is_enabled": {"ui:widget": "hidden"},
        }
        result = _transform_obj(obj, camelize, camelize)
        assert "displayName" in result
        assert "isEnabled" in result

    def test_preserves_metadata_keys(self):
        """Test that ui:/$/structural keys are NOT transformed."""
        obj = {
            "ui:widget": "textarea",
            "ui:options": {"rows": 5},
            "ui:disabled": False,
            "$ref": "#/$defs/Foo",
            "anyOf": [{}, {}],
        }
        result = _transform_obj(obj, camelize, camelize)
        assert result == obj

    def test_transforms_ui_order_values_with_val_fn(self):
        """Test that ui:order values use val_fn, not key_fn."""
        obj = {"ui:order": ["display_name", "is_enabled"]}
        result = _transform_obj(obj, camelize, str.upper)
        assert result == {"ui:order": ["DISPLAY_NAME", "IS_ENABLED"]}

    def test_same_key_and_val_fn(self):
        """Test with the same function for keys and values."""
        obj = {"ui:order": ["display_name"], "display_name": {"ui:widget": "text"}}
        result = _transform_obj(obj, camelize, camelize)
        assert result == {
            "ui:order": ["displayName"],
            "displayName": {"ui:widget": "text"},
        }

    def test_recurses_into_nested_dicts(self):
        """Test recursive transformation in nested structures."""
        obj = {
            "ui:order": ["name", "configuration"],
            "configuration": {
                "ui:order": ["tool_description", "service_config"],
                "tool_description": {"ui:widget": "textarea"},
            },
        }
        result = _transform_obj(obj, camelize, camelize)
        assert result["ui:order"] == ["name", "configuration"]
        assert result["configuration"]["ui:order"] == [
            "toolDescription",
            "serviceConfig",
        ]
        assert "toolDescription" in result["configuration"]

    def test_handles_empty_ui_order(self):
        """Test that empty ui:order lists are preserved."""
        assert _transform_obj({"ui:order": []}, camelize, camelize) == {"ui:order": []}

    def test_handles_non_string_items_in_ui_order(self):
        """Test that non-string items in ui:order are passed through."""
        result = _transform_obj(
            {"ui:order": ["field_name", 42, None]}, camelize, camelize
        )
        assert result == {"ui:order": ["fieldName", 42, None]}

    def test_handles_lists_of_dicts(self):
        """Test recursion into lists containing dicts."""
        obj = [{"ui:order": ["field_one"]}, {"ui:order": ["field_two"]}]
        result = _transform_obj(obj, camelize, camelize)
        assert result == [{"ui:order": ["fieldOne"]}, {"ui:order": ["fieldTwo"]}]

    def test_passthrough_for_scalars(self):
        """Test that scalars are returned unchanged."""
        assert _transform_obj("hello", camelize, camelize) == "hello"
        assert _transform_obj(42, camelize, camelize) == 42
        assert _transform_obj(None, camelize, camelize) is None


class TestTransformUiSchema:
    """Test the public transform_ui_schema function."""

    def test_transforms_keys_and_ui_order_values(self):
        """Test that both dict keys and ui:order values are transformed."""
        raw = {
            "ui:order": ["display_name", "is_enabled", "configuration"],
            "display_name": {"ui:widget": "text"},
            "is_enabled": {"ui:widget": "hidden"},
            "configuration": {
                "ui:order": ["tool_description", "service_config"],
                "tool_description": {"ui:widget": "textarea"},
            },
        }
        result = transform_ui_schema(raw, camelize)
        assert result["ui:order"] == ["displayName", "isEnabled", "configuration"]
        assert "displayName" in result
        assert "isEnabled" in result
        assert result["configuration"]["ui:order"] == [
            "toolDescription",
            "serviceConfig",
        ]
        assert "toolDescription" in result["configuration"]

    def test_preserves_ui_colon_keys(self):
        """Test that ui: prefixed keys are not transformed."""
        raw = {
            "field_name": {
                "ui:widget": "textarea",
                "ui:options": {"rows": 5},
                "ui:disabled": False,
            }
        }
        result = transform_ui_schema(raw, camelize)
        assert result["fieldName"]["ui:widget"] == "textarea"
        assert result["fieldName"]["ui:options"] == {"rows": 5}
        assert result["fieldName"]["ui:disabled"] is False

    def test_empty_schema(self):
        """Test that an empty schema passes through."""
        assert transform_ui_schema({}, camelize) == {}

    def test_custom_transform_function(self):
        """Test with a non-camelize transform function."""
        raw = {
            "ui:order": ["field_a", "field_b"],
            "field_a": {"ui:widget": "text"},
            "field_b": {},
        }
        result = transform_ui_schema(raw, str.upper)
        assert result["ui:order"] == ["FIELD_A", "FIELD_B"]
        assert "FIELD_A" in result
        assert "FIELD_B" in result
        assert result["FIELD_A"]["ui:widget"] == "text"

    def test_separate_value_transform(self):
        """Test that value_transform can differ from key_transform."""
        raw = {
            "ui:order": ["field_a", "field_b"],
            "field_a": {"ui:widget": "text"},
            "field_b": {},
        }
        result = transform_ui_schema(raw, camelize, str.upper)
        assert "fieldA" in result
        assert "fieldB" in result
        assert result["ui:order"] == ["FIELD_A", "FIELD_B"]

    def test_value_transform_defaults_to_key_transform(self):
        """Test that omitting value_transform uses key_transform for both."""
        raw = {
            "ui:order": ["field_a"],
            "field_a": {"ui:widget": "text"},
        }
        only_key = transform_ui_schema(raw, camelize)
        both_same = transform_ui_schema(raw, camelize, camelize)
        assert only_key == both_same

    def test_end_to_end_with_ui_schema_for_model(self):
        """Test the full pipeline: model → ui_schema_for_model → transform_ui_schema."""

        class MyConfig(BaseModel):
            tool_description: Annotated[str, RJSFMetaTag.StringWidget.textarea(rows=10)]
            is_enabled: bool
            service_config_id: str

        raw = ui_schema_for_model(MyConfig)
        result = transform_ui_schema(raw, camelize)

        assert result["ui:order"] == ["toolDescription", "isEnabled", "serviceConfigId"]
        assert "toolDescription" in result
        assert result["toolDescription"]["ui:widget"] == "textarea"
        assert "isEnabled" in result
        assert "serviceConfigId" in result


@pytest.mark.ai
def test_AI_ui_schema_for_model__sub_agent_tool_config__produces_textarea_widgets() -> (
    None
):
    """
    Purpose: Verify SubAgentToolConfig RJSF annotations produce correct uiSchema.
    Why this matters: SubAgentToolConfig uses RJSFMetaTag for form fields; correct
        uiSchema ensures the tool config form renders properly in the UI.
    Setup summary: Call ui_schema_for_model on SubAgentToolConfig, assert
        RJSF-annotated string fields have ui:widget=textarea and ui:options.rows=5.
    """
    from unique_toolkit.agentic.tools.a2a.tool.config import SubAgentToolConfig

    # Act
    schema = ui_schema_for_model(SubAgentToolConfig)

    # Assert: RJSF-annotated fields from commit 16a303df "Add rjsf meta tags"
    textarea_fields = [
        "tool_description_for_system_prompt",
        "tool_description",
        "param_description_sub_agent_user_message",
        "tool_format_information_for_system_prompt",
        "tool_description_for_user_prompt",
        "tool_format_information_for_user_prompt",
    ]
    for field in textarea_fields:
        assert field in schema, f"Expected {field} in schema"
        assert schema[field]["ui:widget"] == "textarea"
        assert schema[field]["ui:options"] == {"rows": 5}

    # tool_input_json_schema is Annotated[str, meta] | None; metadata must be preserved
    assert "tool_input_json_schema" in schema
    assert schema["tool_input_json_schema"]["ui:widget"] == "textarea"
    assert schema["tool_input_json_schema"]["ui:options"] == {"rows": 5}


@pytest.mark.ai
def test_AI_field_named_items_is_transformed_by_key_transform() -> None:
    """
    Purpose: Verify that a field literally named 'items' or 'type' is still
        transformed by key_transform rather than being skipped as a structural key.
    Why this matters: _is_metadata_key treats 'items', 'type', etc. as structural
        keys. Without field_names awareness, a Pydantic field with such a name
        would not be transformed, while its ui:order entry would — causing a mismatch.
    Setup summary: Create a model with fields named 'items' and 'type', call
        ui_schema_for_model with camelize, assert both keys and ui:order are consistent.
    """

    class Edgy(BaseModel):
        items: Annotated[str, RJSFMetaTag.StringWidget.textfield()]
        type: Annotated[str, RJSFMetaTag.StringWidget.textfield()]
        normal_field: Annotated[str, RJSFMetaTag.StringWidget.textfield()]

    schema = ui_schema_for_model(Edgy, key_transform=camelize)

    assert "items" in schema, (
        "field 'items' must be transformed (camelize is identity for 'items')"
    )
    assert "type" in schema, (
        "field 'type' must be transformed (camelize is identity for 'type')"
    )
    assert "normalField" in schema, "field 'normal_field' must be camelized"

    assert schema["ui:order"] == ["items", "type", "normalField"]

    for key in ("items", "type", "normalField"):
        assert key in schema["ui:order"], f"{key} must appear in ui:order"
        assert key in schema, f"{key} must appear as schema key"
