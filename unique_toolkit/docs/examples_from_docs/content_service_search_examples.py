# %%
import os

from unique_toolkit.content.schemas import ContentRerankerConfig, ContentSearchType

MISSING
# Load configuration from environment variables
scope_id = os.getenv("UNIQUE_SCOPE_ID")
scope_ids = (
    os.getenv("UNIQUE_SCOPE_IDS", "").split(",")
    if os.getenv("UNIQUE_SCOPE_IDS")
    else None
)
content_id = os.getenv("UNIQUE_CONTENT_ID")
content_ids = (
    os.getenv("UNIQUE_CONTENT_IDS", "").split(",")
    if os.getenv("UNIQUE_CONTENT_IDS")
    else None
)
chat_id = os.getenv("UNIQUE_CHAT_ID")

# Fixed configuration values
file_path = "/path/to/document.pdf"
filename = "secure-document.pdf"
chunk_size = 1000
chunk_overlap = 200
reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
# Search for content using vector similarity
content_chunks = content_service.search_content_chunks(
    search_string="machine learning algorithms",
    search_type=ContentSearchType.VECTOR,
    limit=10,
    score_threshold=0.7,  # Only return results with high similarity
    content_ids=content_ids,  # Search in specific documents if configured
)

print(f"Found {len(content_chunks)} relevant chunks")
for i, chunk in enumerate(content_chunks[:3]):
    print(f"  {i + 1}. {chunk.text[:100]}...")
# Combined semantic and keyword search for best results
content_chunks = content_service.search_content_chunks(
    search_string="python data analysis",
    search_type=ContentSearchType.COMBINED,
    limit=15,
    search_language="english",
    scope_ids=scope_ids,  # Limit to specific scopes if configured
    content_ids=content_ids,  # Search in specific documents if configured
)

print(f"Combined search found {len(content_chunks)} chunks")
# Configure reranking for better results
reranker_config = ContentRerankerConfig(model=reranker_model, top_k=50)

content_chunks = content_service.search_content_chunks(
    search_string="financial reports Q4",
    search_type=ContentSearchType.COMBINED,
    limit=10,
    reranker_config=reranker_config,
    metadata_filter={"document_type": "financial"},
    chat_only=False,  # Search across all content, not just chat
    scope_ids=scope_ids,  # Limit to specific scopes if configured
    content_ids=content_ids,  # Limit to specific documents if configured
)
