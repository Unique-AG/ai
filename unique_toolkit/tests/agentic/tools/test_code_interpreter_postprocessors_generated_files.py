"""Tests for code interpreter generated-files postprocessor (config, __init__, helpers)."""

import logging
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
    _ensure_fences_are_standalone,
    _file_frontend_type,
    _file_title,
    _inject_code_execution_fences,
    _replace_dangling_sandbox_links,
    _warn_missing_content_ids,
    _warn_unmatched_code_blocks,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.schemas import (
    CodeInterpreterBlock,
    CodeInterpreterFile,
)
from unique_toolkit.content.schemas import ContentReference


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
    Purpose: Verify file link markdown is replaced by a unique://content link when fence FF is on.
    Why this matters: When the fence feature flag is enabled, the content link is needed so the
    subsequent fence injection step can locate and replace it with a fileWithSource fence.
    Setup summary: Text with [label](sandbox:/mnt/data/data.csv); use_content_link=True;
    assert unique://content/{content_id} in result.
    """
    # Arrange
    text = "Data in [file](sandbox:/mnt/data/data.csv)."
    content_id = "cont_abc123"

    # Act
    new_text, replaced = gen_mod._replace_container_file_citation(
        text,
        filename="data.csv",
        content_id=content_id,
        ref_number=1,
        use_content_link=True,
    )

    # Assert
    assert replaced is True
    assert f"[data.csv](unique://content/{content_id})" in new_text
    assert "sandbox" not in new_text


@pytest.mark.ai
def test_replace_container_file_citation__replaces_link__with_superscript_when_fence_ff_off() -> (
    None
):
    """
    Purpose: Verify file link markdown is replaced by a superscript ref when fence FF is off.
    Why this matters: When the fence feature flag is disabled, the original pre-fence behaviour
    must be preserved — the sandbox link becomes <sup>N</sup> and the file remains accessible
    via the references panel only. This restores the regression introduced in PR #1163.
    Setup summary: Text with [label](sandbox:/mnt/data/data.csv); use_content_link=False;
    assert <sup>1</sup> in result, no unique:// link in text.
    """
    # Arrange
    text = "Data in [file](sandbox:/mnt/data/data.csv)."
    content_id = "cont_abc123"

    # Act
    new_text, replaced = gen_mod._replace_container_file_citation(
        text,
        filename="data.csv",
        content_id=content_id,
        ref_number=1,
        use_content_link=False,
    )

    # Assert
    assert replaced is True
    assert "<sup>1</sup>" in new_text
    assert "unique://" not in new_text
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
def test_inject_code_execution_fences__replaces_document_inline_ref__with_fileWithSource() -> (
    None
):
    """
    Purpose: Verify a document link is replaced by a fileWithSource fence.
    Why this matters: Non-image files get a fileWithSource fence carrying contentId,
    title, type and code so the frontend can offer a download with full context.
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

    assert "````fileWithSource(" in result
    assert "cont_doc1" in result
    assert "[data.xlsx](unique://content/cont_doc1)" not in result


@pytest.mark.ai
def test_inject_code_execution_fences__image_and_document_each_get_own_fence() -> None:
    """
    Purpose: Verify that when one block has an image and a document, each gets its own fence.
    Why this matters: Mixed block — image gets imgWithSource, document gets fileWithSource.
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
    assert result.count("````fileWithSource(") == 1
    assert "![image](unique://content/cont_img1)" not in result
    assert "[data.xlsx](unique://content/cont_doc1)" not in result


@pytest.mark.ai
def test_inject_code_execution_fences__removes_second_ref__when_same_file_linked_twice() -> (
    None
):
    """
    Purpose: Verify that when the model emits two download links for the same non-image file
    (overwrite case), the fence is placed at the first occurrence and the duplicate is removed.
    Why this matters: OpenAI may produce two sandbox links for the same filename when a file
    is overwritten. After deduplication, the block has one CodeInterpreterFile entry, so only
    the first occurrence gets a fence — the second must be cleaned up.
    Setup summary: Text has two identical inline refs for the same document file; assert one
    fence, no leftover inline ref.
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

    assert result.count("````fileWithSource(") == 1
    assert result.count("[data.csv](unique://content/cont_csv1)") == 0


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
    assert result.count("````fileWithSource(") == 1
    assert "cont_img2" in result
    assert "cont_doc1" in result
    assert "[kpis.xlsx](unique://content/cont_doc1)" not in result


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


