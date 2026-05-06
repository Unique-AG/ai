"""
Unit tests for pandoc_converter module.
"""

from pathlib import Path

import pytest

from unique_toolkit._common.docx_generator.pandoc_converter import (
    pandoc_markdown_to_docx,
    pandoc_markdown_to_docx_async,
)

# Minimal DOCX magic bytes (ZIP format)
_DOCX_MAGIC = b"PK\x03\x04"


def _fake_convert_write_output(
    source: str, to: str, format: str, outputfile: str, **kwargs: object
) -> None:
    """Side-effect that writes fake docx bytes to outputfile for mock."""
    Path(outputfile).write_bytes(_DOCX_MAGIC)


@pytest.mark.ai
def test_pandoc_markdown_to_docx__returns_bytes__without_template(mocker) -> None:
    """
    Purpose: Ensure conversion without template returns DOCX bytes.
    Why this matters: Core conversion path must work with pandoc defaults.
    Setup summary: Mock pypandoc to write fake docx; assert returned bytes.
    """
    # Arrange
    mocker.patch(
        "unique_toolkit._common.docx_generator.pandoc_converter.pypandoc.convert_text",
        side_effect=_fake_convert_write_output,
    )
    source = "# Hello\n\nWorld"

    # Act
    result = pandoc_markdown_to_docx(source, template=None)

    # Assert
    assert isinstance(result, bytes)
    assert result.startswith(_DOCX_MAGIC)


@pytest.mark.ai
def test_pandoc_markdown_to_docx__passes_reference_doc__with_path_template(
    mocker, tmp_path: Path
) -> None:
    """
    Purpose: Verify Path template passes --reference-doc to pandoc.
    Why this matters: Reference doc styling must be applied when template is provided.
    Setup summary: Mock convert_text, call with Path template, assert extra_args.
    """
    # Arrange
    template_path = tmp_path / "ref.docx"
    template_path.write_bytes(_DOCX_MAGIC)

    mock_convert = mocker.patch(
        "unique_toolkit._common.docx_generator.pandoc_converter.pypandoc.convert_text",
        side_effect=_fake_convert_write_output,
    )

    # Act
    pandoc_markdown_to_docx("# Hi", template=template_path)

    # Assert
    mock_convert.assert_called_once()
    call_kwargs = mock_convert.call_args.kwargs
    extra_args = call_kwargs.get("extra_args", [])
    assert any("--reference-doc=" in str(a) for a in extra_args)
    assert str(template_path) in str(extra_args)


@pytest.mark.ai
def test_pandoc_markdown_to_docx__passes_reference_doc__with_str_template(
    mocker, tmp_path: Path
) -> None:
    """
    Purpose: Verify str template passes --reference-doc to pandoc.
    Why this matters: Callers may pass string paths; must be supported.
    Setup summary: Mock convert_text, call with str path, assert extra_args.
    """
    # Arrange
    template_path = tmp_path / "ref.docx"
    template_path.write_bytes(_DOCX_MAGIC)

    mock_convert = mocker.patch(
        "unique_toolkit._common.docx_generator.pandoc_converter.pypandoc.convert_text",
        side_effect=_fake_convert_write_output,
    )

    # Act
    pandoc_markdown_to_docx("# Hi", template=str(template_path))

    # Assert
    mock_convert.assert_called_once()
    call_kwargs = mock_convert.call_args.kwargs
    extra_args = call_kwargs.get("extra_args", [])
    assert any("--reference-doc=" in str(a) for a in extra_args)


@pytest.mark.ai
def test_pandoc_markdown_to_docx__passes_reference_doc__with_bytes_template(
    mocker,
) -> None:
    """
    Purpose: Verify bytes template is written to temp file and passed to pandoc.
    Why this matters: In-memory templates (e.g. from KB) must be correctly handled.
    Setup summary: Mock convert_text, call with bytes template; assert --reference-doc passed.
    """
    # Arrange
    template_bytes = b"PK\x03\x04fake_docx_content"

    mock_convert = mocker.patch(
        "unique_toolkit._common.docx_generator.pandoc_converter.pypandoc.convert_text",
        side_effect=_fake_convert_write_output,
    )

    # Act
    result = pandoc_markdown_to_docx("# Hi", template=template_bytes)

    # Assert (temp dir is torn down after return, so we verify args only)
    assert result.startswith(_DOCX_MAGIC)
    mock_convert.assert_called_once()
    call_kwargs = mock_convert.call_args.kwargs
    extra_args = call_kwargs.get("extra_args", [])
    assert len(extra_args) == 1
    ref_arg = extra_args[0]
    assert ref_arg.startswith("--reference-doc=")
    ref_path = Path(ref_arg.split("=", 1)[1])
    assert ref_path.name == "ref.docx"


