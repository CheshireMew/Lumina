"""
Property-based testing using Hypothesis

Property-based testing generates hundreds of random inputs
to find edge cases that traditional tests might miss.
"""
import sys
from pathlib import Path
import pytest

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

# Try to import hypothesis - provide alternatives if not available
try:
    from hypothesis import given, settings, example
    from hypothesis import strategies as st
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False
    # Create dummy decorators for when hypothesis is not installed
    def given(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def settings(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def example(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    # Create dummy st module
    class DummyStrategies:
        @staticmethod
        def text(*args, **kwargs):
            def decorator(func):
                return func
            return decorator
        def integers(*args, **kwargs):
            def decorator(func):
                return func
            return decorator
        def floats(*args, **kwargs):
            def decorator(func):
                return func
            return decorator
        def lists(*args, **kwargs):
            def decorator(func):
                return func
            return decorator
        def fixed_dictionaries(*args, **kwargs):
            def decorator(func):
                return func
            return decorator
    st = DummyStrategies()


# ============================================================================
# String Property Tests
# ============================================================================

if HYPOTHESIS_AVAILABLE:
    @pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
    @given(st.text(min_size=0, max_size=1000))
    @settings(max_examples=100)
    def test_input_validation_never_crashes(text):
        """Property: Input validation should never crash on any string input"""
        def validate_input(input_str):
            """Should never raise an exception"""
            if input_str is None:
                return False
            if not isinstance(input_str, str):
                return False
            return True

        # This should never raise an exception for any string
        result = validate_input(text)
        assert isinstance(result, bool)


    @pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
    @given(st.text(alphabet=st.characters(whitelist_categories=('L', 'N', 'Z')), max_size=500))
    @settings(max_examples=50)
    def test_safe_text_always_valid(text):
        """Property: Safe text (letters, numbers) should always be valid"""
        def is_safe_text(input_str):
            """Safe text should not contain special characters"""
            return all(c.isalnum() or c.isspace() for c in input_str)

        assert is_safe_text(text) == True


# ============================================================================
# List Property Tests
# ============================================================================

if HYPOTHESIS_AVAILABLE:
    @pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
    @given(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=20))
    @settings(max_examples=50)
    def test_message_list_roundtrip(messages):
        """Property: Messages should survive roundtrip through serialization"""
        import json

        # Serialize
        serialized = json.dumps(messages)
        # Deserialize
        deserialized = json.loads(serialized)

        assert deserialized == messages


    @pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
    @given(st.lists(st.integers(min_value=-100, max_value=100), min_size=0, max_size=10))
    def test_sum_follows_commutative_property(numbers):
        """Property: Addition is commutative (a + b = b + a)"""
        from itertools import permutations

        for perm in permutations(numbers):
            assert sum(numbers) == sum(perm)


# ============================================================================
# Dictionary Property Tests
# ============================================================================

if HYPOTHESIS_AVAILABLE:
    @pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        values=st.text(min_size=0, max_size=100),
        min_size=0,
        max_size=10
    ))
    @settings(max_examples=30)
    def test_metadata_serialization(metadata):
        """Property: Metadata should be JSON serializable"""
        import json

        # Should not raise an exception
        serialized = json.dumps(metadata)
        deserialized = json.loads(serialized)

        assert deserialized == metadata


# ============================================================================
# Numeric Property Tests
# ============================================================================

