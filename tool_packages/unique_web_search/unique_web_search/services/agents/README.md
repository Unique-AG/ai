# Research Planning and Execution System

This directory contains a comprehensive research planning and execution system for web-based research tasks.

## Components

### 1. Plan Agent (`plan_agent.py`)
Creates intelligent research plans based on user queries.

**Key Features:**
- **Three Planning Modes:**
  - `COMPREHENSIVE`: 5-8 detailed steps with verification and multiple perspectives
  - `FOCUSED`: 3-5 targeted steps for specific topics
  - `QUICK`: 2-3 direct steps for straightforward queries

- **Five Step Types:**
  - `SEARCH`: Perform web search with specific queries
  - `READ_URL`: Read content from specific URLs
  - `VERIFY`: Cross-check information from multiple sources
  - `SYNTHESIZE`: Combine and analyze gathered information
  - `FOLLOW_UP`: Additional searches based on initial findings

- **Advanced Features:**
  - Step dependencies and execution order
  - Priority levels (1-5, where 1 is highest)
  - Date restrictions for temporal queries
  - Advanced search operator suggestions

### 2. Plan Executor (`plan_executor.py`)
Executes research plans step by step with comprehensive error handling.

**Key Features:**
- **Dependency Resolution**: Automatically resolves and executes steps in the correct order
- **Error Handling**: Graceful handling of failed steps with detailed error reporting
- **Progress Reporting**: Integration with progress reporting system
- **Content Management**: Efficient handling and accumulation of research content
- **Synthesis**: Automatic synthesis of gathered information

**Execution Status Tracking:**
- `PENDING`: Step not yet started
- `RUNNING`: Step currently executing
- `COMPLETED`: Step completed successfully
- `FAILED`: Step failed with error
- `SKIPPED`: Step skipped due to unmet dependencies

### 3. Integrated Research Service (`integrated_research.py`)
Combines planning and execution into a single, easy-to-use service.

## Usage Examples

### Basic Usage
```python
from unique_web_search.services.agents.integrated_research import IntegratedResearchService
from unique_web_search.services.agents.plan_agent import PlanningMode

# Initialize service (with proper configuration)
research_service = IntegratedResearchService(
    search_and_crawl_service=search_service,
    language_model_service=llm_service,
    language_model=model_name,
    crawler_type=crawler_type
)

# Perform complete research
result = await research_service.research(
    query="What are the latest developments in renewable energy?",
    mode=PlanningMode.COMPREHENSIVE,
    context="Focus on solar and wind technologies"
)

# Access results
print(f"Research completed: {result.execution_summary}")
print(f"Final synthesis: {result.synthesis_result}")
```

### Advanced Usage - Separate Planning and Execution
```python
# Create plan first
plan = await research_service.create_plan_only(
    query="Impact of AI on job market",
    mode=PlanningMode.FOCUSED
)

# Review plan steps
for i, step in enumerate(plan.steps):
    print(f"{i+1}. {step.step_type}: {step.objective}")
    if step.query:
        print(f"   Query: {step.query}")
    if step.depends_on:
        print(f"   Depends on steps: {step.depends_on}")

# Execute the plan
execution_result = await research_service.execute_plan_only(plan)
```

### Using the Plan Executor Directly
```python
from unique_web_search.services.agents.plan_executor import PlanExecutor

executor = PlanExecutor(
    search_and_crawl_service=search_service,
    language_model_service=llm_service,
    language_model=model_name,
    crawler_type=crawler_type
)

# Execute a pre-created plan
result = await executor.execute_plan(research_plan)

# Access detailed step results
for step_result in result.step_results:
    print(f"Step {step_result.step_index}: {step_result.status}")
    if step_result.error_message:
        print(f"  Error: {step_result.error_message}")
    if step_result.content:
        print(f"  Content chunks: {len(step_result.content)}")
```

## Plan Structure

A research plan contains:
- **Query Analysis**: Understanding of what information is needed
- **Search Strategy**: Overall approach for gathering information
- **Steps**: Ordered list of actions to execute
- **Expected Outcome**: What the plan should produce

Each step includes:
- **Step Type**: The type of action to perform
- **Objective**: Clear description of the step's goal
- **Query/URLs**: Specific parameters for the step
- **Priority**: Execution priority (1-5)
- **Dependencies**: Other steps this step depends on
- **Date Restrictions**: Optional temporal filtering

## Execution Results

The executor provides comprehensive results including:
- **Step Results**: Detailed results for each step
- **Content**: All gathered content chunks
- **Search Results**: Raw search results from search steps
- **Synthesis**: Final synthesis of all information
- **Metrics**: Execution time, success/failure counts
- **Summary**: Human-readable execution summary

## Error Handling

The system includes robust error handling:
- Failed steps don't stop execution of independent steps
- Dependencies are properly tracked and enforced
- Detailed error messages for debugging
- Graceful degradation when services are unavailable

## Integration

This system integrates with:
- **Search Engines**: Google, Tavily, Jina, FireCrawl
- **Crawlers**: Various web content extraction services
- **Language Models**: Any compatible language model service
- **Progress Reporting**: Real-time progress updates
- **Content Management**: Structured content handling

## Configuration

The system requires:
- Configured search and crawl services
- Language model service
- Crawler type specification
- Optional progress reporter
- Token limits and encoding settings

