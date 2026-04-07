"""
Blitzy Platform API Test Suite — Edge Case and Boundary Tests.

This module contains dedicated edge-case tests for the ``percent_complete`` /
``percentComplete`` field across all three Blitzy Platform API endpoints.  It
validates:

- **Value boundaries** — values at, above, and below the ``[0.0, 100.0]``
  inclusive range.
- **Invalid data types** — strings, booleans, lists, and dicts are rejected.
- **Null handling** — ``None`` is an acceptable field value.
- **Field presence** — the field must always be present in every response; its
  absence is explicitly a bug per the specification.
- **Live endpoint verification** — integration tests that confirm the field
  exists in real responses from all three API endpoints.

Test Classes:
    TestValueBoundaries:
        Validates the numeric boundaries of the ``percent_complete`` field value
        using the :func:`~src.validators.validate_percent_value` function.
    TestInvalidTypes:
        Validates that non-numeric types (``str``, ``bool``, ``list``, ``dict``)
        are rejected by the validator.
    TestNullHandling:
        Validates that ``None`` is an accepted value both at the validator level
        and when embedded in a full response dictionary.
    TestFieldPresence:
        Validates that the field can be detected by both naming conventions
        and that its absence from a response is flagged as an error.
    TestLiveEndpointEdgeCases:
        Integration tests that hit all three Blitzy Platform API endpoints and
        assert the field is present in the live response data.

Markers:
    ``edge_cases`` — all tests in this module are marked with the custom
    ``edge_cases`` pytest marker for selective execution.

Usage::

    # Run only edge-case tests
    pytest -m edge_cases -v

    # Run the full test suite
    pytest -v
"""

import pytest

from src.validators import (
    find_percent_field,
    validate_percent_value,
    validate_percent_complete_in_response,
)
from src.api_client import BlitzyAPIClient


# ---------------------------------------------------------------------------
# Module-level pytest marker — applied to every test in this file.
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.edge_cases


# ===========================================================================
# TestValueBoundaries — numeric range edge cases
# ===========================================================================


class TestValueBoundaries:
    """Validate that ``validate_percent_value`` correctly enforces the
    inclusive ``[0.0, 100.0]`` range for the ``percent_complete`` field.

    These are pure unit tests that exercise the validator function directly
    with crafted input values — no API calls are made.
    """

    # -----------------------------------------------------------------------
    # Upper-bound violations
    # -----------------------------------------------------------------------

    def test_value_not_exceeding_100(self) -> None:
        """Values strictly greater than 100.0 must be rejected.

        Per the AAP, the valid domain is ``[0.0, 100.0]`` inclusive.
        Any value exceeding 100.0 is out of range and must return
        ``(False, <message mentioning 'exceeds maximum 100.0'>)``.
        """
        # Just above the upper boundary
        is_valid, error_msg = validate_percent_value(101.0)
        assert is_valid is False, (
            "validate_percent_value(101.0) should reject values exceeding 100.0"
        )
        assert "exceeds maximum 100.0" in error_msg, (
            f"Error message should mention 'exceeds maximum 100.0', got: {error_msg!r}"
        )

        # Slightly above the boundary
        is_valid, error_msg = validate_percent_value(100.1)
        assert is_valid is False, (
            "validate_percent_value(100.1) should reject values exceeding 100.0"
        )
        assert "exceeds maximum 100.0" in error_msg, (
            f"Error message should mention 'exceeds maximum 100.0', got: {error_msg!r}"
        )

        # Extreme upper outlier
        is_valid, error_msg = validate_percent_value(999.99)
        assert is_valid is False, (
            "validate_percent_value(999.99) should reject values exceeding 100.0"
        )
        assert "exceeds maximum 100.0" in error_msg, (
            f"Error message should mention 'exceeds maximum 100.0', got: {error_msg!r}"
        )

    # -----------------------------------------------------------------------
    # Lower-bound violations
    # -----------------------------------------------------------------------

    def test_value_not_below_zero(self) -> None:
        """Values strictly below 0.0 must be rejected.

        Per the AAP, the valid domain starts at 0.0 inclusive.
        Any negative value must return
        ``(False, <message mentioning 'below minimum 0.0'>)``.
        """
        # Just below the lower boundary
        is_valid, error_msg = validate_percent_value(-1.0)
        assert is_valid is False, (
            "validate_percent_value(-1.0) should reject negative values"
        )
        assert "below minimum 0.0" in error_msg, (
            f"Error message should mention 'below minimum 0.0', got: {error_msg!r}"
        )

        # Slightly below zero
        is_valid, error_msg = validate_percent_value(-0.1)
        assert is_valid is False, (
            "validate_percent_value(-0.1) should reject negative values"
        )
        assert "below minimum 0.0" in error_msg, (
            f"Error message should mention 'below minimum 0.0', got: {error_msg!r}"
        )

        # Extreme lower outlier
        is_valid, error_msg = validate_percent_value(-100.0)
        assert is_valid is False, (
            "validate_percent_value(-100.0) should reject negative values"
        )
        assert "below minimum 0.0" in error_msg, (
            f"Error message should mention 'below minimum 0.0', got: {error_msg!r}"
        )

    # -----------------------------------------------------------------------
    # Valid boundary values (inclusive endpoints and a mid-range value)
    # -----------------------------------------------------------------------

    def test_value_at_boundaries(self) -> None:
        """Values exactly at or within the ``[0.0, 100.0]`` boundary must be
        accepted with an empty error message.

        This covers:
        - 0.0 (float lower bound)
        - 100.0 (float upper bound)
        - 0 (int lower bound)
        - 100 (int upper bound)
        - 50.5 (mid-range float)
        """
        # Lower boundary as float
        is_valid, error_msg = validate_percent_value(0.0)
        assert is_valid is True, (
            "validate_percent_value(0.0) should accept the lower boundary"
        )
        assert error_msg == "", (
            f"Expected empty error for valid value 0.0, got: {error_msg!r}"
        )

        # Upper boundary as float
        is_valid, error_msg = validate_percent_value(100.0)
        assert is_valid is True, (
            "validate_percent_value(100.0) should accept the upper boundary"
        )
        assert error_msg == "", (
            f"Expected empty error for valid value 100.0, got: {error_msg!r}"
        )

        # Lower boundary as int
        is_valid, error_msg = validate_percent_value(0)
        assert is_valid is True, (
            "validate_percent_value(0) should accept integer lower boundary"
        )
        assert error_msg == "", (
            f"Expected empty error for valid value 0, got: {error_msg!r}"
        )

        # Upper boundary as int
        is_valid, error_msg = validate_percent_value(100)
        assert is_valid is True, (
            "validate_percent_value(100) should accept integer upper boundary"
        )
        assert error_msg == "", (
            f"Expected empty error for valid value 100, got: {error_msg!r}"
        )

        # Mid-range float
        is_valid, error_msg = validate_percent_value(50.5)
        assert is_valid is True, (
            "validate_percent_value(50.5) should accept mid-range values"
        )
        assert error_msg == "", (
            f"Expected empty error for valid value 50.5, got: {error_msg!r}"
        )


