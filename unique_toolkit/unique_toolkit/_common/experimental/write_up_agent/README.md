# Write-Up Agent

The Write-Up Agent is a powerful tool for automatically generating structured markdown reports from DataFrame data using Large Language Models (LLMs). It transforms tabular data into coherent, well-organized narratives suitable for documentation, analysis reports, and technical write-ups.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Agent Workflow](#agent-workflow)
- [DataFrame and Template Relationship](#dataframe-and-template-relationship)
- [How It Works](#how-it-works)
- [Getting Started](#getting-started)
- [Template System](#template-system)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Examples](#examples)

---

## Overview

### What is the Write-Up Agent?

The Write-Up Agent bridges the gap between structured data and narrative documentation. Given a pandas DataFrame, it:

1. **Organizes** data by grouping rows into logical sections
2. **Summarizes** each section using LLM-powered text generation
3. **Generates** a cohesive markdown report with consistent formatting

### Use Cases

- **Data Analysis Reports**: Convert analysis results into readable summaries
- **FAQ Documentation**: Generate organized FAQ pages from Q&A pairs
- **Survey Summaries**: Transform survey responses into structured reports
- **Knowledge Base Articles**: Create documentation from structured knowledge entries
- **Executive Summaries**: Distill large datasets into key insights

---

## Key Features

### 🎯 Template-Driven Architecture

- **Single Source of Truth**: Jinja2 templates define both data structure and output format
- **Automatic Column Detection**: Templates automatically determine which columns to use
- **Flexible Grouping**: Organize data by any column (e.g., section, category, region)

### 🔄 Intelligent Processing

- **Adaptive Batching**: Automatically splits large groups to fit within token limits
- **Iterative Summarization**: Maintains context across batches for coherent outputs
- **Order Preservation**: Maintains the logical flow from your DataFrame

### 🛡️ Type-Safe & Robust

- **Pydantic Schemas**: Type-safe data structures (`GroupData`, `ProcessedGroup`)
- **Custom Exceptions**: Clear error messages for debugging
- **Automatic Normalization**: Column names converted to snake_case for template compatibility

### 🎨 Customizable

- **Custom Templates**: Define your own structure and formatting
- **Group-Specific Instructions**: Tailor LLM behavior per section
- **Configurable Batching**: Control row and token limits

---

## Agent Workflow

### What Does the Agent Do?

The Write-Up Agent follows a sophisticated 6-step workflow to transform your DataFrame into a polished markdown report:

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. TEMPLATE PARSING                                             │
│    Parse Jinja template → Extract grouping & selected columns   │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. COLUMN NORMALIZATION                                         │
│    DataFrame columns → Convert to snake_case                    │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. VALIDATION                                                   │
│    Check: Required columns exist in normalized DataFrame        │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. GROUPING                                                     │
│    Group DataFrame by detected column → Preserve order          │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. LLM GENERATION (Per Group)                                   │
│    a. Batch rows if needed (token/row limits)                   │
│    b. Render batch content from template                        │
│    c. Build prompts (system + user with section context)        │
│    d. Call LLM with prompts                                     │
│    e. Aggregate batch summaries → Final summary                 │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. REPORT ASSEMBLY                                              │
│    Render final template with all LLM summaries → Markdown      │
└─────────────────────────────────────────────────────────────────┘
```

### Detailed Workflow Explanation

#### Step 1: Template Parsing
The agent parses your Jinja template to automatically detect:
- **Grouping column**: Found from `{{ g.column_name }}` patterns
- **Selected columns**: Found from `{{ row.column_name }}` patterns

Example:
```jinja
# {{ g.section }}        → Grouping column: "section"
{{ row.question }}        → Selected column: "question"
{{ row.answer }}          → Selected column: "answer"
```

#### Step 2: Column Normalization
All DataFrame column names are converted to **snake_case**:
- `"My Section"` → `"my_section"`
- `"UserQuestion"` → `"user_question"`
- `"column-name"` → `"column_name"`

This ensures compatibility with Jinja template syntax.

#### Step 3: Validation
The agent verifies that all columns referenced in the template exist in the normalized DataFrame. If any are missing, a clear error message is raised.

#### Step 4: Grouping
Data is grouped by the detected grouping column:
- Groups appear in **order of first appearance** (not alphabetically)
- Each group contains all rows with the same grouping value
- Selected columns are filtered for each group

#### Step 5: LLM Generation
For each group:
1. **Batching** (if needed): Large groups are split into manageable batches
2. **Content Rendering**: Template renders batch data for LLM input
3. **Prompt Building**: System and user prompts are constructed with:
   - Section name (group key)
   - Group-specific instructions (if configured)
   - Previous batch summary (for context)
4. **LLM Call**: Generate summary for the batch
5. **Aggregation**: If multiple batches, summaries are iteratively combined

#### Step 6: Report Assembly
All group summaries are combined using the template to produce the final markdown report.

---

## DataFrame and Template Relationship

### The Critical Connection

The DataFrame and template are **tightly coupled** through column names. Understanding this relationship is essential for successful report generation.

### 🔑 **CRITICAL: snake_case Requirement**

**All template variable references MUST use snake_case notation.**

Your DataFrame columns can use ANY naming convention:
```python
df = pd.DataFrame({
    'My Section': [...],      # Space-separated
    'UserQuestion': [...],    # PascalCase
    'user-answer': [...]      # kebab-case
})
```

But your template MUST reference them in snake_case:
```jinja
# {{ g.my_section }}         ✓ CORRECT
# {{ row.user_question }}    ✓ CORRECT
# {{ row.user_answer }}      ✓ CORRECT

# {{ g.My Section }}         ✗ WRONG - will fail
# {{ row.UserQuestion }}     ✗ WRONG - will fail
```

### How It Works: Normalization Bridge

```
DataFrame Columns              snake_case           Template References
─────────────────            ─────────────          ──────────────────
"My Section"         →       "my_section"      ←   {{ g.my_section }}
"UserQuestion"       →       "user_question"   ←   {{ row.user_question }}
"column-name"        →       "column_name"     ←   {{ row.column_name }}
"Product_ID"         →       "product_id"      ←   {{ row.product_id }}
```

### Template-DataFrame Mapping Example

**DataFrame:**
```python
df = pd.DataFrame({
    'Report Section': ['Executive Summary', 'Financial Analysis'],
    'Key Finding': ['Revenue up 20%', 'Costs reduced 15%'],
    'Data Source': ['Q4 Report', 'Annual Budget']
})
```

**Template (MUST use snake_case):**
```jinja
{% for g in groups %}
# {{ g.report_section }}    {# Normalized from "Report Section" #}

{% if g.llm_response %}
{{ g.llm_response }}
{% else %}
{% for row in g.rows %}
**Finding**: {{ row.key_finding }}     {# Normalized from "Key Finding" #}
**Source**: {{ row.data_source }}      {# Normalized from "Data Source" #}
{% endfor %}
{% endif %}
{% endfor %}
```

### Group-Specific Instructions: Key Format

When providing `group_specific_instructions`, you must use a specific key format to ensure the instructions are correctly matched to groups:

⚠️ **Key Format**: `"{snake_case_column}:{snake_case_value}"`

**Why both in snake_case?**
- DataFrame column names are automatically normalized to snake_case (e.g., `"Report Section"` → `"report_section"`)
- Group values are also normalized to snake_case (e.g., `"Executive Summary"` → `"executive_summary"`)
- Your instruction keys must match this normalized format

**Example:**

If your DataFrame has:
- Column: `"Section"`
- Values: `"Executive Summary"`, `"Detailed Analysis"`, `"Recommendations"`

Your keys must be:

```python
config = WriteUpAgentConfig(
    generation_handler_config=GenerationHandlerConfig(
        group_specific_instructions={
            # Format: "{snake_case_column}:{snake_case_value}"
            # Both parts must be in snake_case
            "section:executive_summary": "Be concise, highlight key metrics",
            "section:detailed_analysis": "Be thorough, include all data points",
            "section:recommendations": "Be actionable, prioritize by impact"
        }
    )
)
```

**Key Format**: `"{snake_case_column}:{snake_case_value}"`
- **Column name part**: MUST be snake_case (normalized column name)
- **Value part**: MUST be snake_case (normalized group value)

**Transformation Table:**

| DataFrame Column | DataFrame Value | Normalized Column | Normalized Value | Required Key |
| :--------------- | :-------------- | :---------------- | :--------------- | :----------- |
| `Section` | `Executive Summary` | `section` | `executive_summary` | `section:executive_summary` |
| `Report Section` | `User Feedback` | `report_section` | `user_feedback` | `report_section:user_feedback` |
| `topic-name` | `API-Design` | `topic_name` | `api_design` | `topic_name:api_design` |

### Validation and Error Messages

If your template references columns incorrectly, you'll see:

```
DataFrameValidationError: DataFrame missing required columns after 
snake_case normalization: ['My Section', 'UserQuestion']
Available columns: ['my_section', 'user_question', 'user_answer']
```

This tells you:
- What the template is looking for (incorrect format)
- What columns are actually available (snake_case format)

### Quick Reference: Naming Rules

| Component | Format | Example | Notes |
|-----------|--------|---------|-------|
| **DataFrame Columns** | Any format | `"My Column"`, `"UserName"` | Will be normalized to snake_case |
| **DataFrame Values** | Any format | `"Executive Summary"` | Will be normalized to snake_case |
| **Template Variables** | **snake_case** | `{{ g.my_column }}` | MUST use snake_case |
| **Group Instruction Keys** | **snake_case:snake_case** | `"my_column:executive_summary"` | Both parts in snake_case |

---

## How It Works

### Input: DataFrame

The agent requires a pandas DataFrame with your data. Column names can be in any format (spaces, PascalCase, etc.) - they'll be automatically normalized to snake_case.

```python
import pandas as pd

df = pd.DataFrame({
    'Section': ['Introduction', 'Methods', 'Results'],
    'Question': ['What is X?', 'How does Y?', 'What are Z?'],
    'Answer': ['X is...', 'Y works by...', 'Z are...']
})
```

### Configuration

Two main components:

1. **WriteUpAgentConfig**: Defines the template and generation settings
2. **LanguageModelService**: Provides LLM access for summarization

```python
from unique_toolkit._common.experimental.write_up_agent import (
    WriteUpAgent,
    WriteUpAgentConfig,
)
from unique_toolkit.language_model.service import LanguageModelService

config = WriteUpAgentConfig()  # Uses default template
llm_service = LanguageModelService.from_settings(settings)

agent = WriteUpAgent(config=config, llm_service=llm_service)
```

### Processing

The agent orchestrates a multi-step pipeline:

```python
report = agent.process(df)  # Returns markdown string
```

**Internal Pipeline:**

1. **Template Parsing**: Extract grouping column and selected columns from template
2. **DataFrame Validation**: Verify required columns exist (after snake_case normalization)
3. **Grouping**: Create groups based on grouping column, preserving DataFrame order
4. **Batching**: Split large groups into manageable batches (token/row limits)
5. **LLM Generation**: Generate summaries for each batch with context
6. **Report Assembly**: Combine all summaries into final markdown report

### Output: Markdown Report

```markdown
# Introduction

This section introduces the concept of X, explaining its fundamental 
principles and applications...

---

# Methods

The methodology involves Y, which operates through a series of steps...

---
```

---

## Template System

### Templates as Configuration

The Jinja2 template serves as the **single source of truth**, defining:

- **Grouping column**: Which column to group by (e.g., `section`)
- **Selected columns**: Which columns to include in each group (e.g., `question`, `answer`)
- **Output structure**: How the final report should be formatted

### Default Template

The default template expects three columns: `section`, `question`, `answer`

```jinja
{% for g in groups %}
# {{ g.section }}

{% if g.llm_response %}
{{ g.llm_response }}
{% else %}
{% for row in g.rows %}
**Q: {{ row.question }}**

A: {{ row.answer }}

{% endfor %}
{% endif %}

---
{% endfor %}
```

### How Template Parsing Works

The agent automatically detects:

```jinja
# {{ g.section }}          → Grouping column: "section"
{{ row.question }}          → Selected column: "question"  
{{ row.answer }}            → Selected column: "answer"
```

### Reserved Keywords

These keywords are reserved for template logic (not treated as data columns):

- `g.rows`: List of row dictionaries
- `g.llm_response`: LLM-generated summary
- `g.instructions`: Group-specific instructions (future use)

### Two-Phase Rendering

**Phase 1 - LLM Input** (`g.llm_response` is None):
```markdown
**Q: What is the Write-Up Agent?**
A: A tool for generating reports...
```

**Phase 2 - Final Report** (`g.llm_response` is provided):
```markdown
The Write-Up Agent is an automated tool that transforms structured
DataFrame data into coherent summaries...
```

### Custom Templates

Create your own template for different data structures:

```jinja
{% for g in groups %}
## {{ g.category }}

{% if g.llm_response %}
{{ g.llm_response }}
{% else %}
{% for row in g.rows %}
- **{{ row.product }}**: ${{ row.price }} - {{ row.description }}
{% endfor %}
{% endif %}
{% endfor %}
```

This template expects columns: `category`, `product`, `price`, `description`

---

## Configuration

### WriteUpAgentConfig

```python
from unique_toolkit._common.experimental.write_up_agent import WriteUpAgentConfig

config = WriteUpAgentConfig(
    # Template (default: Q&A template for section/question/answer)
    template="{% for g in groups %}...",
    
    # Generation settings
    generation_handler_config=GenerationHandlerConfig(
        language_model=language_model_info,
        common_instruction="You are a technical writer...",
        max_rows_per_batch=20,
        max_tokens_per_batch=4000,
        group_specific_instructions={
            "section:Introduction": "Be welcoming and engaging",
            "section:Methods": "Be precise and technical"
        }
    )
)
```

### Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `template` | `str` | Default Q&A template | Jinja2 template defining structure |
| `generation_handler_config` | `GenerationHandlerConfig` | Default config | LLM generation settings |

### GenerationHandlerConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `language_model` | `LMI` | Required | Language model to use |
| `common_instruction` | `str` | Default system prompt | Base instruction for all groups |
| `max_rows_per_batch` | `int` | 20 | Max rows per LLM call |
| `max_tokens_per_batch` | `int` | 4000 | Max tokens per LLM call |
| `group_specific_instructions` | `dict[str, str]` | `{}` | Custom instructions per group |

---

## Architecture

### Separation of Concerns

The agent follows a clean architecture with three main handlers:

```
WriteUpAgent (Orchestrator)
├── TemplateHandler (Template Operations)
│   ├── Parse template structure
│   ├── Extract columns
│   └── Render groups
├── DataFrameHandler (Data Operations)
│   ├── Normalize column names
│   ├── Validate columns
│   └── Create groups
└── GenerationHandler (LLM Operations)
    ├── Create batches
    ├── Build prompts
    ├── Call LLM
    └── Aggregate summaries
```

### Data Flow

```
DataFrame → Normalize → Validate → Group → Batch → LLM → Aggregate → Report
```

### Type-Safe Schemas

```python
from unique_toolkit._common.experimental.write_up_agent import (
    GroupData,
    ProcessedGroup
)

# GroupData: After DataFrame grouping
GroupData(
    group_key="Introduction",
    rows=[{"question": "...", "answer": "..."}]
)

# ProcessedGroup: After LLM generation
ProcessedGroup(
    group_key="Introduction",
    rows=[{"question": "...", "answer": "..."}],
    llm_response="The introduction section..."
)
```

---

## Examples

### Basic Usage

```python
import pandas as pd
from unique_toolkit._common.experimental.write_up_agent import (
    WriteUpAgent,
    WriteUpAgentConfig,
)
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.language_model.service import LanguageModelService

# Setup
settings = UniqueSettings.from_env()
settings.init_sdk()

# Create DataFrame
df = pd.DataFrame({
    'section': ['Intro', 'Methods', 'Results'],
    'question': ['What?', 'How?', 'What result?'],
    'answer': ['Answer 1', 'Answer 2', 'Answer 3']
})

# Initialize agent
config = WriteUpAgentConfig()
agent = WriteUpAgent(
    config=config,
    llm_service=LanguageModelService.from_settings(settings)
)

# Generate report
report = agent.process(df)
print(report)
```

### Custom Template Example

```python
custom_template = """
{% for g in groups %}
# {{ g.region }} Market Analysis

{% if g.llm_response %}
{{ g.llm_response }}
{% else %}
{% for row in g.rows %}
- **{{ row.product }}**: {{ row.units }} units sold
{% endfor %}
{% endif %}

---
{% endfor %}
"""

config = WriteUpAgentConfig(template=custom_template)

df = pd.DataFrame({
    'Region': ['North', 'South', 'East'],
    'Product': ['Widget', 'Gadget', 'Tool'],
    'Units': [100, 200, 150]
})

agent = WriteUpAgent(config=config, llm_service=llm_service)
report = agent.process(df)
```

### With Group-Specific Instructions

```python
from unique_toolkit._common.experimental.write_up_agent.services.generation_handler import (
    GenerationHandlerConfig
)

# DataFrame column: "Section"
# DataFrame values: "Executive Summary", "Detailed Analysis", "Recommendations"

gen_config = GenerationHandlerConfig(
    language_model=language_model_info,
    common_instruction="You are an expert data analyst.",
    group_specific_instructions={
        # Format: "snake_case_column:snake_case_value"
        # Both column name AND value must be in snake_case
        "section:executive_summary": "Be concise, highlight key metrics",
        "section:detailed_analysis": "Be thorough, include all data points",
        "section:recommendations": "Be actionable, prioritize by impact"
    }
)

config = WriteUpAgentConfig(generation_handler_config=gen_config)
```

**Important**: Both the column name (`section`) AND the values (`executive_summary`, etc.) must be in snake_case to match the automatic normalization applied to your DataFrame.

---

## Advanced Features

### Automatic Column Normalization

All column names are automatically converted to snake_case for template compatibility:

| Original | Normalized |
|----------|------------|
| `My Column` | `my_column` |
| `UserName` | `user_name` |
| `section-name` | `section_name` |

Your DataFrame can use any naming convention - the agent handles normalization automatically.

### Order Preservation

Groups appear in the order they first appear in your DataFrame, not alphabetically:

```python
df = pd.DataFrame({
    'section': ['Intro', 'Methods', 'Results', 'Intro']  # Intro appears twice
})
# Report will show: Intro → Methods → Results (not: Intro → Methods → Results → Intro)
```

### Adaptive Batching

For groups with many rows, the agent automatically:
1. Splits into batches based on token/row limits
2. Processes each batch with LLM
3. Maintains context by passing previous summary to next batch
4. Aggregates all batch summaries into final section summary

### Error Handling

Custom exceptions provide clear error messages:

```python
from unique_toolkit._common.experimental.write_up_agent.services.dataframe_handler import (
    DataFrameValidationError,
    DataFrameGroupingError,
)
from unique_toolkit._common.experimental.write_up_agent.services.template_handler import (
    TemplateParsingError,
    ColumnExtractionError,
)

try:
    report = agent.process(df)
except DataFrameValidationError as e:
    print(f"Missing columns: {e.missing_columns}")
except TemplateParsingError as e:
    print(f"Template error: {e}")
```

---

## Best Practices

1. **Column Names**: Use descriptive names - they'll be normalized automatically
2. **Data Organization**: Arrange DataFrame in logical order (will be preserved)
3. **Template Design**: Start with default template, customize as needed
4. **Batch Sizes**: Adjust `max_rows_per_batch` based on data density
5. **Instructions**: Use `group_specific_instructions` for varied section styles
6. **Testing**: Test with small datasets first to verify template parsing

---

## Troubleshooting

### "DataFrame missing required columns"

The template references columns that don't exist in your DataFrame (after snake_case normalization).

**Solution**: Check template column references match your DataFrame columns (in snake_case).

### "Template must use grouping pattern"

Your template doesn't include `{% for g in groups %}`.

**Solution**: Ensure template follows the grouping pattern shown in examples.

### "Single grouping column required"

Your template references multiple grouping columns (e.g., `{{ g.col1 }}`, `{{ g.col2 }}`).

**Solution**: Currently only single-column grouping is supported. Use one grouping column.

---

## Future Enhancements

- [ ] **Multi-column grouping support**: Group by multiple columns simultaneously (e.g., `region` and `category`)
- [ ] **Reference handling**: Support passing a reference map to automatically resolve and include references in the generated content

---

## Contributing

This is an experimental feature. Feedback and contributions are welcome!

---

## License

Part of the Unique Toolkit - see main repository LICENSE.

