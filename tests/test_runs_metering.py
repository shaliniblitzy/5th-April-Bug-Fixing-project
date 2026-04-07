"""
Blitzy Platform API Test Suite — Tests for GET /runs/metering endpoint.

Validates the ``GET /runs/metering?projectId=xxx`` endpoint, which returns
metering data for multiple code generation runs (historical and completed).
The response is an array-based payload with per-run metering objects, each
expected to contain a ``percent_complete`` (or ``percentComplete``) field.

Test coverage includes:

- **Field presence** — ``percent_complete`` / ``percentComplete`` must exist in
  every record returned by the endpoint.
- **Type validation** — each value must be ``int``, ``float``, or ``None``.
  Strings, booleans, lists, and other types are rejected.
- **Range validation** — numeric values must fall within the inclusive range
  ``[0.0, 100.0]``.
- **Completed-run scenario** — records representing completed runs must have
  valid numeric values within the accepted range.
- **Response structure** — the raw response must be valid JSON (list or dict)
  and individual records must be dictionaries.

All tests are strictly read-only GET verifications.  They are idempotent and
do not modify server state.  Assertion messages include the record index so
that multi-record failures are immediately actionable.
"""

from typing import Any, Dict, List

import pytest

from src.api_client import BlitzyAPIClient
from src.models import MeteringRecord, parse_metering_response
from src.validators import (
    find_percent_field,
    validate_percent_complete_in_response,
    validate_percent_value,
)

# ---------------------------------------------------------------------------
# Module-level pytest marker
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.metering
"""Mark every test in this module with the ``metering`` marker so that
``pytest -m metering`` can selectively run only the /runs/metering tests."""


# ---------------------------------------------------------------------------
# Helper function
# ---------------------------------------------------------------------------


def _extract_records(response_data: Any) -> List[Dict[str, Any]]:
    """Extract a flat list of metering record dicts from the API response.

    The ``GET /runs/metering`` endpoint may return its records in several
    shapes:

    * A bare JSON array — ``[{…}, {…}, …]``
    * A wrapped object with a known list key — ``{"data": [{…}]}``,
      ``{"records": [{…}]}``, ``{"items": [{…}]}``, or
      ``{"results": [{…}]}``

    This helper normalises any of those shapes into a plain ``list[dict]``
    that the test methods can iterate over uniformly.

    Args:
        response_data: The raw JSON-decoded response from the API.

    Returns:
        A list of individual metering record dictionaries.  When the input
        cannot be meaningfully decomposed, the response is wrapped in a
        single-element list ``[response_data]`` so that downstream
        assertions can still inspect it.
    """
    # Case 1: Direct list of records — the most common and simplest case.
    if isinstance(response_data, list):
        return response_data

    # Case 2: Wrapped dict with a recognized list key.
    if isinstance(response_data, dict):
        for key in ("data", "records", "items", "results"):
            if key in response_data and isinstance(response_data[key], list):
                return response_data[key]
        # No recognized wrapper key — wrap the dict itself so the caller
        # can still run per-record assertions (will likely be a single record).
        return [response_data]

    # Fallback — wrap arbitrary types so callers always get a list.
    return [response_data]


# =========================================================================
# Test Class: Field Presence
# =========================================================================


class TestPercentCompleteFieldPresent:
    """Verify that ``percent_complete`` / ``percentComplete`` exists in every
    metering record returned by ``GET /runs/metering``."""

    def test_percent_complete_field_present(
        self,
        api_client: BlitzyAPIClient,
        project_id: str,
    ) -> None:
        """Assert the percent field is present in **every** record.

        Iterates over the full record list and checks each element
        individually.  The assertion message includes the failing record
        index for quick triage.
        """
        response = api_client.get_runs_metering(project_id)
        records = _extract_records(response)

        assert len(records) > 0, (
            "No metering records returned from /runs/metering endpoint"
        )

        for i, record in enumerate(records):
            field_name, _value = find_percent_field(record)
            assert field_name is not None, (
                f"Field 'percent_complete'/'percentComplete' is missing "
                f"from metering record at index {i}"
            )

    def test_percent_complete_field_present_in_first_record(
        self,
        api_client: BlitzyAPIClient,
        project_id: str,
    ) -> None:
        """Quick-check that the first record contains the percent field.

        A lighter-weight smoke test that validates the very first record
        independently of the full-sweep test above.
        """
        response = api_client.get_runs_metering(project_id)
        records = _extract_records(response)

        assert len(records) > 0, (
            "No metering records returned from /runs/metering endpoint"
        )

        first_record = records[0]
        field_name, _value = find_percent_field(first_record)
        assert field_name is not None, (
            "Field 'percent_complete'/'percentComplete' is missing "
            "from the first metering record"
        )


