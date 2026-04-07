"""
Blitzy Platform API Test Suite — Cross-Endpoint Consistency Tests.

Validates that the ``percent_complete`` field naming convention and schema are
**uniform** across all three Blitzy Platform API endpoints:

- ``GET /runs/metering``          — Metering data for multiple code-generation runs
- ``GET /runs/metering/current``  — Metering data for the currently in-progress run
- ``GET /project``                — Project detail with inline (nested) metering data

Consistency rules enforced by this module:

1. **Field naming** — All endpoints must use the same convention for the
   percent-complete key, either ``percent_complete`` (snake_case) everywhere or
   ``percentComplete`` (camelCase) everywhere.  A mix of conventions across
   endpoints is flagged as a potential API inconsistency.

2. **Field presence** — The field must exist in the responses from *all three*
   endpoints.  Absence in any endpoint constitutes a bug per the specification.

3. **Value type uniformity** — Every non-null value must be numeric
   (``int`` or ``float``).  No endpoint should return a ``str``, ``bool``,
   ``list``, or any other type for this field.

4. **Value validation** — Each individual value must satisfy the allowed domain:
   numeric within ``[0.0, 100.0]`` **or** explicitly ``None`` (null).

Test organisation:

- :class:`TestFieldNameConsistency` — Integration tests that call all three
  endpoints and assert field naming consistency.
- :class:`TestSchemaUniformity` — Integration tests that validate value types
  are consistent and individually valid across all endpoints.
- :class:`TestCrossEndpointWithMockData` — Pure unit tests that exercise the
  :func:`~src.validators.check_field_consistency` logic with mock data,
  requiring no network access.
"""

from typing import Any, Dict, List, Optional, Tuple

import pytest

from src.api_client import BlitzyAPIClient
from src.validators import (
    check_field_consistency,
    find_percent_field,
    find_percent_field_nested,
    validate_percent_value,
)


# ---------------------------------------------------------------------------
# Module-level pytest marker — allows ``pytest -m consistency`` filtering
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.consistency


# ---------------------------------------------------------------------------
# Private helper
# ---------------------------------------------------------------------------


def _extract_first_record(response_data: Any) -> Optional[Dict[str, Any]]:
    """Return a single representative record from a potentially list-based response.

    The ``/runs/metering`` endpoint may return either:

    * A bare JSON array of metering records: ``[{…}, {…}, …]``
    * A wrapper object with a data/records key:
      ``{"data": [{…}, {…}]}`` or ``{"records": [{…}, {…}]}``.

    This helper normalises both shapes into a single dictionary suitable for
    field-name detection.

    Args:
        response_data: The parsed JSON response body (list, dict, or other).

    Returns:
        The first record dictionary, or ``None`` when no record can be
        extracted (e.g. empty list, unexpected type).
    """
    if isinstance(response_data, list):
        return response_data[0] if response_data else None

    if isinstance(response_data, dict):
        # Check common wrapper keys used by paginated / envelope APIs.
        for key in ("data", "records", "items", "results"):
            nested = response_data.get(key)
            if isinstance(nested, list) and nested:
                return nested[0]
        # The dict itself may be the record.
        return response_data

    return None


# ============================================================================
# Integration Test Classes — require live API connectivity
# ============================================================================


class TestFieldNameConsistency:
    """Verify that the percent_complete field name is identical across all endpoints.

    These are integration tests that issue real GET requests via the
    ``api_client`` and ``project_id`` fixtures provided by
    ``tests/conftest.py``.
    """

    def test_field_name_consistency(
        self,
        api_client: BlitzyAPIClient,
        project_id: str,
    ) -> None:
        """Assert that all three endpoints use the **same** naming convention.

        Fetches responses from ``/runs/metering``, ``/runs/metering/current``,
        and ``/project``, then delegates to
        :func:`~src.validators.check_field_consistency` to compare the field
        name variants found in each response.

        A mismatch — e.g. ``percent_complete`` in one endpoint but
        ``percentComplete`` in another — causes an assertion failure with a
        detailed message identifying each endpoint's convention.
        """
        # 1. Fetch responses from all three endpoints.
        runs_metering_response: Any = api_client.get_runs_metering(project_id)
        current_metering_response: Dict[str, Any] = (
            api_client.get_runs_metering_current()
        )
        project_response: Dict[str, Any] = api_client.get_project(project_id)

        # 2. Normalise /runs/metering — may be a list; extract first record.
        runs_metering_record: Optional[Dict[str, Any]] = _extract_first_record(
            runs_metering_response,
        )
        assert runs_metering_record is not None, (
            "Cannot verify field naming: /runs/metering returned no records. "
            "Ensure the target project has at least one historical run."
        )

        # 3. Build the responses dict expected by check_field_consistency.
        #    The consistency checker uses find_percent_field_nested internally
        #    so it will handle the /project endpoint's nested metering structure.
        responses: Dict[str, dict] = {
            "/runs/metering": runs_metering_record,
            "/runs/metering/current": current_metering_response,
            "/project": project_response,
        }

        is_consistent, message = check_field_consistency(responses)

        assert is_consistent, (
            f"Field naming is inconsistent across endpoints: {message}"
        )

    def test_field_present_in_all_endpoints(
        self,
        api_client: BlitzyAPIClient,
        project_id: str,
    ) -> None:
        """Assert that the percent_complete field exists in every endpoint.

        The specification mandates that the field must *always* be present —
        even when its value is ``null``.  Absence in any of the three
        endpoint responses is flagged as a bug.
        """
        # 1. Fetch responses.
        runs_metering_response: Any = api_client.get_runs_metering(project_id)
        current_metering_response: Dict[str, Any] = (
            api_client.get_runs_metering_current()
        )
        project_response: Dict[str, Any] = api_client.get_project(project_id)

        # 2. Check /runs/metering — extract a representative record first.
        runs_record: Optional[Dict[str, Any]] = _extract_first_record(
            runs_metering_response,
        )
        assert runs_record is not None, (
            "No metering records returned from /runs/metering"
        )
        field_name_metering, _value_metering = find_percent_field(runs_record)
        assert field_name_metering is not None, (
            "Field 'percent_complete'/'percentComplete' missing from /runs/metering"
        )

        # 3. Check /runs/metering/current — flat dict lookup.
        field_name_current, _value_current = find_percent_field(
            current_metering_response,
        )
        assert field_name_current is not None, (
            "Field 'percent_complete'/'percentComplete' missing from "
            "/runs/metering/current"
        )

        # 4. Check /project — use nested search for inline metering data.
        field_name_project, _value_project, _nested_path = (
            find_percent_field_nested(project_response)
        )
        assert field_name_project is not None, (
            "Field 'percent_complete'/'percentComplete' missing from /project "
            "(searched top-level and nested metering structures)"
        )


