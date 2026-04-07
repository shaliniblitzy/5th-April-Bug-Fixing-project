"""
Blitzy Platform API Test Suite - Core Source Package.

This package provides configuration management, HTTP client abstraction,
validation logic, and response models for validating the percent_complete
field across Blitzy Platform API endpoints.

Submodules:
    config      — Environment-aware configuration loading for API base URLs
                  and authentication credentials via ``Settings`` and
                  ``get_settings()``.
    api_client  — Lightweight HTTP client abstraction (``BlitzyAPIClient``)
                  for making authenticated GET requests to the three target
                  Blitzy Platform API endpoints.
    validators  — Core validation logic for ``percent_complete`` field
                  detection, type/range verification, and cross-endpoint
                  consistency checking.
    models      — Pydantic V2 response models (``MeteringRecord``,
                  ``CurrentMeteringResponse``, ``ProjectResponse``) defining
                  expected API response schemas with ``percent_complete``
                  field support.

Convenience Imports:
    All key classes, functions, and constants from submodules are re-exported
    at the package level for convenient access::

        from src import Settings, get_settings, BlitzyAPIClient, create_client
        from src import find_percent_field, validate_percent_value
        from src import MeteringRecord, CurrentMeteringResponse, ProjectResponse
"""

# ---------------------------------------------------------------------------
# Package version
# ---------------------------------------------------------------------------

__version__: str = "1.0.0"
"""Semantic version string for the Blitzy Platform API Test Suite source package."""

# ---------------------------------------------------------------------------
# Convenience re-exports from submodules
# ---------------------------------------------------------------------------

# Configuration management — Settings class and factory function for loading
# API base URL, authentication token, project ID, and request timeout from
# environment variables or .env files.
from src.config import Settings, get_settings

# HTTP client — BlitzyAPIClient class wrapping httpx.Client for authenticated
# GET requests to the three target Blitzy Platform API endpoints, plus a
# create_client factory function.
from src.api_client import BlitzyAPIClient, create_client

# Validation utilities — Field name detection and normalization, value type
# and range checking, cross-endpoint consistency verification, and a
# convenience end-to-end validator.
from src.validators import (
    find_percent_field,
    validate_percent_value,
    check_field_consistency,
    validate_percent_complete_in_response,
)

# Pydantic response models — Data models representing expected API response
# schemas for the metering and project endpoints, each supporting both
# snake_case and camelCase field naming conventions.
from src.models import (
    MeteringRecord,
    CurrentMeteringResponse,
    ProjectResponse,
)

# ---------------------------------------------------------------------------
# Public API declaration
# ---------------------------------------------------------------------------

__all__: list[str] = [
    # Package metadata
    "__version__",
    # Configuration (src.config)
    "Settings",
    "get_settings",
    # HTTP client (src.api_client)
    "BlitzyAPIClient",
    "create_client",
    # Validators (src.validators)
    "find_percent_field",
    "validate_percent_value",
    "check_field_consistency",
    "validate_percent_complete_in_response",
    # Response models (src.models)
    "MeteringRecord",
    "CurrentMeteringResponse",
    "ProjectResponse",
]