# ============================================================================
# Tests for warning paths — fence injection
# ============================================================================


@pytest.mark.ai
def test_inject_code_execution_fences__logs_warning__when_no_inline_ref_matches(
    caplog,
) -> None:
    """
    Purpose: Verify a WARNING is emitted when the inline ref for a file cannot be found
    in the text, so the fence is discarded.
    Why this matters: Silent drops make production debugging very hard; a warning makes
    the missing link immediately visible in logs.
    Setup summary: Text has no matching unique://content ref for the file; assert warning logged.
    """
    block = CodeInterpreterBlock(
        code='plt.savefig("/mnt/data/chart.png")',
        files=[
            CodeInterpreterFile(
                filename="chart.png", content_id="cont_img1", type="image"
            )
        ],
    )
    text = "No image ref here."

    with caplog.at_level(logging.WARNING, logger="unique_toolkit"):
        result = _inject_code_execution_fences(text, [block])

    assert result == text
    assert any(
        "chart.png" in r.message and r.levelno == logging.WARNING
        for r in caplog.records
    )


@pytest.mark.ai
def test_inject_code_execution_fences__no_warning__when_ref_matches(caplog) -> None:
    """
    Purpose: Verify no WARNING is emitted when the inline ref is found and the fence is
    successfully injected.
    Why this matters: Ensures no false-positive noise in production logs.
    """
    block = CodeInterpreterBlock(
        code='plt.savefig("/mnt/data/chart.png")',
        files=[
            CodeInterpreterFile(
                filename="chart.png", content_id="cont_img1", type="image"
            )
        ],
    )
    text = "Here: ![image](unique://content/cont_img1)"

    with caplog.at_level(logging.WARNING, logger="unique_toolkit"):
        _inject_code_execution_fences(text, [block])

    assert not any(r.levelno == logging.WARNING for r in caplog.records)


# ============================================================================
# Tests for warning paths — stage-1 replacement helpers
# ============================================================================


@pytest.mark.ai
def test_replace_container_image_citation__logs_warning__when_no_sandbox_link(
    caplog,
) -> None:
    """
    Purpose: Verify a WARNING is emitted by _replace_container_image_citation when no
    sandbox link is present for the filename.
    Why this matters: Makes it visible in production that the LLM omitted the link.
    """
    with caplog.at_level(logging.WARNING, logger="unique_toolkit"):
        _, replaced = gen_mod._replace_container_image_citation(
            text="No link here.", filename="plot.png", content_id="cont_x"
        )

    assert replaced is False
    assert any(
        "plot.png" in r.message and r.levelno == logging.WARNING for r in caplog.records
    )


@pytest.mark.ai
def test_replace_container_file_citation__logs_warning__when_no_sandbox_link(
    caplog,
) -> None:
    """
    Purpose: Verify a WARNING is emitted by _replace_container_file_citation when no
    sandbox link is present for the filename.
    """
    with caplog.at_level(logging.WARNING, logger="unique_toolkit"):
        _, replaced = gen_mod._replace_container_file_citation(
            text="No link here.", filename="data.csv", content_id="cont_y"
        )

    assert replaced is False
    assert any(
        "data.csv" in r.message and r.levelno == logging.WARNING for r in caplog.records
    )


@pytest.mark.ai
def test_replace_container_html_citation__logs_warning__when_no_sandbox_link(
    caplog,
) -> None:
    """
    Purpose: Verify a WARNING is emitted by _replace_container_html_citation when no
    sandbox link is present for the filename.
    """
    with caplog.at_level(logging.WARNING, logger="unique_toolkit"):
        _, replaced = gen_mod._replace_container_html_citation(
            text="No link here.", filename="report.html", content_id="cont_z"
        )

    assert replaced is False
    assert any(
        "report.html" in r.message and r.levelno == logging.WARNING
        for r in caplog.records
    )


# ============================================================================
# Tests for _warn_missing_content_ids (end-of-pipeline check)
# ============================================================================


@pytest.mark.ai
def test_warn_missing_content_ids__logs_info__when_content_id_absent(
    caplog,
) -> None:
    """
    Purpose: Verify an INFO message is emitted when a content_id from content_map is
    not present in the final message text.
    Why this matters: An absent content_id can occur during normal LLM iteration
    (e.g. the model retried and overwrote a file), so INFO rather than WARNING
    avoids false-positive noise while still being visible in verbose logs.
    Setup summary: content_map has one entry whose content_id is absent from text.
    """
    content_map: dict[str, str | None] = {"chart.png": "cont_img1"}
    text = "The answer is 42."

    with caplog.at_level(logging.INFO, logger="unique_toolkit"):
        _warn_missing_content_ids(text, content_map)

    assert any(
        "cont_img1" in r.message and r.levelno == logging.INFO for r in caplog.records
    )


