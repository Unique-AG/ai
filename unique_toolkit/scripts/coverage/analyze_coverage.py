#!/usr/bin/env python3
"""
Analyze coverage data for hardcoded focus folders.

This script analyzes coverage.json data and generates detailed reports
with focus folder analysis and coverage goals.
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# DEFAULT CONFIGURATION: Define the default folders to focus on
DEFAULT_FOCUS_FOLDERS = [
    "unique_toolkit/chat",
    "unique_toolkit/content",
    "unique_toolkit/language_model",
    "unique_toolkit/embedding",
    "unique_toolkit/short_term_memory",
    "unique_toolkit/app",
    "unique_toolkit/_common",
    "unique_toolkit/tools",
    "unique_toolkit/framework_utilities",
    "unique_toolkit/evals",
    "unique_toolkit/evaluators",
    "unique_toolkit/history_manager",
    "unique_toolkit/reference_manager",
    "unique_toolkit/postprocessor",
    "unique_toolkit/debug_info_manager",
    "unique_toolkit/thinking_manager",
    "unique_toolkit/smart_rules",
]

# DEFAULT COVERAGE GOALS: Can be overridden via command line
DEFAULT_COVERAGE_GOALS = {
    # Core business logic - high coverage expected
    "unique_toolkit/chat": 85,
    "unique_toolkit/content": 85,
    "unique_toolkit/language_model": 90,
    "unique_toolkit/embedding": 80,
    "unique_toolkit/short_term_memory": 80,
    # Infrastructure - moderate coverage expected
    "unique_toolkit/app": 70,
    "unique_toolkit/_common": 75,
    "unique_toolkit/tools": 60,
    "unique_toolkit/framework_utilities": 60,
    "unique_toolkit/evals": 60,
    "unique_toolkit/evaluators": 60,
    "unique_toolkit/history_manager": 60,
    "unique_toolkit/reference_manager": 60,
    "unique_toolkit/postprocessor": 60,
    "unique_toolkit/debug_info_manager": 60,
    "unique_toolkit/thinking_manager": 60,
    "unique_toolkit/smart_rules": 75,
}


def parse_focus_folders(folders_input: str) -> List[str]:
    """Parse focus folders from command line input."""
    if not folders_input:
        return DEFAULT_FOCUS_FOLDERS

    # Split by comma and strip whitespace
    folders = [folder.strip() for folder in folders_input.split(",")]
    return [folder for folder in folders if folder]  # Remove empty strings


def parse_coverage_goals(goals_input: str, focus_folders: List[str]) -> Dict[str, int]:
    """Parse coverage goals from command line input."""
    if not goals_input:
        # Use defaults, but only for folders that exist in focus_folders
        return {
            folder: DEFAULT_COVERAGE_GOALS.get(folder, 70) for folder in focus_folders
        }

    try:
        # Try to parse as a single integer (applies to all folders)
        goal_value = int(goals_input)
        return {folder: goal_value for folder in focus_folders}
    except ValueError:
        # Try to parse as JSON dictionary
        try:
            goals_dict = json.loads(goals_input)
            if not isinstance(goals_dict, dict):
                raise ValueError("Goals must be a dictionary")

            # Apply goals, using default for missing folders
            result = {}
            for folder in focus_folders:
                if folder in goals_dict:
                    result[folder] = int(goals_dict[folder])
                else:
                    result[folder] = DEFAULT_COVERAGE_GOALS.get(folder, 70)
            return result
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(
                f"Invalid goals format. Use a single integer or JSON dict: {e}"
            )


def discover_all_python_files(focus_folders: List[str]) -> Dict[str, List[Path]]:
    """Discover all Python files in focus folders."""
    all_files = {}
    for folder in focus_folders:
        folder_path = Path(folder)
        if folder_path.exists():
            # Find all .py files recursively, excluding test files
            py_files = [
                f
                for f in folder_path.rglob("*.py")
                if not f.name.startswith("test_") and "/tests/" not in str(f)
            ]
            all_files[folder] = py_files
        else:
            all_files[folder] = []
    return all_files


def analyze_coverage_data(
    coverage_file: Path, focus_folders: List[str], coverage_goals: Dict[str, int]
) -> Dict[str, Dict]:
    """Analyze coverage data for focus folders, including all files."""

    if not coverage_file.exists():
        print("❌ Coverage JSON file not found")
        return {}

    with open(coverage_file) as f:
        coverage_data = json.load(f)

    # Discover all Python files in focus folders
    all_files = discover_all_python_files(focus_folders)

    # Initialize stats for focus folders
    folder_stats = {}
    for folder in focus_folders:
        folder_stats[folder] = {
            "total_statements": 0,
            "covered_statements": 0,
            "missing_statements": 0,
            "files": 0,
            "total_files_on_disk": len(all_files.get(folder, [])),
            "untested_files": 0,
            "goal": coverage_goals.get(folder, 70),
        }

    # Track which files we've seen in coverage data
    covered_files = set()

    # Process files from coverage data
    for file_path, file_data in coverage_data["files"].items():
        if not file_path.startswith("unique_toolkit/"):
            continue

        covered_files.add(file_path)

        # Check if this file belongs to any of our focus folders
        matching_folder = None
        for focus_folder in focus_folders:
            if file_path.startswith(focus_folder + "/"):
                matching_folder = focus_folder
                break

        # Only process files in our focus folders
        if matching_folder and matching_folder in folder_stats:
            folder_stats[matching_folder]["total_statements"] += file_data["summary"][
                "num_statements"
            ]
            folder_stats[matching_folder]["covered_statements"] += file_data["summary"][
                "covered_lines"
            ]
            folder_stats[matching_folder]["missing_statements"] += file_data["summary"][
                "missing_lines"
            ]
            folder_stats[matching_folder]["files"] += 1

    # Add untested files (files that exist but aren't in coverage data)
    for folder, files in all_files.items():
        if folder in folder_stats:
            untested_count = 0
            for file_path in files:
                file_str = str(file_path)
                if file_str not in covered_files:
                    untested_count += 1
            folder_stats[folder]["untested_files"] = untested_count

    # Calculate percentages and goal status
    for folder, stats in folder_stats.items():
        total_files = stats["total_files_on_disk"]
        tested_files = stats["files"]

        if stats["total_statements"] > 0:
            stats["coverage_percent"] = (
                stats["covered_statements"] / stats["total_statements"]
            ) * 100
            stats["meets_goal"] = stats["coverage_percent"] >= stats["goal"]
        else:
            stats["coverage_percent"] = 0.0
            stats["meets_goal"] = False

        # Calculate file coverage percentage
        if total_files > 0:
            stats["file_coverage_percent"] = (tested_files / total_files) * 100
        else:
            stats["file_coverage_percent"] = 0.0

    return folder_stats


def generate_markdown_report(
    folder_stats: Dict[str, Dict], focus_folders: List[str]
) -> str:
    """Generate markdown report for focus folders."""

    report = f"""# Coverage Analysis - Focus Folders

