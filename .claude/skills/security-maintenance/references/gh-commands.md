# GitHub CLI Commands for Security Alerts

## Dependabot

### List open alerts

```bash
gh api repos/Unique-AG/ai/dependabot/alerts --jq '.[] | select(.state=="open") | "\(.number) \(.security_advisory.severity) \(.dependency.package.ecosystem):\(.dependency.package.name) — \(.security_advisory.summary)"'
```

### Get fix version for a specific alert

```bash
gh api repos/Unique-AG/ai/dependabot/alerts/<NUMBER> --jq '.security_vulnerability.first_patched_version.identifier'
```

### Dismiss an alert (after fix is merged via your own PR)

```bash
gh api repos/Unique-AG/ai/dependabot/alerts/<NUMBER> -X PATCH -f state=dismissed -f dismissed_reason=fix_started
```

## CodeQL

### List open findings

```bash
gh api repos/Unique-AG/ai/code-scanning/alerts --jq '.[] | select(.state=="open") | "\(.number) \(.rule.severity) \(.rule.id) — \(.most_recent_instance.location.path):\(.most_recent_instance.location.start_line)"'
```

### Get details for a specific finding

```bash
gh api repos/Unique-AG/ai/code-scanning/alerts/<NUMBER> --jq '{rule: .rule.id, severity: .rule.severity, description: .rule.description, path: .most_recent_instance.location.path, start_line: .most_recent_instance.location.start_line, end_line: .most_recent_instance.location.end_line}'
```
