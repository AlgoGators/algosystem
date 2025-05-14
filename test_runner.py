#!/usr/bin/env python3
"""
Test runner script for AlgoSystem.
Provides various testing options and configurations.
"""

import os
import sys
import pytest
import subprocess
from pathlib import Path

def run_tests(test_type="all", coverage=False, verbose=False, specific_test=None):
    """
    Run tests with specified configuration.
    
    Args:
        test_type: Type of tests to run ('all', 'unit', 'integration', 'slow', 'fast', 'web', 'cli')
        coverage: Whether to run with coverage
        verbose: Whether to show verbose output
        specific_test: Specific test file or test to run
    """
    
    # Build pytest command
    cmd = ["pytest"]
    
    # Add test selection
    if specific_test:
        cmd.append(specific_test)
    elif test_type == "unit":
        cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "slow":
        cmd.extend(["-m", "slow"])
    elif test_type == "fast":
        cmd.extend(["-m", "not slow"])
    elif test_type == "web":
        cmd.extend(["-m", "web"])
    elif test_type == "cli":
        cmd.extend(["-m", "cli"])
    
    # Add coverage if requested
    if coverage:
        cmd.extend(["--cov=algosystem", "--cov-report=html", "--cov-report=term", "--cov-report=xml"])
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # Add parallel execution if available
    try:
        cmd.extend(["-n", "auto"])
    except ImportError:
        pass
    
    # Run tests
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    if coverage and result.returncode == 0:
        print("\nCoverage reports generated:")
        print("- HTML: htmlcov/index.html")
        print("- XML: coverage.xml")
    
    return result.returncode

def run_linting():
    """Run code quality checks."""
    print("Running black (code formatting)...")
    black_result = subprocess.run(["black", "--check", "algosystem", "tests"])
    
    print("\nRunning flake8 (linting)...")
    flake8_result = subprocess.run(["flake8", "algosystem", "tests", "--max-line-length=88", "--extend-ignore=E203,W503"])
    
    print("\nRunning mypy (type checking)...")
    mypy_result = subprocess.run(["mypy", "algosystem", "--ignore-missing-imports"])
    
    # Return overall result
    return max(black_result.returncode, flake8_result.returncode, mypy_result.returncode)

def run_performance_tests():
    """Run performance benchmarks."""
    print("Running performance tests...")
    
    # Create a simple performance test
    performance_script = """
import time
import pandas as pd
import numpy as np
from algosystem import Engine

# Test with different data sizes
sizes = [100, 1000, 5000]
times = []

for size in sizes:
    print(f"Testing with {size} data points...")
    dates = pd.date_range('2020-01-01', periods=size, freq='D')
    returns = np.random.normal(0.001, 0.02, size)
    prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()
    
    start_time = time.time()
    engine = Engine(prices)
    results = engine.run()
    end_time = time.time()
    
    execution_time = end_time - start_time
    times.append(execution_time)
    print(f"  Time: {execution_time:.3f} seconds")

print("\\nPerformance Summary:")
for size, time_taken in zip(sizes, times):
    print(f"  {size} points: {time_taken:.3f}s ({size/time_taken:.0f} points/sec)")
"""
    
    try:
        exec(performance_script)
    except Exception as e:
        print(f"Performance test failed: {e}")

def generate_test_report():
    """Generate a comprehensive test report."""
    print("Generating comprehensive test report...")
    
    # Run tests with coverage and XML output
    cmd = [
        "pytest",
        "--cov=algosystem",
        "--cov-report=html",
        "--cov-report=xml",
        "--junitxml=test-results.xml",
        "-v"
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\nTest report generated:")
        print("- Test results: test-results.xml")
        print("- Coverage HTML: htmlcov/index.html")
        print("- Coverage XML: coverage.xml")
    
    return result.returncode

def run_ci_tests():
    """Run tests suitable for CI environment."""
    print("Running CI test suite...")
    
    # Run linting first
    print("1. Running linting checks...")
    lint_result = run_linting()
    
    # Run tests with coverage
    print("\n2. Running tests with coverage...")
    test_result = run_tests(coverage=True, verbose=True)
    
    # Generate reports
    print("\n3. Generating test reports...")
    report_result = generate_test_report()
    
    # Overall result
    overall_result = max(lint_result, test_result, report_result)
    
    if overall_result == 0:
        print("\n✅ All CI checks passed!")
    else:
        print(f"\n❌ CI checks failed with exit code {overall_result}")
    
    return overall_result

def main():
    """Main function to handle command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AlgoSystem Test Runner")
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration", "slow", "fast", "web", "cli"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--lint", action="store_true", help="Run linting instead of tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--ci", action="store_true", help="Run CI test suite")
    parser.add_argument("--report", action="store_true", help="Generate comprehensive test report")
    parser.add_argument("--test", help="Specific test file or test to run")
    parser.add_argument("--install-deps", action="store_true", help="Install test dependencies")
    
    args = parser.parse_args()
    
    # Install dependencies if requested
    if args.install_deps:
        print("Installing test dependencies...")
        subprocess.run(["pip", "install", "-e", ".[dev]"])
        return 0
    
    if args.lint:
        exit_code = run_linting()
    elif args.performance:
        run_performance_tests()
        exit_code = 0
    elif args.ci:
        exit_code = run_ci_tests()
    elif args.report:
        exit_code = generate_test_report()
    else:
        exit_code = run_tests(
            test_type=args.type,
            coverage=args.coverage,
            verbose=args.verbose,
            specific_test=args.test
        )
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()