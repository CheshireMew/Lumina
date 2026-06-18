"""
Data generators for property-based and parametrized testing

These functions generate random or structured test data.
"""
import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Any


def generate_test_user_input(
    min_length: int = 1,
    max_length: int = 500
) -> str:
    """Generate a random user input string"""
    length = random.randint(min_length, max_length)
    words = ["hello", "world", "test", "input", "message",
             "how", "are", "you", "doing", "today"]
    return " ".join(random.choice(words) for _ in range(length))


def generate_test_memory(
    content: str = None,
    with_embedding: bool = True,
    embedding_dim: int = 512
) -> Dict:
    """Generate a test memory record"""
    if content is None:
        content = f"Test memory {random.randint(1000, 9999)}"

    memory = {
        "id": f"mem_{random.randint(1000, 9999)}",
        "content": content,
        "created_at": datetime.now().isoformat(),
        "metadata": {
            "source": random.choice(["chat", "system", "user"]),
            "importance": random.random()
        }
    }

    if with_embedding:
        memory["embedding"] = [random.uniform(-1, 1) for _ in range(embedding_dim)]

    return memory


def generate_test_messages(
    count: int = 5,
    include_system: bool = False
) -> List[Dict]:
    """Generate test chat messages"""
    messages = []

    if include_system:
        messages.append({
            "role": "system",
            "content": "You are a helpful assistant."
        })

    for i in range(count):
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({
            "role": role,
            "content": f"Message {i + 1}"
        })

    return messages


def generate_random_text(
    min_length: int = 10,
    max_length: int = 1000,
    include_special_chars: bool = False
) -> str:
    """Generate random text for testing"""
    chars = string.ascii_letters + string.digits + " "
    if include_special_chars:
        chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"

    length = random.randint(min_length, max_length)
    return "".join(random.choice(chars) for _ in range(length))


def generate_test_timestamps(
    count: int = 10,
    days_back: int = 30
) -> List[str]:
    """Generate test timestamps"""
    now = datetime.now()
    timestamps = []

    for _ in range(count):
        days_ago = random.randint(0, days_back)
        hours_ago = random.randint(0, 23)
        timestamp = now - timedelta(days=days_ago, hours=hours_ago)
        timestamps.append(timestamp.isoformat())

    return timestamps


def generate_test_module_ids(count: int = 5) -> List[str]:
    """Generate test capability module IDs"""
    prefixes = ["module", "provider", "vendor"]
    ids = []

    for _ in range(count):
        prefix = random.choice(prefixes)
        name = "".join(random.choices(string.ascii_lowercase, k=8))
        ids.append(f"{prefix}.{name}")

    return ids


def generate_test_user_ids(count: int = 10) -> List[str]:
    """Generate test user IDs"""
    return [f"user_{random.randint(10000, 99999)}" for _ in range(count)]


def generate_test_characters(count: int = 3) -> List[Dict]:
    """Generate test character configs"""
    characters = []
    names = ["hiyori", "sakura", "yuki"]

    for i in range(min(count, len(names))):
        characters.append({
            "id": names[i],
            "name": names[i].capitalize(),
            "description": f"Test character {i + 1}",
            "personality": {
                "traits": random.sample(["shy", "energetic", "calm", "cheerful"], 2)
            },
            "voice": {
                "provider": random.choice(["edge", "openai"]),
                "model": f"model-{i}"
            }
        })

    return characters


# ============================================================================
# Hypothesis Strategies for Property-Based Testing
# ============================================================================

try:
    from hypothesis import strategies as st

    # Text strategies
    user_input_strategy = st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'Z'), max_codepoint=127),
        min_size=1,
        max_size=500
    )

    # Number strategies
    probability_strategy = st.floats(min_value=0.0, max_value=1.0)
    importance_strategy = st.floats(min_value=0.0, max_value=1.0)
    energy_level_strategy = st.integers(min_value=0, max_value=100)

    # Data structure strategies
    message_strategy = st.fixed_dictionaries({
        "role": st.sampled_from(["user", "assistant", "system"]),
        "content": st.text(max_size=1000)
    })

    memory_strategy = st.fixed_dictionaries({
        "id": st.text(min_size=1, max_size=50),
        "content": st.text(max_size=1000),
        "importance": st.floats(min_value=0.0, max_value=1.0)
    })

except ImportError:
    # Hypothesis not installed - strategies will be None
    user_input_strategy = None
    probability_strategy = None
    importance_strategy = None
    energy_level_strategy = None
    message_strategy = None
    memory_strategy = None


# ============================================================================
# Edge Case Generators
# ============================================================================

def generate_edge_case_inputs() -> List[str]:
    """Generate edge case inputs for testing"""
    return [
        "",  # Empty
        " ",  # Single space
        "\n",  # Newline only
        "\t",  # Tab only
        "a" * 10000,  # Very long
        "Hello\n\n\nWorld",  # Multiple newlines
        "  Spaces  everywhere  ",  # Extra spaces
        "😀🎉🚀",  # Emojis
        "Mixed中文and English",  # Mixed languages
        "<script>alert('xss')</script>",  # XSS attempt
        "../../etc/passwd",  # Path traversal attempt
        "'; DROP TABLE users; --",  # SQL injection attempt
    ]


def generate_edge_case_messages() -> List[Dict]:
    """Generate edge case messages"""
    return [
        {"role": "", "content": "test"},  # Empty role
        {"role": "user", "content": ""},  # Empty content
        {"role": "invalid", "content": "test"},  # Invalid role
        {"role": "user", "content": "a" * 10000},  # Very long content
        {"content": "test"},  # Missing role
        {"role": "user"},  # Missing content
    ]


def generate_edge_case_numbers() -> List[float]:
    """Generate edge case numbers"""
    return [
        0.0,
        1.0,
        -1.0,
        0.0001,
        0.9999,
        float('inf'),
        float('-inf'),
        1e10,
        -1e10,
    ]
