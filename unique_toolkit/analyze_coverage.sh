#!/bin/bash

# Coverage Analysis Script for unique_toolkit
# This script compares test coverage between the base of the current branch and the current state

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/Users/cedric/Projects/unique/ai/unique_toolkit"
COVERAGE_DIR="$PROJECT_ROOT/coverage_analysis"
BASE_COVERAGE_FILE="$COVERAGE_DIR/base_coverage.xml"
CURRENT_COVERAGE_FILE="$COVERAGE_DIR/current_coverage.xml"
BASE_COVERAGE_JSON="$COVERAGE_DIR/base_coverage.json"
CURRENT_COVERAGE_JSON="$COVERAGE_DIR/current_coverage.json"
BASE_COVERAGE_DB="$COVERAGE_DIR/base_coverage.db"
CURRENT_COVERAGE_DB="$COVERAGE_DIR/current_coverage.db"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not in a git repository"
        exit 1
    fi
}

# Function to get the base commit (merge base with main/master)
get_base_commit() {
    # Try to find the base commit with main or master
    local base_commit=""
    
    # Check if main branch exists
    if git show-ref --verify --quiet refs/remotes/origin/main; then
        base_commit=$(git merge-base HEAD origin/main)
    elif git show-ref --verify --quiet refs/remotes/origin/master; then
        base_commit=$(git merge-base HEAD origin/master)
    else
        # Fallback to first commit of current branch
        base_commit=$(git log --oneline --reverse | head -1 | cut -d' ' -f1)
    fi
    
    if [ -z "$base_commit" ]; then
        print_error "Could not determine base commit"
        exit 1
    fi
    
    echo "$base_commit"
}

# Function to run coverage analysis
run_coverage() {
    local commit_hash="$1"
    local output_file="$2"
    local json_output="$3"
    
    print_status "Running coverage analysis for commit: $commit_hash"
    
    # Checkout the specific commit
    git checkout "$commit_hash" > /dev/null 2>&1
    
    # Clean up any existing coverage data
    rm -f .coverage coverage.xml
    
    # Run tests with coverage
    print_status "Running pytest with coverage..."
    if ! poetry run pytest --cov=unique_toolkit --cov-report=xml --cov-report=json --cov-report=term-missing tests/ > /dev/null 2>&1; then
        print_warning "Some tests failed, but continuing with coverage analysis..."
    fi
    
    # Copy coverage files
    if [ -f coverage.xml ]; then
        cp coverage.xml "$output_file"
        print_success "Coverage XML saved to $output_file"
    else
        print_error "Coverage XML file not generated"
        return 1
    fi
    
    if [ -f coverage.json ]; then
        cp coverage.json "$json_output"
        print_success "Coverage JSON saved to $json_output"
    fi
    
    # Copy coverage database file
    if [ -f .coverage ]; then
        cp .coverage "$(dirname "$output_file")/$(basename "$output_file" .xml).db"
        print_success "Coverage database saved"
    fi
    
    return 0
}

# Function to extract coverage percentage from XML
extract_coverage_percentage() {
    local xml_file="$1"
    if [ -f "$xml_file" ]; then
        # Extract line-rate from coverage XML
        python3 -c "
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('$xml_file')
    root = tree.getroot()
    line_rate = float(root.get('line-rate', 0))
    print(f'{line_rate:.2%}')
except Exception as e:
    print('0.00%')
"
    else
        echo "0.00%"
    fi
}

# Function to extract detailed coverage info from JSON
extract_coverage_details() {
    local json_file="$1"
    if [ -f "$json_file" ]; then
        python3 -c "
import json
try:
    with open('$json_file', 'r') as f:
        data = json.load(f)
    
    total_lines = data.get('totals', {}).get('num_statements', 0)
    covered_lines = data.get('totals', {}).get('covered_lines', 0)
    missing_lines = data.get('totals', {}).get('missing_lines', 0)
    excluded_lines = data.get('totals', {}).get('excluded_lines', 0)
    
    print(f'Total lines: {total_lines}')
    print(f'Covered lines: {covered_lines}')
    print(f'Missing lines: {missing_lines}')
    print(f'Excluded lines: {excluded_lines}')
except Exception as e:
    print('Error parsing coverage JSON')
"
    else
        echo "Coverage JSON not available"
    fi
}

# Function to compare coverage between base and current
compare_coverage() {
    print_status "Comparing coverage between base and current state..."
    
    local base_percentage=$(extract_coverage_percentage "$BASE_COVERAGE_FILE")
    local current_percentage=$(extract_coverage_percentage "$CURRENT_COVERAGE_FILE")
    
    echo ""
    echo "=========================================="
    echo "           COVERAGE COMPARISON"
    echo "=========================================="
    echo ""
    echo "Base commit coverage:    $base_percentage"
    echo "Current coverage:        $current_percentage"
    echo ""
    
    # Calculate difference
    local base_num=$(echo "$base_percentage" | sed 's/%//' | awk '{print $1/100}')
    local current_num=$(echo "$current_percentage" | sed 's/%//' | awk '{print $1/100}')
    local diff=$(python3 -c "print(f'{($current_num - $base_num):.2%}')")
    
    if (( $(echo "$current_num > $base_num" | bc -l) )); then
        print_success "Coverage increased by $diff"
    elif (( $(echo "$current_num < $base_num" | bc -l) )); then
        print_warning "Coverage decreased by $diff"
    else
        print_status "Coverage remained the same"
    fi
    
    echo ""
    echo "=========================================="
    echo "           DETAILED ANALYSIS"
    echo "=========================================="
    echo ""
    
    echo "Base commit details:"
    extract_coverage_details "$BASE_COVERAGE_JSON"
    echo ""
    
    echo "Current commit details:"
    extract_coverage_details "$CURRENT_COVERAGE_JSON"
}

