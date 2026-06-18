"""
Lumina 测试套件运行器
运行所有测试并生成详细报告
"""
import sys
import os
import subprocess
import time
import re
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ============================================================================
# Configuration
# ============================================================================

AUTOMATION_ROOT = Path(__file__).parent
PROJECT_ROOT = AUTOMATION_ROOT.parent
PYTHONPATH = f"{PROJECT_ROOT / 'python_backend'};{PROJECT_ROOT}"

# Test categories
TEST_CATEGORIES = {
    "core": {
        "path": AUTOMATION_ROOT / "tests" / "core",
        "description": "Core module tests (no service dependencies)",
        "requires_service": False
    },
    "infra": {
        "path": AUTOMATION_ROOT / "tests" / "infra",
        "description": "Infrastructure tests (no service dependencies)",
        "requires_service": False
    },
    "services": {
        "path": AUTOMATION_ROOT / "tests" / "services",
        "description": "Service layer tests (mock dependencies)",
        "requires_service": False
    },
    "capabilities": {
        "path": AUTOMATION_ROOT / "tests" / "capabilities",
        "description": "Capability tests (mock dependencies)",
        "requires_service": False
    },
    "backend": {
        "path": AUTOMATION_ROOT / "tests" / "backend",
        "description": "Integration tests (requires running services)",
        "requires_service": True
    }
}

# ANSI Colors for Windows
try:
    from colorama import init, Fore, Style
    init()
    GREEN = Fore.GREEN
    RED = Fore.RED
    YELLOW = Fore.YELLOW
    CYAN = Fore.CYAN
    RESET = Style.RESET_ALL
except ImportError:
    # Fallback if colorama not available
    GREEN = ""
    RED = ""
    YELLOW = ""
    CYAN = ""
    RESET = ""

# ============================================================================
# Test Runner
# ============================================================================

