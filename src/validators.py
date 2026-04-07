"""
Blitzy Platform API Test Suite — Core Validation Logic.

This module provides validation utilities for the ``percent_complete`` field
across Blitzy Platform API endpoints, including:

- **Field name detection and normalization** — handles both ``percent_complete``
  (snake_case) and ``percentComplete`` (camelCase) naming conventions.
- **Value type checking and range verification** — enforces that the field value
  is either a numeric value within the inclusive range [0.0, 100.0] or explicitly
  ``None`` (null) when metering data is not applicable.
- **Cross-endpoint field naming consistency checking** — detects when different
  endpoints use different naming conventions, which indicates a potential API
  inconsistency.

Constants:
    SNAKE_CASE_FIELD: The snake_case field name variant (``"percent_complete"``).
    CAMEL_CASE_FIELD: The camelCase field name variant (``"percentComplete"``).
    VALID_FIELD_NAMES: A set containing both acceptable field name variants.

Functions:
    find_percent_field: Search a flat dictionary for the percent complete field.
    find_percent_field_nested: Search nested structures for the percent complete field.
    validate_percent_value: Validate a field value against the allowed domain.
    check_field_consistency: Compare field naming across multiple endpoint responses.
    validate_percent_complete_in_response: End-to-end convenience validator.

Usage:
    from src.validators import (
        find_percent_field,
        find_percent_field_nested,
        validate_percent_value,
        check_field_consistency,
        validate_percent_complete_in_response,
        SNAKE_CASE_FIELD,
        CAMEL_CASE_FIELD,
        VALID_FIELD_NAMES,
    )

    # Detect the field in an API response
    field_name, field_value = find_percent_field(response_json)

    # Validate the field value
    is_valid, error_msg = validate_percent_value(field_value)

    # One-shot validation of a full response
    ok, msg = validate_percent_complete_in_response(response_json, "runs_metering")
"""

import math
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================================
# Constants
# ============================================================================

SNAKE_CASE_FIELD: str = "percent_complete"
"""The snake_case field name variant used in some API responses."""

CAMEL_CASE_FIELD: str = "percentComplete"
"""The camelCase field name variant used in some API responses."""

VALID_FIELD_NAMES: set = {SNAKE_CASE_FIELD, CAMEL_CASE_FIELD}
"""Set of all acceptable field name variants for the percent complete field."""

# Type alias documenting the valid value domain for the percent_complete field.
# The field must be either a numeric value (int or float) within [0.0, 100.0]
# or None when metering data is not applicable.
PercentValue = Union[int, float, None]
"""Type alias representing valid percent_complete values: int, float, or None."""

# Default nested dictionary keys that may contain metering data in API
# responses.  The ``/project`` endpoint typically nests metering information
# under one of these keys.
_DEFAULT_METERING_KEYS: List[str] = [
    "metering",
    "meteringData",
    "metering_data",
]


# ============================================================================
# Field Detection Functions
# ============================================================================

def find_percent_field(data: dict) -> Tuple[Optional[str], Any]:
    """
    Search a dictionary for the percent_complete field using either naming convention.

    Looks for both ``percent_complete`` (snake_case) and ``percentComplete``
    (camelCase) keys in the provided dictionary.  If both keys exist, the
    snake_case variant is preferred and returned.

    Args:
        data: A dictionary representing an API response payload or a portion
            thereof.  If *data* is not a ``dict``, the function returns
            ``(None, None)`` without raising an error.

    Returns:
        A tuple ``(field_name, field_value)`` where:

        - *field_name* is the actual key found in *data* (``"percent_complete"``
          or ``"percentComplete"``), or ``None`` if neither key exists.
        - *field_value* is the value associated with the found key, or ``None``
          if the field is missing.

    Examples:
        >>> find_percent_field({"percent_complete": 75.5})
        ('percent_complete', 75.5)
        >>> find_percent_field({"percentComplete": 50})
        ('percentComplete', 50)
        >>> find_percent_field({"other_field": "value"})
        (None, None)
        >>> find_percent_field({"percent_complete": 80, "percentComplete": 80})
        ('percent_complete', 80)
    """
    if not isinstance(data, dict):
        return (None, None)

    # Check the snake_case variant first (preferred convention).
    if SNAKE_CASE_FIELD in data:
        # If both naming variants are present we still prefer snake_case,
        # but the dual presence is itself notable and may be surfaced by
        # the consistency checker or test assertions.
        return (SNAKE_CASE_FIELD, data[SNAKE_CASE_FIELD])

    # Fall back to the camelCase variant.
    if CAMEL_CASE_FIELD in data:
        return (CAMEL_CASE_FIELD, data[CAMEL_CASE_FIELD])

    # Neither variant found in the dictionary.
    return (None, None)


