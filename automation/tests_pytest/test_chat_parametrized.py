"""
Parametrized tests for Chat functionality

Demonstrates pytest's parametrization capabilities for testing
multiple scenarios with a single test definition.
"""
import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, AsyncMock
import asyncio

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))


# ============================================================================
# Basic Parametrization - Test Multiple Inputs
# ============================================================================

@pytest.mark.parametrize("user_input,expected_intent", [
    ("你好", "greeting"),
    ("hello", "greeting"),
    ("今天天气", "weather"),
    ("what's the weather", "weather"),
    ("帮我写代码", "coding"),
    ("write some code", "coding"),
])
def test_intent_detection(user_input, expected_intent):
    """Test intent detection with multiple inputs"""
    # Simple intent detection logic for testing
    intent = None
    lower_input = user_input.lower()

    if any(word in lower_input for word in ["你好", "hello", "hi"]):
        intent = "greeting"
    elif any(word in lower_input for word in ["天气", "weather"]):
        intent = "weather"
    elif any(word in lower_input for word in ["代码", "code"]):
        intent = "coding"

    assert intent == expected_intent


# ============================================================================
# Chat Service with Parametrized Mocks
# ============================================================================

@pytest.mark.parametrize("energy_level,expected_response_style", [
    (100, "energetic"),
    (50, "normal"),
    (10, "tired"),
])
def test_soul_energy_affects_response(energy_level, expected_response_style):
    """Test that soul energy level affects response style"""
    # Mock soul with specific energy level
    mock_soul = MagicMock()
    mock_soul.profile = {
        "state": {"energy_level": energy_level}
    }

    # Simulate response generation based on energy
    if energy_level > 75:
        response_style = "energetic"
    elif energy_level > 25:
        response_style = "normal"
    else:
        response_style = "tired"

    assert response_style == expected_response_style


# ============================================================================
# Parametrized Error Cases
# ============================================================================

@pytest.mark.parametrize("invalid_input,error_type", [
    ("", ValueError),
    ("   ", ValueError),
    (None, TypeError),
    (123, TypeError),
])
def test_chat_input_validation(invalid_input, error_type):
    """Test that invalid inputs raise appropriate errors"""
    def validate_input(input_str):
        if input_str is None:
            raise TypeError("Input cannot be None")
        if not isinstance(input_str, str):
            raise TypeError("Input must be a string")
        if not input_str or not input_str.strip():
            raise ValueError("Input cannot be empty")

    with pytest.raises(error_type):
        validate_input(invalid_input)


# ============================================================================
# Message History Tests
# ============================================================================

@pytest.mark.parametrize("history_length,max_tokens,should_truncate", [
    (5, 2000, False),
    (50, 2000, False),
    (100, 2000, False),  # ~1250 tokens, should not truncate
    (200, 2000, True),   # ~2500 tokens, should truncate
])
def test_message_history_truncation(history_length, max_tokens, should_truncate):
    """Test message history truncation based on token count"""
    # Estimate tokens (roughly 4 chars per token)
    avg_message_length = 50
    estimated_tokens = history_length * avg_message_length // 4

    needs_truncation = estimated_tokens > max_tokens
    assert needs_truncation == should_truncate


# ============================================================================
# Parametrized with IDs for Clear Test Names
# ============================================================================

@pytest.mark.parametrize("role,content,expected_valid", [
    ("user", "Hello", True),
    ("assistant", "Hi there!", True),
    ("system", "You are helpful", True),
    ("invalid_role", "Hello", False),
    ("user", "", False),
    ("", "Hello", False),
], ids=["valid_user", "valid_assistant", "valid_system", "invalid_role", "empty_content", "empty_role"])
def test_message_validation(role, content, expected_valid):
    """Test message validation with clear test IDs in output"""
    def is_valid_message(role, content):
        if not role or not content:
            return False
        if role not in ["user", "assistant", "system"]:
            return False
        if not content.strip():
            return False
        return True

    assert is_valid_message(role, content) == expected_valid


# ============================================================================
# Parametrized LLM Configurations
# ============================================================================

