from abc import abstractmethod
from typing import Iterator, AsyncGenerator, Any, Optional, Dict, Tuple, TYPE_CHECKING
from core.interfaces.plugin import BaseSystemPlugin

if TYPE_CHECKING:
    from core.db.query_builder import QueryBuilder

class BaseDriver(BaseSystemPlugin):
    def __init__(self, id: str, name: str, description: str = ""):
        self._id = id
        self._name = name
        self.description = description
        # self.config removal: Handled by BaseSystemPlugin property
        # self.enabled removal: Handled by BaseSystemPlugin property
        
    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    def load_config(self, config: dict):
        self.config.update(config)
        self.enabled = self.config.get("enabled", self.enabled)

    @property
    def config_schema(self) -> Optional[Dict[str, Any]]:
        """
        Return form schema for frontend configuration.
        """
        return None

    @abstractmethod
    async def load(self):
        """Initialize models/resources."""
        pass

class BaseTTSDriver(BaseDriver):
    def __init__(self, id: str, name: str, description: str=""):
        super().__init__(id, name, description)
        
    @abstractmethod
    async def generate_stream(self, text: str, voice: str, **kwargs) -> AsyncGenerator[bytes, None]:
        """Yields audio chunks (mp3/wav bytes)."""
        pass

    @property
    def group_id(self) -> str:
        return "driver.tts"


class BaseSTTDriver(BaseDriver):
    def __init__(self, id: str, name: str, description: str=""):
        super().__init__(id, name, description)

    @abstractmethod
    def transcribe(self, audio_data: Any, **kwargs) -> Dict[str, Any]:
        """
        Transcribes audio data (numpy array or bytes) to text.
        Returns dict: {
            "text": str, 
            "language": str, 
            "emotion": Optional[str], 
            "confidence": float
        }
        """
        pass

    @property
    def group_id(self) -> str:
        return "driver.stt"

class BaseVoiceAuthDriver(BaseDriver):
    def __init__(self, id: str, name: str, description: str=""):
        super().__init__(id, name, description)

    @abstractmethod
    def extract_embedding(self, audio: Any, sample_rate: int = 16000) -> Any:
        """Extracts 1D vector embedding from audio."""
        pass
        
    @abstractmethod
    def verify(self, audio: Any, profiles: Dict[str, Any], threshold: float) -> Tuple[bool, str, float]:
        """
        Verifies audio against a dictionary of {name: embedding}.
        Returns: (is_match, matched_name, score)
        """
        return (False, "", 0.0)

class BaseVisionDriver(BaseDriver):
    def __init__(self, id: str, name: str, description: str=""):
        super().__init__(id, name, description)

    @abstractmethod
    def unload(self):
        """Unload models to free memory."""
        pass
        
    @abstractmethod
    async def analyze(self, image: Any, prompt: str = "Describe this image.") -> str:
        """
        Analyze the image and return a text description.
        image: PIL Image
        """
        pass

class BaseMemoryDriver(BaseDriver):
    """
    Abstract driver for Memory/Vector Database operations.
    Supports both CRUD and Vector Search.
    """
    def __init__(self, id: str, name: str, description: str=""):
        super().__init__(id, name, description)

    @abstractmethod
    async def connect(self):
        """Establish connection to the database."""
        pass

    @abstractmethod
    async def close(self):
        """Close connection."""
        pass

    @abstractmethod
    async def initialize_schema(self):
        """
        Initialize necessary tables, indexes, and extensions.
        """
        pass

    @abstractmethod
    async def create(self, table: str, data: Dict[str, Any]) -> str:
        """Insert data and return ID."""
        pass

    @abstractmethod
    async def update(self, table: str, id: str, data: Dict[str, Any]) -> bool:
        """Update existing record."""
        pass
        
    @abstractmethod
    async def delete(self, table: str, id: str) -> bool:
        """Delete a record."""
        pass

    @abstractmethod
    def get_query_builder(self) -> 'QueryBuilder':
        """Return a QueryBuilder instance adapted for this driver's dialect."""
        pass
        
    @abstractmethod
    async def query(self, sql: str, params: Optional[Dict] = None) -> Any:
        """Execute raw query (Driver specific, fallback)."""
        pass

    @abstractmethod
    async def mark_memories_hit(self, memory_ids: list):
        """Update hit counts/last_access."""
        pass

    @abstractmethod
    async def search_vector(self, 
                          table: str, 
                          vector: list, 
                          limit: int, 
                          threshold: float,
                          filter_criteria: Optional[Dict] = None) -> list:
        """Vector similarity search."""
        pass

    @abstractmethod
    async def search_fulltext(self, 
                            table: str, 
                            query: str, 
                            limit: int,
                            fields: list,
                            filter_criteria: Optional[Dict] = None) -> list:
        """Full text / Substring search."""
        pass

    @abstractmethod
    async def search_hybrid(self,
                          query: str,
                          vector: list,
                          table: str,
                          limit: int,
                          threshold: float,
                          vector_weight: float = 0.5,
                          filter_criteria: Optional[Dict] = None) -> list:
         """Hybrid search."""
         pass

    # --- 馃枼锔?Knowledge Graph Extensions ---
    
    async def relate(self, 
                     subject: str, 
                     predicate: str, 
                     object: str, 
                     data: Optional[Dict] = None) -> bool:
        """
        Create a directed relationship (Subject)-[Predicate]->(Object).
        """
        raise NotImplementedError("Graph 'relate' not implemented for this driver.")

    async def get_neighbors(self, node_id: str, depth: int = 1) -> list:
        """Retrieve related entities."""
        raise NotImplementedError("Graph 'get_neighbors' not implemented for this driver.")

    # --- 馃搼 Realtime / Control Plane Extensions ---

    async def publish(self, channel: str, message: Dict[str, Any]):
        """Broadcast a message (Surreal LiveQuery or Postgres NOTIFY)."""
        raise NotImplementedError("Pub/Sub 'publish' not implemented for this driver.")

    async def listen(self, channel: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Subscribe to a channel."""
        raise NotImplementedError("Pub/Sub 'listen' not implemented for this driver.")
        yield {} # Type hint helper

class BaseLLMDriver(BaseDriver):
    """
    Abstract driver for LLM providers.
    """
    def __init__(self, id: str, name: str, description: str=""):
        super().__init__(id, name, description)

    @abstractmethod
    async def chat_completion(self, 
                            messages: list, 
                            model: str, 
                            temperature: float = 0.7, 
                            stream: bool = False,
                            **kwargs) -> Any:
        """
        Standard chat completion. 
        Returns content string (if stream=False) or AsyncGenerator (if stream=True).
        """
        pass

    @abstractmethod
    async def list_models(self) -> list:
        """List available models."""
        pass
