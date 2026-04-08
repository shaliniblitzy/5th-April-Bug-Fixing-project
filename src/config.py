"""
Blitzy Platform API Test Suite — Configuration Management.

Provides centralized configuration loading for API base URL, authentication
token, project ID, and request timeout from environment variables or .env files.
Supports multiple environments (development, staging, production) by changing
environment variables only — no code changes required.

Environment Variables:
    API_BASE_URL: Base URL of the Blitzy Platform API (required).
        Example: https://api.blitzy.com
    API_AUTH_TOKEN: Bearer token for authenticating API requests (required).
    PROJECT_ID: Default project identifier for test targeting (required).
    REQUEST_TIMEOUT: HTTP request timeout in seconds (optional, default: 30).

Usage:
    from src.config import Settings, get_settings

    # Create and validate settings
    settings = get_settings()
    settings.validate()

    # Access configuration values
    print(settings.api_base_url)
    print(settings.request_timeout)
"""

import os
from typing import Optional

from dotenv import load_dotenv


class Settings:
    """
    Configuration settings for the Blitzy Platform API test suite.

    Loads configuration from environment variables or .env files using
    python-dotenv. All required fields must be set via environment variables
    or a .env file before calling validate().

    Attributes:
        api_base_url: Base URL of the Blitzy Platform API. Trailing slashes
            are automatically stripped for URL consistency.
        api_auth_token: Bearer token for authenticating API requests.
        project_id: Default project identifier for test targeting.
        request_timeout: HTTP request timeout in seconds. Defaults to 30
            if not specified or if the provided value is not a valid integer.
    """

    def __init__(self) -> None:
        """
        Initialize settings by loading environment variables.

        Calls load_dotenv() to populate os.environ from a .env file
        (if present in the current working directory or any parent directory),
        then reads each configuration value from environment variables
        using os.getenv(). Default values are applied where specified.
        """
        # Load .env file to populate environment variables before reading them.
        # load_dotenv() is idempotent and will not override existing env vars
        # unless explicitly configured to do so.
        load_dotenv()

        # Read API base URL from environment (required, no default).
        # Strip trailing slashes for URL consistency so that endpoint paths
        # can be appended without worrying about double slashes.
        api_base_url_raw: Optional[str] = os.getenv("API_BASE_URL")
        if api_base_url_raw is not None:
            self.api_base_url: Optional[str] = api_base_url_raw.rstrip("/")
        else:
            self.api_base_url = None

        # Read API authentication token from environment (required, no default).
        self.api_auth_token: Optional[str] = os.getenv("API_AUTH_TOKEN")

        # Read default project ID from environment (required, no default).
        self.project_id: Optional[str] = os.getenv("PROJECT_ID")

        # Read request timeout from environment with a default fallback of 30
        # seconds. Gracefully handles non-integer values by falling back to the
        # default rather than raising an exception during initialization.
        timeout_raw: Optional[str] = os.getenv("REQUEST_TIMEOUT")
        if timeout_raw is not None:
            try:
                self.request_timeout: int = int(timeout_raw)
            except (ValueError, TypeError):
                # Fall back to default if the provided value cannot be parsed
                # as an integer (e.g., "abc", "30.5", empty string).
                self.request_timeout = 30
        else:
            self.request_timeout = 30

    def validate(self) -> None:
        """
        Validate that all required configuration fields are present and valid.

        This method should be called after initialization to ensure the
        configuration is complete before making API requests. Each validation
        check provides a clear, actionable error message indicating which
        environment variable needs to be set.

        Raises:
            ValueError: If any required field is missing or invalid:
                - API_BASE_URL is empty or None
                - API_AUTH_TOKEN is empty or None
                - PROJECT_ID is empty or None
                - REQUEST_TIMEOUT is not a positive integer
        """
        if not self.api_base_url:
            raise ValueError("API_BASE_URL environment variable is required")

        if not self.api_auth_token:
            raise ValueError("API_AUTH_TOKEN environment variable is required")

        if not self.project_id:
            raise ValueError("PROJECT_ID environment variable is required")

        if not isinstance(self.request_timeout, int) or self.request_timeout <= 0:
            raise ValueError("REQUEST_TIMEOUT must be a positive integer")

    def __repr__(self) -> str:
        """
        Return a string representation of the settings for debugging.

        The api_auth_token value is masked with asterisks for security
        to prevent accidental exposure of credentials in log output.
        """
        token_display = "'***'" if self.api_auth_token else "None"
        return (
            f"Settings("
            f"api_base_url={self.api_base_url!r}, "
            f"api_auth_token={token_display}, "
            f"project_id={self.project_id!r}, "
            f"request_timeout={self.request_timeout!r})"
        )


def get_settings() -> Settings:
    """
    Factory function that creates and returns a new Settings instance.

    Each call creates a fresh instance, which re-reads environment variables
    from the current os.environ state. This design allows:
    - Re-reading env vars that may have changed between calls
    - Isolated settings instances in test scenarios
    - Switching environments by updating env vars and calling again

    Returns:
        Settings: A new Settings instance populated with current environment
            variable values.

    Usage:
        settings = get_settings()
        settings.validate()
        print(settings.api_base_url)
    """
    return Settings()
