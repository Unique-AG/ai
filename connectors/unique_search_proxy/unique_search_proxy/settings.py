import os
from pathlib import Path


def get_env_path() -> Path:
    return Path(os.getcwd()) / ".env"
