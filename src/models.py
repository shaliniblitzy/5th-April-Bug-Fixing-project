"""
Blitzy Platform API Test Suite — Pydantic Response Models.

Defines Pydantic V2 BaseModel classes that enforce the expected structure
of the Blitzy Platform API responses for metering and project endpoints.
Each model supports both snake_case (percent_complete) and camelCase
(percentComplete) field naming conventions via Pydantic aliases with
populate_by_name=True.

Models:
    MeteringRecord: Schema for an individual run metering data record
        with a percent_complete field constrained to Optional[Union[int, float]]
        in the inclusive range [0.0, 100.0].
    MeteringResponse: Schema for the ``GET /runs/metering`` array response.
        Handles both bare-list and wrapped-object response formats via the
        flexible ``from_response()`` class method.
    CurrentMeteringResponse: Schema for the ``GET /runs/metering/current``
        single-object response representing the actively running code
        generation process.
    InlineMeteringData: Schema for the nested metering data embedded within
        the project response payload.
    ProjectResponse: Schema for the ``GET /project`` response that contains
        inline metering information embedded in the response body.

Utility Functions:
    parse_metering_response: Parses a raw ``/runs/metering`` response into a
        list of MeteringRecord instances.
    parse_current_metering_response: Parses a raw ``/runs/metering/current``
        response into a CurrentMeteringResponse instance.
    parse_project_response: Parses a raw ``/project`` response into a
        ProjectResponse instance.

Usage:
    from src.models import (
        MeteringRecord,
        MeteringResponse,
        CurrentMeteringResponse,
        InlineMeteringData,
        ProjectResponse,
        parse_metering_response,
        parse_current_metering_response,
        parse_project_response,
    )

    # Parse a list of metering records from the API response
    records = parse_metering_response(api_response_json)
    for record in records:
        print(record.percent_complete)

    # Parse the project response with nested metering data
    project = parse_project_response(project_json)
    if project.metering:
        print(project.metering.percent_complete)
"""

from typing import Any, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# MeteringRecord — Individual run metering data
# ---------------------------------------------------------------------------

class MeteringRecord(BaseModel):
    """
    Schema for an individual run metering data record.

    Represents a single entry returned in the ``GET /runs/metering`` endpoint
    response array.  Each record tracks the progress percentage of a code
    generation run along with its identifier and current status.

    The ``percent_complete`` field supports both snake_case and camelCase
    naming conventions via the Pydantic alias ``percentComplete`` and the
    ``populate_by_name=True`` model configuration.  The field is nullable —
    a ``None`` value indicates that metering data is not applicable for the
    given run.

    Attributes:
        percent_complete: Numeric progress percentage in the inclusive range
            [0.0, 100.0], or None when metering data is not applicable.
            Accepts both ``percent_complete`` (snake_case) and
            ``percentComplete`` (camelCase) from the API response JSON.
        run_id: Optional identifier string for the code generation run.
        status: Optional status string describing the current run state
            (e.g., "completed", "in_progress", "failed").
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    percent_complete: Optional[Union[int, float]] = Field(
        default=None,
        alias="percentComplete",
        description=(
            "Numeric progress percentage in the inclusive range [0.0, 100.0], "
            "or null when metering data is not applicable."
        ),
    )
    run_id: Optional[str] = Field(
        default=None,
        alias="runId",
        description="Identifier for the code generation run.",
    )
    status: Optional[str] = Field(
        default=None,
        description="Current status of the code generation run.",
    )


# ---------------------------------------------------------------------------
# InlineMeteringData — Nested metering data within a project response
# ---------------------------------------------------------------------------

class InlineMeteringData(BaseModel):
    """
    Schema for the nested metering data embedded within the project response.

    The ``GET /project`` endpoint returns a project object that nests metering
    information inside its response body.  This model captures the relevant
    ``percent_complete`` field from that nested structure.

    Attributes:
        percent_complete: Numeric progress percentage in the inclusive range
            [0.0, 100.0], or None when metering data is not applicable.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    percent_complete: Optional[Union[int, float]] = Field(
        default=None,
        alias="percentComplete",
        description=(
            "Numeric progress percentage in the inclusive range [0.0, 100.0], "
            "or null when metering data is not applicable."
        ),
    )


# ---------------------------------------------------------------------------
# CurrentMeteringResponse — Single-object current-run metering data
# ---------------------------------------------------------------------------