# ===========================================================================
# TestInvalidTypes — data-type rejection edge cases
# ===========================================================================


class TestInvalidTypes:
    """Validate that ``validate_percent_value`` rejects non-numeric, non-null
    data types with clear error messages identifying the offending type.

    CRITICAL: ``bool`` is a subclass of ``int`` in Python.  The validator
    must check for ``bool`` **before** ``int`` to prevent ``True``/``False``
    from being silently accepted as valid numeric values.
    """

    def test_value_not_string(self) -> None:
        """String values must be rejected regardless of their content.

        The error message must indicate that the received type is ``str``.
        """
        # Numeric-looking string
        is_valid, error_msg = validate_percent_value("50")
        assert is_valid is False, (
            "validate_percent_value('50') should reject string values"
        )
        assert "str" in error_msg, (
            f"Error message should indicate wrong type (got str), got: {error_msg!r}"
        )

        # Non-numeric string
        is_valid, error_msg = validate_percent_value("complete")
        assert is_valid is False, (
            "validate_percent_value('complete') should reject string values"
        )
        assert "str" in error_msg, (
            f"Error message should indicate wrong type (got str), got: {error_msg!r}"
        )

    def test_value_not_boolean(self) -> None:
        """Boolean values must be explicitly rejected even though ``bool``
        is a subclass of ``int`` in Python.

        ``isinstance(True, int)`` returns ``True`` in Python, so the
        validator must perform the ``bool`` check **before** the ``int``
        check.  The error message must indicate that the received type is
        ``bool``.
        """
        # True (bool, which is also int in Python)
        is_valid, error_msg = validate_percent_value(True)
        assert is_valid is False, (
            "validate_percent_value(True) should reject boolean values "
            "(bool is a subclass of int in Python)"
        )
        assert "bool" in error_msg, (
            f"Error message should indicate got bool, got: {error_msg!r}"
        )

        # False (bool, which is also int in Python)
        is_valid, error_msg = validate_percent_value(False)
        assert is_valid is False, (
            "validate_percent_value(False) should reject boolean values "
            "(bool is a subclass of int in Python)"
        )
        assert "bool" in error_msg, (
            f"Error message should indicate got bool, got: {error_msg!r}"
        )

    def test_value_not_nan(self) -> None:
        """NaN (Not a Number) must be rejected as an invalid value.

        IEEE 754 NaN comparisons with ``<`` and ``>`` always return ``False``,
        which means NaN would silently pass range boundary checks if not
        explicitly guarded.  The validator must detect NaN and reject it
        with a clear error message.

        Per the AAP (Section 0.7.1), only numeric values within ``[0.0, 100.0]``
        and ``None`` are valid.  NaN is not a meaningful percentage value and
        must be treated as invalid.
        """
        nan_value = float("nan")
        is_valid, error_msg = validate_percent_value(nan_value)
        assert is_valid is False, (
            "validate_percent_value(float('nan')) should reject NaN values — "
            "NaN is not a meaningful percent_complete value"
        )
        assert "NaN" in error_msg, (
            f"Error message should mention 'NaN', got: {error_msg!r}"
        )

    def test_value_not_list_or_dict(self) -> None:
        """Collection types (``list`` and ``dict``) must be rejected.

        These types should never appear as the value of the
        ``percent_complete`` field in a well-formed API response.
        """
        # List containing a numeric value
        is_valid, error_msg = validate_percent_value([50])
        assert is_valid is False, (
            "validate_percent_value([50]) should reject list values"
        )
        assert "list" in error_msg, (
            f"Error message should indicate wrong type (got list), got: {error_msg!r}"
        )

        # Dict containing a numeric value
        is_valid, error_msg = validate_percent_value({"value": 50})
        assert is_valid is False, (
            "validate_percent_value({'value': 50}) should reject dict values"
        )
        assert "dict" in error_msg, (
            f"Error message should indicate wrong type (got dict), got: {error_msg!r}"
        )


