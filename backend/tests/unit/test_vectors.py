"""
Comprehensive tests for vectors module.

Tests cover:
- Embedding generation (sentence transformers, mock)
- Vector similarity calculations
- Semantic search service
- Pinecone integration (mocked)
- Caching behavior
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from core.vectors import (
    EmbeddingService,
    HybridEmbeddingService,
    create_embedding_service,
    SemanticSearchService
)


class TestEmbeddingService:
    """Test EmbeddingService."""

    def test_embedding_service_initialization(self):
        """Test creating embedding service."""
        service = EmbeddingService(provider="mock")
        
        assert service.provider == "mock"
        assert service.embedding_dim == 384
        assert service.cache is not None

    def test_generate_embedding_returns_vector(self):
        """Test that embedding generation returns a vector."""
        service = EmbeddingService(provider="mock")
        
        embedding = service.generate_embedding("test text")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)

    def test_generate_embedding_same_text_same_vector(self):
        """Test that same text produces same embedding (mock)."""
        service = EmbeddingService(provider="mock")
        
        emb1 = service.generate_embedding("hello world")
        emb2 = service.generate_embedding("hello world")
        
        # Mock uses deterministic seed based on text
        assert emb1 == emb2

    def test_generate_embedding_different_text_different_vector(self):
        """Test that different text produces different embeddings."""
        service = EmbeddingService(provider="mock")
        
        emb1 = service.generate_embedding("hello")
        emb2 = service.generate_embedding("goodbye")
        
        assert emb1 != emb2

    def test_empty_text_returns_zero_vector(self):
        """Test that empty text returns zero vector."""
        service = EmbeddingService(provider="mock")
        
        embedding = service.generate_embedding("")
        
        assert all(x == 0.0 for x in embedding)

    def test_caching_enabled_by_default(self):
        """Test that caching is enabled by default."""
        service = EmbeddingService(provider="mock")
        
        # Generate embedding
        emb1 = service.generate_embedding("test")
        
        # Check cache
        assert len(service.cache) > 0

    def test_generate_embeddings_batch(self):
        """Test batch embedding generation."""
        service = EmbeddingService(provider="mock")
        
        texts = ["text 1", "text 2", "text 3"]
        embeddings = service.generate_embeddings_batch(texts)
        
        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)

    def test_calculate_similarity(self):
        """Test cosine similarity calculation."""
        service = EmbeddingService(provider="mock")
        
        # Identical vectors should have similarity ~1.0
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        sim = service.calculate_similarity(vec1, vec2)
        assert abs(sim - 1.0) < 0.01
        
        # Orthogonal vectors should have similarity ~0.0
        vec3 = [1.0, 0.0, 0.0]
        vec4 = [0.0, 1.0, 0.0]
        sim = service.calculate_similarity(vec3, vec4)
        assert abs(sim - 0.0) < 0.01

    def test_find_similar(self):
        """Test finding similar embeddings."""
        service = EmbeddingService(provider="mock")
        
        query = service.generate_embedding("machine learning")
        
        # Create some candidate embeddings
        candidates = [
            service.generate_embedding("machine learning"),  # Very similar
            service.generate_embedding("deep learning"),     # Somewhat similar
            service.generate_embedding("cooking recipes")    # Not similar
        ]
        
        results = service.find_similar(query, candidates, top_k=2)
        
        assert len(results) <= 2
        assert len(results) > 0  # Should have at least one result
        # Results are tuples of (index, similarity)
        assert all(isinstance(r, tuple) for r in results)
        assert all(len(r) == 2 for r in results)
        # First result should have highest similarity
        if len(results) >= 2:
            assert results[0][1] >= results[1][1]

    def test_get_model_info(self):
        """Test getting model information."""
        service = EmbeddingService(provider="mock", model_name="test-model")
        
        info = service.get_model_info()
        
        assert info["provider"] == "mock"
        assert info["model_name"] == "test-model"
        assert info["embedding_dimension"] == 384
        assert info["cache_enabled"] is True


class TestHybridEmbeddingService:
    """Test HybridEmbeddingService."""

    def test_hybrid_initialization(self):
        """Test creating hybrid embedding service."""
        models = [
            {"provider": "mock", "model_name": "model1"},
            {"provider": "mock", "model_name": "model2"}
        ]
        
        service = HybridEmbeddingService(models)
        
        assert len(service.services) == 2
        assert service.embedding_dim == 384 * 2  # Combined dimension

    def test_hybrid_generate_embedding(self):
        """Test hybrid embedding generation."""
        models = [
            {"provider": "mock", "model_name": "model1"},
            {"provider": "mock", "model_name": "model2"}
        ]
        
        service = HybridEmbeddingService(models)
        embedding = service.generate_embedding("test")
        
        # Should concatenate both embeddings
        assert len(embedding) == 768  # 384 * 2


class TestCreateEmbeddingService:
    """Test embedding service factory."""

    def test_create_with_no_config(self):
        """Test creating service with default config."""
        service = create_embedding_service()
        
        assert service is not None
        assert service.provider in ["sentence-transformers", "mock"]

    def test_create_with_custom_config(self):
        """Test creating service with custom config."""
        config = {
            "provider": "mock",
            "model_name": "custom-model",
            "cache_embeddings": False
        }
        
        service = create_embedding_service(config)
        
        assert service.provider == "mock"
        assert service.model_name == "custom-model"
        assert service.cache is None  # Caching disabled

    def test_model_name_shortcuts(self):
        """Test that model name shortcuts are expanded."""
        config = {"provider": "mock", "model_name": "mini"}
        service = create_embedding_service(config)
        
        assert "MiniLM" in service.model_name


class TestSemanticSearchService:
    """Test SemanticSearchService."""

    @pytest.fixture
    def search_service(self):
        """Create search service with mocks."""
        embedding_service = EmbeddingService(provider="mock")
        pinecone_client = Mock()
        
        service = SemanticSearchService(
            embedding_service=embedding_service,
            pinecone_client=pinecone_client
        )
        service.chunk_repo = Mock()
        service.doc_repo = Mock()
        
        return service

    def test_search_service_initialization(self):
        """Test search service initializes correctly."""
        service = SemanticSearchService()
        
        assert service.embedding_service is not None
        assert service.pinecone_client is not None
        assert service.chunk_repo is not None
        assert service.doc_repo is not None

    def test_index_document_generates_embeddings(self, search_service):
        """Test that indexing generates embeddings for all chunks."""
        from core.models import Document, DocumentChunk, DocumentType
        
        doc = Document(
            id="doc123",
            user_id="user123",
            filename="test.pdf",
            original_filename="test.pdf",
            file_path="/path/test.pdf",
            file_size=1024,
            file_hash="hash123",
            document_type=DocumentType.PDF
        )
        
        chunks = [
            DocumentChunk(
                id=f"chunk{i}",
                document_id="doc123",
                user_id="user123",
                chunk_index=i,
                content=f"Content {i}",
                char_count=100,
                word_count=20
            )
            for i in range(3)
        ]
        
        search_service.pinecone_manager.index_document_chunks = Mock(return_value=True)
        search_service.chunk_repo.update_chunk_vectors = Mock()
        
        success, message = search_service.index_document(doc, chunks)
        
        assert success is True
        # Should call update for each chunk
        assert search_service.chunk_repo.update_chunk_vectors.call_count == 3


class TestModuleExports:
    """Test module exports."""

    def test_exports_all_required_symbols(self):
        """Test that __all__ exports all required symbols."""
        from core.vectors import __all__
        
        expected = [
            "EmbeddingService",
            "HybridEmbeddingService",
            "create_embedding_service",
            "PineconeClient",
            "PineconeManager",
            "SemanticSearchService"
        ]
        
        assert set(__all__) == set(expected)

    def test_can_import_all_symbols(self):
        """Test that all exported symbols can be imported."""
        from core.vectors import (
            EmbeddingService,
            HybridEmbeddingService,
            create_embedding_service,
            PineconeClient,
            PineconeManager,
            SemanticSearchService
        )
        
        assert EmbeddingService is not None
        assert HybridEmbeddingService is not None
        assert callable(create_embedding_service)
        assert PineconeClient is not None
        assert PineconeManager is not None
        assert SemanticSearchService is not None
