"""Embedding service using OpenAI text-embedding-3-small."""
import logging
from typing import List
from openai import OpenAI
from ..config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536


class EmbeddingService:
    """Generates semantic embeddings via OpenAI API."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)

    def embed_query(self, text: str) -> List[float]:
        """Generate a 1536-dimension embedding for a search query."""
        logger.info("Generating embedding for query (length=%d chars)", len(text))
        response = self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
        )
        embedding = response.data[0].embedding
        logger.info("Embedding generated: dimension=%d", len(embedding))
        return embedding

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Batch embed multiple texts (for ingestion)."""
        logger.info("Generating embeddings for %d texts", len(texts))
        response = self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
        )
        embeddings = [item.embedding for item in response.data]
        logger.info("Generated %d embeddings", len(embeddings))
        return embeddings
