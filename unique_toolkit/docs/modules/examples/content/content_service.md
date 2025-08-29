
# Content Service
The content service provides capabilities to interact with the the knowledge base.

```{.python #initialize_content_service_standalone}
MISSING
```


## Up and Download contents from the knowledgebase

A `Content` corresponds to a file of any type.

### Into memory
It is encouraged to load contents to memory only in order to avoid information leakage by saving files to disk accidentially


### Into a file on disk
Sometimes a file can only be read from disk with a specific library. In this case the best practice is to save it within a random directory under `/tmp`. Ideally under a random name as well. Furthermore, the file should be deleted at the end of the request.

<!--
```{.python #content_service_imports}
import os
import io
import tempfile
import requests
from pathlib import Path
from unique_toolkit.content.schemas import ContentSearchType, ContentRerankerConfig
import unique_sdk
```
-->

<!--
```{.python #content_service_config}
# Load configuration from environment variables
scope_id = os.getenv("UNIQUE_SCOPE_ID")
scope_ids = os.getenv("UNIQUE_SCOPE_IDS", "").split(",") if os.getenv("UNIQUE_SCOPE_IDS") else None
content_id = os.getenv("UNIQUE_CONTENT_ID")
content_ids = os.getenv("UNIQUE_CONTENT_IDS", "").split(",") if os.getenv("UNIQUE_CONTENT_IDS") else None
chat_id = os.getenv("UNIQUE_CHAT_ID")

# Fixed configuration values
file_path = "/path/to/document.pdf"
filename = "secure-document.pdf"
chunk_size = 1000
chunk_overlap = 200
reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
```
-->

<!--
```{.python #content_service_setup}
<<content_service_imports>>
<<initialize_content_service_standalone>>
<<content_service_config>>
```
-->