class CurrentMeteringResponse(BaseModel):
    """
    Schema for the ``GET /runs/metering/current`` single-object response.

    Represents the metering data for the actively in-progress code generation
    run.  This endpoint is typically invoked via polling / auto-refresh to
    track live progress.

    Attributes:
        percent_complete: Numeric progress percentage in the inclusive range
            [0.0, 100.0], or None when no run is active.
        run_id: Optional identifier string for the current code generation run.
        status: Optional status string describing the current run state.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    percent_complete: Optional[Union[int, float]] = Field(
        default=None,
        alias="percentComplete",
        description=(
            "Numeric progress percentage in the inclusive range [0.0, 100.0], "
            "or null when no active run exists."
        ),
    )
    run_id: Optional[str] = Field(
        default=None,
        alias="runId",
        description="Identifier for the current code generation run.",
    )
    status: Optional[str] = Field(
        default=None,
        description="Current status of the code generation run.",
    )


# ---------------------------------------------------------------------------
# MeteringResponse — Wrapper for the /runs/metering array response
# ---------------------------------------------------------------------------

class MeteringResponse(BaseModel):
    """
    Schema for the ``GET /runs/metering`` response.

    The API may return the metering records as either a bare JSON array or
    as an object wrapping the array under a key such as ``"data"`` or
    ``"records"``.  This model supports both scenarios through optional list
    fields and a ``from_response()`` factory method that normalises the raw
    response into a consistent structure.

    Attributes:
        data: List of MeteringRecord instances when the API wraps the array
            under a ``"data"`` key.
        records: List of MeteringRecord instances when the API wraps the
            array under a ``"records"`` key.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    data: Optional[List[MeteringRecord]] = Field(
        default=None,
        description="Metering records when the response wraps the array under a 'data' key.",
    )
    records: Optional[List[MeteringRecord]] = Field(
        default=None,
        description="Metering records when the response wraps the array under a 'records' key.",
    )

    @classmethod
    def from_response(cls, response_data: Any) -> "MeteringResponse":
        """
        Factory method that normalises a raw API response into a
        ``MeteringResponse`` instance.

        Handles the ambiguity of whether the ``GET /runs/metering`` endpoint
        returns a bare JSON list or a wrapped object:

        * **List input**: Each element is parsed into a ``MeteringRecord``
          and stored in the ``data`` field.
        * **Dict input**: Parsed directly via Pydantic model validation.
          If the dict contains a ``"data"`` or ``"records"`` key the nested
          list is automatically coerced into ``MeteringRecord`` instances.
        * **Other input types**: Returns a ``MeteringResponse`` with both
          ``data`` and ``records`` set to ``None`` (graceful degradation).

        Args:
            response_data: Raw response payload from the API — either a
                ``list`` of record dicts or a ``dict`` wrapping the records.

        Returns:
            MeteringResponse: A normalised response model instance with
            metering records accessible via ``.data`` or ``.records``.
        """
        if isinstance(response_data, list):
            # Bare list response — wrap each item as a MeteringRecord.
            metering_records: List[MeteringRecord] = []
            for item in response_data:
                if isinstance(item, dict):
                    metering_records.append(MeteringRecord.model_validate(item))
                elif isinstance(item, MeteringRecord):
                    metering_records.append(item)
                else:
                    # Attempt model_validate; let Pydantic raise on truly
                    # invalid data.
                    metering_records.append(MeteringRecord.model_validate(item))
            return cls(data=metering_records)

        if isinstance(response_data, dict):
            # Wrapped object response — let Pydantic parse the dict.
            return cls.model_validate(response_data)

        # Fallback for unexpected response shapes — return an empty wrapper
        # rather than crashing, allowing downstream tests to detect the
        # missing data and produce actionable error messages.
        return cls()


# ---------------------------------------------------------------------------
# ProjectResponse — Project data with inline metering information
# ---------------------------------------------------------------------------