Analysis of **{len(focus_folders)} focus folders** with individual coverage goals.

## Focus Folder Coverage

| Status | Folder | Coverage % | Goal % | Tested Files | Total Files | Untested | Statements | Covered | Missing |
|--------|--------|------------|--------|--------------|-------------|----------|------------|---------|---------|
"""

    # Sort by coverage percentage (descending)
    sorted_folders = sorted(
        folder_stats.items(), key=lambda x: x[1]["coverage_percent"], reverse=True
    )

    total_statements = sum(stats["total_statements"] for stats in folder_stats.values())
    total_covered = sum(stats["covered_statements"] for stats in folder_stats.values())
    overall_coverage = (
        (total_covered / total_statements * 100) if total_statements > 0 else 0
    )

    goals_met = 0
    for folder, stats in sorted_folders:
        coverage_pct = stats["coverage_percent"]
        goal_pct = stats["goal"]
        meets_goal = stats["meets_goal"]

        if meets_goal:
            goals_met += 1
            status_emoji = "✅"
        elif coverage_pct >= goal_pct * 0.8:  # Within 80% of goal
            status_emoji = "⚠️"
        else:
            status_emoji = "❌"

        report += f"| {status_emoji} | `{folder}` | {coverage_pct:.1f}% | {goal_pct}% | {stats['files']} | {stats['total_files_on_disk']} | {stats['untested_files']} | {stats['total_statements']} | {stats['covered_statements']} | {stats['missing_statements']} |\n"

    report += f"""
## Summary Statistics

- **Overall Coverage**: {overall_coverage:.1f}%
- **Goals Met**: {goals_met}/{len(folder_stats)} folders ({goals_met / len(folder_stats) * 100:.0f}%)
- **Tested Files**: {sum(stats["files"] for stats in folder_stats.values())}
- **Total Files on Disk**: {sum(stats["total_files_on_disk"] for stats in folder_stats.values())}
- **Untested Files**: {sum(stats["untested_files"] for stats in folder_stats.values())}
- **Total Statements**: {total_statements:,}

