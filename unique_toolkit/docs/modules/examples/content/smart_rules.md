# Filtering with Smart Rules

A powerful mechanism to obtain more relevant information from the knowledge base are `smart rules`. These rules act as conditionals to reduce the amount of retrieved information. A smart rule is a logical statement that either evaluates to `true` or `false` given the metadata of the documents.

**Why use smart rules?**
- Narrow search results to specific folders, file types, or custom metadata
- Reduce irrelevant results and improve search precision
- Combine multiple filtering criteria with AND/OR logic

## Smart Rule Definition 

In its simplest form, a smart rule needs three components:

1. `path`: A list representing the path to a metadata field (e.g., `["title"]`, `["metadata", "category"]`)
2. `operator`: The comparison operator (e.g., `EQUALS`, `CONTAINS`, `GREATER_THAN`)
3. `value`: The value to compare against

## Standard Metada

The following metadata paths are available by default

| Metadata Path | Description | 
| `key` | The title of the document when it was ingested | 
| `url` | The url where the document can be retrieved from | 
| `title` | The title if changed after ingestion | 
| `folderId` | The `scope_id` of the folder that contains the file| 
| `mimeType` | The mime type of the ingested file| 
| `folderIdPath`| A pathlike construct combining the `scope_id`'s of the folders leading to the document | 


##  Examples

The following examples show how to define smart rules in Python: 

<!--
```{.python #smart_rules_imports}
from unique_toolkit.smart_rules.compile import Statement, Operator, AndStatement, OrStatement
```
-->

### 1. Filter by Document Title

Use `CONTAINS` to match partial title text (case-insensitive):

```{.python #smart_rule_file_title}
smart_rule_file_title= Statement(operator=Operator.CONTAINS, 
                                            value="test_title", 
                                            path=["title"])

metadata_filter = smart_rule_file_title.model_dump(mode="json") 
```

### 2. Filter by MIME Type

Use `EQUALS` for exact matches (e.g., only PDF files):

```{.python #smart_rule_mime_type}
smart_rule_mime_type = Statement(operator=Operator.EQUALS, 
                                            value="application/pdf", 
                                            path=["mimeType"])

metadata_filter = smart_rule_mime_type.model_dump(mode="json") 

```

### 3. Filter Content in a Folder and Its Subfolders

The folder must be identified through its `scope_id`. Use `CONTAINS` to include all nested subfolders:

```{.python #smart_rule_folder_and_subfolder}
smart_rule_folder_and_subfolder = Statement(operator=Operator.CONTAINS, 
                                            value=f"{scope_id}", 
                                            path=["folderIdPath"])

metadata_filter = smart_rule_folder_and_subfolder.model_dump(mode="json")
```

### 4. Filter Content in a Specific Folder Only

If a restriction on the content in a specific folder is desired (excluding subfolders), use `EQUALS` instead of `CONTAINS`:

```{.python #smart_rule_folder_content}
smart_rule_folder_content = Statement(operator=Operator.EQUALS, 
                                      value=f"{scope_id}", 
                                      path=["folderId"])

metadata_filter = smart_rule_folder_content.model_dump(mode="json")
```

### 6. Custom Metadata
Custom meta data can be used like normal metadata.


```{.python #smart_rule_custom_metadata}
smart_rule_custom = Statement(operator=Operator.EQUALS, 
                                      value=f"customValue", 
                                      path=["customMetaData"])

metadata_filter = smart_rule_custom.model_dump(mode="json")
```




### 7. Combining Smart Rules: Find PDFs in a Specific Folder

Smart rules can be combined using logical operators to create complex filtering logic:

- `AndStatement`: All conditions must be true (intersection)
- `OrStatement`: At least one condition must be true (union)

This combines the folder and MIME type rules to find only PDF files within a specific folder and its subfolders:

```{.python #smart_rule_mime_type_and_folder_and_sufolder}
smart_rule_folders_and_mime = AndStatement(and_list=[smart_rule_folder_and_subfolder, 
                                                     smart_rule_mime_type])
metadata_filter = smart_rule_folders_and_mime.model_dump(mode="json") 
```

You can nest these statements to create even more complex logic, such as:
- `(folder_A OR folder_B) AND mime_type = PDF`
- `(title CONTAINS "report") AND (year = 2024 OR year = 2025)`