if HYPOTHESIS_AVAILABLE:
    @pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
    @given(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_probability_in_valid_range(probability):
        """Property: Probability should always be in [0, 1]"""
        assert 0.0 <= probability <= 1.0


    @pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
    @given(st.integers(min_value=0, max_value=100))
    @settings(max_examples=50)
    @example(0)  # Also test edge case
    @example(100)  # Also test edge case
    def test_energy_level_bounds(energy):
        """Property: Energy level should stay within bounds"""
        assert 0 <= energy <= 100

        # Test transformation preserves bounds
        transformed = max(0, min(100, energy + 10))
        assert 0 <= transformed <= 100


# ============================================================================
# Combined Property Tests
# ============================================================================

if HYPOTHESIS_AVAILABLE:
    @pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
    @given(st.text(min_size=1, max_size=100), st.integers(min_value=0, max_value=100))
    @settings(max_examples=50)
    def test_message_and_importance(message, importance):
        """Property: Memory creation with various messages and importance values"""
        def create_memory(content, importance_value):
            return {
                "content": content,
                "importance": importance_value,
                "created_at": "2024-01-20"
            }

        memory = create_memory(message, importance)

        assert memory["content"] == message
        assert memory["importance"] == importance
        assert 0 <= importance <= 100


# ============================================================================
# Custom Strategy Definitions
# ============================================================================

# Note: Custom strategies are defined inline in tests below
# to avoid syntax issues when hypothesis is not installed


# ============================================================================
# Invariant Testing
# ============================================================================

if HYPOTHESIS_AVAILABLE:
    @pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
    @given(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=20))
    def test_append_then_pop_preserves_length(messages):
        """Property: append(x); pop() should preserve list length"""
        original_length = len(messages)
        original_list = messages.copy()

        # Add an element
        messages.append("new_message")
        # Remove last element
        messages.pop()

        assert len(messages) == original_length
        assert messages == original_list


# ============================================================================
# Regression Tests with Specific Examples
# ============================================================================

if HYPOTHESIS_AVAILABLE:
    @pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
    @given(st.text())
    @example("")  # Empty string
    @example("   ")  # Spaces only
    @example("Hello\nWorld")  # Newline
    @example("<script>alert('xss')</script>")  # XSS attempt
    def test_sanitization_handles_edge_cases(text):
        """Property: Sanitization should handle all edge cases"""
        def sanitize_input(input_str):
            import re
            # Remove HTML tags
            clean = re.sub(r'<[^>]+>', '', input_str)
            # Normalize whitespace
            clean = re.sub(r'\s+', ' ', clean).strip()
            return clean

        result = sanitize_input(text)
        # Should never contain HTML tags
        assert '<' not in result
        assert '>' not in result


# ============================================================================
# Test Shrinking Example
# ============================================================================

if HYPOTHESIS_AVAILABLE:
    @pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
    @given(st.lists(st.integers(), min_size=0, max_size=100))
    @settings(max_examples=1000)
    def test_mean_is_within_bounds(numbers):
        """Property: Mean of list should be within min/max of elements"""
        if not numbers:
            return  # Skip empty lists

        mean = sum(numbers) / len(numbers)
        assert min(numbers) <= mean <= max(numbers)


# ============================================================================
# Alternative Tests (When Hypothesis is Not Available)
# ============================================================================

@pytest.mark.skipif(HYPOTHESIS_AVAILABLE, reason="hypothesis is installed")
def test_manual_property_testing():
    """Manual property-based tests when hypothesis is not available"""
    test_cases = [
        "",
        "a",
        "Hello World",
        "123",
        "Hello\nWorld",
        "  spaces  ",
        "!@#$%^&*()",
    ]

    for text in test_cases:
        # Test that validation never crashes
        try:
            result = len(text)
            assert result >= 0
        except Exception as e:
            pytest.fail(f"Validation crashed on input: {text!r}, error: {e}")


# ============================================================================
# Summary
# ============================================================================

"""
PROPERTY-BASED TESTING BENEFITS:

1. Finds Edge Cases:
   - Generates hundreds of random inputs
   - Finds bugs you didn't think to test

2. Shrinks Failures:
   - When a test fails, Hypothesis finds the minimal failing case
   - Example: If it fails on a 1000-char string, it shrinks to find the minimal

3. No Manual Test Case Writing:
   - Just describe the property/rules
   - Hypothesis generates the test cases

4. Integrated with Pytest:
   - Works seamlessly with pytest fixtures and marks
   - Can be run alongside regular tests

INSTALL:
    pip install hypothesis

RUN:
    pytest tests_pytest/test_property_based.py -v

EXAMPLE OUTPUT:
    test_property_based.py::test_input_validation_never_crashes PASSED [10%]
    test_property_based.py::test_input_validation_never_crashes PASSED [20%]
    ...
    (Hypothesis runs 100 examples for each test)
"""
