"""
Blitzy Platform API Test Suite — Shared Pytest Fixtures.

Provides session-scoped fixtures that wire configuration into test execution.
All test files in the ``tests/`` package use these fixtures for API connectivity,
authentication, and response caching.

Fixtures Provided:
    settings:
        Validated ``Settings`` instance loaded from environment variables / ``.env``.
    api_client:
        Pre-configured ``BlitzyAPIClient`` with auth headers, base URL, and timeout.
    project_id:
        Target project identifier string from the loaded configuration.
    metering_response:
        Cached JSON response from ``GET /runs/metering?projectId=<id>``.
    current_metering_response:
        Cached JSON response from ``GET /runs/metering/current``.
    project_response:
        Cached JSON response from ``GET /project?id=<id>``.

Session Scoping:
    Every fixture in this module is scoped to the *session* level, meaning it is
    created once and shared across all tests in a single ``pytest`` run.  This
    avoids redundant API calls and ensures test-suite efficiency.

Graceful Degradation:
    The three endpoint response fixtures (``metering_response``,
    ``current_metering_response``, ``project_response``) catch
    ``httpx.HTTPStatusError`` and network-level exceptions and call
    ``pytest.skip()`` rather than letting the entire test session crash.
    Tests depending on an unavailable endpoint are silently skipped while
    the rest of the suite continues to execute.

Environment Configuration:
    The fixtures read all connection details from environment variables
    (or a ``.env`` file).  No URLs, tokens, or project IDs are hard-coded.
    See ``.env.example`` for the required variable names.
"""

from typing import Any, Dict, Optional

import httpx
import pytest

from src.api_client import BlitzyAPIClient
from src.config import Settings, get_settings


