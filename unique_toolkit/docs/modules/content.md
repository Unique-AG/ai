# Content Module

!!! warning "Deprecated"
    This module is deprecated. Use `KnowledgeBaseService` instead.

The Content module provides low-level functionality for interacting with content stored in the knowledge base.

## Overview

The `unique_toolkit.content` module encompasses all content-related functionality. Content can be any type of textual data that is stored in the Knowledgebase on the Unique platform. During ingestion, content is parsed, split into chunks, indexed, and stored in the database.

**Note:** This module is deprecated. Please use `KnowledgeBaseService` from `unique_toolkit.services.knowledge_base` for all knowledge base operations.

## Components

### Service
::: unique_toolkit.content.service.ContentService

### Schemas
::: unique_toolkit.content.schemas.Content
::: unique_toolkit.content.schemas.ContentChunk
::: unique_toolkit.content.schemas.ContentSearchType
::: unique_toolkit.content.schemas.ContentRerankerConfig

### Functions
::: unique_toolkit.content.functions.search_content_chunks
::: unique_toolkit.content.functions.search_contents
::: unique_toolkit.content.functions.upload_content
::: unique_toolkit.content.functions.download_content

### Utilities
::: unique_toolkit.content.utils.sort_content_chunks
::: unique_toolkit.content.utils.merge_content_chunks
::: unique_toolkit.content.utils.count_tokens