@pytest.mark.ai
def test_warn_missing_content_ids__no_warning__when_content_id_present(
    caplog,
) -> None:
    """
    Purpose: Verify no WARNING is emitted when all content_ids appear in the final text.
    Why this matters: Ensures no false-positive noise when the pipeline ran correctly.
    """
    content_map: dict[str, str | None] = {"chart.png": "cont_img1"}
    text = "````imgWithSource(id='1', contentId='cont_img1', ...)````"

    with caplog.at_level(logging.WARNING, logger="unique_toolkit"):
        _warn_missing_content_ids(text, content_map)

    assert not any(r.levelno == logging.WARNING for r in caplog.records)


@pytest.mark.ai
def test_warn_missing_content_ids__skips_none_content_ids(caplog) -> None:
    """
    Purpose: Verify files whose content_id is None (upload failed) are silently skipped.
    Why this matters: Upload failures are already handled upstream; no double warning here.
    """
    content_map: dict[str, str | None] = {"broken.xlsx": None}
    text = "Some text with no content id."

    with caplog.at_level(logging.WARNING, logger="unique_toolkit"):
        _warn_missing_content_ids(text, content_map)

    assert not any(r.levelno == logging.WARNING for r in caplog.records)


@pytest.mark.ai
def test_warn_missing_content_ids__logs_info_only_missing__when_mixed(caplog) -> None:
    """
    Purpose: Verify only the absent content_id triggers an INFO log when some are
    present and some are missing.
    Why this matters: Partial-success pipelines should surface exactly the gap at
    INFO level (not WARNING, since missing IDs can occur during normal LLM iteration).
    Setup summary: Two files; first present in text, second absent; assert one INFO log.
    """
    content_map: dict[str, str | None] = {
        "chart.png": "cont_present",
        "data.csv": "cont_missing",
    }
    text = "See ````imgWithSource(contentId='cont_present')````"

    with caplog.at_level(logging.INFO, logger="unique_toolkit"):
        _warn_missing_content_ids(text, content_map)

    info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
    assert len(info_messages) == 1
    assert "cont_missing" in info_messages[0]


# ============================================================================
# Tests for _ensure_fences_are_standalone
# ============================================================================


@pytest.mark.ai
def test_ensure_fences_are_standalone__strips_list_prefix__before_file_fence() -> None:
    """
    Purpose: Verify a '- File: ' list-item prefix before a fileWithSource fence is stripped.
    Why this matters: The LLM often wraps file links in markdown list items
    (e.g. '- File: [link](sandbox:...)').  After stage-1 replacement the link
    becomes a fence, leaving '- File: ````fileWithSource(...)````. The frontend
    markdown parser cannot extract a fence that is not at the start of its line.
    Setup summary: Text with '- File: ````fileWithSource(...)```'; assert prefix stripped.
    """
    text = 'Results:\n\n- File: ````fileWithSource(id=\'1\', contentId=\'cid\', title="Data", type="csv", code="")````\n\nDone.'

    result = _ensure_fences_are_standalone(text)

    assert "- File: " not in result
    assert "````fileWithSource(" in result
    assert result.count("````fileWithSource(") == 1
    assert "Results:" in result
    assert "Done." in result


@pytest.mark.ai
def test_ensure_fences_are_standalone__strips_list_prefix__before_img_fence() -> None:
    """
    Purpose: Verify a list-item prefix before an imgWithSource fence is also stripped.
    """
    text = "- Chart: ````imgWithSource(id='1', contentId='cid', title=\"Chart\", code=\"\")````"

    result = _ensure_fences_are_standalone(text)

    assert "- Chart: " not in result
    assert result.startswith("````imgWithSource(")


@pytest.mark.ai
def test_ensure_fences_are_standalone__no_change__when_fence_already_standalone() -> (
    None
):
    """
    Purpose: Verify text is unchanged when the fence already starts at the beginning
    of its line.
    Why this matters: No-op on well-formed output avoids accidental mutations.
    """
    text = 'Here is the result:\n\n````fileWithSource(id=\'1\', contentId=\'cid\', title="Data", type="csv", code="")````\n\nDone.'

    result = _ensure_fences_are_standalone(text)

    assert result == text


