#!/usr/bin/env python
"""
Test runner script for ClaimSense.
Runs tests with various configurations and generates reports.
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_tests(args):
    """Run tests with specified configuration."""
    cmd = ["pytest"]
    
    # Test type selection
    if args.unit:
        cmd.extend(["-m", "unit"])
    elif args.integration:
        cmd.extend(["-m", "integration"])
    elif args.e2e:
        cmd.extend(["-m", "e2e"])
    
    # Coverage
    if args.coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--cov-fail-under=70"
        ])
    
    # Verbose
    if args.verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")
    
    # Markers
    if not args.slow:
        cmd.extend(["-m", "not slow"])
    
    # Specific file/directory
    if args.path:
        cmd.append(str(args.path))
    else:
        cmd.append("tests/")
    
    # Parallel execution
    if args.parallel:
        try:
            cmd = ["pip", "install", "-q", "pytest-xdist"] if subprocess.run(
                ["python", "-c", "import xdist"],
                capture_output=True
            ).returncode != 0 else []
            if cmd:
                subprocess.run(cmd, check=True)
            cmd = ["pytest", "-n", str(args.parallel)] + cmd[len("pytest"):]
        except:
            pass
    
    # Run tests
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run ClaimSense tests"
    )
    
    # Test type
    test_type = parser.add_mutually_exclusive_group()
    test_type.add_argument(
        "--unit",
        action="store_true",
        help="Run unit tests only"
    )
    test_type.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests only"
    )
    test_type.add_argument(
        "--e2e",
        action="store_true",
        help="Run end-to-end tests only"
    )
    
    # Options
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--slow",
        action="store_true",
        help="Include slow tests"
    )
    parser.add_argument(
        "--parallel", "-n",
        type=int,
        metavar="N",
        help="Run tests in parallel with N workers"
    )
    parser.add_argument(
        "--path", "-p",
        type=Path,
        help="Specific test file or directory"
    )
    parser.add_argument(
        "--lf",
        action="store_true",
        help="Run last failed tests only"
    )
    parser.add_argument(
        "--ff",
        action="store_true",
        help="Run failed tests first"
    )
    
    args = parser.parse_args()
    
    # Run tests
    exit_code = run_tests(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
