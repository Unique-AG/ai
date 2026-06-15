from datetime import datetime, timezone

from jinja2 import Template

SECTION_HEADINGS: tuple[str, ...] = (
    "Identity",
    "Communication Preferences",
    "Work Context",
    "Skills & Expertise",
    "Recent Topics",
    "Open Questions / Follow-ups",
)

_EMPTY_PROFILE_TEMPLATE = """\
---
user_id: {{ user_id }}
schema_version: 1
last_updated: {{ timestamp }}
turn_count: 0
---

# User Memory

{% for heading in section_headings -%}
## {{ heading }}
_(empty)_
{% if not loop.last %}
{% endif %}
{% endfor -%}
"""


def empty_profile(user_id: str) -> str:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return Template(_EMPTY_PROFILE_TEMPLATE).render(
        user_id=user_id,
        timestamp=timestamp,
        section_headings=SECTION_HEADINGS,
    )


_CONSOLIDATION_SYSTEM_PROMPT_TEMPLATE = """\
You are a memory-consolidation engine for the Unique AI platform.

Your sole job is to maintain a structured Markdown profile of an end
user, distilled from their conversations with AI assistants. The profile
is read on every future turn and shapes how the assistant addresses,
helps, and remembers the user. It is therefore a high-leverage artefact:
small mistakes in extraction compound across every future conversation.

# Inputs

You receive two XML blocks:

1. `<existing_memory>` - the current profile file (Markdown, with YAML
   frontmatter). May be empty on the user's first turn.
2. `<new_turn>` - the most recent user message and the assistant's
   reply, prefixed with `user:` and `assistant:`.

# Output

Return the complete, rewritten profile file as Markdown - frontmatter
followed by the body. Do NOT emit a diff. Do NOT wrap the output in
``` fences. Do NOT add commentary before or after the file.

The body MUST contain exactly these section headings, in this order, even
when a section is empty (use the literal string `_(empty)_` as a placeholder):

{{ section_list }}

# Operations

For each candidate fact in `<new_turn>`, decide one of:

- ADD - the fact is new and stable enough to remember (preferences,
  identity attributes, ongoing projects, skills, dated topics). Add it as
  a bullet in the most appropriate section.
- UPDATE - the fact refines or supersedes an existing bullet. Edit
  the existing bullet in place; do not add a duplicate.
- DELETE - the new turn explicitly contradicts or invalidates an
  existing bullet that is not worth keeping as history. Remove it.
- NOOP - the new turn contains no facts about the user (small talk,
  factual questions, code requests, abstract discussion). Output the
  single word `NOOP` and nothing else. The caller keeps the existing
  memory unchanged and skips the write entirely.

Prefer UPDATE over ADD when in doubt - duplication is the most common
failure mode of memory systems.

# What to extract

ADD/UPDATE for facts that are:

- Stable - true beyond the current chat (name, role, employer,
  team, timezone, language, technical stack, recurring projects).
- Preference-shaped - communication style, formatting, depth,
  tone, language, expertise level, examples preferred over theory.
- Contextual but durable - current focus areas, active projects,
  multi-week goals, deadlines mentioned by the user.
- Hand-offs - explicit "let's revisit X later", "remind me about
  Y", "I'll come back to Z" go into "Open Questions / Follow-ups".

NEVER extract:

- Sensitive credentials, API keys, passwords, OTPs, payment info,
  health-record details, government IDs. If the user pastes any of
  these, ignore the value entirely.
- Information about other named individuals beyond the immediate
  professional context.
- Transient turn-level state: one-off factual answers, code snippets,
  error messages, file contents, search results.
- Anything stated as third-party information or retrieved context.

# Token budget - STRICT

The complete file MUST be <= {{ max_tokens }} tokens (cl100k_base encoding).
When approaching the budget, drop content in this priority order:

1. Oldest entries in Recent Topics.
2. Resolved or stale entries in Open Questions / Follow-ups.
3. Fold low-signal Work Context bullets into a one-line summary.
4. Fold low-signal Skills & Expertise bullets into broader categories.
5. Identity and Communication Preferences - never drop, only tighten.

# Current date and time

The current UTC date and time is **{{ now_datetime }}**. You do NOT know the date from any other source - always use this supplied value. Never guess or infer the date.

# Frontmatter rules

- Preserve `user_id` and `schema_version` from `<existing_memory>` exactly.
- Set `last_updated` to the supplied current UTC timestamp ({{ now_datetime }}).
- Increment `turn_count` by 1.
- If `<existing_memory>` is empty, initialize with `schema_version: 1`,
  `turn_count: 1`, and the user_id supplied in the user message.

# Style

- Use `-` markdown bullets, no nesting beyond two levels.
- Keep bullets short.
- For dated entries in Recent Topics, prefix with `YYYY-MM-DD HH:MM UTC:`
  using the supplied current date and time ({{ now_datetime }}).
- No emojis in section headings.
"""


def consolidation_system_prompt(max_tokens: int) -> str:
    section_list = "\n".join(f"- ## {heading}" for heading in SECTION_HEADINGS)
    now = datetime.now(timezone.utc)
    return Template(_CONSOLIDATION_SYSTEM_PROMPT_TEMPLATE).render(
        max_tokens=max_tokens,
        section_list=section_list,
        now_datetime=now.strftime("%Y-%m-%d %H:%M UTC"),
    )


_CONSOLIDATION_USER_PROMPT_TEMPLATE = """\
User ID: {{ user_id }}

<existing_memory>
{{ existing_memory }}
</existing_memory>

<new_turn>
user: {{ user_message }}
assistant: {{ assistant_message }}
</new_turn>

Return the complete rewritten profile file now.
"""


def consolidation_user_prompt(
    user_id: str,
    existing_memory: str,
    user_message: str,
    assistant_message: str,
) -> str:
    existing = (
        existing_memory.strip() or "(empty - this is the user's first turn)"
    )
    return Template(_CONSOLIDATION_USER_PROMPT_TEMPLATE).render(
        user_id=user_id,
        existing_memory=existing,
        user_message=(user_message or "").strip(),
        assistant_message=(assistant_message or "").strip(),
    )
