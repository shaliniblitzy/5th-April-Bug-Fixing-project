"""
Blitzy Platform API Test Suite — GET /project Inline Metering Tests.

Validates the ``GET /project?id=xxx`` endpoint response, which returns project
data with inline/nested metering information embedded in the response body.
The ``percent_complete`` field resides within a nested metering structure
(commonly under a ``"metering"``, ``"meteringData"``, or ``"metering_data"``
key).

Test Classes:
    TestProjectHasMeteringData:
        Verifies that the project response contains a metering data section
        and that the response is a well-formed JSON object.
    TestProjectPercentCompletePresent:
        Asserts that the ``percent_complete`` / ``percentComplete`` field
        exists within the nested metering data of the project response.
    TestProjectPercentCompleteValid:
        Validates that the field value conforms to the strict value domain:
        numeric (int/float) within [0.0, 100.0] or explicitly ``None``.
    TestProjectMeteringScenarios:
        Covers scenario-based testing for completed runs and no-data states.

Markers:
    All tests in this module are tagged with ``pytest.mark.project`` for
    selective execution (e.g., ``pytest -m project``).

Fixtures Used (from ``tests/conftest.py`` — auto-discovered by pytest):
    project_response:
        Session-scoped cached response from the ``GET /project`` endpoint.
"""

import pytest

from src.validators import (
    find_percent_field,
    find_percent_field_nested,
    validate_percent_value,
    validate_percent_complete_in_response,
)
from src.models import ProjectResponse, InlineMeteringData


# ---------------------------------------------------------------------------
# Module-level pytest marker — tags every test in this file as "project".
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.project

# ---------------------------------------------------------------------------
# Internal constants used by multiple test classes for metering key lookup.
# ---------------------------------------------------------------------------

_METERING_KEYS: list[str] = ["metering", "meteringData", "metering_data"]
"""Common dictionary keys under which inline metering data may be nested
within the ``/project`` response body."""


# ===========================================================================
# Test Class: TestProjectHasMeteringData
# ===========================================================================


class TestProjectHasMeteringData:
    """Tests that the ``GET /project`` response contains a metering data section.

    The project endpoint embeds metering information inside the response body
    under a nested key (e.g., ``"metering"`` or ``"meteringData"``).  These
    tests verify the structural prerequisite before any field-level assertions
    are made.
    """

    def test_project_has_metering_data(self, project_response) -> None:
        """Assert that the project response contains a metering data section.

        Issues ``GET /project?id=<project_id>`` and checks that at least one
        of the well-known metering keys (``"metering"``, ``"meteringData"``,
        ``"metering_data"``) is present in the response body.  If the metering
        data is found at the top level **or** under a ``"data"`` wrapper, the
        test passes.

        Args:
            project_response: Session-scoped cached response from
                the ``GET /project`` endpoint fixture.
        """
        response = project_response

        assert response is not None, (
            "Project response is None — the API returned no data"
        )
        assert isinstance(response, dict), (
            f"Expected dict response from /project, got {type(response).__name__}"
        )

        # Check for metering data at the top level first.
        has_metering: bool = any(
            key in response for key in _METERING_KEYS
        )

        # If not at the top level, check inside a "data" wrapper.
        if not has_metering and isinstance(response.get("data"), dict):
            data_section: dict = response["data"]
            has_metering = any(
                key in data_section for key in _METERING_KEYS
            )

        # As a fallback, use find_percent_field_nested which searches both
        # the top level and the metering sub-keys.  If it finds the percent
        # field anywhere, the response contains metering data.
        if not has_metering:
            field_name, _value, _path = find_percent_field_nested(response)
            has_metering = field_name is not None

        assert has_metering, (
            "Project response does not contain metering data section. "
            f"Searched for keys: {_METERING_KEYS} at top level and under 'data'. "
            f"Response keys: {list(response.keys())}"
        )

        # Additionally, validate that the discovered metering section can be
        # parsed into an InlineMeteringData model when it is a dict.
        for key in _METERING_KEYS:
            section = response.get(key)
            if isinstance(section, dict):
                metering_model: InlineMeteringData = (
                    InlineMeteringData.model_validate(section)
                )
                assert metering_model is not None, (
                    f"Metering section under '{key}' could not be parsed "
                    "into InlineMeteringData model"
                )
                break

    def test_project_response_is_valid_json(self, project_response) -> None:
        """Assert that the project response is a valid, non-empty JSON object.

        Verifies the response from ``GET /project?id=<project_id>`` is not
        ``None``, is a Python ``dict`` (i.e., parsed JSON object), and can be
        parsed into a :class:`~src.models.ProjectResponse` Pydantic model.

        Args:
            project_response: Session-scoped cached response from
                the ``GET /project`` endpoint fixture.
        """
        response = project_response

        assert response is not None, (
            "GET /project returned None — expected a JSON object"
        )
        assert isinstance(response, dict), (
            f"GET /project response is not a JSON object (dict), "
            f"got {type(response).__name__}"
        )

        # Validate the response can be parsed into the ProjectResponse model.
        # Pydantic will accept the dict thanks to extra="allow" config.
        parsed: ProjectResponse = ProjectResponse.model_validate(response)
        assert parsed is not None, (
            "Failed to parse project response into ProjectResponse model"
        )


