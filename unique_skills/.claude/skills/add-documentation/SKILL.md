---
name: add-documentation
description: Document Python code, APIs, or features with clear explanations and examples. Use when new functionality is introduced or existing code needs clarification.
license: MIT
compatibility: claude cursor opencode
metadata:
  version: "1.0.0"
  languages: python
  audience: developers
  workflow: docs
  since: "2026-02-25"
---

# Add Documentation

Explain what the code does, why it exists, and how to use it.

## Steps

1. **Overview**
   - Describe the feature/purpose and business value
   - Summarize the major components and their interactions
   - Call out any prerequisites or assumptions

2. **API documentation**
   - Document function/method signatures, parameter types, and return values
   - Highlight default behaviors, timeouts, and retry semantics
   - Include example usage snippets (CLI command, `requests`, `pytest` invocation)
   - Show error handling (e.g., expected exceptions, HTTP status codes)

3. **Implementation details**
   - Illustrate key architecture decisions or patterns
   - Draw attention to important dependencies or modules
   - Explain any non-obvious performance optimizations or fallbacks

4. **Examples & best practices**
   - Provide common use cases with full code snippets
   - Warn about pitfalls or things to avoid (race conditions, mutable defaults)
   - Point readers to related docs/reference materials

## Checklist
- [ ] Documented what the code/feature does and why it exists
- [ ] Explained key concepts and terminology
- [ ] Documented function/method signatures (params + returns)
- [ ] Included usage examples covering common flows
- [ ] Captured error handling and edge cases
- [ ] Noted architecture decisions, dependencies, and follow-ups
