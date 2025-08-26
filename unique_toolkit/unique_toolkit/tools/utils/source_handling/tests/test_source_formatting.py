import pytest

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.tools.utils.source_handling.schema import SourceFormatConfig
from unique_toolkit.tools.utils.source_handling.source_formatting import (
    _format_page_range,
    format_chunk,
)


@pytest.fixture
def default_config():
    return SourceFormatConfig()


@pytest.fixture
def xml_style_config_without_page_number():
    return SourceFormatConfig(
        source_template="<source${index}>${document}${info}${text}</source${index}>",
        sections={
            "document": "<|document|>{}<|/document|>\n",
            "info": "<|info|>{}<|/info|>\n",
        },
    )


@pytest.fixture
def xml_style_config_with_page_number():
    return SourceFormatConfig(
        source_template="<source${index}>${document}${page}${info}${text}</source${index}>",
        sections={
            "document": "<|document|>{}<|/document|>\n",
            "info": "<|info|>{}<|/info|>\n",
            "page": "<|page|>{}<|/page|>\n",
        },
    )


@pytest.fixture
def xml_style_config_with_metadata():
    return SourceFormatConfig(
        source_template="<source${index}>${document}${date}${text}</source${index}>",
        sections={
            "document": "<|document|>{}<|/document|>\n",
            "date": "<|DateFromMetaData|>{}<|/DateFromMetaData|>\n",
        },
    )


@pytest.fixture
def json_style_config():
    return SourceFormatConfig(
        source_template="{'source_number': ${index}, 'content': '${document}${page}${info}${text}'}",
        sections={
            "document": "<|document|>{}<|/document|>\n",
            "info": "<|info|>{}<|/info|>\n",
            "page": "<|page|>{}<|/page|>\n",
        },
    )


def test_format_page_range():
    # Test same start and end page
    chunk = ContentChunk(id="1", order=1, text="test", start_page=1, end_page=1)
    assert _format_page_range(chunk) == "1"

    # Test page range
    chunk = ContentChunk(id="1", order=1, text="test", start_page=1, end_page=3)
    assert _format_page_range(chunk) == "1 - 3"

    # Test invalid pages
    chunk = ContentChunk(id="1", order=1, text="test", start_page=0, end_page=0)
    assert _format_page_range(chunk) == ""


def test_json_style_formatting(json_style_config):
    chunk = ContentChunk(
        id="1",
        order=1,
        text="<|document|>Doc1<|/document|>\n<|info|>Important<|/info|>\nContent text",
        start_page=1,
        end_page=2,
    )

    formatted = format_chunk(1, chunk, json_style_config)
    expected = "{'source_number': 1, 'content': '<|document|>Doc1<|/document|>\n<|page|>1 - 2<|/page|>\n<|info|>Important<|/info|>\nContent text'}"
    assert formatted == expected


def test_metadata_handling(xml_style_config_with_metadata):
    # Test with metadata that matches a section name
    chunk = ContentChunk(
        id="1",
        order=1,
        text="<|document|>Doc1<|/document|>\nContent text",
        metadata={
            "key": "metadata-key",
            "mimeType": "text/plain",
            "date": "12.03.2025",
        },  # type: ignore
    )

    formatted = format_chunk(1, chunk, xml_style_config_with_metadata)
    expected = "<source1><|document|>Doc1<|/document|>\n<|DateFromMetaData|>12.03.2025<|/DateFromMetaData|>\nContent text</source1>"
    assert formatted == expected

    # Test with metadata that doesn't match a section name
    chunk = ContentChunk(
        id="1",
        order=1,
        text="<|document|>Doc1<|/document|>\nContent text",
        metadata={
            "key": "metadata-key",
            "mimeType": "text/plain",
            "unrelated_key": "Some value",
        },  # type: ignore
    )

    formatted = format_chunk(1, chunk, xml_style_config_with_metadata)
    expected = "<source1><|document|>Doc1<|/document|>\nContent text</source1>"
    assert formatted == expected

    # Test with minimal metadata
    chunk = ContentChunk(
        id="1",
        order=1,
        text="<|document|>Doc1<|/document|>\nContent text",
        metadata={"key": "metadata-key", "mimeType": "text/plain"},  # type: ignore
    )

    formatted = format_chunk(1, chunk, xml_style_config_with_metadata)
    expected = "<source1><|document|>Doc1<|/document|>\nContent text</source1>"
    assert formatted == expected


def test_default_style(
    default_config,
):
    chunk = ContentChunk(
        id="1",
        order=1,
        text="<|document|>Doc1<|/document|>\n<|info|>Important<|/info|>\nContent text",
        start_page=1,
        end_page=2,
    )

    formatted = format_chunk(1, chunk, default_config)
    expected = "<source1><|document|>Doc1<|/document|>\n<|info|>Important<|/info|>\nContent text</source1>"
    assert formatted == expected


def test_xml_style_without_page_number_formatting(
    xml_style_config_without_page_number,
):
    chunk = ContentChunk(
        id="1",
        order=1,
        text="<|document|>Doc1<|/document|>\n<|info|>Important<|/info|>\nContent text",
        start_page=1,
        end_page=2,
    )

    formatted = format_chunk(1, chunk, xml_style_config_without_page_number)
    expected = "<source1><|document|>Doc1<|/document|>\n<|info|>Important<|/info|>\nContent text</source1>"
    assert formatted == expected


def test_xml_style_with_page_number_formatting(
    xml_style_config_with_page_number,
):
    chunk = ContentChunk(
        id="1",
        order=1,
        text="<|document|>Doc1<|/document|>\n<|info|>Important<|/info|>\nContent text",
        start_page=1,
        end_page=2,
    )

    formatted = format_chunk(1, chunk, xml_style_config_with_page_number)
    expected = "<source1><|document|>Doc1<|/document|>\n<|page|>1 - 2<|/page|>\n<|info|>Important<|/info|>\nContent text</source1>"
    assert formatted == expected


def test_special_characters_handling(json_style_config):
    chunk = ContentChunk(
        id="1",
        order=1,
        text="<|document|>Doc's \"title\"<|/document|>\n<|info|>Info with {brackets}<|/info|>\nContent: with 'quotes'",
        start_page=1,
        end_page=1,
    )

    formatted = format_chunk(1, chunk, json_style_config)
    expected = "{'source_number': 1, 'content': '<|document|>Doc's \"title\"<|/document|>\n<|page|>1<|/page|>\n<|info|>Info with {brackets}<|/info|>\nContent: with 'quotes''}"
    assert formatted == expected


def test_empty_sections(xml_style_config_without_page_number, json_style_config):
    chunk = ContentChunk(
        id="1",
        order=1,
        text="Just plain text without any sections",
        start_page=None,
        end_page=None,
    )

    # Test XML style
    xml_formatted = format_chunk(1, chunk, xml_style_config_without_page_number)
    assert xml_formatted == "<source1>Just plain text without any sections</source1>"

    # Test JSON style
    json_formatted = format_chunk(1, chunk, json_style_config)
    assert (
        json_formatted
        == "{'source_number': 1, 'content': 'Just plain text without any sections'}"
    )
