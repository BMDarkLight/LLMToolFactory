import os
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool


def get_uri_source_tool(settings: Dict[str, Any], name: str):
    """
    Factory that returns a LangChain tool for URI search,
    preconfigured with connector settings (like fixed URL).
    """
    url = settings.get("url")

    @tool
    def uri_search(query: str) -> str:
        """
        Search for relevant text in a preconfigured live web page.
        Args:
            query: The question or topic to search for.
        Returns:
            Relevant text snippets if found, otherwise a fallback message.
        """
        if not url:
            return "Error: No URL provided in settings."

        try:
            response = httpx.get(url, follow_redirects=True, timeout=15.0)
            response.raise_for_status()
        except httpx.RequestError as e:
            return f"Error: Failed to fetch the content from {url}: {e}"
        except Exception as e:
            return f"Unexpected error fetching {url}: {e}"

        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text(separator=" ", strip=True)
        if not page_text:
            return f"Error: No text content extracted from {url}"

        query_lower = query.lower()
        page_text_lower = page_text.lower()
        index = page_text_lower.find(query_lower)

        if index == -1:
            snippet = page_text[:1000]
        else:
            start = max(0, index - 500)
            end = min(len(page_text), index + 500)
            snippet = page_text[start:end]

        return f"Content from {url}:\n\n{snippet}"

    uri_search.name = name
    return uri_search