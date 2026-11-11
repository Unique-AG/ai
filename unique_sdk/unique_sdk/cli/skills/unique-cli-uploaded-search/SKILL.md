---
name: unique-cli-uploaded-search
description: >-
  Search the documents attached to the current message with
  `unique-cli uploaded-search "<query>"`: files the user uploaded to this chat,
  or an Agentic Table row's documents. The message names the searchable
  documents; when it names none, there is nothing to search. These
  documents are scoped to the chat, not to a knowledge-base folder, so
  knowledge-base search never returns them. When the question is about them,
  search them first. Results are `<sourceN>` blocks cited as `[sourceN]`,
  numbered continuously with knowledge-base search results within a turn. A
  file that is also in your workspace may instead be read directly and cited
  with `unique-cli cite`.
---

# Unique CLI -- Uploaded Document Search

Use `unique-cli uploaded-search` to search the documents attached to the
current message.

Mentions of `unique-cli search` apply only where knowledge-base search is
available.

## Basic Usage

```bash
# Search the documents attached to the current message
unique-cli uploaded-search "target asset classes and investment strategy"

# Limit results
unique-cli uploaded-search "fee structure" --limit 50
```

There is **no** `--folder`/`--metadata` for `uploaded-search` — the set of
documents is fixed by what this message selects.

If this message selects no documents, the command says so. Files the user did
not select for this message are not searched.

## When to use which command

| You want to search… | Command |
|---------------------|---------|
| The knowledge base, when available | `unique-cli search "<query>"` |
| Documents attached to **this** message | `unique-cli uploaded-search "<query>"` |

## Which source first

- If results are weak or off-target, switch source rather than rewording the
  query more than once.
- Use knowledge-base search, when available, for firm-wide or background facts.

## Output Format

Each result is rendered as a `<sourceN>...</sourceN>` block, identical to
`unique-cli search`. `N` is **1-based** and **shared with `unique-cli search`
within the same turn** — both commands append to the same per-turn citation
manifest, so numbering stays continuous across them (a `search` call that
emitted `<source1>`–`<source3>` is followed by an `uploaded-search` call whose
first result is `<source4>`).

```
Found 1 result(s):

<source1>
<|document|>investment-mandate.pdf</|document|>
<|page|>2</|page|>
<|info|>cont_abc123</|info|>
...the mandate targets EMEA equities with a 5% cap per issuer...
</source1>
```

## Citation Rules

Cite a fact from `uploaded-search` results with `[sourceN]`, **exactly** as you
would for `unique-cli search` — the two share the same namespace and manifest.
The Unique platform converts each `[sourceN]` marker in your final answer into a
`<sup>N</sup>` footnote and a clickable reference chip.

```
The uploaded mandate caps single-issuer exposure at 5% [source1].
```

**Rules** (enforced by the platform's reference post-processor):

1. **`[sourceN]` is for KB and uploaded-document results.** Web results from
   `unique-cli web-search` use `[websourceN]` — never mix the two namespaces.
2. Only cite numbers you saw in the **current** turn's `search` /
   `uploaded-search` output. Numbers from previous turns are stale and will be
   silently dropped.
3. Write `source` in singular form with the number in digits: `[source1]`,
   `[source2]` — not `[Source 1]` or `[source one]`.
4. Prefer citing each fact with a single, most-relevant source.
5. Do not invent source numbers for remembered or inferred facts.

## Command Reference

```
unique-cli uploaded-search <query> [--limit <N>]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--limit` | `-l` | 200 | Max results |

## Prerequisites

Requires these environment variables:

```bash
UNIQUE_USER_ID    # User ID (required)
UNIQUE_COMPANY_ID # Company ID (required)
UNIQUE_API_KEY    # API key — optional on localhost / secured cluster
UNIQUE_APP_ID     # App ID — optional on localhost / secured cluster
```

Install: `pip install unique-sdk`
