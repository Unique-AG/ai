"""CLI for config checker (export and check commands)."""

import json
import logging
import sys
from pathlib import Path

import click

from unique_toolkit._common.config_checker.exporter import ConfigExporter
from unique_toolkit._common.config_checker.registry import ConfigRegistry
from unique_toolkit._common.config_checker.validator import ConfigValidator

logger = logging.getLogger(__name__)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@click.group()
def cli():
    """Config compatibility checker CLI."""
    pass


@cli.command()
@click.option(
    "--package",
    type=click.Path(exists=True),
    default=".",
    help="Path to the package to export configs from (default: current directory)",
)
@click.option(
    "--output",
    type=click.Path(),
    required=True,
    help="Directory to write JSON artifacts",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def export(package: str, output: str, verbose: bool):
    """Export default configurations to JSON artifacts.

    This command should be run at the BASE commit (before changes).
    It discovers all registered configs and exports their defaults to JSON.
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    package_path = Path(package)
    output_dir = Path(output)

    click.echo(f"📦 Exporting configs from: {package_path}")
    click.echo(f"📁 Output directory: {output_dir}")

    try:
        # Discover configs
        registry = ConfigRegistry()
        config_entries = registry.discover_configs(package_path)

        if not config_entries:
            click.echo("⚠️  No configs discovered!")
            sys.exit(1)

        click.echo(f"✓ Discovered {len(config_entries)} config(s)")
        for entry in config_entries:
            click.echo(f"  - {entry.name} ({entry.source})")

        # Export
        exporter = ConfigExporter()
        manifest = exporter.export_all(config_entries, output_dir)

        click.echo("\n✓ Export complete!")
        click.echo(f"  - {manifest.exported_count} exported")
        if manifest.skipped_count > 0:
            click.echo(f"  - {manifest.skipped_count} skipped")

        # Show warnings
        if manifest.warnings:
            click.echo(f"\n⚠️  {len(manifest.warnings)} warning(s):")
            for warning in manifest.warnings:
                click.echo(f"  - {warning.message}")

        sys.exit(0)

    except Exception as e:
        click.echo(f"❌ Export failed: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option(
    "--artifacts",
    type=click.Path(exists=True),
    required=True,
    help="Directory containing exported JSON artifacts from base commit",
)
@click.option(
    "--package",
    type=click.Path(exists=True),
    default=".",
    help="Path to the package to validate configs in (default: current directory)",
)
@click.option(
    "--report-defaults",
    is_flag=True,
    help="Report default value changes (non-breaking)",
)
@click.option(
    "--fail-on-missing",
    is_flag=True,
    help="Fail if a config exists in artifacts but not in package",
)
@click.option(
    "--output-report",
    type=click.Path(),
    default=None,
    help="Path to write markdown report (optional)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def check(
    artifacts: str,
    package: str,
    report_defaults: bool,
    fail_on_missing: bool,
    output_report: str | None,
    verbose: bool,
):
    """Validate configs against schema at current commit (tip).

    This command should be run at the TIP commit (after changes).
    It loads JSON artifacts from base commit and validates them against current schemas.
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    artifacts_dir = Path(artifacts)
    package_path = Path(package)

    click.echo(f"🔍 Validating configs from: {package_path}")
    click.echo(f"📁 Artifact directory: {artifacts_dir}")

    try:
        # Discover current configs
        registry = ConfigRegistry()
        config_entries = registry.discover_configs(package_path)

        click.echo(f"✓ Discovered {len(config_entries)} config(s) at tip")

        # Validate
        validator = ConfigValidator()
        report = validator.validate_all(
            artifacts_dir, config_entries, fail_on_missing=fail_on_missing
        )

        click.echo("\n📊 Validation Results:")
        click.echo(f"  - Total: {report.total_configs}")
        click.echo(f"  - Valid: {report.valid_count}")
        click.echo(f"  - Invalid: {report.invalid_count}")

        # Generate markdown report
        markdown_report = _generate_markdown_report(
            report,
            report_defaults=report_defaults,
            fail_on_missing=fail_on_missing,
        )

        # Write report if path provided
        if output_report:
            report_path = Path(output_report)
            with open(report_path, "w") as f:
                f.write(markdown_report)
            click.echo(f"\n📄 Report written to: {report_path}")

        # Print report summary to stdout
        click.echo("\n" + markdown_report)

        # Exit with appropriate code
        if report.has_failures():
            click.echo("\n❌ Validation FAILED", err=True)
            sys.exit(1)
        else:
            click.echo("\n✓ Validation PASSED")
            sys.exit(0)

    except Exception as e:
        click.echo(f"❌ Check failed: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def _generate_markdown_report(
    report,
    report_defaults: bool = False,
    fail_on_missing: bool = False,
) -> str:
    """Generate a markdown report of validation results."""
    lines = []

    if report.invalid_count > 0:
        lines.append("## ❌ Configuration Breaking Changes Detected\n")
    else:
        lines.append("## ✓ All Configurations Compatible\n")

    # Separate missing configs from other failures
    missing_configs = [
        r
        for r in report.results
        if any("not found at tip" in e.message for e in (r.errors or []))
    ]
    other_failures = [
        r for r in report.results if not r.valid and r not in missing_configs
    ]

    # Schema validation failures
    if other_failures:
        lines.append("### 🔴 Schema Validation Failures\n")
        for result in other_failures:
            lines.append(f"**{result.config_name}**\n")
            if result.errors:
                for error in result.errors:
                    lines.append(f"- `{error.field_path}`: {error.message}\n")
            lines.append("\n")

    # Non-breaking warnings (e.g. removed fields where extra=allow)
    all_warnings = [r for r in report.results if r.warnings]
    if all_warnings:
        lines.append("### 🟡 Configuration Warnings\n")
        for result in all_warnings:
            lines.append(f"**{result.config_name}**\n")
            if result.warnings:
                for warning in result.warnings:
                    lines.append(f"- `{warning.field_path}`: {warning.message}\n")
            lines.append("\n")

    # Missing configs
    if missing_configs:
        status_emoji = "🔴" if fail_on_missing else "🟡"
        status_text = "Failures" if fail_on_missing else "Warnings"
        lines.append(f"### {status_emoji} Missing Configurations ({status_text})\n")
        for result in missing_configs:
            lines.append(f"**{result.config_name}**\n")
            lines.append("- Config class not found at tip (was removed or renamed)\n")
            lines.append("\n")

    # Newly protected configs
    new_configs = [r for r in report.results if r.is_new]
    if new_configs:
        lines.append("### ✨ Newly Protected Configurations\n")
        for result in new_configs:
            lines.append(f"- **{result.config_name}** (First time protected)\n")
        lines.append("\n")

    # Default changes (if requested)
    if report_defaults:
        configs_with_changes = [
            r for r in report.results if r.valid and r.default_changes
        ]
        if configs_with_changes:
            lines.append("### 📊 Default Value Changes (non-breaking)\n")
            for result in configs_with_changes:
                lines.append(f"**{result.config_name}**\n")
                if result.default_changes:
                    for change in result.default_changes:
                        old_val = (
                            json.dumps(change.old_value)
                            if not isinstance(change.old_value, str)
                            else f'"{change.old_value}"'
                        )
                        new_val = (
                            json.dumps(change.new_value)
                            if not isinstance(change.new_value, str)
                            else f'"{change.new_value}"'
                        )
                        lines.append(
                            f"- `{change.field_path}`: {old_val} → {new_val}\n"
                        )
                lines.append("\n")

    # Summary
    lines.append("### Summary\n")
    if report.invalid_count > 0:
        lines.append(f"❌ **{report.invalid_count}** config(s) failed validation.\n")

    if report.valid_count > 0:
        lines.append(f"✅ **{report.valid_count}** config(s) passed validation.\n")

    if not report.results:
        lines.append("No configurations were checked.\n")

    return "".join(lines)


if __name__ == "__main__":
    cli()
