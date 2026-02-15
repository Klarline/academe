"""
Comprehensive tests for document processing module.

Tests cover:
- PDF processing and text extraction
- Text file processing
- Document chunking strategies
- File storage operations
- Document management workflow
- Metadata extraction
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from core.documents import (
    PDFProcessor,
    TextProcessor,
    DocumentProcessorFactory,
    DocumentChunker,
    DocumentStorage,
    DocumentManager
)
from core.models import Document, DocumentChunk, DocumentStatus, DocumentType


class TestPDFProcessor:
    """Test PDF processing functionality."""

    @pytest.fixture
    def pdf_processor(self):
        """Create PDFProcessor instance."""
        return PDFProcessor()

    def test_supported_extensions(self, pdf_processor):
        """Test PDF processor supports correct extensions."""
        assert '.pdf' in pdf_processor.supported_extensions
        assert len(pdf_processor.supported_extensions) == 1

    def test_calculate_file_hash(self, pdf_processor):
        """Test file hash calculation."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            hash1 = pdf_processor.calculate_file_hash(temp_path)
            hash2 = pdf_processor.calculate_file_hash(temp_path)
            
            # Same file should produce same hash
            assert hash1 == hash2
            assert isinstance(hash1, str)
            assert len(hash1) == 64  # SHA256 is 64 hex chars
        finally:
            os.unlink(temp_path)

    def test_validate_pdf_file_not_found(self, pdf_processor):
        """Test validation with non-existent file."""
        is_valid, error = pdf_processor.validate_pdf("/nonexistent/file.pdf")
        assert is_valid is False
        assert error is not None


class TestTextProcessor:
    """Test text file processing."""

    @pytest.fixture
    def text_processor(self):
        """Create TextProcessor instance."""
        return TextProcessor()

    def test_supported_extensions(self, text_processor):
        """Test text processor supports correct extensions."""
        assert '.txt' in text_processor.supported_extensions
        assert '.md' in text_processor.supported_extensions
        assert '.markdown' in text_processor.supported_extensions

    def test_process_text_file(self, text_processor):
        """Test processing a text file."""
        # Create temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content\nLine 2\nLine 3")
            temp_path = f.name
        
        try:
            content, metadata = text_processor.process_text_file(temp_path)
            
            assert "Test content" in content
            assert metadata['filename'].endswith('.txt')
            assert metadata['word_count'] == 6  # "Test content Line 2 Line 3"
            assert metadata['line_count'] == 2
        finally:
            os.unlink(temp_path)

    def test_process_markdown_extracts_title(self, text_processor):
        """Test that markdown title is extracted."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test Title\n\nContent here")
            temp_path = f.name
        
        try:
            content, metadata = text_processor.process_text_file(temp_path)
            assert metadata.get('title') == "Test Title"
        finally:
            os.unlink(temp_path)


class TestDocumentProcessorFactory:
    """Test document processor factory."""

    @pytest.fixture
    def factory(self):
        """Create factory instance."""
        return DocumentProcessorFactory()

    def test_get_pdf_processor(self, factory):
        """Test getting PDF processor."""
        processor = factory.get_processor("/path/to/file.pdf")
        assert isinstance(processor, PDFProcessor)

    def test_get_text_processor(self, factory):
        """Test getting text processor."""
        for ext in ['.txt', '.md', '.markdown']:
            processor = factory.get_processor(f"/path/to/file{ext}")
            assert isinstance(processor, TextProcessor)

    def test_unsupported_file_type(self, factory):
        """Test that unsupported file type raises error."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            factory.get_processor("/path/to/file.docx")


class TestDocumentChunker:
    """Test document chunking."""

    @pytest.fixture
    def chunker(self):
        """Create DocumentChunker instance."""
        return DocumentChunker(chunk_size=100, chunk_overlap=20)

    def test_chunk_document_creates_chunks(self, chunker):
        """Test that chunking creates DocumentChunk objects."""
        text = "This is a test document. " * 50  # ~250 words
        
        chunks = chunker.chunk_document(
            text=text,
            document_id="doc123",
            user_id="user123"
        )
        
        assert len(chunks) > 0
        assert all(isinstance(c, DocumentChunk) for c in chunks)
        assert all(c.document_id == "doc123" for c in chunks)
        assert all(c.user_id == "user123" for c in chunks)

    def test_chunk_has_required_fields(self, chunker):
        """Test that chunks have all required fields."""
        text = "Test content here"
        
        chunks = chunker.chunk_document(text, "doc123", "user123")
        
        chunk = chunks[0]
        assert chunk.content is not None
        assert chunk.chunk_index >= 0
        assert chunk.char_count > 0
        assert chunk.word_count > 0

    def test_chunk_indices_sequential(self, chunker):
        """Test that chunk indices are sequential."""
        text = "Word " * 200
        
        chunks = chunker.chunk_document(text, "doc123", "user123")
        
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_empty_text_produces_no_chunks(self, chunker):
        """Test that empty text produces no chunks."""
        chunks = chunker.chunk_document("   ", "doc123", "user123")
        assert len(chunks) == 0

    def test_content_detection_equations(self, chunker):
        """Test equation detection."""
        text_with_math = "The equation is: ∑x² = √(y + z)"
        chunks = chunker.chunk_document(text_with_math, "doc123", "user123")
        assert chunks[0].has_equations is True
        
        text_no_math = "This is plain text"
        chunks = chunker.chunk_document(text_no_math, "doc123", "user123")
        assert chunks[0].has_equations is False

    def test_content_detection_code(self, chunker):
        """Test code detection."""
        text_with_code = "def hello():\n    print('hi')"
        chunks = chunker.chunk_document(text_with_code, "doc123", "user123")
        assert chunks[0].has_code is True


class TestDocumentStorage:
    """Test document storage operations."""

    @pytest.fixture
    def storage(self):
        """Create DocumentStorage with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = DocumentStorage(storage_path=tmpdir)
            yield storage

    def test_storage_initialization(self, storage):
        """Test storage directory is created."""
        assert storage.storage_path.exists()
        assert storage.storage_path.is_dir()

    def test_save_document_file(self, storage):
        """Test saving a document file."""
        # Create temp source file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            source_path = f.name
        
        try:
            saved_path = storage.save_document_file(
                source_path=source_path,
                user_id="user123",
                document_id="doc456"
            )
            
            assert Path(saved_path).exists()
            assert "user123" in saved_path
            assert "doc456" in saved_path
        finally:
            os.unlink(source_path)
            if Path(saved_path).exists():
                os.unlink(saved_path)

    def test_delete_document_file(self, storage):
        """Test deleting a document file."""
        # Create file to delete
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        
        assert Path(temp_path).exists()
        result = storage.delete_document_file(temp_path)
        assert result is True
        assert not Path(temp_path).exists()


class TestDocumentManager:
    """Test DocumentManager orchestration."""

    @pytest.fixture
    def manager(self):
        """Create DocumentManager with mocks."""
        with patch('core.documents.manager.DocumentStorage') as mock_storage:
            with patch('core.documents.manager.DocumentRepository') as mock_repo:
                manager = DocumentManager()
                manager.storage = mock_storage.return_value
                manager.doc_repo = mock_repo.return_value
                yield manager

    def test_manager_initialization(self):
        """Test manager initializes all components."""
        manager = DocumentManager()
        
        assert manager.storage is not None
        assert manager.doc_repo is not None
        assert manager.chunk_repo is not None
        assert manager.processor_factory is not None
        assert manager.chunker is not None
