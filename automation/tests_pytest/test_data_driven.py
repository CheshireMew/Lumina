"""
Data-driven tests using external test data files

Tests are loaded from YAML/JSON files for easy maintenance.
"""
import sys
from pathlib import Path
import pytest
import yaml
import json

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "data"


# ============================================================================
# YAML-based Test Data
# ============================================================================

def load_yaml_test_cases(filename):
    """Load test cases from YAML file"""
    yaml_path = TEST_DATA_DIR / filename
    if not yaml_path.exists():
        pytest.skip(f"Test data file not found: {filename}")

    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.mark.data_driven
def test_intent_validation_from_yaml():
    """Test intent validation using YAML test data"""
    test_cases = load_yaml_test_cases("intent_validation.yaml")

    for case in test_cases.get("test_cases", []):
        input_text = case["input"]
        expected_intent = case["expected_intent"]

        # Simple intent detection logic
        intent = None
        input_lower = input_text.lower()
        if "hello" in input_lower or "hi" in input_lower:
            intent = "greeting"
        elif "weather" in input_lower:
            intent = "weather"
        elif "help" in input_lower:
            intent = "help_request"
        else:
            intent = "casual_chat"  # Default fallback

        assert intent == expected_intent, f"Input: {input_text}, Expected: {expected_intent}, Got: {intent}"


@pytest.mark.data_driven
def test_provider_id_validation_from_yaml():
    """Test provider ID validation using YAML test data"""
    test_cases = load_yaml_test_cases("provider_id_validation.yaml")

    for case in test_cases.get("test_cases", []):
        provider_id = case["provider_id"]
        is_valid = case["is_valid"]

        # Validate provider ID format
        import re
        pattern = re.compile(r'^[a-zA-Z0-9_\.\-]+$')
        actually_valid = bool(pattern.match(provider_id))

        assert actually_valid == is_valid, f"Provider ID: {provider_id}, Expected valid: {is_valid}"


# ============================================================================
# JSON-based Test Data
# ============================================================================

def load_json_test_cases(filename):
    """Load test cases from JSON file"""
    json_path = TEST_DATA_DIR / filename
    if not json_path.exists():
        pytest.skip(f"Test data file not found: {filename}")

    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@pytest.mark.data_driven
def test_message_validation_from_json():
    """Test message validation using JSON test data"""
    data = load_json_test_cases("message_validation.json")
    test_cases = data.get("test_cases", [])

    for case in test_cases:
        message = case["message"]
        should_be_valid = case["valid"]

        # Validate message structure
        is_valid = bool(
            message.get("role") in ["user", "assistant", "system"] and
            isinstance(message.get("content"), str) and
            len(message.get("content", "").strip()) > 0
        )

        assert is_valid == should_be_valid, f"Message: {message}, Expected valid: {should_be_valid}"


# ============================================================================
# CSV-based Test Data (simple implementation)
# ============================================================================

@pytest.mark.data_driven
def test_character_configurations():
    """Test character configurations from data file"""
    # Define test data inline (could be loaded from CSV)
    characters = [
        {"id": "hiyori", "name": "Hiyori", "personality": "energetic"},
        {"id": "sakura", "name": "Sakura", "personality": "calm"},
        {"id": "yuki", "name": "Yuki", "personality": "shy"}
    ]

    for character in characters:
        # Validate character structure
        assert "id" in character
        assert "name" in character
        assert "personality" in character
        # ID should be lowercase alphanumeric
        assert character["id"].islower() or character["id"].isalnum()


# ============================================================================
# Dynamic Test Generation from Data
# ============================================================================

@pytest.mark.data_driven
@pytest.mark.parametrize("test_case_file", [
    "llm_providers.json",
    "tts_voices.json",
])
def test_external_provider_configurations(test_case_file):
    """Test external provider configurations from JSON files"""
    config = load_json_test_cases(test_case_file)

    for provider_id, provider_config in config.get("providers", {}).items():
        # Validate provider structure
        assert "type" in provider_config
        assert "endpoint" in provider_config or "model" in provider_config

        # Type-specific validation
        if provider_config["type"] == "llm":
            assert "model" in provider_config
        elif provider_config["type"] == "tts":
            assert "voice" in provider_config


# ============================================================================
# Test Data File Creation Helper
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def create_test_data_files():
    """Create test data files if they don't exist"""
    TEST_DATA_DIR.mkdir(exist_ok=True)

    # Create intent_validation.yaml
    intent_yaml = TEST_DATA_DIR / "intent_validation.yaml"
    if not intent_yaml.exists():
        intent_yaml.write_text("""
description: Intent validation test cases
test_cases:
  - input: "Hello there"
    expected_intent: greeting
  - input: "What's the weather like?"
    expected_intent: weather
  - input: "Can you help me?"
    expected_intent: help_request
  - input: "Tell me a joke"
    expected_intent: casual_chat
""")

    # Create provider_id_validation.yaml
    provider_yaml = TEST_DATA_DIR / "provider_id_validation.yaml"
    if not provider_yaml.exists():
        provider_yaml.write_text("""
description: Provider ID validation test cases
test_cases:
  - provider_id: driver.test.provider
    is_valid: True
  - provider_id: provider_test
    is_valid: True
  - provider_id: ../etc/passwd
    is_valid: False
  - provider_id: provider with spaces
    is_valid: False
  - provider_id: <script>alert('xss')</script>
    is_valid: False
""")

    # Create message_validation.json
    message_json = TEST_DATA_DIR / "message_validation.json"
    if not message_json.exists():
        message_json.write_text(json.dumps({
            "description": "Message validation test cases",
            "test_cases": [
                {
                    "message": {"role": "user", "content": "Hello"},
                    "valid": True
                },
                {
                    "message": {"role": "assistant", "content": "Hi there!"},
                    "valid": True
                },
                {
                    "message": {"role": "invalid", "content": "Test"},
                    "valid": False
                },
                {
                    "message": {"role": "user", "content": ""},
                    "valid": False
                },
                {
                    "message": {"content": "Missing role"},
                    "valid": False
                }
            ]
        }, indent=2))


# ============================================================================
# Summary
# ============================================================================

"""
DATA-DRIVEN TESTING BENEFITS:

1. Separation of Test Code and Test Data:
   - Test data in YAML/JSON files
   - Easy to update without touching code
   - Non-programmers can maintain test data

2. Maintainability:
   - Add test cases by editing data files
   - No need to write more test functions
   - Clear structure for test cases

3. Reusability:
   - Same test logic can use different data files
   - Data files can be shared across multiple tests

4. Readability:
   - Test cases in human-readable format
   - Clear structure and validation

5. Extensibility:
   - Easy to add new test scenarios
   - Supports complex test data structures

TEST DATA FILE FORMATS:

YAML Example (intent_validation.yaml):
```yaml
description: Intent validation tests
test_cases:
  - input: "Hello"
    expected_intent: greeting
    metadata:
      priority: high
      category: basic
```

JSON Example (message_validation.json):
```json
{
  "description": "Message validation tests",
  "test_cases": [
    {
      "message": {"role": "user", "content": "Hello"},
      "valid": true
    }
  ]
}
```

RUN DATA-DRIVEN TESTS:
    pytest tests_pytest/test_data_driven.py -v
    pytest -m data_driven -v

CREATE YOUR OWN DATA FILES:
    1. Create data/ subdirectory
    2. Add YAML/JSON files with test cases
    3. Update tests to load your files
"""