def find_percent_field_nested(
    data: dict,
    metering_keys: Optional[List[str]] = None,
) -> Tuple[Optional[str], Any, Optional[str]]:
    """
    Search for the percent_complete field in a dictionary and its nested structures.

    This is an enhanced version of :func:`find_percent_field` that also searches
    within nested dictionaries commonly used to contain metering data in API
    responses.  For example, the ``/project`` endpoint nests metering data
    within a ``metering`` or ``meteringData`` key.

    The search order is:

    1. Top-level keys of *data*.
    2. Each nested dictionary found under the keys listed in *metering_keys*.

    Args:
        data: A dictionary representing an API response.  If *data* is not a
            ``dict``, the function returns ``(None, None, None)`` without
            raising an error.
        metering_keys: Optional list of dictionary keys to search within for
            nested metering data.  When ``None``, defaults to
            ``["metering", "meteringData", "metering_data"]``.

    Returns:
        A tuple ``(field_name, field_value, nested_path)`` where:

        - *field_name* is the actual key found, or ``None`` if not found.
        - *field_value* is the associated value, or ``None`` if not found.
        - *nested_path* is the key under which the field was found (e.g.,
          ``"metering"``), or ``None`` if found at the top level.

    Examples:
        >>> find_percent_field_nested({"percent_complete": 80.0})
        ('percent_complete', 80.0, None)
        >>> find_percent_field_nested({"metering": {"percentComplete": 50}})
        ('percentComplete', 50, 'metering')
        >>> find_percent_field_nested({"unrelated": "data"})
        (None, None, None)
    """
    if not isinstance(data, dict):
        return (None, None, None)

    # 1. Try to find the field at the top level first.
    field_name, field_value = find_percent_field(data)
    if field_name is not None:
        return (field_name, field_value, None)

    # 2. Search within nested metering structures.
    search_keys: List[str] = (
        list(metering_keys) if metering_keys is not None else list(_DEFAULT_METERING_KEYS)
    )

    for nested_key in search_keys:
        if nested_key in data and isinstance(data[nested_key], dict):
            nested_data: Dict[str, Any] = data[nested_key]
            field_name, field_value = find_percent_field(nested_data)
            if field_name is not None:
                return (field_name, field_value, nested_key)

    # Not found at any level.
    return (None, None, None)


# ============================================================================
# Value Validation Function
# ============================================================================

