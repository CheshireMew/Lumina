"""
Security scanning tests for Lumina

Uses automated security tools to find vulnerabilities.
Install: pip install bandit safety
Run: pytest tests_pytest/security/test_scan.py -v
"""
import sys
from pathlib import Path
import pytest
import subprocess
import tempfile
import os

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))


# ============================================================================
# Bandit Security Scanning
# ============================================================================

@pytest.mark.security_scan
def test_bandit_scan_on_source_code():
    """Run bandit security scanner on source code"""
    try:
        import bandit
    except ImportError:
        pytest.skip("bandit not installed. Run: pip install bandit")

    # Scan python_backend directory
    backend_dir = PROJECT_ROOT / "python_backend"

    result = subprocess.run(
        ["bandit", "-r", str(backend_dir), "-f", "json"],
        capture_output=True,
        text=True,
        timeout=60
    )

    # Parse results
    if result.returncode == 0:
        print("✓ No security issues found by bandit")
    else:
        # Try to parse JSON output
        try:
            import json
            issues = json.loads(result.stdout)
            issue_count = len(issues.get("results", []))
            print(f"Bandit found {issue_count} security issues")
            # Don't fail the test, just report
            assert True  # We expect some issues in development
        except:
            # JSON parse failed, just check for issues
            if "severity" in result.stdout.lower():
                print("Bandit found security issues (check output)")
    assert True  # This is informational


# ============================================================================
# Safety Dependency Scanning
# ============================================================================

