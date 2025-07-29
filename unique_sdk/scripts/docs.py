"""Documentation generation scripts for the Unique SDK."""

import shutil
import subprocess
from pathlib import Path


def build_docs() -> None:
    """Build the documentation using MkDocs."""
    print("Building documentation...")
    try:
        subprocess.run(["mkdocs", "build"], check=True)
        print("Documentation built successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error building documentation: {e}")
        raise


def serve_docs() -> None:
    """Serve the documentation locally for preview."""
    print("Starting documentation server...")
    try:
        subprocess.run(["mkdocs", "serve"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error serving documentation: {e}")
        raise


def clean_docs() -> None:
    """Clean the documentation build directory."""
    site_dir = Path("site")
    if site_dir.exists():
        print("Cleaning documentation build directory...")
        shutil.rmtree(site_dir)
        print("Documentation build directory cleaned successfully!")
    else:
        print("No documentation build directory found.")
