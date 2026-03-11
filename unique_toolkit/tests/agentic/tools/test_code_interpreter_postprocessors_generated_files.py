"""Tests for code interpreter generated-files postprocessor (config, __init__, helpers)."""

from unittest.mock import MagicMock

import pytest
from openai.types.responses import ResponseCodeInterpreterToolCall
from openai.types.responses.response_output_text import AnnotationContainerFileCitation

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors import (
    generated_files as gen_mod,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.generated_files import (
    DisplayCodeInterpreterFilesPostProcessor,
    DisplayCodeInterpreterFilesPostProcessorConfig,
    _build_code_blocks,
    _build_file_fence,
    _file_frontend_type,
    _file_title,
    _inject_code_execution_fences,
)
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.schemas import (
    CodeInterpreterBlock,
    CodeInterpreterFile,
)


@pytest.mark.ai
def test_display_code_interpreter_files_config__has_defaults__when_constructed_with_no_args() -> (
    None
):
    """
    Purpose: Verify DisplayCodeInterpreterFilesPostProcessorConfig default field values.
    Why this matters: Ensures upload and concurrency defaults are correct.
    Setup summary: Instantiate config with no args; assert defaults.
    """
    # Act
    config = DisplayCodeInterpreterFilesPostProcessorConfig()

    # Assert
    assert config.upload_to_chat is True
    assert config.upload_scope_id == "<SCOPE_ID_PLACEHOLDER>"
    assert config.file_download_failed_message == "⚠️ File download failed ..."
    assert config.max_concurrent_file_downloads == 10


@pytest.mark.ai
def test_display_code_interpreter_files_post_processor__raises__when_no_chat_service() -> (
    None
):
    """
    Purpose: Verify ValueError when chat_service is None.
    Why this matters: ChatService is always required; prevents misconfiguration that would fail at runtime.
    Setup summary: Construct with chat_service=None; assert ValueError.
    """
    # Arrange
    config = DisplayCodeInterpreterFilesPostProcessorConfig()
    mock_client = MagicMock()
    mock_content_service = MagicMock()

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        DisplayCodeInterpreterFilesPostProcessor(
            client=mock_client,
            content_service=mock_content_service,
            config=config,
            chat_service=None,
        )
    assert "ChatService" in str(exc_info.value)


@pytest.mark.ai
def test_get_next_ref_number__returns_one__when_references_empty() -> None:
    """
    Purpose: Verify next reference number is 1 when no references exist.
    Why this matters: First citation gets sequence number 1.
    Setup summary: Call _get_next_ref_number with empty list; assert 1.
    """
    # Act
    result = gen_mod._get_next_ref_number([])

    # Assert
    assert result == 1


@pytest.mark.ai
def test_get_next_ref_number__returns_max_plus_one__when_references_given() -> None:
    """
    Purpose: Verify next reference number is max(sequence_number) + 1.
    Why this matters: Citations are numbered sequentially without collision.
    Setup summary: References with sequence_number 2 and 5; assert 6.
    """
    # Arrange
    refs = [
        ContentReference(
            name="a",
            sequence_number=2,
            source="s",
            source_id="sid",
            url="u",
        ),
        ContentReference(
            name="b",
            sequence_number=5,
            source="s",
            source_id="sid",
            url="u",
        ),
    ]

    # Act
    result = gen_mod._get_next_ref_number(refs)

    # Assert
    assert result == 6


@pytest.mark.ai
def test_replace_container_file_error__replaces_image_markdown__with_error_message() -> (
    None
):
    """
    Purpose: Verify sandbox image markdown is replaced by error message when download fails.
    Why this matters: User sees a clear failure message instead of broken image.
    Setup summary: Text with [label](sandbox:/mnt/data/file.png); assert replaced with error message.
    """
    # Arrange
    text = "See [chart](sandbox:/mnt/data/file.png) here."
    error_message = "⚠️ File download failed ..."

    # Act
    new_text, replaced = gen_mod._replace_container_file_error(
        text, filename="file.png", error_message=error_message
    )

    # Assert
    assert replaced is True
    assert "file.png" not in new_text or "sandbox" not in new_text
    assert error_message in new_text


@pytest.mark.ai
def test_replace_container_file_error__returns_unchanged__when_no_matching_markdown() -> (
    None
):
    """
    Purpose: Verify text is unchanged when no sandbox image markdown for filename exists.
    Why this matters: Avoids incorrect replacements.
    Setup summary: Text without matching pattern for given filename; assert (text, False).
    """
    # Arrange
    text = "No sandbox link here."
    error_message = "⚠️ File download failed ..."

    # Act
    new_text, replaced = gen_mod._replace_container_file_error(
        text, filename="missing.png", error_message=error_message
    )

    # Assert
    assert replaced is False
    assert new_text == text


@pytest.mark.ai
def test_replace_container_image_citation__replaces_markdown__with_unique_content_image() -> (
    None
):
    """
    Purpose: Verify sandbox image markdown is replaced by unique://content/{id} image.
    Why this matters: Images are displayed from uploaded content.
    Setup summary: Text with image markdown for filename; assert unique://content/{content_id} in result.
    """
    # Arrange
    text = "Chart: [x](sandbox:/mnt/data/plot.png)"
    content_id = "content-123"

    # Act
    new_text, replaced = gen_mod._replace_container_image_citation(
        text, filename="plot.png", content_id=content_id
    )

    # Assert
    assert replaced is True
    assert f"unique://content/{content_id}" in new_text
    assert "sandbox" not in new_text


@pytest.mark.ai
def test_replace_container_file_citation__replaces_link__with_unique_content_link() -> (
    None
):
    """
    Purpose: Verify file link markdown is replaced by a unique://content link with the filename as label.
    Why this matters: Non-image files are shown as download links with a stable content_id in the URL,
    allowing frontend to map the inline position back to the corresponding code_blocks entry.
    Setup summary: Text with [label](sandbox:/mnt/data/data.csv); assert unique://content/{content_id} in result.
    """
    # Arrange
    text = "Data in [file](sandbox:/mnt/data/data.csv)."
    content_id = "cont_abc123"

    # Act
    new_text, replaced = gen_mod._replace_container_file_citation(
        text, filename="data.csv", content_id=content_id
    )

    # Assert
    assert replaced is True
    assert f"[data.csv](unique://content/{content_id})" in new_text
    assert "sandbox" not in new_text


@pytest.mark.ai
def test_replace_container_html_citation__replaces_markdown__with_html_rendering_block() -> (
    None
):
    """
    Purpose: Verify sandbox HTML link is replaced by HtmlRendering code block with content URL.
    Why this matters: HTML files are rendered in chat via special block.
    Setup summary: Text with link to .html file; assert ```HtmlRendering and unique://content in result.
    """
    # Arrange
    text = "Report: [report](sandbox:/mnt/data/report.html)"
    content_id = "html-content-456"

    # Act
    new_text, replaced = gen_mod._replace_container_html_citation(
        text, filename="report.html", content_id=content_id
    )

    # Assert
    assert replaced is True
    assert "HtmlRendering" in new_text
    assert f"unique://content/{content_id}" in new_text
    assert "sandbox" not in new_text


# ============================================================================
# Tests for _build_code_blocks
# ============================================================================


def _make_ci_call(
    code: str, container_id: str = "cntr_1"
) -> ResponseCodeInterpreterToolCall:
    return ResponseCodeInterpreterToolCall(
        id="ci_1",
        code=code,
        container_id=container_id,
        outputs=None,
        status="completed",
        type="code_interpreter_call",
    )


def _make_annotation(
    filename: str, file_id: str = "cfile_1", container_id: str = "cntr_1"
) -> AnnotationContainerFileCitation:
    return AnnotationContainerFileCitation(
        container_id=container_id,
        file_id=file_id,
        filename=filename,
        start_index=0,
        end_index=10,
        type="container_file_citation",
    )


def _make_response(calls, annotations):
    response = MagicMock()
    response.code_interpreter_calls = calls
    response.container_files = annotations
    return response


@pytest.mark.ai
def test_build_code_blocks__maps_single_block_to_single_file__when_path_matches() -> (
    None
):
    """
    Purpose: Verify Case 1 — 1 code block, 1 file — is mapped correctly.
    Why this matters: Simplest case must work; file linked to its producing block.
    Setup summary: Code writes /mnt/data/report.xlsx; annotation for report.xlsx.
    """
    call = _make_ci_call('df.to_excel("/mnt/data/report.xlsx")')
    annotation = _make_annotation("report.xlsx", file_id="cfile_abc")
    content_map = {"report.xlsx": "unique://content/abc123"}
    response = _make_response([call], [annotation])

    result = _build_code_blocks(response, content_map)

    assert len(result) == 1
    assert result[0].code == call.code
    assert len(result[0].files) == 1
    assert result[0].files[0].filename == "report.xlsx"
    assert result[0].files[0].content_id == "unique://content/abc123"
    assert result[0].files[0].type == "document"


@pytest.mark.ai
def test_build_code_blocks__maps_two_blocks_to_separate_files__when_paths_distinct() -> (
    None
):
    """
    Purpose: Verify Case 4 — N blocks, N files — each file maps to its producing block.
    Why this matters: Core mapping logic must assign files to the correct block.
    Setup summary: Block 1 writes xlsx, block 2 writes png; each gets its own entry.
    """
    call1 = _make_ci_call('df.to_excel("/mnt/data/data.xlsx")')
    call2 = _make_ci_call('plt.savefig("/mnt/data/chart.png")')
    ann_xlsx = _make_annotation("data.xlsx", file_id="cfile_1")
    ann_png = _make_annotation("chart.png", file_id="cfile_2")
    content_map = {
        "data.xlsx": "unique://content/id1",
        "chart.png": "unique://content/id2",
    }
    response = _make_response([call1, call2], [ann_xlsx, ann_png])

    result = _build_code_blocks(response, content_map)

    assert len(result) == 2
    assert result[0].files[0].filename == "data.xlsx"
    assert result[0].files[0].type == "document"
    assert result[1].files[0].filename == "chart.png"
    assert result[1].files[0].type == "image"


@pytest.mark.ai
def test_build_code_blocks__discards_blocks_without_files__returns_empty() -> None:
    """
    Purpose: Verify Case 5 — code ran but no files produced — returns empty list.
    Why this matters: Pure computation blocks must not appear in code_blocks.
    Setup summary: Code block with no /mnt/data/ write and no annotations.
    """
    call = _make_ci_call("result = 2 ** 32\nresult")
    content_map: dict = {}
    response = _make_response([call], [])

    result = _build_code_blocks(response, content_map)

    assert result == []


@pytest.mark.ai
def test_build_code_blocks__assigns_image_type__for_png_file() -> None:
    """
    Purpose: Verify PNG files get type 'image', not 'document'.
    Why this matters: Frontend uses type to choose the correct renderer.
    Setup summary: Code writes plot.png; verify type == 'image'.
    """
    call = _make_ci_call('plt.savefig("/mnt/data/plot.png")')
    annotation = _make_annotation("plot.png")
    content_map = {"plot.png": "unique://content/img1"}
    response = _make_response([call], [annotation])

    result = _build_code_blocks(response, content_map)

    assert result[0].files[0].type == "image"


@pytest.mark.ai
def test_build_code_blocks__skips_file__when_content_id_is_none() -> None:
    """
    Purpose: Verify files that failed upload (content_id=None) are excluded.
    Why this matters: Must not expose broken file references to the frontend.
    Setup summary: content_map has None for a filename; verify file excluded.
    """
    call = _make_ci_call('df.to_excel("/mnt/data/broken.xlsx")')
    annotation = _make_annotation("broken.xlsx")
    content_map = {"broken.xlsx": None}
    response = _make_response([call], [annotation])

    result = _build_code_blocks(response, content_map)

    assert result == []


@pytest.mark.ai
def test_build_code_blocks__assigns_file_to_last_block__when_two_blocks_reference_same_file() -> (
    None
):
    """
    Purpose: Verify duplicate-file-across-blocks edge case — last block wins.
    Why this matters: Last block is the final producer; its output is what the user receives.
    Setup summary: Two blocks both reference shared.csv; only block 2 (last writer) should own it.
    """
    call1 = _make_ci_call('df.to_csv("/mnt/data/shared.csv")')
    call2 = _make_ci_call('df.to_csv("/mnt/data/shared.csv")  # final export')
    annotation = _make_annotation("shared.csv", file_id="cfile_1")
    content_map = {"shared.csv": "cont_shared1"}
    response = _make_response([call1, call2], [annotation])

    result = _build_code_blocks(response, content_map)

    assert len(result) == 1
    assert result[0].code == call2.code
    assert result[0].files[0].filename == "shared.csv"


@pytest.mark.ai
def test_build_code_blocks__deduplicates_file__when_two_annotations_for_same_filename() -> (
    None
):
    """
    Purpose: Verify that duplicate annotations for the same filename (emitted by OpenAI when a
    file is overwritten across executions) result in exactly ONE file entry per block.
    Why this matters: Without deduplication, the fence would contain the same content_id line
    twice, causing the frontend parser to produce two identical outputRefs for the same file.
    Setup summary: Two annotations for shared.csv pointing to the same content_id; assert
    the winning block has exactly one file entry.
    """
    call1 = _make_ci_call('df.to_csv("/mnt/data/shared.csv")')
    call2 = _make_ci_call('df.to_csv("/mnt/data/shared.csv")  # overwrite')
    annotation1 = _make_annotation("shared.csv", file_id="cfile_1")
    annotation2 = _make_annotation("shared.csv", file_id="cfile_2")
    content_map = {"shared.csv": "cont_shared1"}
    response = _make_response([call1, call2], [annotation1, annotation2])

    result = _build_code_blocks(response, content_map)

    assert len(result) == 1
    assert len(result[0].files) == 1
    assert result[0].files[0].filename == "shared.csv"
    assert result[0].files[0].content_id == "cont_shared1"


# ============================================================================
# Tests for _file_title
# ============================================================================


@pytest.mark.ai
def test_file_title__strips_extension_and_title_cases() -> None:
    assert _file_title("monthly_revenue_chart.png") == "Monthly Revenue Chart"


@pytest.mark.ai
def test_file_title__handles_hyphens() -> None:
    assert _file_title("random-data.csv") == "Random Data"


@pytest.mark.ai
def test_file_title__handles_no_extension() -> None:
    assert _file_title("report") == "Report"


# ============================================================================
# Tests for _file_frontend_type
# ============================================================================


@pytest.mark.ai
def test_file_frontend_type__returns_excel__for_xlsx() -> None:
    assert _file_frontend_type("data.xlsx") == "excel"


@pytest.mark.ai
def test_file_frontend_type__returns_csv__for_csv() -> None:
    assert _file_frontend_type("data.csv") == "csv"


@pytest.mark.ai
def test_file_frontend_type__returns_image__for_png() -> None:
    assert _file_frontend_type("chart.png") == "image"


@pytest.mark.ai
def test_file_frontend_type__returns_pdf__for_pdf() -> None:
    assert _file_frontend_type("report.pdf") == "pdf"


@pytest.mark.ai
def test_file_frontend_type__returns_document__for_unknown() -> None:
    assert _file_frontend_type("output.xyz") == "document"


# ============================================================================
# Tests for _build_file_fence
# ============================================================================


@pytest.mark.ai
def test_build_file_fence__image__uses_imgWithSource_tag() -> None:
    """
    Purpose: Verify images produce an imgWithSource fence with 4-backtick delimiters.
    """
    file = CodeInterpreterFile(
        filename="chart.png", content_id="cont_img1", type="image"
    )
    fence = _build_file_fence(file, 'plt.savefig("/mnt/data/chart.png")', fence_id=1)
    assert fence.startswith("````imgWithSource(")
    assert fence.endswith("````")
    assert "contentId='cont_img1'" in fence
    assert 'title="Chart"' in fence


@pytest.mark.ai
def test_build_file_fence__document__uses_fileWithSource_tag() -> None:
    """
    Purpose: Verify documents produce a fileWithSource fence with type attribute.
    """
    file = CodeInterpreterFile(
        filename="data.xlsx", content_id="cont_doc1", type="document"
    )
    fence = _build_file_fence(file, 'df.to_excel("/mnt/data/data.xlsx")', fence_id=2)
    assert fence.startswith("````fileWithSource(")
    assert "contentId='cont_doc1'" in fence
    assert 'type="excel"' in fence
    assert 'title="Data"' in fence


@pytest.mark.ai
def test_build_file_fence__code_is_escaped__when_contains_double_quotes() -> None:
    """
    Purpose: Verify double quotes inside the code string are escaped so the
    attribute value is not broken.
    """
    file = CodeInterpreterFile(
        filename="out.csv", content_id="cont_c1", type="document"
    )
    code = 'df.to_csv("/mnt/data/out.csv")'
    fence = _build_file_fence(file, code, fence_id=1)
    assert '\\"' in fence
    assert '"/mnt/data/out.csv"' not in fence


@pytest.mark.ai
def test_build_file_fence__id_is_present() -> None:
    """
    Purpose: Verify the fence_id appears as the id attribute.
    """
    file = CodeInterpreterFile(
        filename="chart.png", content_id="cont_img1", type="image"
    )
    fence = _build_file_fence(file, "plt.savefig(...)", fence_id=42)
    assert "id='42'" in fence


# ============================================================================
# Tests for _inject_code_execution_fences
# ============================================================================


@pytest.mark.ai
def test_inject_code_execution_fences__replaces_image_inline_ref__with_imgWithSource() -> (
    None
):
    """
    Purpose: Verify an inline image ref is replaced by an imgWithSource fence.
    """
    block = CodeInterpreterBlock(
        code='plt.savefig("/mnt/data/chart.png")',
        files=[
            CodeInterpreterFile(
                filename="chart.png", content_id="cont_img1", type="image"
            )
        ],
    )
    text = "Here is the chart: ![image](unique://content/cont_img1)"

    result = _inject_code_execution_fences(text, [block])

    assert "````imgWithSource(" in result
    assert "cont_img1" in result
    assert "![image](unique://content/cont_img1)" not in result


@pytest.mark.ai
def test_inject_code_execution_fences__leaves_document_inline_ref__unchanged() -> None:
    """
    Purpose: Verify document links are NOT replaced (scoped to images only for initial release).
    Why this matters: Non-image files keep their existing download link which already
    renders on the frontend; fileWithSource is not emitted until frontend builds a parser.
    """
    block = CodeInterpreterBlock(
        code='df.to_excel("/mnt/data/data.xlsx")',
        files=[
            CodeInterpreterFile(
                filename="data.xlsx", content_id="cont_doc1", type="document"
            )
        ],
    )
    text = "Download: [data.xlsx](unique://content/cont_doc1)"

    result = _inject_code_execution_fences(text, [block])

    assert "````fileWithSource(" not in result
    assert "[data.xlsx](unique://content/cont_doc1)" in result


@pytest.mark.ai
def test_inject_code_execution_fences__image_fence_and_document_link_coexist() -> None:
    """
    Purpose: Verify that when one block has an image and a document, the image gets
    an imgWithSource fence and the document keeps its inline link.
    Why this matters: Mixed block — image renders via fence, document stays as download link.
    """
    block = CodeInterpreterBlock(
        code='plt.savefig("/mnt/data/chart.png")\ndf.to_excel("/mnt/data/data.xlsx")',
        files=[
            CodeInterpreterFile(
                filename="chart.png", content_id="cont_img1", type="image"
            ),
            CodeInterpreterFile(
                filename="data.xlsx", content_id="cont_doc1", type="document"
            ),
        ],
    )
    text = "![image](unique://content/cont_img1)\nSee also: [data.xlsx](unique://content/cont_doc1)"

    result = _inject_code_execution_fences(text, [block])

    assert result.count("````imgWithSource(") == 1
    assert "````fileWithSource(" not in result
    assert "![image](unique://content/cont_img1)" not in result
    assert "[data.xlsx](unique://content/cont_doc1)" in result


@pytest.mark.ai
def test_inject_code_execution_fences__removes_second_ref__when_same_file_linked_twice() -> (
    None
):
    """
    Purpose: Verify that when the model emits two download links for the same non-image file
    (overwrite case), both links are left unchanged — no fence emitted, no cleanup.
    Why this matters: Non-image files are skipped entirely in this release. The duplicate
    link case is therefore a no-op: both inline refs remain so the user still has a download
    link.
    Setup summary: Text has two identical inline refs for the same document file; assert
    no fence and both refs still present.
    """
    block = CodeInterpreterBlock(
        code='df.to_csv("/mnt/data/data.csv")',
        files=[
            CodeInterpreterFile(
                filename="data.csv", content_id="cont_csv1", type="document"
            )
        ],
    )
    text = (
        "First version: [data.csv](unique://content/cont_csv1)\n"
        "Updated version: [data.csv](unique://content/cont_csv1)"
    )

    result = _inject_code_execution_fences(text, [block])

    assert "````fileWithSource(" not in result
    assert result.count("[data.csv](unique://content/cont_csv1)") == 2


@pytest.mark.ai
def test_inject_code_execution_fences__two_blocks__produce_two_fences() -> None:
    """
    Purpose: Verify two separate code blocks each produce their own fence.
    Why this matters: Case 4 — N blocks, N files — each file gets its own fence.
    """
    block1 = CodeInterpreterBlock(
        code='df.to_excel("/mnt/data/kpis.xlsx")',
        files=[
            CodeInterpreterFile(
                filename="kpis.xlsx", content_id="cont_doc1", type="document"
            )
        ],
    )
    block2 = CodeInterpreterBlock(
        code='plt.savefig("/mnt/data/chart.png")',
        files=[
            CodeInterpreterFile(
                filename="chart.png", content_id="cont_img2", type="image"
            )
        ],
    )
    text = (
        "[kpis.xlsx](unique://content/cont_doc1)\n![image](unique://content/cont_img2)"
    )

    result = _inject_code_execution_fences(text, [block1, block2])

    assert result.count("````imgWithSource(") == 1
    assert "````fileWithSource(" not in result
    assert "cont_img2" in result
    assert "[kpis.xlsx](unique://content/cont_doc1)" in result


@pytest.mark.ai
def test_inject_code_execution_fences__strips_details_block__when_present() -> None:
    """
    Purpose: Verify <details><summary>Code Interpreter Call</summary>...</details>
    blocks are removed after fence injection.
    Why this matters: ShowExecutedCodePostprocessor output is superseded by codeExecution fences.
    Setup summary: Text has a <details> block followed by an image ref; assert <details> stripped.
    """
    block = CodeInterpreterBlock(
        code='plt.savefig("/mnt/data/chart.png")',
        files=[
            CodeInterpreterFile(
                filename="chart.png", content_id="cont_img1", type="image"
            )
        ],
    )
    text = (
        "<details><summary>Code Interpreter Call</summary>\n"
        "```python\nplt.savefig('/mnt/data/chart.png')\n```\n"
        "</details>\n"
        "![image](unique://content/cont_img1)"
    )

    result = _inject_code_execution_fences(text, [block])

    assert "````imgWithSource(" in result
    assert "<details>" not in result


@pytest.mark.ai
def test_inject_code_execution_fences__strips_trailing_br__after_details_block() -> (
    None
):
    """
    Purpose: Verify the stray </br> separator left after <details> stripping is also removed.
    Why this matters: ShowExecutedCodePostprocessor emits <details>...</details>    \n</br>\n
    — after stripping <details> the </br> must not be left dangling at the top of the message.
    """
    block = CodeInterpreterBlock(
        code='plt.savefig("/mnt/data/chart.png")',
        files=[
            CodeInterpreterFile(
                filename="chart.png", content_id="cont_img1", type="image"
            )
        ],
    )
    text = (
        "<details><summary>Code Interpreter Call</summary>\n"
        "```python\nplt.savefig('/mnt/data/chart.png')\n```\n"
        "</details>    \n</br>\n\n"
        "Here is the chart.\n\n"
        "![image](unique://content/cont_img1)"
    )

    result = _inject_code_execution_fences(text, [block])

    assert "</br>" not in result
    assert "<details>" not in result
    assert "Here is the chart." in result
    assert "````imgWithSource(" in result


@pytest.mark.ai
def test_inject_code_execution_fences__no_op__when_code_blocks_empty() -> None:
    """
    Purpose: Verify text is unchanged when code_blocks is empty (Case 5 — no files).
    Why this matters: Must not corrupt message text when no code execution happened.
    """
    text = "The answer is 42."
    result = _inject_code_execution_fences(text, [])
    assert result == text
