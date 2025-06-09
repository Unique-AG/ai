import asyncio
from pathlib import Path

from unique_client.unique_client.api_resources.api_dtos import (
    ContentWhereInput,
    SearchDto,
    StringNullableFilter,
)
from unique_client.unique_client.implementation import UniqueClient


def main_sync():
    """Simple synchronous content search example."""
    # Initialize client from .env file
    client = UniqueClient.from_env(env_file_path=Path(__file__).parent / ".env.api_key")

    # Create search query
    search_data = SearchDto(
        where=ContentWhereInput(title=StringNullableFilter(contains="42")),
    )

    # Perform search
    results = client.content.search(search_data)
    print(f"Found {len(results)} results")

    # Show first few results
    for result in results[:3]:
        print(f"- {result.title} (ID: {result.id})")


async def main_async():
    """Simple asynchronous content search example."""
    # Initialize client from .env file
    client = UniqueClient.from_env(env_file_path=Path(__file__).parent / ".env.api_key")

    # Create search query
    search_data = SearchDto(
        where=ContentWhereInput(title=StringNullableFilter(contains="42")),
    )

    # Perform async search
    results = await client.content.search_async(search_data)
    print(f"Found {len(results)} results")

    # Show first few results
    for result in results[:3]:
        print(f"- {result.title} (ID: {result.id})")


if __name__ == "__main__":
    print("Sync example:")
    main_sync()

    print("\nAsync example:")
    asyncio.run(main_async())


# %%
