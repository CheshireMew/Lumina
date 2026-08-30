from model_manager import model_manager

DEFAULT_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


def create_semantic_encoder(model_name: str = DEFAULT_EMBEDDING_MODEL):
    """Create a lazy local sentence-transformer encoder stored under Lumina data."""
    return model_manager.create_lazy_embedding_encoder(model_name)


_default_encoder = create_semantic_encoder()


def encode_text(text: str) -> list[float]:
    """Compatibility entrypoint backed by the real semantic model."""
    vector = _default_encoder(text)
    return vector.tolist() if hasattr(vector, "tolist") else list(vector)
