# skills_folder

This folder holds [Agent Skills](https://docs.cursor.com/context/rules) for Cursor — reusable instruction sets that guide Claude on specific tasks (e.g. writing PRs, debugging, testing).

## Structure

```
.claude/
└── skills/
    ├── <skill-name>/
    │   ├── SKILL.md          # skill instructions (required)
    │   ├── assets/           # templates, config snippets (optional)
    │   └── scripts/          # helper shell/python scripts (optional)
    └── ...
```

> The `.claude/` subfolder is an internal symlink used so skills resolve correctly when this folder is opened as its own repo context. You can ignore it.

## Adding a new skill

1. Create a subfolder under `skills/` with a short, hyphenated name (e.g. `skills/my-new-skill/`)
2. Add a `SKILL.md` file describing when and how to use the skill
3. Optionally add `assets/` or `scripts/` alongside it
4. Cursor will pick it up automatically — no registration required