class TestRunner:
    def __init__(self):
        self.results = {
            "passed": [],
            "failed": [],
            "errors": [],
            "skipped": []
        }
        self.start_time = None
        self.report_file = AUTOMATION_ROOT / "test_results_report.txt"

    def print_header(self, text):
        print(f"\n{CYAN}{'=' * 70}{RESET}")
        print(f"{CYAN}{text:^70}{RESET}")
        print(f"{CYAN}{'=' * 70}{RESET}")

    def print_test(self, text, status="info"):
        if status == "pass":
            print(f"{GREEN}[PASS]{RESET} {text}")
        elif status == "fail":
            print(f"{RED}[FAIL]{RESET} {text}")
        elif status == "warn":
            print(f"{YELLOW}[WARN]{RESET} {text}")
        else:
            print(f"      {text}")

    def discover_tests(self):
        """Discover all test files in the automation/tests directory"""
        test_files = []
        for category, config in TEST_CATEGORIES.items():
            path = config["path"]
            if path.exists():
                files = list(path.glob("test_*.py"))
                for f in files:
                    test_files.append({
                        "file": f,
                        "category": category,
                        "relative": f.relative_to(AUTOMATION_ROOT)
                    })
        return sorted(test_files, key=lambda x: str(x["file"]))

    def run_test_file(self, test_info):
        """Run a single test file and capture results"""
        test_file = test_info["file"]
        relative = test_info["relative"]
        category = test_info["category"]

        self.print_header(f"Running: {relative}")
        print(f"{CYAN}Category:{RESET} {category}")
        print(f"{CYAN}Requires Service:{RESET} {TEST_CATEGORIES[category]['requires_service']}")

        env = os.environ.copy()
        env["PYTHONPATH"] = PYTHONPATH

        start = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, str(test_file)],
                capture_output=True,
                text=True,
                env=env,
                timeout=120,  # 2 minute timeout per test
                encoding='utf-8',
                errors='replace'
            )
            duration = time.time() - start

            # Parse output
            output = proc.stdout + proc.stderr

            # Look for test results in output
            tests_run_match = re.search(r'Tests run: (\d+)', output)
            failures_match = re.search(r'Failures: (\d+)', output)
            errors_match = re.search(r'Errors: (\d+)', output)

            tests_run = int(tests_run_match.group(1)) if tests_run_match else 0
            failures = int(failures_match.group(1)) if failures_match else 0
            errors = int(errors_match.group(1)) if errors_match else 0

            if proc.returncode == 0 and failures == 0 and errors == 0:
                self.print_test(f"PASSED ({tests_run} tests, {duration:.2f}s)", "pass")
                self.results["passed"].append({
                    "file": str(relative),
                    "tests_run": tests_run,
                    "duration": duration
                })
                return True, output
            else:
                self.print_test(f"FAILED ({tests_run} tests, {failures} failures, {errors} errors, {duration:.2f}s)", "fail")
                self.results["failed"].append({
                    "file": str(relative),
                    "tests_run": tests_run,
                    "failures": failures,
                    "errors": errors,
                    "duration": duration,
                    "output": output
                })
                return False, output

        except subprocess.TimeoutExpired:
            self.print_test(f"TIMEOUT after 120s", "fail")
            self.results["errors"].append({
                "file": str(relative),
                "error": "Timeout after 120 seconds"
            })
            return False, "Timeout"
        except Exception as e:
            self.print_test(f"ERROR: {e}", "fail")
            self.results["errors"].append({
                "file": str(relative),
                "error": str(e)
            })
            return False, str(e)

    def run_all_tests(self, categories=None):
        """Run all tests or specific categories"""
        if categories:
            print(f"{YELLOW}Running specific categories: {', '.join(categories)}{RESET}")
        else:
            print(f"{YELLOW}Running all tests...{RESET}")

        test_files = self.discover_tests()

        if categories:
            test_files = [t for t in test_files if t["category"] in categories]

        self.print_header(f"Found {len(test_files)} test files")

        for test_info in test_files:
            category = test_info["category"]
            requires_service = TEST_CATEGORIES[category]["requires_service"]

            # Check if service is running for integration tests
            if requires_service:
                if not self.check_service_running():
                    self.print_test(f"Skipping {test_info['relative']} - service not running", "warn")
                    self.results["skipped"].append(str(test_info["relative"]))
                    continue

            self.run_test_file(test_info)
            time.sleep(0.5)  # Brief pause between tests

    def check_service_running(self):
        """Check if Lumina service is running"""
        import socket
        ports = [8010, 8765, 8766]  # memory, stt, tts
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result != 0:
                return False
        return True

    def generate_report(self):
        """Generate detailed test report"""
        self.print_header("Generating Test Report")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self.report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("Lumina Test Suite Report\n")
            f.write("=" * 70 + "\n")
            f.write(f"Generated: {timestamp}\n")
            f.write(f"Total Test Files: {len(self.results['passed']) + len(self.results['failed']) + len(self.results['errors'])}\n")
            f.write("\n")

            # Summary
            f.write("=" * 70 + "\n")
            f.write("SUMMARY\n")
            f.write("=" * 70 + "\n")
            f.write(f"Passed: {len(self.results['passed'])}\n")
            f.write(f"Failed: {len(self.results['failed'])}\n")
            f.write(f"Errors: {len(self.results['errors'])}\n")
            f.write(f"Skipped: {len(self.results['skipped'])}\n")
            f.write("\n")

            # Total test cases
            total_tests = sum(r.get('tests_run', 0) for r in self.results['passed'])
            total_tests += sum(r.get('tests_run', 0) for r in self.results['failed'])
            f.write(f"Total Test Cases: {total_tests}\n")
            f.write("\n")

            # Passed tests
            if self.results['passed']:
                f.write("=" * 70 + "\n")
                f.write("PASSED TESTS\n")
                f.write("=" * 70 + "\n")
                for result in sorted(self.results['passed'], key=lambda x: x['file']):
                    f.write(f"\n[PASS] {result['file']}\n")
                    f.write(f"  Tests: {result['tests_run']}, Duration: {result['duration']:.2f}s\n")
                f.write("\n")

            # Failed tests
            if self.results['failed']:
                f.write("=" * 70 + "\n")
                f.write("FAILED TESTS\n")
                f.write("=" * 70 + "\n")
                for result in sorted(self.results['failed'], key=lambda x: x['file']):
                    f.write(f"\n[FAIL] {result['file']}\n")
                    f.write(f"  Tests: {result['tests_run']}, Failures: {result['failures']}, Errors: {result['errors']}\n")
                    f.write(f"  Duration: {result['duration']:.2f}s\n")
                    # Include error output
                    output = result.get('output', '')
                    if output:
                        f.write(f"  Output:\n")
                        # Only show last 50 lines of output
                        lines = output.split('\n')
                        for line in lines[-50:]:
                            f.write(f"    {line}\n")
                f.write("\n")

            # Errors
            if self.results['errors']:
                f.write("=" * 70 + "\n")
                f.write("ERRORS\n")
                f.write("=" * 70 + "\n")
                for error in sorted(self.results['errors'], key=lambda x: x['file']):
                    f.write(f"\n[ERROR] {error['file']}\n")
                    f.write(f"  Error: {error.get('error', 'Unknown')}\n")
                f.write("\n")

            # Skipped
            if self.results['skipped']:
                f.write("=" * 70 + "\n")
                f.write("SKIPPED (Service Not Running)\n")
                f.write("=" * 70 + "\n")
                for skipped in sorted(self.results['skipped']):
                    f.write(f"  [SKIP] {skipped}\n")
                f.write("\n")

        self.print_test(f"Report saved to: {self.report_file}", "pass")
        print(f"\n{CYAN}Report contents:{RESET}")
        with open(self.report_file, 'r', encoding='utf-8') as f:
            print(f.read())

    def print_summary(self):
        """Print final summary"""
        self.print_header("Test Suite Complete")

        total = len(self.results['passed']) + len(self.results['failed']) + len(self.results['errors'])
        passed = len(self.results['passed'])
        failed = len(self.results['failed'])
        errors = len(self.results['errors'])
        skipped = len(self.results['skipped'])

        print(f"\n{CYAN}Total Files:{RESET} {total}")
        print(f"{GREEN}Passed:{RESET} {passed}")
        print(f"{RED}Failed:{RESET} {failed}")
        print(f"{RED}Errors:{RESET} {errors}")
        print(f"{YELLOW}Skipped:{RESET} {skipped}")

        if total > 0:
            pass_rate = (passed / total) * 100
            print(f"\n{CYAN}Pass Rate:{RESET} {pass_rate:.1f}%")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run Lumina test suite")
    parser.add_argument('--category', '-c',
                        choices=list(TEST_CATEGORIES.keys()),
                        action='append',
                        help='Run specific test category (can be used multiple times)')
    parser.add_argument('--no-report', action='store_true',
                        help='Skip report generation')
    args = parser.parse_args()

    print(f"{CYAN}{'=' * 70}{RESET}")
    print(f"{CYAN}{'Lumina Test Suite':^70}{RESET}")
    print(f"{CYAN}{'=' * 70}{RESET}")

    runner = TestRunner()

    try:
        runner.run_all_tests(categories=args.category)
        runner.print_summary()

        if not args.no_report:
            runner.generate_report()

    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test run interrupted by user{RESET}")
        return 1
    except Exception as e:
        print(f"\n{RED}Fatal error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return 1

    return 0 if len(runner.results['failed']) == 0 and len(runner.results['errors']) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
