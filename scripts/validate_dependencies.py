#!/usr/bin/env python3
"""
Dependency Validation Script

This script validates that the actual package dependencies match the structure
shown in the README Mermaid diagram.
"""

import sys
import tomllib
from enum import StrEnum
from pathlib import Path
from typing import Dict, List, Set


class Package(StrEnum):
    """Enum for all workspace packages."""

    SDK = "unique-sdk"
    TOOLKIT = "unique-toolkit"
    AGENTIC = "unique-agentic"
    ORCHESTRATOR = "unique-orchestrator"
    STOCK_TICKER = "unique-stock-ticker"
    FOLLOW_UP_QUESTIONS = "unique-follow-up-questions"
    WEB_SEARCH = "unique-web-search"
    INTERNAL_SEARCH = "unique-internal-search"
    DEEP_RESEARCH = "unique-deep-research"


class PackageGroup(StrEnum):
    """Enum for package groups that allow internal dependencies."""

    CORE = "core"
    FRAMEWORK = "framework"
    TOOLS = "tools"
    POSTPROCESSORS = "postprocessors"


# Package group definitions - easily extensible
PACKAGE_GROUPS: Dict[PackageGroup, Set[Package]] = {
    PackageGroup.CORE: {
        Package.SDK,
        Package.TOOLKIT,
    },
    PackageGroup.FRAMEWORK: {
        Package.AGENTIC,
        Package.ORCHESTRATOR,
    },
    PackageGroup.TOOLS: {
        Package.WEB_SEARCH,
        Package.INTERNAL_SEARCH,
        Package.DEEP_RESEARCH,
    },
    PackageGroup.POSTPROCESSORS: {
        Package.STOCK_TICKER,
        Package.FOLLOW_UP_QUESTIONS,
    },
}

# Groups that allow internal dependencies
GROUPS_ALLOWING_INTERNAL_DEPS = {
    PackageGroup.TOOLS,
    PackageGroup.POSTPROCESSORS,
}


def get_workspace_root() -> Path:
    """Get the workspace root directory."""
    return Path(__file__).parent.parent


def load_pyproject_toml(path: Path) -> Dict:
    """Load and parse a pyproject.toml file."""
    with open(path, "rb") as f:
        return tomllib.load(f)


def extract_package_name(dep_string: str) -> str:
    """Extract clean package name from dependency string."""
    return dep_string.split(">=")[0].split("==")[0].split("<")[0].strip()


def get_project_name_from_pyproject(pyproject_path: Path) -> str | None:
    """Get project name from pyproject.toml file."""
    try:
        data = load_pyproject_toml(pyproject_path)
        return data.get("project", {}).get("name")
    except Exception:
        return None


def get_package_dependencies(package_path: Path) -> Set[str]:
    """Extract dependencies from a package's pyproject.toml."""
    pyproject_path = package_path / "pyproject.toml"
    if not pyproject_path.exists():
        return set()

    data = load_pyproject_toml(pyproject_path)
    dependencies = set()

    # Get main dependencies
    if "project" in data and "dependencies" in data["project"]:
        for dep in data["project"]["dependencies"]:
            pkg_name = extract_package_name(dep)
            if pkg_name.startswith("unique-"):
                dependencies.add(pkg_name)

    return dependencies


def get_package_paths() -> Dict[Package, Path]:
    """Get the filesystem paths for all packages."""
    workspace_root = get_workspace_root()
    return {
        Package.SDK: workspace_root / "unique_sdk",
        Package.TOOLKIT: workspace_root / "unique_toolkit",
        Package.AGENTIC: workspace_root / "unique_agentic",
        Package.ORCHESTRATOR: workspace_root / "unique_orchestrator",
        Package.STOCK_TICKER: workspace_root / "postprocessors" / "unique_stock_ticker",
        Package.FOLLOW_UP_QUESTIONS: workspace_root
        / "postprocessors"
        / "unique_follow_up_questions",
        Package.WEB_SEARCH: workspace_root / "tool_packages" / "unique_web_search",
        Package.INTERNAL_SEARCH: workspace_root
        / "tool_packages"
        / "unique_internal_search",
        Package.DEEP_RESEARCH: workspace_root
        / "tool_packages"
        / "unique_deep_research",
    }