## Goal Achievement Breakdown

"""

    # Group by goal achievement
    met_goals = []
    close_to_goals = []
    needs_work = []

    for folder, stats in folder_stats.items():
        coverage_pct = stats["coverage_percent"]
        goal_pct = stats["goal"]

        if stats["meets_goal"]:
            met_goals.append((folder, coverage_pct, goal_pct))
        elif coverage_pct >= goal_pct * 0.8:
            close_to_goals.append((folder, coverage_pct, goal_pct))
        else:
            needs_work.append((folder, coverage_pct, goal_pct))

    if met_goals:
        report += "### ✅ **Meeting Goals**\n"
        for folder, coverage, goal in met_goals:
            report += f"- `{folder}`: {coverage:.1f}% (goal: {goal}%)\n"
        report += "\n"

    if close_to_goals:
        report += "### ⚠️ **Close to Goals** (within 80%)\n"
        for folder, coverage, goal in close_to_goals:
            gap = goal - coverage
            report += (
                f"- `{folder}`: {coverage:.1f}% (goal: {goal}%, gap: {gap:.1f}%)\n"
            )
        report += "\n"

    if needs_work:
        report += "### ❌ **Needs Attention**\n"
        for folder, coverage, goal in needs_work:
            gap = goal - coverage
            report += (
                f"- `{folder}`: {coverage:.1f}% (goal: {goal}%, gap: {gap:.1f}%)\n"
            )

    return report


def save_coverage_csv(folder_stats: Dict[str, Dict], output_dir: Path):
    """Save coverage data as CSV for tracking over time."""

    csv_file = output_dir / "coverage_history.csv"
    timestamp = datetime.now().isoformat()

    # Check if file exists to determine if we need headers
    file_exists = csv_file.exists()

    # Prepare data row
    row_data = {
        "timestamp": timestamp,
        "overall_coverage": 0.0,
        "goals_met": 0,
        "total_folders": len(folder_stats),
        "tested_files": sum(stats["files"] for stats in folder_stats.values()),
        "total_files": sum(
            stats["total_files_on_disk"] for stats in folder_stats.values()
        ),
        "untested_files": sum(
            stats["untested_files"] for stats in folder_stats.values()
        ),
    }

    # Calculate overall coverage
    total_statements = sum(stats["total_statements"] for stats in folder_stats.values())
    total_covered = sum(stats["covered_statements"] for stats in folder_stats.values())
    if total_statements > 0:
        row_data["overall_coverage"] = (total_covered / total_statements) * 100

    # Count goals met
    row_data["goals_met"] = sum(
        1 for stats in folder_stats.values() if stats.get("meets_goal", False)
    )

    # Add individual folder coverage percentages
    for folder, stats in folder_stats.items():
        # Use folder name without unique_toolkit/ prefix for cleaner column names
        folder_key = folder.replace("unique_toolkit/", "").replace("/", "_")
        row_data[f"{folder_key}_coverage"] = stats["coverage_percent"]
        row_data[f"{folder_key}_goal"] = stats["goal"]
        row_data[f"{folder_key}_meets_goal"] = stats.get("meets_goal", False)

    # Write to CSV
    with open(csv_file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row_data.keys())

        # Write header if file is new
        if not file_exists:
            writer.writeheader()

        writer.writerow(row_data)

    return csv_file


def print_console_summary(folder_stats: Dict[str, Dict]):
    """Print a concise summary to console."""

    goals_met = sum(
        1 for stats in folder_stats.values() if stats.get("meets_goal", False)
    )
    total_folders = len(folder_stats)

    print(
        f"📊 Goal Achievement: {goals_met}/{total_folders} folders ({goals_met / total_folders * 100:.0f}%)"
    )

    # Show folders by status
    meeting_goals = []
    needs_attention = []

    for folder, stats in folder_stats.items():
        if stats.get("meets_goal", False):
            meeting_goals.append((folder, stats["coverage_percent"]))
        elif stats["coverage_percent"] < stats["goal"] * 0.8:
            needs_attention.append((folder, stats["coverage_percent"], stats["goal"]))

    if meeting_goals:
        print("\n✅ Meeting Goals:")
        for folder, coverage in meeting_goals:
            print(f"  {coverage:.1f}% - {folder}")

    if needs_attention:
        print("\n❌ Needs Attention:")
        for folder, coverage, goal in needs_attention:
            gap = goal - coverage
            print(f"  {coverage:.1f}% - {folder} (gap: {gap:.1f}%)")

    # Show file coverage summary
    total_files = sum(stats["total_files_on_disk"] for stats in folder_stats.values())
    tested_files = sum(stats["files"] for stats in folder_stats.values())
    untested_files = sum(stats["untested_files"] for stats in folder_stats.values())

    print("\n📁 File Coverage Summary:")
    print(
        f"   Tested Files: {tested_files}/{total_files} ({tested_files / total_files * 100:.1f}%)"
    )
    print(f"   Untested Files: {untested_files} (never imported/executed)")

    # Show folders with most untested files
    high_untested = [
        (folder, stats["untested_files"])
        for folder, stats in folder_stats.items()
        if stats["untested_files"] > 0
    ]
    if high_untested:
        high_untested.sort(key=lambda x: x[1], reverse=True)
        print("\n📋 Folders with untested files:")
        for folder, count in high_untested[:3]:
            print(f"   {count} untested - {folder}")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze coverage data for focus folders with detailed reporting.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Basic analysis with default folders
  %(prog)s --verbose                    # Verbose output
  %(prog)s --output-dir /tmp/coverage   # Custom output directory
  %(prog)s --coverage-file cov.json     # Custom coverage file
  
  # Custom focus folders
  %(prog)s --focus-folders "unique_toolkit/chat,unique_toolkit/content"
  
  # Single coverage goal for all folders
  %(prog)s --coverage-goals 80
  
  # Custom goals per folder (JSON format)
  %(prog)s --coverage-goals '{"unique_toolkit/chat": 90, "unique_toolkit/content": 85}'
        """,
    )

    parser.add_argument(
        "--coverage-file",
        default="coverage.json",
        help="Path to coverage.json file (default: coverage.json)",
    )

    parser.add_argument(
        "--output-dir",
        default="docs/coverage",
        help="Output directory for reports (default: docs/coverage)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress console output (except errors)",
    )

    parser.add_argument(
        "--save-csv",
        action="store_true",
        default=True,
        help="Save coverage data to CSV for tracking over time (default: True)",
    )

    parser.add_argument(
        "--no-csv", action="store_false", dest="save_csv", help="Skip saving CSV data"
    )

    parser.add_argument(
        "--focus-folders",
        help="Comma-separated list of folders to analyze (default: use built-in list)",
    )

    parser.add_argument(
        "--coverage-goals",
        help="Coverage goals: single integer (applies to all) or JSON dict with folder-specific goals",
    )

    return parser.parse_args()


