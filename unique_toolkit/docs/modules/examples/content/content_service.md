
# Content Service
The content service provides capabilities to interact with the the knowledge base.

```{.python #initialize_content_service_standalone}
content_service = ContentService.from_settings_filename()
```


## Up and Download contents from the knowledgebase

A `Content` corresponds to a file of any type.

### Into memory
It is encouraged to load contents to memory only in order to avoid information leakage by saving files to disk accidentially


### Into a file on disk
Sometimes a file can only be read from disk with a specific library. In this case the best practice is to save it within a random directory under `/tmp`. Ideally under a random name as well. Furthermore, the file should be deleted at the end of the request.

<!--
```{.python #load_demo_variables}
from dotenv import dotenv_values
demo_env_vars = dotenv_values(Path(__file__).parent/"demo.env")

```
```{.python #env_scope_id}
scope_id = demo_env_vars.get("UNIQUE_SCOPE_ID") or "unknown"
```
```{.python #env_scope_ids}
scope_ids = demo_env_vars.get("UNIQUE_SCOPE_IDS", "").split(",") if os.getenv("UNIQUE_SCOPE_IDS") else None
```
```{.python #env_content_id}
content_id = demo_env_vars.get("UNIQUE_CONTENT_ID") or "unknown"
```
```{.python #env_content_ids}
content_ids = demo_env_vars.get("UNIQUE_CONTENT_IDS", "").split(",") if os.getenv("UNIQUE_CONTENT_IDS") else None
```
```{.python #env_chat_id}
chat_id = demo_env_vars.get("UNIQUE_CHAT_ID") or "unknown"

```
-->

<!--
```{.python #content_service_setup}
<<common_imports>>
<<initialize_content_service_standalone>>
```
-->

## Content Upload

### Upload from Memory (Recommended)

For security, prefer uploading from memory to avoid disk-based information leakage:

```{python #content_service_upload_bytes}
content_bytes = b"Your file content here"
content = content_service.upload_content_from_bytes(
    content=content_bytes,
    content_name="document.txt",
    mime_type="text/plain",
    scope_id=scope_id,
    metadata={"category": "documentation", "version": "1.0"}
)
```

<!--
```{.python #content_service_upload_from_memory file=./docs/.python_files/content_service_upload_from_memory.py }
<<content_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<content_service_upload_bytes>>
```
-->

### Upload from File

When you must upload from disk:

```{.python #content_service_upload_from_file}
# Configure ingestion settings
content = content_service.upload_content(
    path_to_content=str(file_path),
    content_name=Path(file_path).name,
    mime_type="text/plain",
    scope_id=scope_id,
    skip_ingestion=False,  # Process the content for search
    metadata={"department": "legal", "classification": "confidential"}
)
```

<!--
```{.python file=./docs/.python_files/content_service_upload_from_file.py }
<<content_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
file_path = Path(__file__).parent/"test.txt"
<<content_service_upload_from_file>>
```
-->



## Content Download

### Download to Memory (Recommended)

Prefer downloading to memory for security:

```{.python #content_service_download_bytes}
# Download content as bytes
content_bytes = content_service.download_content_to_bytes(
    content_id=content_id or "unknown",
)

# Process in memory
text = ""
with io.BytesIO(content_bytes) as file_like:
    text = file_like.read().decode("utf-8")

print(text)
```

<!--
```{.python file=./docs/.python_files/content_service_download_to_memory.py }
<<content_service_setup>>
<<load_demo_variables>>
<<env_content_id>>
<<content_service_download_bytes>>
```
-->



### Download to Temporary File

When you need a file on disk, use secure temporary directories:

```{.python #content_service_download_file}
# Download to secure temporary file

filename = "my_testfile.txt"
temp_file_path = content_service.download_content_to_file_by_id(
    content_id=content_id,
    filename=filename,
    tmp_dir_path=tempfile.mkdtemp()  # Use secure temp directory
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
```{.python file=./docs/.python_files/content_service_download_to_file.py }
<<content_service_setup>>
<<load_demo_variables>>
<<env_content_id>>
<<content_service_download_file>>
```
-->




## Content Search

### Semantic Search (Vector-Based)

Use vector search for semantic similarity matching:

```{.python #content_service_vector_search}
# Search for content using vector similarity
content_chunks = content_service.search_content_chunks(
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
```{.python file=./docs/.python_files/content_service_vector_search_content_chunks.py }
<<content_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<content_service_vector_search>>
```
-->




??? example "Full Examples (Click to expand)"
    
    <!--codeinclude-->
    <!--/codeinclude-->

### Combined Search (Hybrid)

Combine semantic and keyword search for best results:

```{.python #content_service_combined_search}
# Combined semantic and keyword search for best results
content_chunks = content_service.search_content_chunks(
    search_string="Harry Potter",
    search_type=ContentSearchType.COMBINED,
    limit=15,
    search_language="english",
    scope_ids=[scope_id],  # Limit to specific scopes if configured
)

print(f"Combined search found {len(content_chunks)} chunks")
```

<!--
```{.python file=./docs/.python_files/content_service_combined_search_content_chunks.py }
<<content_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<content_service_combined_search>>
```
-->



### Content File Search

Search for complete content files by metadata:

```{.python #content_service_content_search}
# Search for specific content files
contents = content_service.search_contents(
    where={"title": {"contains": "manual"}},
    chat_id=chat_id
)

# Search for content in a specific chat (if chat_id is provided)
if chat_id:
    chat_contents = content_service.search_content_on_chat(chat_id)
```


## Best Practices

### Security Considerations

1. **Prefer Memory Operations**: Always prefer `download_content_to_bytes()` and `upload_content_from_bytes()` to avoid disk-based information leakage.

2. **Temporary File Cleanup**: When using temporary files, always clean them up:
   ```python
   import tempfile
   import os
   
   temp_dir = tempfile.mkdtemp()
   try:
       # Your file operations
       pass
   finally:
       # Clean up all files in temp directory
       import shutil
       shutil.rmtree(temp_dir)
   ```

3. **Secure File Names**: Use random names for temporary files to prevent information leakage through file names.