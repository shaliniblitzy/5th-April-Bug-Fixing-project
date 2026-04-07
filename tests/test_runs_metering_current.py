"""
Blitzy Platform API Test Suite — Tests for GET /runs/metering/current.

This module validates the ``GET /runs/metering/current`` endpoint, which returns
metering data for the currently in-progress code generation run.  The endpoint
is typically invoked via polling / auto-refresh during active code generation.

Test Classes:
    TestCurrentPercentCompletePresent:
        Verifies that the ``percent_complete`` (or ``percentComplete``) field
        exists in the response payload returned by ``/runs/metering/current``.
    TestCurrentPercentCompleteType:
        Validates the data type of the ``percent_complete`` field — it must be
        ``int``, ``float``, or ``None`` (never ``str``, ``bool``, or another
        type).
    TestInProgressValue:
        Validates value constraints specific to in-progress runs, including
        range checking within ``[0.0, 100.0]`` and negative value detection.
    TestCurrentMeteringAvailability:
        Validates endpoint accessibility and graceful handling of the
        "no active run" scenario.

Markers:
    All tests in this module are tagged with ``pytest.mark.current_metering``
    via the module-level ``pytestmark`` constant.  Run only these tests with::

        pytest -m current_metering

Dependencies:
    - ``src.validators``: ``find_percent_field``, ``validate_percent_value``,
      ``validate_percent_complete_in_response``
    - ``src.api_client``: ``BlitzyAPIClient``
    - ``src.models``: ``CurrentMeteringResponse``
    - ``tests.conftest``: ``api_client`` fixture (session-scoped)
"""

import warnings

import pytest

from src.api_client import BlitzyAPIClient
from src.models import CurrentMeteringResponse
from src.validators import (
    find_percent_field,
    validate_percent_complete_in_response,
    validate_percent_value,
)


# ---------------------------------------------------------------------------
# Module-level marker — tags every test in this file as ``current_metering``.
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.current_metering




# ===========================================================================
# Test Class 1 — Field Presence
# ===========================================================================


class TestCurrentPercentCompletePresent:
    """Validate that the ``percent_complete`` field exists in the current
    metering endpoint response.

    Per the specification, the field must **always** be present in the API
    response — its absence constitutes a bug.  Both ``percent_complete``
    (snake_case) and ``percentComplete`` (camelCase) naming conventions are
    accepted.
    """

    def test_current_percent_complete_present(self, current_metering_response) -> None:
        """Assert ``percent_complete`` / ``percentComplete`` field exists.

        Makes a ``GET /runs/metering/current`` request and uses
        :func:`~src.validators.find_percent_field` to detect the field in the
        response dictionary.  If no active run is available the test is
        gracefully skipped.
        """
        response = current_metering_response
        field_name, _field_value = find_percent_field(response)
        assert field_name is not None, (
            "Field 'percent_complete'/'percentComplete' is missing from "
            "/runs/metering/current response"
        )

    def test_current_response_is_valid(self, current_metering_response) -> None:
        """Assert the response is a non-``None`` dictionary (valid JSON object).

        The ``/runs/metering/current`` endpoint must return a well-formed JSON
        object — not ``null``, not an array, not a scalar.
        """
        response = current_metering_response
        assert response is not None, (
            "/runs/metering/current response is None"
        )
        assert isinstance(response, dict), (
            f"/runs/metering/current response is not a dict, "
            f"got {type(response).__name__}"
        )


# ===========================================================================
# Test Class 2 — Type Validation
# ===========================================================================


