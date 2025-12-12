import os
from pathlib import Path

from platformdirs import user_config_dir


class EnvFileNotFoundError(FileNotFoundError):
    """Raised when no environment file can be found in any of the expected locations."""


def find_env_file(
    filenames: list[str] | None = None,
    *,
    app_name: str = "unique",
    app_author: str = "unique",
    required: bool = True,
) -> Path | None:
    """Find environment files using cross-platform fallback locations.

    Search order for each filename:
    1. ENVIRONMENT_FILE_PATH environment variable
    2. Current working directory
    3. User config directory (cross-platform via platformdirs)

    If filenames is None, the default filename '.env' is used.
    If filenames is provided, the filenames are searched in the order they are provided
    in the list.

    Args:
        filenames: List of names of the environment files (default: None)
        app_name: Application name for user config directory (default: 'unique')
        app_author: Application author for user config directory (default: 'unique')
        required: If True, raise EnvFileNotFoundError when file is not found.
                  If False, return None when file is not found (default: True).

    Returns:
        Path to the environment file, or None if not found and required=False.

    Raises:
        EnvFileNotFoundError: If no environment file is found and required=True.
    """
    if filenames is None:
        filenames = [".env"]

    locations = []
    if env_path := os.environ.get("ENVIRONMENT_FILE_PATH"):
        locations.append(Path(env_path))
    else:
        for filename in filenames:
            locations.append(Path.cwd() / filename)
            locations.append(
                Path(user_config_dir(appname=app_name, appauthor=app_author)) / filename
            )

    for location in locations:
        if location and location.exists() and location.is_file():
            return location

    # If no file found, either return None or raise error
    if not required:
        return None

    # If required, provide helpful error message
    searched_locations = [str(loc) for loc in locations if loc is not None]
    raise EnvFileNotFoundError(
        "\n".join(
            [
                f"Environment file '{filename}' not found. Searched locations:\n"
                + "\n".join(f"  - {loc}" for loc in searched_locations)
                for filename in filenames
            ]
        )
    )