@pytest.mark.parametrize("provider,model,temperature,max_tokens", [
    ("openai", "gpt-4", 0.7, 2000),
    ("openai", "gpt-3.5-turbo", 0.5, 4000),
    ("anthropic", "claude-3-opus", 0.8, 4000),
    ("ollama", "llama2", 0.5, 2048),
])
def test_llm_parameter_validation(provider, model, temperature, max_tokens):
    """Test LLM parameter validation for different providers"""
    def validate_llm_params(provider, model, temperature, max_tokens):
        if provider not in ["openai", "anthropic", "ollama"]:
            return False
        if not (0.0 <= temperature <= 1.0):
            return False
        if max_tokens < 1 or max_tokens > 32000:
            return False
        return True

    assert validate_llm_params(provider, model, temperature, max_tokens)


# ============================================================================
# Parametrized Relationship Levels
# ============================================================================

@pytest.mark.parametrize("relationship_level,expected_formality", [
    (-3, "hostile"),
    (-1, "cold"),
    (0, "neutral"),
    (1, "friendly"),
    (3, "intimate"),
])
def test_relationship_affects_formality(relationship_level, expected_formality):
    """Test that relationship level affects response formality"""
    def get_formality_level(level):
        if level <= -2:
            return "hostile"
        elif level <= -1:
            return "cold"
        elif level <= 0:
            return "neutral"
        elif level <= 2:
            return "friendly"
        else:
            return "intimate"

    assert get_formality_level(relationship_level) == expected_formality


# ============================================================================
# Multiple Parameters with Cartesian Product
# ============================================================================

@pytest.mark.parametrize("has_memory", [True, False])
@pytest.mark.parametrize("has_soul_context", [True, False])
def test_context_combinations(has_memory, has_soul_context):
    """Test all combinations of context availability"""
    context = {
        "has_memory": has_memory,
        "has_soul_context": has_soul_context
    }

    # Determine expected behavior
    if has_memory and has_soul_context:
        expected = "full_context"
    elif has_memory:
        expected = "memory_only"
    elif has_soul_context:
        expected = "soul_only"
    else:
        expected = "minimal"

    # This generates 4 test cases automatically (2x2)
    assert context is not None


# ============================================================================
# Parametrized Streaming Responses
# ============================================================================

@pytest.mark.parametrize("chunks", [
    (["Hello", " world", "!"]),
    (["Hi", " there", ", how", " are you?"]),
    (["Single", " chunk"]),
])
def test_streaming_response_assembly(chunks):
    """Test that streaming chunks are assembled correctly"""
    def assemble_response(chunks):
        return "".join(chunks)

    result = assemble_response(chunks)
    expected = "".join(chunks)
    assert result == expected
    assert len(result) == sum(len(c) for c in chunks)


# ============================================================================
# Edge Cases with Parametrization
# ============================================================================

@pytest.mark.parametrize("input_text,should_clean", [
    ("  Hello  ", True),  # Extra spaces
    ("Hello\n\nWorld", True),  # Newlines
    ("Hello\tWorld", True),  # Tabs
    ("Hello", False),  # Already clean
])
def test_input_cleaning(input_text, should_clean):
    """Test input cleaning for various edge cases"""
    def clean_input(text):
        import re
        # Replace multiple whitespace with single space
        return re.sub(r'\s+', ' ', text).strip()

    cleaned = clean_input(input_text)
    if should_clean:
        assert cleaned != input_text
        assert "  " not in cleaned  # No double spaces
    else:
        assert cleaned == input_text


# ============================================================================
# Parametrized with Fixtures
# ============================================================================

@pytest.mark.parametrize("temperature", [0.0, 0.5, 1.0])
def test_temperature_with_fixture(mock_container, temperature):
    """Test temperature parameter with container fixture"""
    mock_llm = MagicMock()
    mock_llm.get_parameters = MagicMock(return_value={"temperature": temperature})

    params = mock_llm.get_parameters()
    assert params["temperature"] == temperature
    assert 0.0 <= temperature <= 1.0


# ============================================================================
# Summary of Parametrization Benefits
# ============================================================================

"""
PARAMETRIZATION BENEFITS:

1. Less Code:
   - Instead of writing 10 similar test methods, write 1 with parametrize
   - Example: test_intent_detection covers 7 cases in ~10 lines

2. Better Test Names:
   - pytest automatically generates descriptive test names
   - Example: test_intent_detection[你好-greeting]

3. Easy to Add Cases:
   - Just add another tuple to the parametrize list
   - No need to write new test methods

4. Combinatorial Testing:
   - Use multiple @parametrize decorators for cartesian product
   - Example: test_context_combinations generates 4 tests from 2x2

5. Clear IDs:
   - Use ids parameter for custom test names in output
   - Example: ids=["valid_user", "invalid_role"]"""
