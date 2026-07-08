#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
MARKETPLACE_DIR="$(cd -- "$PLUGIN_DIR/../.." && pwd)"
PACKAGE_DIR="$(cd -- "$MARKETPLACE_DIR/.." && pwd)"
REPO_ROOT="$(cd -- "$PACKAGE_DIR/.." && pwd)"
# Build artifacts live OUTSIDE the plugin directory: plugin installs copy the
# whole plugin folder into the Claude Code cache, so anything under
# plugins/unique-cli/ (dist, venvs, bundle zips) would bloat every install.
ARTIFACTS_DIR="$MARKETPLACE_DIR/artifacts"
DIST_DIR="$ARTIFACTS_DIR/dist"
BUNDLES_DIR="$ARTIFACTS_DIR/bundles"
PLUGIN_VERSION="$(
  PLUGIN_DIR="$PLUGIN_DIR" python3 -c 'import json, os, pathlib; print(json.loads((pathlib.Path(os.environ["PLUGIN_DIR"]) / ".claude-plugin" / "plugin.json").read_text())["version"])'
)"
ZIP_PATH="$BUNDLES_DIR/unique-cli-plugin-$PLUGIN_VERSION.zip"

PYTHON_IMAGE="${PYTHON_IMAGE:-python:3.11-slim-bookworm}"
if [ "$#" -gt 0 ]; then
  PLATFORMS=("$@")
else
  PLATFORMS=("linux/amd64" "linux/arm64")
  if [ "$(uname -s)" = "Darwin" ]; then
    case "$(uname -m)" in
      x86_64|amd64)
        PLATFORMS+=("darwin/amd64")
        ;;
      arm64|aarch64)
        PLATFORMS+=("darwin/arm64")
        ;;
    esac
  fi
fi

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR" "$PLUGIN_DIR/bin" "$BUNDLES_DIR"

for platform in ${PLATFORMS[*]}; do
  case "$platform" in
    linux/amd64)
      output_name="unique-cli-linux-amd64"
      build_mode="docker"
      ;;
    linux/arm64|linux/arm64/v8)
      output_name="unique-cli-linux-arm64"
      build_mode="docker"
      ;;
    darwin/amd64)
      output_name="unique-cli-darwin-amd64"
      build_mode="local"
      expected_os="Darwin"
      expected_arches=("x86_64" "amd64")
      ;;
    darwin/arm64)
      output_name="unique-cli-darwin-arm64"
      build_mode="local"
      expected_os="Darwin"
      expected_arches=("arm64" "aarch64")
      ;;
    *)
      echo "Unsupported platform: $platform" >&2
      exit 1
      ;;
  esac

  echo "Building $output_name for $platform..."

  if [ "$build_mode" = "docker" ]; then
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
          --distpath '/workspace/unique_sdk/claude-marketplace/artifacts/dist' \
          --workpath '/tmp/pyinstaller-$output_name' \
          --specpath '/tmp' \
          '/workspace/unique_sdk/claude-marketplace/plugins/unique-cli/build/entrypoint.py'
      "
  else
    host_os="$(uname -s)"
    host_arch="$(uname -m)"
    if [ "$host_os" != "$expected_os" ]; then
      echo "Cannot build $platform on $host_os. Build this target on macOS." >&2
      exit 1
    fi

    arch_supported=false
    for expected_arch in "${expected_arches[@]}"; do
      if [ "$host_arch" = "$expected_arch" ]; then
        arch_supported=true
        break
      fi
    done
    if [ "$arch_supported" != "true" ]; then
      echo "Cannot build $platform on $host_os/$host_arch." >&2
      exit 1
    fi

    (
      cd "$PACKAGE_DIR"
      venv_dir="$DIST_DIR/.venv-$output_name"
      rm -rf "$venv_dir"
      python3 -m venv "$venv_dir"
      "$venv_dir/bin/python" -m pip install --upgrade pip
      "$venv_dir/bin/python" -m pip install pyinstaller .
      PYINSTALLER_CONFIG_DIR="$DIST_DIR/.pyinstaller" "$venv_dir/bin/python" -m PyInstaller \
        --clean \
        --onefile \
        --name "$output_name" \
        --distpath "$DIST_DIR" \
        --workpath "/tmp/pyinstaller-$output_name" \
        --specpath /tmp \
        "$PLUGIN_DIR/build/entrypoint.py"
    )
  fi

  # Remove the destination before copying: overwriting a signed Mach-O in
  # place keeps the same inode, and macOS caches code signatures per vnode.
  # The stale cache then kills the new binary with SIGKILL (Code Signature
  # Invalid) on execution.
  rm -f "$PLUGIN_DIR/bin/$output_name"
  cp "$DIST_DIR/$output_name" "$PLUGIN_DIR/bin/$output_name"
  chmod +x "$PLUGIN_DIR/bin/$output_name"
  if [ "$(uname -s)" = "Darwin" ]; then
    case "$output_name" in
      *darwin*)
        codesign --force --sign - "$PLUGIN_DIR/bin/$output_name"
        ;;
    esac
  fi
done

chmod +x "$PLUGIN_DIR/bin/unique-cli"
chmod +x "$PLUGIN_DIR/scripts/session-start.sh"

rm -f "$ZIP_PATH"
(
  cd "$PLUGIN_DIR/.."
  zip -r "$ZIP_PATH" "unique-cli" \
    -x "*.DS_Store" \
    -x "unique-cli/build/*"
)

echo "Created $ZIP_PATH"
