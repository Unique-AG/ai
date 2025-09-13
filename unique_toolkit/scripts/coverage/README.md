# Coverage Scripts

Scripts for generating and analyzing code coverage reports.

## Scripts

### `generate_coverage.sh`
Basic coverage report generation:
- Runs pytest with coverage
- Generates HTML report and terminal output
- Creates simple markdown summary

### `generate_coverage_focused.sh`
Advanced coverage analysis:
- Uses coverage.py's advanced features
- Includes untested files with 0% coverage
- Generates detailed focus folder analysis
- Creates comprehensive reports for documentation

### `analyze_coverage.py`
Python script for detailed coverage analysis:
- Analyzes coverage data for hardcoded focus folders
- Compares coverage against defined goals
- Generates markdown reports with insights
- Called by `generate_coverage_focused.sh`

## Usage

Run from the project root directory:

```bash
# Basic coverage
./scripts/coverage/generate_coverage.sh [OPTIONS]

# Advanced analysis (recommended)
./scripts/coverage/generate_coverage_focused.sh [OPTIONS]
```

### Basic Coverage Options

```bash
./scripts/coverage/generate_coverage.sh -h              # Show help
./scripts/coverage/generate_coverage.sh -v              # Verbose output
./scripts/coverage/generate_coverage.sh -o              # Open report in browser
./scripts/coverage/generate_coverage.sh -d /tmp/cov     # Custom output directory
```

### Advanced Coverage Options

```bash
./scripts/coverage/generate_coverage_focused.sh -h      # Show help
./scripts/coverage/generate_coverage_focused.sh -v -o   # Verbose + open browser
./scripts/coverage/generate_coverage_focused.sh -s      # Skip tests (use existing data)
./scripts/coverage/generate_coverage_focused.sh --keep-temp  # Keep temporary files
```

### Python Analysis Options

```bash
python scripts/coverage/analyze_coverage.py -h          # Show help
python scripts/coverage/analyze_coverage.py --verbose   # Verbose output
python scripts/coverage/analyze_coverage.py --quiet     # Suppress output
python scripts/coverage/analyze_coverage.py --output-dir /tmp/cov  # Custom output

# Custom focus folders
python scripts/coverage/analyze_coverage.py --focus-folders "unique_toolkit/chat,unique_toolkit/content"

# Single coverage goal for all folders
python scripts/coverage/analyze_coverage.py --coverage-goals 80

# Custom goals per folder (JSON format)
python scripts/coverage/analyze_coverage.py --coverage-goals '{"unique_toolkit/chat": 90, "unique_toolkit/content": 85}'
```

## Output

Coverage reports are generated in:
- `docs/coverage/htmlcov/` - Interactive HTML reports
- `docs/coverage/focus_analysis.md` - Focus folder analysis
- `docs/coverage/complete_summary.md` - Complete coverage summary
- `docs/coverage/summary.md` - Basic summary (from basic script)
- `docs/coverage/coverage_history.csv` - Historical coverage data (tracked in git)

## CSV Tracking

The advanced script automatically saves coverage data to `coverage_history.csv` for tracking progress over time. This file includes:
- Timestamp of each run
- Overall coverage percentage
- Goals met count
- Individual folder coverage percentages
- File counts (tested/total/untested)

This CSV file is tracked in git to maintain historical coverage data across commits.

## Customization

### Focus Folders
By default, the script analyzes a predefined set of folders. You can customize this using `--focus-folders`:
- Comma-separated list of folder paths
- Useful for analyzing specific modules or components
- Example: `--focus-folders "unique_toolkit/chat,unique_toolkit/content"`

### Coverage Goals
Coverage goals determine what percentage is considered "passing" for each folder:

1. **Default goals**: Built-in goals based on folder importance
2. **Single goal**: Apply the same goal to all folders (e.g., `--coverage-goals 80`)
3. **Custom goals**: JSON dictionary with folder-specific goals (e.g., `--coverage-goals '{"unique_toolkit/chat": 90}'`)

Goals help identify which modules need attention and track progress toward coverage targets.
