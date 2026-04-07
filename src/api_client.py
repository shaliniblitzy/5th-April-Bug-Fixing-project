"""
Blitzy Platform API Test Suite — HTTP Client Wrapper.

Provides a lightweight HTTP client abstraction encapsulating authenticated
GET requests to the three Blitzy Platform API endpoints used for validating
the ``percent_complete`` field:

- ``GET /runs/metering``          — Metering data for multiple code-generation runs
- ``GET /runs/metering/current``  — Metering data for the currently in-progress run
- ``GET /project``                — Project detail with inline metering information

All methods are strictly read-only (HTTP GET) and include automatic Bearer-token
authentication, configurable timeouts, and structured error propagation via
``httpx.HTTPStatusError`` for non-2xx responses.

Usage::

    from src.api_client import BlitzyAPIClient, create_client

    # Option 1 — Direct instantiation (loads settings from environment)
    client = BlitzyAPIClient()
    data = client.get_runs_metering()
    client.close()

    # Option 2 — Context manager for automatic cleanup
    with BlitzyAPIClient() as client:
        metering = client.get_runs_metering(project_id="my-project")
        current  = client.get_runs_metering_current()
        project  = client.get_project()

    # Option 3 — Factory function
    client = create_client()
"""

import httpx
from typing import Any, Dict, Optional

from src.config import Settings, get_settings