# ===========================================================================
# Test Class: TestProjectPercentCompletePresent
# ===========================================================================


class TestProjectPercentCompletePresent:
    """Tests that ``percent_complete`` / ``percentComplete`` exists in the
    nested metering data of the ``/project`` response.

    Per the specification, this field must **always** be present — its absence
    constitutes a bug.
    """

    def test_project_percent_complete_present(self, project_response) -> None:
        """Assert that the percent_complete field exists within nested metering data.

        Uses :func:`find_percent_field_nested` to search the entire project
        response (top level and nested metering sub-keys) for the field.

        Args:
            project_response: Session-scoped cached response from
                the ``GET /project`` endpoint fixture.
        """
        response = project_response

        field_name, _field_value, _nested_path = find_percent_field_nested(
            response
        )

        assert field_name is not None, (
            "Field 'percent_complete'/'percentComplete' is missing from "
            "project inline metering data. "
            f"Response keys: {list(response.keys()) if isinstance(response, dict) else 'N/A'}"
        )

    def test_project_percent_complete_key_detected(self, project_response) -> None:
        """Assert that the detected field name is a recognised naming convention.

        Navigates to the metering section of the project response and verifies
        that the field is named either ``"percent_complete"`` (snake_case) or
        ``"percentComplete"`` (camelCase).  This aids cross-endpoint
        consistency checking by logging which convention the ``/project``
        endpoint uses.

        Args:
            project_response: Session-scoped cached response from
                the ``GET /project`` endpoint fixture.
        """
        response = project_response

        # First, try to locate the metering section and search within it.
        metering_section: dict | None = None
        for key in _METERING_KEYS:
            if key in response and isinstance(response[key], dict):
                metering_section = response[key]
                break

        # If a metering section was found, check directly within it.
        if metering_section is not None:
            field_name, _value = find_percent_field(metering_section)
        else:
            # Fallback to nested search across the full response.
            field_name, _value, _path = find_percent_field_nested(response)

        assert field_name is not None, (
            "Could not detect percent_complete field name in the project "
            "metering section — field is missing entirely"
        )
        assert field_name in ("percent_complete", "percentComplete"), (
            f"Unexpected field name detected: '{field_name}'. "
            "Expected 'percent_complete' or 'percentComplete'"
        )


# ===========================================================================
# Test Class: TestProjectPercentCompleteValid
# ===========================================================================


