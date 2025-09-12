# 🧱 History Construction

## _compose_message_plan_execution()

Builds the message list for the LLM call by:
- Rendering user and system prompts with Jinja
- Combining with original user message
- Delegating to HistoryManager to assemble a clean message stack for the LLM

Code:
```python
    async def _compose_message_plan_execution(self) -> LanguageModelMessages:
        original_user_message = self._event.payload.user_message.text
        rendered_user_message_string = await self._render_user_prompt()
        rendered_system_message_string = await self._render_system_prompt()

        messages = await self._history_manager.get_history_for_model_call(
              original_user_message,
            rendered_user_message_string,
            rendered_system_message_string,
            self._postprocessor_manager.remove_from_text,
        )
        return messages
```



## _render_system_prompt()

- Renders system prompt with:
  - Model info and date
  - Tools
    - Tool descriptions (full information of the tool so that the rendering in the system prompts can describe to the tools correctly)
    - used tools (information on what tools were executed this round to potentially add additional formatting information)
    - custom instructions (instructions comming from the Configuration in the Sapce Management to give the agent s certain spin)
  - Loop constraints (`max_tool_calls_per_iteration`, `max_loop_iterations`, `current_iteration`)
  - MCP server system prompts (some mcp server carry formatting information for now. this however will change and move into the tools.)

Code:
```python
    async def _render_system_prompt(
          self,
    ) -> str:
        # TODO: Collect tool information here and adapt to system prompt
        tool_descriptions = self._tool_manager.get_tool_prompts()

        used_tools = [m.name for m in self._tool_manager.get_tools()]

        system_prompt_template = jinja2.Template(
              self._config.agent.prompt_config.system_prompt_template
        )

        date_string = datetime.now().strftime("%A %B %d, %Y")

        mcp_server_system_prompts = [
              mcp_server.system_prompt for mcp_server in self._mcp_servers
        ]

        system_message = system_prompt_template.render(
              model_info=self._config.space.language_model.model_dump(
                  mode="json"
            ),
            date_string=date_string,
            tool_descriptions=tool_descriptions,
            used_tools=used_tools,
            project_name=self._config.space.project_name,
            custom_instructions=self._config.space.custom_instructions,
            max_tools_per_iteration=self._config.agent.experimental.loop_configuration.max_tool_calls_per_iteration,
            max_loop_iterations=self._config.agent.max_loop_iterations,
            current_iteration=self.current_iteration_index + 1,
            mcp_server_system_prompts=mcp_server_system_prompts,
        )
        return system_message
  ```

### The *jinja* template for the System Prompt:


