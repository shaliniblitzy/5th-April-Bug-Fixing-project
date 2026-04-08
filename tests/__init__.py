"""
Blitzy Platform API Test Suite.

This package contains comprehensive tests for validating the percent_complete
field across three Blitzy Platform API endpoints:

- GET /runs/metering — Metering data for multiple code generation runs
- GET /runs/metering/current — Current in-progress run metering data
- GET /project — Project detail with inline metering data

Test modules:
- test_runs_metering: Tests for the /runs/metering endpoint
- test_runs_metering_current: Tests for the /runs/metering/current endpoint
- test_project_inline_metering: Tests for the /project endpoint
- test_cross_endpoint_consistency: Cross-endpoint field consistency tests
- test_edge_cases: Edge case and boundary validation tests
"""