class TestSchemaUniformity:
    """Verify that the percent_complete value type and domain are consistent.

    Integration tests that fetch responses from all three endpoints and
    validate that each ``percent_complete`` value individually passes
    domain validation and that non-null values are consistently numeric.
    """

    def test_schema_uniformity(
        self,
        api_client: BlitzyAPIClient,
        project_id: str,
    ) -> None:
        """Assert every endpoint's percent_complete value passes domain validation.

        For each endpoint:

        1. Extract the ``percent_complete`` value.
        2. Call :func:`~src.validators.validate_percent_value` to assert the
           value is either ``None`` or a numeric within ``[0.0, 100.0]``.
        3. If any value fails validation the test provides a clear,
           per-endpoint error message.

        Type-category consistency is also verified:
        - Numeric and ``None`` values may coexist (different run states).
        - A string in one endpoint alongside a number in another indicates
          a schema inconsistency and fails the test.
        """
        # 1. Fetch responses from all three endpoints.
        runs_metering_response: Any = api_client.get_runs_metering(project_id)
        current_metering_response: Dict[str, Any] = (
            api_client.get_runs_metering_current()
        )
        project_response: Dict[str, Any] = api_client.get_project(project_id)

        # 2. Extract the percent_complete value from each endpoint.
        endpoint_values: Dict[str, Tuple[Optional[str], Any]] = {}

        # /runs/metering — extract first record.
        runs_record: Optional[Dict[str, Any]] = _extract_first_record(
            runs_metering_response,
        )
        assert runs_record is not None, (
            "No metering records returned from /runs/metering endpoint"
        )
        endpoint_values["/runs/metering"] = find_percent_field(runs_record)

        # /runs/metering/current — direct lookup.
        endpoint_values["/runs/metering/current"] = find_percent_field(
            current_metering_response,
        )

        # /project — nested lookup; take first two elements of the 3-tuple.
        proj_field_name, proj_value, _nested_path = find_percent_field_nested(
            project_response,
        )
        endpoint_values["/project"] = (proj_field_name, proj_value)

        # 3. Validate each value individually.
        validation_failures: List[str] = []
        for endpoint_name, (field_name, value) in endpoint_values.items():
            if field_name is None:
                validation_failures.append(
                    f"{endpoint_name}: field is missing entirely"
                )
                continue
            is_valid, error_msg = validate_percent_value(value)
            if not is_valid:
                validation_failures.append(
                    f"{endpoint_name} ({field_name}={value!r}): {error_msg}"
                )

        assert not validation_failures, (
            "Schema validation failures detected across endpoints:\n"
            + "\n".join(f"  - {f}" for f in validation_failures)
        )

    def test_value_type_consistency(
        self,
        api_client: BlitzyAPIClient,
        project_id: str,
    ) -> None:
        """Assert that non-null percent_complete values are strictly numeric.

        For each endpoint response:

        * ``None`` is always acceptable (the "no applicable data" scenario).
        * If the value is non-null it **must** be ``int`` or ``float``.
        * ``bool`` is explicitly rejected (``bool`` is a subclass of ``int``
          in Python, so we check for it first).
        * ``str``, ``list``, ``dict``, and all other types are rejected.
        """
        # 1. Fetch responses.
        runs_metering_response: Any = api_client.get_runs_metering(project_id)
        current_metering_response: Dict[str, Any] = (
            api_client.get_runs_metering_current()
        )
        project_response: Dict[str, Any] = api_client.get_project(project_id)

        # 2. Build a mapping of endpoint → extracted value.
        values_by_endpoint: Dict[str, Any] = {}

        runs_record = _extract_first_record(runs_metering_response)
        if runs_record is not None:
            _fname, value = find_percent_field(runs_record)
            values_by_endpoint["/runs/metering"] = value
        else:
            values_by_endpoint["/runs/metering"] = None

        _fname, value = find_percent_field(current_metering_response)
        values_by_endpoint["/runs/metering/current"] = value

        _fname, value, _path = find_percent_field_nested(project_response)
        values_by_endpoint["/project"] = value

        # 3. Assert each non-null value is numeric (not bool).
        type_failures: List[str] = []
        for endpoint_name, val in values_by_endpoint.items():
            if val is None:
                # None is acceptable for any endpoint.
                continue
            if isinstance(val, bool):
                type_failures.append(
                    f"{endpoint_name}: got bool ({val!r}), expected numeric or null"
                )
            elif not isinstance(val, (int, float)):
                type_failures.append(
                    f"{endpoint_name}: got {type(val).__name__} ({val!r}), "
                    f"expected numeric or null"
                )

        assert not type_failures, (
            "Value type inconsistencies detected across endpoints:\n"
            + "\n".join(f"  - {f}" for f in type_failures)
        )


