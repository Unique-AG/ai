import os
from pathlib import Path

from platformdirs import user_config_dir


class EnvFileNotFoundError(FileNotFoundError):
    """Raised when no environment file can be found in any of the expected locations."""


def find_env_file(*, filename: str = "unique.env") -> Path:
    """Find environment file using cross-platform fallback locations.

    Search order:
    1. UNIQUE_ENV_FILE environment variable
    2. Current working directory
    3. User config directory (cross-platform via platformdirs)

    Args:
        filename: Name of the environment file (default: 'unique.env')

    Returns:
        Path to the environment file.

    Raises:
        EnvFileNotFoundError: If no environment file is found in any location.
    """
    locations = [
        # 1. Explicit environment variable
        Path(env_path) if (env_path := os.environ.get("UNIQUE_ENV_FILE")) else None,
        # 2. Current working directory
        Path.cwd() / filename,
        # 3. User config directory (cross-platform)
        Path(user_config_dir("unique", "unique-toolkit")) / filename,
    ]

    for location in locations:
        if location and location.exists() and location.is_file():
            return location

    # If no file found, provide helpful error message
    searched_locations = [str(loc) for loc in locations if loc is not None]
    raise EnvFileNotFoundError(
        f"Environment file '{filename}' not found. Searched locations:\n"
        + "\n".join(f"  - {loc}" for loc in searched_locations)
        + "\n\nTo fix this:\n"
        + f"  1. Create {filename} in one of the above locations, or\n"
        + f"  2. Set UNIQUE_ENV_FILE environment variable to point to your {filename} file"
    )