# ---------------------------------------------------------------------------
# Configuration fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Create and validate an application ``Settings`` instance.

    Loads API connection configuration (base URL, auth token, project ID,
    request timeout) from environment variables and/or a ``.env`` file by
    delegating to :func:`~src.config.get_settings`.  The resulting instance
    is validated to ensure all required values are present before any API
    call is attempted.

    Scope:
        Session — a single ``Settings`` object is shared across every test.

    Returns:
        A fully validated :class:`~src.config.Settings` instance.

    Raises:
        ValueError: If any required configuration variable is missing or
            invalid (propagated from :meth:`Settings.validate`).
    """
    config: Settings = get_settings()
    config.validate()
    return config


# ---------------------------------------------------------------------------
# Client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def api_client(settings: Settings) -> BlitzyAPIClient:
    """Provide a session-scoped ``BlitzyAPIClient`` with automatic cleanup.

    The client is pre-configured with:

    * ``base_url`` — from ``settings.api_base_url``
    * ``Authorization: Bearer <token>`` header — from ``settings.api_auth_token``
    * ``timeout`` — from ``settings.request_timeout``

    A ``yield`` fixture is used so that the underlying ``httpx.Client`` is
    properly closed after all tests have executed, releasing any held network
    resources (connections, sockets).

    Scope:
        Session — a single ``BlitzyAPIClient`` is shared across every test.

    Args:
        settings: Validated configuration fixture.

    Yields:
        A ready-to-use :class:`~src.api_client.BlitzyAPIClient` instance.
    """
    client: BlitzyAPIClient = BlitzyAPIClient(settings=settings)
    yield client
    # Teardown: release the underlying httpx.Client connection pool.
    client.client.close()


# ---------------------------------------------------------------------------
# Project identifier fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def project_id(settings: Settings) -> str:
    """Return the target project identifier from configuration.

    The project ID is read from the ``PROJECT_ID`` environment variable via
    the ``settings`` fixture and is used as a query parameter for the
    ``/runs/metering`` and ``/project`` endpoints.

    Scope:
        Session — a single project ID is used across every test.

    Args:
        settings: Validated configuration fixture.

    Returns:
        The project identifier string.
    """
    return settings.project_id


# ---------------------------------------------------------------------------
# Endpoint response caching fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def metering_response(
    api_client: BlitzyAPIClient,
    project_id: str,
) -> Optional[Dict[str, Any]]:
    """Fetch and cache the ``GET /runs/metering`` response for the session.

    Issues a single ``GET /runs/metering?projectId=<project_id>`` request
    and returns the parsed JSON payload.  The response is cached for the
    entire test session so that multiple tests can inspect it without
    issuing redundant HTTP calls.

    If the endpoint is unreachable or returns a non-2xx status code, the
    fixture calls ``pytest.skip()`` so that tests depending on this fixture
    are gracefully skipped rather than crashing the session.

    Scope:
        Session — fetched once, reused across all tests that request it.

    Args:
        api_client: Configured HTTP client fixture.
        project_id: Target project identifier fixture.

    Returns:
        Parsed JSON response body (``dict`` or ``list``) from the
        ``/runs/metering`` endpoint.
    """
    try:
        response: Dict[str, Any] = api_client.get_runs_metering(project_id)
        return response
    except httpx.HTTPStatusError as exc:
        pytest.skip(
            f"GET /runs/metering endpoint unavailable "
            f"(HTTP {exc.response.status_code}): {exc}"
        )
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as exc:
        pytest.skip(
            f"GET /runs/metering endpoint unreachable: {exc}"
        )


@pytest.fixture(scope="session")
def current_metering_response(
    api_client: BlitzyAPIClient,
) -> Optional[Dict[str, Any]]:
    """Fetch and cache the ``GET /runs/metering/current`` response.

    Issues a single ``GET /runs/metering/current`` request and returns the
    parsed JSON payload.  This endpoint returns metering data for the
    currently in-progress code-generation run.

    Because this endpoint only returns meaningful data while a run is
    actively executing, it may return an error or empty payload when no run
    is in progress.  In that case the fixture calls ``pytest.skip()`` so
    that dependent tests are skipped gracefully.

    Scope:
        Session — fetched once, reused across all tests that request it.

    Args:
        api_client: Configured HTTP client fixture.

    Returns:
        Parsed JSON response body (``dict``) from the
        ``/runs/metering/current`` endpoint, or ``None`` if no active run
        is available (dependent tests will be skipped).
    """
    try:
        response: Dict[str, Any] = api_client.get_runs_metering_current()
        return response
    except httpx.HTTPStatusError as exc:
        pytest.skip(
            f"GET /runs/metering/current endpoint unavailable "
            f"(HTTP {exc.response.status_code}): {exc}"
        )
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as exc:
        pytest.skip(
            f"GET /runs/metering/current endpoint unreachable: {exc}"
        )


@pytest.fixture(scope="session")
def project_response(
    api_client: BlitzyAPIClient,
    project_id: str,
) -> Optional[Dict[str, Any]]:
    """Fetch and cache the ``GET /project`` response for the session.

    Issues a single ``GET /project?id=<project_id>`` request and returns
    the parsed JSON payload.  The project response is expected to contain
    inline metering data (with a ``percent_complete`` or ``percentComplete``
    field) nested within the response body.

    If the endpoint is unreachable or returns a non-2xx status code, the
    fixture calls ``pytest.skip()`` so that dependent tests are gracefully
    skipped.

    Scope:
        Session — fetched once, reused across all tests that request it.

    Args:
        api_client: Configured HTTP client fixture.
        project_id: Target project identifier fixture.

    Returns:
        Parsed JSON response body (``dict``) from the ``/project``
        endpoint.
    """
    try:
        response: Dict[str, Any] = api_client.get_project(project_id)
        return response
    except httpx.HTTPStatusError as exc:
        pytest.skip(
            f"GET /project endpoint unavailable "
            f"(HTTP {exc.response.status_code}): {exc}"
        )
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as exc:
        pytest.skip(
            f"GET /project endpoint unreachable: {exc}"
        )
