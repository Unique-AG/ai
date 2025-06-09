import asyncio
from pathlib import Path

from unique_client.unique_client.api_resources.api_dtos import (
    PublicCreateMessageDto,
    PublicUpdateMessageDto,
    Role,
)
from unique_client.unique_client.implementation import UniqueClient


def main_sync():
    """Simple synchronous messages example."""
    # Initialize client from .env file
    client = UniqueClient.from_env(env_file_path=Path(__file__).parent / ".env.api_key")

    # TODO: Example chat ID - replace with actual chat ID
    chat_id = "chat_example_123"
    assistant_id = "assistant_example_456"

    print("=== Listing Messages ===")
    # List all messages in the chat
    response = client.chat.messages.list(chat_id=chat_id)
    messages = response.data  # Extract the actual messages from ListObjectDto
    print(f"Found {len(messages)} messages in chat")

    # Show first few messages
    for i, message in enumerate(messages[:3]):
        print(f"Message {i+1}:")
        print(f"  ID: {message.get('id', 'N/A')}")
        print(f"  Role: {message.get('role', 'N/A')}")
        print(f"  Text: {message.get('text', 'N/A')}")
        print(f"  Created: {message.get('createdAt', 'N/A')}")
        print()

    print("=== Creating a New Message ===")
    # Create a new message
    create_data = PublicCreateMessageDto(
        chatId=chat_id,
        assistantId=assistant_id,
        text="Hello, this is a test message from the SDK!",
        role=Role.user,
    )

    new_message = client.chat.messages.create(create_data)
    print(f"Created message with ID: {new_message.id}")
    print(f"Message text: {new_message.text}")
    print()

    # Get the message ID for further operations
    message_id = new_message.id

    print("=== Retrieving a Message ===")
    # Retrieve the specific message
    retrieved_message = client.chat.messages.retrieve(message_id, chat_id)
    print("Retrieved message:")
    print(f"  ID: {retrieved_message.id}")
    print(f"  Role: {retrieved_message.role}")
    print(f"  Text: {retrieved_message.text}")
    print()

    print("=== Updating a Message ===")
    # Update the message
    update_data = PublicUpdateMessageDto(
        chatId=chat_id,
        text="Updated message text from the SDK!",
    )

    updated_message = client.chat.messages.update(message_id, update_data)
    print("Updated message:")
    print(f"  ID: {updated_message.id}")
    print(f"  Text: {updated_message.text}")
    print()

    print("=== Deleting a Message ===")
    # Delete the message
    delete_result = client.chat.messages.delete(message_id, chat_id)
    print(f"Deleted message: {delete_result.deleted}")
    print(f"Message ID: {delete_result.id}")


async def main_async():
    """Simple asynchronous messages example."""
    # Initialize client from .env file
    client = UniqueClient.from_env(env_file_path=Path(__file__).parent / ".env.api_key")

    # Example chat ID - replace with actual chat ID
    chat_id = "chat_example_123"
    assistant_id = "assistant_example_456"

    print("=== Async: Creating and Managing Messages ===")

    # Create a new message
    create_data = PublicCreateMessageDto(
        chatId=chat_id,
        assistantId=assistant_id,
        text="Hello from async function!",
        role=Role.user,
    )

    new_message = await client.chat.messages.create_async(create_data)
    print(f"Async created message with ID: {new_message.id}")

    # List messages
    response = await client.chat.messages.list_async(chat_id=chat_id)
    messages = response.data
    print(f"Async found {len(messages)} messages in chat")

    # Clean up - delete the message
    delete_result = await client.chat.messages.delete_async(new_message.id, chat_id)
    print(f"Async deleted message: {delete_result.deleted}")


def advanced_message_example():
    """Example with more advanced message parameters."""
    client = UniqueClient.from_env(env_file_path=Path(__file__).parent / ".env.api_key")

    chat_id = "chat_example_123"
    assistant_id = "assistant_example_456"

    print("=== Advanced Message Creation ===")

    # Create a message with references and debug info
    create_data = PublicCreateMessageDto(
        chatId=chat_id,
        assistantId=assistant_id,
        text="Advanced message with metadata",
        originalText="Original text before processing",
        role=Role.assistant,
        references=[],  # Add references if needed
        debugInfo={"processingTime": 1.5, "tokens": 50},
    )

    advanced_message = client.chat.messages.create(create_data)
    print("Created advanced message:")
    print(f"  ID: {advanced_message.id}")
    print(f"  Role: {advanced_message.role}")
    print(f"  Text: {advanced_message.text}")
    print(f"  Original Text: {advanced_message.original_text}")
    print(f"  Debug Info: {advanced_message.debug_info}")

    # Clean up
    client.chat.messages.delete(advanced_message.id, chat_id)
    print("Cleaned up advanced message")


if __name__ == "__main__":
    print("Sync messages example:")
    try:
        main_sync()
    except Exception as e:
        print(f"Sync example failed: {e}")

    print("\nAsync messages example:")
    try:
        asyncio.run(main_async())
    except Exception as e:
        print(f"Async example failed: {e}")

    print("\nAdvanced messages example:")
    try:
        advanced_message_example()
    except Exception as e:
        print(f"Advanced example failed: {e}")
