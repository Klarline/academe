"""Embedding generation service for Academe.

Supports multiple providers:
    - gemini (default): Google Gemini embedding-001 via free tier API
    - sentence-transformers: Local all-MiniLM-L6-v2 (offline fallback)
    - openai: OpenAI text-embedding-3-small
    - mock: Deterministic random vectors for testing
"""

import logging
import threading
from typing import List, Optional, Dict, Any
import hashlib
import json

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import google.generativeai as genai
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

import numpy as np

logger = logging.getLogger(__name__)

PROVIDER_DEFAULTS = {
    "gemini": ("gemini-embedding-001", 768),
    "sentence-transformers": ("all-MiniLM-L6-v2", 384),
    "openai": ("text-embedding-3-small", 1536),
    "mock": ("mock", 768),
}


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        cache_embeddings: bool = True,
        embedding_dim: Optional[int] = None,
    ):
        """
        Initialize embedding service.

        Args:
            model_name: Name of the embedding model (auto-detected from provider if None)
            provider: Provider to use (gemini, sentence-transformers, openai, mock).
                      Defaults to gemini if GOOGLE_API_KEY is set, else sentence-transformers.
            cache_embeddings: Whether to cache embeddings
            embedding_dim: Override output dimensions (Gemini supports Matryoshka truncation)
        """
        if provider is None:
            provider = self._auto_detect_provider()
        self.provider = provider

        default_model, default_dim = PROVIDER_DEFAULTS.get(
            provider, PROVIDER_DEFAULTS["mock"]
        )
        self.model_name = model_name or default_model
        self.embedding_dim = embedding_dim or default_dim
        self.cache_embeddings = cache_embeddings
        self.cache = {} if cache_embeddings else None
        self._cache_lock = threading.Lock()

        self.model = None
        self._init_model()

    @staticmethod
    def _auto_detect_provider() -> str:
        """Choose the best available provider based on settings, packages, and API keys."""
        try:
            from core.config.settings import get_settings
            settings = get_settings()
            if settings.embedding_provider:
                return settings.embedding_provider
            if settings.google_api_key and GOOGLE_GENAI_AVAILABLE:
                return "gemini"
        except Exception:
            pass

        if SENTENCE_TRANSFORMERS_AVAILABLE:
            return "sentence-transformers"

        return "mock"

    def _init_model(self):
        """Initialize the embedding model."""
        if self.provider == "gemini":
            if not GOOGLE_GENAI_AVAILABLE:
                logger.warning("google-generativeai not installed, falling back")
                self._fallback_init()
                return
            try:
                from core.config.settings import get_settings
                settings = get_settings()
                if not settings.google_api_key:
                    raise ValueError("GOOGLE_API_KEY not set")
                genai.configure(api_key=settings.google_api_key)
                logger.info(
                    f"Using Gemini embeddings: {self.model_name}, "
                    f"dim={self.embedding_dim}"
                )
            except Exception as e:
                logger.warning(f"Gemini embedding init failed: {e}, falling back")
                self._fallback_init()

        elif self.provider == "sentence-transformers":
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                logger.warning("sentence-transformers not installed, using mock embeddings")
                self.provider = "mock"
                return

            try:
                self.model = SentenceTransformer(self.model_name)
                self.embedding_dim = self.model.get_sentence_embedding_dimension()
                logger.info(f"Loaded {self.model_name} with {self.embedding_dim} dimensions")
            except Exception as e:
                logger.error(f"Failed to load model {self.model_name}: {e}")
                self.provider = "mock"

        elif self.provider == "openai":
            if not OPENAI_AVAILABLE:
                logger.warning("OpenAI not installed, using mock embeddings")
                self.provider = "mock"
                return
            logger.info(f"Using OpenAI embeddings: {self.model_name}, dim={self.embedding_dim}")

        elif self.provider == "mock":
            logger.info(f"Using mock embeddings for testing (dim={self.embedding_dim})")

    def _fallback_init(self):
        """Fall back to sentence-transformers, then mock."""
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            self.provider = "sentence-transformers"
            self.model_name = "all-MiniLM-L6-v2"
            try:
                self.model = SentenceTransformer(self.model_name)
                self.embedding_dim = self.model.get_sentence_embedding_dimension()
                logger.info(f"Fallback to {self.model_name} ({self.embedding_dim} dims)")
                return
            except Exception:
                pass
        self.provider = "mock"
        self.embedding_dim = PROVIDER_DEFAULTS["mock"][1]
        logger.info("Fallback to mock embeddings")

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return self._get_zero_vector()

        cache_key = self._get_cache_key(text) if self.cache_embeddings else None

        with self._cache_lock:
            # Check cache
            if self.cache_embeddings and cache_key in self.cache:
                return self.cache[cache_key]

            # Generate embedding based on provider (under lock for thread-safe model/API use)
            if self.provider == "gemini":
                embedding = self._generate_gemini_embedding(text)
            elif self.provider == "sentence-transformers":
                embedding = self._generate_st_embedding(text)
            elif self.provider == "openai":
                embedding = self._generate_openai_embedding(text)
            else:  # mock
                embedding = self._generate_mock_embedding(text)

            # Cache if enabled
            if self.cache_embeddings and embedding:
                self.cache[cache_key] = embedding

            return embedding

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing

        Returns:
            List of embedding vectors
        """
        embeddings = []

        if self.provider == "gemini":
            try:
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    result = genai.embed_content(
                        model=f"models/{self.model_name}",
                        content=batch,
                        output_dimensionality=self.embedding_dim,
                    )
                    embeddings.extend(result["embedding"])
                logger.info(f"Generated {len(embeddings)} Gemini embeddings in batch")
            except Exception as e:
                logger.error(f"Gemini batch embedding failed: {e}")
                for text in texts:
                    embeddings.append(self.generate_embedding(text))

        elif self.provider == "sentence-transformers" and self.model:
            try:
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    batch_embeddings = self.model.encode(batch, convert_to_numpy=True)
                    embeddings.extend(batch_embeddings.tolist())
                logger.info(f"Generated {len(embeddings)} embeddings in batch")
            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                for text in texts:
                    embeddings.append(self.generate_embedding(text))
        else:
            for text in texts:
                embeddings.append(self.generate_embedding(text))

        return embeddings

    def _generate_gemini_embedding(self, text: str) -> List[float]:
        """Generate embedding using Gemini API (free tier)."""
        try:
            result = genai.embed_content(
                model=f"models/{self.model_name}",
                content=text,
                output_dimensionality=self.embedding_dim,
            )
            return result["embedding"]
        except Exception as e:
            logger.error(f"Gemini embedding failed: {e}")
            return self._get_zero_vector()

    def _generate_st_embedding(self, text: str) -> List[float]:
        """Generate embedding using sentence-transformers."""
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return self._get_zero_vector()

    def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API (v1.0+ SDK)."""
        try:
            from openai import OpenAI
            from core.config.settings import get_settings

            settings = get_settings()
            client = OpenAI(api_key=settings.openai_api_key)

            response = client.embeddings.create(
                input=text,
                model=self.model_name,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            return self._get_zero_vector()

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """Generate deterministic mock embedding for testing (thread-safe)."""
        seed = hash(text) & (2**32 - 1)
        rng = np.random.default_rng(seed)
        embedding = rng.standard_normal(self.embedding_dim)
        # Normalize
        embedding = embedding / np.linalg.norm(embedding)
        return embedding.tolist()

    def _get_zero_vector(self) -> List[float]:
        """Get zero vector of appropriate dimension."""
        return [0.0] * self.embedding_dim

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(f"{self.model_name}:{text}".encode()).hexdigest()

    def calculate_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Similarity score between 0 and 1
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        # Ensure result is between -1 and 1 (floating point errors)
        return float(np.clip(similarity, -1.0, 1.0))

    def find_similar(
        self,
        query_embedding: List[float],
        embeddings: List[List[float]],
        top_k: int = 5,
        threshold: float = 0.0
    ) -> List[tuple[int, float]]:
        """
        Find most similar embeddings to query.

        Args:
            query_embedding: Query vector
            embeddings: List of embeddings to search
            top_k: Number of results to return
            threshold: Minimum similarity threshold

        Returns:
            List of (index, similarity) tuples
        """
        similarities = []

        for idx, embedding in enumerate(embeddings):
            sim = self.calculate_similarity(query_embedding, embedding)
            if sim >= threshold:
                similarities.append((idx, sim))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model."""
        return {
            "provider": self.provider,
            "model_name": self.model_name,
            "embedding_dimension": self.embedding_dim,
            "cache_enabled": self.cache_embeddings,
            "cache_size": len(self.cache) if self.cache else 0
        }


class HybridEmbeddingService(EmbeddingService):
    """
    Hybrid embedding service that combines multiple embedding models.
    Useful for better retrieval performance.
    """

    def __init__(
        self,
        models: List[Dict[str, str]],
        weights: Optional[List[float]] = None
    ):
        """
        Initialize hybrid embedding service.

        Args:
            models: List of model configurations
            weights: Weights for combining embeddings
        """
        self.services = []
        for model_config in models:
            service = EmbeddingService(
                model_name=model_config.get("model_name"),
                provider=model_config.get("provider"),
            )
            self.services.append(service)

        self.weights = weights or [1.0 / len(models)] * len(models)

        # Combined embedding dimension
        self.embedding_dim = sum(s.embedding_dim for s in self.services)

    def generate_embedding(self, text: str) -> List[float]:
        """Generate hybrid embedding by concatenating multiple models."""
        embeddings = []

        for service, weight in zip(self.services, self.weights):
            embedding = service.generate_embedding(text)
            weighted_embedding = [e * weight for e in embedding]
            embeddings.extend(weighted_embedding)

        return embeddings


def create_embedding_service(config: Optional[Dict[str, Any]] = None) -> EmbeddingService:
    """
    Factory function to create embedding service.

    Provider priority (when not specified):
        1. gemini — if GOOGLE_API_KEY is set (free tier, best quality)
        2. sentence-transformers — local, no API key needed
        3. mock — deterministic random vectors

    Args:
        config: Configuration dictionary

    Returns:
        Configured embedding service
    """
    if not config:
        config = {}

    provider = config.get("provider")  # None → auto-detect
    model_name = config.get("model_name")

    # Map common shorthand names
    model_map = {
        "mini": "all-MiniLM-L6-v2",
        "base": "all-mpnet-base-v2",
        "large": "all-roberta-large-v1",
        "multilingual": "paraphrase-multilingual-MiniLM-L12-v2",
    }

    if model_name in model_map:
        model_name = model_map[model_name]

    return EmbeddingService(
        model_name=model_name,
        provider=provider,
        cache_embeddings=config.get("cache_embeddings", True),
        embedding_dim=config.get("embedding_dim"),
    )