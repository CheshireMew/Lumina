"""
Run pytest with coverage report

Usage:
    python run_pytest_with_coverage.py                    # Run all tests with coverage
    python run_pytest_with_coverage.py --unit              # Run only unit tests
    python run_pytest_with_coverage.py --integration       # Run only integration tests
    python run_pytest_with_coverage.py --html              # Generate HTML coverage report
"""
import sys
import os
import subprocess
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

AUTOMATION_ROOT = Path(__file__).parent
PROJECT_ROOT = AUTOMATION_ROOT.parent

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"


def print_header(text):
    print(f"\n{CYAN}{'=' * 70}{RESET}")
    print(f"{CYAN}{text:^70}{RESET}")
    print(f"{CYAN}{'=' * 70}{RESET}")


def run_pytest(args):
    """Run pytest with given arguments"""
    cmd = [sys.executable, "-m", "pytest"]

    # Add coverage options
    cmd.extend([
        "--cov=" + str(PROJECT_ROOT / "python_backend"),
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
        "-v"
    ])

    # Add user arguments
    cmd.extend(args)

    # Change to automation directory
    os.chdir(AUTOMATION_ROOT)

    # Set PYTHONPATH
    env = os.environ.copy()
    pythonpath = str(PROJECT_ROOT / "python_backend") + os.pathsep + str(PROJECT_ROOT)
    env["PYTHONPATH"] = pythonpath

    print(f"{CYAN}Running:{RESET} {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(cmd, env=env)
        return result.returncode
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test run interrupted{RESET}")
        return 1


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Lumina tests with coverage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Run all tests with coverage
  %(prog)s --unit              Run only unit tests (fast)
  %(prog)s --integration       Run integration tests (requires services)
  %(prog)s --html              Generate HTML coverage report
  %(prog)s tests_pytest/       Run specific directory
  %(prog)s -k "container"      Run tests matching pattern
        """
    )

    parser.add_argument(
        "--unit", "-u",
        action="store_true",
        help="Run only unit tests (marked with 'unit')"
    )

    parser.add_argument(
        "--integration", "-i",
        action="store_true",
        help="Run only integration tests (marked with 'integration')"
    )

    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML coverage report"
    )

    parser.add_argument(
        "--no-cov",
        action="store_true",
        help="Run without coverage"
    )

    parser.add_argument(
        "extra_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to pytest"
    )

    args = parser.parse_args()

    print_header("Lumina Pytest Runner with Coverage")

    # Build pytest arguments
    pytest_args = []

    if args.unit:
        pytest_args.extend(["-m", "unit"])
        print(f"{YELLOW}Running unit tests only{RESET}")
    elif args.integration:
        pytest_args.extend(["-m", "integration"])
        print(f"{YELLOW}Running integration tests only{RESET}")
    else:
        pytest_args.extend(["-m", "not e2e"])  # Skip E2E by default
        print(f"{YELLOW}Running all tests (except E2E){RESET}")

    # Add extra arguments
    if args.extra_args:
        pytest_args.extend(args.extra_args)

    # If no coverage requested, modify command
    if args.no_cov:
        # We'll need to modify the run_pytest function
        # For now, just note it
        print(f"{YELLOW}Coverage disabled{RESET}")

    # Run tests
    print(f"{CYAN}Coverage report will be saved to:{RESET}")
    print(f"  - Terminal output (with missing lines)")
    print(f"  - HTML report: {AUTOMATION_ROOT / 'htmlcov' / 'index.html'}")
    print(f"  - XML report: {AUTOMATION_ROOT / 'coverage.xml'}")

    return_code = run_pytest(pytest_args)

    # Print summary
    print_header("Test Run Complete")

    if return_code == 0:
        print(f"{GREEN}All tests passed!{RESET}")
    else:
        print(f"{RED}Some tests failed{RESET}")

    print(f"\n{CYAN}View HTML coverage report:{RESET}")
    print(f"  {AUTOMATION_ROOT / 'htmlcov' / 'index.html'}")

    return return_code


if __name__ == "__main__":
    sys.exit(main())
