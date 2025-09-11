## 📘 ReferenceManager Documentation

The `ReferenceManager` is responsible for managing and organizing references and content chunks extracted from tool responses. It plays a critical role in ensuring that references are tracked, organized, and made available for use in subsequent interactions with the LLM. This is essential for maintaining a **consistent and efficient history of references**, especially when dealing with **incremental reference counts** and **token window constraints**.

---

### 🔑 Key Considerations

#### 1. **Incremental Reference Counts**
   - Many tools can return references during a single iteration of the orchestrator. These references need to be **numbered sequentially** across all tools to maintain consistency.
   - A **centralized system** is required to track all references, ensuring that they are properly organized and numbered. While the `ReferenceManager` collects and organizes these references, the **History Manager** is responsible for assigning the incremental reference numbers.
   - This centralized tracking ensures that:
     - References can be cited consistently across multiple iterations.
     - Back-references to previously cited chunks are possible, even when jumping between different parts of the history.

#### 2. **Token Window Constraints**
   - Each LLM has a **token limit** for the input it can process in a single API call. This constraint requires careful management of the references and chunks included in the input.
   - During each iteration, the `ReferenceManager` collects all references and chunks produced by the tools. Once all references are gathered, a **token reduction logic** is applied to ensure that the total number of tokens remains within the LLM's limit.
   - This process involves:
     - **Limiting the number of chunks** included from each tool's response.
     - Optimizing the selection of chunks to prioritize the most relevant references.
     - Ensuring that the history provided to the LLM is concise and fits within the token window.
   - Also here the **History Manager** is responsible for ensuring that the token window is not exceeded.
   - This allows the history to intelligently reduce the number of tokens and does not need to reduce them just arbitrarily

---

### 🛠️ Key Functionalities

#### 1. **Chunk Extraction**
   - **`extract_referenceable_chunks(tool_responses: list[ToolCallResponse])`**  
     Extracts content chunks from tool responses and organizes them for reference.  
     - Adds chunks to the `_chunks` list.
     - Maps tool call IDs to their respective chunks in `_tool_chunks`.

     ```python
     def extract_referenceable_chunks(
         self, tool_responses: list[ToolCallResponse]
     ) -> None:
         for tool_response in tool_responses:
             if not tool_response.content_chunks:
                 continue
             self._chunks.extend(tool_response.content_chunks or [])
             self._tool_chunks[tool_response.id] = tool_chunks(
                 tool_response.name, tool_response.content_chunks
             )
     ```

#### 2. **Chunk Retrieval**
   - **`get_chunks()`**  
     Retrieves all content chunks stored in the manager.  
     ```python
     def get_chunks(self) -> list[ContentChunk]:
         return self._chunks
     ```

   - **`get_tool_chunks()`**  
     Retrieves all tool-specific chunks as a dictionary.  
     ```python
     def get_tool_chunks(self) -> dict[str, tool_chunks]:
         return self._tool_chunks
     ```

   - **`get_chunks_of_all_tools()`**  
     Retrieves chunks grouped by tool.  
     ```python
     def get_chunks_of_all_tools(self) -> list[list[ContentChunk]]:
         return [tool_chunks.chunks for tool_chunks in self._tool_chunks.values()]
     ```

   - **`get_chunks_of_tool(tool_call_id: str)`**  
     Retrieves chunks for a specific tool call ID.  
     ```python
     def get_chunks_of_tool(self, tool_call_id: str) -> list[ContentChunk]:
         return self._tool_chunks.get(tool_call_id, tool_chunks(\"\", [])).chunks
     ```

#### 3. **Chunk Replacement**
   - **`replace_chunks_of_tool(tool_call_id: str, chunks: list[ContentChunk])`**  
     Replaces the chunks for a specific tool call ID.  
     ```python
     def replace_chunks_of_tool(
         self, tool_call_id: str, chunks: list[ContentChunk]
     ) -> None:
         if tool_call_id in self._tool_chunks:
             self._tool_chunks[tool_call_id].chunks = chunks
     ```

   - **`replace(chunks: list[ContentChunk])`**  
     Replaces the entire set of chunks in the manager.  
     ```python
     def replace(self, chunks: list[ContentChunk]):
         self._chunks = chunks
     ```

#### 4. **Reference Management**
   - **`add_references(references: list[ContentReference])`**  
     Adds a new set of references to the manager.  
     ```python
     def add_references(
         self,
         references: list[ContentReference],
     ):
         self._references.append(references)
     ```

   - **`get_references()`**  
     Retrieves all references stored in the manager.  
     ```python
     def get_references(
         self,
     ) -> list[list[ContentReference]]:
         return self._references
     ```

#### 5. **Latest Reference Access**
   - **`get_latest_references()`**  
     Retrieves the most recent set of references.  
     ```python
     def get_latest_references(
         self,
     ) -> list[ContentReference]:
         if not self._references:
             return []
         return self._references[-1]
     ```

   - **`get_latest_referenced_chunks()`**  
     Retrieves the chunks corresponding to the most recent references.  
     ```python
     def get_latest_referenced_chunks(self) -> list[ContentChunk]:
         if not self._references:
             return []
         return self._get_referenced_chunks_from_references(self._references[-1])
     ```

#### 6. **Reference-to-Chunk Mapping**
   - **`_get_referenced_chunks_from_references(references: list[ContentReference])`**  
     Matches references to their corresponding chunks based on source IDs.  
     ```python
     def _get_referenced_chunks_from_references(
         self,
         references: list[ContentReference],
     ) -> list[ContentChunk]:
         referenced_chunks: list[ContentChunk] = []
         for ref in references:
             for chunk in self._chunks:
                 if ref.source_id == f\"{chunk.id}-{chunk.chunk_id}\":
                     referenced_chunks.append(chunk)
         return referenced_chunks
     ```