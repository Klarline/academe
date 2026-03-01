"""
Tests for advanced chunking and retrieval features.

Covers:
- Document type auto-detection
- Adaptive chunking
- Parent-child chunking
- Chunk context enrichment (contextual embeddings)
- Sliding window context building
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from core.documents.doc_type_detector import ContentType, detect_document_type
from core.vectors.search import SemanticSearchService
from core.models.document import DocumentChunk, Document, DocumentSearchResult, DocumentType


def _make_chunker(**kwargs):
    """Create a DocumentChunker with TokenTextSplitter patched to avoid network."""
    with patch("core.documents.chunker.TokenTextSplitter") as MockTTS:
        MockTTS.return_value = Mock()
        MockTTS.return_value.split_text = lambda t: [t]
        from core.documents.chunker import DocumentChunker
        return DocumentChunker(**kwargs)


# ---------------------------------------------------------------------------
# Document type detection
# ---------------------------------------------------------------------------

class TestDetectDocumentType:
    """Test auto-detection of document content type."""

    def test_textbook_detection(self):
        text = (
            "Chapter 1: Introduction\n"
            "Section 1.1 Overview\n"
            "Definition 1.1: A graph is ...\n"
            "Theorem 2.3: For every connected graph ...\n"
        ) * 20
        assert detect_document_type(text, page_count=50) == ContentType.TEXTBOOK

    def test_paper_detection(self):
        abstract = "Abstract\nWe propose a novel approach to ..."
        body = "Introduction\nRelated Work\nMethodology\n" * 10
        refs = "References\n[1] Smith et al. 2023 proceedings\n"
        text = abstract + body + refs
        assert detect_document_type(text, page_count=12) == ContentType.PAPER

    def test_notes_detection(self):
        text = "\n".join(
            f"- bullet point {i}" for i in range(30)
        )
        assert detect_document_type(text, page_count=2) == ContentType.NOTES

    def test_code_detection(self):
        text = "\n".join([
            "import os",
            "import sys",
            "from pathlib import Path",
            "def main():",
            "    print('hello')",
            "class Foo:",
            "    pass",
        ] * 5)
        assert detect_document_type(text) == ContentType.CODE

    def test_general_fallback(self):
        text = "Some generic text without strong signals."
        assert detect_document_type(text) == ContentType.GENERAL

    def test_empty_text(self):
        assert detect_document_type("") == ContentType.GENERAL

    def test_filename_hints_paper(self):
        text = "Some text about machine learning " * 20
        result = detect_document_type(text, filename="arxiv_2024_attention.pdf")
        assert result == ContentType.PAPER

    def test_filename_hints_notes(self):
        text = "Some text " * 10
        result = detect_document_type(text, page_count=2, filename="lecture_notes_week3.md")
        assert result == ContentType.NOTES


# ---------------------------------------------------------------------------
# Adaptive chunking
# ---------------------------------------------------------------------------

class TestAdaptiveChunking:
    """Test adaptive_chunk creates chunks with correct per-type parameters."""

    @pytest.fixture
    def chunker(self):
        return _make_chunker(chunk_size=1000, chunk_overlap=200)

    @patch("core.documents.chunker.TokenTextSplitter")
    def test_adaptive_does_not_mutate_state(self, mock_tts, chunker):
        """adaptive_chunk should not change the instance's chunk_size/overlap."""
        original_size = chunker.chunk_size
        original_overlap = chunker.chunk_overlap
        text = "Word " * 500
        chunker.adaptive_chunk(text, "textbook", "doc1", "user1")
        assert chunker.chunk_size == original_size
        assert chunker.chunk_overlap == original_overlap

    @patch("core.documents.chunker.TokenTextSplitter")
    def test_textbook_uses_larger_chunks(self, mock_tts, chunker):
        text = "Word " * 1000
        chunks = chunker.adaptive_chunk(text, "textbook", "doc1", "user1")
        avg_len = sum(c.char_count for c in chunks) / max(len(chunks), 1)
        # Textbook target is 1200 — average should be larger than default 1000
        assert avg_len > 800

    @patch("core.documents.chunker.TokenTextSplitter")
    def test_paper_uses_smaller_chunks(self, mock_tts, chunker):
        text = "Word " * 1000
        chunks = chunker.adaptive_chunk(text, "paper", "doc1", "user1")
        avg_len = sum(c.char_count for c in chunks) / max(len(chunks), 1)
        assert avg_len < 1000

    @patch("core.documents.chunker.TokenTextSplitter")
    def test_metadata_passed_through(self, mock_tts, chunker):
        text = "Hello world content here. " * 20
        chunks = chunker.adaptive_chunk(
            text, "general", "doc1", "user1",
            metadata={"document_title": "My Doc"},
        )
        assert len(chunks) > 0
        assert chunks[0].metadata.get("document_title") == "My Doc"


# ---------------------------------------------------------------------------
# Parent-child chunking
# ---------------------------------------------------------------------------

class TestParentChildChunking:
    """Test two-level parent-child chunking."""

    @pytest.fixture
    def chunker(self):
        return _make_chunker(chunk_size=1000, chunk_overlap=200)

    @patch("core.documents.chunker.TokenTextSplitter")
    def test_children_reference_parent(self, mock_tts, chunker):
        text = "Sentence about topic. " * 200
        children = chunker.chunk_with_parents(
            text, "doc1", "user1",
            parent_size=500, child_size=150, child_overlap=20,
        )
        assert len(children) > 0
        for child in children:
            assert "parent_chunk_index" in child.metadata
            assert "parent_content" in child.metadata
            assert isinstance(child.metadata["parent_chunk_index"], int)

    @patch("core.documents.chunker.TokenTextSplitter")
    def test_children_smaller_than_parents(self, mock_tts, chunker):
        text = "Sentence about topic. " * 200
        children = chunker.chunk_with_parents(
            text, "doc1", "user1",
            parent_size=500, child_size=150, child_overlap=20,
        )
        for child in children:
            assert child.char_count <= len(child.metadata["parent_content"])

    @patch("core.documents.chunker.TokenTextSplitter")
    def test_all_children_have_valid_content(self, mock_tts, chunker):
        text = "Hello world. " * 100
        children = chunker.chunk_with_parents(text, "doc1", "user1")
        for child in children:
            assert child.content.strip()
            assert child.char_count > 0


