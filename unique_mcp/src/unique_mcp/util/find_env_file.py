import os
from pathlib import Path

from platformdirs import user_config_dir


class EnvFileNotFoundError(FileNotFoundError):
    """Raised when no environment file can be found in any of the expected locations."""


def find_env_file(
    filename: str = ".env",
    *,
    app_name: str = "unique",
    app_author: str = "unique",
    required: bool = True,
) -> Path | None:
    """Find environment file using cross-platform fallback locations.

    Search order:
    1. ENVIRONMENT_FILE_PATH environment variable
    2. Current working directory
    3. User config directory (cross-platform via platformdirs)

    Args:
        filename: Name of the environment file (default: '.env')
        app_name: Application name for user config directory (default: 'unique')
        app_author: Application author for user config directory (default: 'unique')
        required: If True, raise EnvFileNotFoundError when file is not found.
                  If False, return None when file is not found (default: True).

    Returns:
        Path to the environment file, or None if not found and required=False.

    Raises:
        EnvFileNotFoundError: If no environment file is found and required=True.
    """
    locations = [
        # 1. Explicit environment variable
        Path(env_path)
        if (env_path := os.environ.get("ENVIRONMENT_FILE_PATH"))
        else None,
        # 2. Current working directory
        Path.cwd() / filename,
        # 3. User config directory (cross-platform)
        Path(user_config_dir(appname=app_name, appauthor=app_author)) / filename,
    ]

    for location in locations:
        if location and location.exists() and location.is_file():
            return location

    # If no file found, either return None or raise error
    if not required:
        return None

    # If required, provide helpful error message
    searched_locations = [str(loc) for loc in locations if loc is not None]
    raise EnvFileNotFoundError(
        f"Environment file '{filename}' not found. Searched locations:\n"
        + "\n".join(f"  - {loc}" for loc in searched_locations)
        + "\n\nTo fix this:\n"
        + f"  1. Create {filename} in one of the above locations, or\n"
        + f"  2. Set ENVIRONMENT_FILE_PATH environment variable to point to your {filename} file"
    )
