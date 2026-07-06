# unique-document-generator

Tool package that converts markdown to Word (.docx) documents via pandoc and uploads them to the Unique chat.

## Overview

`unique-document-generator` adds a `DocGenerator` tool that lets a space generate a downloadable document from model-produced markdown.

The tool is designed for the standard orchestrator flow:

1. The model prepares a complete markdown document.
2. `DocGenerator` converts the markdown to `.docx` with pandoc.
3. The generated file is uploaded to chat.
4. The tool attaches a `ContentReference` directly to the assistant message.
5. The model replies using the rendered `<sup>N</sup>` download citation.

## Public Surface

### Tool name

- `DocGenerator`

### Input schema

`DocGeneratorToolInput`

- `markdown_content: str`
  The full markdown document to convert.
- `filename: str = "document.docx"`
  Output filename. If the `.docx` suffix is missing, the tool appends it.

### Config schema

`DocGeneratorToolConfig`

- `template_content_id: str = ""`
  Optional knowledge base content id for a `.docx` template. When set, the tool downloads the template and passes it to pandoc.
- `export_format: ExportFormat = ExportFormat.DOCX`
  Current output format. Only `docx` is supported today.
- `tool_description: str`
  Main tool prompt shown to the language model.
- `tool_format_information_for_system_prompt: str = ""`
  Extra formatting guidance appended to the system prompt.

## Default Behavior

- Blank `markdown_content` returns an error response.
- Missing `.docx` suffix is normalized automatically.
- If `template_content_id` is empty, the tool uses plain pandoc defaults.
- If template download fails, the tool falls back to plain pandoc defaults and still generates the file.
- The attachment flow uses `modify_assistant_message_async(references=[...])` so the download reference is attached deterministically.

## Example Configuration

```python
from unique_document_generator import DocGeneratorToolConfig

config = DocGeneratorToolConfig(
    template_content_id="cont_abc123",
    tool_format_information_for_system_prompt=(
        "Use a title page, concise section headings, and an executive summary."
    ),
)
```

## Example Tool Call

```python
{
    "markdown_content": "# Q1 Review\n\n## Summary\n- Revenue increased\n- Risks remain in pipeline coverage",
    "filename": "Q1 Review.docx",
}
```

## Testing

Run the package tests from the package root:

```bash
uv run --with pytest --with pytest-asyncio --with pytest-cov pytest tests --cov=unique_document_generator --cov-report=term-missing
```

## Implementation Notes

- Conversion is handled by `unique_toolkit._common.docx_generator.pandoc_markdown_to_docx_async`.
- Template downloads are handled through `KnowledgeBaseService`.
- The tool intentionally instructs the model to use the exact `<sup>N</sup>` citation returned by the assistant message reference, because that is the format the chat UI renders as the clickable download link.