class TestProjectPercentCompleteValid:
    """Tests that validate the type and range of the nested ``percent_complete``
    field within the ``/project`` response.

    The value domain is strictly:
    - ``int`` or ``float`` within the inclusive range ``[0.0, 100.0]``, or
    - ``None`` when metering data is not applicable.
    """

    def test_project_percent_complete_valid(self, project_response) -> None:
        """End-to-end validation of the percent_complete field in the project response.

        Delegates to :func:`validate_percent_complete_in_response` which
        performs field detection (including nested search) and value validation
        in a single call.

        Args:
            project_response: Session-scoped cached response from
                the ``GET /project`` endpoint fixture.
        """
        response = project_response

        is_valid, error_message = validate_percent_complete_in_response(
            response, "project"
        )

        assert is_valid, (
            f"percent_complete validation failed for /project endpoint: "
            f"{error_message}"
        )

    def test_project_percent_complete_type_is_numeric_or_null(self, project_response) -> None:
        """Assert that the percent_complete value is numeric (int/float) or None.

        Boolean values are explicitly rejected even though ``bool`` is a
        subclass of ``int`` in Python.

        Args:
            project_response: Session-scoped cached response from
                the ``GET /project`` endpoint fixture.
        """
        response = project_response

        field_name, field_value, _nested_path = find_percent_field_nested(
            response
        )

        # If the field is missing, a separate test covers that case.
        # Here we validate the type only when the field is present.
        if field_name is None:
            pytest.skip(
                "percent_complete field not found in project response — "
                "field presence is validated by a separate test"
            )

        assert field_value is None or (
            isinstance(field_value, (int, float))
            and not isinstance(field_value, bool)
        ), (
            f"Expected percent_complete to be numeric or null, "
            f"got {type(field_value).__name__}: {field_value!r}"
        )

    def test_project_percent_complete_in_range(self, project_response) -> None:
        """Assert that a numeric percent_complete value is within [0.0, 100.0].

        If the value is ``None`` (no applicable data), the test passes without
        range assertions.

        Args:
            project_response: Session-scoped cached response from
                the ``GET /project`` endpoint fixture.
        """
        response = project_response

        field_name, field_value, _nested_path = find_percent_field_nested(
            response
        )

        if field_name is None:
            pytest.skip(
                "percent_complete field not found — "
                "field presence is validated by a separate test"
            )

        # None is an acceptable value (no applicable metering data).
        if field_value is None:
            return

        # At this point the value should be numeric.  Validate the range.
        assert isinstance(field_value, (int, float)) and not isinstance(
            field_value, bool
        ), (
            f"Cannot check range — percent_complete is not numeric: "
            f"{type(field_value).__name__}"
        )

        assert 0.0 <= field_value <= 100.0, (
            f"percent_complete value {field_value} is out of valid range "
            f"[0.0, 100.0]"
        )


# ===========================================================================
# Test Class: TestProjectMeteringScenarios
# ===========================================================================


class TestProjectMeteringScenarios:
    """Scenario-based tests covering different project / run states.

    The ``GET /project`` endpoint may return metering data for:
    - **Completed runs**: Numeric value between 0–100 (often exactly 100.0).
    - **No applicable data**: ``None`` (null) — the field is still present.
    """

    def test_project_completed_run_metering(self, project_response) -> None:
        """Verify that a completed run has a valid percent_complete value.

        Fetches the project response and extracts the ``percent_complete``
        value from nested metering data.  If the value is not ``None``
        (indicating a completed or active run), asserts that the value falls
        within the valid range ``[0.0, 100.0]``.

        Args:
            project_response: Session-scoped cached response from
                the ``GET /project`` endpoint fixture.
        """
        response = project_response

        field_name, field_value, _nested_path = find_percent_field_nested(
            response
        )

        if field_name is None:
            pytest.skip(
                "percent_complete field not found — cannot validate "
                "completed-run scenario"
            )

        if field_value is None:
            # No metering data available for this project — the no-data
            # scenario is covered by a separate test.
            pytest.skip(
                "percent_complete is null — project has no completed-run "
                "metering data; skipping completed-run assertion"
            )

        # The value exists and is non-null: validate it.
        is_valid, error_message = validate_percent_value(field_value)
        assert is_valid, (
            f"Completed-run metering validation failed for /project endpoint: "
            f"{error_message}"
        )

        # For completed runs the value is expected to be between 0 and 100.
        assert 0.0 <= field_value <= 100.0, (
            f"Completed-run percent_complete value {field_value} is outside "
            f"valid range [0.0, 100.0]"
        )

    def test_project_no_data_scenario(self, project_response) -> None:
        """Verify the no-data scenario: field is present with a null value.

        When metering data is not applicable, the ``percent_complete`` field
        must still be **present** in the response — its value should be
        ``None`` (null).  Field absence is always a bug.

        If the current project has a non-null value, this test is skipped
        (the completed-run scenario is tested separately).

        Args:
            project_response: Session-scoped cached response from
                the ``GET /project`` endpoint fixture.
        """
        response = project_response

        field_name, field_value, nested_path = find_percent_field_nested(
            response
        )

        # Regardless of the value, the field key must exist.
        assert field_name is not None, (
            "Field 'percent_complete'/'percentComplete' is entirely missing "
            "from the project response — the field must always be present, "
            "even when the value is null"
        )

        if field_value is not None:
            # This project has active metering data — the no-data scenario
            # does not apply; skip this test gracefully.
            pytest.skip(
                f"percent_complete has a non-null value ({field_value}) — "
                "this project does not represent the no-data scenario"
            )

        # Value is None — verify through the validator that this is accepted.
        is_valid, error_message = validate_percent_value(field_value)
        assert is_valid, (
            f"Null percent_complete should be accepted as valid but "
            f"validation failed: {error_message}"
        )
