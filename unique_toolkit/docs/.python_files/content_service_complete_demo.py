# ~/~ begin <<docs/modules/examples/content/content_service.md#docs/.python_files/content_service_complete_demo.py>>[init]
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_setup>>[init]
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_imports>>[init]
import os
import io
import tempfile
import requests
from pathlib import Path
from unique_toolkit.content.schemas import ContentSearchType, ContentRerankerConfig
import unique_sdk
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#initialize_content_service_standalone>>[init]
MISSING
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_config>>[init]
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
# ~/~ end
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_rag_example>>[init]
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
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_pipeline_example>>[init]
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
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_complete_example>>[init]
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
# ~/~ end
# ~/~ end
