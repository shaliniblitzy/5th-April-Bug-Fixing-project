# Blitzy Platform API Test Suite — `percent_complete` Field Validation

A Python-based API test suite that validates the presence, correctness, and schema compliance of the `percent_complete` (or `percentComplete`) field across three Blitzy Platform API endpoints. The suite ensures that every API response includes a properly typed and ranged progress percentage for code generation runs.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Target Endpoints](#target-endpoints)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Environment Configuration](#environment-configuration)
- [Test Execution Guide](#test-execution-guide)
- [Test Suite Structure](#test-suite-structure)
- [Validation Rules](#validation-rules)
- [Project Structure](#project-structure)

---

## Project Overview

This repository contains a comprehensive, read-only API test suite designed to verify that the `percent_complete` field is present, correctly typed, and within valid bounds in the JSON responses returned by three Blitzy Platform API endpoints. The test suite automates the manual browser-based inspection process (Network tab → XHR filter → search for `metering`, `runs`, `project`) into a repeatable, CI-friendly `pytest` workflow.

**Key capabilities:**

- **Field presence verification** — Confirms `percent_complete` or `percentComplete` exists in every API response
- **Type validation** — Asserts the field value is `int`, `float`, or `null` (rejects strings, booleans, and other types)
- **Range validation** — Ensures numeric values fall within the inclusive range `[0.0, 100.0]`
- **Cross-endpoint consistency** — Detects field name mismatches (e.g., snake_case in one endpoint, camelCase in another)
- **Edge case detection** — Flags out-of-range values, incorrect data types, and missing fields
- **Environment flexibility** — Runs against development, staging, or production by changing environment variables only

---

## Target Endpoints

The test suite validates the following three Blitzy Platform API endpoints:

### 1. `GET /runs/metering?projectId=xxx`

Returns metering data for multiple code generation runs (historical and completed). The response is an array of per-run metering objects, each expected to contain a `percent_complete` field.

- **Triggered by:** Viewing run history or fetching metering data
- **Query parameter:** `projectId` (required) — Target project identifier
- **Authentication:** Bearer token required

### 2. `GET /runs/metering/current`

Returns metering data for the currently in-progress code generation run. Typically invoked during live run status polling or auto-refresh.

- **Triggered by:** Viewing live run status or auto-refresh polling
- **Query parameters:** None
- **Authentication:** Bearer token required
- **Note:** Only returns meaningful data when a run is actively in progress

### 3. `GET /project?id=xxx`

Returns project detail data with inline metering information embedded in the response body. The `percent_complete` field is located within a nested metering data structure.

- **Triggered by:** Opening a project page in the Blitzy Platform UI
- **Query parameter:** `id` (required) — Target project identifier
- **Authentication:** Bearer token required

---

## Prerequisites

- **Python 3.12** or later
- **pip** (Python package manager)
- A valid Blitzy Platform **API authentication token**
- A valid **project ID** for the target Blitzy Platform project

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone <repository-url>
cd 5th-April-Bug-Fixing-project
```

### 2. Create and activate a virtual environment

```bash
python3.12 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This installs the following packages:

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | 9.0.2 | Test framework with rich assertion introspection |
| `httpx` | 0.28.1 | Modern HTTP client for authenticated API requests |
| `pydantic` | 2.12.5 | Data validation and response schema modeling |
| `python-dotenv` | 1.2.2 | Environment variable loading from `.env` files |
| `pytest-cov` | 7.1.0 | Test coverage reporting plugin |

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit the `.env` file and replace the placeholder values with your actual credentials. See [Environment Configuration](#environment-configuration) below for details.

---

## Environment Configuration

The test suite reads all connection and authentication settings from environment variables. Copy `.env.example` to `.env` and fill in the required values:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_BASE_URL` | Yes | — | Base URL of the Blitzy Platform API (e.g., `https://api.blitzy.com`) |
| `API_AUTH_TOKEN` | Yes | — | Bearer token for authenticating API requests |
| `PROJECT_ID` | Yes | — | Target project identifier for test execution |
| `REQUEST_TIMEOUT` | No | `30` | HTTP request timeout in seconds |

**Example `.env` file:**

```dotenv
API_BASE_URL=https://api.blitzy.com
API_AUTH_TOKEN=your-auth-token-here
PROJECT_ID=your-project-id-here
REQUEST_TIMEOUT=30
```

> **Security note:** The `.env` file contains credentials and is excluded from version control via `.gitignore`. Never commit it to the repository. The `.env.example` template is safe to commit.

---

## Test Execution Guide

All commands below assume you have activated the virtual environment (`source venv/bin/activate`).

### Run all tests

```bash
pytest
```

### Run with verbose output

```bash
pytest -v
```

### Run a specific test file

```bash
pytest tests/test_runs_metering.py
pytest tests/test_runs_metering_current.py
pytest tests/test_project_inline_metering.py
pytest tests/test_cross_endpoint_consistency.py
pytest tests/test_edge_cases.py
```

### Run tests by marker

```bash
pytest -m metering
pytest -m current_metering
pytest -m project
pytest -m consistency
pytest -m edge_cases
```

### Run with coverage report

```bash
pytest --cov=src
```

### Run with detailed coverage (including missing lines)

```bash
pytest --cov=src --cov-report=term-missing -v
```

---

## Test Suite Structure

The test suite is organized into five test modules, each targeting a specific validation concern:

| Test File | Marker | Description |
|-----------|--------|-------------|
| `tests/test_runs_metering.py` | `metering` | Validates `GET /runs/metering` — field presence in every record, type validation, range checking, and completed run verification |
| `tests/test_runs_metering_current.py` | `current_metering` | Validates `GET /runs/metering/current` — field presence for active runs, type validation, in-progress value checks, and endpoint availability |
| `tests/test_project_inline_metering.py` | `project` | Validates `GET /project` — metering data section presence, nested field detection, type and range validation of inline metering |
| `tests/test_cross_endpoint_consistency.py` | `consistency` | Cross-endpoint checks — field name consistency (`percent_complete` vs `percentComplete`) and schema uniformity across all three endpoints |
| `tests/test_edge_cases.py` | `edge_cases` | Boundary and negative tests — out-of-range values, invalid types (string, boolean, list), null acceptance, and field absence detection |

### Supporting modules

| Source File | Description |
|-------------|-------------|
| `src/config.py` | Configuration management — loads API base URL, auth token, project ID, and timeout from environment variables or `.env` files |
| `src/api_client.py` | HTTP client wrapper — provides authenticated `GET` methods for all three target endpoints with configurable timeout and error handling |
| `src/validators.py` | Validation utilities — field detection (snake_case and camelCase), type checking, range verification, and cross-endpoint consistency checking |
| `src/models.py` | Pydantic response models — defines expected API response schemas including `MeteringRecord`, `CurrentMeteringResponse`, and `ProjectResponse` |
| `tests/conftest.py` | Shared pytest fixtures — session-scoped API client, project ID, and cached endpoint response fixtures |

---

## Validation Rules

The test suite enforces the following rules for the `percent_complete` / `percentComplete` field:

### Field Presence

The field **must always be present** in the API response. Absence of the field constitutes a bug, even if the value would be `null`.

### Type Validation

The field value must be one of:

- **`int`** — Integer value (e.g., `0`, `50`, `100`)
- **`float`** — Floating-point value (e.g., `0.0`, `75.5`, `100.0`)
- **`null`** — Explicitly `null` when metering data is not applicable

The following types are **rejected**:

- `string` (e.g., `"50"`, `"complete"`)
- `boolean` (e.g., `true`, `false`)
- `array` or `object`

### Range Validation

Numeric values must fall within the **inclusive range `[0.0, 100.0]`**:

- Values **below `0.0`** are invalid
- Values **above `100.0`** are invalid
- Boundary values `0.0` and `100.0` are valid

### Cross-Endpoint Naming Consistency

The field naming convention must be **uniform across all three endpoints**. The test suite accepts either `percent_complete` (snake_case) or `percentComplete` (camelCase), but flags a mismatch if different endpoints use different conventions.

### Scenario Coverage

| Scenario | Expected Value | Applicable Endpoints |
|----------|---------------|---------------------|
| Completed run | Numeric value between 0–100 | All three endpoints |
| In-progress run | Numeric value (likely < 100) | Primarily `/runs/metering/current` |
| No applicable data | `null` | All three endpoints |

---

## Project Structure

```
5th-April-Bug-Fixing-project/
├── README.md                                  # Project documentation (this file)
├── requirements.txt                           # Python dependency manifest (pinned versions)
├── pytest.ini                                 # Pytest configuration with markers and test paths
├── .env.example                               # Environment variable template
├── .gitignore                                 # Git exclusion patterns for Python projects
├── src/                                       # Source package
│   ├── __init__.py                            # Package initializer with convenience re-exports
│   ├── config.py                              # Configuration management (env vars, .env loading)
│   ├── api_client.py                          # HTTP client wrapper for Blitzy Platform APIs
│   ├── validators.py                          # Field detection, type/range validation, consistency
│   └── models.py                              # Pydantic response schema models
└── tests/                                     # Test package
    ├── __init__.py                            # Test package initializer
    ├── conftest.py                            # Shared pytest fixtures (API client, responses)
    ├── test_runs_metering.py                  # Tests for GET /runs/metering
    ├── test_runs_metering_current.py          # Tests for GET /runs/metering/current
    ├── test_project_inline_metering.py        # Tests for GET /project inline metering
    ├── test_cross_endpoint_consistency.py     # Cross-endpoint consistency tests
    └── test_edge_cases.py                     # Edge case and boundary tests
```

---

## License

This project is part of the Blitzy Platform ecosystem.
