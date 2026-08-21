from dataclasses import dataclass


@dataclass
class IntegrationTestConfig:
    """Configuration for integration tests loaded from environment variables."""

    api_key: str
    app_id: str
    user_id: str
    company_id: str
    base_url: str
    root_scope_id: str
    root_folder_path: str

    @classmethod
    def from_env(cls, env_vars: dict[str, str | None]) -> "IntegrationTestConfig":
        """
        Create IntegrationTestConfig from environment variables dictionary.

        Args:
            env_vars: Dictionary of environment variables (from dotenv_values or os.environ)

        Returns:
            IntegrationTestConfig instance

        Raises:
            ValueError: If required environment variables are missing
        """
        api_key = env_vars["UNIQUE_TEST_API_KEY"]
        app_id = env_vars["UNIQUE_TEST_APP_ID"]
        user_id = env_vars["UNIQUE_TEST_USER_ID"]
        company_id = env_vars["UNIQUE_TEST_COMPANY_ID"]
        base_url = env_vars["UNIQUE_TEST_BASE_URL"]
        root_scope_id = env_vars["UNIQUE_TEST_ROOT_SCOPE_ID"]
        root_folder_path = env_vars["UNIQUE_TEST_ROOT_FOLDER_PATH"]

        if not api_key:
            raise ValueError("UNIQUE_TEST_API_KEY is required")
        if not app_id:
            raise ValueError("UNIQUE_TEST_APP_ID is required")
        if not user_id:
            raise ValueError("UNIQUE_TEST_USER_ID is required")
        if not company_id:
            raise ValueError("UNIQUE_TEST_COMPANY_ID is required")
        if not base_url:
            raise ValueError("UNIQUE_TEST_BASE_URL is required")
        if not root_scope_id:
            raise ValueError("UNIQUE_TEST_ROOT_SCOPE_ID is required")
        if not root_folder_path:
            raise ValueError("UNIQUE_TEST_ROOT_FOLDER_PATH is required")

        return cls(
            api_key=api_key,
            app_id=app_id,
            user_id=user_id,
            company_id=company_id,
            base_url=base_url,
            root_scope_id=root_scope_id,
            root_folder_path=root_folder_path,
        )