@pytest.mark.ai
def test_inject_code_execution_fences__file_fence_standalone__when_llm_uses_list_item() -> (
    None
):
    """
    Purpose: End-to-end verify that a fence injected into a list-item context
    (e.g. '- File: [data.csv](unique://content/...)') ends up standalone after injection.
    Why this matters: Serhan (frontend) reported fileWithSource fences were being
    embedded inside markdown list items ('- File: ````fileWithSource(...)````'),
    which prevents the frontend markdown parser from extracting them.
    Setup summary: Text has '- File: [data.csv](unique://content/cid)'; after injection
    the fence must start at the beginning of its line with no leading text.
    """
    block = CodeInterpreterBlock(
        code='df.to_csv("/mnt/data/data.csv")',
        files=[
            CodeInterpreterFile(
                filename="data.csv", content_id="cont_csv1", type="document"
            )
        ],
    )
    text = "Generated the file:\n\n- File: [data.csv](unique://content/cont_csv1)\n\nWould you like a preview?"

    result = _inject_code_execution_fences(text, [block])

    assert "````fileWithSource(" in result
    # Fence must not be preceded by any non-whitespace text on the same line
    for line in result.splitlines():
        if "````fileWithSource(" in line:
            assert line.lstrip() == line or line.strip().startswith("````"), (
                f"Fence is not at the start of its line: {line!r}"
            )
    assert "- File: " not in result
    assert "Generated the file:" in result
    assert "Would you like a preview?" in result


# ============================================================================
# Tests for consecutive fences on the same line
# ============================================================================


@pytest.mark.ai
def test_inject_code_execution_fences__separates_fences__when_inline_refs_on_same_line() -> (
    None
):
    """
    Purpose: Verify that two fences which end up on the same line are separated by
    exactly one newline.
    Why this matters: The frontend expects exactly one newline between consecutive
    fences regardless of how the LLM originally spaced the refs.
    Setup summary: Text has two unique:// refs on the same line; assert fences are
    separated by exactly one newline after injection.
    """
    block = CodeInterpreterBlock(
        code='plt.savefig("/mnt/data/chart.png")\ndf.to_csv("/mnt/data/data.csv")',
        files=[
            CodeInterpreterFile(
                filename="chart.png", content_id="cont_img1", type="image"
            ),
            CodeInterpreterFile(
                filename="data.csv", content_id="cont_csv1", type="document"
            ),
        ],
    )
    # Both refs on the same line — edge case the LLM could produce
    text = "Files: ![image](unique://content/cont_img1) and [data.csv](unique://content/cont_csv1)"

    result = _inject_code_execution_fences(text, [block])

    img_end = result.index("````imgWithSource(")
    img_end = result.index("````", img_end + 4) + 4  # end of closing ````
    csv_start = result.index("````fileWithSource(")
    between = result[img_end:csv_start]
    assert between == "\n", (
        f"Expected exactly one newline between fences, got {between!r}"
    )


@pytest.mark.ai
def test_inject_code_execution_fences__normalises_to_one_newline__when_fences_on_separate_lines() -> (
    None
):
    """
    Purpose: Verify that fences already separated by one newline stay at one newline
    (idempotent), and that fences separated by two newlines are normalised down to one.
    Why this matters: The frontend expects exactly one newline between consecutive fences.
    """
    block1 = CodeInterpreterBlock(
        code='plt.savefig("/mnt/data/chart.png")',
        files=[
            CodeInterpreterFile(
                filename="chart.png", content_id="cont_img1", type="image"
            )
        ],
    )
    block2 = CodeInterpreterBlock(
        code='df.to_csv("/mnt/data/data.csv")',
        files=[
            CodeInterpreterFile(
                filename="data.csv", content_id="cont_csv1", type="document"
            )
        ],
    )

    # Case 1: already one newline — should stay as one newline
    text_one = (
        "![image](unique://content/cont_img1)\n[data.csv](unique://content/cont_csv1)"
    )
    result_one = _inject_code_execution_fences(text_one, [block1, block2])
    img_end = result_one.index("````imgWithSource(")
    img_end = result_one.index("````", img_end + 4) + 4
    csv_start = result_one.index("````fileWithSource(")
    assert result_one[img_end:csv_start] == "\n", (
        "One newline should stay as one newline"
    )

    # Case 2: two newlines (blank line) — should be normalised to one newline
    text_two = (
        "![image](unique://content/cont_img1)\n\n[data.csv](unique://content/cont_csv1)"
    )
    result_two = _inject_code_execution_fences(text_two, [block1, block2])
    img_end2 = result_two.index("````imgWithSource(")
    img_end2 = result_two.index("````", img_end2 + 4) + 4
    csv_start2 = result_two.index("````fileWithSource(")
    assert result_two[img_end2:csv_start2] == "\n", (
        "Two newlines should be normalised to one"
    )