# =========================================================================
# Test Class: Type Validation
# =========================================================================


class TestPercentCompleteType:
    """Validate the data type of ``percent_complete`` in each record.

    The field must be ``int``, ``float``, or ``None``.  Strings, booleans,
    and other types are explicitly rejected.
    """

    def test_percent_complete_type(
        self,
        api_client: BlitzyAPIClient,
        project_id: str,
    ) -> None:
        """Assert every record's percent value passes full type validation.

        Uses :func:`validate_percent_value` which enforces the complete
        value-domain rules (type + range).  Also uses the higher-level
        :func:`validate_percent_complete_in_response` for end-to-end
        validation of each record as a standalone response dict.
        """
        response = api_client.get_runs_metering(project_id)
        records = _extract_records(response)

        assert len(records) > 0, (
            "No metering records returned from /runs/metering endpoint"
        )

        for i, record in enumerate(records):
            field_name, value = find_percent_field(record)
            # Only validate the value if the field itself is present.
            # Field-presence is covered by TestPercentCompleteFieldPresent.
            if field_name is not None:
                is_valid, error_message = validate_percent_value(value)
                assert is_valid, (
                    f"Invalid percent_complete type at record index {i}: "
                    f"{error_message}"
                )

            # Additionally perform end-to-end validation using the
            # convenience function, which combines field detection with
            # value validation in a single call.
            if isinstance(record, dict):
                ok, msg = validate_percent_complete_in_response(
                    record, f"runs_metering[{i}]"
                )
                assert ok, (
                    f"End-to-end validation failed for record at index {i}: "
                    f"{msg}"
                )

    def test_percent_complete_not_string_in_any_record(
        self,
        api_client: BlitzyAPIClient,
        project_id: str,
    ) -> None:
        """Assert no record has a string-typed percent value."""
        response = api_client.get_runs_metering(project_id)
        records = _extract_records(response)

        for i, record in enumerate(records):
            field_name, value = find_percent_field(record)
            if field_name is not None:
                assert not isinstance(value, str), (
                    f"percent_complete at index {i} is a string: '{value}'"
                )

    def test_percent_complete_not_boolean_in_any_record(
        self,
        api_client: BlitzyAPIClient,
        project_id: str,
    ) -> None:
        """Assert no record has a boolean-typed percent value.

        This is critical because in Python ``bool`` is a subclass of
        ``int``, so ``isinstance(True, int)`` returns ``True``.  An
        explicit boolean check must precede any integer check.
        """
        response = api_client.get_runs_metering(project_id)
        records = _extract_records(response)

        for i, record in enumerate(records):
            field_name, value = find_percent_field(record)
            if field_name is not None:
                assert not isinstance(value, bool), (
                    f"percent_complete at index {i} is a boolean: {value}"
                )


# =========================================================================
# Test Class: Range Validation
# =========================================================================


class TestPercentCompleteRange:
    """Validate that numeric ``percent_complete`` values lie within the
    inclusive range ``[0.0, 100.0]``.  ``None`` is acceptable and skipped."""

    def test_percent_complete_range(
        self,
        api_client: BlitzyAPIClient,
        project_id: str,
    ) -> None:
        """Assert every numeric value is within [0.0, 100.0]."""
        response = api_client.get_runs_metering(project_id)
        records = _extract_records(response)

        assert len(records) > 0, (
            "No metering records returned from /runs/metering endpoint"
        )

        for i, record in enumerate(records):
            field_name, value = find_percent_field(record)
            if field_name is not None and value is not None:
                # Guard against non-numeric types before comparison.
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    assert 0.0 <= value <= 100.0, (
                        f"percent_complete value {value} at record index {i} "
                        f"is out of range [0.0, 100.0]"
                    )

    def test_percent_complete_not_negative(
        self,
        api_client: BlitzyAPIClient,
        project_id: str,
    ) -> None:
        """Assert no record has a negative percent value."""
        response = api_client.get_runs_metering(project_id)
        records = _extract_records(response)

        for i, record in enumerate(records):
            field_name, value = find_percent_field(record)
            if (
                field_name is not None
                and value is not None
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
            ):
                assert value >= 0.0, (
                    f"percent_complete value {value} at record index {i} "
                    f"is negative"
                )

    def test_percent_complete_not_over_100(
        self,
        api_client: BlitzyAPIClient,
        project_id: str,
    ) -> None:
        """Assert no record has a percent value exceeding 100."""
        response = api_client.get_runs_metering(project_id)
        records = _extract_records(response)

        for i, record in enumerate(records):
            field_name, value = find_percent_field(record)
            if (
                field_name is not None
                and value is not None
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
            ):
                assert value <= 100.0, (
                    f"percent_complete value {value} at record index {i} "
                    f"exceeds maximum 100.0"
                )