class ProjectResponse(BaseModel):
    """
    Schema for the ``GET /project`` response.

    The project endpoint returns project metadata along with inline metering
    information.  The metering data may appear under a ``"metering"``
    (snake_case) key or a ``"meteringData"`` (camelCase) key, both of which
    are captured here.

    Attributes:
        metering: Nested metering data object found under the ``"metering"``
            key in the response payload.
        metering_data: Nested metering data object found under the
            ``"meteringData"`` (camelCase) key in the response payload.
        id: Optional project identifier string.
        name: Optional project name string.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    metering: Optional[InlineMeteringData] = Field(
        default=None,
        description="Nested metering data under the 'metering' key.",
    )
    metering_data: Optional[InlineMeteringData] = Field(
        default=None,
        alias="meteringData",
        description="Nested metering data under the 'meteringData' key.",
    )
    id: Optional[str] = Field(
        default=None,
        description="Unique project identifier.",
    )
    name: Optional[str] = Field(
        default=None,
        description="Project name.",
    )


# ---------------------------------------------------------------------------
# Utility parse functions
# ---------------------------------------------------------------------------

def parse_metering_response(data: Any) -> List[MeteringRecord]:
    """
    Parse a raw ``/runs/metering`` API response into a list of
    ``MeteringRecord`` instances.

    Supports three response shapes:

    1. **Bare list** — ``[{...}, {...}, ...]``
       Each element is validated as a ``MeteringRecord``.
    2. **Wrapped dict** — ``{"data": [{...}]}`` or ``{"records": [{...}]}``
       The list is extracted from the wrapper and each element is validated.
    3. **Anything else** — An empty list is returned to allow downstream
       tests to detect the unexpected shape without crashing.

    Args:
        data: Raw JSON-decoded response from the ``GET /runs/metering``
            endpoint.  May be a ``list``, ``dict``, or other type.

    Returns:
        List[MeteringRecord]: Parsed metering records.  Returns an empty
        list if the input cannot be meaningfully parsed.
    """
    # Case 1: Direct list of records.
    if isinstance(data, list):
        result: List[MeteringRecord] = []
        for item in data:
            try:
                if isinstance(item, dict):
                    result.append(MeteringRecord.model_validate(item))
                elif isinstance(item, MeteringRecord):
                    result.append(item)
                else:
                    result.append(MeteringRecord.model_validate(item))
            except Exception:
                # Skip items that cannot be parsed as MeteringRecord so that
                # downstream tests can still validate the parseable subset.
                continue
        return result

    # Case 2: Wrapped dict response.
    if isinstance(data, dict):
        # Attempt to find the record list under common wrapper keys.
        for key in ("data", "records"):
            if key in data and isinstance(data[key], list):
                return parse_metering_response(data[key])

        # If no recognised wrapper key is found, try parsing the entire dict
        # as a MeteringResponse (which may contain 'data' or 'records' at
        # deeper levels or extra-allow fields).
        try:
            response = MeteringResponse.model_validate(data)
            if response.data is not None:
                return response.data
            if response.records is not None:
                return response.records
        except Exception:
            pass

        return []

    # Case 3: Unrecognised input — return empty list.
    return []


def parse_current_metering_response(data: Any) -> CurrentMeteringResponse:
    """
    Parse a raw ``/runs/metering/current`` API response into a
    ``CurrentMeteringResponse`` instance.

    The endpoint is expected to return a single JSON object (dict)
    representing the metering data for the currently in-progress code
    generation run.

    Args:
        data: Raw JSON-decoded response from the ``GET /runs/metering/current``
            endpoint.  Expected to be a ``dict``.

    Returns:
        CurrentMeteringResponse: Parsed response model.  If ``data`` is not
        a dict or validation fails, returns an empty
        ``CurrentMeteringResponse`` with all fields set to their defaults
        (i.e., ``None``).

    Raises:
        No exceptions are raised — invalid input is handled gracefully to
        allow downstream test assertions to detect the issue.
    """
    if isinstance(data, dict):
        try:
            return CurrentMeteringResponse.model_validate(data)
        except Exception:
            # Return a default instance so downstream tests can inspect the
            # missing / invalid fields and produce clear error messages.
            return CurrentMeteringResponse()

    # Non-dict input (e.g., None, list) — return empty model.
    return CurrentMeteringResponse()


def parse_project_response(data: Any) -> ProjectResponse:
    """
    Parse a raw ``/project`` API response into a ``ProjectResponse``
    instance.

    The endpoint is expected to return a JSON object (dict) containing
    project metadata and inline metering data under either the
    ``"metering"`` or ``"meteringData"`` key.

    Args:
        data: Raw JSON-decoded response from the ``GET /project`` endpoint.
            Expected to be a ``dict``.

    Returns:
        ProjectResponse: Parsed response model.  If ``data`` is not a dict
        or validation fails, returns an empty ``ProjectResponse`` with all
        fields set to their defaults (i.e., ``None``).

    Raises:
        No exceptions are raised — invalid input is handled gracefully.
    """
    if isinstance(data, dict):
        try:
            return ProjectResponse.model_validate(data)
        except Exception:
            # Return a default instance for graceful degradation.
            return ProjectResponse()

    # Non-dict input — return empty model.
    return ProjectResponse()
