"""
Custom Embedding Functions for Vector Stores
Avoids Windows DLL issues with onnxruntime by using OpenAI directly
Compatible with both ChromaDB and pgvector
"""

import hashlib
import os
import logging
from typing import List, Dict
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIEmbeddings:
    """
    Custom OpenAI embedding function that works reliably on Windows
    Compatible with ChromaDB's embedding function interface
    """
    
    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required for embeddings")

        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        # In-memory cache: hash(text) → embedding vector.
        # Avoids repeated OpenAI API calls for the same query text within a session.
        self._cache: Dict[str, List[float]] = {}
        logger.info(f"Initialized OpenAI embeddings with model: {model}")
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts
        
        Args:
            input: List of text strings to embed
            
        Returns:
            List of embedding vectors (lists of floats)
        """
        try:
            results: List[List[float]] = []
            uncached_texts: List[str] = []
            uncached_indices: List[int] = []

            # Check cache first
            for i, text in enumerate(input):
                key = hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()
                if key in self._cache:
                    results.append(self._cache[key])
                else:
                    results.append(None)  # placeholder
                    uncached_texts.append(text)
                    uncached_indices.append(i)

            if uncached_texts:
                # Batch API call for only the uncached texts
                response = self.client.embeddings.create(
                    model=self.model,
                    input=uncached_texts,
                )
                for i, (orig_idx, item) in enumerate(zip(uncached_indices, response.data)):
                    text = uncached_texts[i]
                    key = hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()
                    self._cache[key] = item.embedding
                    results[orig_idx] = item.embedding

            logger.debug(f"Returned {len(results)} embeddings ({len(uncached_texts)} new, {len(input) - len(uncached_texts)} cached)")
            return results

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

