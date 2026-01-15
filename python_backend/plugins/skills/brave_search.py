import os
import json
import logging
import httpx
from typing import List, Dict, Any, Optional
from core.interfaces.search import SearchProvider

logger = logging.getLogger("BraveSearch")

class BraveSearch(SearchProvider):
    """
    Native implementation of Brave Search API.
    Docs: https://api.search.brave.com/app/documentation/web-search/get-started
    """
    def __init__(self, api_key: str, max_results: int = 5):
        self.api_key = api_key
        self.max_results = max_results
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    @property
    def id(self) -> str:
        return "brave"        self.api_key = api_key
        self.max_results = max_results
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    async def search(self, query: str) -> str:
        """
        Executes a web search and returns a formatted string summary.
        """
        if not self.api_key:
            return "Error: Brave API Key is missing. Please configure BRAVE_API_KEY."

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key
        }
        
        params = {
            "q": query,
            "count": self.max_results
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.base_url, headers=headers, params=params)
                
                if response.status_code == 403:
                    return "Error: Invalid Brave API Key (403 Forbidden)."
                
                if response.status_code != 200:
                    return f"Error: Search failed with status {response.status_code}: {response.text}"
                
                data = response.json()
                results = data.get("web", {}).get("results", [])
                
                if not results:
                    return "No results found."
                
                # Format Results
                formatted_output = f"Search Results for '{query}':\n\n"
                
                for i, result in enumerate(results[:self.max_results]):
                    title = result.get("title", "No Title")
                    url = result.get("url", "#")
                    desc = result.get("description", "No description provided.")
                    
                    # Truncate description to save tokens
                    if len(desc) > 300:
                        desc = desc[:297] + "..."
                        
                    formatted_output += f"{i+1}. [{title}]({url})\n   {desc}\n\n"
                    
                return formatted_output.strip()

        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            return f"Error during search: {str(e)}"

# Singleton / Factory if needed, but for now just the class
