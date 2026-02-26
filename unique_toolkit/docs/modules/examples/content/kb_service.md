# Knowledge Base Service - Examples

This page provides practical code examples for implementing knowledge base operations. For broader documentation and concepts, see the [Knowledge Base Documentation](../../../knowledge_base/index.md).

## Content Upload

### Upload from Memory (Recommended)

```{python #kb_service_upload_bytes}
content_bytes = b"Your file content here"
content = kb_service.upload_content_from_bytes(
    content=content_bytes,
    content_name="document.txt",
    mime_type="text/plain",
    scope_id=scope_id,
    metadata={"category": "documentation", "version": "1.0"}
)
```

<!--
```{.python #kb_service_upload_from_memory file=./docs/.python_files/kb_service_upload_from_memory.py }
<<kb_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<kb_service_upload_bytes>>
```
-->

### Upload from File

```{.python #kb_service_upload_from_file}
# Configure ingestion settings
content = kb_service.upload_content(
    path_to_content=str(file_path),
    content_name=Path(file_path).name,
    mime_type="text/plain",
    scope_id=scope_id,
    skip_ingestion=False,  # Process the content for search
    metadata={"department": "legal", "classification": "confidential"}
)
```

<!--
```{.python file=./docs/.python_files/kb_service_upload_from_file.py }
<<kb_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
file_path = Path(__file__).parent/"test.txt"
<<kb_service_upload_from_file>>
```
-->

### Make Uploaded Document Available to User

```python
uploaded_content = kb_service.upload_content(
        path_to_content=str(output_filepath),
        content_name=output_filepath.name,
        mime_type=str(mimetypes.guess_type(output_filepath)[0]),
        chat_id=payload.chat_id,
        skip_ingestion=skip_ingestion,  # Usually True for generated files
    )

reference = ContentReference(
    id=content.id,
    sequence_number=1,
    message_id=message_id,
    name=filename,
    source=payload.name,
    source_id=chat_id,
    url=f"unique://content/{uploaded_content.id}",  # Special URL format for content
)

self.chat_service.modify_assistant_message(
                content="Please find the translated document below in the references.",
                references=[reference],
                set_completed_at=True,
            )
```

??? example "Full Examples Upload (Click to expand)"
    
    <!--codeinclude-->
    [Upload from Memory](../../../examples_from_docs/kb_service_upload_from_memory.py)
    [Upload from File](../../../examples_from_docs/kb_service_upload_from_file.py)
    <!--/codeinclude-->

## Content Download

### Download to Memory (Recommended)

```{.python #kb_service_download_bytes}
# Download content as bytes
content_bytes = kb_service.download_content_to_bytes(
    content_id=content_id or "unknown",
)

# Process in memory
text = ""
with io.BytesIO(content_bytes) as file_like:
    text = file_like.read().decode("utf-8")

print(text)
```

<!--
```{.python file=./docs/.python_files/kb_service_download_to_memory.py }
<<kb_service_setup>>
<<load_demo_variables>>
<<env_content_id>>
<<kb_service_download_bytes>>
```
-->

### Download to Temporary File

```{.python #kb_service_download_file}
# Download to secure temporary file

filename = "my_testfile.txt"
temp_file_path = kb_service.download_content_to_file(
    content_id=content_id,
    output_filename=filename,
    output_dir_path=Path(tempfile.mkdtemp())  # Use secure temp directory
)

try:
    # Process the file
    with open(temp_file_path, 'rb') as file:
        text = file.read().decode("utf-8")
        print(text) 
finally:
    # Always clean up temporary files
    if temp_file_path.exists():
        temp_file_path.unlink()
    # Clean up the temporary directory
    temp_file_path.parent.rmdir()
```

<!--
```{.python file=./docs/.python_files/kb_service_download_to_file.py }
<<kb_service_setup>>
<<load_demo_variables>>
<<env_content_id>>
<<kb_service_download_file>>
```
-->

??? example "Full Examples Download (Click to expand)"
    
    <!--codeinclude-->
    [Download to Memory](../../../examples_from_docs/kb_service_download_to_memory.py)
    [Download to File](../../../examples_from_docs/kb_service_download_to_file.py)
    <!--/codeinclude-->

## Content Deletion

```{.python #kb_service_delete_content}
kb_service.delete_content(
    content_id=content.id
)
```

<!--
```{.python file=./docs/.python_files/kb_service_delete.py }
<<kb_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<kb_service_upload_bytes>>
<<kb_service_delete_content>>
```
-->

??? example "Full Examples Content Deletion (Click to expand)"
    
    <!--codeinclude-->
    [Content Deletion](../../../examples_from_docs/kb_service_delete.py)
    <!--/codeinclude-->

## Content Search

### Semantic Search (Vector-Based)

```{.python #kb_service_vector_search}
# Search for content using vector similarity
content_chunks = kb_service.search_content_chunks(
    search_string="Harry Potter",
    search_type=ContentSearchType.VECTOR,
    limit=10,
    score_threshold=0.7,  # Only return results with high similarity
    scope_ids=[scope_id]
)

print(f"Found {len(content_chunks)} relevant chunks")
for i, chunk in enumerate(content_chunks[:3]):
    print(f"  {i+1}. {chunk.text[:100]}...")
```

<!--
```{.python file=./docs/.python_files/kb_service_vector_search_content_chunks.py }
<<kb_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<kb_service_vector_search>>
```
-->

### Combined Search (Hybrid)

```{.python #kb_service_combined_search}
# Combined semantic and keyword search for best results
content_chunks = kb_service.search_content_chunks(
    search_string="Harry Potter",
    search_type=ContentSearchType.COMBINED,
    limit=15,
    search_language="english",
    scope_ids=[scope_id],  # Limit to specific scopes if configured
)

print(f"Combined search found {len(content_chunks)} chunks")
```

<!--
```{.python file=./docs/.python_files/kb_service_combined_search_content_chunks.py }
<<kb_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<kb_service_combined_search>>
```
-->

### Content File Search

```{.python #kb_service_content_search}
# Search for specific content files
contents = kb_service.search_contents(
    where={"title": {"contains": "manual"}},
)
```

<!--
```{.python file=./docs/.python_files/kb_service_search_content.py }
<<kb_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<kb_service_content_search>>
```
-->

## Full Examples
    
??? example "Full Examples Content Search (Click to expand)"
    
    <!--codeinclude-->
    [Vector Search](../../../examples_from_docs/kb_service_vector_search_content_chunks.py)
    [Combined Search](../../../examples_from_docs/kb_service_combined_search_content_chunks.py)
    [Content Search](../../../examples_from_docs/kb_service_search_content.py)
    <!--/codeinclude-->
