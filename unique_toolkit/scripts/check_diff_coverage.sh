#!/bin/bash
# Local diff coverage checker - mirrors CI behavior
# Run this script to check coverage of your changes before pushing

set -e

# Default values
VERBOSE=false
OPEN_REPORT=false
COMPARE_BRANCH="origin/main"
COVERAGE_THRESHOLD=80
FAIL_ON_INSUFFICIENT=false
SKIP_TESTS=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display help
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Check diff coverage locally - mirrors the CI pipeline behavior.
This script runs tests with coverage and checks only the lines changed 
compared to a base branch using diff-cover.

OPTIONS:
    -h, --help              Show this help message
    -v, --verbose           Enable verbose output
    -o, --open              Open HTML diff coverage report in browser
    -b, --branch BRANCH     Compare branch (default: origin/main)
    -t, --threshold NUM     Coverage threshold percentage (default: 80)
    -f, --fail              Fail on insufficient coverage (default: warn only)
    -s, --skip-tests        Skip running tests (use existing coverage data)

EXAMPLES:
    $0                                  # Basic diff coverage check
    $0 -v -o                           # Verbose output + open report
    $0 -b origin/develop               # Compare against develop branch
    $0 -t 90                           # Require 90% coverage
    $0 -f                              # Fail build on insufficient coverage
    $0 -s                              # Skip tests, use existing coverage.xml

NOTES:
    - Requires poetry and diff-cover to be installed
    - Make sure you've fetched the latest changes from the compare branch
    - The script generates coverage.xml, coverage.json, and HTML reports
    - Use --fail in CI environments, --warn for local development

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
        -b|--branch)
            COMPARE_BRANCH="$2"
            shift 2
            ;;
        -t|--threshold)
            COVERAGE_THRESHOLD="$2"
            shift 2
            ;;
        -f|--fail)
            FAIL_ON_INSUFFICIENT=true
            shift
            ;;
        -s|--skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_status $BLUE "🔍 Diff Coverage Checker"
echo "Compare branch: $COMPARE_BRANCH"
echo "Coverage threshold: $COVERAGE_THRESHOLD%"
echo "Fail on insufficient coverage: $FAIL_ON_INSUFFICIENT"
echo ""

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_status $RED "❌ Error: Not in a git repository"
    exit 1
fi

# Check if poetry is available
if ! command -v poetry &> /dev/null; then
    print_status $RED "❌ Error: Poetry not found. Please install poetry first."
    exit 1
fi

# Check if compare branch exists
if ! git show-ref --verify --quiet "refs/remotes/$COMPARE_BRANCH"; then
    print_status $YELLOW "⚠️  Warning: Branch $COMPARE_BRANCH not found locally."
    print_status $BLUE "Fetching latest changes..."
    git fetch origin
fi

# Run tests with coverage (unless skipped)
if [ "$SKIP_TESTS" = false ]; then
    print_status $BLUE "🧪 Running tests with coverage..."
    if [ "$VERBOSE" = true ]; then
        poetry run pytest --cov=unique_toolkit --cov-report=xml --cov-report=json --cov-report=html --cov-report=term
    else
        poetry run pytest --cov=unique_toolkit --cov-report=xml --cov-report=json --cov-report=html --cov-report=term -q
    fi
    print_status $GREEN "✅ Tests completed"
    
    # Small delay to ensure coverage files are written
    sleep 2
else
    print_status $YELLOW "⏭️  Skipping tests (using existing coverage data)"
    if [ ! -f "coverage.xml" ]; then
        print_status $RED "❌ Error: coverage.xml not found. Run tests first or remove --skip-tests flag."
        exit 1
    fi
fi

echo ""
print_status $BLUE "📊 Checking diff coverage against $COMPARE_BRANCH..."

# Run diff-cover and capture output
DIFF_COVER_OUTPUT=$(mktemp)
DIFF_COVER_EXIT_CODE=0

# Generate HTML report if requested
if [ "$OPEN_REPORT" = true ]; then
    HTML_REPORT="diff_coverage_report.html"
    poetry run diff-cover coverage.xml --compare-branch="$COMPARE_BRANCH" --fail-under="$COVERAGE_THRESHOLD" --html-report="$HTML_REPORT" > "$DIFF_COVER_OUTPUT" 2>&1 || DIFF_COVER_EXIT_CODE=$?
else
    poetry run diff-cover coverage.xml --compare-branch="$COMPARE_BRANCH" --fail-under="$COVERAGE_THRESHOLD" > "$DIFF_COVER_OUTPUT" 2>&1 || DIFF_COVER_EXIT_CODE=$?
fi

# Display diff-cover output
if [ "$VERBOSE" = true ]; then
    cat "$DIFF_COVER_OUTPUT"
else
    # Show summary lines only
    grep -E "(Diff Coverage|TOTAL|ERROR|WARNING)" "$DIFF_COVER_OUTPUT" || cat "$DIFF_COVER_OUTPUT"
fi

echo ""

# Handle results
if [ $DIFF_COVER_EXIT_CODE -eq 0 ]; then
    print_status $GREEN "✅ All new/modified lines have sufficient test coverage!"
    
    if [ "$OPEN_REPORT" = true ] && [ -f "$HTML_REPORT" ]; then
        print_status $BLUE "🌐 Opening coverage report in browser..."
        if command -v open &> /dev/null; then
            open "$HTML_REPORT"
        elif command -v xdg-open &> /dev/null; then
            xdg-open "$HTML_REPORT"
        else
            print_status $YELLOW "⚠️  Cannot open browser automatically. Report saved as: $HTML_REPORT"
        fi
    fi
    
    print_status $GREEN "🎉 Diff coverage check passed!"
    
else
    print_status $YELLOW "⚠️  New or modified lines have insufficient test coverage"
    
    echo ""
    print_status $BLUE "💡 To fix this:"
    echo "   1. Add tests for the new/modified code"
    echo "   2. Run this script again to verify coverage"
    echo "   3. Use -v flag for detailed coverage report"
    
    if [ "$OPEN_REPORT" = true ] && [ -f "$HTML_REPORT" ]; then
        echo "   4. Check the detailed HTML report: $HTML_REPORT"
        if command -v open &> /dev/null; then
            open "$HTML_REPORT"
        elif command -v xdg-open &> /dev/null; then
            xdg-open "$HTML_REPORT"
        fi
    fi
    
    echo ""
    print_status $BLUE "📋 Useful commands:"
    echo "   poetry run diff-cover coverage.xml --compare-branch=$COMPARE_BRANCH"
    echo "   poetry run diff-cover coverage.xml --compare-branch=$COMPARE_BRANCH --html-report=diff_report.html"
    
    if [ "$FAIL_ON_INSUFFICIENT" = true ]; then
        print_status $RED "❌ Diff coverage check failed!"
        rm -f "$DIFF_COVER_OUTPUT"
        exit 1
    else
        print_status $YELLOW "⚠️  Diff coverage check completed with warnings"
    fi
fi

# Cleanup
rm -f "$DIFF_COVER_OUTPUT"

print_status $BLUE "📁 Generated files:"
echo "   - coverage.xml (for diff-cover analysis)"
echo "   - coverage.json (structured data)"
echo "   - htmlcov/ (full coverage report)"
if [ "$OPEN_REPORT" = true ] && [ -f "$HTML_REPORT" ]; then
    echo "   - $HTML_REPORT (diff coverage report)"
fi

echo ""
print_status $GREEN "✨ Diff coverage check completed!"