# ---------------------------------------------------------------------------
# Contextual embedding enrichment
# ---------------------------------------------------------------------------

class TestContextualEmbeddings:
    """Test that index_document enriches text before embedding."""

    def test_enrich_with_title_and_section(self):
        enriched = SemanticSearchService._enrich_text_for_embedding(
            "Some chunk text",
            document_title="Machine Learning 101",
            section_title="Chapter 3",
        )
        assert "Document: Machine Learning 101" in enriched
        assert "Section: Chapter 3" in enriched
        assert "Some chunk text" in enriched

    def test_enrich_with_title_only(self):
        enriched = SemanticSearchService._enrich_text_for_embedding(
            "Chunk content",
            document_title="My Paper",
        )
        assert "Document: My Paper" in enriched
        assert "Section:" not in enriched
        assert "Chunk content" in enriched

    def test_enrich_no_metadata(self):
        enriched = SemanticSearchService._enrich_text_for_embedding("Raw text")
        assert enriched == "Raw text"


# ---------------------------------------------------------------------------
# Sliding window context
# ---------------------------------------------------------------------------

class TestSlidingWindowContext:
    """Test context builder expands chunks with neighbors."""

    def _make_result(self, doc_id, chunk_idx, content, meta=None):
        chunk = DocumentChunk(
            document_id=doc_id,
            user_id="user1",
            chunk_index=chunk_idx,
            content=content,
            char_count=len(content),
            word_count=len(content.split()),
            metadata=meta or {},
        )
        doc = Document(
            id=doc_id,
            user_id="user1",
            filename="test.pdf",
            original_filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            file_hash="abc",
            document_type=DocumentType.PDF,
            title="Test Doc",
        )
        return DocumentSearchResult(chunk=chunk, document=doc, score=0.9, rank=1)

    @patch("core.rag.pipeline.ChunkRepository")
    @patch("core.rag.pipeline.SemanticSearchService")
    @patch("core.rag.pipeline.DocumentManager")
    def test_sliding_window_includes_neighbors(self, MockDM, MockSS, MockCR):
        from core.rag.pipeline import RAGPipeline

        pipeline = RAGPipeline(
            search_service=MockSS(),
            document_manager=MockDM(),
            use_hybrid_search=False,
            use_query_rewriting=False,
        )

        neighbor_chunks = [
            DocumentChunk(
                document_id="doc1", user_id="user1", chunk_index=i,
                content=f"Neighbor {i} text", char_count=15, word_count=3,
            )
            for i in range(3)
        ]
        pipeline.chunk_repo = Mock()
        pipeline.chunk_repo.get_adjacent_chunks.return_value = neighbor_chunks

        result = self._make_result("doc1", 1, "Main chunk text")
        context = pipeline._build_context([result])

        assert "Neighbor 0 text" in context
        assert "Neighbor 1 text" in context
        assert "Neighbor 2 text" in context

    @patch("core.rag.pipeline.ChunkRepository")
    @patch("core.rag.pipeline.SemanticSearchService")
    @patch("core.rag.pipeline.DocumentManager")
    def test_parent_child_uses_parent_content(self, MockDM, MockSS, MockCR):
        from core.rag.pipeline import RAGPipeline

        pipeline = RAGPipeline(
            search_service=MockSS(),
            document_manager=MockDM(),
            use_hybrid_search=False,
            use_query_rewriting=False,
        )
        pipeline.chunk_repo = Mock()

        result = self._make_result(
            "doc1", 2, "Small child chunk",
            meta={"parent_chunk_index": 0, "parent_content": "Full parent text here"},
        )
        context = pipeline._build_context([result])

        assert "Full parent text here" in context
        assert "Small child chunk" not in context

    @patch("core.rag.pipeline.ChunkRepository")
    @patch("core.rag.pipeline.SemanticSearchService")
    @patch("core.rag.pipeline.DocumentManager")
    def test_deduplication_across_results(self, MockDM, MockSS, MockCR):
        from core.rag.pipeline import RAGPipeline

        pipeline = RAGPipeline(
            search_service=MockSS(),
            document_manager=MockDM(),
            use_hybrid_search=False,
            use_query_rewriting=False,
        )
        pipeline.chunk_repo = Mock()
        pipeline.chunk_repo.get_adjacent_chunks.return_value = [
            DocumentChunk(
                document_id="doc1", user_id="user1", chunk_index=1,
                content="Shared neighbor", char_count=15, word_count=2,
            )
        ]

        r1 = self._make_result("doc1", 1, "Chunk 1")
        r2 = self._make_result("doc1", 1, "Chunk 1")  # same chunk
        context = pipeline._build_context([r1, r2])

        assert context.count("Shared neighbor") == 1


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

class TestDocumentsModuleExports:
    """Test updated exports from documents module."""

    def test_exports_include_new_symbols(self):
        from core.documents import __all__
        assert "ContentType" in __all__
        assert "detect_document_type" in __all__

    def test_can_import_new_symbols(self):
        from core.documents import ContentType, detect_document_type
        assert ContentType is not None
        assert callable(detect_document_type)
