
# Content Service
The content service provides capabilities to interact with the the knowledge base.


## Up and Download contents from the knowledgebase

A `Content` corresponds to a file of any type.

### Into memory
It is encouraged to load contents to memory only in order to avoid information leakage by saving files to disk accidentially


### Into a file on disk
Sometimes a file can only be read from disk with a specific library. In this case the best practice is to save it within a random directory under `/tmp`. Ideally under a random name as well. Furthermore, the file should be deleted at the end of the request.


## Retrieve chunks via semantic, keyword or combined search

If ingested the information of a `Content` is split into multiple `Chunks` (pieces or text) that are embedded. These embedding vectors are saved in a vector database for semantic retrieval. This together with traditional keyword search allows for an efficient retrieval of `Chunks` that might be relevant for a users query or any search string.

For

```{.python #content_service_search_content_chunks}
content_chunks = content_service.search_content_chunks(
    search_string="Hello, world!",
    search_type=ContentSearchType.VECTOR,
    limit=10,
)
```





