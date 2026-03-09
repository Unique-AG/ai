# %%

import os
import re
from pathlib import Path

from dotenv import load_dotenv

import unique_sdk
from unique_sdk._list_object import ListObject
from unique_sdk._unique_ql import UQLOperator as UQLOperator
from unique_sdk.api_resources._search import Search
from unique_toolkit.language_model.schemas import LanguageModelMessages


def format_search_results(search_results: ListObject[Search]) -> str:
    """Format search results into a structured string format.

    Args:
        search_results (list): List of search result objects with document information

    Returns:
        str: Formatted string with all search results in the format <source${index}>${document}${topic}${text}</source${index}>

    """
    results = search_results.data
    formatted_results = []

    for index, result in enumerate(results):
        # Extract document name from the text field using regex if available
        document = result.get("key", "Unknown Document")

        # Extract topic from metadata if available
        topic = result.get("metadata", {}).get("topic", "")
        if topic:
            topic = f" - Topic: {topic}"

        # Get the text content, removing any document and info tags
        text = result.get("text", "")
        # Clean up the text by removing document and info tags
        text = re.sub(r"<\|document\|>(.*?)<\|\/document\|>", "", text)
        text = re.sub(r"<\|info\|>(.*?)<\|\/info\|>", "", text)

        # Remove excessive newlines to make the output more compact
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.strip()

        # Format the result with minimal newlines
        formatted_result = (
            f"<source{index + 1}>{document}{topic}\n{text}</source{index + 1}>"
        )
        formatted_results.append(formatted_result)

    return "\n".join(formatted_results)


def replace_sources_with_titles(
    text: str, search: ListObject[Search]
) -> tuple[str, set[int]]:
    """Replace all occurrences of [sourceX] in the text with {search[X].title}.

    Args:
        text (str): The input text containing [sourceX] references.
        search (list): A list of objects, each having a 'title' attribute.

    Returns:
        tuple: (updated_text, used_indexes)
            updated_text (str): The updated text with [sourceX] replaced.
            used_indexes (set[int]): Set of integers representing the used source indexes (1-based).
    """
    results = search.data
    used_indexes: set[int] = set()

    from re import Match

    def replace_match(match: Match[str]) -> str:
        index = int(match.group(1)) - 1
        if 0 <= index < len(results):
            used_indexes.add(index + 1)  # Store as 1-based index
            item = results[index]
            if getattr(item, "url", None):  # Use url if available
                return f"{{{item.url}}}"
            if getattr(item, "title", None):  # Fallback to title
                return f"{{{item.title}}}"
            return f"{{{item.key}}}"
        return match.group(0)  # Leave the original [sourceX] if index is invalid

    updated_text = re.sub(r"\[source(\d+)\]", replace_match, text)
    return updated_text, used_indexes


def create_llm_messages(
    user_message: str, relevant_sources: ListObject[Search]
) -> LanguageModelMessages:
    SEARCH_CONTEXT = format_search_results(relevant_sources)

    REFERENCE_PROMPT = """
STRICTLY reference each fact you use. A fact is preferably referenced by ONLY ONE source e.g [sourceX]. If you use facts from past conversation, use [conversation] as a reference.

Here is an example on how to reference sources (referenced facts must STRICTLY match the source number):
- Some information retrieved from source N°X.[sourceX]
- Some information retrieved from source N°Y and some information retrieved from source N°Z.[sourceY][sourceZ]
- Some information retrieved from past conversation.[conversation]
"""

    SYSTEM_PROMPT = f"""You are helping the employees with their questions. You will find below a question, some information sources and the past conversation (they are delimited with XML tags).

Answer the employee's question using ONLY facts from the sources or past conversation. Information helping the employee's question can also be added.

If not specified, format the answer using an introduction followed by a list of bullet points. The facts you add should ALWAYS help answering the question.

{REFERENCE_PROMPT}
"""

    # User prompt without history
    USER_PROMPT = f"""question:
    ```
    {user_message}
    ```
    
    uploaded document:
    ```
    {SEARCH_CONTEXT}
    ```
    
    question:
    ```
    {user_message}
    ```
    
    Answer in English.
    Answer using ONLY information from the uploaded document and ALWAYS reference each of your facts:"""

    builder = LanguageModelMessages([]).builder()
    messages = (
        builder.system_message_append(SYSTEM_PROMPT)
        .user_message_append(USER_PROMPT)
        .build()
    )

    return messages


if __name__ == "__main__":
    load_dotenv(Path(__file__).parent / ".." / ".env.api_key")

    # Set up SDK configuration
    unique_sdk.api_key = os.getenv("API_KEY", "")
    unique_sdk.app_id = os.getenv("APP_ID", "")
    unique_sdk.api_base = os.getenv("API_BASE", "")
    company_id = os.getenv("COMPANY_ID", "")
    user_id = os.getenv("USER_ID", "")

    # filter for a specific folder in the knowledge base
    metadata_filter = {
        "and": [
            {
                "operator": "equals",
                "value": "uniquepathid://scope_btfo28b3xhlwh5obwgea71bl",
                "path": [
                    "folderIdPath",
                ],
            },
        ]
    }

    user_message = "what does the code of conduct say?"

    # Retrieve ALL content uploaded to the Knowledge Base that might be relevant to the user's question
    # and is within the metadata filtered folder
    relevant_sources: ListObject[Search] = unique_sdk.Search.create(
        user_id=user_id,
        company_id=company_id,
        searchString=user_message,
        searchType="VECTOR",
        chatOnly=False,
        language="English",
        limit=20,
        metaDataFilter=metadata_filter,
    )

    messages = create_llm_messages(user_message, relevant_sources)

    response = unique_sdk.ChatCompletion.create(
        company_id=company_id,
        messages=messages.model_dump(mode="json"),
        model="AZURE_GPT_4o_2024_0806",
        timeout=8000,  # in ms
    )

    answer = response.choices[0]["message"]["content"]
    print(answer)

    updated_text, used_indexes = replace_sources_with_titles(answer, relevant_sources)
    print(updated_text)
    print("Used sources:", used_indexes)
    print(relevant_sources.data[0].title)

    for index in used_indexes.copy():
        print(relevant_sources.data[index - 1])
