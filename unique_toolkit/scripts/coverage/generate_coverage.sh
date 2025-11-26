#!/bin/bash
# Simple coverage report generation script
# This is the basic version - for advanced analysis use generate_coverage_focused.sh

set -e

# Default values
VERBOSE=false
OPEN_REPORT=false
OUTPUT_DIR="docs/coverage"

# Function to display help
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Generate basic code coverage reports for the project.

OPTIONS:
    -h, --help      Show this help message
    -v, --verbose   Enable verbose output
    -o, --open      Open HTML report in browser after generation
    -d, --dir DIR   Output directory (default: docs/coverage)

EXAMPLES:
    $0                          # Basic coverage report
    $0 -v                       # Verbose output
    $0 -o                       # Open report in browser
    $0 -d /tmp/coverage         # Custom output directory

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -o|--open)
            OPEN_REPORT=true
            shift
            ;;
        -d|--dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information."
            exit 1
            ;;
    esac
done

# Verbose logging function
log() {
    if [[ "$VERBOSE" == true ]]; then
        echo "🔍 $1"
    fi
}

echo "🧪 Running tests with coverage..."
log "Using pytest with coverage plugin"

if [[ "$VERBOSE" == true ]]; then
    poetry run pytest tests/ --cov=unique_toolkit --cov-report=html --cov-report=term-missing -v
else
    poetry run pytest tests/ --cov=unique_toolkit --cov-report=html --cov-report=term-missing
fi

echo "📊 Generating markdown summary..."
log "Output directory: $OUTPUT_DIR"

# Create coverage directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Generate markdown report
echo "# Coverage Summary" > "$OUTPUT_DIR/summary.md"
echo "" >> "$OUTPUT_DIR/summary.md"
echo "Generated on: $(date)" >> "$OUTPUT_DIR/summary.md"
echo "" >> "$OUTPUT_DIR/summary.md"
poetry run coverage report --format=markdown >> "$OUTPUT_DIR/summary.md"

echo "✅ Coverage reports generated:"
echo "  - HTML report: $OUTPUT_DIR/htmlcov/index.html"
echo "  - Markdown summary: $OUTPUT_DIR/summary.md"

# Open report in browser if requested
if [[ "$OPEN_REPORT" == true ]]; then
    log "Opening HTML report in browser"
    if command -v open >/dev/null 2>&1; then
        open "$OUTPUT_DIR/htmlcov/index.html"
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$OUTPUT_DIR/htmlcov/index.html"
    else
        echo "⚠️  Could not open browser automatically. Please open: $OUTPUT_DIR/htmlcov/index.html"
    fi
fi
