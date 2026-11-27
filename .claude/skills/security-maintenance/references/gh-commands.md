# GitHub CLI Commands for Security Alerts

## Dependabot

> The Dependabot alerts endpoint is **cursor-paginated**; `?page=N` is rejected. Always use `gh api --paginate ... | jq -s 'add'` or you'll silently cap at one page (100 alerts) and get wrong counts / wrong "oldest" timestamps.

### List open alerts (all pages)

```bash
gh api --paginate "repos/Unique-AG/ai/dependabot/alerts?state=open&per_page=100" \
  | jq -s 'add | .[] | "\(.number) \(.security_advisory.severity) \(.dependency.package.ecosystem):\(.dependency.package.name) — \(.security_advisory.summary)"'
```

### Quick severity counts

```bash
gh api --paginate "repos/Unique-AG/ai/dependabot/alerts?state=open&per_page=100" \
  | jq -s 'add | {
      total: length,
      critical: [.[] | select(.security_advisory.severity=="critical")] | length,
      high:     [.[] | select(.security_advisory.severity=="high")]     | length,
      medium:   [.[] | select(.security_advisory.severity=="medium")]   | length,
      low:      [.[] | select(.security_advisory.severity=="low")]      | length,
      oldest:   ([.[] | .created_at] | sort | first)
    }'
```

### Get fix version for a specific alert

```bash
gh api repos/Unique-AG/ai/dependabot/alerts/<NUMBER> --jq '.security_vulnerability.first_patched_version.identifier'
```

### Dismiss an alert (after fix is merged via your own PR)

```bash
gh api repos/Unique-AG/ai/dependabot/alerts/<NUMBER> -X PATCH -f state=dismissed -f dismissed_reason=fix_started
```

## Trivy image alerts

Image scan results (`[Security] Trivy Image Scan`) land in code scanning with `tool.name` Trivy. The category tells the source: `trivy-image/<package>` is a fresh build of `main`, `trivy-image-release/<package>` is a published release.

### List open image alerts

```bash
gh api --paginate "repos/Unique-AG/ai/code-scanning/alerts?state=open&per_page=100&tool_name=Trivy" \
  | jq -s 'add | .[] | "\(.number) \(.rule.security_severity_level) \(.rule.id) \(.most_recent_instance.category) \(.most_recent_instance.location.path)"'
```

The path shows what to fix: `app/.venv/lib/python3.12/site-packages/<pkg>-<version>.dist-info/METADATA` is a Python dependency, and a path that is only the image name (`unique-ag/ai/search-proxy`) is a Debian package.

### Read one alert (package, installed and fixed version)

```bash
gh api repos/Unique-AG/ai/code-scanning/alerts/<NUMBER> --jq '.most_recent_instance.message.text'
```

### Re-scan after the fix merged

```bash
gh workflow run "[Security] Trivy Image Scan" --ref main            # build main
gh workflow run "[Security] Trivy Image Scan" --ref main -f source=release   # latest published release
```

## CodeQL

### List open findings (all pages)

```bash
gh api --paginate "repos/Unique-AG/ai/code-scanning/alerts?state=open&per_page=100&tool_name=CodeQL" \
  | jq -s 'add | .[] | "\(.number) \(.rule.severity) \(.rule.id) — \(.most_recent_instance.location.path):\(.most_recent_instance.location.start_line)"'
```

### Get details for a specific finding

```bash
gh api repos/Unique-AG/ai/code-scanning/alerts/<NUMBER> --jq '{rule: .rule.id, severity: .rule.severity, description: .rule.description, path: .most_recent_instance.location.path, start_line: .most_recent_instance.location.start_line, end_line: .most_recent_instance.location.end_line}'
```
