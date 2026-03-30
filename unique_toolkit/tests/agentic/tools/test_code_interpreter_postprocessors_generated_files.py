"""Tests for code interpreter generated-files postprocessor (config, __init__, helpers)."""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

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
    _collect_stdout,
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
from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.schemas import ResponsesLanguageModelStreamResponse

GEN_FILES_FF = "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.generated_files.feature_flags"


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
def test_get_next_ref_number__returns_one__when_references_none() -> None:
    """Message.references may be None before postprocessing; treat like no refs."""
    assert gen_mod._get_next_ref_number(None) == 1


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
    Purpose: Verify sandbox HTML link replaced by HtmlRendering block with correct single blank line.
    Why this matters: HTML files are rendered in chat via special block; exact format matters.
    Setup summary: Link at start of line — no leading newline injected.
    """
    text = "[report](sandbox:/mnt/data/report.html)"
    content_id = "html-content-456"

    new_text, replaced = gen_mod._replace_container_html_citation(
        text, filename="report.html", content_id=content_id
    )

    assert replaced is True
    assert "sandbox" not in new_text
    expected_block = (
        f"```HtmlRendering\n800px\n600px\n\nunique://content/{content_id}\n\n```"
    )
    assert expected_block in new_text


@pytest.mark.ai
def test_replace_container_html_citation__inline_link__starts_on_new_line() -> None:
    """
    Purpose: Verify that when the sandbox link is mid-line (e.g. in a list item), the
    HtmlRendering block is placed on a new line so the frontend parser can detect it.
    Why this matters: LLMs often write "3. Dashboard: [link](sandbox://...)" — without
    a leading newline the HtmlRendering fence is inline and fails to render.
    """
    text = (
        "3. **HTML Dashboard**: [View the dashboard](sandbox:/mnt/data/dashboard.html) "
    )
    content_id = "cid-dash"

    new_text, replaced = gen_mod._replace_container_html_citation(
        text, filename="dashboard.html", content_id=content_id
    )

    assert replaced is True
    assert "sandbox" not in new_text
    # Block must be preceded by a newline (not inline after the label)
    block = f"```HtmlRendering\n800px\n600px\n\nunique://content/{content_id}\n\n```"
    assert "\n" + block in new_text
    # Label is preserved before the block
    assert "3. **HTML Dashboard**:" in new_text


@pytest.mark.ai
def test_replace_container_html_citation__indented_link_only_line__flushes_fence_left() -> (
    None
):
    """
    Purpose: List continuations often use two spaces then the sandbox link alone on
    the line. Replacing only the link left `` ```HtmlRendering `` indented; parsers
    require a column-0 fence. The full whitespace+link line must become the block.
    """
    text = (
        "- 📊 HTML dashboard:\n\n"
        "  [VIX Analytics Dashboard (HTML)](sandbox:/mnt/data/vix_dashboard.html)\n"
    )
    content_id = "cid-html"
    new_text, replaced = gen_mod._replace_container_html_citation(
        text, filename="vix_dashboard.html", content_id=content_id
    )

    assert replaced is True
    assert "sandbox" not in new_text
    assert "  ```HtmlRendering" not in new_text
    block = f"```HtmlRendering\n800px\n600px\n\nunique://content/{content_id}\n\n```"
    assert block in new_text


@pytest.mark.ai
def test_replace_container_html_citation__blank_lines_before_link__are_stripped() -> (
    None
):
    """
    Purpose: When the link is on its own indented line, any whitespace-only lines
    immediately before it (common list separator lines like '  \\n') must also be
    consumed so they don't appear as orphaned blank lines above the HtmlRendering block.
    """
    text = (
        "- HTML dashboard (open in your browser):\n"
        "  \n"
        "  [Dashboard](sandbox:/mnt/data/dash.html)\n"
        "- Next item\n"
    )
    content_id = "cid-blank"
    new_text, replaced = gen_mod._replace_container_html_citation(
        text, filename="dash.html", content_id=content_id
    )
    block = f"```HtmlRendering\n800px\n600px\n\nunique://content/{content_id}\n\n```"
    assert replaced is True
    assert "sandbox" not in new_text
    assert "  ```HtmlRendering" not in new_text
    assert block in new_text
    # The orphaned '  \n' must not appear between the label and the block
    assert "  \n" + block not in new_text


