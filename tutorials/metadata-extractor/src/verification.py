import os

from dotenv import load_dotenv
from quart import current_app as app


def verify_encrypted_env():
    # On AKS, we can not write onto the containers native filesystem
    env_path = os.environ.get("DECRYPTED_ENV_FILE_ABSOLUTE")
    app.logger.info("DECRYPTED_ENV_FILE_ABSOLUTE: %s", env_path)
    if env_path:
        if not os.path.exists(env_path):
            raise FileNotFoundError(f"Environment file not found at path: {env_path}")

        if not os.access(env_path, os.R_OK):
            raise PermissionError(
                f"No read permission for environment file at: {env_path}"
            )

        if os.path.getsize(env_path) == 0:
            raise ValueError(f"Environment file is empty: {env_path}")

        try:
            loaded = load_dotenv(env_path, override=True)
            if not loaded:
                raise EnvironmentError(
                    f"Failed to load environment variables from: {env_path}, file may have invalid format"
                )
        except Exception as e:
            raise EnvironmentError(f"Error loading environment file: {str(e)}")

        app.logger.info(
            f"API Key starts with: -{os.environ.get('API_KEY', '')[:5]}****-"
        )
        app.logger.info(
            f"ENDPOINT Secret starts with: -{os.environ.get('ENDPOINT_SECRET', '')[:5]}****-"
        )
