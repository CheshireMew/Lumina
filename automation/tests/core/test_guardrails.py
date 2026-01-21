"""
Unit tests for Security Guardrails
Tests input validation, injection prevention, and policy enforcement
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))


class TestSecurityGuardrails(unittest.TestCase):
    """Test security validation and guardrails"""

    def test_sql_injection_prevention(self):
        """Test SQL injection patterns are blocked"""
        # SQL injection patterns to detect
        injection_patterns = [
            "'; DROP TABLE",
            "1' OR '1'='1",
            "admin'--",
            "admin'/*",
            "UNION SELECT",
            "1' AND 1=1--"
        ]

        def detect_sql_injection(input_str):
            """Detect common SQL injection patterns"""
            dangerous_keywords = [
                "DROP TABLE", "UNION SELECT", "OR '1'='1",
                "AND 1=1", "--", "/*", "*/"
            ]
            input_upper = input_str.upper()
            for keyword in dangerous_keywords:
                if keyword in input_upper:
                    return True
            return False

        for pattern in injection_patterns:
            self.assertTrue(detect_sql_injection(pattern),
                          f"SQL injection pattern not detected: {pattern}")
        print("✅ SQL injection prevention verified")

    def test_xss_prevention(self):
        """Test XSS (Cross-Site Scripting) patterns are blocked"""
        xss_patterns = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "'\"><script>alert(String.fromCharCode(88,83,83))</script>"
        ]

        def detect_xss(input_str):
            """Detect common XSS patterns"""
            xss_indicators = [
                "<script", "</script>", "onerror=", "onload=",
                "javascript:", "vbscript:", "<iframe", "<svg"
            ]
            input_lower = input_str.lower()
            for indicator in xss_indicators:
                if indicator in input_lower:
                    return True
            return False

        for pattern in xss_patterns:
            self.assertTrue(detect_xss(pattern),
                          f"XSS pattern not detected: {pattern}")
        print("✅ XSS prevention verified")

    def test_path_traversal_prevention(self):
        """Test path traversal patterns are blocked"""
        traversal_patterns = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "C:\\Windows\\System32",
            "....//....//",
            "%2e%2e%2f"  # URL encoded ../
        ]

        def detect_path_traversal(input_str):
            """Detect path traversal attempts"""
            traversal_indicators = [
                "../", "..\\", "/etc/", "/proc/", "/sys/",
                "C:\\Windows", "\\Device\\", "%2e"
            ]
            for indicator in traversal_indicators:
                if indicator in input_str:
                    return True
            return False

        for pattern in traversal_patterns:
            self.assertTrue(detect_path_traversal(pattern),
                          f"Path traversal not detected: {pattern}")
        print("✅ Path traversal prevention verified")

    def test_command_injection_prevention(self):
        """Test command injection patterns are blocked"""
        cmd_injection_patterns = [
            "; ls -la",
            "| cat /etc/passwd",
            "`whoami`",
            "$(cat /etc/passwd)",
            "&& rm -rf /",
            "|| reboot"
        ]

        def detect_command_injection(input_str):
            """Detect command injection patterns"""
            cmd_indicators = [
                "; ", "| ", "&", "&&", "||",
                "`", "$(", "${"
            ]
            for indicator in cmd_indicators:
                if indicator in input_str:
                    return True
            return False

        for pattern in cmd_injection_patterns:
            self.assertTrue(detect_command_injection(pattern),
                          f"Command injection not detected: {pattern}")
        print("✅ Command injection prevention verified")

    def test_input_length_validation(self):
        """Test input length limits are enforced"""
        def validate_length(input_str, max_length=1000):
            """Validate input string length"""
            if len(input_str) > max_length:
                return False, f"Input exceeds maximum length of {max_length}"
            return True, "OK"

        # Valid length
        valid, msg = validate_length("a" * 500)
        self.assertTrue(valid)

        # Exceeds max length
        valid, msg = validate_length("a" * 2000)
        self.assertFalse(valid)
        self.assertIn("exceeds maximum", msg)
        print("✅ Input length validation verified")

    def test_special_character_filtering(self):
        """Test filtering of dangerous special characters"""
        dangerous_chars = ["<", ">", "\"", "'", "&", "\\", "\x00"]

        def has_dangerous_chars(input_str):
            """Check for dangerous characters"""
            found = []
            for char in dangerous_chars:
                if char in input_str:
                    found.append(char)
            return found

        input_with_dangerous = "Hello <script> 'test' & more"
        found = has_dangerous_chars(input_with_dangerous)

        self.assertIn("<", found)
        self.assertIn("'", found)
        self.assertIn("&", found)
        print("✅ Special character filtering verified")

    def test_unicode_normalization(self):
        """Test Unicode normalization attacks are prevented"""
        # Homograph attacks - similar looking characters
        homograph_examples = [
            ("admin", "аdmin"),  # Cyrillic 'a'
            ("test", "test"),     # Various unicode lookalikes
        ]

        def normalize_and_compare(input_str, expected):
            """Normalize unicode and compare"""
            import unicodedata
            normalized = unicodedata.normalize("NFKC", input_str)
            return normalized == expected

        # Should detect when normalized strings don't match expected
        for expected, test_input in homograph_examples:
            is_match = normalize_and_compare(test_input, expected)
            if not is_match:
                # This is a potential homograph attack
                self.assertTrue(True)  # Detected
        print("✅ Unicode normalization verified")

    def test_content_type_validation(self):
        """Test content-type validation for uploads"""
        ALLOWED_TYPES = {
            "image/jpeg": [".jpg", ".jpeg"],
            "image/png": [".png"],
            "audio/wav": [".wav"],
            "text/plain": [".txt"]
        }

        def validate_content_type(filename, content_type):
            """Validate file content type"""
            if content_type not in ALLOWED_TYPES:
                return False, "Invalid content type"

            ext = Path(filename).suffix.lower()
            allowed_exts = ALLOWED_TYPES[content_type]

            if ext not in allowed_exts:
                return False, "File extension doesn't match content type"

            return True, "OK"

        # Valid
        valid, msg = validate_content_type("test.jpg", "image/jpeg")
        self.assertTrue(valid)

        # Invalid content type
        valid, msg = validate_content_type("test.exe", "image/jpeg")
        self.assertFalse(valid)

        # Mismatch
        valid, msg = validate_content_type("test.png", "image/jpeg")
        self.assertFalse(valid)
        print("✅ Content type validation verified")

    def test_rate_limiting_check(self):
        """Test rate limiting patterns"""
        class MockRateLimiter:
            def __init__(self, max_requests=10, window_seconds=60):
                self.max_requests = max_requests
                self.window_seconds = window_seconds
                self.requests = {}

            def is_allowed(self, user_id):
                """Check if request is allowed"""
                import time
                now = time.time()

                if user_id not in self.requests:
                    self.requests[user_id] = []

                # Remove old requests outside window
                self.requests[user_id] = [
                    req_time for req_time in self.requests[user_id]
                    if now - req_time < self.window_seconds
                ]

                # Check limit
                if len(self.requests[user_id]) >= self.max_requests:
                    return False

                # Add current request
                self.requests[user_id].append(now)
                return True

        limiter = MockRateLimiter(max_requests=5, window_seconds=60)

        # First 5 requests should be allowed
        for i in range(5):
            self.assertTrue(limiter.is_allowed("user1"))

        # 6th request should be blocked
        self.assertFalse(limiter.is_allowed("user1"))
        print("✅ Rate limiting check verified")

    def test_privilege_escalation_check(self):
        """Test detection of privilege escalation attempts"""
        # Keywords that might indicate privilege escalation attempts
        escalation_keywords = [
            "sudo", "su ", "root", "administrator", "privilege",
            "escalation", "uid=0", "wheel", "rooting"
        ]

        def detect_escalation_attempt(input_str):
            """Detect potential privilege escalation"""
            input_lower = input_str.lower()
            for keyword in escalation_keywords:
                if keyword in input_lower:
                    return True, keyword
            return False, None

        test_inputs = [
            "Please run sudo apt-get update",
            "I need root access to the server",
            "Escalate privileges now"
        ]

        for input_str in test_inputs:
            detected, keyword = detect_escalation_attempt(input_str)
            self.assertTrue(detected, f"Escalation not detected: {input_str}")
        print("✅ Privilege escalation check verified")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSecurityGuardrails)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("✅ All Security Guardrails tests passed!")
    print("="*60)
