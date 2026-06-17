#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PACKAGE_DIR="$(cd -- "$PLUGIN_DIR/.." && pwd)"
REPO_ROOT="$(cd -- "$PACKAGE_DIR/.." && pwd)"
DIST_DIR="$PLUGIN_DIR/dist"
PLUGIN_VERSION="$(
  PLUGIN_DIR="$PLUGIN_DIR" python3 -c 'import json, os, pathlib; print(json.loads((pathlib.Path(os.environ["PLUGIN_DIR"]) / ".claude-plugin" / "plugin.json").read_text())["version"])'
)"
BUNDLES_DIR="$PLUGIN_DIR/bundles"
ZIP_PATH="$BUNDLES_DIR/unique-cli-plugin-$PLUGIN_VERSION.zip"

PYTHON_IMAGE="${PYTHON_IMAGE:-python:3.11-slim-bookworm}"
if [ "$#" -gt 0 ]; then
  PLATFORMS=("$@")
else
  PLATFORMS=("linux/amd64" "linux/arm64")
fi

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR" "$PLUGIN_DIR/bin" "$BUNDLES_DIR"

for platform in ${PLATFORMS[*]}; do
  case "$platform" in
    linux/amd64)
      output_name="unique-cli-linux-amd64"
      ;;
    linux/arm64|linux/arm64/v8)
      output_name="unique-cli-linux-arm64"
      ;;
    *)
      echo "Unsupported platform: $platform" >&2
      exit 1
      ;;
  esac

  echo "Building $output_name for $platform..."
  docker run --rm \
    --platform "$platform" \
    -v "$REPO_ROOT:/workspace" \
    -w /workspace/unique_sdk \
    "$PYTHON_IMAGE" \
    bash -lc "
      set -euo pipefail
      apt-get update
      apt-get install -y --no-install-recommends binutils
      rm -rf /var/lib/apt/lists/*
      python -m pip install --upgrade pip
      python -m pip install pyinstaller .
      pyinstaller \
        --clean \
        --onefile \
        --name '$output_name' \
        --distpath '/workspace/unique_sdk/claude-cowork-plugin/dist' \
        --workpath '/tmp/pyinstaller-$output_name' \
        --specpath '/tmp' \
        '/workspace/unique_sdk/claude-cowork-plugin/build/entrypoint.py'
    "

  cp "$DIST_DIR/$output_name" "$PLUGIN_DIR/bin/$output_name"
  chmod +x "$PLUGIN_DIR/bin/$output_name"
done

chmod +x "$PLUGIN_DIR/bin/unique-cli"

rm -f "$ZIP_PATH"
(
  cd "$PACKAGE_DIR"
  zip -r "$ZIP_PATH" "claude-cowork-plugin" \
    -x "*.DS_Store" \
    -x "claude-cowork-plugin/dist/*" \
    -x "claude-cowork-plugin/build/*" \
    -x "claude-cowork-plugin/bundles/*"
)

echo "Created $ZIP_PATH"
