import asyncio
import tempfile
from pathlib import Path

import pypandoc


def pandoc_markdown_to_docx(
    source: str, *, template: bytes | Path | str | None = None
) -> bytes:
    """Convert markdown to DOCX via pandoc.

    Args:
        source: Markdown content as string.
        template: Optional reference document for styles. Can be:
            - None: use pandoc defaults
            - Path or str: path to .docx template file
            - bytes: template content in memory (written to temp file)

    Returns:
        DOCX file content as bytes.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        out_path = tmp_path / "out.docx"

        if template is None:
            extra_args = []
        elif isinstance(template, bytes):
            ref_path = tmp_path / "ref.docx"
            ref_path.write_bytes(template)
            extra_args = [f"--reference-doc={ref_path}"]
        else:
            extra_args = [f"--reference-doc={str(template)}"]

        pypandoc.convert_text(
            source,
            to="docx",
            format="md",
            outputfile=str(out_path),
            extra_args=extra_args,
        )
        return out_path.read_bytes()


async def pandoc_markdown_to_docx_async(
    source: str,
    *,
    template: bytes | Path | str | None = None,
) -> bytes:
    """
    Runs the conversion in a thread so that the main event loop is not blocked on I/O operations.
    """
    return await asyncio.to_thread(
        pandoc_markdown_to_docx,
        source,
        template=template,
    )
