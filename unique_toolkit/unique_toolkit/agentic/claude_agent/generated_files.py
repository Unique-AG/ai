"""
Generated files handling for Claude Agent SDK integration.

This module handles post-processing of Claude's output to surface uploaded files
inline in the chat response.

How inline file rendering works
--------------------------------
Claude is instructed (via _FILE_OUTPUT_INSTRUCTIONS in prompts.py) to:
  1. Save all output files to `./output/` (e.g. `./output/chart.png`)
  2. Reference them inline at the relevant point in the response using markdown:
     - Images:       `![Description](./output/chart.png)`
     - HTML reports: `![Report](./output/report.html)`
     - Other files:  `[📎 data.csv](./output/data.csv)`

After upload, `inject_file_references_into_text()` replaces those `./output/`
paths with `unique://content/{id}` URLs in-place.  Any file Claude saved but
did NOT reference in the text is appended at the end (fallback).

This mirrors the Responses API postprocessor approach:
  sandbox:/mnt/data/file.png → replaced by DisplayCodeInterpreterFilesPostProcessor
  ./output/file.png          → replaced here by inject_file_references_into_text()

The end result for the frontend is identical: `unique://content/{id}` URLs
positioned at the exact point the user expects to see the output.
"""

from __future__ import annotations

import mimetypes
import re


def inject_file_references_into_text(
    text: str,
    uploaded_files: dict[str, str],
) -> str:
    """Replace ./output/{filename} path references in text with platform content URLs.

    Claude is instructed to embed `./output/filename.ext` paths inline in its
    response (as markdown images or links) at the point where the file is relevant.
    This function resolves those paths to hosted platform URLs after upload.

    Two-phase processing:
      1. Replace every `./output/{filename}` occurrence with `unique://content/{id}`.
         For HTML files embedded as markdown images, the img syntax is rewritten to
         an HtmlRendering fenced block so the frontend renders it as an iframe.
      2. Any file that was uploaded but NOT referenced inline by Claude is appended
         at the end as a fallback (with a horizontal rule separator).

    Args:
        text: The accumulated Claude response text.
        uploaded_files: Dict mapping filename → content_id from workspace upload.

    Returns:
        Text with ./output/ paths resolved to platform URLs, unreferenced files
        appended at the end.
    """
    if not uploaded_files:
        return text

    referenced: set[str] = set()

    for filename, content_id in uploaded_files.items():
        mime_type, _ = mimetypes.guess_type(filename)
        mime_type = mime_type or "application/octet-stream"
        platform_url = f"unique://content/{content_id}"
        escaped = re.escape(f"./output/{filename}")

        if not re.search(escaped, text):
            continue

        referenced.add(filename)

        if mime_type == "text/html":
            html_block = f"```HtmlRendering\n100%\n500px\n\n{platform_url}\n\n```"
            # Replace markdown img syntax: ![alt](./output/file.html) → HtmlRendering block
            text = re.sub(
                rf"!\[[^\]]*\]\({escaped}\)",
                html_block,
                text,
            )
            # Replace any remaining bare path references (e.g. in plain text)
            text = re.sub(escaped, platform_url, text)
        else:
            # Images and other files: replace the path wherever it appears.
            # Markdown img/link syntax is preserved; only the URL part changes.
            text = re.sub(escaped, platform_url, text)

    # Fallback: append files Claude did not reference inline
    unreferenced = {
        fn: cid for fn, cid in uploaded_files.items() if fn not in referenced
    }
    if not unreferenced:
        return text

    fallback_lines: list[str] = []
    for filename, content_id in unreferenced.items():
        mime_type, _ = mimetypes.guess_type(filename)
        mime_type = mime_type or "application/octet-stream"
        platform_url = f"unique://content/{content_id}"

        if mime_type.startswith("image/"):
            fallback_lines.append(f"![{filename}]({platform_url})")
        elif mime_type == "text/html":
            fallback_lines.append(
                f"```HtmlRendering\n100%\n500px\n\n{platform_url}\n\n```"
            )
        else:
            fallback_lines.append(f"[📎 {filename}]({platform_url})")

    return text + "\n\n---\n\n" + "\n\n".join(fallback_lines)


# Keep old name as alias so any external callers aren't broken
append_file_references_to_text = inject_file_references_into_text
