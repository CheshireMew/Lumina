import logging
import json
from typing import List, Dict, Any, Optional
from core.interfaces.search import SearchProvider

logger = logging.getLogger("DuckDuckGoSearch")

class DuckDuckGoSearch(SearchProvider):
    """
    Native implementation of DuckDuckGo Search using `duckduckgo-search` library.
    No API Key required.
    """
    def __init__(self, max_results: int = 5):
        self.max_results = max_results
        try:
            from duckduckgo_search import DDGS
            self.ddgs = DDGS()
            self._available = True
        except ImportError:
            self._available = False
            logger.error("duckduckgo-search library not found. Please pip install duckduckgo-search")

    @property
    def id(self) -> str:
        return "duckduckgo"

    async def search(self, query: str) -> str:
        """
        Executes a web search and returns a formatted string summary.
        """
        if not self._available:
            return "Error: duckduckgo-search library is not installed."
            
        try:
            # valid arguments for DDGS().text() in recent versions:
            # keywords, region='wt-wt', safesearch='moderate', timelimit=None, max_results=None
            
            # The library is synchronous or async depending on version/usage. 
            # DDGS() methods are synchronous usually. We run in thread pool to avoid blocking async loop.
            import asyncio
            from duckduckgo_search import DDGS

            def _do_search():
                with DDGS() as ddgs:
                    # limiting results via max_results arg or manual slice
                    results = list(ddgs.text(query, max_results=self.max_results))
                return results

            results = await asyncio.to_thread(_do_search)

            if not results:
                return "No results found."

            # Format Results
            formatted_output = f"Search Results for '{query}' (via DuckDuckGo):\n\n"
            
            for i, result in enumerate(results):
                title = result.get("title", "No Title")
                url = result.get("href", "#")
                desc = result.get("body", "No description provided.")
                
                # Truncate description
                if len(desc) > 300:
                    desc = desc[:297] + "..."
                    
                formatted_output += f"{i+1}. [{title}]({url})\n   {desc}\n\n"
                
            return formatted_output.strip()

        except Exception as e:
            logger.error(f"DDG Search execution failed: {e}")
            return f"Error during search: {str(e)}"
