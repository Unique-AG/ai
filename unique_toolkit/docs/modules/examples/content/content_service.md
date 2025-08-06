
# Content Service


Once the content service is initialized it can be used to 

## Retrieve chunks via semantic,keyword or combined search


```{.python #content_service_search_content_chunks}
from unique_toolkit.content.schemas import ContentSearchType

content_chunks = content_service.search_content_chunks(
    search_string="Hello, world!",
    search_type=ContentSearchType.VECTOR,
    limit=10,
)
```



<!--
```{.python file=examples/generated/content_standalone.py}
# %%
<<initialize_content_service_standalone>>
<<content_service_search_content_chunks>>
```
-->

<!--
```{.python file=examples/generated/content_event_driven.py}
# %%
```
-->