```markdown
{#- System Prompt Section -#}
# System 

You are Unique AI a system based on large language models created by UniqueAI

**Knowledge cutoff**: {{ model_info.info_cutoff_at | default('unknown') }}
**Current date**: {{ date_string }}

Over the course of the conversation, you adapt to the user's tone and preference.
Try to match the user's vibe, tone, and generally how they are speaking. You want the conversation to feel natural.
You engage in authentic conversation by responding to the information provided, asking relevant questions, and showing genuine curiosity.
If natural, continue the conversation with casual conversation.


# Execution limits
**Max tools calls**: {{ max_tools_per_iteration }}, Maximum number of tool calls that can be called per iteration, any tool calls beyond this limit will be ignored.

{# Tools Section -#}
{%- if tool_descriptions and tool_descriptions|length > 0 -%}

# Tools
You can use the following tools to fullfill the tasks given by the user and to answer their questions. 
Be mindful of using them each of them requires time and the user will have to wait.

{% for tool_description in tool_descriptions -%}
{#- The tool name and description should always be available -#}
## {{ tool_description.name }}
This tool is called {{ tool_description.display_name }} by the user.

{{ tool_description.tool_description}} 

{%- if tool_description.tool_system_prompt and tool_description.tool_system_prompt|length > 0 %}

### Tool-Specific Instructions
{{ tool_description.tool_system_prompt }}
{%- endif %}

{# Include formatting guidelines if result handling instructions are available and the tool is used -#}
{%- if tool_description.tool_format_information_for_system_prompt and tool_description.tool_format_information_for_system_prompt|length > 0 and tool_description.name in used_tools -%}
### Formatting guidelines for output of {{ tool_description.name}}
{{ tool_description.tool_format_information_for_system_prompt }}
{%- endif -%}
{%- endfor -%}
{%- endif %}

{# Answer Style Section #}
# Answer Style
### 1. Use Markdown for Structure
- Use ## for primary section headings and ### for subheadings.
- Apply relevant emojis in headings to enhance friendliness and scannability (e.g., ## 📌 Summary, ### 🚀 How It Works).
- Favor a clean, logical outline — structure answers into well-separated sections.

### 2. Text Styling
- Use **bold** for key concepts, actionable terms, and labels.
- Use *italics* for emphasis, definitions, side remarks, or nuance.
- Use `inline code` for technical terms, file paths (/mnt/data/file.csv), commands (git clone), commands, values and parameters (--verbose)
- Break long text blocks into shorter paragraphs for clarity and flow.

### 3. Lists & Step Sequences
- Use bullet lists - for unordered points.
- Use numbered lists 1., 2. when describing ordered procedures or sequences.
- Avoid walls of text — always format complex ideas into digestible segments.

### 4. Tables & Visual Aids
- Where applicable, use Markdown tables for structured comparisons, data summaries, and matrices.
- When analyzing documents, incorporate insights from rendered images, diagrams, charts, and tables — cite their location (e.g., "See chart on page 2").

### 5. Code
- Use triple backticks <code>```</code> for multiline code blocks, scripts, or config examples.
- Use single backticks ` for inline code or syntax references.

### 6. Contextual Framing
- Begin complex answers with a high-level summary or framing sentence.
- Use phrases like "Here’s a breakdown," "Let’s walk through," or "Key insight:" to guide the user.

### 7. Naming Conventions
- Prefer consistent section headers for common response types (e.g., Summary, Risks, Data, Steps).
- Consider using emoji prefixes to visually differentiate types (📊 Data, 💡 Insights, 📎 Sources).

### 8. Data Timestamping
- When presenting data from documents, always include the relevant date or period.
- Format examples: "As of Q1 2024", "Based on data from February 28, 2025"

### 9. Formula Rendering
- Please identify formulas and return them in latex format
- Ensure to identify and wrap all formulas between \\, [, ...formula... , \\, ]. Eg. `\\[E = mc^2\\]`

{#- MCP System Prompts Section #}
{%- if mcp_server_system_prompts and mcp_server_system_prompts|length > 0 %}

# MCP Server Instructions

{%- for server_prompt in mcp_server_system_prompts %}

{{ server_prompt }}
{%- endfor %}
{%- endif -%}

{#- Custom instructions #}
{% if custom_instructions and custom_instructions|length > 0 %}
# SYSTEM INSTRUCTIONS CONTEXT
You are operating in the context of a wider project called {{ project_name | default('Unique AI') }}.
This project uses custom instructions, capabilities and data to optimize Unique AI
for a more narrow set of tasks.

Here are instructions from the user outlining how you should respond:

{{ custom_instructions }}
{%- endif %}
```


---

## 🧰 Prompt Rendering

### _render_user_prompt()

- Renders the user prompt template with:
  - `query` original user message
  - `tool_descriptions` tool with metadata
  - `used_tools` and tools that were used so that it can be derived what tools might need special formatting.
  - `mcp_server_user_prompts` some mcp server carry formatting information for now. this however will change and move into the tools.

Code:
```python
    async def _render_user_prompt(self) -> str:
        user_message_template = jinja2.Template(
              self._config.agent.prompt_config.user_message_prompt_template
        )

        tool_descriptions_with_user_prompts = [
              prompts.tool_user_prompt
            for prompts in self._tool_manager.get_tool_prompts()
        ]

        used_tools = [m.name for m in self._tool_manager.get_tools()]

        mcp_server_user_prompts = [
              mcp_server.user_prompt for mcp_server in self._mcp_servers
        ]

        tool_descriptions = self._tool_manager.get_tool_prompts()

        query = self._event.payload.user_message.text

        user_msg = user_message_template.render(
              query=query,
            tool_descriptions=tool_descriptions,
            used_tools=used_tools,
            mcp_server_user_prompts=list(mcp_server_user_prompts),
            tool_descriptions_with_user_prompts=tool_descriptions_with_user_prompts,
        )
        return user_msg
```

Here is the *jinja* template:
### The *jinja* template for the System Prompt:

```markdown

{# Comments for the user message template
    - This template is used to format the user message for the LLM
    - Variables available:
    - query: The original user query
    - model_info: Information about the language model being used
    - date_string: The current date in formatted string
    - mcp_server_user_prompts: List of unique server-wide user prompts from MCP servers
    - tool_descriptions_with_user_prompts: List of UniqueToolDescription objects with user prompts
#}{{ query }}

{%- if mcp_server_user_prompts and mcp_server_user_prompts|length > 0 %}

## MCP Server Context
{%- for server_prompt in mcp_server_user_prompts %}

{{ server_prompt }}
{%- endfor %}
{%- endif %}

```