class BlitzyAPIClient:
    """HTTP client wrapper for authenticated GET requests to Blitzy Platform APIs.

    Wraps :class:`httpx.Client` to provide typed, endpoint-specific methods
    for each of the three Blitzy Platform metering/project API endpoints.
    Authentication is handled automatically via the Bearer token supplied
    through :class:`~src.config.Settings`.

    The client supports the context-manager protocol so that connections are
    properly released when the ``with`` block exits.

    Attributes:
        client: The underlying ``httpx.Client`` instance used for HTTP calls.

    Args:
        settings: An optional :class:`~src.config.Settings` instance. When
            ``None`` (the default), :func:`~src.config.get_settings` is called
            to create a fresh settings object from the current environment.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """Initialise the API client with authentication and timeout settings.

        Creates an ``httpx.Client`` pre-configured with the Blitzy Platform
        base URL, a ``Bearer`` authorization header, and the request timeout
        read from the provided (or default) :class:`~src.config.Settings`.

        Args:
            settings: Configuration object holding API connection details.
                Falls back to :func:`~src.config.get_settings` when omitted.
        """
        # Resolve settings — use the caller-supplied instance or create one
        # from the current environment variables / .env file.
        self._settings: Settings = settings if settings is not None else get_settings()

        # Build the authorization header.  If the token is ``None`` (i.e. the
        # environment variable was not set), we still construct the header with
        # an empty token so that ``httpx.Client`` can be created without error;
        # the server will reject the request with a 401 when the token is
        # actually missing, which is more actionable than a startup crash.
        auth_token: str = self._settings.api_auth_token or ""

        # Resolve base URL — guard against ``None`` by falling back to an
        # empty string.  Requests will fail with a clear connection error when
        # the base URL is unconfigured, preserving fail-fast semantics while
        # allowing the client to be constructed unconditionally.
        base_url: str = self._settings.api_base_url or ""

        # Instantiate the underlying HTTP client with shared configuration.
        self.client: httpx.Client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Accept": "application/json",
            },
            timeout=float(self._settings.request_timeout),
        )

    # ------------------------------------------------------------------
    # Endpoint methods — strictly read-only HTTP GET operations
    # ------------------------------------------------------------------

    def get_runs_metering(
        self, project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch metering data for multiple code-generation runs.

        Issues ``GET /runs/metering?projectId=<id>`` and returns the parsed
        JSON response body.

        Args:
            project_id: Target project identifier.  When ``None``, falls back
                to ``settings.project_id``.

        Returns:
            Parsed JSON response body as a dictionary.  The response is
            expected to contain an array of metering records, each with a
            ``percent_complete`` (or ``percentComplete``) field.

        Raises:
            httpx.HTTPStatusError: If the server returns a non-2xx status code.
            httpx.ConnectError: If the connection to the API fails.
        """
        resolved_project_id: Optional[str] = (
            project_id if project_id is not None else self._settings.project_id
        )
        response: httpx.Response = self.client.get(
            "/runs/metering",
            params={"projectId": resolved_project_id},
        )
        response.raise_for_status()
        return response.json()

    def get_runs_metering_current(self) -> Dict[str, Any]:
        """Fetch metering data for the currently in-progress run.

        Issues ``GET /runs/metering/current`` and returns the parsed JSON
        response body.  This endpoint is typically polled during an active
        code-generation run.

        Returns:
            Parsed JSON response body as a dictionary containing the metering
            record for the active run, including a ``percent_complete`` (or
            ``percentComplete``) field.

        Raises:
            httpx.HTTPStatusError: If the server returns a non-2xx status code.
            httpx.ConnectError: If the connection to the API fails.
        """
        response: httpx.Response = self.client.get("/runs/metering/current")
        response.raise_for_status()
        return response.json()

    def get_project(
        self, project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch project detail with inline metering information.

        Issues ``GET /project?id=<id>`` and returns the parsed JSON response
        body.  The metering data (including ``percent_complete``) is embedded
        within the project response under a nested metering key.

        Args:
            project_id: Target project identifier.  When ``None``, falls back
                to ``settings.project_id``.

        Returns:
            Parsed JSON response body as a dictionary representing the project
            with nested metering data.

        Raises:
            httpx.HTTPStatusError: If the server returns a non-2xx status code.
            httpx.ConnectError: If the connection to the API fails.
        """
        resolved_project_id: Optional[str] = (
            project_id if project_id is not None else self._settings.project_id
        )
        response: httpx.Response = self.client.get(
            "/project",
            params={"id": resolved_project_id},
        )
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Context-manager protocol
    # ------------------------------------------------------------------

    def __enter__(self) -> "BlitzyAPIClient":
        """Enter the context manager, returning this client instance.

        Returns:
            The current :class:`BlitzyAPIClient` instance for use inside a
            ``with`` block.
        """
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> None:
        """Exit the context manager, closing the underlying HTTP client.

        Ensures the ``httpx.Client`` is properly closed and all associated
        network resources (connections, sockets) are released regardless of
        whether an exception occurred inside the ``with`` block.

        Args:
            exc_type: The exception class, if an exception was raised.
            exc_val: The exception instance, if an exception was raised.
            exc_tb: The traceback object, if an exception was raised.
        """
        self.client.close()

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Explicitly close the underlying HTTP client.

        Callers that do **not** use the context-manager pattern should call
        this method when the client is no longer needed to release network
        resources.
        """
        self.client.close()

    def __repr__(self) -> str:
        """Return a developer-friendly string representation of the client."""
        base_url = self._settings.api_base_url or "<not configured>"
        return f"BlitzyAPIClient(base_url={base_url!r})"


# ------------------------------------------------------------------
# Module-level factory function
# ------------------------------------------------------------------


def create_client(settings: Optional[Settings] = None) -> BlitzyAPIClient:
    """Create and return a new :class:`BlitzyAPIClient` instance.

    This convenience factory function provides a simple entry point for
    obtaining a configured API client.  It accepts the same optional
    ``settings`` parameter as the class constructor.

    Args:
        settings: An optional :class:`~src.config.Settings` instance.
            When ``None``, the client will load settings from the current
            environment via :func:`~src.config.get_settings`.

    Returns:
        A ready-to-use :class:`BlitzyAPIClient` instance.

    Usage::

        client = create_client()
        try:
            data = client.get_runs_metering()
        finally:
            client.close()
    """
    return BlitzyAPIClient(settings=settings)