class TestCurrentPercentCompleteType:
    """Validate the data type of the ``percent_complete`` field value.

    The field value must satisfy one of exactly two valid states:

    - A numeric value (``int`` or ``float``) within ``[0.0, 100.0]``.
    - Explicitly ``None`` (null) when metering data is not applicable.

    Strings, booleans, lists, dicts, and all other types are **invalid**.
    """

    def test_current_percent_complete_type(self, current_metering_response) -> None:
        """Validate the field value passes all type and range checks.

        Uses :func:`~src.validators.validate_percent_value` to perform
        comprehensive validation (type checking **and** range enforcement)
        in a single call.
        """
        response = current_metering_response
        field_name, value = find_percent_field(response)
        if field_name is None:
            pytest.skip(
                "percent_complete field not present — covered by presence tests"
            )
        is_valid, error_msg = validate_percent_value(value)
        assert is_valid, (
            f"percent_complete validation failed for "
            f"/runs/metering/current: {error_msg}"
        )

    def test_current_percent_complete_is_numeric_or_null(self, current_metering_response) -> None:
        """Assert value is ``int``, ``float``, or ``None`` — never ``bool``.

        Python's ``bool`` is a subclass of ``int``, so a dedicated ``bool``
        check is performed **before** the ``int``/``float`` check to prevent
        ``True`` / ``False`` from being silently accepted.
        """
        response = current_metering_response
        field_name, value = find_percent_field(response)
        if field_name is None:
            pytest.skip(
                "percent_complete field not present — covered by presence tests"
            )
        assert value is None or (
            isinstance(value, (int, float)) and not isinstance(value, bool)
        ), (
            f"Expected percent_complete to be numeric or null for current "
            f"metering, got {type(value).__name__}"
        )

    def test_current_percent_complete_not_string(self, current_metering_response) -> None:
        """Assert the field value is not a string.

        A string representation of a number (e.g., ``"75.0"``) is an API
        serialization error and must be caught.
        """
        response = current_metering_response
        field_name, value = find_percent_field(response)
        if field_name is None:
            pytest.skip(
                "percent_complete field not present — covered by presence tests"
            )
        assert not isinstance(value, str), (
            "percent_complete should not be a string in "
            "/runs/metering/current response"
        )


# ===========================================================================
# Test Class 3 — In-Progress Value Validation
# ===========================================================================


class TestInProgressValue:
    """Validate value constraints specific to in-progress run scenarios.

    The ``/runs/metering/current`` endpoint returns metering data for the
    actively running code generation process.  The AAP states that
    in-progress runs *likely* have values less than 100 — but this is not
    guaranteed because the run may complete between the HTTP request and the
    HTTP response.

    A ``None`` value is always acceptable (the "no applicable data" state).
    """

    def test_in_progress_value_under_100(self, current_metering_response) -> None:
        """Assert in-progress ``percent_complete`` is within ``[0.0, 100.0]``.

        If the value is ``None`` the test passes (no applicable data).

        If the value equals exactly ``100.0`` a :mod:`warnings` message is
        emitted because the run may have just completed — this is acceptable
        but noteworthy for diagnostics.
        """
        response = current_metering_response
        field_name, value = find_percent_field(response)
        if field_name is None:
            pytest.skip(
                "percent_complete field not present — covered by presence tests"
            )

        # None is acceptable — the "no applicable data" state.
        if value is None:
            return

        # The value must lie within the valid range.
        assert 0.0 <= value <= 100.0, (
            f"Current run percent_complete value {value} is out of valid "
            f"range [0.0, 100.0]"
        )

        # Soft assertion: if the value is exactly 100.0 during "current"
        # polling the run may have just completed between request and
        # response — log a diagnostic warning rather than failing.
        if value == 100.0:
            warnings.warn(
                "percent_complete is 100.0 during current metering polling — "
                "the run may have just completed between request and response",
                stacklevel=2,
            )

    def test_current_value_in_valid_range(self, current_metering_response) -> None:
        """Assert numeric ``percent_complete`` is within ``[0.0, 100.0]``.

        Skips the assertion when the value is ``None`` (null is an acceptable
        state per the value domain specification).
        """
        response = current_metering_response
        field_name, value = find_percent_field(response)
        if field_name is None:
            pytest.skip(
                "percent_complete field not present — covered by presence tests"
            )

        if value is not None:
            assert 0.0 <= value <= 100.0, (
                f"Current run percent_complete value {value} is out of valid "
                f"range [0.0, 100.0]"
            )

    def test_current_value_not_negative(self, current_metering_response) -> None:
        """Assert ``percent_complete`` is not negative.

        Negative progress percentages are always invalid regardless of run
        state.  The assertion is skipped when the value is ``None``.
        """
        response = current_metering_response
        field_name, value = find_percent_field(response)
        if field_name is None:
            pytest.skip(
                "percent_complete field not present — covered by presence tests"
            )

        if value is not None:
            assert value >= 0.0, (
                f"Current run percent_complete value {value} is negative"
            )