@pytest.mark.ai
def test_replace_container_html_citation__mid_line_followed_by_more_text__trailing_newline() -> (
    None
):
    """
    Purpose: When the link is mid-line and is followed immediately by more text
    (no newline), the closing ``` must still be followed by a newline so subsequent
    content starts on a fresh line.
    """
    text = "Dashboard: [d](sandbox:/mnt/data/d.html)More text here"
    content_id = "cid-trail"
    new_text, replaced = gen_mod._replace_container_html_citation(
        text, filename="d.html", content_id=content_id
    )
    block = f"```HtmlRendering\n800px\n600px\n\nunique://content/{content_id}\n\n```"
    assert replaced is True
    assert "sandbox" not in new_text
    assert block + "\n" in new_text or new_text.endswith(block)


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


def _make_display_files_postprocessor(
    company_id: str = "co-test",
) -> DisplayCodeInterpreterFilesPostProcessor:
    config = DisplayCodeInterpreterFilesPostProcessorConfig()
    return DisplayCodeInterpreterFilesPostProcessor(
        client=MagicMock(),
        content_service=MagicMock(),
        config=config,
        chat_service=MagicMock(),
        company_id=company_id,
        user_id="u1",
        chat_id="ch1",
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


@pytest.mark.ai
def test_build_code_blocks__assigns_images_via_stem__when_helper_function_constructs_path() -> (
    None
):
    """
    Purpose: Verify secondary (stem) matching assigns images saved via a helper function.
    Why this matters: A common LLM pattern is to define a save_fig(fig, name) helper that
    builds the path as f"/mnt/data/{name}.png" at runtime. The literal path
    "/mnt/data/nvda_price_sma.png" is never in the code — only the stem "nvda_price_sma"
    appears as a quoted string. Without secondary matching these images are silently dropped
    from code_blocks and never get an imgWithSource fence (the UN-17972 edge case).
    Setup summary: Code has save_fig(fig, "nvda_price_sma") with no literal /mnt/data/ path;
    assert the file is assigned to that block.
    """
    code = (
        "def save_fig(fig, name):\n"
        '    out = f"/mnt/data/{name}.png"\n'
        "    fig.savefig(out, dpi=160)\n\n"
        'save_fig(fig, "nvda_price_sma")\n'
        'save_fig(fig, "nvda_volume")\n'
    )
    call = _make_ci_call(code)
    ann1 = _make_annotation("nvda_price_sma.png", file_id="cfile_1")
    ann2 = _make_annotation("nvda_volume.png", file_id="cfile_2")
    content_map = {
        "nvda_price_sma.png": "cont_img1",
        "nvda_volume.png": "cont_img2",
    }
    response = _make_response([call], [ann1, ann2])

    result = _build_code_blocks(response, content_map)

    assert len(result) == 1
    filenames = {f.filename for f in result[0].files}
    assert filenames == {"nvda_price_sma.png", "nvda_volume.png"}
    assert all(f.type == "image" for f in result[0].files)


@pytest.mark.ai
def test_build_code_blocks__assigns_images_via_full_filename__when_helper_passes_filename_with_extension() -> (
    None
):
    """
    Purpose: Verify secondary matching via full filename (Pattern B).
    Why this matters: A second common LLM pattern passes the full filename (with extension)
    to a helper that builds the path with os.path.join, e.g.:
        make_chart(kind, "random_line_chart.png", 42)
        fig.savefig(os.path.join(output_dir, filename), ...)
    The literal "/mnt/data/random_line_chart.png" is never in the code, but
    "random_line_chart.png" IS quoted. Without full-filename matching these images
    are silently dropped (the edge case confirmed in UI testing on 2026-03-18).
    Setup summary: Code has "random_line_chart.png" as a quoted argument; no literal
    /mnt/data/ path; assert the file is assigned to that block.
    """
    code = (
        "charts = [\n"
        '    ("line", "random_line_chart.png", 42),\n'
        '    ("bar", "random_bar_chart.png", 123),\n'
        "]\n"
        "for kind, fname, seed in charts:\n"
        "    make_chart(kind, fname, seed=seed)\n\n"
        "def make_chart(kind, filename, seed=None):\n"
        '    fig.savefig(os.path.join(output_dir, filename), bbox_inches="tight")\n'
    )
    call = _make_ci_call(code)
    ann1 = _make_annotation("random_line_chart.png", file_id="cfile_1")
    ann2 = _make_annotation("random_bar_chart.png", file_id="cfile_2")
    content_map = {
        "random_line_chart.png": "cont_img1",
        "random_bar_chart.png": "cont_img2",
    }
    response = _make_response([call], [ann1, ann2])

    result = _build_code_blocks(response, content_map)

    assert len(result) == 1
    filenames = {f.filename for f in result[0].files}
    assert filenames == {"random_line_chart.png", "random_bar_chart.png"}
    assert all(f.type == "image" for f in result[0].files)


@pytest.mark.ai
def test_build_code_blocks__assigns_images_via_last_block_fallback__when_name_fully_dynamic() -> (
    None
):
    """
    Purpose: Verify last-resort fallback (Step 1c) assigns images whose names are
    assembled entirely at runtime via f-strings or variable concatenation.
    Why this matters: Pattern C — e.g. f"/mnt/data/chart_{chart_type}_{i}.png" —
    produces filenames like "chart_line_0.png" where neither the full path, the full
    filename, nor the stem appears as a quoted string literal anywhere in the code.
    Neither primary nor secondary matching succeeds; the fallback must kick in.
    Setup summary: Code constructs filenames with an f-string loop; no quoted static
    token matches; assert all files are assigned to the single (last) code block.
    """
    code = (
        'chart_types = ["line", "bar"]\n'
        "for i, chart_type in enumerate(chart_types):\n"
        '    filename = f"/mnt/data/chart_{chart_type}_{i}.png"\n'
        "    create_and_save_chart(chart_type, filename)\n"
    )
    call = _make_ci_call(code)
    ann1 = _make_annotation("chart_line_0.png", file_id="cfile_1")
    ann2 = _make_annotation("chart_bar_1.png", file_id="cfile_2")
    content_map = {
        "chart_line_0.png": "cont_img1",
        "chart_bar_1.png": "cont_img2",
    }
    response = _make_response([call], [ann1, ann2])

    result = _build_code_blocks(response, content_map)

    assert len(result) == 1
    filenames = {f.filename for f in result[0].files}
    assert filenames == {"chart_line_0.png", "chart_bar_1.png"}
    assert all(f.type == "image" for f in result[0].files)


@pytest.mark.ai
def test_build_code_blocks__secondary_last_writer_wins__when_two_blocks_match_stem() -> (
    None
):
    """
    Purpose: Verify secondary matching uses last-writer-wins across blocks, like primary.
    Why this matters: If block 0 and block 1 both reference the same stem (no literal
    /mnt/data/{filename} in either), the file must be owned by the last block — not the first.
    Setup summary: Two calls each with save(fig, "plot") pattern; assert plot.png maps to block 1.
    """
    code0 = 'def save(f, n):\n    f.savefig(f"/mnt/data/{n}.png")\nsave(fig, "plot")\n'
    code1 = (
        "def save(f, n):\n"
        '    f.savefig(f"/mnt/data/{n}.png")\n'
        'save(fig, "plot")  # final write\n'
    )
    call0 = _make_ci_call(code0, container_id="cntr_1")
    call1 = _make_ci_call(code1, container_id="cntr_1")
    annotation = _make_annotation("plot.png", file_id="cfile_1")
    content_map = {"plot.png": "cont_img1"}
    response = _make_response([call0, call1], [annotation])

    result = _build_code_blocks(response, content_map)

    assert len(result) == 1
    assert result[0].code == call1.code
    assert result[0].files[0].filename == "plot.png"


@pytest.mark.ai
def test_build_code_blocks__primary_match_beats_stem__when_both_present() -> None:
    """
    Purpose: Verify primary (literal path) match takes precedence over secondary (stem) match.
    Why this matters: If a later block has the stem but an earlier block has the full literal
    path, the earlier block should own the file (primary wins regardless of order).
    Setup summary: Block 0 has literal path; block 1 has stem only; file should go to block 0.
    """
    call0 = _make_ci_call('plt.savefig("/mnt/data/chart.png")', container_id="cntr_1")
    call1 = _make_ci_call('save_fig(fig, "chart")', container_id="cntr_1")
    annotation = _make_annotation("chart.png", file_id="cfile_1")
    content_map = {"chart.png": "cont_img1"}
    response = _make_response([call0, call1], [annotation])

    result = _build_code_blocks(response, content_map)

    assert len(result) == 1
    assert result[0].code == call0.code


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
def test_build_file_fence__html__falls_through_to_fileWithSource() -> None:
    """
    Purpose: HTML files now fall through to fileWithSource in _build_file_fence.
    Why this matters: HTML is rendered via HtmlRendering blocks (not fence injection),
    so this function should never be called for HTML in practice, but if it is the
    fallback is a fileWithSource fence rather than the removed htmlWithSource branch.
    """
    file = CodeInterpreterFile(
        filename="report.html", content_id="cont_html1", type="html"
    )
    fence = _build_file_fence(
        file, 'open("/mnt/data/report.html", "w").write("<html></html>")', fence_id=3
    )
    assert fence.startswith("````fileWithSource(")
    assert "cont_html1" in fence
    assert "htmlWithSource" not in fence


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
def test_inject_code_execution_fences__html_file__is_not_injected() -> None:
    """
    Purpose: HTML files are rendered via HtmlRendering blocks (not fence injection),
    so an HTML block passed to _inject_code_execution_fences leaves the text unchanged.
    Why this matters: In normal flow HTML never reaches fence injection — this guards
    against accidental regressions where an htmlWithSource fence is emitted.
    """
    block = CodeInterpreterBlock(
        code='open("/mnt/data/page.html", "w").write("<html></html>")',
        files=[
            CodeInterpreterFile(
                filename="page.html", content_id="cont_html1", type="html"
            )
        ],
    )
    # HTML produces no unique://content inline ref (it was replaced by HtmlRendering),
    # so there is nothing for the injector to match.
    text = "```HtmlRendering\nunique://content/cont_html1\n```"

    result = _inject_code_execution_fences(text, [block])

    assert "htmlWithSource" not in result
    assert "HtmlRendering" in result
    assert "cont_html1" in result


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
            text="No link here.",
            filename="data.csv",
            content_id="cont_y",
            ref_number=1,
            use_content_link=False,
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


# ============================================================================
# Tests for _collect_stdout
# ============================================================================


def _make_logs_output(logs: str) -> MagicMock:
    """Build a mock output item with type='logs' and the given logs string."""
    output = MagicMock()
    output.type = "logs"
    output.logs = logs
    return output


def _make_image_output() -> MagicMock:
    """Build a mock output item with type='image' (should be ignored by _collect_stdout)."""
    output = MagicMock()
    output.type = "image"
    return output


def _make_call(outputs: list | None) -> ResponseCodeInterpreterToolCall:
    """Build a minimal ResponseCodeInterpreterToolCall with the given outputs list."""
    call = MagicMock(spec=ResponseCodeInterpreterToolCall)
    call.outputs = outputs
    return call


@pytest.mark.ai
def test_collect_stdout__returns_empty_string__when_outputs_is_none() -> None:
    """
    Purpose: Verify _collect_stdout returns '' when the call has no outputs (include not set).
    Why this matters: When the Responses API is called without include=["code_interpreter_call.outputs"],
    call.outputs is None; we must not crash and must fall back to source code.
    """
    call = _make_call(outputs=None)
    assert _collect_stdout(call) == ""


@pytest.mark.ai
def test_collect_stdout__returns_empty_string__when_outputs_is_empty_list() -> None:
    """
    Purpose: Verify _collect_stdout returns '' for an empty outputs list.
    Why this matters: Empty list is a valid API response when code produces no stdout.
    """
    call = _make_call(outputs=[])
    assert _collect_stdout(call) == ""


@pytest.mark.ai
def test_collect_stdout__returns_logs__when_single_logs_output() -> None:
    """
    Purpose: Verify _collect_stdout extracts the logs text from a single logs output item.
    Why this matters: Core happy-path: stdout from a print() call should become the txt content.
    """
    call = _make_call(outputs=[_make_logs_output("Hello, world!")])
    assert _collect_stdout(call) == "Hello, world!"


@pytest.mark.ai
def test_collect_stdout__joins_multiple_logs_outputs__with_newline() -> None:
    """
    Purpose: Verify _collect_stdout joins multiple logs outputs with newlines.
    Why this matters: Code interpreter may emit several log chunks; they must be
    concatenated in order so the txt file is readable.
    """
    call = _make_call(
        outputs=[
            _make_logs_output("line 1"),
            _make_logs_output("line 2"),
            _make_logs_output("line 3"),
        ]
    )
    assert _collect_stdout(call) == "line 1\nline 2\nline 3"


@pytest.mark.ai
def test_collect_stdout__ignores_non_logs_outputs() -> None:
    """
    Purpose: Verify _collect_stdout skips image (and other non-logs) output items.
    Why this matters: Code interpreter outputs can include images; those must not
    be included in the stdout text.
    """
    call = _make_call(
        outputs=[
            _make_logs_output("stdout text"),
            _make_image_output(),
        ]
    )
    assert _collect_stdout(call) == "stdout text"


# ============================================================================
# Tests for orphan path, _get_next_fence_id, _build_orphan_fences, run()
# ============================================================================


@pytest.mark.ai
def test_get_next_fence_id__returns_one__when_no_fences_in_text() -> None:
    assert gen_mod._get_next_fence_id("plain text") == 1


@pytest.mark.ai
def test_get_next_fence_id__returns_max_plus_one__when_fences_in_text() -> None:
    text = "x ````fileWithSource(id='2', contentId='a')```` y ````imgWithSource(id='5', contentId='b')````"
    assert gen_mod._get_next_fence_id(text) == 6


@pytest.mark.ai
def test_build_orphan_fences__concatenates_file_fences() -> None:
    f = CodeInterpreterFile(filename="code.txt", content_id="cid1", type="document")
    block = CodeInterpreterBlock(code="print(1)", files=[f])
    out = gen_mod._build_orphan_fences([block], start_fence_id=1)
    assert "fileWithSource" in out
    assert "cid1" in out
    assert "print(1)" in out or "\\n" in out  # code may be escaped in fence


@pytest.mark.ai
@patch(GEN_FILES_FF)
def test_apply_postprocessing__normalizes_none_message_text__to_empty_string(
    mock_ff: MagicMock,
) -> None:
    """
    Purpose: `apply_postprocessing_to_response` must coerce `message.text` None to ''.
    Why this matters: Downstream regex/replace assumes a string; Responses payloads can
    omit text until postprocessing.
    """
    mock_ff.enable_code_execution_fence_un_17972.is_enabled.return_value = False
    config = DisplayCodeInterpreterFilesPostProcessorConfig()
    proc = DisplayCodeInterpreterFilesPostProcessor(
        client=MagicMock(),
        content_service=MagicMock(),
        config=config,
        chat_service=MagicMock(),
        company_id="company-null-text",
    )
    proc._content_map = {}
    proc._orphan_code_blocks = []
    msg = ChatMessage(
        chat_id="c1",
        role=ChatMessageRole.ASSISTANT,
        content=None,
        references=[],
    )
    loop = ResponsesLanguageModelStreamResponse(message=msg, output=[])
    proc.apply_postprocessing_to_response(loop)
    assert msg.text == ""


@pytest.mark.ai
@patch(GEN_FILES_FF)
def test_apply_postprocessing__orphan_path_appends_fence_but_not_references__when_ff_on(
    mock_ff: MagicMock,
) -> None:
    """
    Purpose: Orphan blocks get fence text but NO ContentReference entries when fence FF is on.
    Why this matters: Orphan artifacts are rendered via fences in message.text; adding them
    to references would surface them as source citations, which is semantically wrong.
    Setup summary: One orphan block with a document file, fence FF ON; assert fence text
    added and references remain empty.
    """
    mock_ff.enable_code_execution_fence_un_17972.is_enabled.return_value = True
    config = DisplayCodeInterpreterFilesPostProcessorConfig()
    proc = DisplayCodeInterpreterFilesPostProcessor(
        client=MagicMock(),
        content_service=MagicMock(),
        config=config,
        chat_service=MagicMock(),
        company_id="company-orphan",
    )
    proc._content_map = {}
    orphan_file = CodeInterpreterFile(
        filename="code.txt", content_id="cont_orphan", type="document"
    )
    proc._orphan_code_blocks = [
        CodeInterpreterBlock(code="print('hi')", files=[orphan_file]),
    ]
    msg = ChatMessage(
        chat_id="c1",
        role=ChatMessageRole.ASSISTANT,
        content="Hello",
        references=None,
    )
    loop = ResponsesLanguageModelStreamResponse(message=msg, output=[])
    changed = proc.apply_postprocessing_to_response(loop)
    assert changed is True
    assert msg.text is not None
    assert "fileWithSource" in msg.text
    assert msg.references == []


@pytest.mark.ai
@patch(GEN_FILES_FF)
def test_apply_postprocessing__ff_on__does_not_append_reference_for_non_image_file(
    mock_ff: MagicMock,
) -> None:
    """
    Purpose: When fence FF is ON, non-image files must NOT be added to message.references.
    Why this matters: Files are rendered as fence blocks in message.text; references entries
    would incorrectly surface them as source citations in the references panel.
    Setup summary: One .pdf with sandbox link, fence FF ON; assert references stays empty.
    """
    mock_ff.enable_code_execution_fence_un_17972.is_enabled.return_value = True
    mock_ff.enable_html_rendering_un_15131.is_enabled.return_value = False
    config = DisplayCodeInterpreterFilesPostProcessorConfig()
    proc = DisplayCodeInterpreterFilesPostProcessor(
        client=MagicMock(),
        content_service=MagicMock(),
        config=config,
        chat_service=MagicMock(),
        company_id="company-fence-on",
    )
    proc._content_map = {"report.pdf": "cid-pdf-1"}
    proc._orphan_code_blocks = []
    message = SimpleNamespace(
        text="See [report.pdf](sandbox:/mnt/data/report.pdf) for details.",
        references=[],
    )
    loop_response = SimpleNamespace(
        message=message,
        container_files=[],
        code_interpreter_calls=[],
    )
    proc.apply_postprocessing_to_response(loop_response)
    assert message.references == []


@pytest.mark.ai
@patch(GEN_FILES_FF)
def test_apply_postprocessing__ff_off__appends_reference_for_non_image_file(
    mock_ff: MagicMock,
) -> None:
    """
    Purpose: When fence FF is OFF, non-image files must still be added to message.references.
    Why this matters: The legacy references UI uses these entries for download/open actions.
    Setup summary: One .pdf with sandbox link, fence FF OFF; assert one ContentReference appended.
    """
    mock_ff.enable_code_execution_fence_un_17972.is_enabled.return_value = False
    mock_ff.enable_html_rendering_un_15131.is_enabled.return_value = False
    config = DisplayCodeInterpreterFilesPostProcessorConfig()
    proc = DisplayCodeInterpreterFilesPostProcessor(
        client=MagicMock(),
        content_service=MagicMock(),
        config=config,
        chat_service=MagicMock(),
        company_id="company-fence-off",
    )
    proc._content_map = {"report.pdf": "cid-pdf-1"}
    proc._orphan_code_blocks = []
    message = SimpleNamespace(
        text="See [report.pdf](sandbox:/mnt/data/report.pdf) for details.",
        references=[],
    )
    loop_response = SimpleNamespace(
        message=message,
        container_files=[],
        code_interpreter_calls=[],
    )
    proc.apply_postprocessing_to_response(loop_response)
    assert len(message.references) == 1
    ref = message.references[0]
    assert ref.source_id == "cid-pdf-1"
    assert ref.name == "report.pdf"


@pytest.mark.ai
@patch(GEN_FILES_FF)
def test_apply_postprocessing__ff_off__existing_citation_refs_preserved(
    mock_ff: MagicMock,
) -> None:
    """
    Purpose: Pre-existing (ingestion/citation) references are preserved when fence FF is OFF
    and a new artifact reference is appended alongside them.
    Why this matters: Regression check — the fix must not disturb existing non-artifact refs.
    Setup summary: One pre-existing ContentReference; one .xlsx with sandbox link; FF OFF.
    Assert both refs present after postprocessing.
    """
    mock_ff.enable_code_execution_fence_un_17972.is_enabled.return_value = False
    mock_ff.enable_html_rendering_un_15131.is_enabled.return_value = False
    config = DisplayCodeInterpreterFilesPostProcessorConfig()
    proc = DisplayCodeInterpreterFilesPostProcessor(
        client=MagicMock(),
        content_service=MagicMock(),
        config=config,
        chat_service=MagicMock(),
        company_id="company-existing-refs",
    )
    proc._content_map = {"data.xlsx": "cid-xls-1"}
    proc._orphan_code_blocks = []
    existing_ref = ContentReference(
        name="source-doc",
        sequence_number=3,
        source="ingestion",
        source_id="existing-sid",
        url="unique://content/existing-sid",
    )
    message = SimpleNamespace(
        text="See [data.xlsx](sandbox:/mnt/data/data.xlsx).",
        references=[existing_ref],
    )
    loop_response = SimpleNamespace(
        message=message,
        container_files=[],
        code_interpreter_calls=[],
    )
    proc.apply_postprocessing_to_response(loop_response)
    assert len(message.references) == 2
    source_ids = {r.source_id for r in message.references}
    assert "existing-sid" in source_ids
    assert "cid-xls-1" in source_ids


@pytest.mark.ai
@pytest.mark.asyncio
@patch(GEN_FILES_FF)
async def test_run__populates_orphan_blocks__when_ff_on_and_no_container_files(
    mock_ff: MagicMock,
) -> None:
    mock_ff.enable_code_execution_fence_un_17972.is_enabled.return_value = True
    call = ResponseCodeInterpreterToolCall(
        id="call-1",
        container_id="ctr",
        status="completed",
        type="code_interpreter_call",
        code="print(42)",
    )
    msg = ChatMessage(
        chat_id="c1",
        role=ChatMessageRole.ASSISTANT,
        content="Hi",
    )
    loop = ResponsesLanguageModelStreamResponse(message=msg, output=[call])
    uploaded = MagicMock()
    uploaded.id = "cont_up"
    chat = AsyncMock()
    chat.upload_to_chat_from_bytes_async = AsyncMock(return_value=uploaded)
    proc = DisplayCodeInterpreterFilesPostProcessor(
        client=MagicMock(),
        content_service=MagicMock(),
        config=DisplayCodeInterpreterFilesPostProcessorConfig(),
        chat_service=chat,
        company_id="co1",
    )
    await proc.run(loop)
    assert len(proc._orphan_code_blocks) == 1
    assert proc._orphan_code_blocks[0].files[0].content_id == "cont_up"
    chat.upload_to_chat_from_bytes_async.assert_awaited()


@pytest.mark.ai
@pytest.mark.asyncio
@patch(GEN_FILES_FF)
async def test_run__clears_orphan_blocks__when_fence_ff_off(mock_ff: MagicMock) -> None:
    mock_ff.enable_code_execution_fence_un_17972.is_enabled.return_value = False
    call = ResponseCodeInterpreterToolCall(
        id="call-1",
        container_id="ctr",
        status="completed",
        type="code_interpreter_call",
        code="print(1)",
    )
    msg = ChatMessage(chat_id="c1", role=ChatMessageRole.ASSISTANT, content="Hi")
    loop = ResponsesLanguageModelStreamResponse(message=msg, output=[call])
    proc = DisplayCodeInterpreterFilesPostProcessor(
        client=MagicMock(),
        content_service=MagicMock(),
        config=DisplayCodeInterpreterFilesPostProcessorConfig(),
        chat_service=AsyncMock(),
        company_id="co1",
    )
    proc._orphan_code_blocks = [
        CodeInterpreterBlock(code="old", files=[]),
    ]
    await proc.run(loop)
    assert proc._orphan_code_blocks == []


@pytest.mark.ai
@pytest.mark.asyncio
@patch(GEN_FILES_FF)
async def test_run__orphan_upload_skips_calls_when_upload_fails(
    mock_ff: MagicMock,
) -> None:
    mock_ff.enable_code_execution_fence_un_17972.is_enabled.return_value = True
    call = ResponseCodeInterpreterToolCall(
        id="call-1",
        container_id="ctr",
        status="completed",
        type="code_interpreter_call",
        code="print(1)",
    )
    msg = ChatMessage(chat_id="c1", role=ChatMessageRole.ASSISTANT, content="Hi")
    loop = ResponsesLanguageModelStreamResponse(message=msg, output=[call])
    chat = AsyncMock()
    chat.upload_to_chat_from_bytes_async = AsyncMock(
        side_effect=RuntimeError("upload failed")
    )
    proc = DisplayCodeInterpreterFilesPostProcessor(
        client=MagicMock(),
        content_service=MagicMock(),
        config=DisplayCodeInterpreterFilesPostProcessorConfig(),
        chat_service=chat,
        company_id="co1",
    )
    await proc.run(loop)
    assert proc._orphan_code_blocks == []


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_orphan_code_as_txt__returns_empty_when_container_files_present() -> (
    None
):
    proc = DisplayCodeInterpreterFilesPostProcessor(
        client=MagicMock(),
        content_service=MagicMock(),
        config=DisplayCodeInterpreterFilesPostProcessorConfig(),
        chat_service=MagicMock(),
        company_id="co1",
    )
    lr = MagicMock(spec=ResponsesLanguageModelStreamResponse)
    lr.container_files = [MagicMock()]
    lr.code_interpreter_calls = []
    assert await proc._upload_orphan_code_as_txt(lr) == []


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_orphan_code_as_txt__returns_empty_when_no_calls() -> None:
    proc = DisplayCodeInterpreterFilesPostProcessor(
        client=MagicMock(),
        content_service=MagicMock(),
        config=DisplayCodeInterpreterFilesPostProcessorConfig(),
        chat_service=MagicMock(),
        company_id="co1",
    )
    lr = MagicMock(spec=ResponsesLanguageModelStreamResponse)
    lr.container_files = []
    lr.code_interpreter_calls = []
    assert await proc._upload_orphan_code_as_txt(lr) == []


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_orphan_code_as_txt__skips_call_without_code() -> None:
    proc = DisplayCodeInterpreterFilesPostProcessor(
        client=MagicMock(),
        content_service=MagicMock(),
        config=DisplayCodeInterpreterFilesPostProcessorConfig(),
        chat_service=MagicMock(),
        company_id="co1",
    )
    call_no_code = MagicMock(spec=ResponseCodeInterpreterToolCall)
    call_no_code.code = None
    lr = MagicMock(spec=ResponsesLanguageModelStreamResponse)
    lr.container_files = []
    lr.code_interpreter_calls = [call_no_code]
    assert await proc._upload_orphan_code_as_txt(lr) == []


@pytest.mark.ai
@pytest.mark.asyncio
@pytest.mark.parametrize("num_calls", [1, 2])
async def test_upload_orphan_code_as_txt__uploads_txt_uses_expected_filename(
    num_calls: int,
) -> None:
    """Single call → code.txt; multiple calls → code_1.txt, code_2.txt."""
    calls = [
        ResponseCodeInterpreterToolCall(
            id=f"call-{i}",
            container_id="ctr",
            status="completed",
            type="code_interpreter_call",
            code=f"print({i})",
        )
        for i in range(num_calls)
    ]
    lr = MagicMock(spec=ResponsesLanguageModelStreamResponse)
    lr.container_files = []
    lr.code_interpreter_calls = calls
    chat = AsyncMock()

    async def _upload(**kwargs):
        m = MagicMock()
        m.id = f"id-{kwargs.get('content_name', '')}"
        return m

    chat.upload_to_chat_from_bytes_async = AsyncMock(side_effect=_upload)
    proc = DisplayCodeInterpreterFilesPostProcessor(
        client=MagicMock(),
        content_service=MagicMock(),
        config=DisplayCodeInterpreterFilesPostProcessorConfig(),
        chat_service=chat,
        company_id="co1",
    )
    blocks = await proc._upload_orphan_code_as_txt(lr)
    assert len(blocks) == num_calls
    if num_calls == 1:
        chat.upload_to_chat_from_bytes_async.assert_awaited_once()
        assert blocks[0].files[0].filename == "code.txt"
    else:
        assert {blocks[i].files[0].filename for i in range(2)} == {
            "code_1.txt",
            "code_2.txt",
        }


@pytest.mark.ai
@patch(
    "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors."
    "generated_files.feature_flags.enable_html_rendering_un_15131.is_enabled",
    return_value=True,
)
@patch(
    "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors."
    "generated_files.feature_flags.enable_code_execution_fence_un_17972.is_enabled",
    return_value=False,
)
def test_apply_postprocessing_to_response__html_uses_legacy_HtmlRendering__when_fence_ff_off(
    _mock_fence_ff: MagicMock,
    _mock_html_ff: MagicMock,
) -> None:
    """
    Purpose: HTML with fence FF off and HTML-rendering FF on uses _replace_container_html_citation.
    Why this matters: Covers the legacy HtmlRendering branch (UN-15131) in apply_postprocessing.
    """
    proc = _make_display_files_postprocessor()
    proc._content_map = {"report.html": "cid_html"}

    refs: list[ContentReference] = []
    message = SimpleNamespace(
        text="[Download](sandbox:/mnt/data/report.html)",
        references=refs,
    )
    loop_response = SimpleNamespace(
        message=message,
        container_files=[],
        code_interpreter_calls=[],
    )

    changed = proc.apply_postprocessing_to_response(loop_response)

    assert changed is True
    assert "HtmlRendering" in message.text
    assert "unique://content/cid_html" in message.text
    assert len(refs) == 0


@pytest.mark.ai
@patch(
    "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors."
    "generated_files.feature_flags.enable_html_rendering_un_15131.is_enabled",
    return_value=False,
)
@patch(
    "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors."
    "generated_files.feature_flags.enable_code_execution_fence_un_17972.is_enabled",
    return_value=True,
)
def test_apply_postprocessing_to_response__html_with_fence_ff_on__uses_HtmlRendering(
    _mock_fence_ff: MagicMock,
    _mock_html_ff: MagicMock,
) -> None:
    """
    Purpose: HTML + fence FF on now emits a HtmlRendering block (not htmlWithSource).
    Why this matters: Product revert — HTML always goes through _replace_container_html_citation
    regardless of fence FF state; no ContentReference row is added.
    """
    proc = _make_display_files_postprocessor()
    proc._content_map = {"page.html": "cid_page"}

    refs: list[ContentReference] = []
    message = SimpleNamespace(
        text="[page.html](sandbox:/mnt/data/page.html)",
        references=refs,
    )
    call = _make_ci_call('open("/mnt/data/page.html", "w").write("x")')
    ann = _make_annotation("page.html", file_id="f_html", container_id="cntr_x")
    loop_response = SimpleNamespace(
        message=message,
        container_files=[ann],
        code_interpreter_calls=[call],
    )

    changed = proc.apply_postprocessing_to_response(loop_response)

    assert changed is True
    assert len(refs) == 0
    assert "HtmlRendering" in message.text
    assert "cid_page" in message.text
    assert "htmlWithSource" not in message.text