## Using the Metadatafilter

### For Content Chunk Search

Metadata filters enhance search precision by limiting results to documents that match specific criteria. This combines semantic/keyword search with metadata-based filtering for highly targeted results.

Once you've defined a smart rule, pass it to the search function via the `metadata_filter` parameter:

```{.python #kb_service_combined_with_metadafilter}


content_chunks = kb_service.search_content_chunks(
    search_string="Harry Potter",
    search_type=ContentSearchType.COMBINED,
    limit=15,
    metadata_filter=metadata_filter
)
```

<!--
```{.python file=./docs/.python_files/content_chunk_search_with_smart_rule_on_folders.py }
<<smart_rules_imports>>
<<kb_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<smart_rule_folder_content>>
<<kb_service_combined_with_metadafilter>>
```
-->

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

```{.python #kb_content_search}
infos =kb_service.get_paginated_content_infos(
    metadata_filter=metadata_filter
)
```


<!--
```{.python file=./docs/.python_files/content_search_with_smart_rule_on_folders.py }
<<smart_rules_imports>>
<<kb_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<smart_rule_custom_metadata>>
<<kb_content_search>>
```
-->

### For Bulk Content Deletion

Metadata filters can be used to delete multiple files at once based on their metadata. This is useful for cleanup operations but should be used with caution.

**⚠️ Warning:** This operation is irreversible and will permanently delete all content matching the filter criteria.

**Use cases:**
- Cleaning up files in a specific folder after project completion
- Removing all files of a certain type (e.g., temporary files)
- Bulk deletion based on custom metadata (e.g., expired content)

**Best practice:** Always test your filter with `search_contents()` first to verify which files will be affected before deleting.
```{python #upload_with_custom_metadata}
content_bytes = b"Your file content here"
content = kb_service.upload_content_from_bytes(
    content=content_bytes,
    content_name="document_custom.txt",
    mime_type="text/plain",
    scope_id=scope_id,
    metadata={"customMetaData": "customValue", "version": "1.0"}
)
```

```{python #combined_folder_and_custom_metadata}
smart_rule_folders_and_mime = AndStatement(and_list=[smart_rule_folder_content, 
                                                     smart_rule_custom])
metadata_filter = smart_rule_folders_and_mime.model_dump(mode="json") 
```


```{.python #kb_service_delete}
kb_service.delete_contents(
    metadata_filter=metadata_filter
)
```

<!--
```{.python file=./docs/.python_files/deletion_with_smart_rule_on_folders.py }
<<smart_rules_imports>>
<<kb_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<upload_with_custom_metadata>>
<<kb_service_upload_bytes>>
<<smart_rule_custom_metadata>>
<<smart_rule_folder_content>>
<<combined_folder_and_custom_metadata>>
<<kb_service_delete>>
```
-->


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

**Example: Add a department tag to all PDFs in a folder**

```{.python #kb_service_update_metadata}
# Update metadata for all files matching the filter
updated_contents = kb_service.update_contents_metadata(
    additional_metadata={
        "department": "legal",
        "classification": "confidential",
        "last_reviewed": "2025-01-01"
    },
    metadata_filter=metadata_filter
)

print(f"Updated metadata for {len(updated_contents)} files")
```

<!--
```{.python file=./docs/.python_files/update_metadata_with_smart_rule.py }
<<smart_rules_imports>>
<<kb_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<smart_rule_folder_content>>
<<kb_service_update_metadata>>
```
-->

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

**Example: Remove temporary metadata from processed files**

```{.python #kb_service_remove_metadata}
# Remove specific metadata keys from all matching files
updated_contents = kb_service.remove_contents_metadata(
    keys_to_remove=["temp_status", "processing_id", "draft_version"],
    metadata_filter=metadata_filter
)

print(f"Removed metadata from {len(updated_contents)} files")
```

**Best practice:** Test your filter with `get_paginated_content_infos()` first to see which files will be affected and what metadata they currently have.

<!--
```{.python file=./docs/.python_files/remove_metadata_with_smart_rule.py }
<<smart_rules_imports>>
<<kb_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<smart_rule_folder_content>>
<<kb_service_remove_metadata>>
```
-->














