# exclude-newer and exclude-newer-package

## How it works

The root `pyproject.toml` sets a global rolling window:

```toml
[tool.uv]
exclude-newer = "2 weeks"
```

This tells `uv` to ignore any package version whose PyPI artifacts were uploaded after the cutoff. This prevents unexpected breakage from brand-new releases but can conflict with security fixes that were published recently.

## When you need an override

If a security fix version was published within the last 2 weeks, `uv lock` will fail to resolve it. Add a per-package override:

```toml
[tool.uv.exclude-newer-package]
"<package>" = "YYYY-MM-DD"
```

## Finding the correct timestamp

The timestamp must be the **day after** the latest artifact (wheel/sdist) upload time for the required version. `uv` uses a strict `<` comparison on individual wheel upload times, not the version's publication date.

### Step-by-step

1. Query the PyPI JSON API for the latest artifact upload time:
   ```bash
   curl -s https://pypi.org/pypi/<package>/<version>/json | python3 -c "
   import sys, json
   data = json.load(sys.stdin)['urls']
   print(max(u['upload_time_iso_8601'] for u in data))
   "
   ```

2. Round up to the **next day**. For example:
   - Latest upload: `2026-04-08T23:45:00Z` → use `"2026-04-09"`
   - Latest upload: `2026-04-09T00:01:00Z` → use `"2026-04-10"`

3. Never use the exact upload time or same day — some wheels for different Python versions / platforms are uploaded over several minutes or hours.

## Pruning stale entries

Any `exclude-newer-package` timestamp older than the `exclude-newer` window (currently 2 weeks) is **redundant** — the global window already allows that version through. Remove these during every maintenance session.

Keep entries that are:
- Set to `false` (permanent overrides, e.g. `unique-toolkit`)
- Still within the 2-week window

## Example

```toml
[tool.uv]
exclude-newer = "2 weeks"
constraint-dependencies = [
    "cryptography>=46.0.7",
]

[tool.uv.exclude-newer-package]
"unique-toolkit" = false            # permanent — always use latest workspace version
"cryptography" = "2026-04-09"       # security fix, published 2026-04-08 — remove after 2026-04-22
```
