## 📘 ToolCallResponse Overview

The `ToolCallResponse` class is the output produced by a tool after its execution. It provides structured information that the LLM can use produce an answer to the user query. The response contains several key components, each serving a specific purpose.

---

### 🔑 Key fields of ToolCallResponse

When to fill what information on the tool call response, not all fields must be filled it depends on the case.

1. **Content (`content`)**  
   - This is the default field to fill for most tools.  
   - Use this field for general output that does not require references or special handling.
   - Example: A success message, API results, or any plain data.
   - this can be left empty if other fields are filled

2. **Referenceable Content (`content_chunks`)**  
   - If the tool produces content that should be referenceable (e.g., citations, search results), it must be added to the `content_chunks` field.  
   - These chunks are processed by the **Reference Manager**, which ensures they are displayed correctly in the front end and are referenceable by the LLM.
   - this can be left empty if other fields are filled

3. **Debug Information (`debug_info`)**  
   - Use this field to include additional data for debugging purposes.  
   - The **Debug Information Manager** processes this field and ensures it is displayed in the appropriate location in the front end.  
   - Example: Internal tool states, execution steps, or metadata.
   - this can be left empty if other fields are filled

4. **On Error (`error_message`)**  
   - If an error occurs during tool execution, include the error details in this field. 
   - This ensures that errors are clearly communicated to the LLM and the user.  
   - this can be left empty if other fields are filled


```python

class ToolCallResponse(BaseModel):
    id: str
    name: str
    content: str = ""
    debug_info: Optional[dict] = None  # TODO: Make the default {}
    content_chunks: Optional[list[ContentChunk]] = None  # TODO: Make the default []
    reasoning_result: Optional[dict] = None  # TODO: Make the default {} 
    error_message: str = ""

```