def main():
    """Main analysis function."""
    args = parse_arguments()

    coverage_file = Path(args.coverage_file)
    output_dir = Path(args.output_dir)

    # Parse focus folders and coverage goals
    try:
        focus_folders = parse_focus_folders(args.focus_folders)
        coverage_goals = parse_coverage_goals(args.coverage_goals, focus_folders)
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)

    if not args.quiet:
        print("📊 Analyzing coverage data for focus folders...")
        if args.verbose:
            print(f"🔍 Coverage file: {coverage_file}")
            print(f"🔍 Output directory: {output_dir}")
            print(f"🔍 Focus folders: {len(focus_folders)} folders")
            if args.focus_folders:
                print(f"🔍 Custom folders: {', '.join(focus_folders)}")
            if args.coverage_goals:
                print(f"🔍 Custom goals: {args.coverage_goals}")

    # Check if coverage file exists
    if not coverage_file.exists():
        print(f"❌ Coverage file not found: {coverage_file}")
        print("💡 Run coverage generation first to create coverage.json")
        sys.exit(1)

    folder_stats = analyze_coverage_data(coverage_file, focus_folders, coverage_goals)

    if not folder_stats:
        print("❌ No coverage data found")
        sys.exit(1)

    # Generate markdown report
    if args.verbose:
        print("🔍 Generating markdown report...")

    report = generate_markdown_report(folder_stats, focus_folders)

    # Save report
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / "focus_analysis.md"

    with open(report_file, "w") as f:
        f.write(report)

    # Save CSV data for tracking over time
    csv_file = None
    if args.save_csv:
        if args.verbose:
            print("🔍 Saving coverage data to CSV...")
        csv_file = save_coverage_csv(folder_stats, output_dir)

    if not args.quiet:
        print("✅ Focus folder analysis complete:")
        print(f"  - Report saved: {report_file}")
        if csv_file:
            print(f"  - CSV history: {csv_file}")

        if args.verbose:
            print("🔍 Report contents:")
            # Print console summary
            print_console_summary(folder_stats)
        elif not args.quiet:
            # Brief summary for normal mode
            print_console_summary(folder_stats)


if __name__ == "__main__":
    main()
