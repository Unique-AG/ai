import asyncio
from pathlib import Path

from unique_client.unique_client.api_resources.api_dtos import (
    PublicCreateSearchDto,
    SearchType,
)
from unique_client.unique_client.implementation import UniqueClient


def main_sync():
    """Simple synchronous search example."""
    # Initialize client from .env file
    client = UniqueClient.from_env(env_file_path=Path(__file__).parent / ".env.api_key")

    # Create search query
    search_data = PublicCreateSearchDto(
        searchString="intelligence",
        searchType=SearchType.vector,
    )

    # Perform search
    response = client.search.search(search_data)
    results = response.data  # Extract the actual search results from ListObjectDto
    print(f"Found {len(results)} search results")

    # Show first few results
    for i, result in enumerate(results[:3]):
        print(f"Result {i+1}:")
        print(f"  ID: {result.get('id', 'N/A')}")
        print(f"  Title: {result.get('title', 'N/A')}")
        print(f"  Key: {result.get('key', 'N/A')}")
        print(f"  URL: {result.get('url', 'N/A')}")
        print()


async def main_async():
    """Simple asynchronous search example."""
    # Initialize client from .env file
    client = UniqueClient.from_env(env_file_path=Path(__file__).parent / ".env.api_key")

    # Create search query with different parameters
    search_data = PublicCreateSearchDto(
        searchString="python programming tutorial",
        searchType=SearchType.combined,
        limit=20,
        page=1,
        chatOnly=False,
        language="en",
    )

    # Perform async search
    response = await client.search.search_async(search_data)
    results = response.data  # Extract the actual search results from ListObjectDto
    print(f"Found {len(results)} search results")

    # Show first few results
    for i, result in enumerate(results[:3]):
        print(f"Result {i+1}:")
        print(f"  ID: {result.get('id', 'N/A')}")
        print(f"  Title: {result.get('title', 'N/A')}")
        print(f"  Key: {result.get('key', 'N/A')}")
        print(f"  URL: {result.get('url', 'N/A')}")
        print()


def advanced_search_example():
    """Example with more advanced search parameters."""
    client = UniqueClient.from_env(env_file_path=Path(__file__).parent / ".env.api_key")

    # Create search with metadata filter and scope IDs
    search_data = PublicCreateSearchDto(
        searchString="data analysis report",
        searchType=SearchType.combined,
        limit=15,
        page=1,
        chatOnly=True,
        scopeIds=["scope_123", "scope_456"],  # Replace with actual scope IDs
        metaDataFilter={"category": "reports", "year": "2023"},
        language="en",
    )

    # Perform search
    response = client.search.search(search_data)
    results = response.data  # Extract the actual search results from ListObjectDto
    print(f"Advanced search completed: Found {len(results)} results")

    # Show first few results with more details
    for i, result in enumerate(results[:2]):
        print(f"Result {i+1}:")
        print(f"  ID: {result.get('id', 'N/A')}")
        print(f"  Title: {result.get('title', 'N/A')}")
        print(f"  Key: {result.get('key', 'N/A')}")
        print(f"  URL: {result.get('url', 'N/A')}")
        if result.get("internallyStoredAt"):
            print(f"  Stored at: {result.get('internallyStoredAt')}")
        print()


if __name__ == "__main__":
    print("Sync search example:")
    main_sync()

    print("\nAsync search example:")
    asyncio.run(main_async())

    print("\nAdvanced search example:")
    advanced_search_example()
