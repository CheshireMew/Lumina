"""
Quick smoke test to verify pytest infrastructure is working
"""
import sys
from pathlib import Path

# Add python_backend to path
AUTOMATION_ROOT = Path(__file__).parent
PROJECT_ROOT = AUTOMATION_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

# Fix Windows encoding - do this before any prints
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def test_imports():
    """Test that all key modules can be imported"""
    print("\n=== Testing Imports ===")

    try:
        from services.container import ServiceContainer
        print("✓ ServiceContainer imported")
    except Exception as e:
        print(f"✗ ServiceContainer failed: {e}")
        return False

    try:
        from services.plugin_service import PluginService
        print("✓ PluginService imported")
    except Exception as e:
        print(f"✗ PluginService failed: {e}")
        return False

    try:
        import pytest
        print(f"✓ pytest {pytest.__version__} available")
    except ImportError:
        print("✗ pytest not installed")
        return False

    return True


def test_fixtures():
    """Test that fixtures can be loaded"""
    print("\n=== Testing Fixtures ===")

    try:
        import conftest
        print("✓ conftest.py loaded")
    except Exception as e:
        print(f"✗ conftest.py failed: {e}")
        return False

    try:
        from fixtures import factories
        print("✓ fixtures.factories loaded")
    except Exception as e:
        print(f"✗ fixtures.factories failed: {e}")
        return False

    return True


def test_pytest_discovery():
    """Test that pytest can discover tests"""
    print("\n=== Testing Pytest Discovery ===")

    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "tests_pytest/"],
        capture_output=True,
        text=True,
        cwd=str(AUTOMATION_ROOT)
    )

    if "collected" in result.stdout or "test session starts" in result.stdout:
        # Count collected tests
        lines = result.stdout.split('\n')
        test_count = sum(1 for line in lines if '<Function' in line or '<TestCase' in line)
        print(f"✓ Pytest discovered {test_count} tests")
        return True
    else:
        print("✗ Pytest discovery failed")
        print(result.stdout)
        print(result.stderr)
        return False


def main():
    print("=" * 60)
    print("Lumina Pytest Infrastructure Smoke Test")
    print("=" * 60)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("Fixtures", test_fixtures()))
    results.append(("Pytest Discovery", test_pytest_discovery()))

    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)

    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {name}: {status}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n✓ All checks passed! Pytest infrastructure is ready.")
        print("\nNext steps:")
        print("  1. Run tests: pytest tests_pytest/ -v")
        print("  2. Run with coverage: python run_pytest_with_coverage.py")
        return 0
    else:
        print("\n✗ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