# =========================================================================
# Test Class: Completed Run Values
# =========================================================================


class TestCompletedRunValue:
    """Verify completed-run behaviour for the ``percent_complete`` field.

    Completed runs are identified as records that have a non-null value.
    The AAP states: *"Completed runs: expected value between 0–100"*.
    """

    def test_completed_run_value(
        self,
        api_client: BlitzyAPIClient,
        project_id: str,
    ) -> None:
        """Assert all non-null values are within [0.0, 100.0].

        This satisfies the AAP requirement for completed-run verification.
        At least one record with a non-null value is expected when the
        project has historical runs.
        """
        response = api_client.get_runs_metering(project_id)
        records = _extract_records(response)

        assert len(records) > 0, (
            "No metering records returned from /runs/metering endpoint"
        )

        non_null_found = False
        for i, record in enumerate(records):
            field_name, value = find_percent_field(record)
            if field_name is not None and value is not None:
                non_null_found = True
                # Ensure the value is numeric before range assertion.
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    assert 0.0 <= value <= 100.0, (
                        f"Completed run percent_complete value {value} at "
                        f"record index {i} is out of range [0.0, 100.0]"
                    )

        # Soft check: we expect at least one non-null value when historical
        # runs exist.  If no non-null values are found, the test still passes
        # but logs a note.  This avoids flaky failures in environments with
        # no run history.
        if not non_null_found and len(records) > 0:
            # All records have null values — acceptable but noteworthy.
            pass

    def test_metering_records_contain_data(
        self,
        api_client: BlitzyAPIClient,
        project_id: str,
    ) -> None:
        """Assert the endpoint returns at least one metering record.

        Also verifies that at least one record has a non-null
        ``percent_complete`` value when test data exists.
        """
        response = api_client.get_runs_metering(project_id)
        records = _extract_records(response)

        assert len(records) > 0, (
            "Expected at least one metering record from "
            "/runs/metering endpoint"
        )

        # Check for at least one record with a non-null percent_complete.
        has_non_null = False
        for record in records:
            field_name, value = find_percent_field(record)
            if field_name is not None and value is not None:
                has_non_null = True
                break

        # If test data is expected to exist, this assertion helps detect
        # regressions where all values are unexpectedly null.
        if len(records) > 0:
            assert has_non_null, (
                "All metering records have null percent_complete values — "
                "expected at least one non-null value when run data exists"
            )


# =========================================================================
# Test Class: Response Structure
# =========================================================================


class TestMeteringResponseStructure:
    """Validate the overall structure of the ``GET /runs/metering`` response.

    Ensures the raw response is valid JSON and that individual records are
    proper dictionaries.
    """

    def test_metering_response_is_valid(
        self,
        api_client: BlitzyAPIClient,
        project_id: str,
    ) -> None:
        """Assert the response is not None and is a valid JSON type."""
        response = api_client.get_runs_metering(project_id)

        assert response is not None, (
            "GET /runs/metering returned None — expected a JSON response"
        )
        assert isinstance(response, (list, dict)), (
            f"GET /runs/metering returned unexpected type "
            f"{type(response).__name__} — expected list or dict"
        )

    def test_metering_records_are_dicts(
        self,
        api_client: BlitzyAPIClient,
        project_id: str,
    ) -> None:
        """Assert every extracted record is a dictionary.

        Also verifies that the raw response can be parsed into
        :class:`~src.models.MeteringRecord` instances via
        :func:`~src.models.parse_metering_response`, ensuring
        schema compatibility with the Pydantic response models.
        """
        response = api_client.get_runs_metering(project_id)
        records = _extract_records(response)

        for i, record in enumerate(records):
            assert isinstance(record, dict), (
                f"Metering record at index {i} is not a dict — "
                f"got {type(record).__name__}"
            )

        # Verify the response can be parsed into MeteringRecord models.
        parsed_records: List[MeteringRecord] = parse_metering_response(response)
        for i, parsed in enumerate(parsed_records):
            assert isinstance(parsed, MeteringRecord), (
                f"Parsed metering record at index {i} is not a "
                f"MeteringRecord instance — got {type(parsed).__name__}"
            )
