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
    _build_code_execution_fence,
    _inject_code_execution_fences,
    _to_frontend_type,
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
# Tests for _to_frontend_type
# ============================================================================


@pytest.mark.ai
def test_to_frontend_type__returns_chart__for_image() -> None:
    """
    Purpose: Verify image maps to 'chart' (the frontend type for image outputs).
    Why this matters: Frontend uses 'chart' not 'image' for CodeExecutionOutputRef type.
    """
    assert _to_frontend_type("image") == "chart"


@pytest.mark.ai
def test_to_frontend_type__returns_document__for_document() -> None:
    assert _to_frontend_type("document") == "document"


@pytest.mark.ai
def test_to_frontend_type__returns_html__for_html() -> None:
    assert _to_frontend_type("html") == "html"


# ============================================================================
# Tests for _build_code_execution_fence
# ============================================================================


@pytest.mark.ai
def test_build_code_execution_fence__contains_outer_4backtick_fence() -> None:
    """
    Purpose: Verify the outer fence uses 4 backticks so the inner 3-backtick
    code block does not prematurely close it.
    Why this matters: CommonMark: closing fence must match opening backtick count.
    """
    block = CodeInterpreterBlock(
        code='plt.savefig("/mnt/data/chart.png")',
        files=[
            CodeInterpreterFile(
                filename="chart.png", content_id="cont_img1", type="image"
            )
        ],
    )
    fence = _build_code_execution_fence(block)
    assert fence.startswith("````codeExecution\n")
    assert fence.endswith("\n````")


@pytest.mark.ai
def test_build_code_execution_fence__contains_summary_title() -> None:
    """
    Purpose: Verify <summary> tag is present so the frontend parser can extract the title.
    """
    block = CodeInterpreterBlock(
        code="print('hello')",
        files=[
            CodeInterpreterFile(
                filename="out.csv", content_id="cont_csv1", type="document"
            )
        ],
    )
    fence = _build_code_execution_fence(block)
    assert "<summary>Code Interpreter Call</summary>" in fence


@pytest.mark.ai
def test_build_code_execution_fence__contains_inner_python_code_block() -> None:
    """
    Purpose: Verify inner ```python fence wraps the source code so parseInnerCodeBlock
    can extract language and sourceCode.
    """
    code = 'df.to_excel("/mnt/data/data.xlsx")'
    block = CodeInterpreterBlock(
        code=code,
        files=[
            CodeInterpreterFile(
                filename="data.xlsx", content_id="cont_x1", type="document"
            )
        ],
    )
    fence = _build_code_execution_fence(block)
    assert "```python\n" in fence
    assert code in fence


@pytest.mark.ai
def test_build_code_execution_fence__contains_content_id_lines_with_type() -> None:
    """
    Purpose: Verify content_id lines are present in the format parseContentIdLines expects:
    'unique://content/{id} {type}' — one line per file, after the inner closing fence.
    """
    block = CodeInterpreterBlock(
        code='plt.savefig("/mnt/data/chart.png")',
        files=[
            CodeInterpreterFile(
                filename="chart.png", content_id="cont_img99", type="image"
            )
        ],
    )
    fence = _build_code_execution_fence(block)
    assert "unique://content/cont_img99 chart" in fence


@pytest.mark.ai
def test_build_code_execution_fence__multiple_files__all_content_id_lines_present() -> (
    None
):
    """
    Purpose: Verify that all files in a block appear as separate content_id lines.
    Why this matters: Case 2 — one block, multiple files.
    """
    block = CodeInterpreterBlock(
        code='df.to_excel("/mnt/data/kpis.xlsx")\nplt.savefig("/mnt/data/chart.png")',
        files=[
            CodeInterpreterFile(
                filename="kpis.xlsx", content_id="cont_doc1", type="document"
            ),
            CodeInterpreterFile(
                filename="chart.png", content_id="cont_img2", type="image"
            ),
        ],
    )
    fence = _build_code_execution_fence(block)
    assert "unique://content/cont_doc1 document" in fence
    assert "unique://content/cont_img2 chart" in fence


# ============================================================================
# Tests for _inject_code_execution_fences
# ============================================================================


@pytest.mark.ai
def test_inject_code_execution_fences__replaces_image_inline_ref__with_fence() -> None:
    """
    Purpose: Verify an inline image ref is replaced by a codeExecution fence.
    Why this matters: Core injection for image outputs.
    Setup summary: Text contains ![image](unique://content/cont_img1); assert fence in result.
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

    assert "````codeExecution" in result
    assert "unique://content/cont_img1 chart" in result
    assert "![image](unique://content/cont_img1)" not in result


@pytest.mark.ai
def test_inject_code_execution_fences__replaces_document_inline_ref__with_fence() -> (
    None
):
    """
    Purpose: Verify a document link is replaced by a codeExecution fence.
    Why this matters: Core injection for document outputs.
    Setup summary: Text has [data.xlsx](unique://content/cont_doc1); assert fence replaces it.
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

    assert "````codeExecution" in result
    assert "unique://content/cont_doc1 document" in result
    assert "[data.xlsx](unique://content/cont_doc1)" not in result


@pytest.mark.ai
def test_inject_code_execution_fences__one_fence_for_multifile_block__removes_extra_refs() -> (
    None
):
    """
    Purpose: Verify that when one block has two files, only ONE fence is injected
    at the position of the first inline ref, and the second inline ref is removed.
    Why this matters: Files from the same execution must not produce two separate fences.
    Setup summary: Text has image ref then document ref for same block; assert one fence only.
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

    assert result.count("````codeExecution") == 1
    assert "unique://content/cont_img1 chart" in result
    assert "unique://content/cont_doc1 document" in result
    assert "![image](unique://content/cont_img1)" not in result
    assert "[data.xlsx](unique://content/cont_doc1)" not in result


@pytest.mark.ai
def test_inject_code_execution_fences__removes_second_ref__when_same_file_linked_twice() -> (
    None
):
    """
    Purpose: Verify that when the model emits two download links for the same file
    (overwrite case), the fence is placed at the first link and the second is removed.
    Why this matters: OpenAI may produce two sandbox links for the same filename when a
    file is overwritten. After deduplication, the block has one CodeInterpreterFile entry,
    so only the first occurrence gets a fence — the second must still be cleaned up.
    Setup summary: Text has two identical inline refs for the same file; assert one fence,
    no leftover inline ref.
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

    assert result.count("````codeExecution") == 1
    assert "unique://content/cont_csv1 document" in result
    assert result.count("[data.csv](unique://content/cont_csv1)") == 0


@pytest.mark.ai
def test_inject_code_execution_fences__two_blocks__produce_two_fences() -> None:
    """
    Purpose: Verify two separate code blocks produce two separate fences in the text.
    Why this matters: Case 4 — N blocks, N files — each block must have its own fence.
    Setup summary: Text has one image ref and one document ref from separate blocks.
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

    assert result.count("````codeExecution") == 2
    assert "unique://content/cont_doc1 document" in result
    assert "unique://content/cont_img2 chart" in result


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

    assert "<details>" not in result
    assert "````codeExecution" in result


@pytest.mark.ai
def test_inject_code_execution_fences__no_op__when_code_blocks_empty() -> None:
    """
    Purpose: Verify text is unchanged when code_blocks is empty (Case 5 — no files).
    Why this matters: Must not corrupt message text when no code execution happened.
    """
    text = "The answer is 42."
    result = _inject_code_execution_fences(text, [])
    assert result == text
