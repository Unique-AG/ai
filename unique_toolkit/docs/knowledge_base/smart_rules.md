# Filtering with Smart Rules

A powerful mechanism to obtain more relevant information from the knowledge base are `smart rules`. These rules act as conditionals to reduce the amount of retrieved information. A smart rule is a logical statement that either evaluates to `true` or `false` given the metadata of the documents.

## Why use smart rules?

- Narrow search results to specific folders, file types, or custom metadata
- Reduce irrelevant results and improve search precision
- Combine multiple filtering criteria with AND/OR logic

## Smart Rule Definition 

In its simplest form, a smart rule needs three components:

1. `path`: A list representing the path to a metadata field (e.g., `["title"]`, `["metadata", "category"]`)
2. `operator`: The comparison operator (e.g., `EQUALS`, `CONTAINS`, `GREATER_THAN`)
3. `value`: The value to compare against

## Standard Metadata

The following metadata paths are available by default:

| Metadata Path | Description | 
|--|--|
| `key` | The title of the document when it was ingested | 
| `url` | The url where the document can be retrieved from | 
| `title` | The title if changed after ingestion | 
| `folderId` | The `scope_id` of the folder that contains the file| 
| `mimeType` | The mime type of the ingested file| 
| `folderIdPath`| A pathlike construct combining the `scope_id`'s of the folders leading to the document | 

## Common Use Cases

### Filter by Document Title
Use `CONTAINS` to match partial title text (case-insensitive).

### Filter by MIME Type
Use `EQUALS` for exact matches (e.g., only PDF files).

### Filter Content in a Folder and Its Subfolders
The folder must be identified through its `scope_id`. Use `CONTAINS` to include all nested subfolders.

### Filter Content in a Specific Folder Only
If a restriction on the content in a specific folder is desired (excluding subfolders), use `EQUALS` instead of `CONTAINS`.

### Custom Metadata
Custom metadata can be used like normal metadata.

### Combining Smart Rules
Smart rules can be combined using logical operators to create complex filtering logic:

- `AndStatement`: All conditions must be true (intersection)
- `OrStatement`: At least one condition must be true (union)

You can nest these statements to create even more complex logic, such as:

- `(folder_A OR folder_B) AND mime_type = PDF`
- `(title CONTAINS "report") AND (year = 2024 OR year = 2025)`

## Using the Metadata Filter

### For Content Chunk Search

Metadata filters enhance search precision by limiting results to documents that match specific criteria. This combines semantic/keyword search with metadata-based filtering for highly targeted results.

Once you've defined a smart rule, pass it to the search function via the `metadata_filter` parameter.

For implementation examples, see the [Smart Rules Examples](../../modules/examples/content/smart_rules#using-the-metadatafilter).

### For Content Info Search

Retrieve file metadata and information without searching text content. This is useful when you need to list, audit, or manage files based on their metadata rather than their content.

**What you get:**

- File metadata (title, MIME type, size, dates)
- Folder information
- Custom metadata
- File IDs for download or deletion
- **No text chunks** - just file information

**Use cases:**

- Check what your smart rule finds before deletion

**Pagination:** This method returns paginated results, making it efficient for large result sets.

### For Bulk Content Deletion

Metadata filters can be used to delete multiple files at once based on their metadata. This is useful for cleanup operations but should be used with caution.

**⚠️ Warning:** This operation is irreversible and will permanently delete all content matching the filter criteria.

**Use cases:**

- Cleaning up files in a specific folder after project completion
- Removing all files of a certain type (e.g., temporary files)
- Bulk deletion based on custom metadata (e.g., expired content)

**Best practice:** Always test your filter with `search_contents()` first to verify which files will be affected before deleting.

### For Bulk Metadata Updates

Update or add metadata fields to multiple files at once based on a metadata filter. This is useful for tagging, categorizing, or enriching file metadata without modifying the files themselves.

**What it does:**

- Adds new metadata fields to matching files
- Updates existing metadata fields (merges with existing metadata)
- Preserves other metadata that isn't specified in the update
- Returns the updated content information

**Use cases:**

- Tag all files in a folder with a project identifier
- Add classification or department labels to existing files
- Update version numbers or status fields in bulk
- Enrich metadata based on file location or type

### For Bulk Metadata Removal

Remove specific metadata fields from multiple files at once. This is useful for cleaning up obsolete metadata or removing sensitive information.

**What it does:**

- Removes specified metadata keys from matching files
- Leaves other metadata fields intact
- Does not affect file content or standard metadata (title, MIME type, etc.)
- Returns the updated content information

**Use cases:**

- Remove temporary or expired metadata fields
- Clean up metadata from deprecated workflows
- Remove sensitive metadata that's no longer needed
- Standardize metadata by removing inconsistent fields

**Best practice:** Test your filter with `get_paginated_content_infos()` first to see which files will be affected and what metadata they currently have.

## Full Examples

For complete, runnable examples of all smart rules features, see the [Smart Rules Examples](../../modules/examples/content/smart_rules) section.