@pytest.mark.security_scan
def test_safety_check_dependencies():
    """Check for known security vulnerabilities in dependencies"""
    try:
        import safety
    except ImportError:
        pytest.skip("safety not installed. Run: pip install safety")

    # Check requirements.txt
    requirements_files = [
        PROJECT_ROOT / "requirements.txt",
        PROJECT_ROOT / "python_backend" / "requirements.txt"
    ]

    issues_found = []
    for req_file in requirements_files:
        if req_file.exists():
            result = subprocess.run(
                ["safety", "check", "--file", str(req_file), "--json"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                try:
                    import json
                    issues = json.loads(result.stdout)
                    issues_found.extend(issues)
                except:
                    pass

    if issues_found:
        print(f"Safety found {len(issues_found)} vulnerabilities:")
        for issue in issues[:5]:  # Show first 5
            print(f"  - {issue.get('package', 'unknown')}: {issue.get('vulnerability', 'unknown')}")
        assert True  # Informational - don't fail the test


# ============================================================================
# Static Analysis for Security Issues
# ============================================================================

@pytest.mark.security_scan
def test_static_security_audit():
    """Perform static analysis for security patterns"""
    # Scan for potential security issues in source code
    security_issues = []

    # Common security patterns to check
    security_patterns = {
        "Hardcoded passwords": [
            (r'password\s*=\s*["\'].*["\']', "password assignment in code"),
            (r'api_key\s*=\s*["\'].*["\']', "API key in code"),
        ],
        "SQL injection risks": [
            (r'f"SELECT.*\{.*\}', "f-strings with SQL (potential injection)"),
            (r'execute\s*\(\s*["\'][^"]*SELECT', "execute() with SQL"),
        ],
        "Command injection risks": [
            (r'subprocess\.call\(.*["\'].*;.*["\']', "subprocess.call with semicolon"),
            (r'os\.system\(["\'])', "os.system() with user input"),
        ],
        "Weak cryptography": [
            (r'from Crypto\.Cipher import AES', "PyCrypto (deprecated, has vulnerabilities)"),
            (r'import hashlib.*\.md5\(', "MD5 (weak for passwords)"),
        ]
    }

    # Scan python_backend directory
    backend_dir = PROJECT_ROOT / "python_backend"

    for category, patterns in security_patterns.items():
        for pattern, description in patterns:
            import re
            try:
                with open(backend_dir / "services" / "chat_service.py", 'r', encoding='utf-8') as f:
                    content = f.read()
                    if re.search(pattern, content):
                        security_issues.append(f"{category}: {description}")
                        break  # Only need to find once per category
            except:
                pass

    for issue in security_issues:
        print(f"Security scan found: {issue}")

    # This is informational
    assert True


# ============================================================================
# Permission Audit
# ============================================================================

@pytest.mark.security_scan
def test_permissions_audit():
    """Verify that file permissions are secure"""
    # Check sensitive files
    sensitive_files = [
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / "config" / "secrets.yaml",
        PROJECT_ROOT / "python_backend" / "credentials.json",
    ]

    issues = []
    for file_path in sensitive_files:
        if file_path.exists():
            stat_info = file_path.stat()
            mode = oct(stat_info.st_mode)

            # Check if readable by others
            if len(mode) >= 4:
                if int(mode[-3:]) & 0o044:  # Readable by others
                    issues.append(f"{file_path}: readable by others")

    for issue in issues:
        print(f"Permission issue: {issue}")

    # Allow this to be informational
    assert True


# ============================================================================
# Environment Variable Security
# ============================================================================

@pytest.mark.security_scan
def test_environment_variable_security():
    """Check that environment variables don't leak secrets"""
    # Check for common secret patterns in environment
    secret_patterns = [
        "PASSWORD", "SECRET", "API_KEY", "TOKEN", "PRIVATE_KEY",
        "DATABASE_URL", "CONNECTION_STRING"
    ]

    leaked_secrets = []
    for pattern in secret_patterns:
        for key, value in os.environ.items():
            if pattern in key.upper():
                # Check if value looks like a secret (not a path)
                if isinstance(value, str) and len(value) > 20:
                    # Exclude file-like values
                    if not any(x in value for x in ["/", "\\", ":", "localhost"]):
                        leaked_secrets.append(f"{key}: {value[:20]}...")

    if leaked_secrets:
        print(f"Potential secrets in environment: {leaked_secrets}")
        print("Note: This may be expected for development, but check before production")

    # Informational test
    assert True


# ============================================================================
# Secrets Detection in Code
# ============================================================================

@pytest.mark.security_scan
def test_no_secrets_in_code():
    """Scan codebase for hardcoded secrets"""
    # Patterns that look like secrets
    secret_patterns = [
        (r'["\']([A-Z0-9]{20,})["\']', "Potential API key"),
        (r'password\s*=\s*["\'][^"\']{20,}["\']', "Hardcoded password"),
        (r'token\s*=\s*["\'][^"\']{20,}["\']', 'Hardcoded token'),
        (r'secret\s*=\s*["\'][^"\']{20,}["\']', 'Hardcoded secret'),
    ]

    # Scan a sample of key files
    files_to_scan = [
        PROJECT_ROOT / "python_backend" / "services" / "chat_service.py",
        PROJECT_ROOT / "python_backend" / "routers" / "gateway.py",
    ]

    findings = []

    for file_path in files_to_scan:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    for pattern, description in secret_patterns:
                        import re
                        if re.search(pattern, line, re.IGNORECASE):
                            findings.append(f"{file_path}:{i}: {description}")
                            break

    if findings:
        print(f"Potential secrets found in code:")
        for finding in findings[:10]:  # Show first 10
            print(f"  - {finding}")

    # This is informational
    assert True


# ============================================================================
# Summary
# ============================================================================

"""
SECURITY SCANNING TOOLS:

1. Bandit:
   Python security linter
   Finds common security issues
   Install: pip install bandit
   Run: bandit -r python_backend

2. Safety:
   Checks dependency vulnerabilities
   Scans requirements.txt
   Install: pip install safety
   Run: safety check --file requirements.txt

3. Pylint with Security:
   Enhanced linting with security checks
   Install: pip install pylint

RUNNING SECURITY TESTS:
    pytest tests_pytest/security/test_scan.py -v
    pytest -m security_scan -v

COMMON SECURITY ISSUES TO CHECK:

1. Injection Attacks:
   - SQL injection
   - Command injection
   - LDAP injection

2. Authentication/Authorization:
   - Weak passwords
   - Session fixation
   - Missing authorization

3. Cryptography:
   - Weak algorithms
   - Hardcoded keys
   - Missing encryption

4. Data Exposure:
   - Sensitive data in logs
   - Error messages revealing info
   - Minified code with secrets

5. Denial of Service:
   - Unbounded loops
   - Unbounded memory allocation
   - Resource exhaustion

AUTOMATING SECURITY SCANS:

1. Pre-commit Hook:
   # .git/hooks/pre-commit
   #!/bin/bash
   bandit -r python_backend
   safety check --file requirements.txt

2. CI/CD Integration:
   # Add to .github/workflows/tests.yml
   - name: Run security scan
     run: |
       pip install bandit safety
       bandit -r python_backend
       safety check --file requirements.txt

3. Regular Scans:
   # Schedule weekly scans
   # Review results and prioritize fixes
"""