@pytest.mark.ai
def test_pandoc_markdown_to_docx__passes_source_to_pandoc(mocker) -> None:
    """
    Purpose: Verify markdown source is passed correctly to pandoc.
    Why this matters: Content integrity depends on correct source being converted.
    Setup summary: Mock convert_text, call with known source, assert source in call.
    """
    # Arrange
    mock_convert = mocker.patch(
        "unique_toolkit._common.docx_generator.pandoc_converter.pypandoc.convert_text",
        side_effect=_fake_convert_write_output,
    )
    source = "# Title\n\n**Bold** and *italic*"

    # Act
    pandoc_markdown_to_docx(source)

    # Assert
    call_args = mock_convert.call_args
    assert call_args.args[0] == source
    assert call_args.kwargs["to"] == "docx"
    assert call_args.kwargs["format"] == "md"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_pandoc_markdown_to_docx_async__returns_same_as_sync(mocker) -> None:
    """
    Purpose: Verify async wrapper returns identical result to sync function.
    Why this matters: Async API must preserve conversion behavior.
    Setup summary: Mock convert_text, call sync and async, assert same output.
    """
    # Arrange
    mocker.patch(
        "unique_toolkit._common.docx_generator.pandoc_converter.pypandoc.convert_text",
        side_effect=_fake_convert_write_output,
    )
    source = "# Async test"

    # Act
    sync_result = pandoc_markdown_to_docx(source)
    async_result = await pandoc_markdown_to_docx_async(source)

    # Assert
    assert sync_result == async_result
    assert async_result.startswith(_DOCX_MAGIC)


class TestPandocConverterIntegration:
    """Integration tests requiring real pandoc. Skipped when pandoc unavailable."""

    @pytest.fixture
    def template_dir(self) -> Path:
        """Path to docx_generator template directory."""
        return (
            Path(__file__).resolve().parent.parent.parent
            / "unique_toolkit"
            / "_common"
            / "docx_generator"
            / "template"
        )

    @pytest.fixture
    def report_md_path(self, template_dir: Path) -> Path | None:
        """Path to report.md in template folder, or None if missing."""
        path = template_dir / "report.md"
        return path if path.exists() else None

    def _pandoc_available(self) -> bool:
        try:
            import pypandoc

            pypandoc.get_pandoc_version()
            return True
        except OSError:
            return False

    @pytest.mark.ai
    def test_pandoc_markdown_to_docx__produces_valid_docx__simple_markdown(
        self,
    ) -> None:
        """
        Purpose: Verify real conversion produces valid DOCX (ZIP) output.
        Why this matters: End-to-end sanity check when pandoc is installed.
        Setup summary: Call conversion with simple markdown, no template; assert PK header.
        """
        if not self._pandoc_available():
            pytest.skip("pandoc not installed")

        # Arrange
        source = "# Title\n\nHello, world."

        # Act
        result = pandoc_markdown_to_docx(source, template=None)

        # Assert
        assert isinstance(result, bytes)
        assert len(result) > 100
        assert result.startswith(b"PK")

    @pytest.mark.ai
    def test_pandoc_markdown_to_docx__produces_valid_docx__with_path_template(
        self, tmp_path: Path
    ) -> None:
        """
        Purpose: Verify conversion with Path template produces valid DOCX.
        Why this matters: Template application must work in real usage.
        Setup summary: Create reference docx via pandoc, convert with it; assert valid output.
        """
        if not self._pandoc_available():
            pytest.skip("pandoc not installed")

        import pypandoc

        # Arrange: create minimal reference docx
        ref_path = tmp_path / "ref.docx"
        pypandoc.convert_text(" ", to="docx", format="md", outputfile=str(ref_path))
        source = "# Test\n\nContent"

        # Act
        result = pandoc_markdown_to_docx(source, template=ref_path)

        # Assert
        assert isinstance(result, bytes)
        assert result.startswith(b"PK")

    @pytest.mark.ai
    def test_pandoc_markdown_to_docx__produces_valid_docx__with_report_md(
        self, report_md_path: Path | None, tmp_path: Path
    ) -> None:
        """
        Purpose: Verify conversion of report.md produces valid DOCX.
        Why this matters: Real markdown with headings and tables must convert correctly.
        Setup summary: Use report.md from template folder if present; assert valid output.
        """
        if not self._pandoc_available():
            pytest.skip("pandoc not installed")
        if report_md_path is None:
            pytest.skip("report.md not found in template folder")

        import pypandoc

        # Arrange
        source = report_md_path.read_text()
        ref_path = tmp_path / "ref.docx"
        pypandoc.convert_text(" ", to="docx", format="md", outputfile=str(ref_path))

        # Act
        result = pandoc_markdown_to_docx(source, template=ref_path)

        # Assert
        assert isinstance(result, bytes)
        assert result.startswith(b"PK")
        assert len(result) > 1000

    @pytest.mark.ai
    def test_pandoc_markdown_to_docx__produces_valid_docx__with_bundled_template(
        self, template_dir: Path
    ) -> None:
        """
        Purpose: Verify conversion with template from docx_generator/template folder.
        Why this matters: Ensures bundled templates (e.g. test.docx, Doc Template.docx) work.
        Setup summary: Use first .docx/.dotx found in template dir; skip if none.
        """
        if not self._pandoc_available():
            pytest.skip("pandoc not installed")

        template_path = None
        for name in ("test.docx", "Testtemplate.dotx", "Doc Template.docx"):
            candidate = template_dir / name
            if candidate.exists():
                template_path = candidate
                break
        if template_path is None:
            pytest.skip("no .docx/.dotx template found in template folder")

        # Act
        result = pandoc_markdown_to_docx("# Test\n\nContent", template=template_path)

        # Assert
        assert isinstance(result, bytes)
        assert result.startswith(b"PK")