def validate_percent_value(value: Any) -> Tuple[bool, str]:
    """
    Validate that a percent_complete field value conforms to the expected domain.

    The accepted value domain is strictly one of:

    - ``None`` — acceptable when metering data is not applicable.
    - A numeric value (``int`` or ``float``) within the **inclusive** range
      ``[0.0, 100.0]``.

    Boolean values are **explicitly rejected** even though ``bool`` is a
    subclass of ``int`` in Python (``isinstance(True, int)`` returns ``True``).
    String values, lists, dictionaries, and all other non-numeric types are
    also rejected.

    .. important::
        The ``bool`` check is performed **before** the ``int``/``float`` check
        to ensure that ``True`` and ``False`` are not silently accepted as
        valid numeric values.

    Args:
        value: The value to validate.  Expected to satisfy the
            :data:`PercentValue` type alias (``Union[int, float, None]``).

    Returns:
        A tuple ``(is_valid, error_message)`` where:

        - *is_valid* is ``True`` if the value is acceptable, ``False`` otherwise.
        - *error_message* is an empty string when valid, or a clear, actionable
          description of the validation failure.

    Examples:
        >>> validate_percent_value(None)
        (True, '')
        >>> validate_percent_value(75.5)
        (True, '')
        >>> validate_percent_value(0)
        (True, '')
        >>> validate_percent_value(100.0)
        (True, '')
        >>> validate_percent_value(True)
        (False, "Expected numeric or null, got bool: True")
        >>> validate_percent_value("75")
        (False, "Expected numeric or null, got str: '75'")
        >>> validate_percent_value(150.0)
        (False, 'Value 150.0 exceeds maximum 100.0')
        >>> validate_percent_value(-5)
        (False, 'Value -5 is below minimum 0.0')
    """
    # ------------------------------------------------------------------
    # Rule 1: None is valid (represents "metering data not applicable").
    # ------------------------------------------------------------------
    if value is None:
        return (True, "")

    # ------------------------------------------------------------------
    # Rule 2 (CRITICAL): Reject booleans BEFORE checking int/float.
    # In Python ``bool`` is a subclass of ``int``, so ``isinstance(True, int)``
    # returns ``True``.  We must catch booleans explicitly first.
    # ------------------------------------------------------------------
    if isinstance(value, bool):
        return (False, f"Expected numeric or null, got bool: {value!r}")

    # ------------------------------------------------------------------
    # Rule 3: Accept int and float; reject every other type.
    # ------------------------------------------------------------------
    if not isinstance(value, (int, float)):
        return (
            False,
            f"Expected numeric or null, got {type(value).__name__}: {value!r}",
        )

    # ------------------------------------------------------------------
    # Rule 3b: Reject NaN — IEEE 754 NaN is not a meaningful percentage.
    # NaN comparisons (< and >) always return False, so NaN would silently
    # pass the range checks below.  We must catch it explicitly here.
    # ------------------------------------------------------------------
    if isinstance(value, float) and math.isnan(value):
        return (False, "Expected numeric value, got NaN")

    # ------------------------------------------------------------------
    # Rule 4: Range lower bound — value must be >= 0.0.
    # ------------------------------------------------------------------
    if value < 0.0:
        return (False, f"Value {value} is below minimum 0.0")

    # ------------------------------------------------------------------
    # Rule 5: Range upper bound — value must be <= 100.0.
    # ------------------------------------------------------------------
    if value > 100.0:
        return (False, f"Value {value} exceeds maximum 100.0")

    # ------------------------------------------------------------------
    # All checks passed — the value is within the valid domain.
    # ------------------------------------------------------------------
    return (True, "")


# ============================================================================
# Cross-Endpoint Consistency Function
# ============================================================================

