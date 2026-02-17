"""Embedding service supporting multiple providers (OpenAI, Gemini).

The provider is selected via the EMBEDDING_PROVIDER env var (default: "openai").
Model and dimension can be overridden via EMBEDDING_MODEL / EMBEDDING_DIMENSION.
"""
import logging
from typing import List

from ..config import settings

logger = logging.getLogger(__name__)

# Provider-specific defaults
_DEFAULTS = {
    "openai": {"model": "text-embedding-3-small", "dimension": 1536},
    "gemini": {"model": "gemini-embedding-001", "dimension": 768},
}


def _resolve(provider: str):
    """Return (model, dimension) for the given provider.

    Ignores EMBEDDING_MODEL / EMBEDDING_DIMENSION overrides when they
    clearly belong to a different provider (e.g. an OpenAI model name
    while the provider is gemini).
    """
    defaults = _DEFAULTS.get(provider, _DEFAULTS["openai"])
    model = settings.embedding_model
    dimension = settings.embedding_dimension

    # Detect cross-provider mismatch and fall back to defaults
    if model:
        # Also catch the old deprecated Gemini model names
        _KNOWN_OPENAI = {"text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"}
        _KNOWN_GEMINI = {"models/text-embedding-004", "models/embedding-001", "gemini-embedding-001"}

        if provider == "gemini" and model in _KNOWN_OPENAI:
            print(
                f"[config] WARNING: EMBEDDING_MODEL={model!r} is an OpenAI model "
                f"— ignoring override, using default {defaults['model']!r}"
            )
            model = None
            dimension = None
        elif provider == "openai" and model in _KNOWN_GEMINI:
            print(
                f"[config] WARNING: EMBEDDING_MODEL={model!r} is a Gemini model "
                f"— ignoring override, using default {defaults['model']!r}"
            )
            model = None
            dimension = None

    model = model or defaults["model"]
    dimension = dimension or defaults["dimension"]
    return model, dimension


class EmbeddingService:
    """Generates semantic embeddings via the configured provider."""

    def __init__(self):
        self.provider = (settings.embedding_provider or "openai").lower()
        self.model, self.dimension = _resolve(self.provider)

        if self.provider == "gemini":
            key = settings.gemini_api_key
            if key:
                logger.info("GEMINI_API_KEY found (%s…%s)", key[:4], key[-4:])
            else:
                logger.error("GEMINI_API_KEY is NOT set — embedding calls will fail!")
            from google import genai
            self._genai_client = genai.Client(api_key=key)
        elif self.provider == "openai":
            key = settings.openai_api_key
            if key:
                logger.info("OPENAI_API_KEY found (%s…%s)", key[:4], key[-4:])
            else:
                logger.error("OPENAI_API_KEY is NOT set — embedding calls will fail!")
            from openai import OpenAI
            self._openai = OpenAI(api_key=key)
        else:
            raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {self.provider!r}")

        print(f"[config] Provider initialized: provider={self.provider} model={self.model} dimension={self.dimension}")
        logger.info(
            "EmbeddingService initialised: provider=%s  model=%s  dimension=%d",
            self.provider, self.model, self.dimension,
        )

    # ------------------------------------------------------------------

    def embed_query(self, text: str) -> List[float]:
        """Generate an embedding for a single search query."""
        logger.info("Generating embedding for query (length=%d chars)", len(text))
        if self.provider == "gemini":
            embedding = self._embed_gemini([text])[0]
        else:
            embedding = self._embed_openai([text])[0]
        logger.info("Embedding generated: dimension=%d", len(embedding))
        return embedding

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Batch embed multiple texts (for ingestion)."""
        logger.info("Generating embeddings for %d texts", len(texts))
        if self.provider == "gemini":
            embeddings = self._embed_gemini(texts)
        else:
            embeddings = self._embed_openai(texts)
        logger.info("Generated %d embeddings", len(embeddings))
        return embeddings

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        response = self._openai.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]

    def _embed_gemini(self, texts: List[str]) -> List[List[float]]:
        from google.genai import types

        result = self._genai_client.models.embed_content(
            model=self.model,
            contents=texts,
            config=types.EmbedContentConfig(output_dimensionality=self.dimension),
        )
        return [emb.values for emb in result.embeddings]