# Function to generate HTML report comparison
generate_html_report() {
    print_status "Generating coverage reports..."
    
    # Generate report for base
    if [ -f "$BASE_COVERAGE_DB" ]; then
        poetry run coverage report --data-file="$BASE_COVERAGE_DB" --show-missing > "$COVERAGE_DIR/base_coverage_report.txt"
        print_success "Base coverage report saved to $COVERAGE_DIR/base_coverage_report.txt"
    fi
    
    # Generate report for current
    if [ -f "$CURRENT_COVERAGE_DB" ]; then
        poetry run coverage report --data-file="$CURRENT_COVERAGE_DB" --show-missing > "$COVERAGE_DIR/current_coverage_report.txt"
        print_success "Current coverage report saved to $COVERAGE_DIR/current_coverage_report.txt"
    fi
}

# Function to show files with coverage changes
show_coverage_changes() {
    print_status "Analyzing files with coverage changes..."
    
    if [ -f "$BASE_COVERAGE_JSON" ] && [ -f "$CURRENT_COVERAGE_JSON" ]; then
        python3 -c "
import json
import sys

def get_file_coverage(data, filename):
    files = data.get('files', {})
    if filename in files:
        file_data = files[filename]
        total = file_data.get('summary', {}).get('num_statements', 0)
        covered = file_data.get('summary', {}).get('covered_lines', 0)
        return (total, covered)
    return (0, 0)

try:
    with open('$BASE_COVERAGE_JSON', 'r') as f:
        base_data = json.load(f)
    
    with open('$CURRENT_COVERAGE_JSON', 'r') as f:
        current_data = json.load(f)
    
    print('Files with coverage changes:')
    print('-' * 50)
    
    all_files = set(base_data.get('files', {}).keys()) | set(current_data.get('files', {}).keys())
    
    for filename in sorted(all_files):
        base_total, base_covered = get_file_coverage(base_data, filename)
        current_total, current_covered = get_file_coverage(current_data, filename)
        
        if base_total > 0:
            base_pct = (base_covered / base_total) * 100
        else:
            base_pct = 0
            
        if current_total > 0:
            current_pct = (current_covered / current_total) * 100
        else:
            current_pct = 0
        
        diff = current_pct - base_pct
        
        if abs(diff) > 0.1:  # Only show files with significant changes
            status = '+' if diff > 0 else '-'
            print(f'{status} {filename}: {base_pct:.1f}% -> {current_pct:.1f}% ({diff:+.1f}%)')

except Exception as e:
    print(f'Error analyzing coverage changes: {e}')
"
    fi
}

# Main execution
main() {
    print_status "Starting coverage analysis..."
    
    # Check prerequisites
    check_git_repo
    
    # Create coverage analysis directory
    mkdir -p "$COVERAGE_DIR"
    
    # Get current branch and commit info
    local current_branch=$(git branch --show-current)
    local current_commit=$(git rev-parse HEAD)
    local base_commit=$(get_base_commit)
    
    print_status "Current branch: $current_branch"
    print_status "Current commit: $current_commit"
    print_status "Base commit: $base_commit"
    
    # Store current state
    local original_commit="$current_commit"
    local original_branch="$current_branch"
    
    # Function to restore original state
    restore_original_state() {
        print_status "Restoring original state..."
        git checkout "$original_branch" > /dev/null 2>&1
        print_success "Returned to branch: $original_branch"
    }
    
    # Set up trap to ensure we return to original state on exit
    trap restore_original_state EXIT
    
    # Run coverage analysis for base commit
    print_status "Analyzing base commit coverage..."
    if ! run_coverage "$base_commit" "$BASE_COVERAGE_FILE" "$BASE_COVERAGE_JSON"; then
        print_error "Failed to analyze base commit coverage"
        restore_original_state
        exit 1
    fi
    
    # Return to current commit
    git checkout "$original_commit" > /dev/null 2>&1
    
    # Run coverage analysis for current commit
    print_status "Analyzing current commit coverage..."
    if ! run_coverage "$current_commit" "$CURRENT_COVERAGE_FILE" "$CURRENT_COVERAGE_JSON"; then
        print_error "Failed to analyze current commit coverage"
        restore_original_state
        exit 1
    fi
    
    # Compare coverage
    compare_coverage
    
    # Show files with coverage changes
    show_coverage_changes
    
    # Generate HTML reports
    generate_html_report
    
    print_success "Coverage analysis complete!"
    print_status "Results saved in: $COVERAGE_DIR"
    print_status "Coverage reports available in: $COVERAGE_DIR/base_coverage_report.txt and $COVERAGE_DIR/current_coverage_report.txt"
    
    # Explicitly return to original state
    restore_original_state
}

# Run main function
main "$@"
