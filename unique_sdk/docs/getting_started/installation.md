# Installation

Install the Unique Python SDK from [PyPI](https://pypi.org/project/unique-sdk/).

## Requirements

- Python 3.11 or higher

## Install via pip

```bash
pip install unique-sdk
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install unique-sdk
```

This installs the SDK with all required dependencies, including the `unique-cli` command-line tool.

## Optional: OpenAI Integration

To use the OpenAI integration utilities:

```bash
pip install unique-sdk[openai]
```

## Verify Installation

Verify the installation by importing the SDK:

```python
import unique_sdk
print("SDK installed successfully")
```

Verify the CLI is available:

```bash
unique-cli --version
```

## Next Steps

Now that you've installed the SDK:

1. **[Configure your credentials](configuration.md)** - Set up your API key and App ID
2. **[Try the Quickstart guide](quickstart.md)** - Make your first API call
3. **[Explore API Resources](../api_resources/index.md)** - Learn about available APIs
4. **[Try the CLI](../cli/index.md)** - Browse files interactively
5. **[Check out Tutorials](../tutorials/folder_updates.md)** - See step-by-step tutorials