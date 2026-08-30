from typing import Protocol

class SearchProvider(Protocol):
    id: str
    name: str
    description: str

    async def search(self, query: str) -> str:
        ...
