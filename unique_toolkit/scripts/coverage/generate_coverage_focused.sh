#!/bin/bash

# Generate coverage reports with focus folder analysis
# This script handles test execution and report generation

set -e

# Default values
VERBOSE=false
OPEN_REPORT=false
OUTPUT_DIR="docs/coverage"
SKIP_TESTS=false
CLEAN_TEMP=true

# Function to display help
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Generate advanced code coverage reports with focus folder analysis.

OPTIONS:
    -h, --help          Show this help message
    -v, --verbose       Enable verbose output
    -o, --open          Open HTML report in browser after generation
    -d, --dir DIR       Output directory (default: docs/coverage)
    -s, --skip-tests    Skip running tests (use existing coverage data)
    --keep-temp         Keep temporary files (coverage.json, .coverage)

EXAMPLES:
    $0                          # Full analysis with focus folders
    $0 -v -o                    # Verbose output and open report
    $0 -s                       # Skip tests, analyze existing data
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
        -s|--skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --keep-temp)
            CLEAN_TEMP=false
            shift
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

# Run tests unless skipped
if [[ "$SKIP_TESTS" == false ]]; then
    echo "🧪 Running tests with coverage..."
    log "Using coverage.py with --source=unique_toolkit"
    
    if [[ "$VERBOSE" == true ]]; then
        poetry run coverage run --source=unique_toolkit -m pytest tests/ -v
    else
        poetry run coverage run --source=unique_toolkit -m pytest tests/
    fi
else
    echo "⏭️  Skipping test execution (using existing coverage data)"
    log "Checking for existing .coverage file"
    if [[ ! -f ".coverage" ]]; then
        echo "❌ No existing coverage data found. Run without -s first."
        exit 1
    fi
fi

echo "📊 Generating reports..."
log "Output directory: $OUTPUT_DIR"

# Create coverage directory
mkdir -p "$OUTPUT_DIR"

# Generate HTML and JSON reports
log "Generating HTML report"
poetry run coverage html --directory="$OUTPUT_DIR/htmlcov"

log "Generating JSON data for analysis"
poetry run coverage json -o coverage.json

echo "🎯 Analyzing focus folders..."
log "Running Python analysis script"

if [[ "$VERBOSE" == true ]]; then
    python scripts/coverage/analyze_coverage.py --verbose --output-dir "$OUTPUT_DIR"
else
    python scripts/coverage/analyze_coverage.py --output-dir "$OUTPUT_DIR"
fi

echo "📝 Generating additional reports..."
log "Creating complete coverage summary"

# Generate standard coverage summary with header
{
    echo "# Standard Coverage Report"
    echo ""
    echo "This is the complete coverage report for all files in \`unique_toolkit\`."
    echo ""
    echo "For **focus folder analysis**, see [Focus Analysis](focus_analysis.md)."
    echo ""
    echo "## Complete Coverage Summary"
    echo ""
    poetry run coverage report --format=markdown
} > "$OUTPUT_DIR/complete_summary.md"

echo "✅ Coverage reports generated:"
echo "  - HTML report: $OUTPUT_DIR/htmlcov/index.html"
echo "  - Focus analysis: $OUTPUT_DIR/focus_analysis.md"
echo "  - Complete summary: $OUTPUT_DIR/complete_summary.md"

# Clean up temporary files
if [[ "$CLEAN_TEMP" == true ]]; then
    log "Cleaning up temporary files"
    rm -f coverage.json .coverage
fi

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
