import os
from typing import List, Dict, Any
import numpy as np
import httpx
from bs4 import BeautifulSoup
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.tools import tool


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    vec1, vec2 = np.array(vec1), np.array(vec2)
    dot = np.dot(vec1, vec2)
    norm1, norm2 = np.linalg.norm(vec1), np.linalg.norm(vec2)
    return dot / (norm1 * norm2) if norm1 and norm2 else 0.0


def get_uri_source_tool(settings: Dict[str, Any]):
    """
    Factory that returns a LangChain tool for URI search,
    preconfigured with connector settings (like fixed URL).
    """

    url = settings.get("url")
    embedding_model = OpenAIEmbeddings()

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

        # Extract and clean page text
        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text(separator=" ", strip=True)
        if not page_text:
            return f"Error: No text content extracted from {url}"

        # Split into chunks
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_text(page_text)
        if not chunks:
            return f"Error: Could not split {url} content into chunks."

        # Embed + rank by similarity
        chunk_embeddings = embedding_model.embed_documents(chunks)
        query_embedding = embedding_model.embed_query(query)

        scored = [
            {"text": chunks[i], "score": cosine_similarity(query_embedding, emb)}
            for i, emb in enumerate(chunk_embeddings)
        ]
        top_chunks = sorted(scored, key=lambda x: x["score"], reverse=True)[:3]

        if not top_chunks or top_chunks[0]["score"] < 0.7:
            return "Could not find any relevant information in the source URI for that query."

        combined_context = "\n\n---\n\n".join([c["text"] for c in top_chunks])
        return f"Found relevant information from {url}:\n\n{combined_context}"

    return uri_search