"""Embedding generation service for Academe."""

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
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        provider: str = "sentence-transformers",
        cache_embeddings: bool = True
    ):
        """
        Initialize embedding service.

        Args:
            model_name: Name of the embedding model
            provider: Provider to use (sentence-transformers, openai, custom)
            cache_embeddings: Whether to cache embeddings
        """
        self.model_name = model_name
        self.provider = provider
        self.cache_embeddings = cache_embeddings
        self.cache = {} if cache_embeddings else None
        self._cache_lock = threading.Lock()

        # Initialize model based on provider
        self.model = None
        self._init_model()

    def _init_model(self):
        """Initialize the embedding model."""
        if self.provider == "sentence-transformers":
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

            # For OpenAI, we'll use their API
            self.embedding_dim = 1536  # OpenAI ada-002 dimension
            logger.info("Using OpenAI embeddings")

        elif self.provider == "mock":
            # Mock provider for testing
            self.embedding_dim = 384
            logger.info("Using mock embeddings for testing")

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
            if self.provider == "sentence-transformers":
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

        if self.provider == "sentence-transformers" and self.model:
            # Sentence transformers can handle batch processing
            try:
                # Process in batches
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    batch_embeddings = self.model.encode(batch, convert_to_numpy=True)
                    embeddings.extend(batch_embeddings.tolist())

                logger.info(f"Generated {len(embeddings)} embeddings in batch")
            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                # Fall back to individual processing
                for text in texts:
                    embeddings.append(self.generate_embedding(text))
        else:
            # Process individually for other providers
            for text in texts:
                embeddings.append(self.generate_embedding(text))

        return embeddings

    def _generate_st_embedding(self, text: str) -> List[float]:
        """Generate embedding using sentence-transformers."""
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return self._get_zero_vector()

    def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        try:
            import openai
            from core.config.settings import get_settings

            settings = get_settings()
            openai.api_key = settings.openai_api_key

            response = openai.Embedding.create(
                input=text,
                model="text-embedding-ada-002"
            )
            return response['data'][0]['embedding']
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            return self._get_zero_vector()

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """Generate mock embedding for testing (thread-safe, deterministic per text)."""
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
                model_name=model_config.get("model_name", "all-MiniLM-L6-v2"),
                provider=model_config.get("provider", "sentence-transformers")
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
            # Apply weight
            weighted_embedding = [e * weight for e in embedding]
            embeddings.extend(weighted_embedding)

        return embeddings


def create_embedding_service(config: Optional[Dict[str, Any]] = None) -> EmbeddingService:
    """
    Factory function to create embedding service.

    Args:
        config: Configuration dictionary

    Returns:
        Configured embedding service
    """
    if not config:
        config = {}

    provider = config.get("provider", "sentence-transformers")
    model_name = config.get("model_name", "all-MiniLM-L6-v2")

    # Map common model names to full paths
    model_map = {
        "mini": "all-MiniLM-L6-v2",
        "base": "all-mpnet-base-v2",
        "large": "all-roberta-large-v1",
        "multilingual": "paraphrase-multilingual-MiniLM-L12-v2"
    }

    if model_name in model_map:
        model_name = model_map[model_name]

    # Check if we should use mock for testing
    if provider == "sentence-transformers" and not SENTENCE_TRANSFORMERS_AVAILABLE:
        logger.info("Using mock embeddings for testing (sentence-transformers not installed)")
        provider = "mock"

    return EmbeddingService(
        model_name=model_name,
        provider=provider,
        cache_embeddings=config.get("cache_embeddings", True)
    )