# ===========================================================================
# TestNullHandling — None / null acceptance edge cases
# ===========================================================================


class TestNullHandling:
    """Validate that ``None`` (JSON ``null``) is correctly accepted as a valid
    value for the ``percent_complete`` field.

    Per the AAP, ``None`` represents "metering data not applicable" and is
    one of the two valid states (the other being a numeric value within
    ``[0.0, 100.0]``).
    """

    def test_null_is_acceptable(self) -> None:
        """``None`` must be accepted as a valid value with no error message.

        This validates the lowest-level validator function
        :func:`validate_percent_value` treats ``None`` as valid.
        """
        is_valid, error_msg = validate_percent_value(None)
        assert is_valid is True, (
            "validate_percent_value(None) should accept null as a valid value"
        )
        assert error_msg == "", (
            f"Expected empty error for valid null value, got: {error_msg!r}"
        )

    def test_null_in_response_data(self) -> None:
        """``None`` embedded in a full response dictionary must be accepted
        by the end-to-end response validator.

        Creates a mock response with ``percent_complete: None`` and runs it
        through :func:`validate_percent_complete_in_response` to ensure the
        entire validation pipeline accepts null values.
        """
        data = {"percent_complete": None, "run_id": "abc-123", "status": "completed"}
        is_valid, error_msg = validate_percent_complete_in_response(
            data, "test_endpoint"
        )
        assert is_valid is True, (
            "validate_percent_complete_in_response should accept "
            "percent_complete=None in response data"
        )


# ===========================================================================
# TestFieldPresence — field detection and absence edge cases
# ===========================================================================


class TestFieldPresence:
    """Validate that the ``percent_complete`` / ``percentComplete`` field is
    correctly detected in both naming conventions and that its absence from
    a response is flagged as an error.

    Per the AAP (Section 0.7.1), the absence of the field from any
    endpoint response is **explicitly a bug**.  The field must always be
    present even if its value is ``null``.
    """

    def test_field_not_missing(self) -> None:
        """A response dict without either ``percent_complete`` or
        ``percentComplete`` must be flagged as an error.

        The error message must clearly indicate that the field is missing
        from the response.
        """
        # Response with no percent_complete field at all
        data = {"run_id": "xyz-789", "status": "completed", "duration_ms": 12345}
        is_valid, error_msg = validate_percent_complete_in_response(
            data, "test_endpoint"
        )
        assert is_valid is False, (
            "validate_percent_complete_in_response should detect missing "
            "percent_complete field in response"
        )
        assert "missing" in error_msg.lower(), (
            f"Error message should mention 'missing' for absent field, "
            f"got: {error_msg!r}"
        )

    def test_field_present_snake_case(self) -> None:
        """The snake_case variant ``percent_complete`` must be detected.

        :func:`find_percent_field` must return
        ``("percent_complete", <value>)`` when the snake_case key is present.
        """
        data = {"percent_complete": 50.0, "run_id": "abc-123"}
        field_name, field_value = find_percent_field(data)
        assert field_name == "percent_complete", (
            f"Expected field name 'percent_complete', got {field_name!r}"
        )
        assert field_value == 50.0, (
            f"Expected field value 50.0, got {field_value!r}"
        )

    def test_field_present_camel_case(self) -> None:
        """The camelCase variant ``percentComplete`` must be detected.

        :func:`find_percent_field` must return
        ``("percentComplete", <value>)`` when the camelCase key is present.
        """
        data = {"percentComplete": 75.5, "runId": "def-456"}
        field_name, field_value = find_percent_field(data)
        assert field_name == "percentComplete", (
            f"Expected field name 'percentComplete', got {field_name!r}"
        )
        assert field_value == 75.5, (
            f"Expected field value 75.5, got {field_value!r}"
        )