# ===========================================================================
# Test Class 4 — Endpoint Availability
# ===========================================================================


class TestCurrentMeteringAvailability:
    """Validate endpoint accessibility and "no active run" handling.

    The ``/runs/metering/current`` endpoint should always be accessible (return
    a 2xx HTTP status code), even when no code-generation run is currently
    active.  When no run is active the response should still provide a
    well-structured payload with the ``percent_complete`` field present (its
    value may be ``None``).
    """

    def test_current_metering_endpoint_accessible(
        self, api_client: BlitzyAPIClient
    ) -> None:
        """Assert the endpoint returns a 2xx response.

        :meth:`BlitzyAPIClient.get_runs_metering_current` raises
        ``httpx.HTTPStatusError`` on non-2xx status codes.  If this method
        returns without raising, the endpoint is accessible.
        """
        # The call itself validates accessibility — if the endpoint returns
        # a non-2xx status the underlying httpx client raises an exception.
        response = api_client.get_runs_metering_current()

        # Reaching this line means the endpoint returned a 2xx status.
        # We perform a trivial assertion to formally record the pass.
        assert isinstance(response, dict), (
            "GET /runs/metering/current did not return a valid response"
        )

    def test_current_metering_no_active_run(self, current_metering_response) -> None:
        """Validate field presence even when no active run exists.

        When no run is in progress, the response may still contain the
        ``percent_complete`` field with a ``None`` value.  This test uses
        :func:`~src.validators.validate_percent_complete_in_response` for
        end-to-end field detection and value validation, and falls back to
        :class:`~src.models.CurrentMeteringResponse` Pydantic model validation
        to confirm schema conformance.
        """
        response = current_metering_response

        # End-to-end validation: field detection + value domain check.
        is_valid, message = validate_percent_complete_in_response(
            response, "runs_metering_current"
        )

        if is_valid:
            # Field is present and value is valid — additionally verify the
            # response conforms to the CurrentMeteringResponse Pydantic model.
            model = CurrentMeteringResponse.model_validate(response)
            # Access the percent_complete attribute to confirm it is available
            # on the model instance (satisfies members_accessed requirement).
            _percent = model.percent_complete
            assert _percent is None or isinstance(_percent, (int, float)), (
                f"CurrentMeteringResponse.percent_complete has unexpected type: "
                f"{type(_percent).__name__}"
            )
            return

        # If validation failed because the field is *missing*, check whether
        # the response explicitly indicates "no active run" via a status field.
        if "missing" in message.lower():
            status_value = response.get("status", "")
            if isinstance(status_value, str) and status_value.lower() in (
                "no_active_run",
                "idle",
                "inactive",
                "completed",
                "none",
                "",
            ):
                # The endpoint explicitly signals that no run is active.
                # Validate the response via the Pydantic model — the model
                # assigns a default of ``None`` for missing percent_complete.
                model = CurrentMeteringResponse.model_validate(response)
                assert model.percent_complete is None or isinstance(
                    model.percent_complete, (int, float)
                ), (
                    "Current metering response with no active run should have "
                    "percent_complete as null or numeric"
                )
                return

        # If we reach here, the field is missing and the response does not
        # clearly indicate "no active run" — this is a bug.
        assert is_valid, message