<!--
```{.python #content_service_search_content_chunks}
from unique_toolkit.content.schemas import ContentSearchType

```{.python #content_service_search_content_chunks}
content_chunks = content_service.search_content_chunks(
    search_string="Hello, world!",
    search_type=ContentSearchType.VECTOR,
    limit=10,
)
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
    mime_type="application/pdf",
    scope_id=scope_id,
    chat_id=chat_id,
    metadata={"category": "documentation", "version": "1.0"}
)
```

### Upload from File

When you must upload from disk:

```{.python #content_service_upload_file}
# Configure ingestion settings
ingestion_config = unique_sdk.Content.IngestionConfig(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap,
    extract_images=True
)

content = content_service.upload_content(
    path_to_content=file_path,
    content_name=Path(file_path).name,
    mime_type="application/pdf",
    scope_id=scope_id,
    skip_ingestion=False,  # Process the content for search
    ingestion_config=ingestion_config,
    metadata={"department": "legal", "classification": "confidential"}
)
```

## Content Download

### Download to Memory (Recommended)

Prefer downloading to memory for security:

```{.python #content_service_download_bytes}
# Download content as bytes
content_bytes = content_service.download_content_to_bytes(
    content_id=content_id,
    chat_id=chat_id
)

# Process in memory
with io.BytesIO(content_bytes) as file_like:
    # Process the content without saving to disk
    pass
```

### Download to Temporary File

When you need a file on disk, use secure temporary directories:

```{.python #content_service_download_file}
# Download to secure temporary file
temp_file_path = content_service.download_content_to_file_by_id(
    content_id=content_id,
    chat_id=chat_id,
    filename=filename,
    tmp_dir_path=tempfile.mkdtemp()  # Use secure temp directory
)

try:
    # Process the file
    with open(temp_file_path, 'rb') as file:
        # Your file processing logic here
        pass
finally:
    # Always clean up temporary files
    if temp_file_path.exists():
        temp_file_path.unlink()
    # Clean up the temporary directory
    temp_file_path.parent.rmdir()
```

### Request Content Response

For direct HTTP response handling:

```{.python #content_service_request_content}
response = content_service.request_content_by_id(
    content_id=content_id,
    chat_id=chat_id
)

if response.status_code == 200:
    # Stream the content
    for chunk in response.iter_content(chunk_size=8192):
        # Process chunk by chunk
        pass
```

## Content Search

### Semantic Search (Vector-Based)

Use vector search for semantic similarity matching:

```{.python #content_service_vector_search}
# Search for content using vector similarity
content_chunks = content_service.search_content_chunks(
    search_string="machine learning algorithms",
    search_type=ContentSearchType.VECTOR,
    limit=10,
    score_threshold=0.7,  # Only return results with high similarity
    content_ids=content_ids  # Search in specific documents if configured
)

print(f"Found {len(content_chunks)} relevant chunks")
for i, chunk in enumerate(content_chunks[:3]):
    print(f"  {i+1}. {chunk.text[:100]}...")
```

??? example "Full Examples (Click to expand)"
    
    <!--codeinclude-->
    [Search Examples](../../../examples_from_docs/content_service_search_examples.py)
    [Upload Examples](../../../examples_from_docs/content_service_upload_examples.py)
    [Download Examples](../../../examples_from_docs/content_service_download_examples.py)
    [Complete Demo](../../../examples_from_docs/content_service_complete_demo.py)
    <!--/codeinclude-->

### Combined Search (Hybrid)

Combine semantic and keyword search for best results:

```{.python #content_service_combined_search}
# Combined semantic and keyword search for best results
content_chunks = content_service.search_content_chunks(
    search_string="python data analysis",
    search_type=ContentSearchType.COMBINED,
    limit=15,
    search_language="english",
    scope_ids=scope_ids,  # Limit to specific scopes if configured
    content_ids=content_ids  # Search in specific documents if configured
)

print(f"Combined search found {len(content_chunks)} chunks")
```

### Advanced Search Options

```{.python #content_service_advanced_search}
# Configure reranking for better results
reranker_config = ContentRerankerConfig(
    model=reranker_model,
    top_k=50
)

content_chunks = content_service.search_content_chunks(
    search_string="financial reports Q4",
    search_type=ContentSearchType.COMBINED,
    limit=10,
    reranker_config=reranker_config,
    metadata_filter={"document_type": "financial"},
    chat_only=False,  # Search across all content, not just chat
    scope_ids=scope_ids,  # Limit to specific scopes if configured
    content_ids=content_ids  # Limit to specific documents if configured
)
```

### Asynchronous Search

For better performance in async applications:

```{.python #content_service_async_search}
async def search_content_async():
    content_chunks = await content_service.search_content_chunks_async(
        search_string="user authentication",
        search_type=ContentSearchType.VECTOR,
        limit=20
    )
    return content_chunks
```

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

### Performance Optimization

1. **Use Async Methods**: For better performance in async applications:
   ```python
   content_chunks = await content_service.search_content_chunks_async(...)
   ```

2. **Optimize Search Parameters**:
   - Use appropriate `limit` values
   - Set `score_threshold` to filter low-quality results
   - Use `scope_ids` to limit search scope when possible

3. **Batch Operations**: When processing multiple files, consider batching operations.

### Search Strategy

1. **Choose the Right Search Type**:
   - `VECTOR`: Best for semantic similarity
   - `COMBINED`: Best for hybrid keyword + semantic search

2. **Use Metadata Filters**: Narrow down results with metadata filters:
   ```python
   metadata_filter = {
       "document_type": "manual",
       "created_date": {"gte": "2024-01-01"}
   }
   ```

3. **Implement Reranking**: Use reranking for improved result quality in critical applications.

### Error Handling

Always implement proper error handling:

```{.python #content_service_error_handling}
try:
    content_chunks = content_service.search_content_chunks(
        search_string="query",
        search_type=ContentSearchType.VECTOR,
        limit=10
    )
except Exception as e:
    logger.error(f"Search failed: {e}")
    # Implement fallback logic
    content_chunks = []
```

## Common Use Cases

### RAG (Retrieval-Augmented Generation)

```{.python #content_service_rag_example}
def create_rag_prompt(user_query: str) -> str:
    # Search for relevant context
    relevant_chunks = content_service.search_content_chunks(
        search_string=user_query,
        search_type=ContentSearchType.COMBINED,
        limit=5,
        score_threshold=0.7
    )

    # Extract text for context
    context = "\n\n".join([chunk.text for chunk in relevant_chunks])

    # Use context in your language model prompt
    prompt = f"Context: {context}\n\nQuestion: {user_query}\nAnswer:"
    return prompt
```

### Document Processing Pipeline

```{.python #content_service_pipeline_example}
def process_document():
    """Upload a document and search within it"""
    print(f"Processing document: {file_path}")

    # 1. Upload document
    content = content_service.upload_content(
        path_to_content=file_path,
        content_name=Path(file_path).name,
        mime_type="application/pdf",
        scope_id=scope_id,
        metadata={"source": "user_upload", "processed": False}
    )
    print(f"Uploaded document with ID: {content.id}")

    # 2. Wait for ingestion (in real apps, use webhooks or polling)
    print("Waiting for content ingestion...")
    import time
    time.sleep(3)  # Wait a bit longer for processing

    # 3. Search within the uploaded document
    print("Searching for summary information...")
    chunks = content_service.search_content_chunks(
        search_string="summary",
        search_type=ContentSearchType.VECTOR,
        limit=3,
        content_ids=[content.id]  # Only search in the uploaded document
    )

    print(f"Found {len(chunks)} relevant chunks:")
    for i, chunk in enumerate(chunks):
        print(f"  {i+1}. {chunk.text[:150]}...")

    return chunks
```

```{.python #content_service_complete_example}
def content_service_demo():
    """Complete demonstration of ContentService functionality"""

    print("=== ContentService Demo ===")

    # 1. Upload a document first
    if file_path and scope_id:
        print(f"Uploading document: {file_path}")
        content = content_service.upload_content(
            path_to_content=file_path,
            content_name=Path(file_path).name,
            mime_type="application/pdf",
            scope_id=scope_id,
            metadata={"demo": True, "uploaded_by": "content_service_demo"}
        )
        print(f"Uploaded content ID: {content.id}")

        # Wait a moment for ingestion (in real apps, use webhooks or polling)
        print("Waiting for content ingestion...")
        import time
        time.sleep(2)

        # 2. Search within the uploaded document
        print(f"\nSearching within uploaded document...")
        search_results = content_service.search_content_chunks(
            search_string="documentation",
            search_type=ContentSearchType.COMBINED,
            limit=5,
            content_ids=[content.id]  # Search only in the uploaded document
        )
        print(f"Found {len(search_results)} chunks in uploaded document")

        # Display some results
        for i, chunk in enumerate(search_results[:3]):
            print(f"  Chunk {i+1}: {chunk.text[:100]}...")

        # 3. Download the uploaded content
        print(f"\nDownloading the uploaded content...")
        try:
            content_bytes = content_service.download_content_to_bytes(
                content_id=content.id,
                chat_id=chat_id
            )
            print(f"Downloaded {len(content_bytes)} bytes")
        except Exception as e:
            print(f"Download failed: {e}")

        # 4. RAG example with uploaded content
        user_query = "What are the main topics covered?"
        print(f"\nCreating RAG prompt for: '{user_query}'")
        relevant_chunks = content_service.search_content_chunks(
            search_string=user_query,
            search_type=ContentSearchType.COMBINED,
            limit=3,
            content_ids=[content.id],
            score_threshold=0.5
        )

        if relevant_chunks:
            context = "\n\n".join([chunk.text for chunk in relevant_chunks])
            rag_prompt = f"Context: {context}\n\nQuestion: {user_query}\nAnswer:"
            print(f"RAG prompt created (length: {len(rag_prompt)} characters)")
        else:
            print("No relevant chunks found for RAG example")
    else:
        print("No file path or scope ID configured - skipping upload and search demo")
        print("Please set UNIQUE_UPLOAD_FILE_PATH and UNIQUE_SCOPE_ID environment variables")

    print("=== Demo Complete ===")

if __name__ == "__main__":
    content_service_demo()
```

<!--
```{.python file=docs/.python_files/content_service_search_examples.py}
<<content_service_setup>>
<<content_service_vector_search>>
<<content_service_combined_search>>
<<content_service_advanced_search>>
```
-->

<!--
```{.python file=docs/.python_files/content_service_upload_examples.py}
<<content_service_setup>>
<<content_service_upload_bytes>>
<<content_service_upload_file>>
```
-->

<!--
```{.python file=docs/.python_files/content_service_download_examples.py}
<<content_service_setup>>
<<content_service_download_bytes>>
<<content_service_download_file>>
<<content_service_request_content>>
```
-->

<!--
```{.python file=docs/.python_files/content_service_complete_demo.py}
<<content_service_setup>>
<<content_service_rag_example>>
<<content_service_pipeline_example>>
<<content_service_complete_example>>
```
-->

## Environment Variables Reference

The examples in this documentation use environment variables for configuration. Here are all the variables you can set:

### Required Variables
```env
# Basic authentication (inherited from application type setup)
UNIQUE_API_BASE_URL=            # The backend URL of Unique's public API
UNIQUE_API_VERSION=             # The version of Unique's public API
UNIQUE_COMPANY_ID=              # Your company identifier
UNIQUE_USER_ID=                 # Your user identifier
```

### Optional Configuration Variables
```env
# Content and search configuration
UNIQUE_SCOPE_ID=                # Default scope ID for uploads
UNIQUE_SCOPE_IDS=               # Comma-separated list of scope IDs for search (e.g., "scope1,scope2,scope3")
UNIQUE_CONTENT_ID=              # Content ID for download operations
UNIQUE_CONTENT_IDS=             # Comma-separated list of content IDs for search filtering
UNIQUE_CHAT_ID=                 # Chat ID for chat-specific operations
```

### Example .env File
```env
# Required
UNIQUE_API_BASE_URL=https://api.unique.ch
UNIQUE_API_VERSION=v4
UNIQUE_COMPANY_ID=your-company-id
UNIQUE_USER_ID=your-user-id

# Optional - Content configuration
UNIQUE_SCOPE_ID=your-default-scope
UNIQUE_SCOPE_IDS=scope1,scope2,scope3
UNIQUE_CHAT_ID=your-chat-id
UNIQUE_CONTENT_ID=content-to-download
```

### Fixed Configuration Values

The following values are set as constants in the code for simplicity:

- **File path**: `/path/to/document.pdf` (update in code for actual use)
- **Download filename**: `secure-document.pdf`
- **Chunk size**: `1000` tokens
- **Chunk overlap**: `200` tokens  
- **Reranker model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`

This comprehensive guide covers all major aspects of using the `ContentService` effectively and securely.

