from abc import ABC, abstractmethod

class SearchProvider(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        pass

    @abstractmethod
    async def search(self, query: str) -> str:
        """Execute search and return markdown summary."""
        pass