def convert_string_deps_to_enums(string_deps: Set[str]) -> Set[Package]:
    """Convert string dependencies to Package enums, skipping invalid ones."""
    enum_deps = set()
    for dep in string_deps:
        try:
            enum_deps.add(Package(dep))
        except ValueError:
            # Skip non-workspace dependencies
            pass
    return enum_deps


def get_actual_dependencies() -> Dict[Package, Set[Package]]:
    """Get actual dependencies from all workspace packages."""
    actual_deps = {}
    package_paths = get_package_paths()

    for pkg_enum, pkg_path in package_paths.items():
        if pkg_path.exists():
            raw_deps = get_package_dependencies(pkg_path)
            actual_deps[pkg_enum] = convert_string_deps_to_enums(raw_deps)
        else:
            print(f"⚠️  Package path not found: {pkg_path}")
            actual_deps[pkg_enum] = set()

    return actual_deps


def get_expected_dependencies() -> Dict[Package, Set[Package]]:
    """Define expected dependencies based on the Mermaid diagram."""
    return {
        Package.SDK: set(),  # Base package
        Package.TOOLKIT: {Package.SDK},
        Package.AGENTIC: {Package.SDK, Package.TOOLKIT},
        Package.ORCHESTRATOR: {Package.TOOLKIT, Package.AGENTIC},
        Package.STOCK_TICKER: {Package.SDK, Package.TOOLKIT},
        Package.FOLLOW_UP_QUESTIONS: {Package.SDK, Package.TOOLKIT},
        Package.WEB_SEARCH: {Package.SDK, Package.TOOLKIT},
        Package.INTERNAL_SEARCH: {Package.SDK, Package.TOOLKIT},
        Package.DEEP_RESEARCH: {Package.SDK, Package.TOOLKIT},
    }


def get_package_group(package: Package) -> PackageGroup | None:
    """Get the group that a package belongs to."""
    for group, packages in PACKAGE_GROUPS.items():
        if package in packages:
            return group
    return None


def get_group_packages(group: PackageGroup) -> Set[Package]:
    """Get all packages in a specific group."""
    return PACKAGE_GROUPS.get(group, set())


def get_workspace_scan_directories() -> List[Path]:
    """Get directories to scan for workspace packages."""
    workspace_root = get_workspace_root()
    return [
        workspace_root,  # Root level packages
        workspace_root / "postprocessors",
        workspace_root / "tool_packages",
    ]


def scan_directory_for_packages(directory: Path) -> Set[str]:
    """Scan a directory for packages with pyproject.toml files."""
    found_packages = set()

    if not directory.exists():
        return found_packages

    for item in directory.iterdir():
        if not item.is_dir():
            continue

        pyproject_path = item / "pyproject.toml"
        if not pyproject_path.exists():
            continue

        package_name = get_project_name_from_pyproject(pyproject_path)
        if package_name and package_name.startswith("unique-"):
            found_packages.add(package_name)

    return found_packages


def find_all_workspace_packages() -> Set[str]:
    """Find all packages in the workspace by scanning directories."""
    found_packages = set()
    scan_dirs = get_workspace_scan_directories()

    for directory in scan_dirs:
        found_packages.update(scan_directory_for_packages(directory))

    return found_packages


def validate_package_registration() -> bool:
    """Validate that all workspace packages are registered in the Package enum."""
    print("🔍 Validating package registration...\n")

    found_packages = find_all_workspace_packages()
    registered_packages = {pkg.value for pkg in Package}

    unregistered = found_packages - registered_packages
    orphaned = registered_packages - found_packages

    all_valid = True

    if unregistered:
        all_valid = False
        print("❌ Found unregistered packages:")
        for pkg in sorted(unregistered):
            print(f"   • {pkg}")
        print("   Please add these packages to the Package enum.\n")

    if orphaned:
        print("⚠️  Registered packages not found in workspace:")
        for pkg in sorted(orphaned):
            print(f"   • {pkg}")
        print("   Consider removing these from the Package enum if no longer needed.\n")

    if all_valid and not orphaned:
        print("✅ All workspace packages are properly registered!\n")
    elif all_valid:
        print(
            "✅ All found packages are registered (some registered packages not found).\n"
        )

    return all_valid


def format_package_names(packages: Set[Package]) -> str:
    """Format a set of packages as a sorted list of names."""
    return str(sorted([pkg.value for pkg in packages])) if packages else "None"


