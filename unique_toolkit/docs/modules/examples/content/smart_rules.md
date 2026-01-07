# Smart Rules - Examples

This page provides practical code examples for implementing smart rules with the knowledge base. For broader documentation and concepts, see the [Smart Rules Documentation](../../../knowledge_base/smart_rules).

## Smart Rule Definition Examples

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

### 5. Custom Metadata

Custom meta data can be used like normal metadata.

```{.python #smart_rule_custom_metadata}
smart_rule_custom = Statement(operator=Operator.EQUALS, 
                                      value=f"customValue", 
                                      path=["customMetaData"])

metadata_filter = smart_rule_custom.model_dump(mode="json")
```

### 6. Combining Smart Rules: Find PDFs in a Specific Folder

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

## Using the Metadata Filter

### For Content Chunk Search

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
```{.python file=./docs/.python_files/kb_content_chunk_search_with_smart_rule_on_folders.py }
<<smart_rules_imports>>
<<kb_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<smart_rule_folder_content>>
<<kb_service_combined_with_metadafilter>>
```
-->

### For Content Info Search

```{.python #kb_content_search}
infos =kb_service.get_paginated_content_infos(
    metadata_filter=metadata_filter
)
```

<!--
```{.python file=./docs/.python_files/kb_content_search_with_smart_rule_on_folders.py }
<<smart_rules_imports>>
<<kb_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<smart_rule_custom_metadata>>
<<kb_content_search>>
```
-->

### For Bulk Content Deletion

**⚠️ Warning:** This operation is irreversible and will permanently delete all content matching the filter criteria.

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
```{.python file=./docs/.python_files/kb_deletion_with_smart_rule_on_folders.py }
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
```{.python file=./docs/.python_files/kb_update_metadata_with_smart_rule.py }
<<smart_rules_imports>>
<<kb_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<smart_rule_folder_content>>
<<kb_service_update_metadata>>
```
-->

### For Bulk Metadata Removal

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
```{.python file=./docs/.python_files/kb_remove_metadata_with_smart_rule.py }
<<smart_rules_imports>>
<<kb_service_setup>>
<<load_demo_variables>>
<<env_scope_id>>
<<smart_rule_folder_content>>
<<kb_service_remove_metadata>>
```
-->

## Full Examples

??? example "Full Examples Smart Rules (Click to expand)"
    
    <!--codeinclude-->
    [Content Chunks](../../../examples_from_docs/kb_content_chunk_search_with_smart_rule_on_folders.py)
    [Content Search](../../../examples_from_docs/kb_content_search_with_smart_rule_on_folders.py)    
    [Content Deletion](../../../examples_from_docs/kb_deletion_with_smart_rule_on_folders.py)
    [Metadata Update](../../../examples_from_docs/kb_update_metadata_with_smart_rule.py)
    [Metadata Removal](../../../examples_from_docs/kb_remove_metadata_with_smart_rule.py)
    <!--/codeinclude-->
