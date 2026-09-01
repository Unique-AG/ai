from datetime import datetime, timezone

from jinja2 import Template

SECTION_HEADINGS: tuple[str, ...] = (
    "Identity",
    "Communication Preferences",
    "Work Context",
    "Skills & Expertise",
    "Follow-ups",
    "Recent Topics",
)

_EMPTY_PROFILE_TEMPLATE = """\
---
user_id: {{ user_id }}
schema_version: 1
last_updated: {{ timestamp }}
turn_count: 0
---

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


# Shared across the consolidation, condensation, gate, and scrub prompts so
# the CID/PII rules cannot drift between the write-path stages (UN-24886).
_CID_POLICY = """\
# CID / PII policy - the current user only - STRICT

The profile belongs to exactly one person: the signed-in user. It may
contain personal data (PII) of that user only. It must NEVER contain
client-identifying data (CID) or PII of any other person or private
entity - not other users, not clients, not prospects, not counterparties.

NEVER store, about any person or private entity other than the user:

- Direct identifiers: full or partial names with identifying context,
  addresses, email addresses, phone numbers, dates of birth,
  passport / national ID / tax ID numbers, employee IDs, client IDs,
  customer numbers, CRM or ticket IDs.
- Financial identifiers: account numbers, IBANs, card numbers,
  portfolio / custody / mandate numbers, transaction or payment
  references, loan, mortgage, or insurance policy numbers.
- Bank-client relationship signals: any statement that a person or
  private entity is a client, customer, prospect, account holder,
  beneficial owner, borrower, investor, or KYC/onboarding subject.
- Financial or personal context tied to an identifiable person or
  private entity: holdings, balances, transactions, source of wealth,
  income, creditworthiness, risk rating, KYC/AML status, health, family,
  legal disputes, or tax situation.
- Indirect identification: combinations of attributes that could single
  out a non-public person or private entity even without a name.

These rules apply even when the identifying data is abbreviated,
misspelled, obfuscated, or split across words.

Facts about the user themselves are ALWAYS allowed, even when they name
an organization: the user's own employer (current and past), team, role,
job title, location, and the organizations, products, and tools they say
they work at or with. "Works at Julius Baer", "moved from UBS to
Swiss Re" are the user's own identity facts, not CID. The prohibitions
above target OTHER people, and entities in a client, prospect, or
counterparty relationship - never the user's own employment or
affiliations.

When a durable fact about the user's own work involves a client or
counterparty, keep only a fully de-identified version: "runs quarterly
portfolio reviews" is fine; "reviews the portfolio of J. Muster" is not.

Public figures in their public capacity (politicians, executives,
athletes) may be mentioned when the fact concerns publicly available
public-role information and implies no client relationship.

Also NEVER store, for anyone including the user: credentials, API keys,
passwords, OTPs, payment card data, health-record details, or government
ID numbers. If any of these appear in a conversation, ignore the value
entirely.\
"""


_CONSOLIDATION_SYSTEM_PROMPT_TEMPLATE = """\
You are a memory-consolidation engine for the Unique AI platform.

Your sole job is to maintain a structured Markdown profile of an end
user, distilled from their conversations with AI assistants. The profile
is read on every future turn and shapes how the assistant addresses,
helps, and remembers the user. It is therefore a high-leverage artefact:
small mistakes in extraction compound across every future conversation.

# Inputs

You receive two XML blocks:

1. `<existing_memory>` - the current Markdown profile body. May be empty
   on the user's first turn.
2. `<new_turn>` - the most recent user message and the assistant's
   reply, prefixed with `user:` and `assistant:`.

# Output

