# Claude Cowork Unique CLI Plugin

This plugin bundles `unique-cli` for Claude Cowork. Cowork runs commands inside a Linux VM, so the plugin ships Linux binaries for both common VM architectures:

- `bin/unique-cli-linux-amd64`
- `bin/unique-cli-linux-arm64`

`bin/unique-cli` dispatches to the right binary at runtime.

## Build

From the repository root:

```bash
./unique_sdk/claude-cowork-plugin/build/build-plugin.sh
```

The script uses Docker and PyInstaller to build both Linux binaries, then creates:

```text
unique_sdk/claude-cowork-plugin/bundles/unique-cli-plugin-<version>.zip
```

Upload the generated zip from `unique_sdk/claude-cowork-plugin/bundles/` to Claude Desktop/Cowork as the plugin package.