def print_dependency_mismatch(
    missing: Set[Package], extra: Set[Package], dep_type: str = ""
):
    """Print missing and extra dependencies in a consistent format."""
    prefix = f"{dep_type} " if dep_type else ""

    if missing:
        missing_names = sorted([dep.value for dep in missing])
        print(f"   ❌ Missing {prefix}dependencies: {missing_names}")
    if extra:
        extra_names = sorted([dep.value for dep in extra])
        print(f"   ⚠️  Extra {prefix}dependencies: {extra_names}")


def validate_package_dependencies(
    package: Package, expected_deps: Set[Package], actual_deps: Set[Package]
) -> bool:
    """Validate dependencies for a single package."""
    print(f"📦 {package.value}:")
    print(f"   Expected: {format_package_names(expected_deps)}")
    print(f"   Actual:   {format_package_names(actual_deps)}")

    package_group = get_package_group(package)

    # Check if this package belongs to a group that allows internal dependencies
    if package_group and package_group in GROUPS_ALLOWING_INTERNAL_DEPS:
        return validate_grouped_package_dependencies(
            package, package_group, expected_deps, actual_deps
        )
    else:
        return validate_exact_package_dependencies(expected_deps, actual_deps)


def validate_grouped_package_dependencies(
    package: Package,
    package_group: PackageGroup,
    expected_deps: Set[Package],
    actual_deps: Set[Package],
) -> bool:
    """Validate dependencies for a package that belongs to a group allowing internal deps."""
    group_packages = get_group_packages(package_group)
    group_deps = actual_deps & group_packages
    base_deps = actual_deps - group_packages

    if base_deps == expected_deps:
        if group_deps:
            group_names = sorted([dep.value for dep in group_deps])
            print(
                f"   ✅ Base dependencies match! (+ {package_group.value} deps: {group_names})"
            )
        else:
            print("   ✅ Dependencies match!")
        return True
    else:
        missing = expected_deps - base_deps
        extra = base_deps - expected_deps

        print_dependency_mismatch(missing, extra, "base")

        if group_deps:
            group_names = sorted([dep.value for dep in group_deps])
            print(
                f"   ℹ️  {package_group.value.title()} dependencies (allowed): {group_names}"
            )
        return False


def validate_exact_package_dependencies(
    expected_deps: Set[Package], actual_deps: Set[Package]
) -> bool:
    """Validate that dependencies match exactly."""
    if actual_deps == expected_deps:
        print("   ✅ Dependencies match!")
        return True
    else:
        missing = expected_deps - actual_deps
        extra = actual_deps - expected_deps
        print_dependency_mismatch(missing, extra)
        return False


def print_validation_summary(all_valid: bool, validation_type: str = "dependencies"):
    """Print validation summary with consistent messaging."""
    allowed_groups = [group.value for group in GROUPS_ALLOWING_INTERNAL_DEPS]
    groups_note = f"ℹ️  Note: {', '.join(allowed_groups)} packages are allowed to depend on each other within their groups."

    if all_valid:
        print(f"🎉 All package {validation_type} match the Mermaid diagram!")
        print(groups_note)
    else:
        print(f"❌ Some package {validation_type} don't match the diagram.")
        print("   Please update either the dependencies or the diagram.")
        print(groups_note)


def validate_dependencies() -> bool:
    """Validate that actual dependencies match expected dependencies."""
    print("🔍 Validating package dependencies against Mermaid diagram...\n")

    actual = get_actual_dependencies()
    expected = get_expected_dependencies()
    all_valid = True

    for package, expected_deps in expected.items():
        actual_deps = actual.get(package, set())
        package_valid = validate_package_dependencies(
            package, expected_deps, actual_deps
        )
        all_valid = all_valid and package_valid
        print()

    print_validation_summary(all_valid)
    return all_valid


def main():
    """Main function."""
    try:
        # First validate package registration
        registration_valid = validate_package_registration()

        # Then validate dependencies
        dependencies_valid = validate_dependencies()

        # Both must pass for overall success
        success = registration_valid and dependencies_valid

        if not success:
            print("\n" + "=" * 60)
            if not registration_valid:
                print("❌ Package registration validation failed!")
            if not dependencies_valid:
                print("❌ Dependency validation failed!")
            print("Please fix the issues above and run again.")

        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error validating dependencies: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
