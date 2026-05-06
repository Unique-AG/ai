# Common CodeQL Fix Patterns

CodeQL fixes require code changes — there is no config shortcut. Below are common vulnerability classes and their remediation patterns.

## SQL injection

**Problem**: User input interpolated into SQL strings.

**Fix**: Use parameterized queries.

```python
# Bad
cursor.execute(f"SELECT * FROM users WHERE id = '{user_id}'")

# Good
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

## Path traversal

**Problem**: User-controlled input used in file paths without validation.

**Fix**: Validate and resolve paths, ensure they stay within allowed directories.

```python
# Bad
open(os.path.join(base_dir, user_input))

# Good
resolved = os.path.realpath(os.path.join(base_dir, user_input))
if not resolved.startswith(os.path.realpath(base_dir)):
    raise ValueError("Path traversal detected")
open(resolved)
```

## Hardcoded credentials

**Problem**: Secrets, API keys, or passwords in source code.

**Fix**: Move to environment variables or a secret manager.

```python
# Bad
api_key = "sk-1234567890"

# Good
api_key = os.environ["API_KEY"]
```

## Unsafe deserialization

**Problem**: Loading untrusted data with `pickle`, `yaml.load`, or similar.

**Fix**: Use safe loaders or validate input.

```python
# Bad
data = yaml.load(content)
data = pickle.loads(payload)

# Good
data = yaml.safe_load(content)
data = json.loads(payload)  # prefer JSON over pickle for untrusted data
```

## Command injection

**Problem**: User input passed to shell commands via string concatenation.

**Fix**: Use subprocess with argument lists, never `shell=True` with user input.

```python
# Bad
os.system(f"grep {query} /var/log/app.log")
subprocess.run(f"grep {query} /var/log/app.log", shell=True)

# Good
subprocess.run(["grep", query, "/var/log/app.log"], check=True)
```

## Server-side request forgery (SSRF)

**Problem**: User-controlled URLs passed to HTTP requests without validation.

**Fix**: Validate URLs against an allowlist, block internal/private ranges.

```python
# Bad
response = requests.get(user_provided_url)

# Good
from urllib.parse import urlparse
parsed = urlparse(user_provided_url)
if parsed.hostname not in ALLOWED_HOSTS:
    raise ValueError("URL not allowed")
response = requests.get(user_provided_url)
```
