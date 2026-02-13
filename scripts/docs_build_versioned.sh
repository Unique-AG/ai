#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Local Documentation Versioning Build Script
# ============================================================================
# Simulates the CI workflow locally to test multi-version docs structure.
#
# Usage:
#   ./scripts/docs_build_versioned.sh [options]
#
# Options:
#   --clean               Clean _local_docs before building
#   --serve               Start local server after building (port 8000)
#   --sdk-version VER     Override SDK version (default: read from pyproject.toml)
#   --toolkit-version VER Override Toolkit version (default: read from pyproject.toml)
#   --port PORT           Server port (default: 8000)
#   --help                Show this help message
#
# Examples:
#   ./scripts/docs_build_versioned.sh --clean --serve
#   ./scripts/docs_build_versioned.sh --sdk-version 0.10.76 --serve
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$REPO_ROOT/_local_docs"

# Default options
CLEAN=false
SERVE=false
SDK_VERSION=""
TOOLKIT_VERSION=""
PORT=8000

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    sed -n '/^# ====/,/^# ====/p' "$0" | sed 's/^# //g' | head -n -1 | tail -n +2
    exit 0
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v poetry &> /dev/null; then
        log_error "Poetry not found. Please install: https://python-poetry.org/docs/#installation"
        exit 1
    fi
    
    if ! poetry show mkdocs &> /dev/null; then
        log_error "mkdocs not installed. Run: poetry install --with dev"
        exit 1
    fi
    
    log_success "Dependencies OK"
}

get_version_from_pyproject() {
    local project_dir=$1
    poetry -C "$project_dir" version -s
}

# Copy the versioned site into latest/ so that /latest/ and /latest/any/subpath/ both work
copy_version_to_latest() {
    local output_path=$1
    local version=$2
    if [ -d "$output_path/$version" ]; then
        log_info "Copying $output_path/$version/ -> $output_path/latest/"
        rm -rf "$output_path/latest"
        cp -r "$output_path/$version" "$output_path/latest"
    else
        log_warn "$output_path/$version not found, skipping latest copy"
    fi
}

# Redirect /unique-sdk/ and /unique-toolkit/ to .../latest/ so the base path doesn't list subfolders
create_base_redirect() {
    local output_path=$1
    mkdir -p "$output_path"
    cat > "$output_path/index.html" <<EOF
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="0; url=latest/">
    <link rel="canonical" href="latest/">
    <title>Redirecting to latest</title>
  </head>
  <body>
    <p>Redirecting to <a href="latest/">latest</a>...</p>
  </body>
</html>
EOF
}

generate_versions_json() {
    local project_dir=$1
    local current_version=$2
    local output_file=$3
    
    log_info "Generating versions.json for $(basename "$project_dir")"
    mkdir -p "$(dirname "$output_file")"
    
    # Find version directories: only include semver-like names (e.g. 1.46.4, 0.10.80)
    # Exclude: latest, unique_toolkit, unique_sdk, and any other non-version folder
    local versions=()
    if [ -d "$project_dir" ]; then
        while IFS= read -r dir; do
            local version=$(basename "$dir")
            # Must look like a version: digits.digits.digits (optional suffix e.g. -rc1, .0)
            if [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+.*$ ]] && [ -d "$dir" ]; then
                versions+=("$version")
            fi
        done < <(find "$project_dir" -maxdepth 1 -type d -not -name ".")
    fi
    
    # Add current version if not in list
    if [[ ! " ${versions[@]} " =~ " ${current_version} " ]]; then
        versions+=("$current_version")
    fi
    
    # Sort versions (semantic sort)
    IFS=$'\n' versions=($(sort -V -r <<<"${versions[*]}"))
    unset IFS
    
    # Generate JSON
    echo "[" > "$output_file"
    local first=true
    for version in "${versions[@]}"; do
        if [ "$first" = false ]; then
            echo "," >> "$output_file"
        fi
        first=false
        
        local title="$version"
        local aliases="[]"
        if [ "$version" = "$current_version" ]; then
            aliases='["latest"]'   # Theme shows "(latest)" via alias; keep title as plain version
        fi
        
        echo -n "  {\"version\": \"$version\", \"title\": \"$title\", \"aliases\": $aliases}" >> "$output_file"
    done
    echo "" >> "$output_file"
    echo "]" >> "$output_file"
    
    log_success "Generated versions.json with ${#versions[@]} version(s)"
}

build_root_site() {
    log_info "Building root site..."
    cd "$REPO_ROOT"
    
    # Build to temporary location
    poetry run mkdocs build -d "$OUTPUT_DIR/root_temp" --clean
    
    # Copy to output root (excluding subdirs we'll replace)
    rsync -av --exclude='unique-sdk' --exclude='unique-toolkit' "$OUTPUT_DIR/root_temp/" "$OUTPUT_DIR/"
    rm -rf "$OUTPUT_DIR/root_temp"
    
    log_success "Root site built"
}