def check_field_consistency(
    responses: Dict[str, dict],
) -> Tuple[bool, str]:
    """
    Check that percent_complete field naming is consistent across endpoints.

    Verifies that all provided API endpoint responses use the **same** naming
    convention for the percent_complete field — either all use
    ``percent_complete`` (snake_case) or all use ``percentComplete``
    (camelCase).  A mismatch is flagged as a potential API inconsistency.

    The function also detects endpoints where the field is missing entirely,
    which per the specification constitutes a bug.

    Args:
        responses: A dictionary mapping endpoint names (descriptive strings) to
            their response data dictionaries.

            Example::

                {
                    "runs_metering": {"percent_complete": 75},
                    "runs_metering_current": {"percentComplete": 50},
                    "project": {"metering": {"percent_complete": 80}},
                }

    Returns:
        A tuple ``(is_consistent, message)`` where:

        - *is_consistent* is ``True`` if all endpoints use the same field name
          variant, ``False`` if there is a naming mismatch or if any endpoint
          is missing the field.
        - *message* is a descriptive string explaining the finding:

          - If consistent: ``"All endpoints use '<name>' consistently"``.
          - If inconsistent: ``"Field name mismatch detected: <details>"``.
          - If fields are missing: ``"Field missing from endpoint(s): <names>"``.

    Examples:
        >>> responses = {
        ...     "metering": {"percent_complete": 75},
        ...     "current": {"percent_complete": 50},
        ... }
        >>> check_field_consistency(responses)
        (True, "All endpoints use 'percent_complete' consistently")
    """
    if not responses:
        return (True, "No responses provided for consistency check")

    # Map each endpoint to the field name variant it uses (or record it as missing).
    field_names: Dict[str, Optional[str]] = {}
    missing_endpoints: List[str] = []

    for endpoint_name, response_data in responses.items():
        if not isinstance(response_data, dict):
            missing_endpoints.append(endpoint_name)
            continue

        # Use nested search so that the project endpoint's nested metering
        # structure is handled transparently.
        field_name, _value, _path = find_percent_field_nested(response_data)

        if field_name is None:
            missing_endpoints.append(endpoint_name)
        else:
            field_names[endpoint_name] = field_name

    # Report missing fields first — field absence is a bug per the AAP.
    if missing_endpoints:
        missing_list: str = ", ".join(sorted(missing_endpoints))
        return (
            False,
            f"Field missing from endpoint(s): {missing_list}",
        )

    # Determine whether all endpoints agree on the field name.
    unique_names: set = set(field_names.values())

    if len(unique_names) == 1:
        consistent_name: Optional[str] = unique_names.pop()
        return (True, f"All endpoints use '{consistent_name}' consistently")

    # Mismatch detected — build a detailed, per-endpoint report.
    details_parts: List[str] = []
    for endpoint_name in sorted(field_names.keys()):
        details_parts.append(f"{endpoint_name} uses '{field_names[endpoint_name]}'")
    details: str = "; ".join(details_parts)

    return (
        False,
        f"Field name mismatch detected: {details}",
    )


# ============================================================================
# Convenience Validation Function
# ============================================================================

def validate_percent_complete_in_response(
    data: dict,
    endpoint_name: str = "unknown",
) -> Tuple[bool, str]:
    """
    Validate the percent_complete field in an API response end-to-end.

    This high-level convenience function combines field detection (including
    nested structure search) with value validation in a single call.  It
    provides clear, actionable error messages suitable for test assertion
    output.

    The validation flow is:

    1. Verify that *data* is a dictionary.
    2. Search for the ``percent_complete`` / ``percentComplete`` field at the
       top level and within nested metering structures.
    3. If the field is not found anywhere, report it as missing (this is a bug
       per the specification — the field must always be present).
    4. If the field is found, validate its value with :func:`validate_percent_value`.

    Args:
        data: A dictionary representing the full API response body.
        endpoint_name: A descriptive name for the endpoint being validated,
            used in error messages for clear identification.  Defaults to
            ``"unknown"``.

    Returns:
        A tuple ``(is_valid, message)`` where:

        - *is_valid* is ``True`` if the field is present and its value is valid.
        - *message* is an empty string when valid, or a descriptive error
          message identifying the specific validation failure and the endpoint.

    Examples:
        >>> validate_percent_complete_in_response(
        ...     {"percent_complete": 75.5},
        ...     "runs_metering",
        ... )
        (True, '')
        >>> validate_percent_complete_in_response(
        ...     {"other_field": "value"},
        ...     "project",
        ... )
        (False, "Field 'percent_complete'/'percentComplete' is missing from project response")
    """
    # Guard against non-dict input.
    if not isinstance(data, dict):
        return (
            False,
            f"Expected dict response from {endpoint_name}, "
            f"got {type(data).__name__}",
        )

    # Search for the field including nested metering structures.
    field_name, field_value, nested_path = find_percent_field_nested(data)

    # If the field is not found anywhere this is a bug per the specification.
    if field_name is None:
        return (
            False,
            f"Field 'percent_complete'/'percentComplete' is missing from "
            f"{endpoint_name} response",
        )

    # Field found — validate the value against the allowed domain.
    is_valid, error_message = validate_percent_value(field_value)

    if is_valid:
        return (True, "")

    # Build a detailed error including the location context.
    location: str = (
        "at top level" if nested_path is None else f"under '{nested_path}'"
    )
    return (
        False,
        f"Invalid {field_name} value in {endpoint_name} response "
        f"({location}): {error_message}",
    )