# ============================================================================
# Unit Test Class — mock data, no network access required
# ============================================================================


class TestCrossEndpointWithMockData:
    """Verify :func:`~src.validators.check_field_consistency` with mock payloads.

    These tests exercise the consistency-checking logic deterministically
    without requiring live API connectivity.  They cover four scenarios:

    1. All endpoints use ``percent_complete`` (snake_case) — consistent.
    2. All endpoints use ``percentComplete`` (camelCase) — consistent.
    3. Endpoints use mixed conventions — inconsistent, must be detected.
    4. One endpoint is missing the field entirely — inconsistent / bug.
    """

    def test_consistent_snake_case(self) -> None:
        """All endpoints use ``percent_complete`` → consistency check passes."""
        responses: Dict[str, dict] = {
            "runs_metering": {"percent_complete": 50.0},
            "runs_metering_current": {"percent_complete": 75.0},
            "project": {"percent_complete": 100.0},
        }

        is_consistent, message = check_field_consistency(responses)

        assert is_consistent, (
            f"Expected consistent snake_case naming across all endpoints "
            f"but got: {message}"
        )
        assert "percent_complete" in message, (
            f"Expected message to reference 'percent_complete', got: {message}"
        )

    def test_consistent_camel_case(self) -> None:
        """All endpoints use ``percentComplete`` → consistency check passes."""
        responses: Dict[str, dict] = {
            "runs_metering": {"percentComplete": 50.0},
            "runs_metering_current": {"percentComplete": 75.0},
            "project": {"percentComplete": 100.0},
        }

        is_consistent, message = check_field_consistency(responses)

        assert is_consistent, (
            f"Expected consistent camelCase naming across all endpoints "
            f"but got: {message}"
        )
        assert "percentComplete" in message, (
            f"Expected message to reference 'percentComplete', got: {message}"
        )

    def test_inconsistent_naming(self) -> None:
        """Mixed naming conventions → consistency check must flag mismatch."""
        responses: Dict[str, dict] = {
            "runs_metering": {"percent_complete": 50.0},
            "runs_metering_current": {"percentComplete": 75.0},
            "project": {"percent_complete": 100.0},
        }

        is_consistent, message = check_field_consistency(responses)

        assert not is_consistent, (
            "Expected inconsistency to be detected when endpoints use "
            "mixed naming conventions (percent_complete vs percentComplete)"
        )
        # The message must clearly describe the mismatch.
        assert "mismatch" in message.lower(), (
            f"Expected 'mismatch' in error message, got: {message}"
        )
        # Verify the offending endpoint is identified.
        assert "runs_metering_current" in message, (
            f"Expected the inconsistent endpoint 'runs_metering_current' to be "
            f"identified in the error message, got: {message}"
        )

    def test_missing_field_in_one_endpoint(self) -> None:
        """One endpoint missing the field entirely → consistency check must fail."""
        responses: Dict[str, dict] = {
            "runs_metering": {"percent_complete": 50.0},
            "runs_metering_current": {"status": "running"},  # Missing!
            "project": {"percent_complete": 100.0},
        }

        is_consistent, message = check_field_consistency(responses)

        assert not is_consistent, (
            "Expected missing field to be detected when "
            "runs_metering_current lacks percent_complete/percentComplete"
        )
        assert "missing" in message.lower(), (
            f"Expected 'missing' in error message, got: {message}"
        )
        # The message must identify which endpoint is missing the field.
        assert "runs_metering_current" in message, (
            f"Expected the endpoint with the missing field "
            f"('runs_metering_current') to be identified, got: {message}"
        )