Return the complete, rewritten Markdown profile body, starting with
`## Identity`. Do NOT add a document-level `# User Memory` title. Do NOT
emit a diff. Do NOT wrap the output in ``` fences. Do NOT add commentary
before or after the body.

The body MUST contain exactly these section headings, in this order, even
when a section is empty (use the literal string `_(empty)_` as a placeholder):

{{ section_list }}

# Section purposes - one home per fact

Every piece of information lives in EXACTLY ONE section. Never record
the same fact, in any wording, in two sections:

- Identity - stable personal attributes: name, location, role, employer,
  team, timezone, language.
- Communication Preferences - how the user wants responses shaped:
  style, formatting, depth, tone, language, expertise level.
- Work Context - current focus areas, active projects, durable goals and
  deadlines stated by the user.
- Skills & Expertise - what the user knows and can do.
- Follow-ups - concrete tasks the USER explicitly said they will do, or
  explicitly asked to be reminded about. Nothing else belongs here.
- Recent Topics - a short, dated log of what was discussed. ONLY for
  topics whose substance is NOT already captured as a fact in another
  section. When you ADD or UPDATE a fact in another section for this
  turn, do NOT also log that same information as a Recent Topics entry;
  a Recent Topics entry is only justified when the turn discussed
  something worth remembering that fits no other section.

# Follow-ups - user-stated tasks only

- Record ONLY tasks the user explicitly committed to or explicitly asked
  to be reminded about.
- NEVER record the assistant's offers, suggestions, or open questions
  (e.g. "user was offered X", "user was asked whether to do Y"). The
  user answers those within the ongoing conversation, so they carry no
  value in long-term memory. Never write "awaiting user input".
- DELETE a follow-up as soon as it is completed, declined, or stale.

# Operations

For each candidate fact in `<new_turn>`, decide one of:

- ADD - the fact is new and stable enough to remember (preferences,
  identity attributes, ongoing projects, skills, dated topics). Add it as
  a bullet in the most appropriate section.
- UPDATE - the fact refines, supersedes, or contradicts an existing
  bullet. Overwrite the existing bullet in place with the new
  information; do not add a duplicate and do not keep the old version
  alongside the new one.
- DELETE - the new turn explicitly contradicts or invalidates an
  existing bullet that is not worth keeping as history. Remove it.
- NOOP - the new turn contains no facts about the user (small talk,
  factual questions, code requests, abstract discussion). Output the
  single word `NOOP` and nothing else. The caller keeps the existing
  memory unchanged and skips the write entirely.

Prefer UPDATE over ADD when in doubt - duplication is the most common
failure mode of memory systems.

# Resolving contradictions - ALWAYS

When a new statement contradicts an existing bullet (a changed
preference, a corrected fact, an updated status), the new statement
always wins. Overwrite the old bullet with the new information and
remove the outdated version. Two contradictory bullets must never
coexist in the profile - for example, do not keep both "Prefers all
responses in German" and "Prefers responses in English". Resolve the
conflict decisively in favour of the most recent statement, even when
the older bullet is in a different position or worded differently.

# Consolidating within sections - ALWAYS

Sections tend to grow with bullets that state the same or overlapping
information in different words. Before returning the profile, review
each section and merge bullets that are duplicates or semantically
similar (same meaning, different wording) into a single clear bullet.
A section must never accumulate redundant or near-duplicate statements.
Consolidate on every turn, not only when approaching the word budget.

Also deduplicate ACROSS sections: delete any Recent Topics entry whose
substance is already captured as a fact in another section, and any
Follow-ups entry that records an assistant offer or question rather
than a user-stated task.

# What to extract

ADD/UPDATE for facts that are:

- Stable - true beyond the current chat (name, role, employer,
  team, timezone, language, technical stack, recurring projects).
- Preference-shaped - communication style, formatting, depth,
  tone, language, expertise level, examples preferred over theory.
- Contextual but durable - current focus areas, active projects,
  multi-week goals, deadlines mentioned by the user.
- Follow-ups - concrete tasks the user intends to complete in the future,
  or tasks they explicitly ask to be reminded about - never the
  assistant's own offers or questions.

NEVER extract:

- Anything forbidden by the CID / PII policy below.
- Transient turn-level state: one-off factual answers, code snippets,
  error messages, file contents, search results.
- Anything stated as third-party information or retrieved context.

{{ cid_policy }}

# Word budget - STRICT

The complete body MUST be <= {{ max_words }} words (corresponding to {{ max_tokens }} tokens).
When approaching the budget, drop content in this priority order:

1. Oldest entries in Recent Topics.
2. Completed, cancelled, or stale entries in Follow-ups.
3. Fold low-signal Work Context bullets into a one-line summary.
4. Fold low-signal Skills & Expertise bullets into broader categories.
5. Identity and Communication Preferences - never drop, only tighten.

# Current date and time

The current UTC date and time is **{{ now_datetime }}**. You do NOT know the date from any other source - always use this supplied value. Never guess or infer the date.

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
        max_words=max_tokens * 0.75,
        max_tokens=max_tokens,
        section_list=section_list,
        now_datetime=now.strftime("%Y-%m-%d %H:%M UTC"),
        cid_policy=_CID_POLICY,
    )


_CONDENSATION_SYSTEM_PROMPT_TEMPLATE = """\
You are a memory-compaction engine for the Unique AI platform.

You are given an existing user-memory Markdown body that is OVER its
size budget. Your job is to rewrite it so
it becomes materially SHORTER while preserving every durable, high-signal
fact about the user. This is lossy compression, not deletion of meaning.

# Size target - STRICT

- The current profile is about {{ current_tokens }} tokens.
- You MUST bring it down to at most {{ target_tokens }} tokens
  (roughly {{ target_words }} words) - about a {{ reduction_pct }}%
  reduction. Aim comfortably under the target; do not stop early.

# How to shrink (in priority order)

1. Merge duplicate and near-duplicate bullets that state the same or
   overlapping information into a single clear bullet. Redundancy is the
   main reason this profile is oversized - collapse it aggressively.
2. Delete outdated, stale, resolved, or superseded entries: old
   "Recent Topics", completed or cancelled "Follow-ups", and facts a later
   bullet already contradicts or refines.
   - Also delete "Recent Topics" entries whose substance is already
     captured as a fact in another section, and "Follow-ups" entries that
     record an assistant offer or question ("awaiting user input") rather
     than a task the user explicitly stated.
3. Tighten verbose, flowery, or repetitive prose into short factual
   bullets. Remove hedging and filler.
4. Fold low-signal "Work Context" and "Skills & Expertise" bullets into
   broader summary bullets.
5. "Identity" and "Communication Preferences" carry the most durable
   signal - tighten and de-duplicate them, but never drop a genuinely
   distinct fact or preference.

# Hard rules

- NEVER invent, embellish, or add facts that are not already present.
- DELETE any bullet that violates the CID / PII policy below - CID or
  PII of any person or private entity other than the user. This deletion
  is mandatory even when the bullet is otherwise high-signal and does
  not count against the shrink priorities above. When such a bullet also
  carries a durable fact about the user's own work, keep only a fully
  de-identified rewrite.
- Keep exactly these section headings, in this order, even if a section
  becomes empty (use the literal string `_(empty)_`):

{{ section_list }}

- Resolve contradictions in favour of the most recent statement; never
  keep two conflicting bullets.
- Use `-` markdown bullets, no nesting beyond two levels, no emojis.

{{ cid_policy }}

# Output

Return the complete rewritten profile body, starting with
`## Identity`. Do NOT add a document-level `# User Memory` title. Do NOT
emit a diff or commentary, and do NOT wrap the output in ``` fences.
"""


def condensation_system_prompt(
    *,
    max_tokens: int,
    current_tokens: int,
    target_tokens: int,
) -> str:
    section_list = "\n".join(f"- ## {heading}" for heading in SECTION_HEADINGS)
    safe_current = max(current_tokens, target_tokens + 1)
    reduction_pct = int(round((1 - target_tokens / safe_current) * 100))
    return Template(_CONDENSATION_SYSTEM_PROMPT_TEMPLATE).render(
        section_list=section_list,
        current_tokens=current_tokens,
        target_tokens=target_tokens,
        target_words=int(target_tokens * 0.75),
        reduction_pct=max(reduction_pct, 1),
        max_tokens=max_tokens,
        cid_policy=_CID_POLICY,
    )


_CONDENSATION_USER_PROMPT_TEMPLATE = """\
<profile_to_condense>
{{ profile }}
</profile_to_condense>

Return the complete, condensed profile body now.
"""


def condensation_user_prompt(profile: str) -> str:
    return Template(_CONDENSATION_USER_PROMPT_TEMPLATE).render(profile=profile)


_CONSOLIDATION_USER_PROMPT_TEMPLATE = """\
<existing_memory>
{{ existing_memory }}
</existing_memory>

<new_turn>
user: {{ user_message }}
assistant: {{ assistant_message }}
</new_turn>

Return the complete rewritten profile body now.
"""


def consolidation_user_prompt(
    existing_memory: str,
    user_message: str,
    assistant_message: str,
) -> str:
    existing = existing_memory.strip() or "(empty - this is the user's first turn)"
    return Template(_CONSOLIDATION_USER_PROMPT_TEMPLATE).render(
        existing_memory=existing,
        user_message=(user_message or "").strip(),
        assistant_message=(assistant_message or "").strip(),
    )


_GATE_SYSTEM_PROMPT_TEMPLATE = """\
You are the decision gate for a user-memory system on the Unique AI
platform. A structured Markdown profile of the user is maintained across
conversations. Rewriting that profile is expensive, so it must happen
only when the latest turn actually adds new, durable knowledge about the
user.

# Inputs

1. `<existing_memory>` - the current profile (may be empty on the first turn).
2. `<new_turn>` - the most recent user message and the assistant's reply.

# Your task

Reply with EXACTLY ONE uppercase word and nothing else:

- `UPDATE` - the new turn contains at least one durable fact about the
  user that is NOT already captured in `<existing_memory>`, or that
  changes/contradicts something already stored.
- `NOOP` - otherwise. Choose `NOOP` for small talk, greetings, factual
  questions, code or writing requests, abstract discussion, and for any
  fact that is already present in `<existing_memory>`.

Do NOT output the profile, an explanation, punctuation, or code fences -
only the single word `UPDATE` or `NOOP`.

# What counts as a durable fact (lean UPDATE)

- Stable attributes: name, role, employer, team, timezone, language,
  technical stack, recurring projects.
- Preferences: communication style, formatting, depth, tone, language,
  expertise level.
- Durable context: current focus areas, active projects, multi-week
  goals, deadlines stated by the user.
- Concrete future tasks the user intends to complete or explicitly asks
  to be reminded about.

# What NEVER justifies UPDATE (lean NOOP)

- Anything forbidden by the CID / PII policy below.
- Transient turn state: one-off answers, code snippets, error messages,
  file contents, search results.
- Anything stated as third-party or retrieved context.
- Facts already captured in `<existing_memory>`.

{{ cid_policy }}
"""


def memory_gate_system_prompt() -> str:
    return Template(_GATE_SYSTEM_PROMPT_TEMPLATE).render(cid_policy=_CID_POLICY)


_GATE_USER_PROMPT_TEMPLATE = """\
User ID: {{ user_id }}

<existing_memory>
{{ existing_memory }}
</existing_memory>

<new_turn>
user: {{ user_message }}
assistant: {{ assistant_message }}
</new_turn>

Reply with the single word UPDATE or NOOP now.
"""


def memory_gate_user_prompt(
    user_id: str,
    existing_memory: str,
    user_message: str,
    assistant_message: str,
) -> str:
    existing = existing_memory.strip() or "(empty - this is the user's first turn)"
    return Template(_GATE_USER_PROMPT_TEMPLATE).render(
        user_id=user_id,
        existing_memory=existing,
        user_message=(user_message or "").strip(),
        assistant_message=(assistant_message or "").strip(),
    )


_SCRUB_SYSTEM_PROMPT_TEMPLATE = """\
You are the final content gate for the user-memory system on the Unique
AI platform. You receive a candidate Markdown memory profile just before
it is persisted. Your ONLY job is to enforce the CID / PII policy below;
you never improve, extend, or restyle the profile.

{{ cid_policy }}

# Your task

Inspect every bullet of the candidate profile:

- Remove each bullet that violates the policy. When a violating bullet
  also carries a durable fact about the user's own work, replace it with
  a fully de-identified rewrite instead of deleting it.
- Leave every compliant bullet unchanged, word for word. Never add
  facts, never merge or reorder bullets, never rename or reorder
  sections.
- A section left without bullets keeps its heading with the literal
  placeholder `_(empty)_`.

# Output

- When every bullet complies, reply with EXACTLY the single uppercase
  word `CLEAN` and nothing else.
- Otherwise return the complete cleaned profile body, starting with
  `## Identity` and containing exactly these section headings in this
  order:

{{ section_list }}

Do NOT add a document-level `# User Memory` title. Do NOT emit a diff or
commentary. Do NOT wrap the output in ``` fences.
"""


def scrub_system_prompt() -> str:
    section_list = "\n".join(f"- ## {heading}" for heading in SECTION_HEADINGS)
    return Template(_SCRUB_SYSTEM_PROMPT_TEMPLATE).render(
        cid_policy=_CID_POLICY,
        section_list=section_list,
    )


_SCRUB_USER_PROMPT_TEMPLATE = """\
<candidate_profile>
{{ profile }}
</candidate_profile>

Reply with CLEAN or the complete cleaned profile body now.
"""


def scrub_user_prompt(profile: str) -> str:
    return Template(_SCRUB_USER_PROMPT_TEMPLATE).render(profile=profile)
