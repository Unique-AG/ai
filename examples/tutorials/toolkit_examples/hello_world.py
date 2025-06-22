import os
import asyncio
import traceback
from dotenv import load_dotenv
from unique_toolkit.language_model import functions as llm_functions
from unique_toolkit.app import init_sdk
from unique_toolkit import LanguageModelMessages
from unique_toolkit.language_model import LanguageModelName

load_dotenv()

async def main():
    print("Initializing Unique Toolkit...")

    try:
        company_id = os.environ["COMPANY_ID"]

    except KeyError as e:
        print(f"Error: Missing environment variable from .env file: {e}")
        return

    init_sdk()
    

    builder = LanguageModelMessages([]).builder()
    messages = builder.system_message_append("You are a friendly bot.").user_message_append("Hello, world!").build()
    
    try:
        assistant_response = await llm_functions.complete_async(
            company_id=company_id,
            messages=messages,
            model_name=LanguageModelName.AZURE_GPT_4o_2024_0513
        )

        print("\n--- Assistant's Response ---")
        if assistant_response:
            print(f"Assistant: {assistant_response}")
        else:
            print("Did not receive a response from the assistant.")
        print("--------------------------\n")

    except Exception:
        print(f"\nTraceback while sending message:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