# ============================================================================
# Tests for _replace_dangling_sandbox_links
# ============================================================================


@pytest.mark.ai
def test_replace_dangling_sandbox_links__replaces_and_warns__when_sandbox_link_present(
    caplog,
) -> None:
    """
    Purpose: Verify that dangling sandbox links are replaced with the error message
    and a WARNING is logged.
    Why this matters: Without replacement the user sees a broken link; the warning
    makes the incident visible in production logs.
    """
    text = "Download: [chart](sandbox:/mnt/data/chart.png)"
    error_msg = "⚠️ File download failed ..."

    with caplog.at_level(logging.WARNING, logger="unique_toolkit"):
        result, replaced = _replace_dangling_sandbox_links(text, error_msg)

    assert replaced is True
    assert error_msg in result
    assert "sandbox:/mnt/data/chart.png" not in result
    assert any(
        "sandbox:/mnt/data/chart.png" in r.message and r.levelno == logging.WARNING
        for r in caplog.records
    )


@pytest.mark.ai
def test_replace_dangling_sandbox_links__no_change__when_no_sandbox_link(
    caplog,
) -> None:
    """
    Purpose: Verify no replacement or WARNING when the text contains no dangling
    sandbox links.
    """
    text = "Here is your result: ````imgWithSource(contentId='cont_1')````"
    error_msg = "⚠️ File download failed ..."

    with caplog.at_level(logging.WARNING, logger="unique_toolkit"):
        result, replaced = _replace_dangling_sandbox_links(text, error_msg)

    assert replaced is False
    assert result == text
    assert not any(r.levelno == logging.WARNING for r in caplog.records)


# ============================================================================
# Tests for _warn_unmatched_code_blocks
# ============================================================================


@pytest.mark.ai
def test_warn_unmatched_code_blocks__logs_warning__when_file_not_in_any_block(
    caplog,
) -> None:
    """
    Purpose: Verify a WARNING is emitted when an uploaded file (with a valid content_id)
    is not present in any code block.
    Why this matters: This means the file won't receive a fence when FF=on.  It will
    appear as a plain download link and the frontend artifact UI won't be shown.
    The warning tells the operator the query should be re-run.
    Setup summary: content_map has one file; code_blocks is empty; assert warning.
    """
    content_map: dict[str, str | None] = {"report.xlsx": "cont_abc"}
    code_blocks: list[CodeInterpreterBlock] = []

    with caplog.at_level(logging.WARNING, logger="unique_toolkit"):
        _warn_unmatched_code_blocks(content_map, code_blocks)

    assert any(
        "report.xlsx" in r.message and r.levelno == logging.WARNING
        for r in caplog.records
    )


@pytest.mark.ai
def test_warn_unmatched_code_blocks__no_warning__when_file_is_in_block(
    caplog,
) -> None:
    """
    Purpose: Verify no WARNING when the file is correctly matched to a code block.
    """
    content_map: dict[str, str | None] = {"chart.png": "cont_img1"}
    code_blocks = [
        CodeInterpreterBlock(
            code='plt.savefig("/mnt/data/chart.png")',
            files=[
                CodeInterpreterFile(
                    filename="chart.png", content_id="cont_img1", type="image"
                )
            ],
        )
    ]

    with caplog.at_level(logging.WARNING, logger="unique_toolkit"):
        _warn_unmatched_code_blocks(content_map, code_blocks)

    assert not any(r.levelno == logging.WARNING for r in caplog.records)


@pytest.mark.ai
def test_warn_unmatched_code_blocks__skips_none_content_ids(caplog) -> None:
    """
    Purpose: Verify files whose upload failed (content_id=None) are silently skipped.
    Why this matters: Upload failures are already handled upstream; no double warning.
    """
    content_map: dict[str, str | None] = {"broken.xlsx": None}
    code_blocks: list[CodeInterpreterBlock] = []

    with caplog.at_level(logging.WARNING, logger="unique_toolkit"):
        _warn_unmatched_code_blocks(content_map, code_blocks)

    assert not any(r.levelno == logging.WARNING for r in caplog.records)
