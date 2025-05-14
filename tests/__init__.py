"""
AlgoSystem Test Suite

This test suite provides comprehensive testing for the AlgoSystem library,
ensuring that all major functionality works correctly and handles edge cases gracefully.

Test Structure:
- test_engine.py: Tests for the core Engine class
- test_metrics.py: Tests for performance metrics calculations
- test_dashboard_generation.py: Tests for dashboard creation and export
- test_web_app.py: Tests for web application components
- test_cli.py: Tests for command-line interface
- test_risk_analysis.py: Tests for risk analysis functions
- test_performance_analysis.py: Tests for performance analysis functions
- conftest.py: Test fixtures and setup

Running Tests:
- All tests: pytest
- Specific test file: pytest tests/test_engine.py
- With coverage: pytest --cov=algosystem
- Verbose output: pytest -v

Test Philosophy:
The tests focus on ensuring the system doesn't crash rather than testing exact outputs,
since financial calculations can vary based on implementation details and may include
randomness or floating-point precision issues.
"""