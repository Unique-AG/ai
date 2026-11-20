# Unique public agent skills

Skills in this directory are meant for [skills.sh](https://www.skills.sh/) / `npx skills add`. They encode Unique platform conventions for agents that are **not** necessarily working inside this monorepo.

Internal Unique-AG/ai workflows (PR review, CI, Poetry, …) stay in [`.claude/skills/`](../.claude/skills/).

| Skill | Install |
| ----- | ------- |
| [unique-mcp](unique-mcp/) | `npx skills add Unique-AG/ai/skills/unique-mcp` |

```bash
npx skills add Unique-AG/ai --skill unique-mcp
npx skills add Unique-AG/ai/skills/unique-mcp -g   # user-level
```

After the first public install, the skill can appear on [skills.sh](https://www.skills.sh/) via install telemetry.
