"""Service for generating text embeddings via Google Generative AI.

Uses the text-embedding-004 model (768 dimensions) from Google's API,
which is the same API key used for Gemini agents.
"""

from __future__ import annotations

import hashlib
from typing import Sequence

from google import genai
from google.genai.types import HttpOptions

from app.config import settings
from app.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Generates text embeddings using Google's Generative AI embedding models.

    This service wraps the google-genai SDK to produce dense vector
    representations of text for semantic search via pgvector.
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._model = model or settings.embedding_model
        # text-embedding-004 is only available on API v1, not v1beta
        # (which is the default in google-genai SDK).
        self._client = genai.Client(
            api_key=api_key or settings.google_api_key,
            http_options=HttpOptions(api_version="v1"),
        )

    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text.

        Args:
            text: The text to embed. Will be truncated at ~8000 chars
                  to stay within model token limits.

        Returns:
            List of floats representing the embedding vector.

        Raises:
            Exception: If the embedding API call fails.
        """
        # Truncate to avoid token limits (~8000 chars ≈ ~2000 tokens)
        truncated = text[:8000] if len(text) > 8000 else text

        try:
            result = self._client.models.embed_content(
                model=self._model,
                contents=truncated,
            )
            return result.embeddings[0].values
        except Exception as e:
            logger.error(
                "embedding.generate_error",
                model=self._model,
                text_length=len(text),
                error=str(e),
            )
            raise

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors, one per input text.
        """
        if not texts:
            return []

        truncated = [t[:8000] if len(t) > 8000 else t for t in texts]

        try:
            result = self._client.models.embed_content(
                model=self._model,
                contents=truncated,
            )
            return [e.values for e in result.embeddings]
        except Exception as e:
            logger.error(
                "embedding.batch_error",
                model=self._model,
                count=len(texts),
                error=str(e),
            )
            raise

    @staticmethod
    def content_hash(text: str) -> str:
        """Generate a SHA-256 hash of text content.

        Used to avoid re-embedding identical content.

        Args:
            text: Text to hash.

        Returns:
            Hex digest of SHA-256 hash.
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
