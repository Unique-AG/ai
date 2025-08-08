import asyncio

from dotenv import load_dotenv
from src.clients.content import ContentClient
from src.utilities import find_date, internal_to_iso_date

load_dotenv()

scope_ids = []
max_concurrent_requests = 25


async def run():
    content_client = ContentClient()
    contents = []
    for scope_id in scope_ids:
        result = await content_client.get_all_in_scope(scope_id)
        contents.extend(result["data"]["content"])
    print(f"Found {len(contents)} contents")

    await process_update_tasks_with_limit(
        content_client, contents, max_concurrent_requests
    )

    content_ids = [content["id"] for content in contents]
    print(f"Marking {len(content_ids)} contents for rebuild")
    await content_client.mark_rebuild_metadata_by_ids(content_ids)

    print(f"Rebuilding metadata for {len(content_ids)} contents")
    await content_client.rebuild_metadata()


async def process_update_tasks_with_limit(content_client, contents, limit):
    semaphore = asyncio.Semaphore(limit)

    async def limited_update(content):
        async with semaphore:
            content_id = content["id"]
            print(f"Processing content ID: {content_id}")

            existing_metadata = content.get("metadata", {})
            title = content.get("key", "")
            default_date = internal_to_iso_date(content.get("createdAt"))
            extracted_metadata = {"validAsOf": find_date(title, default_date)}
            new_metadata = {**existing_metadata, **extracted_metadata}

            print(f"Updating metadata for {content_id}: {extracted_metadata}")
            await content_client.update_metadata(content_id, new_metadata)
            print(f"Completed update for content ID: {content_id}")

    update_tasks = [limited_update(content) for content in contents]
    await asyncio.gather(*update_tasks)


if __name__ == "__main__":
    asyncio.run(run())
