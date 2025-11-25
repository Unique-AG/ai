# Examples

Complete examples demonstrating common use cases and integration patterns with the Unique SDK.

## Table of Contents

- [Chat Assistant](#chat-assistant)
- [Knowledge Base Management](#knowledge-base-management)
- [Advanced Search](#advanced-search)
- [Streaming Responses](#streaming-responses)
- [Webhook Integration](#webhook-integration)
- [Async Batch Processing](#async-batch-processing)
- [Working with Spaces](#working-with-spaces)
- [Agentic Tables (Magic Tables)](#agentic-tables-magic-tables)

## Chat Assistant

??? example "Build a simple chat assistant that responds to user messages"

    ```python
    import unique_sdk

    # Configure SDK
    unique_sdk.api_key = "ukey_..."
    unique_sdk.app_id = "app_..."

    def create_chat_assistant(user_id, company_id, assistant_id):
        """
        Create a simple chat assistant.
        """
        # Create a new chat or use existing chat_id
        chat_id = None
        
        while True:
            # Get user input
            user_message = input("You: ")
            if user_message.lower() in ['exit', 'quit']:
                break
            
            # Create user message
            user_msg = unique_sdk.Message.create(
                user_id=user_id,
                company_id=company_id,
                chatId=chat_id,
                assistantId=assistant_id,
                text=user_message,
                role="USER"
            )
            
            # Get or set chat_id from first message
            if not chat_id:
                chat_id = user_msg.chatId
            
            # Wait for assistant response
            # In production, use webhooks instead of polling
            import time
            time.sleep(2)
            
            # Get latest messages
            messages = unique_sdk.Message.list(
                user_id=user_id,
                company_id=company_id,
                chatId=chat_id
            )
            
            # Find assistant's response
            for msg in messages.data:
                if msg.role == "ASSISTANT" and msg.createdAt > user_msg.createdAt:
                    print(f"Assistant: {msg.text}")
                    break

    # Usage
    create_chat_assistant(
        user_id="user_123",
        company_id="company_456",
        assistant_id="assistant_abc"
    )
    ```

## Knowledge Base Management

??? example "Upload, organize, and manage documents in the knowledge base"

    ```python
    import unique_sdk
    from unique_sdk.utils import file_io
    import os

    unique_sdk.api_key = "ukey_..."
    unique_sdk.app_id = "app_..."

    def upload_directory(user_id, company_id, directory_path, scope_id):
        """
        Upload all PDF files from a directory to the knowledge base.
        """
        uploaded_files = []
        
        for filename in os.listdir(directory_path):
            if filename.endswith('.pdf'):
                file_path = os.path.join(directory_path, filename)
                
                try:
                    print(f"Uploading {filename}...")
                    
                    content = file_io.upload_file(
                        company_id=company_id,
                        user_id=user_id,
                        path_to_file=file_path,
                        displayed_filename=filename,
                        mime_type="application/pdf",
                        scope_or_unique_path=scope_id,
                        ingestion_config={
                            "chunkStrategy": "default",
                            "chunkMaxTokens": 1000,
                            "uniqueIngestionMode": "standard"
                        }
                    )
                    
                    uploaded_files.append({
                        'filename': filename,
                        'content_id': content.id
                    })
                    
                    print(f"✓ Uploaded: {content.id}")
                    
                except Exception as e:
                    print(f"✗ Failed to upload {filename}: {e}")
        
        return uploaded_files

    def organize_by_folders(user_id, company_id):
        """
        Create folder structure and organize content.
        """
        # Create folder structure
        folders = [
            "/Company/Reports/Q1",
            "/Company/Reports/Q2",
            "/Company/Policies"
        ]
        
        unique_sdk.Folder.create_paths(
            user_id=user_id,
            company_id=company_id,
            paths=folders
        )
        
        print("Folders created")
        
        # Move content to appropriate folder
        # Get Q1 folder info
        folder_info = unique_sdk.Folder.get_info(
            user_id=user_id,
            company_id=company_id,
            folderPath="/Company/Reports/Q1"
        )
        
        # Move a file
        unique_sdk.Content.update(
            user_id=user_id,
            company_id=company_id,
            contentId="cont_xyz",
            ownerId=folder_info.id
        )
        
        print("Content organized")

    # Usage
    uploaded = upload_directory(
        user_id="user_123",
        company_id="company_456",
        directory_path="/path/to/pdfs",
        scope_id="scope_xyz"
    )

    organize_by_folders("user_123", "company_456")
    ```

    ## Advanced Search

    Implement advanced search with filtering, reranking, and metadata.

    ```python
    import unique_sdk
    from unique_sdk import UQLOperator, UQLCombinator

    unique_sdk.api_key = "ukey_..."
    unique_sdk.app_id = "app_..."

    def advanced_search_with_filters(user_id, company_id, query, scope_ids=None):
        """
        Perform advanced search with metadata filtering and reranking.
        """
        # Create metadata filter using UniqueQL
        metadata_filter = {
            UQLCombinator.AND: [
                {
                    "path": ["title"],
                    "operator": UQLOperator.CONTAINS,
                    "value": "report"
                },
                {
                    UQLCombinator.OR: [
                        {
                            "path": ["year"],
                            "operator": UQLOperator.EQUALS,
                            "value": "2024"
                        },
                        {
                            "path": ["year"],
                            "operator": UQLOperator.EQUALS,
                            "value": "2023"
                        }
                    ]
                }
            ]
        }
        
        # Perform search
        results = unique_sdk.Search.create(
            user_id=user_id,
            company_id=company_id,
            searchString=query,
            searchType="COMBINED",  # Vector + Full-text
            metaDataFilter=metadata_filter,
            scopeIds=scope_ids or [],
            limit=50,
            scoreThreshold=0.7,
            reranker={"deploymentName": "my_reranker"},
            language="English"
        )
        
        return results

    def semantic_search_with_context(user_id, company_id, chat_id, user_query):
        """
        Perform semantic search with chat context.
        """
        # Transform user query with chat context
        search_string = unique_sdk.SearchString.create(
            user_id=user_id,
            company_id=company_id,
            prompt=user_query,
            chat_id=chat_id
        )
        
        print(f"Original: {user_query}")
        print(f"Enhanced: {search_string.searchString}")
        
        # Perform search with enhanced query
        results = unique_sdk.Search.create(
            user_id=user_id,
            company_id=company_id,
            chatId=chat_id,
            searchString=search_string.searchString,
            searchType="VECTOR",
            limit=20
        )
        
        return results

    def multi_scope_search(user_id, company_id, query, scope_list):
        """
        Search across multiple scopes and merge results.
        """
        from unique_sdk.utils import sources
        
        all_results = []
        
        for scope_id in scope_list:
            results = unique_sdk.Search.create(
                user_id=user_id,
                company_id=company_id,
                searchString=query,
                searchType="VECTOR",
                scopeIds=[scope_id],
                limit=10
            )
            all_results.extend(results.data)
        
        # Merge and deduplicate sources
        merged = sources.merge_sources(all_results)
        sorted_results = sources.sort_sources(merged)
        
        return sorted_results

    # Usage
    results = advanced_search_with_filters(
        user_id="user_123",
        company_id="company_456",
        query="quarterly financial performance",
        scope_ids=["scope_abc", "scope_def"]
    )

    for result in results.data[:5]:
        print(f"Score: {result.score:.3f}")
        print(f"Source: {result.key}")
        print(f"Text: {result.text[:200]}...")
        print("---")
    ```

## Streaming Responses

??? example "Stream AI-generated responses to the chat frontend"

    ```python
    import unique_sdk

    unique_sdk.api_key = "ukey_..."
    unique_sdk.app_id = "app_..."

    def stream_response_to_chat(
        user_id,
        company_id,
        chat_id,
        user_message_id,
        assistant_message_id,
        system_prompt,
        search_context=None
    ):
        """
        Stream an AI-generated response to the chat UI.
        """
        # Get chat history
        from unique_sdk.utils import chat_history
        
        history = chat_history.load_history(
            user_id,
            company_id,
            chat_id,
            maxTokens=8000,
            percentOfMaxTokens=0.15,
            maxMessages=4
        )
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        messages.extend(history)
        
        # Add search context to system message if available
        if search_context:
            context_text = "\n\n".join([
                f"[source{i}] {item['text']}"
                for i, item in enumerate(search_context)
            ])
            messages[0]["content"] += f"\n\nContext:\n{context_text}"
        
        # Stream response
        unique_sdk.Integrated.chat_stream_completion(
            user_id=user_id,
            company_id=company_id,
            assistantMessageId=assistant_message_id,
            userMessageId=user_message_id,
            messages=messages,
            chatId=chat_id,
            searchContext=search_context or [],
            model="AZURE_GPT_4o_2024_1120",
            timeout=30000,
            options={"temperature": 0.7},
            startText="Let me help you with that...",
            debugInfo={"version": "1.0", "model": "gpt-4"}
        )

    # Usage with RAG (Retrieval-Augmented Generation)
    def rag_stream_response(user_id, company_id, chat_id, user_query):
        """
        Perform RAG: Search, then stream response with sources.
        """
        # 1. Search for relevant context
        search_results = unique_sdk.Search.create(
            user_id=user_id,
            company_id=company_id,
            chatId=chat_id,
            searchString=user_query,
            searchType="COMBINED",
            limit=10,
            scoreThreshold=0.7
        )
        
        # 2. Format search context
        search_context = [
            {
                "id": result.id,
                "chunkId": result.chunkId,
                "key": result.key,
                "sequenceNumber": i + 1,
                "url": result.url
            }
            for i, result in enumerate(search_results.data)
        ]
        
        # 3. Create user message
        user_msg = unique_sdk.Message.create(
            user_id=user_id,
            company_id=company_id,
            chatId=chat_id,
            text=user_query,
            role="USER"
        )
        
        # 4. Create empty assistant message
        assistant_msg = unique_sdk.Message.create(
            user_id=user_id,
            company_id=company_id,
            chatId=chat_id,
            text="",
            role="ASSISTANT"
        )
        
        # 5. Stream response
        stream_response_to_chat(
            user_id=user_id,
            company_id=company_id,
            chat_id=chat_id,
            user_message_id=user_msg.id,
            assistant_message_id=assistant_msg.id,
            system_prompt="You are a helpful assistant. Answer based on the provided context.",
            search_context=search_context
        )
    ```

## Webhook Integration

??? example "Complete Flask application with webhook handling"

    ```python
    from flask import Flask, request, jsonify
    from http import HTTPStatus
    import unique_sdk
    import os

    app = Flask(__name__)

    # Configuration
    unique_sdk.api_key = os.environ.get("UNIQUE_API_KEY")
    unique_sdk.app_id = os.environ.get("UNIQUE_APP_ID")
    endpoint_secret = os.environ.get("UNIQUE_ENDPOINT_SECRET")

    @app.route("/webhook", methods=["POST"])
    def webhook():
        """Handle incoming webhooks from Unique."""
        payload = request.data
        sig_header = request.headers.get("X-Unique-Signature")
        timestamp = request.headers.get("X-Unique-Created-At")
        
        if not sig_header or not timestamp:
            return jsonify(success=False), HTTPStatus.BAD_REQUEST
        
        try:
            # Verify webhook signature
            event = unique_sdk.Webhook.construct_event(
                payload, sig_header, timestamp, endpoint_secret
            )
            
            # Route to appropriate handler
            if event.event == "unique.chat.user-message.created":
                handle_user_message(event)
                
            elif event.event == "unique.chat.external-module.chosen":
                handle_external_module(event)
            
            return jsonify(success=True), HTTPStatus.OK
            
        except unique_sdk.SignatureVerificationError as e:
            print(f"⚠️ Webhook signature verification failed: {e}")
            return jsonify(success=False), HTTPStatus.BAD_REQUEST
        except Exception as e:
            print(f"⚠️ Webhook processing error: {e}")
            return jsonify(success=False), HTTPStatus.INTERNAL_SERVER_ERROR

    def handle_user_message(event):
        """Handle new user messages."""
        user_id = event.userId
        company_id = event.companyId
        chat_id = event.payload.chatId
        text = event.payload.text
        
        print(f"New message in chat {chat_id}: {text}")
        
        # Your custom logic here
        # For example, trigger a search or process the message

    def handle_external_module(event):
        """Handle external module selection."""
        user_id = event.userId
        company_id = event.companyId
        chat_id = event.payload.chatId
        module_name = event.payload.name
        user_message_id = event.payload.userMessage.id
        assistant_message_id = event.payload.assistantMessage.id
        
        print(f"External module '{module_name}' chosen in chat {chat_id}")
        
        # Process with your custom module
        if module_name == "custom-search":
            # Perform custom search
            results = unique_sdk.Search.create(
                user_id=user_id,
                company_id=company_id,
                chatId=chat_id,
                searchString=event.payload.userMessage.text,
                searchType="COMBINED",
                limit=20
            )
            
            # Update assistant message with results
            response_text = f"Found {len(results.data)} results:\n\n"
            for i, result in enumerate(results.data[:5], 1):
                response_text += f"{i}. {result.key}\n"
            
            unique_sdk.Message.modify(
                user_id=user_id,
                company_id=company_id,
                id=assistant_message_id,
                chatId=chat_id,
                text=response_text
            )

    if __name__ == "__main__":
        app.run(host="0.0.0.0", port=5000)
    ```

    ## Async Batch Processing

    Process multiple operations concurrently for better performance.

    ```python
    import asyncio
    import unique_sdk

    unique_sdk.api_key = "ukey_..."
    unique_sdk.app_id = "app_..."

    async def batch_search_queries(user_id, company_id, queries):
        """
        Execute multiple search queries concurrently.
        """
        tasks = [
            unique_sdk.Search.create_async(
                user_id=user_id,
                company_id=company_id,
                searchString=query,
                searchType="VECTOR",
                limit=10
            )
            for query in queries
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Query {i} failed: {result}")
            else:
                print(f"Query {i}: {len(result.data)} results")
        
        return [r for r in results if not isinstance(r, Exception)]

    async def batch_content_operations(user_id, company_id, content_ids):
        """
        Fetch multiple content items concurrently.
        """
        tasks = [
            unique_sdk.Content.get_infos_async(
                user_id=user_id,
                company_id=company_id,
                parentId=content_id
            )
            for content_id in content_ids
        ]
        
        results = await asyncio.gather(*tasks)
        return results

    async def parallel_rag_pipeline(user_id, company_id, chat_id, user_query):
        """
        Execute RAG pipeline steps in parallel where possible.
        """
        # Step 1: Search and get search string in parallel
        search_task = unique_sdk.Search.create_async(
            user_id=user_id,
            company_id=company_id,
            chatId=chat_id,
            searchString=user_query,
            searchType="VECTOR",
            limit=10
        )
        
        search_string_task = unique_sdk.SearchString.create_async(
            user_id=user_id,
            company_id=company_id,
            prompt=user_query,
            chat_id=chat_id
        )
        
        search_results, enhanced_query = await asyncio.gather(
            search_task,
            search_string_task
        )
        
        print(f"Enhanced query: {enhanced_query.searchString}")
        print(f"Found {len(search_results.data)} results")
        
        return search_results, enhanced_query

    # Usage
    async def main():
        queries = [
            "What is machine learning?",
            "Explain neural networks",
            "What is deep learning?",
            "How does AI work?"
        ]
        
        results = await batch_search_queries(
            user_id="user_123",
            company_id="company_456",
            queries=queries
        )
        
        print(f"Completed {len(results)} searches")

    # Run
    asyncio.run(main())
    ```

    ## Working with Spaces

    Interact with conversational spaces and assistants.

    ```python
    import unique_sdk
    from unique_sdk.utils.chat_in_space import (
        send_message_and_wait_for_completion,
        chat_against_file
    )

    unique_sdk.api_key = "ukey_..."
    unique_sdk.app_id = "app_..."

    async def chat_in_space_example(user_id, company_id, assistant_id):
        """
        Send a message to a space and wait for completion.
        """
        # Send message and wait for response
        latest_message = await send_message_and_wait_for_completion(
            user_id=user_id,
            company_id=company_id,
            assistant_id=assistant_id,
            text="Tell me about quantum computing",
            tool_choices=["WebSearch", "InternalSearch"],
            scope_rules={
                "or": [
                    {
                        "operator": "contains",
                        "path": ["folderIdPath"],
                        "value": "uniquepathid://scope_tech_docs"
                    }
                ]
            },
            poll_interval=2,
            max_wait=120
        )
        
        print(f"Assistant response: {latest_message.text}")
        return latest_message

    async def chat_with_document(user_id, company_id, assistant_id):
        """
        Upload a document and chat against it.
        """
        result = await chat_against_file(
            user_id=user_id,
            company_id=company_id,
            assistant_id=assistant_id,
            path_to_file="/path/to/document.pdf",
            displayed_filename="document.pdf",
            mime_type="application/pdf",
            text="Summarize the key points in bullet format",
            should_delete_chat=True  # Clean up after
        )
        
        print(f"Summary: {result.text}")
        return result

    def manage_space_chats(user_id, company_id, space_id):
        """
        Manage chats within a space.
        """
        # Get space information
        space_info = unique_sdk.Space.get_space(
            user_id=user_id,
            company_id=company_id,
            space_id=space_id
        )
        
        print(f"Space: {space_info.name}")
        print(f"Modules: {space_info.modules}")
        
        # Create a message (starts new chat if no chat_id provided)
        message = unique_sdk.Space.create_message(
            user_id=user_id,
            company_id=company_id,
            assistantId=space_id,
            text="Hello, I need help",
            toolChoices=["WebSearch"]
        )
        
        chat_id = message.chatId
        
        # Get chat messages
        messages = unique_sdk.Space.get_chat_messages(
            user_id=user_id,
            company_id=company_id,
            chat_id=chat_id,
            skip=0,
            take=50
        )
        
        for msg in messages.data:
            print(f"{msg.role}: {msg.text}")
        
        # Delete chat when done
        unique_sdk.Space.delete_chat(
            user_id=user_id,
            company_id=company_id,
            chat_id=chat_id
        )

    # Usage
    import asyncio

    asyncio.run(chat_in_space_example(
        user_id="user_123",
        company_id="company_456",
        assistant_id="assistant_abc"
    ))
    ```

    ## Agentic Tables (Magic Tables)

    Work with AI-powered interactive tables.

    ```python
    import unique_sdk
    from datetime import datetime

    unique_sdk.api_key = "ukey_..."
    unique_sdk.app_id = "app_..."

    async def create_and_populate_table(user_id, company_id, table_id):
        """
        Create and populate a magic table with data.
        """
        # Set multiple cells at once
        cells_data = []
        for row in range(5):
            for col in range(3):
                cells_data.append({
                    "rowOrder": row,
                    "columnOrder": col,
                    "text": f"Cell ({row}, {col})"
                })
        
        result = await unique_sdk.AgenticTable.set_multiple_cells(
            user_id=user_id,
            company_id=company_id,
            tableId=table_id,
            cells=cells_data
        )
        
        print(f"Populated {len(cells_data)} cells")
        
        # Set column metadata
        await unique_sdk.AgenticTable.set_column_metadata(
            user_id=user_id,
            company_id=company_id,
            tableId=table_id,
            columnOrder=0,
            columnWidth=200,
            editable=True,
            cellRenderer="SelectableCellRenderer"
        )
        
        return result

    async def process_table_with_ai(user_id, company_id, table_id):
        """
        Process table cells with AI and track progress.
        """
        # Set activity status
        await unique_sdk.AgenticTable.set_activity(
            user_id=user_id,
            company_id=company_id,
            tableId=table_id,
            activity="UpdateCell",
            status="IN_PROGRESS",
            text="Processing cells with AI"
        )
        
        # Get table data
        sheet_data = await unique_sdk.AgenticTable.get_sheet_data(
            user_id=user_id,
            company_id=company_id,
            tableId=table_id,
            includeCells=True,
            includeLogHistory=True
        )
        
        # Process each cell
        for row_idx, row in enumerate(sheet_data.cells):
            for col_idx, cell in enumerate(row):
                if cell and cell.text:
                    # Process with AI (example: translate or summarize)
                    processed_text = await process_with_ai(cell.text)
                    
                    # Update cell with log entry
                    await unique_sdk.AgenticTable.set_cell(
                        user_id=user_id,
                        company_id=company_id,
                        tableId=table_id,
                        rowOrder=row_idx,
                        columnOrder=col_idx,
                        text=processed_text,
                        logEntries=[{
                            "text": f"Processed by AI",
                            "createdAt": datetime.now().isoformat(),
                            "actorType": "SYSTEM",
                            "details": [{
                                "text": "Applied AI transformation"
                            }]
                        }]
                    )
        
        # Mark activity as completed
        await unique_sdk.AgenticTable.set_activity(
            user_id=user_id,
            company_id=company_id,
            tableId=table_id,
            activity="UpdateCell",
            status="COMPLETED",
            text="All cells processed"
        )
        
        # Update sheet state
        await unique_sdk.AgenticTable.update_sheet_state(
            user_id=user_id,
            company_id=company_id,
            tableId=table_id,
            state="IDLE"
        )

    async def process_with_ai(text):
        """Placeholder for AI processing."""
        # Your AI processing logic here
        return text.upper()

    async def bulk_verify_rows(user_id, company_id, table_id, row_indices):
        """
        Bulk update verification status of rows.
        """
        result = await unique_sdk.AgenticTable.bulk_update_status(
            user_id=user_id,
            company_id=company_id,
            tableId=table_id,
            rowOrders=row_indices,
            status="VERIFIED"
        )
        
        print(f"Verified {len(row_indices)} rows")
        return result

    # Usage
    import asyncio

    async def main():
        user_id = "user_123"
        company_id = "company_456"
        table_id = "sheet_abc"
        
        await create_and_populate_table(user_id, company_id, table_id)
        await process_table_with_ai(user_id, company_id, table_id)
        await bulk_verify_rows(user_id, company_id, table_id, [0, 1, 2, 3, 4])

    asyncio.run(main())
    ```

- Webhook handling with signature verification
- User message and external module event handling
- Search integration
- Chat completion
- Error handling and logging
- Production-ready patterns

## Related Resources

- [Quickstart Guide](quickstart.md)
- [API Reference](sdk.md)
- [Architecture](architecture.md)
- [Error Handling](error-handling.md)