build_project_site() {
    local project_name=$1
    local project_dir=$2
    local version=$3
    local output_path="$OUTPUT_DIR/$project_name/$version"
    
    log_info "Building $project_name v$version..."
    
    # Check if already built
    if [ -d "$output_path" ] && [ "$(ls -A "$output_path")" ]; then
        log_warn "$project_name v$version already exists, skipping build"
        return 0
    fi
    
    # Update site_url in mkdocs.yaml for local testing
    local temp_config="$project_dir/mkdocs.local.yaml"
    local site_url="http://localhost:$PORT/$project_name/$version/"
    
    # Create temporary config with updated site_url
    sed "s|site_url:.*|site_url: $site_url|g" "$project_dir/mkdocs.yaml" > "$temp_config"
    
    # Build from repo root so root's poetry (with mkdocs) is used.
    # Suppress SyntaxWarning from mkdocs-include-dir-to-nav (invalid escape sequence in its code).
    (
        cd "$REPO_ROOT"
        PYTHONWARNINGS=ignore::SyntaxWarning poetry run mkdocs build -f "$temp_config" -d "$output_path" --clean
    )
    
    # Cleanup temp config
    rm -f "$temp_config"
    
    log_success "$project_name v$version built"
}

# ============================================================================
# Main Script
# ============================================================================

main() {
    log_info "Starting versioned documentation build..."
    log_info "Repository root: $REPO_ROOT"
    log_info "Output directory: $OUTPUT_DIR"
    echo ""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean)
                CLEAN=true
                shift
                ;;
            --serve)
                SERVE=true
                shift
                ;;
            --sdk-version)
                SDK_VERSION="$2"
                shift 2
                ;;
            --toolkit-version)
                TOOLKIT_VERSION="$2"
                shift 2
                ;;
            --port)
                PORT="$2"
                shift 2
                ;;
            --help|-h)
                show_help
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Clean if requested
    if [ "$CLEAN" = true ]; then
        log_info "Cleaning output directory..."
        rm -rf "$OUTPUT_DIR"
        log_success "Cleaned"
    fi
    
    # Check dependencies
    check_dependencies
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    
    # Get versions from pyproject.toml if not provided
    if [ -z "$SDK_VERSION" ]; then
        SDK_VERSION=$(get_version_from_pyproject "$REPO_ROOT/unique_sdk")
        log_info "Detected SDK version: $SDK_VERSION"
    else
        log_info "Using custom SDK version: $SDK_VERSION"
    fi
    
    if [ -z "$TOOLKIT_VERSION" ]; then
        TOOLKIT_VERSION=$(get_version_from_pyproject "$REPO_ROOT/unique_toolkit")
        log_info "Detected Toolkit version: $TOOLKIT_VERSION"
    else
        log_info "Using custom Toolkit version: $TOOLKIT_VERSION"
    fi
    
    echo ""
    
    # Build root site
    build_root_site
    
    # Build SDK
    build_project_site "unique-sdk" "$REPO_ROOT/unique_sdk" "$SDK_VERSION"
    
    # Build Toolkit
    build_project_site "unique-toolkit" "$REPO_ROOT/unique_toolkit" "$TOOLKIT_VERSION"
    
    echo ""
    
    # Generate versions.json files
    generate_versions_json "$OUTPUT_DIR/unique-sdk" "$SDK_VERSION" "$OUTPUT_DIR/unique-sdk/versions.json"
    generate_versions_json "$OUTPUT_DIR/unique-toolkit" "$TOOLKIT_VERSION" "$OUTPUT_DIR/unique-toolkit/versions.json"
    
    # Copy current version into latest/ so .../latest/ and .../latest/any/subpath/ both work
    log_info "Creating latest/ copies..."
    copy_version_to_latest "$OUTPUT_DIR/unique-sdk" "$SDK_VERSION"
    copy_version_to_latest "$OUTPUT_DIR/unique-toolkit" "$TOOLKIT_VERSION"
    # Base-path redirects: /unique-sdk/ and /unique-toolkit/ -> .../latest/
    create_base_redirect "$OUTPUT_DIR/unique-sdk"
    create_base_redirect "$OUTPUT_DIR/unique-toolkit"
    log_success "Latest copies and redirects created"
    
    echo ""
    log_success "Build complete!"
    echo ""
    echo "Structure:"
    echo "  $OUTPUT_DIR/"
    echo "  ├── index.html                        (root site)"
    echo "  ├── unique-sdk/"
    echo "  │   ├── versions.json"
    echo "  │   ├── latest/                       -> $SDK_VERSION"
    echo "  │   └── $SDK_VERSION/"
    echo "  └── unique-toolkit/"
    echo "      ├── versions.json"
    echo "      ├── latest/                       -> $TOOLKIT_VERSION"
    echo "      └── $TOOLKIT_VERSION/"
    echo ""
    
    # Serve if requested
    if [ "$SERVE" = true ]; then
        log_info "Starting local server on port $PORT..."
        echo ""
        echo "================================================================"
        echo "  Documentation Server Running"
        echo "================================================================"
        echo ""
        echo "  Root:    http://localhost:$PORT/"
        echo "  SDK:     http://localhost:$PORT/unique-sdk/latest/"
        echo "  Toolkit: http://localhost:$PORT/unique-toolkit/latest/"
        echo ""
        echo "  Press Ctrl+C to stop"
        echo ""
        echo "================================================================"
        echo ""
        
        cd "$OUTPUT_DIR"
        poetry run python -m http.server "$PORT"
    else
        log_info "To serve locally, run:"
        echo "  cd $OUTPUT_DIR && python -m http.server $PORT"
        echo ""
        echo "  Then visit:"
        echo "    http://localhost:$PORT/"
        echo "    http://localhost:$PORT/unique-sdk/latest/"
        echo "    http://localhost:$PORT/unique-toolkit/latest/"
    fi
}

# Run main function
main "$@"