# ===========================================================================
# TestLiveEndpointEdgeCases — integration tests against real APIs
# ===========================================================================


class TestLiveEndpointEdgeCases:
    """Integration tests that verify the ``percent_complete`` field is present
    in live API responses from all three Blitzy Platform endpoints.

    These tests use the ``api_client`` and ``project_id`` fixtures provided
    by ``tests/conftest.py``.  If an endpoint is unreachable or returns an
    error, the test is skipped gracefully using ``pytest.skip()``.

    The tests are read-only (HTTP GET only) and idempotent — they do not
    modify server state.
    """

    def test_runs_metering_field_not_missing(
        self, api_client: BlitzyAPIClient, project_id: str
    ) -> None:
        """``GET /runs/metering`` — every record must contain the
        ``percent_complete`` / ``percentComplete`` field.

        Iterates over all records in the response and asserts that
        :func:`find_percent_field` detects the field in each one.
        """
        try:
            response = api_client.get_runs_metering(project_id)
        except Exception as exc:
            pytest.skip(
                f"GET /runs/metering endpoint unavailable: {exc}"
            )

        # The response may be a list of records or a dict wrapping a list.
        records = response if isinstance(response, list) else []
        if isinstance(response, dict):
            for key in ("data", "records", "items", "results"):
                if key in response and isinstance(response[key], list):
                    records = response[key]
                    break
            if not records:
                # Treat the entire dict as a single record.
                records = [response]

        assert len(records) > 0, (
            "GET /runs/metering returned no records — cannot verify "
            "percent_complete field presence"
        )

        for idx, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            field_name, _value = find_percent_field(record)
            assert field_name is not None, (
                f"Field 'percent_complete'/'percentComplete' is missing from "
                f"metering record at index {idx} in GET /runs/metering response"
            )

    def test_runs_metering_current_field_not_missing(
        self, api_client: BlitzyAPIClient
    ) -> None:
        """``GET /runs/metering/current`` — the response must contain the
        ``percent_complete`` / ``percentComplete`` field.

        If no run is currently active the endpoint may return an error or
        empty payload — in that case the test is skipped gracefully.
        """
        try:
            response = api_client.get_runs_metering_current()
        except Exception as exc:
            pytest.skip(
                f"GET /runs/metering/current endpoint unavailable: {exc}"
            )

        if not isinstance(response, dict) or not response:
            pytest.skip(
                "GET /runs/metering/current returned empty or non-dict "
                "response — no active run available"
            )

        field_name, _value = find_percent_field(response)
        assert field_name is not None, (
            "Field 'percent_complete'/'percentComplete' is missing from "
            "GET /runs/metering/current response"
        )

    def test_project_metering_field_not_missing(
        self, api_client: BlitzyAPIClient, project_id: str
    ) -> None:
        """``GET /project`` — the nested metering data must contain the
        ``percent_complete`` / ``percentComplete`` field.

        The project response typically embeds metering data under a nested
        key such as ``metering``, ``meteringData``, or ``metering_data``.
        This test uses :func:`validate_percent_complete_in_response` which
        searches both top-level and nested structures.
        """
        try:
            response = api_client.get_project(project_id)
        except Exception as exc:
            pytest.skip(
                f"GET /project endpoint unavailable: {exc}"
            )

        if not isinstance(response, dict):
            pytest.skip(
                "GET /project returned non-dict response — cannot verify "
                "percent_complete field"
            )

        is_valid, error_msg = validate_percent_complete_in_response(
            response, "project"
        )
        assert is_valid is True, (
            f"GET /project edge-case field presence check failed: {error_msg}"
        )
